"""
동물별 8비트 울음소리 만들기 (외부 라이브러리 없음) — 펫이 말 대신 우는 소리.
말풍선 글자가 내용을 전하고, 소리는 "펫이 뭔가 알려 준다"는 신호만 준다.
도트 그림에 맞춰 옛날 게임기 소리(사각파·잡음)로 합성한다 → 녹음 소리를 베끼지 않음.
사용: python 동물_울음소리_만들기.py <assets\\voice 폴더>
출력: cry_<이름>_<기분>.wav — cat·dog·lion·horse + 상점 car·dragon·plane·heli·ufo + 흰/검은 고양이·할로윈·공룡, 기분 talk(평소)·alert(위험)·happy(코인)
"""
import math
import os
import random
import struct
import sys
import wave

RATE = 16000
random.seed(7)


def pulse(phase, duty):
    return 1.0 if phase % 1.0 < duty else -1.0


def voice(points, ms, vol=0.32, duty=(0.5, 0.5), vib=(0.0, 0.0), attack=12, release=60, noise=0.0, trem=(0.0, 0.0)):
    """음 높이 곡선(points: (0~1 위치, Hz) 목록)을 따라가는 사각파 한 소리.
    duty: 시작→끝 파형 폭 (좁으면 '이', 넓으면 '아오' 느낌), vib: (속도 Hz, 폭 비율), trem: 떨림 (속도, 깊이), noise: 잡음 섞기"""
    n = int(RATE * ms / 1000)
    out = []
    phase = 0.0
    hold = 0.0
    for i in range(n):
        p = i / n
        # 음 높이: 꺾은선 보간
        for (a, fa), (b, fb) in zip(points, points[1:]):
            if a <= p <= b:
                f = fa + (fb - fa) * ((p - a) / (b - a) if b > a else 0)
                break
        else:
            f = points[-1][1]
        t = i / RATE
        if vib[0]:
            f *= 1 + vib[1] * math.sin(2 * math.pi * vib[0] * t)
        phase += f / RATE
        d = duty[0] + (duty[1] - duty[0]) * p
        s = pulse(phase, d) * (1 - noise)
        if noise:
            if i % 3 == 0:
                hold = random.choice((-1.0, 1.0))
            s += hold * noise
        env = min(1.0, i / max(1, RATE * attack / 1000)) * min(1.0, (n - i) / max(1, RATE * release / 1000))
        if trem[0]:
            env *= 1 - trem[1] * (0.5 + 0.5 * math.sin(2 * math.pi * trem[0] * t))
        out.append(s * vol * env)
    return out


def rest(ms):
    return [0.0] * int(RATE * ms / 1000)


def save(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in samples))


# ── 고양이: 냐옹 (올라갔다 내려오는 음 + 파형 폭이 '이→아→오'로 넓어짐) ──
def cat_talk():
    return voice([(0, 620), (0.35, 940), (1, 560)], 380, duty=(0.12, 0.5), vib=(7, 0.015))


def cat_alert():
    one = voice([(0, 820), (0.4, 1180), (1, 900)], 150, vol=0.34, duty=(0.12, 0.4))
    return one + rest(50) + one


def cat_happy():
    return voice([(0, 700), (0.3, 1000), (1, 820)], 200, duty=(0.12, 0.45)) + rest(30) + voice([(0, 900), (1, 1350)], 220, duty=(0.2, 0.5), vib=(9, 0.02))


# ── 강아지: 멍 (짧고 굵게 떨어지는 음 + 잡음) ──
def bark(f0, f1, ms=120, vol=0.36):
    return voice([(0, f0), (1, f1)], ms, vol=vol, duty=(0.5, 0.3), noise=0.25, attack=4, release=40)


def dog_talk():
    return bark(380, 230) + rest(90) + bark(360, 220)


def dog_alert():
    out = []
    for _ in range(3):
        out += bark(520, 330, 95, 0.38) + rest(60)
    return out


def dog_happy():
    return bark(400, 260) + rest(70) + voice([(0, 700), (1, 1300)], 160, duty=(0.25, 0.25), attack=4)


# ── 사자: 어흥 (낮은 음 + 떨림 + 잡음, 귀엽게 짧게) ──
def lion_talk():
    return voice([(0, 150), (0.5, 230), (1, 130)], 520, vol=0.38, duty=(0.35, 0.5), noise=0.3, trem=(26, 0.45), attack=40, release=140)


