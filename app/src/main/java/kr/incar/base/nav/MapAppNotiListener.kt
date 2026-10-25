package kr.incar.base.nav

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import kr.incar.base.App

/**
 * 길안내 앱(네이버 지도 · 카카오맵 · 티맵) 알림 읽기 — 목적지·남은 거리·남은 시간을 Pixel TMI 깃발로 가져온다.
 * 탭 설정 > 알림 > 기기 및 앱 알림 > 알림 접근에서 'Pixel TMI'를 허용해야 동작한다.
 * 이 세 앱의 알림만 보고, 다른 앱 알림은 열어보지 않는다.
 */
class MapAppNotiListener : NotificationListenerService() {

    private val on: Boolean get() = (application as App).isOn()

    /** 꺼 둔 상태에서 시스템이 다시 붙이면 바로 떼어 달라고 한다 (앱이 혼자 되살아나지 않게) */
    override fun onListenerConnected() {
        super.onListenerConnected()
        if (!on) { runCatching { requestUnbind() }; return }
        runCatching { activeNotifications?.forEach { onNotificationPosted(it) } }   // 이미 안내 중이던 것도
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (!on) return
        val from = MapApp.of(sbn.packageName) ?: return
        val n = sbn.notification
        if (!sbn.isOngoing && n.category != Notification.CATEGORY_NAVIGATION) return   // 광고·출발 알림은 무시
        val e = n.extras
        fun s(k: String) = e.getCharSequence(k)?.toString()
        val lines = e.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)?.joinToString(" ")
        (application as App).graph.maps.onNotification(
            from,
            s(Notification.EXTRA_TITLE) ?: s(Notification.EXTRA_TITLE_BIG),
            s(Notification.EXTRA_TEXT),
            listOfNotNull(s(Notification.EXTRA_BIG_TEXT), lines).joinToString(" ").ifBlank { null },
            listOfNotNull(s(Notification.EXTRA_SUB_TEXT), s(Notification.EXTRA_INFO_TEXT), s(Notification.EXTRA_SUMMARY_TEXT)).joinToString(" ").ifBlank { null },
        )
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {
        if (!on) return
        val from = MapApp.of(sbn.packageName) ?: return
        if (sbn.isOngoing) (application as App).graph.maps.onNotificationGone(from)
    }
}
