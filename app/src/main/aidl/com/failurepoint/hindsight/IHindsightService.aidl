package com.failurepoint.hindsight;
interface IHindsightService {
    boolean startCapture(int modeBytesOrTime, long cacheValue);
    void stopCapture();
    boolean saveClip(int seconds);
    boolean isRunning();
    int getBufferSeconds();
}
