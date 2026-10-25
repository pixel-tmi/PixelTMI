package kr.incar.base.nav

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Geocoder
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.net.Uri
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kr.incar.base.tmi.NaviState
import java.util.Locale
import kotlin.math.roundToInt

/** 휴대폰·탭 길안내 앱 (Pleos 차량에선 차량 기본 내비 = 현대·기아 내비가 늘 먼저) */
enum class MapApp(val label: String, val pkg: String, val color: Int, val badge: String, val badgeInk: Int) {
    NAVER("네이버 지도", "com.nhn.android.nmap", 0xFF03C75A.toInt(), "N", 0xFFFFFFFF.toInt()),
    KAKAO("카카오맵", "net.daum.android.map", 0xFFFEE500.toInt(), "K", 0xFF191919.toInt()),
    TMAP("티맵", "com.skt.tmap.ku", 0xFFEF3E5C.toInt(), "T", 0xFFFFFFFF.toInt());

    fun routeUrl(name: String, lat: Double, lng: Double, me: String): String {
        val n = Uri.encode(name)
        return when (this) {
            NAVER -> "nmap://navigation?dlat=$lat&dlng=$lng&dname=$n&appname=$me"
            KAKAO -> "kakaomap://route?ep=$lat,$lng&by=car"
            TMAP -> "tmap://route?referrer=com.skt.Tmap&goalname=$n&goalx=$lng&goaly=$lat&rGoName=$n&rGoX=$lng&rGoY=$lat"
        }
    }

    fun searchUrl(q: String, me: String): String = when (this) {
        NAVER -> "nmap://search?query=${Uri.encode(q)}&appname=$me"
        KAKAO -> "kakaomap://search?q=${Uri.encode(q)}"
        TMAP -> "tmap://search?name=${Uri.encode(q)}"
    }

    fun mapUrl(me: String): String = when (this) {
        NAVER -> "nmap://map?appname=$me"
        KAKAO -> "kakaomap://open"
        TMAP -> "tmap://"
    }

    companion object {
        /** 카카오맵에서 '카카오내비로 안내'를 고르면 알림이 카카오내비에서 온다 */
        fun of(pkg: String?): MapApp? = if (pkg == "com.locnall.KimGiSa") KAKAO else entries.firstOrNull { it.pkg == pkg }
    }
}

/**
 * 탭 길안내 = 네이버 지도 · 카카오맵 · 티맵 (고른 앱).
 * 1) 앱에서 목적지를 정하면(글자·말) 위치를 찾아(Geocoder) 고른 길안내 앱을 바로 켠다.
 *    목적지까지 남은 거리는 GPS로 계산해 깃발·남은 거리·가는 길 TMI를 돌린다.
 * 2) 길안내 앱의 알림을 읽을 수 있으면(알림 접근 허용) 거기 적힌 남은 거리·시간을 우선 쓴다.
 *    그 앱에서 직접 길안내를 켜도 목적지가 따라온다.
 */
class MapAppNaviSource(private val context: Context, private val scope: CoroutineScope) {

    data class Dest(val name: String, val lat: Double, val lng: Double, val address: String = "")

    private val _state = MutableStateFlow(NaviState())
    val state: StateFlow<NaviState> = _state.asStateFlow()

    /** 도착했을 때 (주차 처리·세레모니) */
    var onArrived: (() -> Unit)? = null
    /** 화면에서 D를 눌러 모의 주행 중인가 — 그동안은 남은 거리를 GPS로 다시 재지 않는다 */
    var simulating: () -> Boolean = { false }

    private val prefs = context.getSharedPreferences("Pixel TMI_navi", Context.MODE_PRIVATE)
    private var dest: Dest? = null
    private var gps: LocationListener? = null
    private var fix: Location? = null
    private var notiRemainM: Int? = null
    private var notiRemainSec: Int? = null
    private var notiName: String? = null
    private var notiAt = 0L
    private var arrived = false
    /** 사용자가 '길안내 끝내기'를 누른 앱 — 그 앱이 계속 안내해도 다시 깃발을 세우지 않는다 */
    private var ignoreApp: MapApp? = null
    /** '안내 종료'를 누른 뒤 이 시각까지는 어떤 지도 앱 알림도 깃발로 세우지 않는다 */
    private var ignoreUntil = 0L
    private var notiSeen = false
    private var routeSeq = 0

    /** 길안내에 쓸 앱 (기본: 설치된 것 중 네이버 지도 → 카카오맵 → 티맵) */
    var app: MapApp = MapApp.entries.firstOrNull { it.name == prefs.getString("map_app", null) }
        ?: MapApp.entries.firstOrNull { installed(it) } ?: MapApp.NAVER
        set(v) { field = v; prefs.edit().putString("map_app", v.name).apply() }

