package kr.incar.base

import android.app.Activity
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.ViewGroup
import android.view.WindowManager
import android.view.inputmethod.EditorInfo
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView

/**
 * 짧은 글자 입력 창 — 목적지(길안내) · 펫 이름.
 *   mode=dest : "어디로 갈까요?" → 고른 길안내 앱(네이버 지도·카카오맵·티맵) + 깃발
 *   mode=name : 펫 이름 바꾸기 ("안녕! ○○예요")
 * 삼성 키보드의 마이크 키로 말로 넣어도 된다.
 */
class InputActivity : Activity() {

    private val vm: AppGraph get() = (application as App).graph

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val mode = intent.getStringExtra("mode") ?: "dest"
        val d = resources.displayMetrics.density
        fun px(v: Int) = (v * d).toInt()
        val ink = 0xFF1E1E1E.toInt()

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(px(28), px(24), px(28), px(20))
            background = GradientDrawable().apply { setColor(0xFFFFFFFF.toInt()); cornerRadius = px(18).toFloat(); setStroke(px(3), ink) }
        }
        fun title(t: String) = TextView(this).apply {
            text = t; textSize = 24f; setTypeface(typeface, Typeface.BOLD); setTextColor(ink)
        }
        fun button(t: String, filled: Boolean, onClick: () -> Unit) = Button(this).apply {
            text = t; textSize = 18f; setTypeface(typeface, Typeface.BOLD); isAllCaps = false
            setTextColor(if (filled) 0xFFFFFFFF.toInt() else ink)
            background = GradientDrawable().apply { setColor(if (filled) ink else 0xFFF2F2F2.toInt()); cornerRadius = px(12).toFloat() }
            setOnClickListener { onClick() }
        }
        val input = EditText(this).apply {
            textSize = 22f; setTypeface(typeface, Typeface.BOLD); setTextColor(ink); setSingleLine()
            inputType = InputType.TYPE_CLASS_TEXT
            imeOptions = EditorInfo.IME_ACTION_DONE
        }

        if (mode == "name") {
            root.addView(title("펫 이름"))
            root.addView(TextView(this).apply { text = "차에 타면 \"안녕! ○○예요\" 하고 인사해요 (8자까지)"; textSize = 17f; setTypeface(typeface, Typeface.BOLD); setTextColor(0xFF333333.toInt()) })
            input.filters = arrayOf(android.text.InputFilter.LengthFilter(8))
            input.setText(vm.engine.petName)
            input.setSelection(input.text.length)
            input.hint = "예: 티미, 나비, 호두"
            root.addView(input, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = px(14) })
            val save = { vm.setPetName(input.text.toString()); finish() }
            input.setOnEditorActionListener { _, _, _ -> save(); true }
            root.addView(row(button("취소", false) { finish() }, button("저장", true) { save() }, px(12)))
        } else {
            root.addView(title("어디로 갈까요?"))
            root.addView(TextView(this).apply { text = "고른 길안내 앱으로 안내하고, 목적지 깃발까지 가는 길 TMI를 알려 드려요"; textSize = 17f; setTypeface(typeface, Typeface.BOLD); setTextColor(0xFF333333.toInt()) })
            var chosen = vm.maps.app                                   // 길안내를 눌렀을 때만 저장 (취소하면 그대로)
            // 길안내 앱 고르기 (없는 앱은 흐리게 — 눌러도 고를 수는 있다)
            val goButton = button("", true) { }
            fun refreshGo() { val a = chosen; goButton.text = "${a.label}${kr.incar.base.tmi.josa(a.label, "로", "으로")} 길안내" }
            val chips = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setPadding(0, px(14), 0, 0) }
            val chipViews = mutableListOf<Pair<kr.incar.base.nav.MapApp, Button>>()
            fun paintChips() = chipViews.forEach { (a, b) ->
                val on = a == chosen
                b.setTextColor(if (on) a.badgeInk else if (vm.maps.installed(a)) ink else 0xFFAAAAAA.toInt())
                b.background = GradientDrawable().apply { setColor(if (on) a.color else 0xFFF2F2F2.toInt()); cornerRadius = px(12).toFloat() }
            }
            kr.incar.base.nav.MapApp.entries.forEach { a ->
                val b = button(a.label + if (vm.maps.installed(a)) "" else " (설치 안 됨)", false) { chosen = a; paintChips(); refreshGo() }
                chipViews += a to b
                chips.addView(b, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = px(8) })
            }
            paintChips()
            refreshGo()
            root.addView(chips)
            input.hint = "예: 잠실역, 롯데월드타워, 회사 주소"
            root.addView(input, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = px(14) })
            val go = {
                val t = input.text.toString()
                if (t.isBlank()) android.widget.Toast.makeText(this, "목적지를 입력해 주세요", android.widget.Toast.LENGTH_SHORT).show()
                else { vm.maps.app = chosen; vm.navigateTo(t); finish() }
            }
            input.setOnEditorActionListener { _, _, _ -> go(); true }
            // 최근 목적지 — 한 번에
            val recent = vm.maps.recent()
            if (recent.isNotEmpty()) {
                root.addView(TextView(this).apply { text = "최근 목적지"; textSize = 16f; setTypeface(typeface, Typeface.BOLD); setTextColor(0xFF333333.toInt()); setPadding(0, px(12), 0, px(4)) })
                recent.take(3).forEach { r ->
                    root.addView(button("⌖  $r", false) { vm.maps.app = chosen; vm.navigateTo(r); finish() }.apply { gravity = Gravity.START or Gravity.CENTER_VERTICAL; setSingleLine() },
                        LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { topMargin = px(6) })
                }
            }
            goButton.setOnClickListener { go() }
            root.addView(row(button("취소", false) { finish() }, goButton, px(14)))
            if (vm.maps.active) root.addView(TextView(this).apply {
                text = "지금 길안내 끝내기"; textSize = 17f; setTypeface(typeface, Typeface.BOLD); setTextColor(0xFFD32F2F.toInt())
                gravity = Gravity.CENTER; setPadding(0, px(14), 0, px(4))
                setOnClickListener { vm.maps.cancel(); finish() }
            })
        }

        setContentView(root, ViewGroup.LayoutParams(px(560), ViewGroup.LayoutParams.WRAP_CONTENT))
        window.setLayout(px(560), ViewGroup.LayoutParams.WRAP_CONTENT)
        window.setGravity(Gravity.CENTER)
        window.setBackgroundDrawableResource(android.R.color.transparent)
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_VISIBLE or WindowManager.LayoutParams.SOFT_INPUT_ADJUST_PAN)
        input.requestFocus()
    }

    private fun row(a: Button, b: Button, top: Int) = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        setPadding(0, top, 0, 0)
        addView(a, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = top / 2 })
        addView(b, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.6f))
    }
}
