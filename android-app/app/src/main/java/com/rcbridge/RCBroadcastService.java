package com.rcbridge;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;

import com.skydroid.rcsdk.RCSDKManager;
import com.skydroid.rcsdk.SDKManagerCallBack;
import com.skydroid.rcsdk.key.RemoteControllerKey;
import com.skydroid.rcsdk.KeyManager;
import com.skydroid.rcsdk.common.callback.CompletionCallbackWith;
import com.skydroid.rcsdk.common.error.SkyException;

import org.json.JSONObject;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;
import java.util.Arrays;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/**
 * H12 Pro 通道是 GET 方式，需要轮询
 * 轮询和广播统一为 50ms (20Hz)，避免发送重复帧
 */
public class RCBroadcastService extends Service {

    private static final String TAG = "RCBridge";
    private static final int UDP_PORT = 10001;
    private static final String BROADCAST_IP = "255.255.255.255";
    private static final long POLL_INTERVAL_MS = 50L; // 20Hz
    private static final long BROADCAST_INTERVAL_MS = 50L; // 20Hz，与轮询同步
    private static final String CHANNEL_ID = "rc_bridge_channel";
    private static final int NOTIF_ID = 1001;

    private boolean isRunning = false;
    private DatagramSocket sendSocket = null;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private int[] latestChannels = new int[12]; // H12 Pro 只有 12 通道
    private final Object channelLock = new Object();
    private final CountDownLatch dataReady = new CountDownLatch(1);

    private final Runnable pollRunnable = new Runnable() {
        @Override
        public void run() {
            if (!isRunning) return;
            pollChannels();
            handler.postDelayed(this, POLL_INTERVAL_MS);
        }
    };

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "Service created");
        createNotificationChannel();
        startForeground(NOTIF_ID, buildNotification("RC Bridge 正在运行..."));
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (!isRunning) startBridge();
        return START_STICKY;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel c = new NotificationChannel(CHANNEL_ID, "RC Bridge", NotificationManager.IMPORTANCE_LOW);
            c.setDescription("RC Bridge 后台服务");
            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.createNotificationChannel(c);
        }
    }

    private Notification buildNotification(String text) {
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            b = new Notification.Builder(this, CHANNEL_ID);
        else
            b = new Notification.Builder(this);
        return b.setContentTitle("RC Bridge").setContentText(text)
                .setSmallIcon(android.R.drawable.ic_menu_compass).setOngoing(true).build();
    }

    private void startBridge() {
        isRunning = true;
        Log.d(TAG, "Starting RC bridge...");

        RCSDKManager.INSTANCE.initSDK(getApplicationContext(), new SDKManagerCallBack() {
            @Override
            public void onRcConnected() {
                Log.d(TAG, "RCSDK connected! Starting poll...");
                startUDPBroadcast();
                handler.post(pollRunnable);
            }

            @Override
            public void onRcConnectFail(SkyException e) {
                Log.e(TAG, "RCSDK connect fail: " + (e != null ? e.getMessage() : "unknown"));
                stopSelf();
            }

            @Override
            public void onRcDisconnect() {
                Log.d(TAG, "RCSDK disconnected");
                stopAll();
            }
        });

        RCSDKManager.INSTANCE.connectToRC();
    }

    private void pollChannels() {
        // H12 Pro 是 GET 方式，每次主动请求通道值
        KeyManager.INSTANCE.get(RemoteControllerKey.INSTANCE.getKeyChannels(),
            new CompletionCallbackWith<int[]>() {
                @Override
                public void onSuccess(int[] values) {
                    if (values != null) {
                        synchronized (channelLock) {
                            latestChannels = values;
                        }
                        dataReady.countDown(); // 首次数据到达后唤醒广播线程
                    }
                }

                @Override
                public void onFailure(SkyException e) {
                    // 偶尔失败是正常的
                }
            });
    }

    private void startUDPBroadcast() {
        try {
            sendSocket = new DatagramSocket();
            sendSocket.setBroadcast(true);

            final DatagramSocket sock = sendSocket;
            Thread broadcastThread = new Thread(() -> {
                // 用 CountDownLatch 替代 busy-wait，等待首次通道数据
                try {
                    if (!dataReady.await(5, TimeUnit.SECONDS)) {
                        Log.w(TAG, "Timeout waiting for first channel data");
                        if (isRunning) stopSelf();
                        return;
                    }
                } catch (InterruptedException e) {
                    return;
                }

                while (isRunning && sock != null && !Thread.interrupted()) {
                    try {
                        JSONObject json = new JSONObject();
                        synchronized (channelLock) {
                            int len = Math.min(latestChannels.length, 12);
                            for (int i = 0; i < len; i++) {
                                json.put("ch" + (i + 1), latestChannels[i]);
                            }
                        }
                        json.put("ts", System.currentTimeMillis());

                        byte[] data = json.toString().getBytes("UTF-8");
                        InetAddress addr = InetAddress.getByName(BROADCAST_IP);
                        DatagramPacket packet = new DatagramPacket(data, data.length, addr, UDP_PORT);
                        sock.send(packet);
                        Thread.sleep(BROADCAST_INTERVAL_MS); // 20Hz，与轮询同步
                    } catch (InterruptedException e) {
                        break;
                    } catch (Exception e) {
                        if (isRunning) Log.e(TAG, "UDP error", e);
                    }
                }
            });
            broadcastThread.setDaemon(true);
            broadcastThread.start();
            Log.d(TAG, "UDP broadcast started");

            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.notify(NOTIF_ID, buildNotification("广播中 - " + UDP_PORT));
        } catch (Exception e) {
            Log.e(TAG, "Failed UDP", e);
            stopSelf();
        }
    }

    private void stopAll() {
        isRunning = false;
        handler.removeCallbacks(pollRunnable);
        if (sendSocket != null) {
            sendSocket.close();
            sendSocket = null;
        }
    }

    @Override
    public void onDestroy() {
        stopAll();
        try { RCSDKManager.INSTANCE.disconnectRC(); } catch (Exception ignored) {}
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }
}
