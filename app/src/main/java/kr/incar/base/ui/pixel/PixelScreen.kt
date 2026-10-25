package kr.incar.base.ui.pixel

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.delay
import kr.incar.base.AppViewModel
import kr.incar.base.Mode
import kr.incar.base.tmi.Fx
import kr.incar.base.tmi.Hazard
import kr.incar.base.tmi.HazardType
import kr.incar.base.tmi.ReportStage
import kr.incar.base.tmi.Rewards
import kr.incar.base.tmi.Source
import kr.incar.base.tmi.TmiKind
import kr.incar.base.tmi.TmiUi
import kotlin.math.roundToInt

/**
 * Pixel TMI — 도트 다마고치 화면.
 * 화면의 주인공은 티미의 말풍선. 운전 중엔 듣기만 하면 되고, 손은 큰 버튼 한 번.
 * Pleos 앱 영역의 반쪽(세로)에 맞춰 짜고, 나머지 반쪽은 내비 지도에 양보한다.
 */
@Composable
fun PixelScreen(vm: AppViewModel) {
    val ctx = LocalContext.current
    val font = remember { galmuri(ctx.assets) }
    val ui by vm.engine.ui.collectAsStateWithLifecycle()
    val car by vm.state.collectAsStateWithLifecycle()
    val navi by vm.naviView.collectAsStateWithLifecycle()
    val mode by vm.mode.collectAsStateWithLifecycle()
    val step by vm.demo.currentStep.collectAsStateWithLifecycle()
    val speaking by vm.voice.speaking.collectAsStateWithLifecycle()
    val partial by vm.listener.partial.collectAsStateWithLifecycle()

    var cut by remember { mutableStateOf<Hazard?>(null) }
    var coinPop by remember { mutableStateOf<Pair<Long, Int>?>(null) }
    var levelUp by remember { mutableStateOf<Long?>(null) }
    var happyUntil by remember { mutableStateOf(0L) }
    LaunchedEffect(Unit) {
        vm.engine.fx.collect { f ->
            when (f) {
                is Fx.Danger -> cut = f.hazard
                is Fx.Coins -> { coinPop = System.currentTimeMillis() to f.amount; happyUntil = System.currentTimeMillis() + 1800 }
                is Fx.LevelUp -> levelUp = System.currentTimeMillis()
                is Fx.Expired, is Fx.Arrived -> Unit   // 펫 화면에서 보여 준다
            }
        }
    }

    // 말풍선: 새 TMI가 오면 쏙 나왔다가, 다 읽을 시간이 지나면 들어간다
    val line = ui.feed.firstOrNull()
    var bubbleOn by remember { mutableStateOf(false) }
    LaunchedEffect(line?.atMillis) {
        if (line == null) return@LaunchedEffect
        bubbleOn = false
        delay(120)
        bubbleOn = true
        delay((3200 + line.text.length * 95L).coerceAtMost(12_000))
        bubbleOn = false
    }

    val approachD = ui.approach?.distanceM
    val mood = when {
        approachD != null && approachD <= 500 && !ui.approach!!.hazard.type.fixed -> Mood.ALERT
        ui.parkedSummary || System.currentTimeMillis() < happyUntil -> Mood.HAPPY
        speaking -> Mood.TALK
        else -> Mood.NORMAL
    }

    BoxWithConstraints(Modifier.fillMaxSize().background(P.paper)) {
        val wide = maxWidth > 1100.dp
        Column(Modifier.fillMaxSize().padding(horizontal = 18.dp, vertical = 14.dp)) {
            Header(vm, ui, mode, navi.hasRoute, navi.destinationName, vm.engine.remainingM(), font)
            Spacer(Modifier.height(12.dp))
            if (wide) {
                Row(Modifier.weight(1f)) {
                    Lcd(Modifier.weight(0.6f).fillMaxHeight(), ui, car.speedKmh ?: 0f, mood, font, line?.kind, bubbleText(line?.text), bubbleOn, cut, { cut = null },
                        coinPop, levelUp, if (mode == Mode.DEMO) step else null, vm)
                    Spacer(Modifier.width(16.dp))
                    Column(Modifier.weight(0.4f).fillMaxHeight()) { Controls(vm, ui, partial, font) }
                }
            } else {
                Lcd(Modifier.weight(1f).fillMaxWidth(), ui, car.speedKmh ?: 0f, mood, font, line?.kind, bubbleText(line?.text), bubbleOn, cut, { cut = null },
                    coinPop, levelUp, if (mode == Mode.DEMO) step else null, vm)
                Spacer(Modifier.height(12.dp))
                Controls(vm, ui, partial, font)
            }
        }
    }
}

