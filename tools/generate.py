#!/usr/bin/env python3
"""Programmatic project generator for GoodEcho.

Edit the tables/templates below, run `python3 tools/generate.py`, commit.
The Kotlin/UI code is data-driven so future changes are generator edits, not
hand-edits - minimizes iteration cost.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = "com.failurepoint.goodecho"
PKD = PKG.replace(".", "/")

def w(rel, content):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    print("+", rel)

# ---------------- gradle ----------------
w("settings.gradle.kts", """pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositories { google(); mavenCentral() } }
rootProject.name = "GoodEcho"
include(":app")
""")

w("build.gradle.kts", """plugins {
    id("com.android.application") version "8.7.3" apply false
    id("org.jetbrains.kotlin.android") version "2.1.0" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.1.0" apply false
}
""")

w("gradle.properties", """org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
""")

w("app/build.gradle.kts", """plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "%s"
    compileSdk = 35
    defaultConfig {
        applicationId = "%s"
        minSdk = 28
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }
    buildFeatures { compose = true; aidl = true; buildConfig = true }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}
dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("dev.rikka.shizuku:api:13.1.5")
    implementation("dev.rikka.shizuku:provider:13.1.5")
    implementation("androidx.core:core-ktx:1.15.0")
}
""" % (PKG, PKG))

w("app/proguard-rules.pro", "-keep class %s.** { *; }\n" % PKG)

# ---------------- manifest ----------------
w("app/src/main/AndroidManifest.xml", """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC"/>
    <uses-permission android:name="android.permission.RECORD_AUDIO"/>
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
    <queries>
        <package android:name="moe.shizuku.privileged.api"/>
        <intent><action android:name="rikka.shizuku.manager.intent.START_SHIZUKU"/></intent>
    </queries>
    <application android:label="GoodEcho" android:theme="@style/Theme.GoodEcho"
        android:icon="@drawable/ic_launcher" android:allowBackup="false">
        <activity android:name=".MainActivity" android:exported="true" android:launchMode="singleTask">
            <intent-filter><action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/></intent-filter>
        </activity>
        <service android:name=".ShellUserService" android:exported="false" android:permission="android.permission.BIND_SHIZUKU_SERVICE">
            <intent-filter><action android:name="rikka.shizuku.intent.action.USER_SERVICE"/></intent-filter>
        </service>
        <service android:name=".EchoForegroundService" android:exported="false"
            android:foregroundServiceType="dataSync"/>
        <service android:name=".EchoTileService" android:exported="true" android:label="GoodEcho save clip"
            android:permission="android.permission.BIND_QUICK_SETTINGS_TILE">
            <intent-filter><action android:name="android.service.quicksettings.action.QS_TILE"/></intent-filter>
        </service>
        <receiver android:name=".BootReceiver" android:exported="true">
            <intent-filter><action android:name="android.intent.action.BOOT_COMPLETED"/></intent-filter>
        </receiver>
        <provider android:name="rikka.shizuku.ShizukuProvider"
            android:authorities="${applicationId}.shizuku" android:multiprocess="false"
            android:enabled="true" android:exported="true"
            android:permission="android.permission.INTERACT_ACROSS_USERS_FULL"/>
    </application>
</manifest>
""")

# ---------------- aidl ----------------
w("app/src/main/aidl/%s/IEchoService.aidl" % PKD, """package %s;
interface IEchoService {
    boolean startCapture(int modeBytesOrTime, long cacheValue);
    void stopCapture();
    boolean saveClip(int seconds);
    boolean isRunning();
    int getBufferSeconds();
}
""" % PKG)

# ---------------- capture config ----------------
w("app/src/main/java/%s/CaptureConfig.kt" % PKD, """package %s

enum class CacheMode { BYTES, TIME }