    /** 지금 길안내 중인 앱 (알림으로 따라온 경우 그 앱) */
    var routeApp: MapApp = app
        private set

    fun installed(a: MapApp): Boolean = runCatching { context.packageManager.getPackageInfo(a.pkg, 0) }.isSuccess

    /** 최근 목적지 (설정·입력 화면에서 한 번에 고르기) */
    fun recent(): List<String> = prefs.getString("recent", "")!!.split('\n').filter { it.isNotBlank() }

    val active: Boolean get() = _state.value.hasRoute

    /** 목적지 이름으로 길안내 시작. 결과 한 줄을 돌려준다 (말풍선용) */
    fun navigate(place: String, adjacent: Boolean, done: (String) -> Unit) {
        val name = place.trim()
        if (name.isEmpty()) return
        val a = app
        prefs.edit().putString("recent", (listOf(name) + recent().filter { it != name }).take(6).joinToString("\n")).apply()
        scope.launch {
            val near = lastFix()
            val found = withContext(Dispatchers.IO) { geocode(name, near) }
            if (found == null) {
                // 위치를 못 찾으면 그 앱 검색으로 넘긴다 (거기서 길안내를 누르면 알림으로 따라간다)
                val ok = open(a, a.searchUrl(name, context.packageName), adjacent)
                done(if (ok) "'$name' 위치를 못 찾았어요\n${a.label}에서 골라 길안내를 눌러 주세요" else "${a.label}${kr.incar.base.tmi.josa(a.label, "가", "이")} 이 탭에 없어요")
                return@launch
            }
            dest = found
            routeApp = a
            arrived = false
            routeSeq++
            notiRemainM = null; notiRemainSec = null; notiName = null; notiSeen = false; ignoreApp = null; ignoreUntil = 0L
            startGps()
            update()
            val ok = open(a, a.routeUrl(found.name, found.lat, found.lng, context.packageName), adjacent)
            val where = found.address.takeIf { it.isNotBlank() }?.let { "\n($it)" } ?: ""
            done(if (ok) "${found.name}까지 ${a.label} 길안내 시작$where" else "${a.label}${kr.incar.base.tmi.josa(a.label, "가", "이")} 이 탭에 없어요\n깃발은 내 위치로 따라갈게요")
        }
    }

    /** 모의 주행으로 목적지에 닿음 */
    fun arriveBySim() {
        if (arrived || dest == null) return
        arrived = true
        _state.value = _state.value.copy(remainM = 1)
        onArrived?.invoke()
    }

    /** 길안내 끝내기 (우리 쪽 깃발만 내린다) */
    fun cancel(user: Boolean = true) {
        // 지도 앱에서 안내가 계속 돌아도 깃발이 되살아나지 않게 (새 목적지를 정하면 다시 따라간다)
        if (user) { ignoreApp = routeApp; ignoreUntil = SystemClock.elapsedRealtime() + 30 * 60_000L }
        routeSeq++
        dest = null
        notiRemainM = null; notiRemainSec = null; notiName = null; notiAt = 0L; notiSeen = false; arrived = false
        stopGps()
        _state.value = NaviState(connected = true)
    }

    /** 길안내 앱 다시 앞으로 */
    fun showMap(adjacent: Boolean): Boolean {
        val d = dest
        val a = if (active) routeApp else app
        return open(a, if (d != null) a.routeUrl(d.name, d.lat, d.lng, context.packageName) else a.mapUrl(context.packageName), adjacent)
    }

    private var openedAt = 0L

    /** 방금(5초 안) 우리가 길안내 앱을 앞으로 띄웠나 — Pleos 앱이 가려진 게 지도 때문인지 구분 */
    fun justOpened(): Boolean = SystemClock.elapsedRealtime() - openedAt < 5000

