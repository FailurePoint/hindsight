package com.failurepoint.goodecho

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
