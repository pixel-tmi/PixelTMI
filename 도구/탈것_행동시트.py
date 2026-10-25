"""
Pixel TMI 탈것 5종 행동 시트 — 스포츠카 · 비행기 · 헬기 · UFO · 용.
앱(PetView)이 대기 동작 <act> 를 하는 동안 pet/<id>_<act>.png 가 있으면 그 칸들을 왼쪽→오른쪽으로 약 200ms마다 넘긴다.
  2장 = 반복 · 3장(한 번) = 순서대로 한 번 보여 주고 마지막 장 유지 · 잠(hoard) = 0번이 눕는 장면, 1·2번 번갈아 새근새근.
기본 모양은 탈것_도트만들기.py 를 그대로 불러 쓴다 (같은 색 · 같은 크기 · 같은 자리 · 같은 진회색 자동 외곽선).
그래서 행동에 필요한 부분(불빛·바퀴·문·턱·눈 …)만 바뀌고 나머지는 대기 시트와 한 칸도 다르지 않다.
기계의 이동·회전(루프·드리프트·지그재그 …)은 앱이 하므로, 그림은 '제 몸의 변화'만 담는다.

규칙: 한 칸 34×24 · 투명 · 오른쪽을 본다 · 좌우 1칸 여백 (x=0·33 은 비움 — 자동 검사).
  여백 때문에 기본 그림에서 깎은 칸: 스포츠카 앞 범퍼 끝 1칸 · 비행기 수평 꼬리날개 끝 1칸 · UFO 테두리 양 끝 1칸씩 ·
  헬기 로터 잔상 양 끝 · 용 주둥이 끝 1칸(꼬리 가시는 1칸 안쪽으로).
  heli_bucket 만 헬기를 4칸 위로 올려 그렸다 (스키드 아래에 줄 + 물바구니가 들어갈 자리가 24칸 안에 없어서).

사용: python 탈것_행동시트.py <출력 폴더> <미리보기.png> [--덮어쓰기]
  출력 폴더에 같은 이름 파일이 하나라도 있으면 아무것도 쓰지 않고 멈춘다 (--덮어쓰기 를 붙였을 때만 새로 씀).
출력 (이름 · 칸 수):
  car_flash 2 · car_honk 2 · car_nitro 2 · car_drift 2
  plane_touchgo 2 · plane_smoke 2
  heli_search 2 · heli_hoist 2 · heli_bucket 2
  ufo_beam 2 · ufo_alien 2 · ufo_lights 3(한 번)
  dragon_fire 3(한 번) · dragon_roar 3(한 번) · dragon_snort 2 · dragon_pearl 2 · dragon_hoard 3(0=눕기 · 1·2=새근새근)
미리보기: 줄마다 시트 하나 — 이름 · 1배/2배 실물 크기 · 6배 흰 바탕 · 6배 어두운 바탕.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import 탈것_도트만들기 as T  # noqa: E402  (기본 시트 생성기 — 색·도형·외곽선을 그대로 씀)

Cv, W, H, CLEAR, LINE, rnd, shade, alpha = T.Cv, T.W, T.H, T.CLEAR, T.LINE, T.rnd, T.shade, T.alpha

ACT_LINE = (150, 162, 186, 255)      # 음파·경적 자국 (공룡 행동 시트와 같은 회청색 — 흰 바탕·어두운 바탕 둘 다 보임)
STAR_FILL = (255, 222, 70, 255)
STAR_CORE = (255, 255, 236, 255)
LAMP = (255, 252, 236, 255)          # 켜진 등
BEAM_Y = (255, 232, 110)             # 전조등·탐조등 빛 (알파는 칸마다 — 흰 바탕에서도 보이게 노란 기)


# ══════════════════════════════════════════════════════════════════════
# 공통 도구
# ══════════════════════════════════════════════════════════════════════
def grab(fn, frame, mode, **swap):
    """기본 생성기 함수(T.car 등)를 돌리되 마지막 image() 직전의 캔버스를 그대로 받아 온다.
    swap 으로 T 안의 함수를 잠깐 바꿔 끼울 수 있다 (예: wheel=없음 → 바퀴 없는 차체만)."""
    box = {}
    real_image = T.Cv.image
    old = {k: getattr(T, k) for k in swap}

    def keep(self, dx=0, dy=0, tilt=0.0, cx=17):
        box["cv"] = self

    T.Cv.image = keep
    for k, v in swap.items():
        setattr(T, k, v)
    try:
        fn(frame, mode)
    finally:
        T.Cv.image = real_image
        for k, v in old.items():
            setattr(T, k, v)
    return box["cv"]


def moved(cv, dx=0, dy=0):
    out = Cv()
    out.paste(cv, dx, dy)
    return out


def rot_pt(p, ang, pivot):
    """점 p 를 pivot 둘레로 ang 도 회전 (+ = 화면에서 시계 방향 → 주둥이가 내려감, − = 고개를 듦)"""
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    dx, dy = p[0] - pivot[0], p[1] - pivot[1]
    return (pivot[0] + dx * ca - dy * sa, pivot[1] + dx * sa + dy * ca)


def rotated(src, ang, pivot):
    """캔버스 통째 회전 (가장 가까운 칸 뽑기 — 구멍 없이 채워짐). 외곽선은 그릴 때 자동으로 다시 둘러진다"""
    out = Cv()
    pts = [p for name in ("px", "dt", "fx") for p in getattr(src, name)]
    if not pts:
        return out
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    px0, py0 = pivot
    R = max(math.hypot(x - px0, y - py0) for x, y in pts) + 2
    for ty in range(int(py0 - R) - 1, int(py0 + R) + 2):
        for tx in range(int(px0 - R) - 1, int(px0 + R) + 2):
            dx, dy = tx - px0, ty - py0
            k = (rnd(px0 + dx * ca + dy * sa), rnd(py0 - dx * sa + dy * ca))
            for name in ("px", "dt", "fx"):
                L = getattr(src, name)
                if k in L:
                    getattr(out, name)[(tx, ty)] = L[k]
    return out


def blob(cv, cx, cy, r, core, edge, to="fx"):
    """연기·김 한 덩이 (밝은 속 + 테) — 원하는 층(fx=몸 뒤, dt=몸 앞)에"""
    L = getattr(cv, to)
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            d = math.hypot(x - cx, y - cy)
            if d <= r - 0.75:
                L[(x, y)] = core
            elif d <= r + 0.3:
                L[(x, y)] = edge


def smoke(cv, cx, cy, r, a=235, to="fx"):
    blob(cv, cx, cy, r, (246, 246, 250, a), (168, 172, 186, a), to)


def steam(cv, cx, cy, r, a=235):
    """콧김 한 덩이 (맨 앞): 흰 바탕에서도 보이게 속이 살짝 푸른 회색"""
    blob(cv, cx, cy, r, (236, 240, 248, a), (150, 158, 178, a), "dt")


def marks(cv, cx, cy, r, a0, a1, n=3, ln=2, col=ACT_LINE):
    """중심에서 바깥으로 뻗는 짧은 선 n개 (경적·포효 음파). 외곽선 없는 맨 앞(dt) 층"""
    for k in range(n):
        a = math.radians(a0 + (a1 - a0) * k / max(1, n - 1))
        x0, y0 = cx + r * math.cos(a), cy + r * math.sin(a)
        x1, y1 = cx + (r + ln - 1) * math.cos(a), cy + (r + ln - 1) * math.sin(a)
        cv.line(rnd(x0), rnd(y0), rnd(x1), rnd(y1), col, to="dt")


def sparkle(cv, cx, cy, big=False):
    """반짝 (+): 노란 네 갈래 + 하얀 속. 큰 것은 갈래가 2칸"""
    for k in ((1, 2) if big else (1,)):
        for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            cv.dt[(cx + dx, cy + dy)] = STAR_FILL if k == 1 else alpha(STAR_FILL, 170)
    cv.dt[(cx, cy)] = STAR_CORE


def render(cv, dy=0, tilt=0.0, cx=17):
    """여백 자르기 → 그리기. 효과(dt·fx)는 x=1..32 밖을 버리고, 몸(px)은 x=2..31 밖이면 오류 (외곽선이 x=0·33 에 닿으므로)"""
    for name in ("dt", "fx"):
        L = getattr(cv, name)
        for p in [p for p in L if not (1 <= p[0] <= W - 2)]:
            del L[p]
    bad = sorted(p for p in cv.px if not (2 <= p[0] <= W - 3))
    if bad:
        raise ValueError(f"좌우 여백 침범 (몸 칸): {bad[:8]}")
    return cv.image(0, dy, tilt, cx)


def check_margin(name, frames):
    for k, f in enumerate(frames):
        a = f.getchannel("A")
        hit = [(x, y) for x in (0, W - 1) for y in range(H) if a.getpixel((x, y))]
        if hit:
            raise ValueError(f"{name} 프레임 {k}: 좌우 여백 침범 {hit[:6]}")


# ══════════════════════════════════════════════════════════════════════
# 스포츠카
# ══════════════════════════════════════════════════════════════════════
def car_body():
    """대기 시트 0번과 같은 차체 (바퀴 없이). 앞 범퍼 끝 1칸만 깎아 오른쪽 여백을 만든다"""
    b = grab(T.car, 0, "idle", wheel=lambda *a, **k: None)
    for y in (16, 17, 18):
        b.px.pop((32, y), None)
    b.dt.pop((32, 18), None)
    return b


TREAD = (112, 114, 128, 255)


def turned_wheel(cv, cx, cy):
    """꺾인 앞바퀴: 바퀴가 비스듬히 돌아 폭이 좁아 보이고(휠집 안쪽 어둠이 드러남),
    휠은 세로로 긴 타원 · 앞쪽에 타이어 접지면의 밝은 홈 무늬가 보인다"""
    cv.ellipse(cx + 0.5, cy, 2.55, 3.45, T.TIRE)
    cv.ellipse(cx - 0.4, cy, 1.0, 2.2, T.RIM, to="dt")
    for y in (cy - 2, cy, cy + 2):
        cv.dt[(cx, y)] = T.SPOKE
    cv.dt[(cx - 1, cy - 1)] = T.SPOKE; cv.dt[(cx - 1, cy + 1)] = T.SPOKE
    cv.dt[(cx, cy)] = T.REDL
    for y in range(cy - 3, cy + 4):                       # 접지면 홈 (밝은 줄 · 어두운 줄 번갈아)
        cv.dt[(cx + 2, y)] = TREAD if (y - cy) % 2 == 0 else (64, 64, 74, 255)
    cv.dt[(cx + 2, cy - 3)] = (84, 84, 96, 255)


def car_frame(body, tilt=0.0, front="normal", step=0, rot=0.0):
    cv = Cv()
    if rot:                                              # 차체만 뒷바퀴 축 둘레로 살짝 돌림 (− = 앞이 들림) — 바퀴는 땅에 그대로
        body = rotated(body, rot, (9, 19))
    cv.paste(body, 0, 0, tilt=tilt, cx=9)
    T.wheel(cv, 9, 19, step)
    if front == "turn":
        turned_wheel(cv, 27, 19)
    else:
        T.wheel(cv, 27, 19, step)
    return cv


def car_flash(i):
    """상향등: 0 = 전조등이 하얗게 번쩍 — 앞모서리가 환해지고 앞으로 빛이 뻗고 빛살이 반짝 · 1 = 꺼짐(평소)"""
    cv = car_frame(car_body())
    if i == 0:
        for (x, y) in list(cv.px):                       # 앞모서리가 불빛에 물듦
            d = math.hypot(x - 30, y - 15.5)
            if d <= 2.7 and cv.px[(x, y)] in (T.RED, T.RED_DK):
                cv.dt[(x, y)] = BEAM_Y + (130 if d > 1.6 else 190,)
        for p in ((29, 15), (30, 15), (31, 16), (30, 16)):
            cv.dt[p] = LAMP
        for y, a in zip(range(13, 19), (110, 190, 250, 250, 190, 110)):   # 앞으로 뻗는 빛 (그림 끝까지)
            cv.dt[(32, y)] = BEAM_Y + (a,)
        cv.dt[(31, 15)] = BEAM_Y + (255,); cv.dt[(31, 14)] = BEAM_Y + (200,)
        cv.dt[(31, 12)] = alpha(STAR_FILL, 200); cv.dt[(32, 11)] = alpha(STAR_FILL, 150)   # 위로 빛살
        sparkle(cv, 29, 11)
        cv.dt[(26, 9)] = alpha(STAR_FILL, 140)
    return render(cv)


def car_honk(i):
    """경적: 0 = 차체가 살짝 눌림(창이 한 줄로 납작) + 앞에서 음파 3줄 · 1 = 원래 높이 + 음파가 바깥으로 퍼짐"""
    b = car_body()
    if i == 0:                                           # 유리 아랫줄(13)을 빼고 그 위를 1칸 내림 → 지붕이 1칸 낮아짐
        for name in ("px", "dt", "fx"):
            L = getattr(b, name)
            new = {}
            for (x, y), c in L.items():
                if y == 13:
                    continue
                new[(x, y + 1 if y < 13 else y)] = c
            setattr(b, name, new)
    cv = car_frame(b)
    if i == 0:                                           # 보닛 앞끝 위로 부채꼴 음파 (안쪽)
        for seg in (((26, 11), (26, 10)), ((29, 11), (30, 10)), ((31, 13), (32, 12))):
            cv.line(*seg[0], *seg[1], ACT_LINE, to="dt")
        cv.dt[(31, 16)] = LAMP                            # 경적 누르면 전조등도 살짝
    else:                                                # 바깥으로 퍼짐
        for seg in (((25, 8), (25, 7)), ((29, 8), (30, 7)), ((32, 10), (32, 9))):
            cv.line(*seg[0], *seg[1], ACT_LINE, to="dt")
    return render(cv)


NITRO = [(255, 255, 255, 255), (196, 240, 255, 255), (110, 196, 255, 240), (60, 120, 255, 190), (60, 120, 255, 110)]


def car_nitro(i):
    """니트로: 머플러에서 파랗고 하얀 불꽃이 펑 · 차체는 앞이 들리며 뒤로 젖혀짐(뒤가 눌림)"""
    cv = car_frame(car_body(), rot=-4.0 if i == 0 else -3.0, step=i * 2)
    c0, c1, c2, c3, c4 = NITRO
    if i == 0:                                           # 크게 펑
        flame = {(2, 19): c0, (1, 19): c1, (2, 18): c1, (2, 20): c1, (1, 18): c2, (1, 20): c2,
                 (3, 20): c2, (1, 17): c3, (1, 21): c3, (2, 21): c3, (2, 17): c3, (3, 21): c4}
    else:                                                # 작게 일렁
        flame = {(2, 19): c1, (1, 19): c2, (2, 18): c3, (2, 20): c2, (1, 20): c3, (3, 20): c3}
    for p, c in flame.items():
        cv.dt[p] = c
    cv.dt[(3, 19)] = (190, 230, 255, 255); cv.dt[(4, 19)] = (150, 200, 240, 255)   # 머플러 끝이 달아오름
    for p in ((4, 15), (5, 15), (4, 16)):                # 테일램프 환하게
        cv.dt[p] = (255, 170, 170, 255)
    return render(cv)


def car_drift(i):
    """드리프트: 앞바퀴가 꺾임 · 뒷바퀴에서 타이어 연기가 뭉게뭉게 (0·1 이 번갈아 피어오름)"""
    cv = car_frame(car_body(), front="turn", step=i * 3)
    if i == 0:
        smoke(cv, 4.6, 20.4, 2.3, 225)
        smoke(cv, 2.6, 16.9, 1.7, 150)
        smoke(cv, 7.6, 22.2, 1.4, 245, to="dt")          # 타이어 바닥 앞을 덮는 연기
        smoke(cv, 11.2, 22.6, 0.9, 220, to="dt")
    else:
        smoke(cv, 3.6, 19.6, 2.5, 200)
        smoke(cv, 2.4, 15.6, 1.4, 110)
        smoke(cv, 6.4, 21.9, 1.7, 240, to="dt")
        smoke(cv, 10.4, 22.7, 1.0, 230, to="dt")
    return render(cv)


# ══════════════════════════════════════════════════════════════════════
# 비행기 (프로펠러가 도는 걷기 0·2번 그림을 바탕으로)
# ══════════════════════════════════════════════════════════════════════
def plane_base(f):
    cv = grab(T.plane, f, "walk")
    cv.px.pop((1, 12), None)                              # 수평 꼬리날개 끝 1칸 (왼쪽 여백)
    return cv


def landing_gear(cv):
    """바퀴 내림: 주날개 아래 주바퀴 + 기수 아래 앞바퀴 (은색 다리 + 검은 타이어 + 휠)"""
    for y in range(17, 20):
        cv.put(19, y, T.HUB)
    for y in range(16, 20):
        cv.put(26, y, T.HUB)
    for wx in (19, 26):
        cv.ellipse(wx, 21, 1.5, 1.5, T.TIRE)
        cv.dt[(wx, 21)] = T.HUB
        cv.dt[(wx - 1, 20)] = (84, 84, 94, 255)


def plane_touchgo(i):
    """터치앤고: 바퀴를 내림 · 1 = 바퀴가 활주로에 닿아 작은 연기"""
    cv = plane_base(0 if i == 0 else 2)
    landing_gear(cv)
    if i == 1:
        smoke(cv, 16.3, 22.0, 1.6, 235)
        smoke(cv, 13.6, 21.2, 1.2, 170)
        smoke(cv, 23.6, 22.4, 1.0, 210)
    return render(cv)


SMOKE_COLS = [((248, 164, 192), (214, 110, 150)), ((92, 196, 252), (40, 140, 214)), ((252, 214, 70), (214, 160, 30))]


def plane_smoke(i):
    """에어쇼 색 연기: 꼬리 밑 연기통에서 무지개 연기 줄기(분홍→노랑→하늘)가 뒤로 흘러내림.
    덩이가 서로 겹쳐 한 줄기로 보이게 · 0·1 이 줄기가 살랑 흔들리며 흘러감"""
    cv = plane_base(0 if i == 0 else 2)
    cv.put(4, 14, T.STEEL)                                # 연기통
    w = [0, 0.5, 0.8, 0.4, -0.3] if i == 0 else [0, -0.3, -0.2, 0.5, 0.9]
    seq = [(3.4, 15.4, 1.0), (2.7, 16.9, 1.25), (2.6, 18.6, 1.5), (3.1, 20.4, 1.75), (4.2, 22.1, 1.9)]
    cols = [SMOKE_COLS[0], SMOKE_COLS[0], SMOKE_COLS[2], SMOKE_COLS[1], SMOKE_COLS[1]]
    for k in range(len(seq) - 1, -1, -1):                # 아래(오래된 연기)부터 깔고 위를 덮음
        x, y, r = seq[k]
        core, edge = cols[k]
        a = 250 if k < 3 else 215 if k == 3 else 170
        blob(cv, x + w[k], y, r, core + (a,), edge + (a,), to="fx")
    cv.fx[(3, 14)] = SMOKE_COLS[0][0] + (255,)           # 연기통 입구
    return render(cv)


# ══════════════════════════════════════════════════════════════════════
# 헬기 (로터가 도는 걷기 0·2번 그림을 바탕으로)
# ══════════════════════════════════════════════════════════════════════
CABLE = (176, 180, 194, 255)
CREW_SUIT = (255, 120, 40, 255)


def heli_base(f):
    return grab(T.heli, f, "walk")


def heli_search(i):
    """탐조등: 기수 아래 등이 켜지고 빛줄기가 앞아래로 — 0·1 이 살짝 훑음"""
    cv = heli_base(0 if i == 0 else 2)
    cv.rect(26, 18, 28, 18, T.STEEL)                      # 탐조등 몸통
    cv.put(28, 19, T.STEEL)
    cv.dt[(28, 18)] = LAMP; cv.dt[(28, 19)] = BEAM_Y + (255,)
    if i == 0:                                           # 앞아래로 비스듬히
        beam = {(29, 19): 235, (30, 19): 170, (29, 20): 220, (30, 20): 205, (31, 20): 140,
                (30, 21): 190, (31, 21): 170, (32, 21): 110, (31, 22): 150, (32, 22): 130, (32, 23): 100, (31, 23): 80}
    else:                                                # 더 아래로
        beam = {(29, 19): 235, (29, 20): 225, (30, 20): 170, (28, 20): 120, (29, 21): 205, (30, 21): 185,
                (28, 21): 110, (29, 22): 165, (30, 22): 160, (31, 22): 110, (28, 22): 90, (29, 23): 130, (30, 23): 130, (31, 23): 90}
    for p, a in beam.items():
        cv.dt[p] = BEAM_Y + (min(255, a + 25),)
    return render(cv)


def heli_hoist(i):
    """구조 윈치: 옆문이 열려 구조대원이 보이고, 문 위 윈치 팔이 나와 줄이 아래로 — 끝 갈고리가 살랑"""
    cv = heli_base(0 if i == 0 else 2)
    cv.rect(17, 11, 20, 14, (40, 42, 54, 255), to="dt")   # 열린 문 (어두운 실내)
    for y in range(10, 16):
        cv.dt[(16, y)] = T.Y_DK                           # 문틀
    cv.dt[(17, 15)] = T.Y_DK; cv.dt[(18, 15)] = T.Y_DK; cv.dt[(19, 15)] = T.Y_DK; cv.dt[(20, 15)] = T.Y_DK
    cv.dt[(19, 12)] = T.WHITE; cv.dt[(20, 12)] = T.WHITE  # 구조대원: 흰 헬멧 · 고글 · 주황 옷
    cv.dt[(20, 13)] = T.GLASS_DK; cv.dt[(19, 13)] = (250, 214, 180, 255)
    cv.dt[(19, 14)] = CREW_SUIT; cv.dt[(20, 14)] = CREW_SUIT
    cv.put(18, 8, T.STEEL)                                 # 윈치 팔: 문 위 기둥(진회색) + 밖으로 뻗은 팔·도르래(밝은 은색)
    cv.put(16, 8, T.HUB); cv.put(17, 8, T.HUB); cv.put(16, 9, T.HUB)
    cv.dt[(16, 9)] = T.SPOKE
    sway = 0 if i == 0 else 1
    for y in range(10, 21):                                # 줄
        cv.dt[(16 if y < 17 else 16 - (sway if y >= 19 else 0), y)] = CABLE
    hx = 16 - sway
    cv.put(hx, 21, T.REDL); cv.put(hx, 22, T.REDL); cv.put(hx + 1, 22, T.REDL)   # 갈고리 (빨강)
    cv.dt[(hx, 21)] = (255, 120, 110, 255)
    return render(cv)


BUCKET = (255, 143, 0, 255)
BUCKET_DK = (206, 100, 10, 255)
WATER = (90, 190, 255, 255)
WATER_HI = (200, 236, 255, 255)


def heli_bucket(i):
    """산불 물바구니: 배 아래 갈고리에 짧은 줄 + 주황 물바구니 (물이 찰랑, 물방울이 똑) — 헬기는 4칸 위로"""
    cv = moved(heli_base(0 if i == 0 else 2), 0, -4)
    sw = 0 if i == 0 else 1                               # 바구니가 살짝 흔들림
    cv.put(21, 16, T.STEEL)                               # 갈고리 (배 아래, 경광등 옆)
    cv.dt[(21, 17)] = CABLE; cv.dt[(21, 18)] = CABLE; cv.dt[(21 + sw, 19)] = CABLE
    bx = 21 + sw
    cv.rect(bx - 2, 21, bx + 2, 21, BUCKET)               # 물바구니: 위가 넓은 통
    cv.rect(bx - 1, 22, bx + 1, 22, BUCKET)
    cv.dt[(bx - 1, 21)] = WATER; cv.dt[(bx, 21)] = WATER_HI if i == 0 else WATER; cv.dt[(bx + 1, 21)] = WATER
    cv.dt[(bx - 2, 21)] = BUCKET_DK
    cv.dt[(bx + 1, 22)] = BUCKET_DK
    cv.dt[(bx - 2, 20)] = CABLE; cv.dt[(bx + 2, 20)] = CABLE   # 바구니 고리줄
    cv.dt[(bx - 1, 20)] = CABLE; cv.dt[(bx + 1, 20)] = CABLE
    cv.dt[(bx, 20)] = CABLE
    drop = (bx + 3, 22) if i == 0 else (bx - 3, 23)       # 물방울
    cv.dt[drop] = WATER
    return render(cv)


# ══════════════════════════════════════════════════════════════════════
# UFO
# ══════════════════════════════════════════════════════════════════════
LIGHT_X = (2, 6, 10, 14, 18, 22, 26, 30)


def ufo_base(f, mode="walk"):
    cv = grab(T.ufo, f, mode)
    for x in (1, 32):                                     # 테두리 양 끝 1칸 (좌우 여백)
        cv.px.pop((x, 15), None)
        cv.dt.pop((x, 15), None)
    return cv


def rim_light(cv, i, col, lv):
    """테두리 불빛 하나: lv 2=환하게(+위로 번짐) · 1=은은 · 0=꺼짐"""
    x = LIGHT_X[i]
    if lv == 2:
        cv.dt[(x, 15)] = col + (255,)
        cv.dt[(x + 1, 15)] = tuple(min(255, v + 90) for v in col) + (255,)
        cv.dt[(x, 14)] = col + (150,); cv.dt[(x + 1, 14)] = col + (150,)
        cv.dt[(x, 16)] = col + (120,); cv.dt[(x + 1, 16)] = col + (120,)
    elif lv == 1:
        c = shade(col + (255,), 0.72)
        cv.dt[(x, 15)] = c; cv.dt[(x + 1, 15)] = c
    else:
        cv.dt[(x, 15)] = (62, 68, 86, 255); cv.dt[(x + 1, 15)] = (62, 68, 86, 255)


def ufo_beam(i):
    """견인 빔: 배 밑 해치가 열려 환하게 · 빔이 아래로 퍼지기 시작 (빛 알갱이가 빨려 올라감)"""
    cv = ufo_base(0 if i == 0 else 2)
    for p in [p for p in cv.fx if p[1] >= 20]:
        del cv.fx[p]
    cv.rect(12, 19, 21, 19, T.M_DK)                       # 해치 테 (넓게 열림)
    cv.rect(13, 19, 20, 19, T.BEAM, to="dt")
    cv.dt[(15, 19)] = T.GLINT; cv.dt[(16, 19)] = T.GLINT; cv.dt[(17, 19)] = T.GLINT
    cv.dt[(12, 19)] = shade(T.BEAM, 0.7); cv.dt[(21, 19)] = shade(T.BEAM, 0.7)
    for y, (x0, x1), a in ((20, (12, 21), 200), (21, (11, 22), 150), (22, (10, 23), 110), (23, (9, 24), 75)):
        for x in range(x0, x1 + 1):
            edge = x in (x0, x1)
            cv.dt[(x, y)] = alpha(T.BEAM, int(a * (0.6 if edge else 1.0)))
    for x in (14, 19) if i == 0 else (16, 17):            # 빔 속 밝은 줄기
        for y in (20, 21, 22):
            cv.dt[(x, y)] = alpha(T.GLINT, 200 - (y - 20) * 40)
    for p in (((12, 22), (21, 21)) if i == 0 else ((13, 21), (20, 23))):   # 빛 알갱이
        cv.dt[p] = T.GLINT
    return render(cv)


ALIEN_PAL = {"g": T.ALIEN, "e": T.EYE, "w": T.GLINT, "m": (200, 70, 110, 255), "d": shade(T.ALIEN, 0.75)}
ANT_BALL = (255, 120, 180, 255)


def ufo_alien(i):
    """돔 꼭대기 해치가 퐁 열리고 꼬마 외계인이 고개를 쏙 · 1 = 손을 흔듦"""
    cv = ufo_base(0, "idle")
    for (x, y) in list(cv.dt):                            # 돔 속 외계인 지우기 → 빈 유리
        if 5 <= y <= 12 and 12 <= x <= 21 and (x, y) in cv.px and cv.px[(x, y)] == T.GLASS:
            cv.dt[(x, y)] = T.GLASS_DK if x >= 21 else T.GLASS
    for p in ((12, 7), (11, 8), (11, 9), (13, 6)):        # 돔 반짝 되살리기
        cv.dt[p] = T.GLINT
    for x in range(13, 21):                               # 안테나 자리도 유리로
        for y in (5, 6):
            if (x, y) in cv.px:
                cv.dt[(x, y)] = T.GLASS
    thru, thru_dk = (136, 214, 178, 255), (104, 178, 150, 255)   # 유리 너머로 비치는 외계인 몸 (초록 + 유리 하늘색)
    cv.rect(16, 7, 17, 8, thru, to="dt")                  # 목
    cv.rect(15, 9, 18, 12, thru, to="dt")                 # 몸통 (어깨 둥글게)
    cv.dt[(15, 9)] = T.GLASS; cv.dt[(18, 9)] = T.GLASS
    cv.dt[(15, 12)] = thru_dk; cv.dt[(18, 12)] = thru_dk; cv.dt[(18, 10)] = thru_dk; cv.dt[(18, 11)] = thru_dk
    cv.rect(14, 5, 19, 6, (60, 70, 96, 255), to="dt")     # 열린 해치 구멍
    # 해치 뚜껑: 왼쪽 경첩에 매달려 비스듬히 젖혀짐
    for p in ((11, 4), (12, 4), (12, 3), (13, 3), (13, 2)):
        cv.put(*p, T.M_)
    cv.dt[(12, 3)] = T.M_HI; cv.dt[(13, 2)] = T.M_HI
    # 외계인 머리 (해치 위로 쏙)
    up = 0 if i == 0 else 1
    rows = ["..gggg..",
            ".gggggg.",
            "gweggweg",
            "geeggeeg",
            ".gmmmmg." if i == 1 else ".ggmmgg."]
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch != ".":
                cv.put(13 + dx, 1 + dy - up, ALIEN_PAL["g"])
    cv.art(13, 1 - up, rows, ALIEN_PAL)
    cv.dt[(15, 0 - up)] = ANT_BALL; cv.dt[(18, 0 - up)] = ANT_BALL
    if i == 1:                                           # 손 흔들기 (오른손 번쩍)
        for p in ((21, 3), (22, 2), (22, 1), (23, 1), (23, 0)):
            cv.put(*p, T.ALIEN)
        cv.dt[(23, 0)] = shade(T.ALIEN, 1.15)
        marks(cv, 23, 1, 2, -40, 20, n=2, ln=1)
    else:
        cv.put(21, 4, T.ALIEN)                            # 해치 테를 잡은 손
    return render(cv)


def ufo_lights(i):
    """미지와의 조우: 테두리 불빛이 왼쪽부터 색색으로 차례차례 켜짐 → 2 = 모두 환하게 (마지막 장 유지)"""
    cv = ufo_base(0, "idle")
    lit = [range(0, 3), range(3, 6), range(0, 8)][i]
    for k in range(8):
        col = T.LIGHTS[k % len(T.LIGHTS)]
        if k in lit:
            lv = 2
        elif i == 1 and k < 3:
            lv = 1
        else:
            lv = 0
        rim_light(cv, k, col, lv)
    cv.dt[(16, 19)] = T.GLINT
    if i == 2:                                           # 전부 켜지면 위로 반짝
        sparkle(cv, 5, 10)
        sparkle(cv, 28, 9)
        cv.dt[(2, 12)] = alpha(STAR_FILL, 160); cv.dt[(31, 12)] = alpha(STAR_FILL, 160)
    # 외계인도 신나서 입을 동그랗게
    if i >= 1:
        cv.dt[(15, 11)] = (200, 70, 110, 255); cv.dt[(16, 11)] = (200, 70, 110, 255)
        cv.dt[(17, 11)] = (200, 70, 110, 255); cv.dt[(18, 11)] = (200, 70, 110, 255)
    return render(cv)


# ══════════════════════════════════════════════════════════════════════
# 용 (주황 꼬마 용) — 탈것_도트만들기.dragon 과 같은 도형을 관절별로 움직일 수 있게 다시 조립
# ══════════════════════════════════════════════════════════════════════
G, G_HI, G_DK = T.G, T.G_HI, T.G_DK
BELLY, BELLY_DK, MEMB, SPIKE, HORN, BLUSH = T.BELLY, T.BELLY_DK, T.MEMB, T.SPIKE, T.HORN, T.BLUSH
EYE, GLINT = T.EYE, T.GLINT
MOUTH = (150, 40, 56, 255)
TONGUE = (240, 118, 138, 255)
TOOTH = (252, 250, 240, 255)
FIRE = [(255, 252, 228, 255), (255, 226, 86, 255), (255, 160, 40, 255), (234, 70, 40, 255)]
PEARL = (255, 222, 104, 255)
PEARL_HI = (255, 250, 214, 255)
PEARL_DK = (226, 152, 28, 255)
COIN = (240, 180, 30, 255)          # coin_spin.png 와 같은 금색
COIN_HI = (252, 214, 70, 255)
COIN_DK = (200, 136, 20, 255)
COIN_SHINE = (255, 250, 210, 255)
HEAD_PIVOT = (20.5, 12.0)           # 목 밑동 — 고개를 들거나 숙일 때 돌리는 축


def wing_cv(w, sx=14, sy=11):
    """T.wing 과 같은 그림 (어깨 위치를 옮길 수 있게). w = {'wr','f','r'} 또는 자세 번호"""
    if isinstance(w, int):
        w = T.WINGS[w]
    cv = Cv()
    wr, fs, r = w["wr"], w["f"], w["r"]
    pts = [(sx, sy), wr]
    for i, f in enumerate(fs):
        pts.append(f)
        nxt = fs[i + 1] if i + 1 < len(fs) else r
        mx, my = (f[0] + nxt[0]) / 2, (f[1] + nxt[1]) / 2
        pts.append((mx + (wr[0] - mx) * 0.3, my + (wr[1] - my) * 0.3))
    pts.append(r)
    cv.poly(pts, MEMB)
    cv.line(sx, sy, wr[0], wr[1], G)
    cv.line(sx + 1, sy, wr[0] + 1, wr[1], G)
    for f in fs:
        cv.line(wr[0], wr[1], f[0], f[1], shade(MEMB, 0.8), to="dt")
    for (x, y) in list(cv.px):
        if cv.px[(x, y)] == G and (x, y - 1) not in cv.px:
            cv.dt[(x, y)] = G_HI
    cv.put(wr[0], wr[1] - 1, HORN)
    return cv


# 벌린 입 (머리 기본 자리 기준, 11번 줄부터 아래로 · x=23 부터): G=살 · M=입 속 · n=혀 · T=이빨 · '.'=비움 · ' '=그대로
# 윗입술(10번 줄)은 그대로 두고 아래턱이 내려가며 입 속이 드러난다
MOUTHS = {
    "s": ["    MMMMM.",          # 11  살짝: 가는 틈
          "  GGGGGG..",          # 12  아래턱
          ],
    "m": ["   GMMMTM.",          # 11  반쯤: 윗니 하나
          "   GMMnM..",          # 12  혀
          "  GGGGGG..",          # 13  아래턱
          ],
    "l": ["   GMMMTM.",          # 11  크게: 윗니
          "  GMMMMM..",          # 12
          "  GMMnnT..",          # 13  혀 + 아랫니
          "  GGGGGG..",          # 14  아래턱
          "   GGGG...",          # 15  턱 끝
          ],
}
MOUTH_COL = {"G": None, "M": MOUTH, "n": TONGUE, "T": TOOTH}


def head_cv(mouth=None, cheeks=False):
    """머리 (기본 자리 기준): 큰 머리 + 주둥이(끝 1칸 깎음) + 뿔. mouth = None(다문 입) · 's' · 'm' · 'l'"""
    h = Cv()
    h.ellipse(24.5, 8.2, 6.2, 5.0, G)
    h.ellipse(29.4, 9.8, 2.55, 2.1, G)
    for p in ((21, 3), (20, 2), (26, 3), (26, 2)):
        h.put(*p, HORN)
    if cheeks:                                            # 숨 들이마셔 볼이 빵빵 (아래로 둥글게 부풂)
        h.ellipse(26.4, 11.8, 2.8, 2.3, G)
    if mouth:
        for dy, row in enumerate(MOUTHS[mouth]):
            for dx, ch in enumerate(row):
                p = (23 + dx, 11 + dy)
                if ch == ".":
                    h.px.pop(p, None)
                elif ch != " ":
                    h.px[p] = MOUTH_COL[ch] or G
    return h


def put_eye(cv, ex, ey, kind="normal"):
    """눈 (ex,ey = 기본 2×3 눈의 왼쪽 위)"""
    if kind == "normal":
        cv.rect(ex, ey, ex + 1, ey + 2, EYE, to="dt")
        cv.dt[(ex, ey)] = GLINT; cv.dt[(ex + 1, ey + 2)] = (70, 84, 120, 255)
    elif kind == "wide":                                  # 동그랗게 뜬 눈 (흰자 테)
        cv.rect(ex, ey, ex + 1, ey + 2, EYE, to="dt")
        cv.dt[(ex, ey)] = GLINT
        cv.dt[(ex - 1, ey)] = G_DK
        cv.dt[(ex + 2, ey - 1)] = G_DK; cv.dt[(ex + 1, ey - 1)] = G_DK
    elif kind == "squeeze":                               # 질끈 ( > )
        cv.dt[(ex, ey)] = EYE; cv.dt[(ex + 1, ey + 1)] = EYE; cv.dt[(ex, ey + 2)] = EYE
    elif kind == "fierce":                                # 힘준 눈 + 앞으로 내려간 눈썹
        cv.rect(ex, ey + 1, ex + 1, ey + 2, EYE, to="dt")
        cv.dt[(ex, ey + 1)] = GLINT
        cv.dt[(ex - 1, ey - 1)] = LINE; cv.dt[(ex, ey - 1)] = LINE; cv.dt[(ex + 1, ey)] = LINE; cv.dt[(ex + 2, ey)] = LINE
    elif kind == "squint":                                # 실눈 (흥!): 무거운 눈꺼풀 선 밑으로 가는 눈동자 한 줄
        for x in range(ex - 1, ex + 3):
            cv.dt[(x, ey + 1)] = LINE
        cv.dt[(ex, ey + 2)] = EYE; cv.dt[(ex + 1, ey + 2)] = EYE
    elif kind == "happy":                                 # 웃는 눈 ( ^ )
        cv.dt[(ex - 1, ey + 2)] = EYE; cv.dt[(ex, ey + 1)] = EYE; cv.dt[(ex + 1, ey + 1)] = EYE; cv.dt[(ex + 2, ey + 2)] = EYE
    elif kind == "half":                                  # 졸린 눈 (눈꺼풀이 반쯤)
        cv.rect(ex, ey + 1, ex + 1, ey + 2, EYE, to="dt")
        cv.dt[(ex + 1, ey + 2)] = (70, 84, 120, 255)
        for x in range(ex - 1, ex + 3):
            cv.dt[(x, ey + 1 if x in (ex, ex + 1) else ey + 2)] = G_DK if x not in (ex, ex + 1) else cv.dt[(x, ey + 1)]
        cv.dt[(ex - 1, ey + 1)] = G_DK; cv.dt[(ex, ey)] = G_DK; cv.dt[(ex + 1, ey)] = G_DK; cv.dt[(ex + 2, ey + 1)] = G_DK
    elif kind == "sleep":                                 # 감은 눈 (가로 선)
        for x in range(ex - 1, ex + 3):
            cv.dt[(x, ey + 2)] = EYE


def dragon_cv(pose=3, sway=0, head=None, arms="rest", belly=1.0, legs="hang"):
    """선 자세 용. head = dict(dx, dy, ang, cheeks, eye, mouth). pose = 날개 자세(번호 또는 dict)
    mouth: smile(기본) · tight(꾹) · grin(활짝, 혀) · s · m · l (벌린 입: 살짝 · 반 · 크게)"""
    hd = dict(dx=0, dy=0, ang=0.0, cheeks=False, eye="normal", mouth="smile")
    hd.update(head or {})
    open_ = hd["mouth"] if hd["mouth"] in MOUTHS else None
    cv = Cv()
    tail = [(9, 16, 2.3), (6.4, 16.6, 1.8), (4.3, 15.8, 1.4), (2.9, 14.2 + sway * 0.6, 1.1)]
    for x, y, r in tail:
        cv.ellipse(x, y, r, r, G)
    cv.art(2, 11 + sway, [".s.", "sss", ".s."], {"s": SPIKE}, to="px")      # 꼬리 끝 가시 (1칸 안쪽)
    cv.ellipse(14.5, 15.2, 6.4, 4.6 * belly, G)
    cv.rect(18, 10, 21, 14, G)
    cv.ellipse(22.0, 12.6, 2.4, 2.0, G)                   # 목 앞(멱) — 고개를 들어도 틈이 안 생기게
    if legs == "hang":
        cv.ellipse(11.5, 17.6, 2.6, 2.2, G)
        cv.rect(10, 19, 12, 20, G)
        cv.rect(18, 18, 19, 20, G)
    if arms == "rest":
        cv.put(21, 15, G); cv.put(21, 16, G)
    # 머리 (돌리고 옮겨서 얹기)
    hc = head_cv(open_, hd["cheeks"])
    if hd["ang"]:
        hc = rotated(hc, hd["ang"], HEAD_PIVOT)
    hc = moved(hc, hd["dx"], hd["dy"])
    cv.px.update(hc.px)
    cv.dt.update(hc.dt)
    # 등 가시
    tops = {}
    for (x, y) in cv.px:
        tops[x] = min(tops.get(x, 99), y)
    for x in (10, 13, 16, 6):
        if cv.px.get((x, tops[x])) == G:
            cv.put(x, tops[x] - 1, SPIKE)
    # 무늬: 배 비늘 · 광택 · 그늘
    cv.ellipse(17, 16.2, 3.7, 2.7, BELLY, to="dt", keep=lambda x, y: (x, y) in cv.px and cv.px[(x, y)] == G)
    for (x, y) in list(cv.dt):
        if cv.dt[(x, y)] == BELLY and y in (15, 17) and (x + 1, y) in cv.dt:
            cv.dt[(x, y)] = BELLY_DK
    cv.top_light(G_HI, skip=(SPIKE, HORN, MOUTH, TONGUE, TOOTH), x0=18 + hd["dx"] - 2, x1=31)
    for (x, y) in list(cv.px):
        if cv.px[(x, y)] == G and (x, y + 1) not in cv.px and (x, y) not in cv.dt:
            cv.dt[(x, y)] = G_DK
    if legs == "hang":
        cv.dt[(10, 20)] = HORN; cv.dt[(12, 20)] = HORN; cv.dt[(19, 20)] = HORN
    # 얼굴 (머리와 같이 돌린 자리에)
    def at(p):
        q = rot_pt(p, hd["ang"], HEAD_PIVOT) if hd["ang"] else p
        return rnd(q[0] + hd["dx"]), rnd(q[1] + hd["dy"])
    ex, ey = at((25, 7))
    put_eye(cv, ex, ey, hd["eye"])
    for p in ((23, 10), (24, 10)):
        cv.dt[at(p)] = BLUSH
    if hd["cheeks"]:
        for p in ((25, 11), (26, 11), (25, 12)):
            cv.dt[at(p)] = BLUSH
    cv.dt[at((31, 9))] = G_DK                              # 콧구멍
    if not open_:
        if hd["mouth"] == "smile":
            for p in ((28, 11), (29, 11), (27, 10)):
                cv.dt[at(p)] = G_DK
        elif hd["mouth"] == "tight":                       # 꾹 다문 입
            for p in ((28, 11), (29, 11), (30, 11)):
                cv.dt[at(p)] = G_DK
        elif hd["mouth"] == "grin":                        # 활짝 웃는 입 (혀)
            for p in ((27, 10), (28, 11), (29, 11), (30, 10)):
                cv.dt[at(p)] = G_DK
            cv.dt[at((28, 12))] = MOUTH; cv.dt[at((29, 12))] = TONGUE
            cv.px[at((28, 12))] = G; cv.px[at((29, 12))] = G
    cv.overlay(wing_cv(pose))
    return cv


def flame(cv, x0, y0, x1, h1, phase=0):
    """불꽃 브레스: 입(x0,y0)에서 x1 까지 퍼지는 원뿔. 속은 하얀 노랑 → 노랑 → 주황 → 빨강, 끝은 들쭉날쭉"""
    n = max(1, x1 - x0)
    for x in range(x0, x1 + 1):
        t = (x - x0) / n
        hh = 0.7 + (h1 - 0.7) * t
        for y in range(int(y0 - hh) - 1, int(y0 + hh) + 2):
            d = abs(y - y0) / hh
            if d > 1.05:
                continue
            k = d * 0.75 + t * 0.45
            if (x + y + phase) % 3 == 0 and d > 0.75:      # 들쭉날쭉한 가장자리
                continue
            col = FIRE[0] if k < 0.32 else FIRE[1] if k < 0.62 else FIRE[2] if k < 0.88 else FIRE[3]
            cv.dt[(x, y)] = col


def head_at(hd, p):
    """머리 기본 자리의 점 p 가 고개 돌림·옮김 뒤 어디에 오는지"""
    q = rot_pt(p, hd.get("ang", 0), HEAD_PIVOT) if hd.get("ang") else p
    return q[0] + hd.get("dx", 0), q[1] + hd.get("dy", 0)


def dragon_fire(i):
    """불꽃 브레스 (한 번): 0 = 고개를 뒤로 젖히며 숨을 들이마셔 볼이 빵빵(바람이 입으로 빨려 듦)
    · 1 = 입이 반쯤 열리며 불씨 · 2 = 날개를 펴고 앞으로 화르륵"""
    if i == 0:
        hd = dict(dx=-3, dy=-1, ang=-6, cheeks=True, eye="squeeze", mouth="tight")
        cv = dragon_cv(pose=0, head=hd, belly=1.08)
        sx, sy = head_at(hd, (31.5, 10.0))
        sx, sy = rnd(sx), rnd(sy)
        for seg in (((sx + 2, sy - 3), (sx + 3, sy - 3)), ((sx + 3, sy), (sx + 4, sy)), ((sx + 2, sy + 3), (sx + 3, sy + 3))):
            cv.line(*seg[0], *seg[1], ACT_LINE, to="dt")
    elif i == 1:
        hd = dict(dx=-4, ang=-3, eye="fierce", mouth="m")
        cv = dragon_cv(pose=3, head=hd)
        mx, my = head_at(hd, (31.0, 11.5))
        mx, my = rnd(mx), rnd(my)
        for p, c in (((mx + 1, my), FIRE[0]), ((mx + 2, my - 1), FIRE[1]), ((mx + 2, my + 1), FIRE[2]),
                     ((mx + 3, my - 2), FIRE[1]), ((mx + 4, my), FIRE[2]), ((mx + 3, my + 2), FIRE[3])):
            cv.dt[p] = c
    else:
        hd = dict(dx=-4, ang=3, eye="fierce", mouth="l")
        cv = dragon_cv(pose=1, head=hd)
        mx, my = head_at(hd, (30.5, 12.5))
        flame(cv, rnd(mx), rnd(my), 32, 3.3)
    return render(cv)


def dragon_roar(i):
    """포효 (한 번): 고개를 뒤로 젖혀 들며 입을 점점 크게 → 2 = 날개 활짝 + 음파 (마지막 장 유지)"""
    dx, dy, ang, mouth, pose, eye = [(-1, 0, -6, "s", 3, "normal"), (-2, -1, -13, "m", 0, "fierce"),
                                     (-3, -1, -20, "l", 0, "squeeze")][i]
    hd = dict(dx=dx, dy=dy, ang=ang, eye=eye, mouth=mouth)
    cv = dragon_cv(pose=pose, head=hd)
    mx, my = head_at(hd, (32.0, 12.5))
    if i == 1:
        marks(cv, mx, my, 1.5, -40, 20, n=2, ln=2)
    elif i == 2:
        marks(cv, mx, my, 1.5, -60, 30, n=3, ln=2)
        marks(cv, mx, my, 4.5, -40, 10, n=2, ln=1)
    return render(cv)


def dragon_snort(i):
    """콧김 '흥!': 실눈 + 꾹 다문 입, 고개를 살짝 들고 콧구멍에서 김이 앞아래로 푸쉭 (황소처럼)
    0 = 막 뿜음 (콧구멍 앞 작은 김 + 동그란 김) · 1 = 아래로 퍼지며 옅어짐"""
    hd = dict(ang=-4 if i == 0 else -2, eye="squint", mouth="tight")
    cv = dragon_cv(pose=3, sway=-1 if i else 0, head=hd)
    nx, ny = head_at(hd, (31, 9))
    nx, ny = rnd(nx), rnd(ny)
    if i == 0:
        steam(cv, nx + 1, ny + 3, 1.0, 250)
        steam(cv, nx, ny + 6, 1.8, 245)
    else:
        steam(cv, nx + 1, ny + 4, 1.0, 220)
        steam(cv, nx - 1, ny + 7, 1.8, 225)
        steam(cv, nx + 1, ny + 10, 1.3, 160)
    return render(cv)


def pearl(cv, cx, cy, glow):
    """여의주: 금빛 구슬 (테두리 자동) + 반짝 + 둘레 빛무리(몸 뒤)"""
    for y in range(cy - 5, cy + 6):
        for x in range(cx - 5, cx + 6):
            d = math.hypot(x - cx, y - cy)
            if 2.6 < d <= glow:
                cv.fx[(x, y)] = (255, 218, 80, 150 if d < glow - 0.9 else 85)
    cv.ellipse(cx, cy, 2.3, 2.3, PEARL)
    for p in ((cx - 1, cy - 1), (cx, cy - 2), (cx - 2, cy), (cx - 1, cy - 2)):
        cv.dt[p] = PEARL_HI
    cv.dt[(cx - 1, cy - 1)] = (255, 255, 255, 255)
    for p in ((cx + 1, cy + 1), (cx, cy + 2), (cx + 2, cy), (cx + 1, cy + 2), (cx + 2, cy + 1)):
        cv.dt[p] = PEARL_DK


def dragon_pearl(i):
    """여의주: 앞발로 금빛 여의주를 받쳐 들고 싱글벙글 · 반짝 (0·1 이 빛무리 크기 · 반짝 자리를 바꿈)"""
    cv = dragon_cv(pose=3, sway=-1 if i else 0, head=dict(eye="happy", mouth="grin"), arms="hold")
    pc = Cv()
    pearl(pc, 27, 17, 4.4 if i == 0 else 3.6)
    cv.overlay(pc)
    hand = Cv()                                            # 앞발: 가슴에서 뻗어 여의주 왼쪽 아래를 감쌈
    for p in ((21, 15), (22, 16), (23, 17), (24, 17), (24, 18), (25, 19)):
        hand.put(*p, G)
    hand.dt[(22, 16)] = G_HI; hand.dt[(25, 19)] = G_DK
    cv.overlay(hand)
    cv.dt[(25, 17)] = HORN; cv.dt[(26, 19)] = HORN         # 발톱이 여의주를 꼭 쥠
    if i == 0:
        sparkle(cv, 31, 15)
        cv.dt[(23, 14)] = alpha(STAR_FILL, 220)
    else:
        sparkle(cv, 31, 20)
        sparkle(cv, 24, 21)
    return render(cv)


# ── 보물 더미 위에서 낮잠 ──────────────────────────────────────────────
def coin_pile():
    """작은 금화 더미: 동전이 엇갈려 쌓인 언덕 (위 테두리는 동전 머리로 울퉁불퉁) + 반짝 + 보석 둘"""
    c = Cv()
    c.spans({22: (2, 31), 21: (2, 31), 20: (3, 31), 19: (3, 30), 18: (4, 30), 17: (6, 29), 16: (10, 27)}, COIN)
    for x in (4, 8, 12, 17, 21, 25, 28):                  # 위로 볼록 솟은 동전
        top = min(y for (xx, y) in c.px if xx == x)
        c.put(x, top - 1, COIN); c.put(x + 1, top - 1, COIN)
    for (x, y) in list(c.px):                             # 동전 무늬: 3칸짜리 동전이 줄마다 엇갈림 (밝은 윗면 · 어두운 아랫테)
        u = (x + (y // 2) * 2) % 3
        if y % 2 == 0 and u in (0, 1):
            c.dt[(x, y)] = COIN_HI
        elif y % 2 == 1 and u in (1, 2):
            c.dt[(x, y)] = COIN_DK
    tops = {}
    for (x, y) in c.px:
        tops[x] = min(tops.get(x, 99), y)
    for x, y in tops.items():
        c.dt[(x, y)] = COIN_HI
    for p in ((6, 19), (27, 19), (29, 22), (13, 21), (20, 22)):
        c.dt[p] = COIN_SHINE
    for y in range(13, 18):                               # 왼쪽 끝에 동전 탑 (한 닢씩 밝고 어두운 줄)
        for x in (2, 3, 4):
            c.put(x, y, COIN)
            c.dt[(x, y)] = COIN_HI if y % 2 == 1 else COIN_DK
    c.dt[(2, 13)] = COIN_SHINE
    c.put(4, 21, (228, 52, 56, 255)); c.dt[(4, 21)] = (255, 120, 120, 255)      # 빨간 보석
    c.dt[(26, 20)] = (90, 200, 255, 255); c.dt[(27, 20)] = (40, 140, 220, 255)  # 파란 보석
    return c


REST_WING = {"wr": (16, 10), "f": [(10, 11), (7, 13), (9, 15)], "r": (12, 16)}  # 등에 납작 접은 날개


def dragon_lying(breath=0):
    """금화 위에 엎드려 몸을 말고 자는 용. breath=1 이면 숨을 들이쉼 (등이 1칸 부풂)"""
    b = breath
    d = Cv()
    d.ellipse(13.8, 16.4 - 0.5 * b, 7.0, 3.6 + 0.5 * b, G)  # 몸통
    d.ellipse(9.4, 18.2, 2.6, 1.9, G)                       # 접은 뒷다리
    d.rect(19, 14, 22, 18, G)                              # 목 (낮게 앞으로)
    hd = dict(dx=0, dy=5)
    head = moved(head_cv(), 0, 5)                          # 머리를 앞발 위에 내려놓음
    d.px.update(head.px)
    tops = {}
    for (x, y) in d.px:
        tops[x] = min(tops.get(x, 99), y)
    for x in (8, 11, 14, 17):                              # 등 가시
        if d.px.get((x, tops[x])) == G:
            d.put(x, tops[x] - 1, SPIKE)
    for x in range(10, 19):                                # 바닥에 깔린 배 (크림색 띠)
        if d.px.get((x, 19)) == G:
            d.dt[(x, 19)] = BELLY
    d.top_light(G_HI, skip=(SPIKE, HORN), x0=17, x1=31)
    for (x, y) in list(d.px):
        if d.px[(x, y)] == G and (x, y + 1) not in d.px and (x, y) not in d.dt:
            d.dt[(x, y)] = G_DK
    paws = Cv()                                            # 앞발 (턱 밑에 모음)
    paws.rect(20, 19, 24, 19, G); paws.put(21, 18, G); paws.put(22, 18, G)
    paws.dt[(20, 19)] = HORN; paws.dt[(22, 19)] = HORN; paws.dt[(24, 19)] = HORN
    d.overlay(paws)
    tail = Cv()                                            # 꼬리: 엉덩이에서 내려와 몸 앞 바닥으로 둥글게 감쌈
    for x, y, r in [(6.2, 18.6, 1.7), (5.6, 20.4, 1.4), (7.8, 21.2, 1.3), (10.6, 21.4, 1.15), (13.4, 21.4, 1.0)]:
        tail.ellipse(x, y, r, r, G)
    tail.art(15, 20, ["s.", "ss", "s."], {"s": SPIKE}, to="px")
    for (x, y) in list(tail.px):
        if tail.px[(x, y)] == G:
            tail.dt[(x, y)] = G_HI if (x, y - 1) not in tail.px else (G_DK if (x, y + 1) not in tail.px else G)
    d.overlay(tail)
    put_eye(d, *[rnd(v) for v in head_at(hd, (25, 7))], "sleep")
    for p in ((23, 10), (24, 10)):
        d.dt[tuple(rnd(v) for v in head_at(hd, p))] = BLUSH
    d.dt[tuple(rnd(v) for v in head_at(hd, (31, 9)))] = G_DK
    for p in ((28, 11), (29, 11), (27, 10)):
        d.dt[tuple(rnd(v) for v in head_at(hd, p))] = G_DK
    d.overlay(wing_cv(REST_WING, 14, 14 - b))
    return d


def dragon_hoard(i):
    """보물 지키며 낮잠: 0 = 금화 더미에 내려앉아 꾸벅 (졸린 눈) · 1·2 = 몸을 말고 엎드려 쿨쿨
    (2 = 숨 들이쉼: 등이 부풀고 콧방울)"""
    base = coin_pile()
    if i == 0:
        d = dragon_cv(pose=3, head=dict(dx=0, dy=2, ang=8, eye="half", mouth="smile"), legs="sit")
        d.ellipse(11.5, 18.6, 2.7, 1.8, G)                 # 앉은 뒷다리
        d.rect(18, 18, 20, 19, G)                         # 앞발 짚음
        d.dt[(18, 19)] = HORN; d.dt[(20, 19)] = HORN
        d.dt[(11, 20)] = G_DK; d.dt[(12, 20)] = G_DK
        d = moved(d, 0, 1)
    else:
        d = dragon_lying(breath=i - 1)
    base.overlay(d)
    if i == 2:                                           # 콧방울
        for p, c in (((31, 11), (200, 232, 255, 235)), ((32, 11), (200, 232, 255, 235)), ((31, 12), (200, 232, 255, 235)),
                     ((32, 12), (150, 200, 240, 235)), ((31, 10), (150, 200, 240, 200)), ((32, 10), (150, 200, 240, 200))):
            base.dt[p] = c
        base.dt[(31, 11)] = (255, 255, 255, 255)
    if i >= 1:
        sparkle(base, 28, 21 if i == 1 else 20)
    return render(base)


# ══════════════════════════════════════════════════════════════════════
# 목록 · 저장 · 미리보기
# ══════════════════════════════════════════════════════════════════════
SHEETS = [
    ("car_flash", car_flash, 2, "상향등 번쩍 / 꺼짐"),
    ("car_honk", car_honk, 2, "경적: 눌림 + 음파"),
    ("car_nitro", car_nitro, 2, "니트로 불꽃 + 뒤로 젖힘"),
    ("car_drift", car_drift, 2, "앞바퀴 꺾임 + 타이어 연기"),
    ("plane_touchgo", plane_touchgo, 2, "바퀴 내림 / 접지 연기"),
    ("plane_smoke", plane_smoke, 2, "꼬리 색 연기"),
    ("heli_search", heli_search, 2, "기수 탐조등"),
    ("heli_hoist", heli_hoist, 2, "문 열고 윈치 줄"),
    ("heli_bucket", heli_bucket, 2, "물바구니 (4칸 위)"),
    ("ufo_beam", ufo_beam, 2, "배 밑 해치 + 빔"),
    ("ufo_alien", ufo_alien, 2, "해치 열고 외계인 인사"),
    ("ufo_lights", ufo_lights, 3, "불빛 차례로 (한 번)"),
    ("dragon_fire", dragon_fire, 3, "들숨 → 입 → 불꽃 (한 번)"),
    ("dragon_roar", dragon_roar, 3, "고개 들고 포효 (한 번)"),
    ("dragon_snort", dragon_snort, 2, "실눈 + 콧김"),
    ("dragon_pearl", dragon_pearl, 2, "여의주 들고 싱글벙글"),
    ("dragon_hoard", dragon_hoard, 3, "금화 위 낮잠 (0=눕기)"),
]


def build():
    out = []
    for name, fn, n, desc in SHEETS:
        frames = [fn(i) for i in range(n)]
        check_margin(name, frames)
        out.append((name, desc, frames))
    return out


def font(size):
    for p in (r"C:\Windows\Fonts\malgunbd.ttf", r"C:\Windows\Fonts\malgun.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def preview(sheets, path, S=6):
    GAP, SEC, LEFT, TOP = 8, 26, 250, 44
    nmax = max(len(f) for _, _, f in sheets)
    fw, fh = W * S, H * S
    pw = LEFT + 2 * (nmax * (fw + GAP)) + SEC + 12
    ph = TOP + len(sheets) * (fh + GAP) + 10
    im = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
    dr = ImageDraw.Draw(im)
    dark_x = LEFT + nmax * (fw + GAP) + SEC
    dr.rectangle([dark_x - 8, 0, pw, ph], fill=(36, 38, 46, 255))
    f1, f2 = font(22), font(15)
    dr.text((12, 8), "Pixel TMI · 탈것 행동 시트 (×6 · 왼쪽 흰 바탕 / 오른쪽 어두운 바탕 · 이름 밑은 실제 1배·2배)", fill=(30, 30, 36, 255), font=f2)
    for r, (name, desc, frames) in enumerate(sheets):
        y = TOP + r * (fh + GAP)
        dr.text((12, y + 4), f"{name}", fill=(24, 24, 30, 255), font=f1)
        dr.text((12, y + 34), f"{len(frames)}칸 · {desc}", fill=(90, 92, 104, 255), font=f2)
        sx = 12
        for f in frames:                                  # 1배
            im.alpha_composite(f, (sx, y + 64))
            sx += W + 4
        sx = 12
        for f in frames:                                  # 2배
            im.alpha_composite(f.resize((W * 2, H * 2), Image.NEAREST), (sx, y + 64 + H + 6))
            sx += W * 2 + 6
        for k, f in enumerate(frames):
            big = f.resize((fw, fh), Image.NEAREST)
            x = LEFT + k * (fw + GAP)
            dr.rectangle([x - 1, y - 1, x + fw, y + fh], outline=(226, 226, 232, 255))
            im.alpha_composite(big, (x, y))
            xd = dark_x + k * (fw + GAP)
            dr.rectangle([xd - 1, y - 1, xd + fw, y + fh], outline=(60, 62, 74, 255))
            im.alpha_composite(big, (xd, y))
            dr.text((x + 3, y + fh - 18), str(k), fill=(170, 170, 180, 255), font=f2)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    im.convert("RGB").save(path)


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")         # 윈도 콘솔에서 한글이 깨지지 않게
    except Exception:
        pass
    force = "--덮어쓰기" in argv
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    out, prev = args[0], args[1]
    os.makedirs(out, exist_ok=True)
    targets = [os.path.join(out, f"{name}.png") for name, *_ in SHEETS]
    exist = [p for p in targets if os.path.exists(p)]
    if exist and not force:
        print("이미 있는 파일이 있어 멈춥니다 (덮어쓰려면 --덮어쓰기):")
        for p in exist:
            print("  ", p)
        sys.exit(2)
    sheets = build()
    for (name, desc, frames), path in zip(sheets, targets):
        sheet = Image.new("RGBA", (W * len(frames), H), CLEAR)
        for k, f in enumerate(frames):
            sheet.alpha_composite(f, (k * W, 0))
        sheet.save(path)
    preview(sheets, prev)
    print("ok", len(sheets), "시트 →", out)
    for name, desc, frames in sheets:
        print(f"  {name}.png  {len(frames)}칸  {desc}")


if __name__ == "__main__":
    main(sys.argv[1:])
