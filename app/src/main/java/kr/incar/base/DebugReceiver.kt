package kr.incar.base

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Handler
import android.os.Looper

/**
 * 시연 영상 녹화용 명령 — 화면을 바꾸지 않고 (MainActivity를 띄우지 않고) 보낸다.
 *   adb shell am broadcast -a kr.incar.base.CMD -n kr.incar.base/.DebugReceiver --es say "2차로 포트홀"
 * 받는 명령은 MainActivity와 같다 (say·char·act·gear·boost·dest·chaser·shop·fx·kind·freeze·mute·pet·demo).
 * 매니페스트에서 android.permission.DUMP 를 요구 → adb(셸)만 보낼 수 있고 다른 앱은 못 보낸다.
 */
class DebugReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val vm = (context.applicationContext as App).graph
        val copy = Intent(intent)
        Handler(Looper.getMainLooper()).post { DebugCommands.run(context.applicationContext, vm, copy) }
    }
}

object DebugCommands {
    fun run(context: Context, vm: AppGraph, intent: Intent) {
        intent.getStringExtra("say")?.let { vm.engine.onUtterance(it) }
        intent.getStringExtra("char")?.let { vm.selectCharacterForCheck(it) }
        if (intent.getStringExtra("stage") == "pleos")
            context.startActivity(Intent(context, StageActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))   // 탭 Pleos 화면 모드
        intent.getStringExtra("at")?.toFloatOrNull()?.let { vm.pet.debugMoveTo(it) }   // 펫을 화면 가로 비율 자리로 (녹화용)
        when (val a = intent.getStringExtra("act")) {
            null -> Unit
            "climb" -> vm.pet.debugClimb()
            else -> vm.pet.debugAct(a)                // groom·stretch·eat·sleep·wave·pounce·land · p_습성동작
        }
        when (intent.getStringExtra("gear")) {
            "d" -> vm.live.setGear(kr.incar.base.car.Gear.D)
            "p" -> vm.live.setGear(kr.incar.base.car.Gear.P)
        }
        intent.getStringExtra("boost")?.let { on -> if (vm.live.simBoost != (on == "on")) vm.live.toggleBoost() }
        intent.getStringExtra("dest")?.let { vm.navigateTo(it) }
        intent.getStringExtra("chaser")?.let { vm.engine.emergencyFromBehind(if (it == "fire") "소방차" else "구급차") }   // 뒤에서 오는 긴급차량
        when (intent.getStringExtra("shop")) {
            "chars" -> vm.openShop(0)
            "records" -> vm.openShop(2)
            "close" -> vm.pet.closeShop()
        }
        when (val fx = intent.getStringExtra("fx")) {
            "party" -> vm.pet.celebrate(kr.incar.base.tmi.TmiEngine.ARRIVAL_COINS, intent.getLongExtra("freeze", -1L), intent.getStringExtra("kind"))
            "punch", "cutin" -> vm.pet.debugFx(fx, intent.getLongExtra("freeze", 300L))
        }
        when (intent.getStringExtra("mute")) {
            "on" -> { vm.voice.muted = true; vm.voice.stop() }
            "off" -> vm.voice.muted = false
        }
        when (intent.getStringExtra("pet")) {
            "on" -> vm.pet.show()
            "off" -> vm.pet.hide()
        }
        when (intent.getStringExtra("demo")) {
            "commute" -> vm.startCommuteDemo()
            "live" -> vm.setMode(Mode.LIVE)
        }
    }
}
