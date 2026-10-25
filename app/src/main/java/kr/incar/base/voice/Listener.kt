package kr.incar.base.voice

import ai.pleos.playground.stt.SpeechToText
import ai.pleos.playground.stt.constant.ErrorType
import ai.pleos.playground.stt.constant.Mode
import ai.pleos.playground.stt.listener.OnInitializeListener
import ai.pleos.playground.stt.listener.ResultListener
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.Locale

/**
 * 말로 제보 — Pleos SpeechToText SDK (기기 안 인식, ON_DEVICE).
 * Playground에서 "준비 중"이라 실차에서 안 될 수 있다. 안 되면 화면의 큰 버튼이 같은 일을 한다.
 */
class Listener(private val context: Context, private val onFinal: (String) -> Unit) {

    private val main = Handler(Looper.getMainLooper())
    private var stt: SpeechToText? = null
    private var ready = false

    private val _status = MutableStateFlow("음성 인식 준비 중")
    val status: StateFlow<String> = _status.asStateFlow()

    private val _partial = MutableStateFlow<String?>(null)
    val partial: StateFlow<String?> = _partial.asStateFlow()

    private val _listening = MutableStateFlow(false)
    val listening: StateFlow<Boolean> = _listening.asStateFlow()

    private val results = object : ResultListener {
        override fun onUpdated(text: String, isFinal: Boolean) {
            _partial.value = text
            if (isFinal && text.isNotBlank()) main.post { onFinal(text) }
        }
        override fun onUpdatedEpdData(start: Long, end: Long) = Unit
        override fun onStartedRecognition() { _listening.value = true; fails = 0 }
        override fun onEndedRecognition() { _listening.value = false; again(600) }
        override fun onError(error: ErrorType) {
            _listening.value = false
            fails++
            again(if (fails < 5) 3000 else -1)
            _status.value = "음성 인식 오류: ${error.name}"
            Log.w(TAG, "STT error $error")
        }
        override fun onReady() { _status.value = "음성 인식 켜짐" }
        override fun onUpdatedRms(rms: Double) = Unit
    }

    // ── 갤럭시 탭 등 Pleos가 아닌 기기: 기기 기본 음성 인식(삼성·구글)으로 계속 듣기 ──
    private var sys: android.speech.SpeechRecognizer? = null

    /**
     * 기기 기본 인식은 다시 들을 때마다 '띵' 소리를 낸다 (계속 듣기라 몇 초마다).
     * 다른 소리(내 안내 음성·길안내 앱 음성)가 안 나고 있고 quietStart가 참일 때만
     * 듣기 시작 순간 미디어 소리를 잠깐(준비될 때까지, 길어야 0.7초) 죽였다 살린다.
     */
    var quietStart: () -> Boolean = { false }
    private val am = context.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
    private var hushed = false
    private val unhushTask = Runnable { unhush() }

    private fun hush() {
        if (hushed || !quietStart() || am.isMusicActive) return
        runCatching { am.adjustStreamVolume(android.media.AudioManager.STREAM_MUSIC, android.media.AudioManager.ADJUST_MUTE, 0); hushed = true }
        main.postDelayed(unhushTask, 700)
    }

    private fun unhush() {
        main.removeCallbacks(unhushTask)
        if (!hushed) return
        hushed = false
        runCatching { am.adjustStreamVolume(android.media.AudioManager.STREAM_MUSIC, android.media.AudioManager.ADJUST_UNMUTE, 0) }
    }