data class CaptureConfig(
    val mode: CacheMode = CacheMode.TIME,
    val cacheMinutes: Int = 30,
    val cacheMegabytes: Int = 64,
    val saveRollbackSeconds: Int = 30,
    val amoled: Boolean = false,
    val autoStart: Boolean = true
) {
    companion object {
        const val MIN_MINUTES = 30
        const val MAX_RAM_FRACTION = 0.30
        /** per-minute 16-bit mono PCM bytes for a sample rate */
        fun bytesPerMinute(rate: Int, ch: Int = 1) = rate.toLong() * ch * 2L * 60L
        fun maxBytes(maxHeap: Long) = (maxHeap * MAX_RAM_FRACTION).toLong()
        fun clampMinutes(m: Int, rate: Int, maxHeap: Long): Int {
            val cap = (maxBytes(maxHeap) / bytesPerMinute(rate)).toInt().coerceAtLeast(MIN_MINUTES)
            return m.coerceIn(MIN_MINUTES, cap)
        }
        fun clampMegabytes(b: Int, maxHeap: Long): Int =
            b.coerceIn(32, (maxBytes(maxHeap) / (1024 * 1024)).toInt().coerceAtLeast(32))
    }
}
""" % PKG)

# ---------------- ring buffer ----------------
w("app/src/main/java/%s/RingBuffer.kt" % PKD, ("""package %s

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
            val tail = (writePos %% buf.size).toInt()
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
            val idx = (((start + off) %% buf.size) + buf.size).toInt() %% buf.size
            val n = minOf(want - off, buf.size - idx)
            System.arraycopy(buf, idx, tmp, off, n); off += n
        }
        ByteBuffer.wrap(tmp).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer().get(out)
        out
    }

    fun seconds(rate: Int, ch: Int = 1): Int = (filled / (rate * ch * 2)).toInt()
    fun capacityBytes(): Int = buf.size
}
(""" % PKG).replace("%%", "%"))

# ---------------- shell user service ----------------
w("app/src/main/java/%s/ShellUserService.kt" % PKD, """package %s

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
""".replace("%s", PKG))

# ---------------- shizuku bridge ----------------
w("app/src/main/java/%s/ShizukuBridge.kt" % PKD, """package %s

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import rikka.shizuku.Shizuku

/** Thin wrapper over the Shizuku user-service bind dance. */
object ShizukuBridge {
    private fun args() = Shizuku.UserServiceArgs(ComponentName(PKG, ShellUserService::class.java.name))
        .processNameSuffix("shell")
        .debuggable(false)
        .version(1)

    fun bind(ctx: Context): Boolean = try {
        val intent = Intent().setClassName(ctx, ShellUserService::class.java.name)
        Shizuku.bindUserService(args(), intent)
        true
    } catch (e: Exception) { false }

    fun service(): IEchoService? = try {
        IEchoService.Stub.asInterface(Shizuku.getUserServiceBinder(args()))
    } catch (e: Exception) { null }
}
""".replace("%s", PKG))

# ---------------- foreground service (app side, no mic type) ----------------
w("app/src/main/java/%s/EchoForegroundService.kt" % PKD, """package %s

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder

/** Keeps the app process alive to hold the Shizuku binding. Deliberately NOT
 *  a microphone-type foreground service: the mic is held by the shell-uid
 *  capture process, not this one. */
class EchoForegroundService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onStartCommand(i: Intent?, f: Int, id: Int): Int {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel("echo", "GoodEcho", NotificationManager.IMPORTANCE_LOW))
        val n = Notification.Builder(this, "echo")
            .setContentTitle("GoodEcho buffer active")
            .setContentText("Recording stays in RAM until you save a clip.")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now).build()
        if (Build.VERSION.SDK_INT >= 30) startForeground(1, n, 0x01000000 /* DATA_SYNC */)
        else startForeground(1, n)
        return START_STICKY
    }
}
""".replace("%s", PKG))

# ---------------- QS tile ----------------
w("app/src/main/java/%s/EchoTileService.kt" % PKD, """package %s

import android.service.quicksettings.Tile
import android.service.quicksettings.TileService

/** Quick settings tile: tap = save a clip using the configured rollback length. */
class EchoTileService : TileService() {
    override fun onClick() {
        super.onClick()
        val svc = ShizukuBridge.service()
        val prefs = getSharedPreferences("echo", MODE_PRIVATE)
        val rollback = prefs.getInt("saveRollbackSeconds", 30)
        if (svc != null && svc.isRunning) svc.saveClip(rollback)
        update()
    }
    override fun onStartListening() { super.onStartListening(); update() }
    private fun update() {
        val t = qsTile ?: return
        val svc = ShizukuBridge.service()
        val running = svc != null && try { svc.isRunning } catch (e: Exception) { false }
        t.state = if (running) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
        t.updateTile()
    }
}
""".replace("%s", PKG))

# ---------------- boot receiver ----------------
w("app/src/main/java/%s/BootReceiver.kt" % PKD, """package %s

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val prefs = ctx.getSharedPreferences("echo", MODE_PRIVATE)
        if (!prefs.getBoolean("autoStart", true)) return
        ctx.startForegroundService(Intent(ctx, EchoForegroundService::class.java))
        // Shizuku may not be ready this early; EchoForegroundService / MainActivity
        // retry binding until Shizuku is up.
    }
}
""".replace("%s", PKG))

# ---------------- preferences ----------------
w("app/src/main/java/%s/Prefs.kt" % PKD, """package %s

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

