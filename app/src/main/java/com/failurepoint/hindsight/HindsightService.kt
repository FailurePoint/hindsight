package com.failurepoint.hindsight

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
class HindsightService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onStartCommand(i: Intent?, f: Int, id: Int): Int {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel("echo", "Hindsight", NotificationManager.IMPORTANCE_LOW))
        val n = Notification.Builder(this, "echo")
            .setContentTitle("Hindsight buffer active")
            .setContentText("Recording stays in RAM until you save a clip.")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now).build()
        // FOREGROUND_SERVICE_TYPE_DATA_SYNC (0x1). Do NOT include MICROPHONE here:
        // that type requires RECORD_AUDIO to be runtime-granted in THIS process at
        // startForeground() time, but capture runs in the shell-uid Shizuku process,
        // so this process never holds RECORD_AUDIO -> SecurityException crash on
        // Android 14+. And check hex constants: 0x01000000 is SYSTEM_EXEMPTED.
        val fgsType = 0x1
        if (Build.VERSION.SDK_INT >= 30) startForeground(1, n, fgsType)
        else startForeground(1, n)
        return START_STICKY
    }
}
