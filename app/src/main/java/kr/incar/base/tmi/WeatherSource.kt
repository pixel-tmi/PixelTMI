package kr.incar.base.tmi

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Calendar

/** 지금 이 자리 날씨 (기상청 예보 모델) */
data class Weather(
    val ok: Boolean = false,
    val tempC: Float = 0f,
    /** WMO 날씨 코드 (0 맑음 · 45 안개 · 61 비 · 71 눈 · 80 소나기 · 95 뇌우 …) */
    val code: Int = 0,
    val windMs: Float = 0f,
    /** 오늘 남은 시간 중 비·눈 올 확률이 가장 높은 시각과 확률 */
    val wetHour: Int? = null,
    val wetProb: Int = 0,
    val maxC: Float = 0f,
    val minC: Float = 0f,
) {
    val raining get() = code in 51..67 || code in 80..82 || code >= 95
    val snowing get() = code in 71..77 || code in 85..86
    val foggy get() = code == 45 || code == 48
    val label: String get() = when {
        code >= 95 -> "뇌우"
        snowing -> "눈"
        code in 80..82 -> "소나기"
        raining -> "비"
        foggy -> "안개"
        code == 3 -> "흐림"
        code in 1..2 -> "구름 조금"
        else -> "맑음"
    }

    /** 브리핑 한 줄: "오늘 맑음 12° (최고 18° · 최저 7°) · 오후 3시부터 비 60%" */
    fun line(): String {
        val now = if (tempC.isNaN()) "" else " ${tempC.toInt()}°"
        val range = if (maxC.isNaN() || minC.isNaN()) "" else " (최고 ${maxC.toInt()}° / 최저 ${minC.toInt()}°)"
        val base = "오늘 $label$now$range"
        val wet = wetHour?.takeIf { wetProb >= 40 }?.let { h ->
            val ampm = if (h < 12) "오전" else "오후"
            val hh = if (h % 12 == 0) 12 else h % 12
            " · $ampm ${hh}시쯤 비·눈 ${wetProb}%"
        } ?: ""
        val wind = if (windMs >= 9f) " · 바람 강함 ${windMs.toInt()}m/s" else ""
        return base + wet + wind
    }
}

/**
 * GPS 위치 기준 오늘 날씨 — 기상청(KMA) 예보 모델을 Open-Meteo로 받는다 (키 없이, 5분마다).
 * 운전자 날씨 제보(우박·소나기·폭설·강풍)는 이것과 별도로 TMI 제보로 올라간다.
 * 출처 표시: 날씨 데이터 Open-Meteo.com (CC BY 4.0), 기상청 모델.
 */
class WeatherSource(private val context: Context, private val scope: CoroutineScope) {

    private val _state = MutableStateFlow(Weather())
    val state: StateFlow<Weather> = _state.asStateFlow()

    fun start() {
        scope.launch {
            while (isActive) {
                runCatching { fetch() }.onFailure { Log.w(TAG, "날씨 받기 실패", it) }
                delay(if (_state.value.ok) 5 * 60_000L else 60_000L)            // 5분마다 새로 (실패하면 1분 뒤 다시)
            }
        }
    }

    private suspend fun fetch(model: String? = "kma_seamless") {
        val (lat, lng) = where()
        val url = "https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f".format(lat, lng) +
            "&current=temperature_2m,weather_code,wind_speed_10m" +
            "&hourly=precipitation_probability&daily=temperature_2m_max,temperature_2m_min" +
            (if (model != null) "&models=$model" else "") + "&wind_speed_unit=ms&timezone=Asia%2FSeoul&forecast_days=1"
        val body = withContext(Dispatchers.IO) {
            val c = URL(url).openConnection() as HttpURLConnection
            c.connectTimeout = 8000; c.readTimeout = 8000
            c.setRequestProperty("User-Agent", "PixelTMI-contest-demo")
            try { c.inputStream.bufferedReader().readText() } finally { c.disconnect() }
        }
        val j = JSONObject(body)
        val cur = j.getJSONObject("current")
        val probs = j.optJSONObject("hourly")?.optJSONArray("precipitation_probability")
        val nowH = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
        var bestH: Int? = null; var best = 0
        if (probs != null) for (h in nowH until minOf(24, probs.length())) {
            val p = probs.optInt(h, 0)
            if (p > best) { best = p; bestH = h }
        }
        val daily = j.optJSONObject("daily")
        fun org.json.JSONObject.num(k: String) = if (isNull(k)) Double.NaN else optDouble(k, Double.NaN)
        fun org.json.JSONArray?.first0() = if (this == null || length() == 0 || isNull(0)) Double.NaN else optDouble(0, Double.NaN)
        val t = cur.num("temperature_2m")
        if (t.isNaN() && model != null) return fetch(null)                 // 기상청 모델 값이 비면 기본 예보로 다시
        _state.value = Weather(
            ok = true,
            tempC = t.toFloat(),
            code = cur.optInt("weather_code", 0),
            windMs = cur.optDouble("wind_speed_10m", 0.0).toFloat(),
            wetHour = bestH, wetProb = best,
            maxC = daily?.optJSONArray("temperature_2m_max").first0().toFloat(),
            minC = daily?.optJSONArray("temperature_2m_min").first0().toFloat(),
        )
        Log.i(TAG, "날씨: ${_state.value.line()}")
    }

    /** 마지막으로 알려진 내 위치 (없으면 서울 시청) */
    private fun where(): Pair<Double, Double> {
        if (context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            context.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
            val lm = context.getSystemService(LocationManager::class.java)
            val loc = runCatching {
                listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER, "fused")
                    .mapNotNull { p -> runCatching { lm?.getLastKnownLocation(p) }.getOrNull() }
                    .maxByOrNull { it.time }
            }.getOrNull()
            if (loc != null) return loc.latitude to loc.longitude
        }
        return 37.5665 to 126.9780
    }

    companion object {
        private const val TAG = "Weather"
    }
}
