package com.failurepoint.goodecho

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
