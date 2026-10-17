package com.failurepoint.goodecho

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
