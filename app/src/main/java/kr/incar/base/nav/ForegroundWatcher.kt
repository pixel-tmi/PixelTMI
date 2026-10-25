package kr.incar.base.nav

import android.app.AppOpsManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.os.Process

/**
 * 지금 탭 맨 앞에 떠 있는 앱 알아내기 (사용 정보 접근 허용 필요).
 * 길안내 앱(네이버 지도·카카오맵·티맵)이 앞에 있을 때만 고양이를 지도 위로 따라 띄우고,
 * 홈 화면·다른 앱에선 숨기려고 쓴다.
 * 허용: 탭 설정 > 애플리케이션 > 특별한 접근 > 사용 정보 접근 > Pixel TMI (adb: appops set kr.incar.base GET_USAGE_STATS allow)
 */
class ForegroundWatcher(private val context: Context) {

    private var lastPkg: String? = null
    private var lastQuery = 0L

    fun granted(): Boolean {
        val ops = context.getSystemService(AppOpsManager::class.java) ?: return false
        return runCatching {
            ops.unsafeCheckOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), context.packageName) == AppOpsManager.MODE_ALLOWED
        }.getOrDefault(false)
    }

    /** 맨 앞 앱 패키지 (모르면 null) */
    fun current(): String? {
        val usm = context.getSystemService(UsageStatsManager::class.java) ?: return null
        val now = System.currentTimeMillis()
        val from = if (lastQuery == 0L) now - 10 * 60_000 else lastQuery - 2000
        runCatching {
            val events = usm.queryEvents(from, now)
            val e = UsageEvents.Event()
            while (events.hasNextEvent()) {
                events.getNextEvent(e)
                if (e.eventType == UsageEvents.Event.ACTIVITY_RESUMED) lastPkg = e.packageName
            }
        }
        lastQuery = now
        return lastPkg
    }
}