val Context.dataStore by preferencesDataStore(name = "echo_settings")

/** DataStore-backed settings, mirrored to SharedPreferences on write so the
 *  QS tile (no coroutine scope) can read the rollback length. */
data class Settings(
    val mode: CacheMode = CacheMode.TIME,
    val cacheMinutes: Int = 30,
    val cacheMegabytes: Int = 64,
    val saveRollbackSeconds: Int = 30,
    val amoled: Boolean = false,
    val autoStart: Boolean = true
)

class Prefs(private val ctx: Context) {
    private val ds = ctx.dataStore

    val settings: Flow<Settings> = ds.data.map { p ->
        Settings(
            mode = if (p[KEY_MODE] == "bytes") CacheMode.BYTES else CacheMode.TIME,
            cacheMinutes = p[KEY_MINUTES] ?: 30,
            cacheMegabytes = p[KEY_MB] ?: 64,
            saveRollbackSeconds = p[KEY_ROLLBACK] ?: 30,
            amoled = p[KEY_AMOLED] ?: false,
            autoStart = p[KEY_AUTOSTART] ?: true
        )
    }

    suspend fun save(s: Settings) {
        ds.edit { e ->
            e[KEY_MODE] = if (s.mode == CacheMode.BYTES) "bytes" else "time"
            e[KEY_MINUTES] = s.cacheMinutes
            e[KEY_MB] = s.cacheMegabytes
            e[KEY_ROLLBACK] = s.saveRollbackSeconds
            e[KEY_AMOLED] = s.amoled
            e[KEY_AUTOSTART] = s.autoStart
        }
        ctx.getSharedPreferences("echo", Context.MODE_PRIVATE).edit()
            .putInt("saveRollbackSeconds", s.saveRollbackSeconds)
            .putBoolean("autoStart", s.autoStart).apply()
    }

    companion object {
        private val KEY_MODE = stringPreferencesKey("mode")
        private val KEY_MINUTES = intPreferencesKey("minutes")
        private val KEY_MB = intPreferencesKey("mb")
        private val KEY_ROLLBACK = intPreferencesKey("rollback")
        private val KEY_AMOLED = booleanPreferencesKey("amoled")
        private val KEY_AUTOSTART = booleanPreferencesKey("autostart")
    }
}
""".replace("%s", PKG))

print("part 1 done")

# ---------------- theme ----------------
w("app/src/main/java/%s/ui/Theme.kt" % PKD, """package %s.ui

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

/** Material You dynamic color; AMOLED black forces a pure-black background. */
@Composable
fun GoodEchoTheme(amoled: Boolean, content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val ctx = LocalContext.current
    val scheme: ColorScheme = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        val dyn = if (dark) dynamicDarkColorScheme(ctx) else dynamicLightColorScheme(ctx)
        if (amoled && dark) dyn.copy(
            background = Color.Black,
            onBackground = Color(0xFFE6E1E5),
            surface = Color.Black,
            surfaceContainerLowest = Color.Black,
            surfaceContainerLow = Color(0xFF0A0A0A),
            surfaceContainer = Color(0xFF0E0E0E),
            surfaceContainerHigh = Color(0xFF131313),
            surfaceContainerHighest = Color(0xFF1A1A1A)
        ) else dyn
    } else if (dark) darkColorScheme() else lightColorScheme()
    MaterialTheme(colorScheme = scheme, content = content)
}
""".replace("%s", PKG))

# ---------------- main activity ----------------
w("app/src/main/java/%s/MainActivity.kt" % PKD, """package %s