def lion_alert():
    return voice([(0, 170), (0.3, 280), (1, 140)], 800, vol=0.4, duty=(0.3, 0.5), noise=0.35, trem=(30, 0.5), attack=30, release=200)


def lion_happy():
    return voice([(0, 200), (1, 320)], 220, vol=0.36, duty=(0.4, 0.5), noise=0.25, trem=(24, 0.35), attack=20)


# ── 말: 히히힝 (높게 시작해 떨며 내려오는 음) + 푸르르 ──
def horse_talk():
    return voice([(0, 1250), (0.25, 1400), (1, 620)], 600, vol=0.3, duty=(0.15, 0.4), vib=(11, 0.06), release=120)


def snort():
    return voice([(0, 110), (1, 90)], 220, vol=0.3, duty=(0.5, 0.5), noise=0.6, trem=(32, 0.6), attack=10)


def horse_alert():
    return voice([(0, 1450), (0.2, 1650), (1, 700)], 650, vol=0.33, duty=(0.15, 0.4), vib=(12, 0.07), release=120) + rest(60) + snort()


def horse_happy():
    return voice([(0, 900), (1, 1500)], 260, vol=0.3, duty=(0.15, 0.35), vib=(11, 0.05))


# ── 상점 캐릭터: 스포츠카 빵빵 · 용 크앙 · 비행기 슝 · 헬기 두두두 · UFO 삐용삐용 ──
def car_talk():
    beep = voice([(0, 520), (1, 520)], 110, vol=0.3, duty=(0.5, 0.5), attack=4, release=20)
    return beep + rest(70) + beep


def car_alert():
    return voice([(0, 620), (1, 620)], 420, vol=0.32, duty=(0.5, 0.5), vib=(6, 0.02), attack=4)


def car_happy():
    return voice([(0, 90), (0.6, 160), (1, 120)], 420, vol=0.32, duty=(0.3, 0.5), noise=0.35, trem=(40, 0.5), attack=10) + car_talk()


def dragon_talk():
    return voice([(0, 300), (0.4, 480), (1, 260)], 420, vol=0.34, duty=(0.3, 0.5), noise=0.2, trem=(22, 0.35), attack=20)


def dragon_alert():
    return voice([(0, 320), (0.3, 560), (1, 240)], 700, vol=0.36, duty=(0.3, 0.5), noise=0.3, trem=(28, 0.45), attack=20, release=160)


def dragon_happy():
    return voice([(0, 420), (1, 760)], 260, vol=0.32, duty=(0.3, 0.45), noise=0.15, trem=(20, 0.3))


def plane_talk():
    return voice([(0, 900), (1, 1500)], 320, vol=0.26, duty=(0.25, 0.25), vib=(14, 0.02))


def plane_alert():
    return voice([(0, 1500), (0.5, 900), (1, 1500)], 520, vol=0.3, duty=(0.25, 0.25))


def plane_happy():
    return voice([(0, 700), (1, 1800)], 420, vol=0.26, duty=(0.2, 0.3), vib=(10, 0.03))


def chop(n, f=95, vol=0.32):
    out = []
    for _ in range(n):
        out += voice([(0, f), (1, f * 0.8)], 60, vol=vol, duty=(0.5, 0.5), noise=0.5, attack=2, release=25) + rest(25)
    return out


def heli_talk():
    return chop(5)


def heli_alert():
    return chop(9, 120, 0.36)


def heli_happy():
    return chop(4) + voice([(0, 800), (1, 1300)], 160, vol=0.26, duty=(0.25, 0.25))


def ufo_talk():
    return voice([(0, 700), (1, 700)], 360, vol=0.26, duty=(0.5, 0.5), vib=(9, 0.25))


def ufo_alert():
    return voice([(0, 1100), (0.5, 600), (1, 1100)], 600, vol=0.3, duty=(0.5, 0.5), vib=(12, 0.2))


def ufo_happy():
    return voice([(0, 600), (1, 1600)], 420, vol=0.26, duty=(0.5, 0.5), vib=(10, 0.15))



# ── 추가 캐릭터 (10-25): 흰/검은 고양이 · 할로윈 · 공룡 — 캐릭터마다 다른 소리 ──
def cat_white_talk():
    return voice([(0, 760), (0.35, 1150), (1, 690)], 340, duty=(0.1, 0.45), vib=(8, 0.02))


def cat_white_alert():
    one = voice([(0, 980), (0.4, 1400), (1, 1080)], 130, vol=0.32, duty=(0.1, 0.35))
    return one + rest(45) + one


