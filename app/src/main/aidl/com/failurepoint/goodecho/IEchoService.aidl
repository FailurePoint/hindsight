package com.failurepoint.goodecho;
interface IEchoService {
    boolean startCapture(int modeBytesOrTime, long cacheValue);
    void stopCapture();
    boolean saveClip(int seconds);
    boolean isRunning();
    int getBufferSeconds();
}
