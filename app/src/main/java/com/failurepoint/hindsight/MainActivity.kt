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

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        if (Build.VERSION.SDK_INT >= 33) permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        if (Shizuku.checkSelfPermission() != 0) Shizuku.requestPermission(0)
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(Intent(this, HindsightService::class.java))
        else startService(Intent(this, HindsightService::class.java))

        setContent {
            val s by prefs.settings.collectAsState(initial = Settings())
            HindsightTheme(amoled = s.amoled) {
                HindsightApp(settings = s, onSave = { s2 -> lifecycleScope.launch { prefs.save(s2) } },
                    onAction = { act ->
                        val svc = ShizukuBridge.service(applicationContext)
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