import android.Manifest
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import com.failurepoint.goodecho.ui.GoodEchoTheme
import kotlinx.coroutines.launch
import rikka.shizuku.Shizuku

class MainActivity : ComponentActivity() {
    private lateinit var prefs: Prefs

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        if (Build.VERSION.SDK_INT >= 33) permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        if (Shizuku.checkSelfPermission() != 0) Shizuku.requestPermission(0)
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(Intent(this, EchoForegroundService::class.java))
        else startService(Intent(this, EchoForegroundService::class.java))

        setContent {
            val s by prefs.settings.collectAsState(initial = Settings())
            GoodEchoTheme(amoled = s.amoled) {
                EchoApp(settings = s, onSave = { s2 -> lifecycleScope.launch { prefs.save(s2) } },
                    onAction = { act ->
                        val svc = ShizukuBridge.service()
                        when (act) {
                            "start" -> if (svc != null) svc.startCapture(if (s.mode == CacheMode.BYTES) 0 else 1,
                                if (s.mode == CacheMode.BYTES) s.cacheMegabytes.toLong() else s.cacheMinutes.toLong())
                            "stop" -> svc?.stopCapture()
                            "save" -> {
                                val ok = svc?.saveClip(s.saveRollbackSeconds) == true
                                Toast.makeText(this, if (ok) "Clip saved" else "Not recording", Toast.LENGTH_SHORT).show()
                            }
                        }
                    })
            }
        }
    }
}
""".replace("%s", PKG))

# ---------------- app screen ----------------
w("app/src/main/java/%s/EchoApp.kt" % PKD, """package %s

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.util.concurrent.TimeUnit
import kotlin.math.abs

/** Single-screen MD3 UI. Cache settings are linked sliders: both are views of
 *  the same RAM budget (30%% of heap); changing one updates the other. */