/** 말풍선에선 " · "를 줄바꿈으로 — TMI가 한 줄씩 쏟아지는 느낌 */
private fun bubbleText(s: String?) = s?.replace(" · ", "\n") ?: ""

@Composable
private fun Header(vm: AppViewModel, ui: TmiUi, mode: Mode, hasRoute: Boolean, dest: String?, remainM: Int, font: FontFamily) {
    var menu by remember { mutableStateOf(false) }
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column {
            Row(verticalAlignment = Alignment.Bottom) {
                Text("Pixel", color = P.ink, fontSize = 30.sp, fontFamily = font)
                Text("TMI", color = P.red, fontSize = 30.sp, fontFamily = font)
            }
            Text(
                if (hasRoute) "가는 길 · ${dest ?: ""} ${"%.1f".format(remainM / 1000.0)}km" else "내 주변 TMI",
                color = P.mid, fontSize = 17.sp, fontFamily = font,
            )
        }
        Spacer(Modifier.weight(1f))
        CoinIcon(30.dp)
        Spacer(Modifier.width(8.dp))
        Text("${ui.rewards.coins}", color = P.ink, fontSize = 26.sp, fontFamily = font)
        Spacer(Modifier.width(12.dp))
        Box(Modifier.pixelBox(fill = P.ink, dot = 3.dp, shadow = false).padding(horizontal = 12.dp, vertical = 6.dp)) {
            Text("Lv.${ui.rewards.level}", color = P.paper, fontSize = 18.sp, fontFamily = font)
        }
        Spacer(Modifier.width(12.dp))
        Box(
            Modifier.pixelBox(fill = if (ui.on) P.ink else P.paper, dot = 4.dp).clickable { vm.engine.setOn(!ui.on) }
                .padding(start = 16.dp, end = 20.dp, top = 8.dp, bottom = 12.dp)
        ) {
            Text(if (ui.on) "TMI ON" else "TMI OFF", color = if (ui.on) P.paper else P.ink, fontSize = 20.sp, fontFamily = font)
        }
        Spacer(Modifier.width(10.dp))
        Box {
            Box(Modifier.pixelBox(dot = 4.dp).clickable { menu = true }.padding(start = 14.dp, end = 18.dp, top = 6.dp, bottom = 10.dp)) {
                Text("≡", color = P.ink, fontSize = 24.sp, fontFamily = font)
            }
            DropdownMenu(menu, onDismissRequest = { menu = false }) {
                DropdownMenuItem(text = { Text("▶ 출근길 시연", fontFamily = font, fontSize = 20.sp) }, onClick = { menu = false; vm.startCommuteDemo() })
                DropdownMenuItem(text = { Text("실차 연결${if (mode == Mode.LIVE) " ✓" else ""}", fontFamily = font, fontSize = 20.sp) }, onClick = { menu = false; vm.setMode(Mode.LIVE) })
                DropdownMenuItem(text = { Text("배속 바꾸기 (×1 / ×4)", fontFamily = font, fontSize = 20.sp) }, onClick = { menu = false; vm.cycleScale() })
                DropdownMenuItem(text = { Text("위험 다시 깔기", fontFamily = font, fontSize = 20.sp) }, onClick = { menu = false; vm.reseed() })
                DropdownMenuItem(text = { Text("바탕화면 펫 켜기/끄기", fontFamily = font, fontSize = 20.sp) }, onClick = { menu = false; vm.togglePet() })
                DropdownMenuItem(text = { Text("차량 신호 점검", fontFamily = font, fontSize = 20.sp) }, onClick = { menu = false; vm.showSignals(true) })
                DropdownMenuItem(text = { Text("코인 초기화", fontFamily = font, fontSize = 20.sp) }, onClick = { menu = false; vm.engine.resetRewards() })
            }
        }
    }
}

