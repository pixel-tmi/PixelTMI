package kr.incar.base

import android.app.Application
import android.content.ComponentName
import android.os.Handler
import android.os.Looper
import android.service.notification.NotificationListenerService
import kr.incar.base.car.CarSpeedSource
import kr.incar.base.nav.MapAppNotiListener

/**
 * 앱이 켜지면 몸통(AppGraph)을 한 번 만든다 → 펫이 화면과 상관없이 돈다.
 * onCreate 안에서 바로 만들면 느린 차량 PC에서 "시작 실패(ANR)"로 꺼지므로, 시작이 끝난 다음 차례에 만든다.
 * 갤럭시 탭은 '켜짐'일 때만 만든다 — 꺼 둔 뒤 안드로이드가 알림 읽기 때문에 앱을 다시 깨워도 아무것도 돌지 않게.
 */
class App : Application() {
    val graph: AppGraph by lazy { AppGraph(this) }

    private val onPrefs by lazy { getSharedPreferences("Pixel TMI_on", MODE_PRIVATE) }

    /** 사용자가 아이콘으로 켰나 (■ 종료·끄기로 false) */
    fun isOn(): Boolean = CarSpeedSource.available || onPrefs.getBoolean("on", false)

    fun setOn(on: Boolean) {
        onPrefs.edit().putBoolean("on", on).commit()
        if (on) runCatching { NotificationListenerService.requestRebind(ComponentName(this, MapAppNotiListener::class.java)) }
    }

    override fun onCreate() {
        super.onCreate()
        if (isOn()) Handler(Looper.getMainLooper()).post { graph }
    }
}
