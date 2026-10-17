package com.failurepoint.goodecho

import android.app.Service
import android.content.Intent
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.IBinder
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import kotlin.concurrent.thread

/** Runs as shell uid via Shizuku. All audio stays in this process's RAM;
 *  a clip is only written to storage on an explicit save. */
class ShellUserService : Service() {
    private var recorder: AudioRecord? = null
    private var readThread: Thread? = null
    private val running = AtomicBoolean(false)
    private val saving = AtomicInteger(0)
    private var ring: RingBuffer? = null
    private val sampleRate = 44100
    private val channels = 1

    private val binder = object : IEchoService.Stub() {
        override fun startCapture(modeBytesOrTime: Int, cacheValue: Long): Boolean = start(modeBytesOrTime, cacheValue)
        override fun stopCapture() = stop()
        override fun saveClip(seconds: Int): Boolean = writeClip(seconds)
        override fun isRunning(): Boolean = running.get()
        override fun getBufferSeconds(): Int = ring?.seconds(sampleRate, channels) ?: 0
    }

    override fun onBind(intent: Intent?): IBinder = binder

    private fun start(modeBytesOrTime: Int, cacheValue: Long): Boolean {
        if (running.get()) return true
        val minBuf = AudioRecord.getMinBufferSize(sampleRate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (minBuf <= 0) return false
        val maxHeap = Runtime.getRuntime().maxMemory()
        val capBytes: Long = if (modeBytesOrTime == 0) {
            CaptureConfig.clampMegabytes(cacheValue.toInt(), maxHeap) * 1024L * 1024L
        } else {
            CaptureConfig.clampMinutes(cacheValue.toInt(), sampleRate, maxHeap) * CaptureConfig.bytesPerMinute(sampleRate)
        }
        ring = RingBuffer(capBytes.coerceAtLeast(minBuf.toLong()).toInt())
        val rec = AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, sampleRate,
            AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
            maxOf(minBuf, 4096))
        if (rec.state != AudioRecord.STATE_INITIALIZED) { rec.release(); return false }
        recorder = rec
        rec.startRecording()
        running.set(true)
        readThread = thread(name = "echo-capture", isDaemon = true) { pump(rec) }
        return true
    }

    private fun pump(rec: AudioRecord) {
        val chunk = ShortArray(4096)
        while (running.get()) {
            val n = rec.read(chunk, 0, chunk.size)
            if (n > 0) ring?.write(chunk, n)
        }
    }

    private fun stop() {
        running.set(false)
        readThread?.interrupt(); readThread?.join(500); readThread = null
        recorder?.let { try { it.stop() } catch (_: Exception) {} ; it.release() }
        recorder = null
    }

    private fun writeClip(seconds: Int): Boolean {
        if (!running.get()) return false
        if (saving.getAndIncrement() != 0) { saving.decrementAndGet(); return false }
        try {
            val dir = File(getExternalFilesDir(null), "Recordings").apply { mkdirs() }
            val f = File(dir, "goodecho-" + System.currentTimeMillis().toString() + ".wav")
            FileOutputStream(f).use { out ->
                val shorts = ring?.readLast(seconds.coerceAtLeast(1) * sampleRate * channels) ?: return false
                val bytes = ByteArray(shorts.size * 2)
                ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer().put(shorts)
                out.write(wavHeader(bytes.size.toLong()))
                out.write(bytes)
            }
            return true
        } catch (e: Exception) { return false } finally { saving.decrementAndGet() }
    }

    private fun wavHeader(dataLen: Long): ByteArray = ByteArray(44).also {
        val bb = ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN)
        bb.put("RIFF".toByteArray()); bb.putInt((36 + dataLen).toInt()); bb.put("WAVE".toByteArray())
        bb.put("fmt ".toByteArray()); bb.putInt(16); bb.putShort(1); bb.putShort(channels.toShort())
        bb.putInt(sampleRate); bb.putInt(sampleRate * channels * 2); bb.putShort((channels * 2).toShort()); bb.putShort(16)
        bb.put("data".toByteArray()); bb.putInt(dataLen.toInt())
    }

    override fun onDestroy() { stop(); super.onDestroy() }
}