def cat_white_happy():
    return voice([(0, 860), (1, 1250)], 170, duty=(0.1, 0.4)) + rest(25) + voice([(0, 1100), (1, 1650)], 200, duty=(0.15, 0.45), vib=(10, 0.02))


def cat_black_talk():
    return voice([(0, 470), (0.4, 740), (1, 420)], 440, duty=(0.15, 0.55), vib=(6, 0.03))


def cat_black_alert():
    one = voice([(0, 640), (0.4, 920), (1, 700)], 170, vol=0.34, duty=(0.15, 0.45))
    return one + rest(55) + one


def cat_black_happy():
    return voice([(0, 540), (0.3, 800), (1, 650)], 220, duty=(0.15, 0.5)) + rest(30) + voice([(0, 700), (1, 1050)], 240, duty=(0.2, 0.5), vib=(8, 0.03))


# 유령: 우~우~ (느린 떨림으로 미끄러지는 소리)
def ghost_talk():
    return voice([(0, 520), (0.5, 640), (1, 360)], 720, vol=0.22, duty=(0.5, 0.5), vib=(5, 0.07), attack=140, release=220)


def ghost_alert():
    return voice([(0, 420), (1, 900)], 300, vol=0.26, duty=(0.5, 0.5), vib=(7, 0.08), attack=40) + voice([(0, 900), (1, 380)], 420, vol=0.24, duty=(0.5, 0.5), vib=(6, 0.08), release=200)


def ghost_happy():
    out = []
    for f in (900, 1100, 1300):
        out += voice([(0, f), (1, f * 1.1)], 110, vol=0.22, duty=(0.5, 0.5), vib=(12, 0.05), attack=10, release=40) + rest(30)
    return out


# 호박 잭: 흐흐흐 (통통 튀는 웃음)
def cackle(fs, ms=90, vol=0.28):
    out = []
    for f in fs:
        out += voice([(0, f), (1, f * 0.85)], ms, vol=vol, duty=(0.25, 0.35), noise=0.12, attack=4, release=30) + rest(40)
    return out


def pumpkin_talk():
    return cackle((720, 660, 600))


def pumpkin_alert():
    return cackle((980, 900, 980, 900, 980), 70, 0.32)


def pumpkin_happy():
    return cackle((520, 660, 820, 1040), 80)


# 마녀 고양이: 냐~ + 반짝 마법 소리
def twinkle(fs=(1568, 1976, 2349, 3136)):
    out = []
    for f in fs:
        out += voice([(0, f), (1, f)], 55, vol=0.16, duty=(0.12, 0.12), attack=2, release=30)
    return out


def witch_talk():
    return voice([(0, 680), (0.35, 1020), (1, 640)], 320, duty=(0.12, 0.45), vib=(8, 0.02)) + twinkle()


def witch_alert():
    return voice([(0, 900), (1, 1250)], 140, vol=0.32, duty=(0.12, 0.4)) + rest(40) + cackle((620, 560, 500), 80)


def witch_happy():
    return voice([(0, 760), (1, 1150)], 200, duty=(0.12, 0.45)) + twinkle((1047, 1319, 1568, 2093))


# 티라노: 크르르 어흥 (아주 낮은 음 + 거친 잡음)
def trex_talk():
    return voice([(0, 95), (0.4, 150), (1, 85)], 620, vol=0.4, duty=(0.35, 0.5), noise=0.45, trem=(30, 0.5), attack=50, release=160)


def trex_alert():
    return voice([(0, 110), (0.3, 210), (1, 80)], 950, vol=0.42, duty=(0.3, 0.5), noise=0.5, trem=(34, 0.55), attack=40, release=240)


def trex_happy():
    chomp = voice([(0, 160), (1, 90)], 70, vol=0.36, duty=(0.5, 0.5), noise=0.6, attack=2, release=20)
    return voice([(0, 120), (1, 160)], 300, vol=0.34, duty=(0.4, 0.5), noise=0.35, trem=(24, 0.4)) + rest(40) + chomp + rest(50) + chomp


# 트리케라톱스: 흥! 콧김 + 쿵쿵 발 구르기
def thump(vol=0.38):
    return voice([(0, 80), (1, 50)], 90, vol=vol, duty=(0.5, 0.5), noise=0.4, attack=2, release=50)


def trike_talk():
    return voice([(0, 170), (0.5, 230), (1, 150)], 380, vol=0.34, duty=(0.4, 0.5), noise=0.3, trem=(20, 0.3), attack=20) + rest(40) + thump()


