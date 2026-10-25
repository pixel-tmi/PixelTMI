package kr.incar.base.pet

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import android.util.Log
import kr.incar.base.App
import kr.incar.base.R

/**
 * 펫 상주 서비스 — 앱 화면을 닫으면 안드로이드가 프로세스를 "쉬는 앱"으로 보고 얼리거나 끈다.
 * 알림 하나를 띄워 두는 포그라운드 서비스로 살아 있게 해서, 고양이와 TMI 엔진이 계속 돈다.
 */
class PetService : Service() {

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_QUIT) {
            (application as App).graph.quit()
            stopSelf()
            return START_NOT_STICKY
        }
        val nm = getSystemService(NotificationManager::class.java)
        val g = (application as App).graph
        val off = android.app.PendingIntent.getService(this, 1, Intent(this, PetService::class.java).setAction(ACTION_QUIT),
            android.app.PendingIntent.FLAG_IMMUTABLE or android.app.PendingIntent.FLAG_UPDATE_CURRENT)
        nm.createNotificationChannel(NotificationChannel(CHANNEL, "Pixel TMI 펫", NotificationManager.IMPORTANCE_MIN))
        val n = Notification.Builder(this, CHANNEL)
            .setSmallIcon(R.drawable.ic_launcher_fg)
            .setContentTitle("Pixel TMI")
            .setContentText(if (g.mapMode) "지도 위 펫 · 길안내 앱 앞에서만 보여요" else "앞길 TMI를 살피는 중")
            .setOngoing(true)
            .addAction(Notification.Action.Builder(null, "끄기 (완전히)", off).build())
            .build()
        val mic = checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) == android.content.pm.PackageManager.PERMISSION_GRANTED
        val ok = (mic && runCatching { startForeground(ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE) }.isSuccess) ||
            runCatching { startForeground(ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE) }.onFailure { Log.w(TAG, "상주 시작 실패", it) }.isSuccess
        if (!ok) { stopSelf(); return START_NOT_STICKY }
        return START_NOT_STICKY   // 꺼지면 다시 살아나지 않게 (완전히 끄기)
    }

    /** 탭: 최근 앱에서 Pleos 전용 앱을 밀어 닫으면 소리까지 전부 같이 꺼진다 */
    override fun onTaskRemoved(rootIntent: Intent?) {
        super.onTaskRemoved(rootIntent)
        val g = (application as App).graph
        if (g.tablet) g.quit(closeStage = false)
    }

    companion object {
        private const val TAG = "PetService"
        private const val CHANNEL = "Pixel TMI_pet"
        private const val ID = 7
        const val ACTION_QUIT = "kr.incar.base.QUIT"

        fun start(c: Context) {
            runCatching { c.startForegroundService(Intent(c, PetService::class.java)) }
                .onFailure { Log.w(TAG, "상주 서비스 요청 실패", it) }
        }
    }
}
