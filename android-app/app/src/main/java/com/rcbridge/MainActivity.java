package com.rcbridge;

import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {

    private Button serviceBtn;
    private boolean isServiceRunning = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        TextView title = findViewById(R.id.statusText);
        title.setText("点击下方按钮启动 RC Bridge");

        serviceBtn = findViewById(R.id.serviceBtn);
        serviceBtn.setText("启动广播服务");

        // 隐藏连接按钮（服务会自动连接 RCSDK）
        Button connectBtn = findViewById(R.id.connectBtn);
        connectBtn.setVisibility(android.view.View.GONE);

        serviceBtn.setOnClickListener(v -> {
            if (isServiceRunning) {
                stopService(new Intent(this, RCBroadcastService.class));
                serviceBtn.setText("启动广播服务");
                isServiceRunning = false;
                Toast.makeText(this, "已停止", Toast.LENGTH_SHORT).show();
            } else {
                startForegroundService(new Intent(this, RCBroadcastService.class));
                serviceBtn.setText("停止广播服务");
                isServiceRunning = true;
                Toast.makeText(this, "RC Bridge 已启动", Toast.LENGTH_SHORT).show();
            }
        });
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
    }
}