@Composable
private fun Lcd(
    modifier: Modifier,
    ui: TmiUi,
    speed: Float,
    mood: Mood,
    font: FontFamily,
    kind: TmiKind?,
    text: String,
    bubbleOn: Boolean,
    cut: Hazard?,
    onCutDone: () -> Unit,
    coinPop: Pair<Long, Int>?,
    levelUp: Long?,
    step: String?,
    vm: AppViewModel,
) {
    Box(modifier.pixelBox(dot = 6.dp).padding(start = 12.dp, top = 12.dp, end = 18.dp, bottom = 18.dp)) {
        Stage(ui.posM, speed, ui.hazards, ui.approach?.hazard?.id, ui.rewards.level, mood, font, Modifier.fillMaxSize())

        SpeechBubble(
            visible = bubbleOn && cut == null && text.isNotBlank(),
            tag = when (kind) { TmiKind.SYSTEM, null -> "티미"; else -> kind.label },
            text = text,
            danger = kind == TmiKind.DANGER,
            font = font,
            modifier = Modifier.align(Alignment.TopStart).padding(start = 22.dp, top = 18.dp, end = 22.dp),
        )

        if (step != null) {
            Text(step, color = P.mid, fontSize = 16.sp, fontFamily = font, modifier = Modifier.align(Alignment.BottomEnd).padding(8.dp))
        }

        CoinPop(coinPop, font)
        LevelUpBanner(levelUp, font)
        DangerCutIn(cut, font, onCutDone)

        if (ui.parkedSummary) Summary(ui.rewards, font) { vm.closeSummary() }
    }
}

@Composable
private fun CoinPop(pop: Pair<Long, Int>?, font: FontFamily) {
    if (pop == null) return
    val a = remember(pop.first) { Animatable(0f) }
    LaunchedEffect(pop.first) { a.animateTo(1f, tween(1000)) }
    if (a.value >= 1f) return
    Box(Modifier.fillMaxSize()) {
        Row(
            Modifier.align(Alignment.BottomStart).padding(start = 140.dp, bottom = 230.dp)
                .offset { IntOffset(0, (-90 * a.value).roundToInt()) }
                .graphicsLayer { alpha = 1f - a.value * a.value },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            CoinIcon(34.dp)
            Spacer(Modifier.width(6.dp))
            Text("+${pop.second}", color = P.ink, fontSize = 34.sp, fontFamily = font)
        }
    }
}

@Composable
private fun LevelUpBanner(at: Long?, font: FontFamily) {
    if (at == null) return
    var show by remember(at) { mutableStateOf(true) }
    LaunchedEffect(at) { delay(2200); show = false }
    if (!show) return
    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Box(Modifier.pixelBox(fill = P.yellow, dot = 6.dp).padding(horizontal = 34.dp, vertical = 20.dp)) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text("LEVEL UP!", color = P.ink, fontSize = 46.sp, fontFamily = font)
                Text("티미가 자랐어요", color = P.ink, fontSize = 24.sp, fontFamily = font)
            }
        }
    }
}

@Composable
private fun Controls(vm: AppViewModel, ui: TmiUi, partial: String?, font: FontFamily) {
    ReportStrip(ui, font)
    // 말하기 (가장 큰 버튼)
    Box(
        Modifier.fillMaxWidth().height(124.dp)
            .pixelBox(fill = if (ui.listening) P.ink else P.paper, dot = 6.dp)
            .clickable { vm.talk() },
        contentAlignment = Alignment.CenterStart,
    ) {
        Row(Modifier.padding(start = 26.dp, end = 30.dp, bottom = 6.dp), verticalAlignment = Alignment.CenterVertically) {
            Canvas(Modifier.size(64.dp)) {
                val d = size.width / 13f
                sprite(Sprites.MIC, 0f, 0f, d, tint = if (ui.listening) P.paper else null)
            }
            Spacer(Modifier.width(18.dp))
            Column {
                Text(if (ui.listening) "듣는 중…" else "말하기", color = if (ui.listening) P.paper else P.ink, fontSize = 40.sp, fontFamily = font)
                Text(
                    (ui.heard ?: partial)?.let { "“$it”" } ?: "“TMI 알려줘” “1차로 포트홀”",
                    color = if (ui.listening) P.paper else P.mid, fontSize = 20.sp, fontFamily = font, maxLines = 1,
                )
            }
        }
    }
    Spacer(Modifier.height(14.dp))
    val v = ui.verify
    if (v != null) {
        Text("방금 지난 ${v.hazard.type.label}, 아직 있어?", color = P.ink, fontSize = 26.sp, fontFamily = font)
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
            PixelButton("아직 있어", font, Modifier.weight(1f).height(130.dp), fill = P.ink, textColor = P.paper, sizeSp = 36) { vm.engine.answerVerify(true) }
            PixelButton("없어졌어", font, Modifier.weight(1f).height(130.dp), sizeSp = 36) { vm.engine.answerVerify(false) }
        }
    } else {
        val quick = listOf(HazardType.POTHOLE, HazardType.DEBRIS, HazardType.ACCIDENT, HazardType.CONSTRUCTION)
        quick.chunked(2).forEachIndexed { i, row ->
            if (i > 0) Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                row.forEach { t ->
                    PixelButton(t.label, font, Modifier.weight(1f).height(112.dp), icon = Sprites.of(t), sizeSp = 34) { vm.engine.report(t, null) }
                }
            }
        }
    }
}

