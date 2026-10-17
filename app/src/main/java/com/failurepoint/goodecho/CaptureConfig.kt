package com.failurepoint.goodecho

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
