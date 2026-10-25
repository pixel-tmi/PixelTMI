package kr.incar.base.voice

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * 펫 소리 — 말 대신 그 동물의 울음소리(8비트, assets/voice/cry_<동물>_<기분>.wav).
 * 내용은 말풍선 글자가 전하고, 소리는 "펫이 뭔가 알려 준다"는 신호만 준다.
 * 위험은 다급한 울음, 코인·기여는 기쁜 울음, 나머지는 평소 울음. 효과음(sfx_)은 그대로 곁들인다.
 * 내비 안내와 겹치지 않도록 짧은 오디오 포커스(덕킹)를 잡는다.
 */
class Voice(context: Context) {

    private val app = context.applicationContext
    private val main = Handler(Looper.getMainLooper())
    private val audio = app.getSystemService(AudioManager::class.java)
    private val clips: Set<String> = app.assets.list("voice")?.map { it.removeSuffix(".wav") }?.toSet() ?: emptySet()

    private val _status = MutableStateFlow(if (clips.any { it.startsWith("cry_") }) "울음소리 켜짐" else "소리 파일 없음")
    val status: StateFlow<String> = _status.asStateFlow()

    private val _lastLatencyMs = MutableStateFlow<Long?>(null)
    val lastLatencyMs: StateFlow<Long?> = _lastLatencyMs.asStateFlow()

    private val _speaking = MutableStateFlow(false)
    val speaking: StateFlow<Boolean> = _speaking.asStateFlow()

    private val queue = ArrayDeque<String>()
    private var player: MediaPlayer? = null
    private var requestedAt = 0L
    private var focus: AudioFocusRequest? = null

    private val attrs = AudioAttributes.Builder()
        .setUsage(AudioAttributes.USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
        .build()

    fun has(clip: String) = clip in clips

    private val prefs = app.getSharedPreferences("Pixel TMI_pet", Context.MODE_PRIVATE)

    /** 소리 크기 0.2~1.0 (설정 말풍선·"소리 크게/작게") — 다음 실행에도 기억 */
    var volume: Float = prefs.getFloat("volume", 1f)
        set(v) {
            field = v.coerceIn(0.2f, 1f)
            prefs.edit().putFloat("volume", field).apply()
            player?.let { p -> runCatching { p.setVolume(field, field) } }
        }

    /** 설정 말풍선의 "음성 끄기" — 말풍선은 그대로, 소리만 끈다 */
    @Volatile var muted = false
    /** 탭 Pleos 앱이 가려져 있고 길안내도 없을 때 — 소리 내지 않는다 */
    @Volatile var suspended = true

    /** 지금 캐릭터 — 어떤 울음소리를 낼지 고른다 */
    @Volatile var character = "cat"

    /**
     * 펫이 알려 줄 때. text는 말풍선에 이미 떠 있으니 소리로 읽지 않는다.
     * urgent = 위험 경고처럼 지금 울던 것을 끊고 바로 알려야 할 때 · happy = 코인·기여 · cry=false면 효과음만
     */
    @Suppress("UNUSED_PARAMETER")
    fun say(text: String, clipKeys: List<String>, urgent: Boolean = false, happy: Boolean = false, cry: Boolean = true, speech: String? = null, mood: String? = null) = main.post {
        if (muted || suspended) return@post
        val sfx = clipKeys.filter { it.startsWith("sfx_") && it != "sfx_pop" && it in clips }
        val m = mood ?: when { urgent -> "alert"; happy -> "happy"; else -> "talk" }
        val base = kr.incar.base.pet.Catalog.get(character).base
        val cryClip = if (cry) listOf("cry_${character}_$m", "cry_${base}_$m", "cry_cat_$m").firstOrNull { it in clips } else null
        val before = sfx.filter { it == "sfx_zing" || it == "sfx_hello" }   // 찌릭·등장음 → 울음 → 코인 띠링
        // 근접 안내는 울음으로 먼저 포인트를 주고 말로 알려 준다 (말소리 파일이 있을 때)
        val talk = speech?.let { "say_$it" }?.takeIf { it in clips }
        val usable = before + listOfNotNull(cryClip, talk) + (sfx - before.toSet())
        if (usable.isEmpty()) return@post
        if (urgent) {
            queue.clear()
            stopPlayer()
        }
        if (player == null) requestedAt = SystemClock.elapsedRealtime()
        queue.addAll(usable)
        queue.add(GAP)
        if (player == null && !gapPending) playNext()
    }

    private var gapPending = false
    private val gapDone = Runnable { gapPending = false; playNext() }

    fun stop() = main.post {
        main.removeCallbacks(gapDone)
        gapPending = false
        queue.clear()
        stopPlayer()
        release()
    }

    private fun playNext() {
        val next = queue.removeFirstOrNull()
        if (next == null) {
            release()
            return
        }
        if (next == GAP) {
            // 소리 사이 짧은 숨 (Pleos 가이드: 음성 앞뒤 150~200ms 여유) — 쉬는 동안엔 새로 틀지 않는다
            gapPending = true
            main.postDelayed(gapDone, 180)
            return
        }
        grabFocus()
        _speaking.value = true
        runCatching {
            app.assets.openFd("voice/$next.wav").use { fd ->
                MediaPlayer().apply {
                    setAudioAttributes(attrs)
                    setDataSource(fd.fileDescriptor, fd.startOffset, fd.length)
                    setOnCompletionListener { mp ->
                        mp.release()
                        player = null
                        playNext()
                    }
                    prepare()
                    setVolume(volume, volume)
                    start()
                }
            }
        }.onSuccess { mp ->
            if (requestedAt != 0L) {
                _lastLatencyMs.value = SystemClock.elapsedRealtime() - requestedAt
                requestedAt = 0L
            }
            player = mp
        }.onFailure {
            player = null
            playNext()
        }
    }

    private fun stopPlayer() {
        player?.let { runCatching { it.stop() }; it.release() }
        player = null
    }

    private fun grabFocus() {
        if (focus != null) return
        val req = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
            .setAudioAttributes(attrs)
            .build()
        audio?.requestAudioFocus(req)
        focus = req
    }

    private fun release() {
        _speaking.value = false
        focus?.let { audio?.abandonAudioFocusRequest(it) }
        focus = null
    }

    fun shutdown() = stop()

    companion object {
        private const val GAP = "__gap"
    }
}