    private fun startSystem() {
        if (!android.speech.SpeechRecognizer.isRecognitionAvailable(context)) {
            _status.value = "이 기기엔 음성 인식이 없어요"
            return
        }
        val r = android.speech.SpeechRecognizer.createSpeechRecognizer(context)
        r.setRecognitionListener(object : android.speech.RecognitionListener {
            override fun onReadyForSpeech(params: android.os.Bundle?) {
                _listening.value = true; fails = 0
                if (hushed) { main.removeCallbacks(unhushTask); main.postDelayed(unhushTask, 250) }   // 띵은 준비 직후에 난다
            }
            override fun onBeginningOfSpeech() = Unit
            override fun onRmsChanged(rmsdB: Float) = Unit
            override fun onBufferReceived(buffer: ByteArray?) = Unit
            override fun onEndOfSpeech() = Unit
            override fun onPartialResults(partial: android.os.Bundle?) {
                partial?.getStringArrayList(android.speech.SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()?.let { _partial.value = it }
            }
            override fun onResults(results: android.os.Bundle?) {
                _listening.value = false
                results?.getStringArrayList(android.speech.SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                    ?.takeIf { it.isNotBlank() }?.let { Log.i(TAG, "들은 말: $it"); onFinal(it) }
                again(300)
            }
            override fun onError(error: Int) {
                _listening.value = false
                unhush()
                // 아무 말이 없었던 건 실패가 아니다 (계속 듣기라 자주 생김)
                val quiet = error == android.speech.SpeechRecognizer.ERROR_NO_MATCH || error == android.speech.SpeechRecognizer.ERROR_SPEECH_TIMEOUT
                if (!quiet) fails++
                again(if (quiet) 300 else if (fails < 5) 2500 else -1)
            }
            override fun onEvent(eventType: Int, params: android.os.Bundle?) = Unit
        })
        sys = r
        ready = true
        _status.value = "음성 인식 켜짐 (기기 기본)"
        if (continuous && !paused) listen()
    }

    /** 음성 인식 엔진 연결 — 앱 시작을 막지 않도록 조금 뒤에 부른다 */
    fun start() {
        if (stt != null || sys != null) return
        if (!kr.incar.base.car.CarSpeedSource.available) { startSystem(); return }   // 차가 아니면 기기 기본 음성 인식
        runCatching {
            SpeechToText(context.applicationContext, Mode.ON_DEVICE).also { s ->
                stt = s
                s.initialize(object : OnInitializeListener {
                    override fun onSuccess() {
                        ready = true
                        runCatching { s.setLocale(Locale.KOREA) }
                        s.addListener(results)
                        _status.value = "음성 인식 켜짐"
                        if (continuous) main.post { listen() }
                    }
                    override fun onFailure(error: ErrorType) {
                        _status.value = "음성 인식 불가: ${error.name}"
                    }
                })
            }
        }.onFailure {
            _status.value = "음성 인식 불가: ${it.javaClass.simpleName}"
            Log.w(TAG, "STT init failed", it)
        }
    }

    /**
     * 계속 듣기 — 부르는 말 없이 "제보", "1차로 포트홀"이 바로 먹는다 (벤츠 "다음 트랙"처럼).
     * 한 문장이 끝나면 다시 듣고, 연달아 5번 실패하면 쉰다.
     */
    var continuous = true
        set(v) {
            field = v
            if (v) { fails = 0; listen() } else cancel()
        }
    private var fails = 0

    /** 앱이 가려졌을 때 잠깐 멈춤 — 탭에선 앱 밖에서 마이크(와 인식 시작음)도 쉰다 */
    @Volatile var paused = false
        private set

    fun pause() {
        paused = true
        main.removeCallbacksAndMessages(null)
        cancel()
        unhush()
    }

    /** 다시 듣기 (멈춤이었든 5번 실패로 쉬던 중이든) */
    fun resume() {
        paused = false
        fails = 0
        if (continuous && !_listening.value) listen()
    }

    /** 연달아 실패해서 쉬게 됐을 때 (말풍선 안내용) */
    var onGaveUp: (() -> Unit)? = null

    private fun again(delayMs: Long) {
        if (paused) return
        if (!continuous || delayMs < 0) {
            if (delayMs < 0) { _status.value = "음성 인식 쉬는 중 (마이크 버튼으로 다시)"; onGaveUp?.invoke() }
            return
        }
        main.postDelayed({ if (continuous && !paused && !_listening.value) listen() }, delayMs)
    }

    /** 말하기 버튼. 인식이 안 되면 false를 돌려준다. */
    fun listen(): Boolean {
        sys?.let { r ->
            if (!ready) return false
            _partial.value = null
            val i = android.content.Intent(android.speech.RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                .putExtra(android.speech.RecognizerIntent.EXTRA_LANGUAGE_MODEL, android.speech.RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                .putExtra(android.speech.RecognizerIntent.EXTRA_LANGUAGE, "ko-KR")
                .putExtra(android.speech.RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                .putExtra(android.speech.RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            hush()
            return runCatching { r.startListening(i); _listening.value = true }.isSuccess.also { if (!it) unhush() }
        }
        val s = stt ?: return false
        if (!ready) return false
        _partial.value = null
        return runCatching { s.request(); _listening.value = true }.isSuccess
    }

    fun cancel() {
        runCatching { sys?.cancel() }
        runCatching { stt?.stop() }
        _listening.value = false
    }

    fun release() {
        paused = true
        main.removeCallbacksAndMessages(null)
        unhush()
        runCatching { sys?.destroy() }
        sys = null
        runCatching { stt?.removeListener(results) }
        runCatching { stt?.release() }
    }

    companion object {
        private const val TAG = "Listener"
    }
}