@Composable
private fun ReportStrip(ui: TmiUi, font: FontFamily) {
    val r = ui.myReport ?: return
    Row(
        Modifier.fillMaxWidth().pixelBox(dot = 4.dp, shadow = false).padding(horizontal = 18.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            "${if (r.source == Source.AUTO) "차가 제보" else "내 제보"} ${kr.incar.base.tmi.laneText(r.lane)}${r.type.label}",
            color = P.ink, fontSize = 20.sp, fontFamily = font,
        )
        Spacer(Modifier.weight(1f))
        StepChip("접수", true, font)
        StepChip(if (r.sharedTo > 0) "공유${r.sharedTo}" else "공유", r.stage >= ReportStage.SHARED, font)
        if (r.type != HazardType.RAIN) StepChip(if (r.confirms > 0) "확인${r.confirms}" else "확인", r.stage >= ReportStage.CONFIRMED, font)
    }
    Spacer(Modifier.height(12.dp))
}

@Composable
private fun StepChip(label: String, done: Boolean, font: FontFamily) {
    Box(
        Modifier.padding(start = 8.dp).pixelBox(fill = if (done) P.ink else P.paper, dot = 3.dp, shadow = false).padding(horizontal = 10.dp, vertical = 4.dp)
    ) {
        Text(if (done) "✓$label" else label, color = if (done) P.paper else P.mid, fontSize = 17.sp, fontFamily = font)
    }
}

@Composable
private fun Summary(r: Rewards, font: FontFamily, onClose: () -> Unit) {
    Box(Modifier.fillMaxSize().background(P.paper.copy(alpha = 0.94f)).clickable(onClick = onClose), contentAlignment = Alignment.Center) {
        Column(
            Modifier.pixelBox(dot = 6.dp).padding(horizontal = 36.dp, vertical = 28.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text("오늘의 정산", color = P.mid, fontSize = 22.sp, fontFamily = font)
            Spacer(Modifier.height(8.dp))
            Canvas(Modifier.size(width = 240.dp, height = 200.dp)) {
                val tPx = size.width / 30f
                drawTimi(r.level, Mood.HAPPY, size.width / 2 - 12 * tPx, size.height - 18 * tPx, tPx)
            }
            Text("Lv.${r.level} ${r.title}", color = P.ink, fontSize = 38.sp, fontFamily = font)
            if (r.level > 1) Text("티미가 자랐어요!", color = P.red, fontSize = 22.sp, fontFamily = font)
            Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(28.dp)) {
                Stat("${r.coins}", "코인", font)
                Stat("${kr.incar.base.tmi.FleetSimulator.HELPED_TODAY}대", "내 덕분에 감속", font)
                Stat("${r.reportsToday}건", "직접 제보", font)
            }
            Spacer(Modifier.height(12.dp))
            Text("주차 중에만 보여요 · 눌러서 닫기", color = P.mid, fontSize = 16.sp, fontFamily = font, textAlign = TextAlign.Center)
        }
    }
}

@Composable
private fun Stat(value: String, label: String, font: FontFamily) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(value, color = P.ink, fontSize = 34.sp, fontFamily = font)
        Text(label, color = P.mid, fontSize = 17.sp, fontFamily = font)
    }
}
