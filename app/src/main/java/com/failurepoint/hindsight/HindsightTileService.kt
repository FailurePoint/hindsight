package com.failurepoint.hindsight

import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import android.content.Context

/** Quick settings tile: tap = save a clip using the configured rollback length. */
class HindsightTileService : TileService() {
    override fun onClick() {
        super.onClick()
        val svc = ShizukuBridge.service(baseContext)
        val rollback = getSharedPreferences("hindsight", Context.MODE_PRIVATE).getInt("saveRollbackSeconds", 30)
        if (svc != null && svc.isRunning) svc.saveClip(rollback)
        update()
    }
    override fun onStartListening() { super.onStartListening(); update() }
    private fun update() {
        val t = qsTile ?: return
        val svc = ShizukuBridge.service(baseContext)
        val running = svc != null && try { svc.isRunning } catch (e: Exception) { false }
        t.state = if (running) Tile.STATE_ACTIVE else Tile.STATE_INACTIVE
        t.updateTile()
    }
}