    private fun open(a: MapApp, url: String, adjacent: Boolean): Boolean {
        val i = Intent(Intent.ACTION_VIEW, Uri.parse(url)).addCategory(Intent.CATEGORY_BROWSABLE)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or (if (adjacent) Intent.FLAG_ACTIVITY_LAUNCH_ADJACENT else 0))
            .setPackage(a.pkg)
        return try {
            openedAt = SystemClock.elapsedRealtime()
            context.startActivity(i)
            true
        } catch (e: ActivityNotFoundException) {
            Log.w(TAG, "${a.label} 없음", e)
            false
        } catch (e: Exception) {
            Log.w(TAG, "${a.label} 열기 실패", e)
            false
        }
    }

    /** 이름 → 위치 (차량 내비에 목적지를 넣을 때도 쓴다) */
    fun lookup(name: String): Dest? = geocode(name.trim(), lastFix())

    @Suppress("DEPRECATION")
    private fun geocode(name: String, near: Location?): Dest? = runCatching {
        if (!Geocoder.isPresent()) return null
        val g = Geocoder(context, Locale.KOREA)
        // 내 위치 주변(약 30km) 먼저, 없으면 한국 안 전체 (해외의 같은 이름이 걸리지 않게)
        val list = near?.let { g.getFromLocationName(name, 5, it.latitude - 0.3, it.longitude - 0.4, it.latitude + 0.3, it.longitude + 0.4) }
            ?.takeIf { it.isNotEmpty() }
            ?: g.getFromLocationName(name, 5, 33.0, 124.5, 38.7, 132.0)
            ?.takeIf { it.isNotEmpty() }
            ?: if (name.endsWith("로")) null else g.getFromLocationName(name + "로", 5, 33.0, 124.5, 38.7, 132.0)   // 을지로·세종대로처럼 '로'가 잘린 경우
        val a = list?.minByOrNull { addr ->
            if (near == null) 0f else FloatArray(1).also { Location.distanceBetween(near.latitude, near.longitude, addr.latitude, addr.longitude, it) }[0]
        } ?: return null
        Dest(name, a.latitude, a.longitude, a.getAddressLine(0)?.removePrefix("대한민국 ") ?: "")
    }.onFailure { Log.w(TAG, "위치 찾기 실패", it) }.getOrNull()

    private fun lastFix(): Location? {
        fix?.let { return it }
        if (!granted()) return null
        val lm = context.getSystemService(LocationManager::class.java) ?: return null
        return runCatching {
            listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER, "fused")
                .mapNotNull { p -> runCatching { lm.getLastKnownLocation(p) }.getOrNull() }
                .maxByOrNull { it.time }
        }.getOrNull()
    }

    private fun granted() = context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED

    private fun startGps() {
        if (gps != null || !granted()) return
        val lm = context.getSystemService(LocationManager::class.java) ?: return
        val l = LocationListener { loc ->
            val f = fix
            val worse = loc.provider == LocationManager.NETWORK_PROVIDER && f?.provider == LocationManager.GPS_PROVIDER && loc.time - f.time < 10_000
            if (!worse && (f == null || loc.accuracy <= 60f)) { fix = loc; update() }
        }
        runCatching {
            lm.requestLocationUpdates(LocationManager.GPS_PROVIDER, 2000L, 0f, l, Looper.getMainLooper())
            runCatching { lm.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 4000L, 0f, l, Looper.getMainLooper()) }
            gps = l
        }.onFailure { Log.w(TAG, "GPS 시작 실패", it) }
    }

    private fun stopGps() {
        gps?.let { l -> runCatching { context.getSystemService(LocationManager::class.java)?.removeUpdates(l) } }
        gps = null
    }

    /** 남은 거리 다시 계산: 알림 값이 30초 안이면 그것, 아니면 GPS 직선거리 × 도로 계수 */
    private fun update() {
        if (simulating() && _state.value.hasRoute && !arrived) return
        val fresh = SystemClock.elapsedRealtime() - notiAt < 30_000
        val d = dest
        val name = d?.name ?: notiName.takeIf { fresh }
        if (name == null) {
            if (_state.value.hasRoute) _state.value = NaviState(connected = true)
            return
        }
        val straight = d?.let { dd -> lastFix()?.let { f -> FloatArray(1).also { Location.distanceBetween(f.latitude, f.longitude, dd.lat, dd.lng, it) }[0] } }
        val remain = when {
            fresh && notiRemainM != null -> notiRemainM!!
            straight != null -> (straight * ROAD_FACTOR).roundToInt()
            else -> _state.value.remainM ?: return   // 위치를 모르면 가짜 거리로 깃발을 세우지 않는다
        }
        val sec = if (fresh && notiRemainSec != null) notiRemainSec else (remain / AVG_MPS).roundToInt()
        if (straight != null && straight < ARRIVE_M && !arrived) {
            arrived = true
            onArrived?.invoke()
        }
        // 도착하면 깃발 바로 앞(1m)에 세워 두고, 다음 목적지 때 새로 시작
        _state.value = NaviState(connected = true, destinationName = name, remainM = if (arrived) 1 else remain.coerceAtLeast(1), remainSec = sec)
    }

    /** 길안내 앱 알림 한 개 (MapAppNotiListener가 넘겨준다) */
    fun onNotification(from: MapApp, title: String?, text: String?, big: String?, sub: String?) {
        if (from == ignoreApp || SystemClock.elapsedRealtime() < ignoreUntil) return
        val all = listOfNotNull(title, text, big, sub).joinToString(" · ")
        Log.i(TAG, "${from.label} 알림: $all")
        prefs.edit().putString("last_noti_${from.name}", all).apply()
        val m = parseRemainM(all)
        val s = parseRemainSec(all)
        if (m == null && notiName == null && dest == null) return   // 처음엔 남은 거리가 있어야 길안내로 본다 (출발 알림·광고 무시)
        notiRemainM = m ?: notiRemainM
        notiRemainSec = s ?: notiRemainSec
        if (dest == null && notiName == null) notiName = parseName(listOfNotNull(title, text).joinToString(" ")) ?: "${from.label} 목적지"
        notiAt = SystemClock.elapsedRealtime()
        if (from == routeApp) notiSeen = true
        if (dest == null) { routeApp = from; startGps() }
        update()
    }

    /** 길안내 알림이 사라짐 = 안내 끝 */
    /** 길안내 알림이 사라짐 = 지도 앱에서 안내가 끝남 (도착이면 세레모니 뒤 2분 있다 깃발 정리, 취소면 바로) */
    fun onNotificationGone(from: MapApp) {
        if (from == ignoreApp) { ignoreApp = null; return }
        if (from != routeApp || !(notiSeen || (dest == null && notiName != null))) return
        val nearEnd = (_state.value.remainM ?: Int.MAX_VALUE) <= 500
        if (nearEnd && !arrived) { arrived = true; onArrived?.invoke(); update() }
        val seq = routeSeq
        scope.launch {
            kotlinx.coroutines.delay(if (nearEnd) 120_000 else 0)
            if (seq == routeSeq) cancel(user = false)
        }
    }

    companion object {
        private const val TAG = "MapAppNavi"
        /** 직선거리 → 실제 도로 거리 어림 */
        private const val ROAD_FACTOR = 1.3f
        /** 도심 평균 속도 (남은 시간 어림, m/s ≈ 30km/h) */
        private const val AVG_MPS = 8.3f
        /** 목적지 이만큼 안이면 도착 */
        private const val ARRIVE_M = 90f

        private val DIST = Regex("""(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(km|㎞|m)(?![a-zA-Z/])""", RegexOption.IGNORE_CASE)
        /** "300m 앞 우회전"처럼 뒤에 '앞/후'가 붙으면 회전까지 거리 */
        private val TURN_AFTER = Regex("""^\s*(앞|후|전방|지나)""")
        private val REMAIN_KEY = Regex("""(남은\s*거리|잔여\s*거리|목적지까지|도착까지)\s*[:：]?\s*$""")
        /** 도착 시각("오후 3시 25분 도착", "15:25")은 남은 시간이 아니다 */
        private val CLOCK = Regex("""(오전|오후)?\s*\d{1,2}\s*시\s*\d{1,2}\s*분\s*(도착|예정)?|\d{1,2}:\d{2}""")
        private val DUR = Regex("""(?:(\d+)\s*시간)?\s*(?:(\d+)\s*분)?""")

        /** 남은 거리(m): '남은 거리' 표시가 있으면 그것, 없으면 회전·속도 숫자를 뺀 가장 큰 값 */
        fun parseRemainM(t: String): Int? {
            var keyed: Int? = null
            var best: Int? = null
            for (d in DIST.findAll(t)) {
                val after = t.substring(d.range.last + 1)
                if (TURN_AFTER.containsMatchIn(after)) continue
                val v = toM(d.groupValues[1], d.groupValues[2]) ?: continue
                val before = t.substring(maxOf(0, d.range.first - 12), d.range.first)
                if (REMAIN_KEY.containsMatchIn(before) || after.trimStart().startsWith("남")) keyed = v
                if (best == null || v > best) best = v
            }
            return keyed ?: best
        }

        fun parseRemainSec(t: String): Int? = DUR.findAll(CLOCK.replace(t, " ")).mapNotNull { m ->
            val h = m.groupValues[1].toIntOrNull()
            val min = m.groupValues[2].toIntOrNull()
            if (h == null && min == null) null else ((h ?: 0) * 60 + (min ?: 0)) * 60
        }.maxOrNull()

        /** 확실한 꼴만 목적지 이름으로: "목적지: ○○", "○○로 안내 중" (회전 문장의 "오른쪽으로"는 안 잡는다) */
        fun parseName(t: String): String? =
            Regex("""(?:목적지|도착지)\s*[:：]\s*([가-힣A-Za-z][^\s·,]{1,19})""").find(t)?.groupValues?.get(1)
                ?: Regex("""([가-힣A-Za-z][^\s·,]{1,19}?)(?:으로|로)\s*길?\s*안내\s*중""").find(t)?.groupValues?.get(1)

        private fun toM(n: String, unit: String): Int? {
            val v = n.replace(",", "").toDoubleOrNull() ?: return null      // "1,200m" = 1200m
            return if (unit.lowercase() == "m") v.roundToInt() else (v * 1000).roundToInt()
        }
    }
}
