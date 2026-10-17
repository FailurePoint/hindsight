package com.failurepoint.hindsight

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
import com.failurepoint.hindsight.ui.HindsightTheme
import kotlinx.coroutines.launch
import rikka.shizuku.Shizuku

class MainActivity : ComponentActivity() {
    private lateinit var prefs: Prefs

    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { }

    // Shizuku's binder is NOT available on the first frames after process start
    // (the provider connects asynchronously). Calling checkSelfPermission() before
    // the binder arrives throws "binder haven't been received" and crashes the app
    // on cold start (observed on GrapheneOS). So: ping first, otherwise wait for the
    // sticky binder-received listener, and retry if the binder dies and reconnects.
    private fun requestShizukuIfReady() {
        runOnUiThread {
            try {
                if (Shizuku.pingBinder() && Shizuku.checkSelfPermission() != 0) {
                    Shizuku.requestPermission(0)
                }
            } catch (_: IllegalStateException) {
                // binder dropped between ping and call; the sticky listener will fire
            }
        }
    }

    private val binderReceivedListener = Shizuku.OnBinderReceivedListener {
        requestShizukuIfReady()
    }
    private val binderDeadListener = Shizuku.OnBinderDeadListener {
        // binder died (Shizuku restarted); the sticky re-receive will re-request
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        if (Build.VERSION.SDK_INT >= 33) permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(Intent(this, HindsightService::class.java))
        else startService(Intent(this, HindsightService::class.java))
        requestShizukuIfReady()
        Shizuku.addBinderReceivedListenerSticky(binderReceivedListener)
        Shizuku.addBinderDeadListener(binderDeadListener)

        setContent {
            val s by prefs.settings.collectAsState(initial = Settings())
            HindsightTheme(amoled = s.amoled) {
                HindsightApp(settings = s, onSave = { s2 -> lifecycleScope.launch { prefs.save(s2) } },
                    onAction = { act ->
                        val svc = if (Shizuku.pingBinder()) ShizukuBridge.service(applicationContext) else null
                        when (act) {
                            "start" -> if (svc != null) svc.startCapture(if (s.mode == CacheMode.BYTES) 0 else 1,
                                if (s.mode == CacheMode.BYTES) s.cacheMegabytes.toLong() else s.cacheMinutes.toLong())
                                else Toast.makeText(this, "Shizuku not connected", Toast.LENGTH_SHORT).show()
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
    override fun onDestroy() {
        Shizuku.removeBinderReceivedListener(binderReceivedListener)
        Shizuku.removeBinderDeadListener(binderDeadListener)
        super.onDestroy()
    }
}
