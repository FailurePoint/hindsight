package com.failurepoint.hindsight

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
 *  the same RAM budget (30% of heap); changing one updates the other. */
@Composable
fun HindsightApp(settings: Settings, onSave: (Settings) -> Unit, onAction: (String) -> Unit) {
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
        Text("Hindsight", style = MaterialTheme.typography.headlineMedium)

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
        Text("Keep about %d minutes of audio".format(minutesFromBytes), style = MaterialTheme.typography.bodyMedium)
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
        Text("Keep about %d MB of RAM".format(mbFromBytes), style = MaterialTheme.typography.bodyMedium)
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