def trike_alert():
    return thump() + rest(50) + thump() + rest(40) + voice([(0, 200), (0.4, 300), (1, 160)], 500, vol=0.38, duty=(0.35, 0.5), noise=0.35, trem=(26, 0.4))


def trike_happy():
    return snort() + rest(30) + voice([(0, 200), (1, 340)], 240, vol=0.32, duty=(0.4, 0.5), noise=0.2)


# 스테고사우루스: 웅~ 낮은 콧노래 + 꼬리 휙
def swish():
    return voice([(0, 1800), (1, 600)], 160, vol=0.18, duty=(0.5, 0.5), noise=0.9, attack=10, release=60)


def stego_talk():
    one = voice([(0, 120), (1, 105)], 220, vol=0.34, duty=(0.55, 0.6), trem=(14, 0.25), attack=30, release=80)
    return one + rest(60) + one


def stego_alert():
    return stego_talk() + rest(40) + swish() + thump(0.34)


def stego_happy():
    return voice([(0, 110), (1, 190)], 420, vol=0.32, duty=(0.55, 0.6), trem=(10, 0.2), attack=40)


# 브라키오사우루스: 부우~우 (고래처럼 낮고 긴 울음)
def brachio_talk():
    return voice([(0, 80), (0.4, 125), (1, 70)], 950, vol=0.4, duty=(0.5, 0.55), vib=(3, 0.05), attack=220, release=300)


def brachio_alert():
    call = voice([(0, 90), (0.4, 150), (1, 80)], 650, vol=0.42, duty=(0.5, 0.55), vib=(4, 0.06), attack=120, release=200)
    return call + rest(80) + call


def brachio_happy():
    return voice([(0, 95), (1, 210)], 700, vol=0.38, duty=(0.5, 0.55), vib=(3, 0.04), attack=150, release=160)


# 익룡: 끼야악 (높고 날카로운 외침)
def ptero_talk():
    return voice([(0, 1500), (0.3, 2100), (1, 1150)], 360, vol=0.24, duty=(0.12, 0.2), noise=0.15, vib=(18, 0.05), attack=8)


def ptero_alert():
    one = voice([(0, 1700), (0.3, 2400), (1, 1300)], 300, vol=0.27, duty=(0.12, 0.2), noise=0.2, vib=(20, 0.06), attack=6)
    return one + rest(60) + one


def ptero_happy():
    return voice([(0, 1200), (1, 2200)], 160, vol=0.22, duty=(0.12, 0.2), vib=(16, 0.04)) + rest(30) + voice([(0, 1500), (1, 2600)], 160, vol=0.22, duty=(0.12, 0.2))


CRIES = {
    "cat": (cat_talk, cat_alert, cat_happy),
    "dog": (dog_talk, dog_alert, dog_happy),
    "lion": (lion_talk, lion_alert, lion_happy),
    "horse": (horse_talk, horse_alert, horse_happy),
    "car": (car_talk, car_alert, car_happy),
    "dragon": (dragon_talk, dragon_alert, dragon_happy),
    "plane": (plane_talk, plane_alert, plane_happy),
    "heli": (heli_talk, heli_alert, heli_happy),
    "ufo": (ufo_talk, ufo_alert, ufo_happy),
    # 10-25 추가 (뒤에 붙여서 위 캐릭터 소리는 그대로 나온다)
    "cat_white": (cat_white_talk, cat_white_alert, cat_white_happy),
    "cat_black": (cat_black_talk, cat_black_alert, cat_black_happy),
    "ghost": (ghost_talk, ghost_alert, ghost_happy),
    "pumpkin": (pumpkin_talk, pumpkin_alert, pumpkin_happy),
    "witch": (witch_talk, witch_alert, witch_happy),
    "trex": (trex_talk, trex_alert, trex_happy),
    "trike": (trike_talk, trike_alert, trike_happy),
    "stego": (stego_talk, stego_alert, stego_happy),
    "brachio": (brachio_talk, brachio_alert, brachio_happy),
    "ptero": (ptero_talk, ptero_alert, ptero_happy),
}


def main(out):
    os.makedirs(out, exist_ok=True)
    for name, fns in CRIES.items():
        for mood, fn in zip(("talk", "alert", "happy"), fns):
            save(os.path.join(out, f"cry_{name}_{mood}.wav"), rest(20) + fn() + rest(20))
    print("ok", len(CRIES) * 3)


if __name__ == "__main__":
    main(sys.argv[1])
