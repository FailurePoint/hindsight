package com.failurepoint.goodecho

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/** Contiguous RAM ring buffer. Samples never touch storage here: the only
 *  consumer of data is readLast(), called on an explicit save. */
class RingBuffer(capacityBytes: Int) {
    private val buf = ByteArray(capacityBytes)
    private val lock = ReentrantLock()
    private var writePos = 0L
    private var filled = 0L

    fun write(src: ShortArray, n: Int) = lock.withLock {
        val bytes = ByteArray(n * 2)
        ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer().put(src, 0, n)
        var off = 0
        while (off < bytes.size) {
            val tail = (writePos % buf.size).toInt()
            val n2 = minOf(bytes.size - off, buf.size - tail)
            System.arraycopy(bytes, off, buf, tail, n2)
            writePos += n2; off += n2
        }
        filled = minOf(filled + n * 2, buf.size.toLong())
    }

    fun readLast(shorts: Int): ShortArray = lock.withLock {
        val want = minOf(shorts * 2, filled.toInt()).coerceAtLeast(0)
        val out = ShortArray(want / 2)
        val tmp = ByteArray(want)
        var start = writePos - want
        if (start < 0) start += buf.size.toLong()
        var off = 0
        while (off < want) {
            val idx = (((start + off) % buf.size) + buf.size).toInt() % buf.size
            val n = minOf(want - off, buf.size - idx)
            System.arraycopy(buf, idx, tmp, off, n); off += n
        }
        ByteBuffer.wrap(tmp).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer().get(out)
        out
    }

    fun seconds(rate: Int, ch: Int = 1): Int = (filled / (rate * ch * 2)).toInt()
    fun capacityBytes(): Int = buf.size
}
(