package com.failurepoint.goodecho

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.IBinder
import rikka.shizuku.Shizuku
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Shizuku user-service bridge. bindUserService delivers the binder through
 *  a ServiceConnection; we latch-wait briefly so synchronous callers work. */
object ShizukuBridge {
    private const val PKG = "com.failurepoint.goodecho"

    @Volatile private var binder: IBinder? = null
    private val latch = CountDownLatch(1)
    private var bound = false

    private fun args() = Shizuku.UserServiceArgs(ComponentName(PKG, ShellUserService::class.java.name))
        .processNameSuffix("shell")
        .debuggable(false)
        .version(1)

    private val conn = object : ServiceConnection {
        override fun onServiceConnected(name: ComponentName, service: IBinder) {
            binder = service; latch.countDown()
        }
        override fun onServiceDisconnected(name: ComponentName) { binder = null; bound = false }
    }

    fun bind(ctx: Context): Boolean = try {
        if (!bound) {
            val intent = Intent().setClassName(ctx, ShellUserService::class.java.name)
            Shizuku.bindUserService(args(), conn)
            bound = true
        }
        true
    } catch (e: Exception) { false }

    fun service(ctx: Context): IEchoService? = try {
        if (binder == null) { bind(ctx); latch.await(750, TimeUnit.MILLISECONDS) }
        binder?.let { IEchoService.Stub.asInterface(it) }
    } catch (e: Exception) { null }
}
