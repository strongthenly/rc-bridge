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

/**
 * H12 Pro 通道是 GET 方式，需要轮询
 */
public class RCBroadcastService extends Service {

    private static final String TAG = "RCBridge";
    private static final int UDP_PORT = 10001;
    private static final String BROADCAST_IP = "255.255.255.255";
    private static final long POLL_INTERVAL_MS = 50L; // 20Hz
    private static final String CHANNEL_ID = "rc_bridge_channel";
    private static final int NOTIF_ID = 1001;

    private boolean isRunning = false;
    private DatagramSocket sendSocket = null;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private int[] latestChannels = new int[12]; // H12 Pro 只有 12 通道
    private boolean hasData = false;
    private final Object channelLock = new Object();

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
                            hasData = true;
                        }
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
                // 等拿到第一次通道数据再开始广播
                while (isRunning) {
                    synchronized (channelLock) { if (hasData) break; }
                    try { Thread.sleep(10); } catch (InterruptedException e) { return; }
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
                        Thread.sleep(20); // 50Hz 广播
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
