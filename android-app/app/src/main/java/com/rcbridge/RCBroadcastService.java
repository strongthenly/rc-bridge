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
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * H12 Pro 通道是 GET 方式，需要轮询
 * 数据驱动广播：每次 poll 拿到新数据立即发送，不另开定时线程
 * 延迟 = poll 间隔（50ms），无额外 broadcast sleep
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
    private int[] latestChannels = new int[12];
    private final Object channelLock = new Object();
    private final CountDownLatch dataReady = new CountDownLatch(1);
    private final ExecutorService udpSender = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "udp-sender");
        t.setDaemon(true);
        return t;
    });

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
        KeyManager.INSTANCE.get(RemoteControllerKey.INSTANCE.getKeyChannels(),
            new CompletionCallbackWith<int[]>() {
                @Override
                public void onSuccess(int[] values) {
                    if (values != null) {
                        synchronized (channelLock) {
                            latestChannels = values;
                        }
                        // 首次数据到达后标记就绪
                        dataReady.countDown();
                        // 数据驱动：拿到新数据立即发送，不另开定时广播线程
                        udpSender.submit(RCBroadcastService.this::sendCurrentChannels);
                    }
                }

                @Override
                public void onFailure(SkyException e) {
                    // 偶尔失败是正常的
                }
            });
    }

    /**
     * 读取 latestChannels 构造 JSON 并 UDP 广播
     * 在 udpSender 线程池中执行，不阻塞回调线程
     */
    private void sendCurrentChannels() {
        if (sendSocket == null || sendSocket.isClosed()) return;
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
            sendSocket.send(packet);
        } catch (Exception e) {
            if (isRunning) Log.e(TAG, "UDP send error", e);
        }
    }

    private void startUDPBroadcast() {
        try {
            sendSocket = new DatagramSocket();
            sendSocket.setBroadcast(true);
            Log.d(TAG, "UDP broadcast ready");

            NotificationManager nm = getSystemService(NotificationManager.class);
            if (nm != null) nm.notify(NOTIF_ID, buildNotification("广播中 - " + UDP_PORT));
        } catch (Exception e) {
            Log.e(TAG, "Failed UDP init", e);
            stopSelf();
        }
    }

    private void stopAll() {
        isRunning = false;
        handler.removeCallbacks(pollRunnable);
        udpSender.shutdownNow();
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