@Composable
fun EchoApp(settings: Settings, onSave: (Settings) -> Unit, onAction: (String) -> Unit) {
    val perMinBytes = 44100L * 2L * 60L
    val maxBytes = CaptureConfig.maxBytes(Runtime.getRuntime().maxMemory())
    val minBytes = CaptureConfig.MIN_MINUTES * perMinBytes
    fun bytesOf(s: Settings): Long = when (s.mode) {
        CacheMode.BYTES -> s.cacheMegabytes * 1024L * 1024L
        CacheMode.TIME -> s.cacheMinutes * perMinBytes
    }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("GoodEcho", style = MaterialTheme.typography.headlineMedium)

        // status + controls
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = { onAction("start") }) { Text("Start buffer") }
            OutlinedButton(onClick = { onAction("stop") }) { Text("Stop") }
            FilledTonalButton(onClick = { onAction("save") }) { Text("Save clip") }
        }

        HorizontalDivider()

        // cache mode
        Text("Cache limit", style = MaterialTheme.typography.titleMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = settings.mode == CacheMode.BYTES,
                onClick = { onSave(settings.copy(mode = CacheMode.BYTES)) },
                label = { Text("RAM size") })
            FilterChip(
                selected = settings.mode == CacheMode.TIME,
                onClick = { onSave(settings.copy(mode = CacheMode.TIME)) },
                label = { Text("Recording time") })
        }

        // linked slider 1: minutes (always visible, linked)
        val currentBytes = bytesOf(settings).coerceIn(minBytes, maxBytes)
        val minutesFromBytes = (currentBytes / perMinBytes).toInt().coerceAtLeast(CaptureConfig.MIN_MINUTES)
        val maxMinutes = (maxBytes / perMinBytes).toInt().coerceAtLeast(CaptureConfig.MIN_MINUTES)
        Text("Keep about %%d minutes of audio".format(minutesFromBytes), style = MaterialTheme.typography.bodyMedium)
        Slider(
            value = minutesFromBytes.toFloat(),
            onValueChange = { v ->
                val m = v.toInt().coerceIn(CaptureConfig.MIN_MINUTES, maxMinutes)
                onSave(settings.copy(mode = CacheMode.TIME, cacheMinutes = m, cacheMegabytes =
                    (m * perMinBytes / (1024L * 1024L)).toInt().coerceAtLeast(32)))
            },
            valueRange = CaptureConfig.MIN_MINUTES.toFloat()..maxMinutes.toFloat())

        // linked slider 2: MB
        val mbFromBytes = (currentBytes / (1024L * 1024L)).toInt().coerceAtLeast(32)
        val maxMB = (maxBytes / (1024L * 1024L)).toInt().coerceAtLeast(32)
        Text("Keep about %%d MB of RAM".format(mbFromBytes), style = MaterialTheme.typography.bodyMedium)
        Slider(
            value = mbFromBytes.toFloat(),
            onValueChange = { v ->
                val mb = v.toInt().coerceIn(32, maxMB)
                onSave(settings.copy(mode = CacheMode.BYTES, cacheMegabytes = mb, cacheMinutes =
                    (mb * 1024L * 1024L / perMinBytes).toInt().coerceAtLeast(CaptureConfig.MIN_MINUTES)))
            },
            valueRange = 32f..maxMB.toFloat())

        HorizontalDivider()

        // rollback
        Text("Rollback length on save", style = MaterialTheme.typography.titleMedium)
        Text("%d seconds".format(settings.saveRollbackSeconds), style = MaterialTheme.typography.bodyMedium)
        Slider(
            value = settings.saveRollbackSeconds.toFloat(),
            onValueChange = { v -> onSave(settings.copy(saveRollbackSeconds = v.toInt())) },
            valueRange = 5f..300f)

        HorizontalDivider()

        // amoled
        ListItem(headlineContent = { Text("AMOLED black") },
            supportingContent = { Text("Pure black backgrounds in dark mode") },
            trailingContent = {
                Switch(checked = settings.amoled, onCheckedChange = { onSave(settings.copy(amoled = it)) })
            })

        ListItem(headlineContent = { Text("Start with Shizuku on boot") },
            supportingContent = { Text("Starts the RAM buffer when the device boots") },
            trailingContent = {
                Switch(checked = settings.autoStart, onCheckedChange = { onSave(settings.copy(autoStart = it)) })
            })

        Text(
            "Audio lives only in RAM. A clip is written to storage only when you tap " +
                "Save clip (or the Quick Settings tile).",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
""".replace("%s", PKG).replace("%%", "%"))

# ---------------- resources ----------------
w("app/src/main/res/values/themes.xml", """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.GoodEcho" parent="android:Theme.Material.Light.NoActionBar"/>
</resources>
""")

w("app/src/main/res/drawable/ic_launcher.xml", """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="48dp" android:height="48dp"
    android:viewportWidth="24" android:viewportHeight="24">
    <path android:fillColor="#FF6750A4"
        android:pathData="M12,14c1.66,0 3,-1.34 3,-3V5c0,-1.66 -1.34,-3 -3,-3S9,3.34 9,5v6C9,12.66 10.34,14 12,14zM17,11c0,2.76 -2.24,5 -5,5s-5,-2.24 -5,-5H5c0,3.53 2.61,6.43 6,6.92V21h2v-3.08c3.39,-0.49 6,-3.39 6,-6.92H17z"/>
</vector>
""")

# ---------------- CI: heavy lifting on GitHub ----------------
w(".github/workflows/build.yml", """name: build
on:
  push:
    branches: [main]
  workflow_dispatch:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with: { distribution: temurin, java-version: "17" }
      - uses: gradle/actions/setup-gradle@v4
      - name: Generate project from templates
        run: python3 tools/generate.py
      - name: Build
        run: gradle :app:assembleDebug --no-daemon --stacktrace
      - uses: actions/upload-artifact@v4
        with:
          name: GoodEcho-debug-apk
          path: app/build/outputs/apk/debug/*.apk
""")

# ---------------- README ----------------
w("README.md", """# GoodEcho

Rollback audio buffer that never leaves RAM unless you save a clip. Runs its
capture in a Shizuku shell-uid service so it does not conflict with other
apps' audio detection.

- Jetpack Compose + Material 3, dynamic color (Material You), AMOLED black option
- Cache limit: linked sliders (minutes <-> RAM MB), min 30 min, max 30%% of heap
- Quick Settings tile to save a clip with configurable rollback length
- Auto-start on boot with Shizuku

## Workflow
Edit `tools/generate.py` (the whole project is generated from it), run
`python3 tools/generate.py`, commit. CI builds the APK on every push and
uploads it as an artifact. Never hand-edit generated files.

Generated. Do not edit emitted sources by hand.
""".replace("%%", "%"))

print("all done")
