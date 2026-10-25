"""
Pixel TMI 동물 3종 (강아지·사자·말) — 고양이 오마주(고양이_오마주.py)와 같은 결로 다시 그린 도트.
결: 동물마다 한 가지 털색 + 같은 계열 진한 외곽선(자동 1칸), 3/4 정면 얼굴(점 눈 두 개 + 작은 입),
    네 발로 서는 진짜 동물 자세(옷·두 발 서기 없음), 무섭지 않고 귀엽게.
    분홍·빨강 코 덩어리 금지 — 코는 아주 작은 진한 점(강아지·사자)이나 콧구멍 점(말)만.
그림을 베끼지 않고 도형을 조립한 뒤 외곽선을 자동으로 두른다.
v2 (2026-10-25) 디테일: 사자 = 3겹 갈기(술 끝·밝은 쪽·골) + 어깨·가슴 갈기 가닥(걸음 따라 출렁) + 꼬리 술 + 수염 + 밝은 발가락 + 배 그늘,
    말 = 갈기·꼬리 가닥 결(걸음 따라 흐름) + 회갈색 발굽 윤기·흰 양말 다리는 밝은 발굽 + 어깨·엉덩이 근육 결 + 주둥이·볼 그늘·귀 안쪽,
    강아지 = 걸음에 늦게 따라오는 귀 끝 + 꼬리 살랑 + 정수리·등 윤기 + 볼털·가슴털 + 이름표 반짝 + 발뒤꿈치 그늘.
    좌우 1칸 여백을 지키도록 끝 칸을 다듬는다. v1 원본(그림·코드)은 베이스앱/_보관/동물_기본_v1/.
    행동 시트(동물_행동시트.py)가 이 파일의 몸·머리를 가져다 쓰므로, 여기를 고치면 그것도 다시 돌린다.
한 프레임 = 가로 34 × 세로 24칸 (앱 아이콘 24도트와 1:1), 시트는 왼쪽→오른쪽 한 줄.

사용: python 동물_오마주.py <출력 폴더> <미리보기.png>
출력 (동물 = dog · lion · horse):
  <동물>_walk.png  걷기 4프레임
  <동물>_run.png   성격 있는 달리기 (강아지 6 · 사자 6 · 말 8프레임 — 택시 미터기 말처럼 전력 갤럽)
  <동물>_idle.png  가만히 2프레임 (기본 · 눈 깜빡)
  <동물>_face.png  표정 3프레임 (말하기 · 놀람 · 웃음) — idle과 같은 자세
  <동물>_sneak.png 살금살금 4프레임 (위험 구간 앞: 두 발로 서서 까치발) — 강아지·사자만 (말은 없음)
"""
import math
import os
import sys

from PIL import Image, ImageDraw

W, H = 34, 24
CLEAR = (0, 0, 0, 0)
SHINE = (252, 252, 252, 255)


class Pal:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# ── 색 ────────────────────────────────────────────────────────────────
DOG = Pal(
    LINE=(96, 56, 32, 255),
    FUR=(226, 150, 76, 255),        # 따뜻한 시바 황갈색
    FUR_HI=(242, 178, 106, 255),    # 정수리·등 윤기
    FUR_DK=(204, 128, 62, 255),     # 배 그늘·허벅지 결
    FAR=(194, 122, 58, 255),        # 먼 쪽 다리
    CREAM=(252, 238, 212, 255),     # 주둥이·가슴·배·양말
    CREAM_SH=(230, 206, 170, 255),  # 발뒤꿈치·턱 밑 그늘
    CREAM_FAR=(226, 204, 172, 255),
    CREAM_FAR_SH=(204, 178, 142, 255),
    EAR_IN=(250, 214, 178, 255),
    EYE=(30, 22, 20, 255),
    NOSE=(36, 26, 24, 255),
    MOUTH=(132, 78, 50, 255),
    TONGUE=(240, 112, 126, 255),
    TONGUE_DK=(172, 62, 76, 255),
    COLLAR=(48, 118, 214, 255),
    TAG=(246, 196, 40, 255),
    TAG_DK=(200, 150, 20, 255),
)

LION = Pal(
    LINE=(104, 60, 30, 255),
    FUR=(238, 188, 90, 255),        # 금빛 몸
    FUR_HI=(250, 212, 128, 255),    # 등 윤기
    FUR_DK=(220, 164, 72, 255),     # 배 그늘·근육 결
    FAR=(208, 156, 68, 255),
    LIGHT=(252, 230, 174, 255),     # 주둥이·배·발
    LIGHT_FAR=(232, 204, 146, 255),
    MANE=(194, 104, 42, 255),       # 갈기 (가운데 층)
    MANE_HI=(224, 140, 62, 255),    # 갈기 바깥 술
    MANE_TIP=(242, 170, 84, 255),   # 술 끝 (가장 밝게)
    MANE_DK=(150, 76, 30, 255),     # 얼굴 둘레·술 사이 골
    EAR_IN=(176, 100, 52, 255),
    EYE=(32, 20, 16, 255),
    MOUTH=(126, 68, 38, 255),
    TONGUE=(222, 96, 104, 255),
    MOUTH_IN=(150, 60, 66, 255),     # 벌린 입 안 (분홍 코처럼 보이지 않게 어둡게)
    WHISK=(255, 244, 214, 255),      # 수염 (갈기 위로 빼꼼)
    WHISK_DOT=(198, 142, 82, 255),   # 수염 자리 점
)

HORSE = Pal(
    LINE=(66, 38, 24, 255),
    FUR=(184, 104, 56, 255),        # 밤색
    FUR_HI=(206, 128, 76, 255),     # 등·목덜미 윤기
    FUR_DK=(160, 88, 46, 255),      # 어깨·엉덩이 근육 결, 배 그늘
    FAR=(148, 80, 42, 255),
    MANE=(72, 44, 34, 255),         # 진한 갈기·꼬리
    MANE_HI=(110, 70, 50, 255),
    MANE_DK=(50, 30, 24, 255),
    MUZ=(224, 176, 134, 255),       # 밝은 주둥이 (분홍 X)
    MUZ_DK=(202, 152, 110, 255),
    BLAZE=(250, 246, 236, 255),     # 이마 흰 줄
    SOCK=(246, 240, 228, 255),
    HOOF=(82, 70, 66, 255),         # 발굽 (외곽선보다 밝은 회갈색)
    HOOF_HI=(128, 114, 106, 255),
    HOOF_PALE=(178, 156, 126, 255), # 흰 양말 다리의 밝은 발굽 (실제 말처럼)
    EAR_IN=(126, 68, 42, 255),
    EYE=(26, 18, 16, 255),
    NOSTRIL=(110, 64, 42, 255),
    MOUTH=(122, 72, 48, 255),
    MOUTH_IN=(150, 70, 66, 255),
)
class Cv:
    def __init__(self, pal):
        self.p = pal
        self.px = {}

    def rect(self, x0, y0, x1, y1, c=None):
        c = c or self.p.FUR
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                self.px[(x, y)] = c

    def put(self, x, y, c=None):
        self.px[(x, y)] = c or self.p.FUR

    def cut(self, *pts):
        for p in pts:
            self.px.pop(p, None)

    def limb(self, x0, y0, x1, y1, c=None, w=2):
        """비스듬한 굵기 w 선 (위 끝 → 아래 끝). 눕는 선은 세로로, 서는 선은 가로로 굵게"""
        c = c or self.p.FUR
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        flat = abs(x1 - x0) > abs(y1 - y0)
        for i in range(steps + 1):
            x = round(x0 + (x1 - x0) * i / steps)
            y = round(y0 + (y1 - y0) * i / steps)
            if flat:
                self.rect(x, y, x, y + w - 1, c)
            else:
                self.rect(x, y, x + w - 1, y, c)

    def leg2(self, top, knee, foot, c=None, w=2, tip=None, tip_len=1):
        """무릎 있는 다리: 위 → 무릎 → 발끝. tip = 발끝 색(발굽·양말)"""
        self.limb(*top, *knee, c, w)
        self.limb(*knee, *foot, c, w)
        if tip:
            fx, fy = foot
            kx, ky = knee
            flat = abs(fx - kx) > abs(fy - ky)
            for k in range(tip_len):
                if flat:
                    sx = -1 if fx > kx else 1
                    self.rect(fx + sx * k, fy, fx + sx * k, fy + w - 1, tip)
                else:
                    self.rect(fx, fy - k, fx + w - 1, fy - k, tip)

    def image(self, details=()):
        im = Image.new("RGBA", (W, H), CLEAR)
        post = POST.get(id(self.p))                  # 동물별 마무리 (발가락 그늘·발굽 색 같은 규칙)
        if post:
            post(self.px)
        for k in [k for k in self.px if not 2 <= k[0] <= W - 3]:
            del self.px[k]                           # 좌우 여백 1칸 (외곽선이 x=0·33 에 닿지 않게 끝 칸을 다듬음)
        for (x, y) in list(self.px):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n not in self.px and 0 <= n[0] < W and 0 <= n[1] < H:
                    im.putpixel(n, self.p.LINE)
        for (x, y), c in self.px.items():
            if 0 <= x < W and 0 <= y < H:
                im.putpixel((x, y), c)
        for x, y, c in details:
            if 0 <= x < W and 0 <= y < H:
                im.putpixel((x, y), c)
        return im


def eyes(d, P, xs, ey, mood="normal", blink=False):
    """점 눈 두 개 (고양이와 같은 문법)"""
    for ex in xs:
        if blink:
            d += [(ex - 1, ey + 1, P.EYE), (ex, ey + 1, P.EYE)]
        elif mood == "happy":
            d += [(ex - 1, ey + 1, P.EYE), (ex, ey, P.EYE), (ex + 1, ey + 1, P.EYE)]
        elif mood == "surprised":
            d += [(ex, ey - 1, P.EYE), (ex, ey, P.EYE), (ex, ey + 1, P.EYE), (ex - 1, ey, P.EYE), (ex - 1, ey + 1, P.EYE),
                  (ex - 1, ey - 1, SHINE)]
        else:
            d += [(ex, ey, P.EYE), (ex, ey + 1, P.EYE)]


WALK_POSE = [   # (x, 기울기, 들림) — 뒤-가까운, 앞-가까운, 뒤-먼, 앞-먼 (고양이 걷기와 같은 박자)
    ((9, -1, 0), (21, 1, 0), (12, 0, 0), (18, 0, 0)),
    ((11, 0, 0), (19, 0, 1), (10, 0, 0), (20, 0, 0)),
    ((12, 0, 0), (18, 0, 0), (9, -1, 0), (21, 1, 0)),
    ((10, 0, 0), (20, 0, 0), (11, 0, 0), (19, 0, 1)),
]


# ══════════════════════════════════════════════════════════════════════
# 강아지 (시바 느낌): 황갈색 + 크림 가면·가슴·양말, 말린 꼬리, 쫑긋 귀(달리면 펄럭), 웃으면 혀
# ══════════════════════════════════════════════════════════════════════
def dog_head(cv, hx, top, ears="up"):
    P = DOG
    F, C, I = P.FUR, P.CREAM, P.EAR_IN
    cv.rect(hx + 1, top, hx + 10, top, F)
    cv.rect(hx, top + 1, hx + 11, top + 5, F)
    cv.rect(hx + 4, top, hx + 7, top, P.FUR_HI)       # 정수리 윤기
    cv.rect(hx, top + 6, hx + 11, top + 7, C)          # 크림 볼·주둥이
    cv.rect(hx + 1, top + 8, hx + 10, top + 8, C)
    cv.rect(hx + 3, top + 9, hx + 8, top + 9, C)       # 턱
    cv.put(hx + 3, top + 9, P.CREAM_SH); cv.put(hx + 8, top + 9, P.CREAM_SH)   # 턱 밑 그늘
    cv.put(hx - 1, top + 6, C); cv.put(hx - 1, top + 7, P.CREAM_SH)   # 볼털 복슬 (오른쪽은 여백 1칸을 지킬 때만)
    if hx + 12 <= W - 3:
        cv.put(hx + 12, top + 6, C); cv.put(hx + 12, top + 7, P.CREAM_SH)
    cv.put(hx + 1, top + 5, C); cv.put(hx + 10, top + 5, C)
    cv.rect(hx + 5, top + 4, hx + 6, top + 5, C)       # 콧등
    for ox, s in ((hx + 1, 1), (hx + 10, -1)):         # s = 안쪽 방향
        if ears in ("up", "flop"):  # 쫑긋 세모 귀 (flop = 걸음에 귀 끝이 한 박자 늦게 바깥으로 까딱)
            cv.put(ox + (0 if ears == "flop" else s), top - 3)
            cv.rect(ox, top - 2, ox + s * 2, top - 2)
            cv.rect(ox, top - 1, ox + s * 3, top - 1)
            cv.put(ox + s, top - 2, I); cv.rect(ox + s, top - 1, ox + s * 2, top - 1, I)
        elif ears == "tilt":    # 바깥으로 살짝 젖힘
            cv.put(ox - s, top - 3)
            cv.rect(ox - s, top - 2, ox + s, top - 2)
            cv.rect(ox - s, top - 1, ox + s * 2, top - 1)
            cv.put(ox, top - 2, I); cv.rect(ox, top - 1, ox + s, top - 1, I)
        else:                   # back: 바람에 옆으로 펄럭
            cv.rect(ox - s * 2, top - 1, ox + s, top - 1)
            cv.rect(ox - s * 2, top - 2, ox - s, top - 2)
            cv.put(ox - s * 2, top, F)
            cv.rect(ox - s * 1, top - 1, ox, top - 1, I)


def dog_face(d, hx, top, mood="normal", blink=False, tongue=False):
    P = DOG
    eyes(d, P, (hx + 3, hx + 8), top + 3, mood, blink)
    d += [(hx + 3, top + 1, P.CREAM), (hx + 8, top + 1, P.CREAM)]          # 시바 눈썹 점
    d += [(hx + 5, top + 6, P.NOSE), (hx + 6, top + 6, P.NOSE)]            # 작은 검은 코
    if mood in ("talk", "surprised"):
        d += [(hx + 4, top + 7, P.MOUTH), (hx + 7, top + 7, P.MOUTH),
              (hx + 5, top + 7, P.TONGUE_DK), (hx + 6, top + 7, P.TONGUE_DK),
              (hx + 5, top + 8, P.MOUTH), (hx + 6, top + 8, P.MOUTH)]
    elif mood == "happy" or tongue:
        d += [(hx + 4, top + 7, P.MOUTH), (hx + 7, top + 7, P.MOUTH),
              (hx + 5, top + 7, P.TONGUE_DK), (hx + 6, top + 7, P.TONGUE_DK),
              (hx + 5, top + 8, P.TONGUE), (hx + 6, top + 8, P.TONGUE),
              (hx + 5, top + 9, P.TONGUE), (hx + 6, top + 9, P.TONGUE_DK)]
    else:
        d += [(hx + 4, top + 7, P.MOUTH), (hx + 7, top + 7, P.MOUTH), (hx + 5, top + 8, P.MOUTH), (hx + 6, top + 8, P.MOUTH)]


def dog_tail(cv, x, y):
    """말린 꼬리 (등 위에 동그랗게 — 크림색 안쪽이 소용돌이, 위는 윤기·아래는 그늘) — (x, y) = 왼쪽 위"""
    P = DOG
    F, C = P.FUR, P.CREAM
    cv.rect(x + 1, y, x + 3, y, F)
    cv.rect(x, y + 1, x + 4, y + 3, F)
    cv.rect(x + 1, y + 4, x + 4, y + 4, F)
    cv.put(x + 2, y + 2, C); cv.put(x + 1, y + 2, C); cv.put(x + 2, y + 3, C)
    cv.put(x + 1, y + 1, P.FUR_HI); cv.put(x + 2, y, P.FUR_HI)
    cv.put(x + 4, y + 3, P.FUR_DK); cv.put(x + 3, y + 4, P.FUR_DK)


def dog_neck_collar(d, hx, top, glint=True):
    P = DOG
    band = [(hx - 1, top + 7), (hx, top + 8), (hx + 1, top + 8), (hx + 1, top + 9), (hx + 2, top + 9),
            (hx + 2, top + 10), (hx + 3, top + 10)]
    d += [(x, y, P.COLLAR) for x, y in band]
    d += [(hx + 3, top + 11, SHINE if glint else P.TAG), (hx + 4, top + 11, P.TAG), (hx + 3, top + 12, P.TAG_DK)]


def dog_body_side(cv, by, x0=9, x1=23):
    P = DOG
    cv.rect(x0, by, x1, by + 5)
    cv.cut((x0, by), (x0, by + 5), (x1, by + 5))
    cv.rect(x0 + 2, by, x1 - 4, by, P.FUR_HI)            # 등 윤기
    cv.rect(x0 + 5, by + 4, x1 - 6, by + 4, P.FUR_DK)    # 배 그늘
    cv.rect(x0 + 3, by + 5, x1 - 3, by + 5, P.CREAM)     # 배
    cv.rect(x1 - 2, by + 3, x1, by + 4, P.CREAM)         # 가슴
    cv.put(x1 + 1, by + 3, P.CREAM)                      # 가슴 털 한 가닥
    for dx, dy in ((2, 1), (3, 2), (4, 3), (4, 4)):      # 허벅지 둥근 결
        cv.put(x0 + dx, by + dy, P.FUR_DK)
    for dx, dy in ((-5, 1), (-5, 2), (-4, 3)):           # 어깨 결
        cv.put(x1 + dx, by + dy, P.FUR_DK)
    cv.put(x0 + 1, by + 1, P.FUR_HI)                     # 엉덩이 윤기


def dog_walk(frame, blink=False):
    P = DOG
    cv = Cv(P)
    hx, top = 20, 4
    bn, fn, bf, ff = WALK_POSE[frame]
    for (x, s, up) in (bf, ff):
        cv.leg2((x, 16), (x, 19), (x + s, 22 - up), P.FAR, tip=P.CREAM_FAR)
    dog_tail(cv, 5 + (0, 1, 0, -1)[frame], 5 + (0, 1, 0, 1)[frame])     # 걸음마다 꼬리 살랑
    cv.rect(8, 9, 10, 11)
    dog_body_side(cv, 11)
    for (x, s, up) in (bn, fn):
        cv.leg2((x, 16), (x, 19), (x + s, 22 - up), tip=P.CREAM)
    dog_head(cv, hx, top, ears=("up", "flop", "up", "flop")[frame])
    d = []
    dog_face(d, hx, top, blink=blink)
    dog_neck_collar(d, hx, top, glint=frame in (0, 2))
    return cv.image(d)


def dog_run(frame):
    """신난 질주 6장: 쭉 뻗어 붕 → 앞발 착지 → 모으기 → 뒷발 차기 → 붕 → 쭉. 귀 펄럭 · 혀 · 꼬리 통통"""
    P = DOG
    cv = Cv(P)
    oy = (-1, 0, 1, 0, -1, -1)[frame]
    by = 11 + oy
    hx, top = 20, 4 + oy
    ears = ("back", "tilt", "up", "up", "tilt", "back")[frame]
    top = 4 + (oy if ears == "back" else max(oy, 0))     # 귀가 선 프레임은 머리가 칸 위로 넘지 않게
    lt = by + 5
    # 다리: (위, 무릎, 발) — 뒤-먼, 앞-먼, 뒤-가까운, 앞-가까운
    legs = [
        (((13, lt), (9, lt + 3), (5, lt + 4)),  ((20, lt), (24, lt + 2), (28, lt + 3)),
         ((11, lt), (7, lt + 3), (3, lt + 5)),  ((22, lt), (26, lt + 2), (30, lt + 4))),          # 쭉 뻗어 붕
        (((13, lt), (11, lt + 3), (8, lt + 5)),  ((20, lt), (24, lt + 3), (26, 22)),
         ((11, lt), (9, lt + 3), (6, lt + 5)),  ((22, lt), (24, lt + 3), (24, 22))),             # 앞발 착지
        (((13, lt), (15, lt + 3), (14, 22)),     ((20, lt), (20, lt + 3), (18, 22)),
         ((11, lt), (14, lt + 3), (12, 22)),     ((22, lt), (21, lt + 3), (20, 22))),             # 모으기 (몸 낮게)
        (((13, lt), (14, lt + 3), (11, 22)),     ((20, lt), (22, lt + 2), (20, lt + 4)),
         ((11, lt), (12, lt + 3), (9, 22)),      ((22, lt), (24, lt + 2), (22, lt + 4))),          # 뒷발로 차기
        (((13, lt), (10, lt + 3), (7, lt + 5)),  ((20, lt), (23, lt + 2), (26, lt + 3)),
         ((11, lt), (8, lt + 3), (5, lt + 6)),   ((22, lt), (25, lt + 2), (28, lt + 4))),          # 붕
        (((13, lt), (10, lt + 3), (6, lt + 4)),  ((20, lt), (24, lt + 1), (28, lt + 2)),
         ((11, lt), (8, lt + 3), (4, lt + 4)),   ((22, lt), (26, lt + 1), (30, lt + 3))),          # 쭉
    ][frame]
    for t, k, f in legs[:2]:
        cv.leg2(t, k, f, P.FAR, tip=P.CREAM_FAR)
    dog_tail(cv, 5, by - 6 + (0, 1, 0, -1, 0, 1)[frame])
    cv.rect(8, by - 2, 10, by)
    dog_body_side(cv, by)
    for t, k, f in legs[2:]:
        cv.leg2(t, k, f, tip=P.CREAM)
    dog_head(cv, hx, top, ears)
    d = []
    dog_face(d, hx, top, mood="happy" if frame in (1, 4) else "normal", tongue=True)
    dog_neck_collar(d, hx, top, glint=frame in (0, 3))
    return cv.image(d)


def dog_sit(mood="normal", blink=False):
    P = DOG
    cv = Cv(P)
    hx, top = 18, 4
    d = []
    dog_sit_body(cv, d)
    dog_head(cv, hx, top)
    dog_face(d, hx, top, mood=mood, blink=blink)
    dog_front_collar(d, hx, top)
    return cv.image(d)


# ══════════════════════════════════════════════════════════════════════
# 사자: 금빛 몸 + 크고 복슬한 진한 갈기, 꼬리 끝 술
# ══════════════════════════════════════════════════════════════════════
def lion_mane(cv, cx, cy, sweep=0, lift=0, R=6.8, bumps=9, phase=0.0, amp=0.9):
    """복슬 갈기 (겹겹이 털 뭉치): 뭉치마다 한쪽은 밝고 다른 쪽은 골이 져서 입체, 뭉치 끝은 가장 밝게.
    sweep > 0 = 뒤(왼쪽)로 휘날림, < 0 = 앞(오른쪽)으로 쏠림, lift = 위아래 출렁, phase = 뭉치가 걸음 따라 출렁"""
    P = LION
    cx2, cy2 = cx - sweep * 0.4, cy + lift * 0.5
    for y in range(int(cy - R - 3), int(cy + R + 4)):
        for x in range(int(cx - R - 6), int(cx + R + 5)):
            dx, dy = x - cx2, y - cy2
            if sweep > 0 and dx < 0:
                dx = dx / (1 + sweep * 0.10)
            if sweep < 0 and dx > 0:
                dx = dx / (1 - sweep * 0.10)
            ang = math.atan2(dy, dx)
            lobe = bumps * ang + phase
            wob = math.cos(lobe)
            r = R + amp * wob
            dist = math.hypot(dx, dy)
            if dist <= r and 2 <= x <= W - 3:          # 좌우 여백 1칸은 비움
                side = math.sin(lobe)
                if dist > r - 1.0 and wob > 0.6:
                    c = P.MANE_TIP                    # 뭉치 끝
                elif dist > r * 0.55 and side > 0.45:
                    c = P.MANE_HI                     # 뭉치의 밝은 쪽
                elif dist > r * 0.55 and side < -0.55:
                    c = P.MANE_DK                     # 뭉치 사이 골
                else:
                    c = P.MANE
                cv.put(x, y, c)


def lion_head(cv, fx, fy, sweep=0, lift=0, phase=0.0):
    """얼굴 10×9 (fx, fy = 왼쪽 위) + 둘레 갈기 + 동그란 귀"""
    P = LION
    F, L = P.FUR, P.LIGHT
    lion_mane(cv, fx + 4.5, fy + 4.4, sweep, lift, phase=phase)
    face = set()
    for x0, y0, x1, y1 in ((fx + 1, fy, fx + 8, fy), (fx, fy + 1, fx + 9, fy + 6), (fx + 1, fy + 7, fx + 8, fy + 7),
                           (fx + 2, fy + 8, fx + 7, fy + 8)):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                face.add((x, y))
    # 얼굴 둘레 갈기 그늘 (얼굴과 갈기 경계를 또렷하게)
    for (x, y) in face:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n not in face and n in cv.px:
                cv.px[n] = P.MANE_DK
    for p in face:
        cv.px[p] = F
    for ox in (fx, fx + 8):                                # 갈기 위로 빼꼼 동그란 귀
        cv.rect(ox, fy - 2, ox + 1, fy - 1, F)
        cv.put(ox + (1 if ox == fx else 0), fy - 1, P.EAR_IN)
    cv.rect(fx + 3, fy + 5, fx + 6, fy + 5, L)             # 밝은 주둥이
    cv.rect(fx + 2, fy + 6, fx + 7, fy + 7, L)
    cv.rect(fx + 3, fy + 8, fx + 6, fy + 8, L)


def lion_face(d, fx, fy, mood="normal", blink=False):
    P = LION
    eyes(d, P, (fx + 2, fx + 7), fy + 3, mood, blink)
    m = P.MOUTH
    d += [(fx + 4, fy + 5, m), (fx + 5, fy + 5, m)]        # 작은 진한 코 (분홍 X)
    if mood in ("talk", "surprised"):
        # 코와 한 줄 띄워 작게 벌린 입 'o' (코와 붙으면 큰 코처럼 보임)
        d += [(fx + 3, fy + 7, m), (fx + 6, fy + 7, m), (fx + 4, fy + 7, P.MOUTH_IN), (fx + 5, fy + 7, P.MOUTH_IN),
              (fx + 4, fy + 8, m), (fx + 5, fy + 8, m)]
    elif mood == "happy":
        d += [(fx + 2, fy + 6, m), (fx + 7, fy + 6, m), (fx + 3, fy + 7, m), (fx + 6, fy + 7, m),
              (fx + 4, fy + 7, P.TONGUE), (fx + 5, fy + 7, P.TONGUE)]
    else:
        d += [(fx + 2, fy + 6, m), (fx + 7, fy + 6, m), (fx + 3, fy + 7, m), (fx + 6, fy + 7, m),
              (fx + 4, fy + 6, m), (fx + 5, fy + 6, m)]
    lion_whiskers(d, fx, fy)


def lion_tail(cv, pts, tuft):
    """꼬리 + 끝 술 (밝은 윗면·진한 아랫면, 꼬리 방향으로 털 한 가닥)"""
    P = LION
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.limb(ax, ay, bx, by, P.FUR, w=1)
    tx, ty = tuft
    cv.rect(tx - 1, ty - 1, tx + 1, ty + 1, P.MANE)
    cv.put(tx - 1, ty - 1, P.MANE_TIP); cv.put(tx, ty - 1, P.MANE_HI); cv.put(tx - 1, ty, P.MANE_HI)
    cv.put(tx + 1, ty + 1, P.MANE_DK)
    ax, ay = pts[-1]
    if abs(ty - ay) >= abs(tx - ax):
        cv.put(tx, ty + (2 if ty > ay else -2), P.MANE_HI)
    else:
        cv.put(tx + (2 if tx > ax else -2), ty, P.MANE_HI)


def lion_body_side(cv, by, x0=8, x1=24, arch=0):
    P = LION
    cv.rect(x0, by, x1, by + 5)
    if arch:
        cv.rect(x0 + 3, by - arch, x1 - 4, by - 1)
    cv.cut((x0, by), (x0, by + 5), (x1, by + 5))
    top = by - arch
    cv.rect(x0 + 3 if arch else x0 + 2, top, x1 - 5, top, P.FUR_HI)          # 등 윤기
    cv.rect(x0 + 4, by + 4, x1 - 6, by + 4, P.FUR_DK)                         # 배 그늘
    cv.rect(x0 + 3, by + 5, x1 - 4, by + 5, P.LIGHT)
    cv.put(x0 + 2, by + 2, P.FUR_DK); cv.put(x0 + 3, by + 3, P.FUR_DK)       # 엉덩이 근육 결


def lion_leg(cv, t, k, f, far=False, thick=False):
    """사자 다리 + 도톰한 앞발 (발끝이 진행 방향으로 1칸 더, 발가락은 밝게). thick = 힘찬 허벅지·어깨 (달리기)"""
    P = LION
    c = P.FAR if far else P.FUR
    L = P.LIGHT_FAR if far else P.LIGHT
    cv.limb(*t, *k, c, 3 if thick else 2)
    cv.limb(*k, *f, c, 2)
    fx, fy = f
    kx, ky = k
    if abs(fx - kx) > abs(fy - ky):        # 누운 발: 아래로 한 칸
        cv.put(fx, fy + 2, L)
        cv.put(fx, fy + 1, L)
    else:
        cv.put(fx + 2, fy, L)
        cv.put(fx + 1, fy, L)


def lion_walk(frame, blink=False):
    P = LION
    cv = Cv(P)
    fx, fy = 20, 4
    bn, fn, bf, ff = WALK_POSE[frame]
    sw = (2, 3, 2, 1)[frame]
    for (x, s, up) in (bf, ff):
        lion_leg(cv, (x, 16), (x, 19), (x + s, 22 - up), far=True)
    lion_tail(cv, [(8, 12), (5, 12), (3, 10), (2 + sw, 6)], (2 + sw, 5))
    lion_body_side(cv, 11)
    lion_shoulder_mane(cv, 20, 11, phase=frame)
    for (x, s, up) in (bn, fn):
        lion_leg(cv, (x, 16), (x, 19), (x + s, 22 - up))
    lion_head(cv, fx, fy, lift=(0, 1, 0, 1)[frame], phase=frame * 0.55)
    d = []
    lion_face(d, fx, fy, blink=blink)
    return cv.image(d)


def lion_run(frame):
    """힘찬 도약 질주 6장: 공중 쭉 → 앞발 착지 → 앞발 지탱·뒷발 당김 → 웅크려 모으기 → 뒷발로 박차기 → 날아오르기.
    보폭이 크다 (앞발 끝 x≈31, 뒷발 끝 x≈3). 갈기는 보폭 따라 출렁, 꼬리 술은 휙휙"""
    P = LION
    cv = Cv(P)
    oy = (-2, -1, 0, 1, 0, -1)[frame]
    by = 11 + oy
    fx, fy = 20, 4 + max(oy, -1)
    lt = by + 4
    legs = [
        (((14, lt), (9, lt + 3), (5, lt + 6)),   ((20, lt), (25, lt + 3), (28, lt + 6)),
         ((12, lt), (7, lt + 3), (3, lt + 6)),   ((22, lt), (27, lt + 3), (31, lt + 5))),       # 0 공중 쭉
        (((14, lt), (10, lt + 3), (8, lt + 6)),  ((20, lt), (25, lt + 2), (29, lt + 4)),
         ((12, lt), (8, lt + 3), (6, lt + 6)),   ((22, lt), (25, lt + 4), (27, 22))),           # 1 앞발 착지
        (((14, lt), (13, lt + 3), (16, lt + 5)), ((20, lt), (23, lt + 4), (25, 22)),
         ((12, lt), (11, lt + 3), (14, lt + 6)), ((22, lt), (22, lt + 4), (21, 22))),           # 2 앞발 지탱, 뒷발 당겨옴
        (((14, lt), (15, lt + 3), (18, 22)),     ((20, lt), (23, lt + 2), (21, lt + 4)),
         ((12, lt), (13, lt + 3), (16, 22)),     ((22, lt), (25, lt + 2), (23, lt + 4))),       # 3 웅크려 모으기 (뒷발 앞으로, 앞발 접어 올림)
        (((14, lt), (13, lt + 3), (11, 22)),     ((20, lt), (24, lt + 2), (27, lt + 4)),
         ((12, lt), (11, lt + 3), (8, 22)),      ((22, lt), (26, lt + 2), (30, lt + 4))),       # 4 뒷발로 박차기
        (((14, lt), (10, lt + 3), (7, lt + 5)),  ((20, lt), (25, lt + 2), (28, lt + 4)),
         ((12, lt), (8, lt + 3), (4, lt + 6)),   ((22, lt), (27, lt + 2), (31, lt + 3))),       # 5 날아오르기
    ][frame]
    for t, k, f in legs[:2]:
        lion_leg(cv, t, k, f, far=True, thick=True)
    tails = [
        ([(8, by + 1), (5, by), (3, by - 2), (2, by - 4)], (2, by - 5)),
        ([(8, by + 1), (5, by), (3, by - 1), (2, by - 2)], (2, by - 3)),
        ([(8, by + 1), (5, by + 2), (3, by + 1), (2, by - 1)], (2, by - 2)),
        ([(9, by + 1), (6, by + 2), (4, by + 4), (3, by + 6)], (3, by + 7)),
        ([(8, by + 1), (5, by + 1), (3, by + 3), (2, by + 4)], (2, by + 5)),
        ([(8, by + 1), (5, by), (3, by - 2), (2, by - 3)], (2, by - 4)),
    ][frame]
    lion_tail(cv, *tails)
    x0 = (7, 8, 9, 10, 9, 7)[frame]
    lion_body_side(cv, by, x0, 24, arch=1 if frame == 3 else 0)
    lion_shoulder_mane(cv, 20, by, phase=frame, depth=(7, 7, 6, 5, 6, 7)[frame])
    for t, k, f in legs[2:]:
        lion_leg(cv, t, k, f, thick=True)
    lion_head(cv, fx, fy, sweep=(3, 2, 1, 0, 1, 3)[frame], lift=(2, 1, -1, -1, 1, 2)[frame], phase=frame * 0.5)
    d = []
    lion_face(d, fx, fy, mood="normal")
    return cv.image(d)


def lion_sit(mood="normal", blink=False):
    P = LION
    cv = Cv(P)
    fx, fy = 19, 4
    d = []
    lion_sit_body(cv, d)
    lion_head(cv, fx, fy)
    lion_face(d, fx, fy, mood=mood, blink=blink)
    return cv.image(d)


# ══════════════════════════════════════════════════════════════════════
# 말: 밤색 몸 + 진한 갈기·긴 꼬리, 이마 흰 줄, 흰 양말 한 짝, 발굽
# ══════════════════════════════════════════════════════════════════════
def horse_head(cv, hx, top):
    """3/4 정면 말 얼굴 9×9 (위가 넓고 아래 주둥이가 밝음) + 뾰족 귀(안쪽 진하게) + 앞머리 + 흰 줄"""
    P = HORSE
    F, M, U, B = P.FUR, P.MANE, P.MUZ, P.BLAZE
    cv.rect(hx + 1, top, hx + 7, top, F)
    cv.rect(hx, top + 1, hx + 8, top + 4, F)
    cv.rect(hx + 1, top + 5, hx + 7, top + 5, F)
    cv.put(hx, top + 4, P.FUR_DK); cv.put(hx + 8, top + 4, P.FUR_DK)          # 볼 그늘
    cv.put(hx + 1, top + 5, P.FUR_DK); cv.put(hx + 7, top + 5, P.FUR_DK)
    cv.put(hx + 2, top + 1, P.FUR_HI); cv.put(hx + 6, top + 1, P.FUR_HI)      # 눈두덩 윤기
    cv.rect(hx + 1, top + 6, hx + 7, top + 7, U)
    cv.rect(hx + 2, top + 8, hx + 6, top + 8, U)
    cv.put(hx + 1, top + 7, P.MUZ_DK); cv.put(hx + 7, top + 7, P.MUZ_DK)      # 주둥이 그늘
    cv.put(hx + 2, top + 8, P.MUZ_DK); cv.put(hx + 6, top + 8, P.MUZ_DK)
    for ox, s in ((hx + 1, 1), (hx + 7, -1)):              # 뾰족 귀
        cv.put(ox, top - 2)
        cv.rect(ox, top - 1, ox + s, top - 1)
        cv.put(ox + s, top - 1, P.EAR_IN)
    cv.rect(hx + 3, top - 1, hx + 5, top, M)               # 앞머리
    cv.rect(hx + 3, top + 1, hx + 4, top + 1, M)
    cv.put(hx + 4, top - 1, P.MANE_HI); cv.put(hx + 3, top, P.MANE_DK)
    cv.rect(hx + 4, top + 2, hx + 4, top + 4, B)           # 흰 줄
    cv.rect(hx + 3, top + 5, hx + 5, top + 5, B)


def horse_face(d, hx, top, mood="normal", blink=False):
    P = HORSE
    eyes(d, P, (hx + 2, hx + 6), top + 2, mood, blink)
    d += [(hx + 2, top + 7, P.NOSTRIL), (hx + 6, top + 7, P.NOSTRIL)]   # 콧구멍 점 두 개
    m = P.MOUTH
    if mood in ("talk", "surprised"):
        d += [(hx + 3, top + 8, m), (hx + 4, top + 8, P.MOUTH_IN), (hx + 5, top + 8, m)]
    elif mood == "happy":
        d += [(hx + 2, top + 8, m), (hx + 3, top + 8, P.MOUTH_IN), (hx + 4, top + 8, P.MOUTH_IN), (hx + 5, top + 8, P.MOUTH_IN),
              (hx + 6, top + 8, m)]
    else:
        d += [(hx + 3, top + 8, m), (hx + 4, top + 8, m), (hx + 5, top + 8, m)]


def horse_neck(cv, hx, top, by, wx=16, stream=0, phase=0):
    """목: 머리 왼쪽(hx, top+2) → 기갑(wx, by)으로 비스듬히. 목덜미 쪽에 진한 갈기 (가닥 결이 걸음마다 흐름),
    목덜미 윤기. stream = 뒤로 휘날리는 길이"""
    P = HORSE
    y0, y1 = top + 2, by + 1
    for y in range(y0, y1 + 1):
        t = (y - y0) / max(1, y1 - y0)
        xl = round(hx - 2 - t * (hx - 2 - wx))
        cv.rect(xl, y, xl + 5, y)
        cv.put(xl, y, P.FUR_HI)
        k = (y + phase) % 3
        cv.put(xl - 2, y, P.MANE_HI if k == 0 else P.MANE)
        cv.put(xl - 1, y, P.MANE_DK if k == 1 else P.MANE)
        if stream and (y + phase) % 2 == 0:
            n = stream + ((y + phase) // 2) % 2
            cv.rect(xl - 2 - n, y, xl - 3, y, P.MANE)
            cv.put(xl - 2 - n, y, P.MANE_HI)
    cv.rect(hx - 2, top, hx, top + 2, P.MANE)              # 귀 뒤 갈기
    cv.put(hx - 1, top, P.MANE_HI)


def horse_body(cv, by, x0=7, x1=21, pitch=0):
    """몸통 (pitch>0 = 앞이 들림). 엉덩이·가슴은 둥글게, 등 윤기 · 배 그늘 · 엉덩이와 어깨 근육 결"""
    P = HORSE
    tops = {}
    for x in range(x0, x1 + 1):
        t = (x - x0) / (x1 - x0)
        yt = by - round(pitch * t)
        tops[x] = yt
        y0, y1 = yt, yt + 5
        if x in (x0, x1):
            y0, y1 = y0 + 1, y1 - 1
        cv.rect(x, y0, x, y1)
        if x0 + 2 <= x <= x1 - 3:
            cv.put(x, yt, P.FUR_HI)
        if x0 + 4 <= x <= x1 - 4:
            cv.put(x, yt + 5, P.FUR_DK)
    yt = by - pitch
    cv.rect(x1 + 1, yt + 2, x1 + 1, yt + 3)                # 가슴 볼록
    for dx, dy in ((3, 1), (4, 2), (4, 3)):                # 엉덩이 근육 결
        cv.put(x0 + dx, tops[x0 + dx] + dy, P.FUR_DK)
    for dx, dy in ((-3, 1), (-3, 2), (-2, 3)):             # 어깨 근육 결
        cv.put(x1 + dx, tops[x1 + dx] + dy, P.FUR_DK)


def horse_tail(cv, pts, ws, hi=True, phase=0):
    """꼬리: 진한 갈기색 + 밝은 가닥·더 진한 가닥 (phase 로 가닥 결이 흐름)"""
    P = HORSE
    t = Cv(P)
    for i, ((ax, ay), (bx, by)) in enumerate(zip(pts, pts[1:])):
        t.limb(ax, ay, bx, by, P.MANE, ws[min(i, len(ws) - 1)])
    if hi:   # 꼬리 결 (밝은 한 가닥)
        for (ax, ay), (bx, by) in zip(pts[1:-1], pts[2:]):
            t.limb(ax, ay, bx, by, P.MANE_HI, 1)
        for (x, y), c in list(t.px.items()):
            if c == P.MANE and (x + y + phase) % 4 == 0 and (x - 1, y) in t.px and (x + 1, y) in t.px:
                t.px[(x, y)] = P.MANE_DK
    cv.px.update(t.px)


def horse_walk(frame, blink=False):
    P = HORSE
    cv = Cv(P)
    by = 9
    hx, top = 23, 3 + (0, 1, 0, 1)[frame]
    sw = (0, 1, 0, -1)[frame]
    bn, fn, bf, ff = WALK_POSE[frame]
    hip, sh = -1, 0             # 다리 x 보정 (몸이 왼쪽으로 1칸 이동)
    for (x, s, up), hind in ((bf, True), (ff, False)):
        x += hip if hind else sh
        knee = (x - 1, 18 - up) if hind else (x + (1 if s > 0 else 0), 18 - up)
        cv.leg2((x, 14), knee, (x + s, 22 - up), P.FAR, tip=P.HOOF)
    horse_tail(cv, [(7, by + 1), (4, by + 2), (3 + sw, by + 5), (3 + sw, by + 9), (4 + sw, by + 12)], (3, 3, 2, 2), phase=frame)
    horse_neck(cv, hx, top, by, phase=frame)
    horse_body(cv, by)
    for (x, s, up), hind in ((bn, True), (fn, False)):
        x += hip if hind else sh
        knee = (x - 1, 18 - up) if hind else (x + (1 if s > 0 else 0), 18 - up)
        cv.leg2((x, 14), knee, (x + s, 22 - up), tip=P.HOOF)
        if hind:   # 뒷다리 흰 양말
            cv.rect(x + s, 21 - up, x + s + 1, 21 - up, P.SOCK)
    horse_head(cv, hx, top)
    d = []
    horse_face(d, hx, top, blink=blink)
    return cv.image(d)


def horse_run(frame):
    """택시 미터기 말 전력 갤럽 8장.
    0 공중 쭉(앞발 앞으로·뒷발 뒤로) → 1 앞발 착지 → 2 앞발 지탱(몸 낮게) → 3 앞발 밀기·뒷발 당김
    → 4 네 다리 모아 공중(몸 가장 높이) → 5 뒷발 착지 → 6 뒷발 지탱·앞발 뻗기 → 7 뒷발 박차기"""
    P = HORSE
    cv = Cv(P)
    oy = (-1, 0, 1, 0, -2, -1, 0, -1)[frame]
    pitch = (0, -1, -1, -1, 0, 1, 1, 1)[frame]
    by = 9 + oy
    hx = 23
    top = (3, 4, 5, 4, 3, 3, 3, 3)[frame]
    hl = by + 4                 # 엉덩이 관절 높이
    fl = by + 4 - pitch         # 어깨 관절 높이
    G = 22
    # 다리: (위, 무릎/비절, 발굽) — 뒤-먼, 앞-먼, 뒤-가까운, 앞-가까운
    legs = [
        (((12, hl), (8, hl + 4), (5, hl + 7)),     ((18, fl), (22, fl + 4), (24, fl + 7)),
         ((10, hl), (6, hl + 3), (2, hl + 6)),     ((20, fl), (24, fl + 3), (28, fl + 6))),     # 0 공중 쭉
        (((12, hl), (9, hl + 4), (7, hl + 7)),     ((18, fl), (22, fl + 3), (26, fl + 5)),
         ((10, hl), (7, hl + 3), (4, hl + 6)),     ((20, fl), (23, fl + 4), (25, G))),          # 1 앞발 착지
        (((12, hl), (10, hl + 3), (13, hl + 5)),   ((18, fl), (21, fl + 3), (23, G)),
         ((10, hl), (8, hl + 3), (11, hl + 6)),    ((20, fl), (21, fl + 3), (21, G))),          # 2 앞발 지탱
        (((12, hl), (13, hl + 3), (16, hl + 5)),   ((18, fl), (19, fl + 4), (20, G)),
         ((10, hl), (10, hl + 4), (13, hl + 6)),   ((20, fl), (19, fl + 4), (17, G))),          # 3 앞발 밀기, 뒷발 앞으로
        (((12, hl), (11, hl + 4), (15, hl + 6)),   ((18, fl), (21, fl + 4), (18, fl + 6)),
         ((10, hl), (9, hl + 4), (13, hl + 6)),    ((20, fl), (23, fl + 3), (20, fl + 6))),     # 4 네 다리 모아 공중
        (((12, hl), (12, hl + 4), (14, G)),        ((18, fl), (21, fl + 3), (22, fl + 6)),
         ((10, hl), (10, hl + 4), (13, hl + 8)),   ((20, fl), (23, fl + 3), (25, fl + 6))),     # 5 뒷발 착지
        (((12, hl), (11, hl + 4), (8, G)),         ((18, fl), (22, fl + 3), (25, fl + 6)),
         ((10, hl), (10, hl + 4), (10, G)),        ((20, fl), (24, fl + 3), (27, fl + 6))),     # 6 뒷발 지탱, 앞발 뻗기
        (((12, hl), (8, hl + 3), (5, hl + 6)),     ((18, fl), (22, fl + 4), (26, fl + 7)),
         ((10, hl), (7, hl + 4), (4, G)),          ((20, fl), (24, fl + 3), (28, fl + 6))),     # 7 뒷발 박차기
    ][frame]
    for t, k, f in legs[:2]:
        cv.leg2(t, k, f, P.FAR, tip=P.HOOF)
    # 꼬리: 뒤로 길게 휘날림 (물결 — 끝이 위아래로 출렁)
    wv = (0, 1, 2, 1, -1, -1, 0, 0)[frame]
    horse_tail(cv, [(7, by + 1), (4, by), (3, by + 1 + (wv > 0)), (2, by + 2 + wv)], (3, 3, 2), phase=frame)
    horse_neck(cv, hx, top, by - pitch, stream=3, phase=frame)
    horse_body(cv, by, pitch=pitch)
    for i, (t, k, f) in enumerate(legs[2:]):
        cv.leg2(t, k, f, tip=P.HOOF)
        if i == 0:   # 뒷다리 흰 양말 (발굽 바로 위)
            fx_, fy_ = f
            kx_, ky_ = k
            if abs(fx_ - kx_) > abs(fy_ - ky_):
                sx = 1 if fx_ < kx_ else -1
                cv.rect(fx_ + sx, fy_, fx_ + sx, fy_ + 1, P.SOCK)
            else:
                cv.rect(fx_, fy_ - 1, fx_ + 1, fy_ - 1, P.SOCK)
    horse_head(cv, hx, top)
    d = []
    horse_face(d, hx, top)
    return cv.image(d)


def horse_stand(mood="normal", blink=False, swish=0):
    P = HORSE
    cv = Cv(P)
    hx, top = 23, 3
    by = 9
    cv.leg2((11, 14), (10, 18), (11, 22), P.FAR, tip=P.HOOF)
    cv.leg2((18, 14), (18, 18), (18, 22), P.FAR, tip=P.HOOF)
    horse_tail(cv, [(7, by + 1), (4, by + 2), (2 + swish, by + 5), (2 + swish, by + 9), (3 + swish, by + 12)], (3, 3, 2, 2),
               phase=swish)
    horse_neck(cv, hx, top, by)
    horse_body(cv, by)
    cv.leg2((9, 14), (8, 18), (9, 22), tip=P.HOOF)
    cv.rect(9, 21, 10, 21, P.SOCK)
    cv.leg2((20, 14), (20, 18), (20, 22), tip=P.HOOF)
    horse_head(cv, hx, top)
    d = []
    horse_face(d, hx, top, mood=mood, blink=blink)
    return cv.image(d)


# ══════════════════════════════════════════════════════════════════════
# 살금살금 (위험 구간 앞에서 두 발로 서서 까치발로 지나가기) — 고양이_오마주.py의 sneak와 같은 뼈대
# ══════════════════════════════════════════════════════════════════════
SNEAK_STEP = [("sup", "lift"), ("rear", "front"), ("lift", "sup"), ("front", "rear")]   # (먼 다리, 가까운 다리)


def sneak_overlay(cv, d, sub, against=None):
    """겹친 팔다리: sub의 칸을 몸 위에 얹고, 이미 있던 몸(against를 주면 그 칸만)과 맞닿는 곳에 외곽선 1칸"""
    against = cv.px if against is None else against
    for (x, y) in sub.px:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in cv.px and n in against and n not in sub.px:
                d.append((n[0], n[1], cv.p.LINE))
    d[:] = [p for p in d if (p[0], p[1]) not in sub.px]
    cv.px.update(sub.px)


def sneak_leg(c, kind, col, tip, hip=17):
    """lift = 무릎을 엉덩이 높이로 들고 발끝은 아래로(공중) / sup = 몸 밑에서 까치발 / front·rear = 앞·뒤로 디딘 까치발.
    발끝 1칸을 뾰족하게 (tip = 발끝·양말 색)"""
    if kind == "lift":
        c.rect(18, hip, 23, hip + 1, col)        # 허벅지 (무릎을 몸 앞으로 번쩍)
        c.rect(22, hip + 2, 23, hip + 2, tip)    # 정강이 끝
        c.put(22, hip + 3, tip)                  # 뾰족 발끝 (땅에서 2칸 뜸)
        return
    t, k, f = {"sup": ((15, hip), (16, 19), (15, 21)),
               "front": ((18, hip), (20, 19), (20, 21)), "rear": ((15, hip), (14, 19), (13, 21))}[kind]
    c.limb(*t, *k, col)
    c.limb(*k, *f, col)
    c.rect(f[0], f[1], f[0] + 1, f[1], tip)
    c.put(f[0] + 1, f[1] + 1, tip)


def sneak_eyes(d, P, xs, ey, look):
    """반쯤 감은 눈꺼풀(가로 2칸) 아래 눈동자 1칸이 한쪽으로 힐끔 (look = -1 뒤, 0 앞)"""
    d[:] = [p for p in d if p[2] != P.EYE]
    for ex in xs:
        d += [(ex - 1, ey, P.LINE), (ex, ey, P.LINE), (ex + look, ey + 1, P.EYE)]


def dog_sneak(frame):
    """강아지 살금살금: 몸을 세워 앞으로 살짝 숙이고 크림 앞발 두 짝을 가슴 앞에 축 늘어뜨린 채 까치발"""
    P = DOG
    cv = Cv(P)
    d = []
    up = (0, 1, 0, 1)[frame]
    hx, top = 18, 4 + up
    far_k, near_k = SNEAK_STEP[frame]
    sneak_leg(cv, far_k, P.FAR, P.CREAM_FAR)
    sw = (0, 0, -1, -1)[frame]
    cv.limb(14, 16, 12, 14)                                  # 엉덩이 → 말린 꼬리
    dog_tail(cv, 8 + sw, 9 + up)
    fp = (0, 1, 0, 1)[frame]
    cv.rect(23, top + 11, 28 + fp, top + 11, P.FAR)          # 먼 앞발
    cv.rect(28 + fp, top + 11, 29 + fp, top + 13, P.CREAM_FAR)
    cv.rect(17, top + 7, 23, 14)                             # 몸통 (위가 앞으로 기욺)
    cv.rect(15, 14, 22, 15)
    cv.rect(14, 16, 20, 17)
    cv.rect(15, 18, 19, 18)
    cv.cut((22, 15), (14, 17), (15, 14))
    cv.rect(21, top + 10, 23, 14, P.CREAM)                   # 크림 가슴·배
    cv.rect(20, 15, 21, 15, P.CREAM)
    cv.rect(19, 16, 20, 17, P.CREAM)
    np_ = (0, -1, 0, 1)[frame]
    cv.rect(23, top + 11, 26 + np_, top + 12)                # 가까운 앞발: 손목이 축
    cv.rect(26 + np_, top + 12, 27 + np_, top + 14, P.CREAM)
    dog_head(cv, hx, top)
    sub = Cv(P)                                              # 가까운 다리 (맨 앞, 겹치면 외곽선)
    sneak_leg(sub, near_k, P.FUR, P.CREAM)
    sneak_overlay(cv, d, sub)
    dog_face(d, hx, top)
    sneak_eyes(d, P, (hx + 3, hx + 8), top + 3, -1 if frame < 2 else 0)
    d += [(x, top + 10, P.COLLAR) for x in range(hx - 1, hx + 6) if (x, top + 10) in cv.px]   # 목걸이 + 이름표
    d += [(hx + 3, top + 11, SHINE), (hx + 4, top + 11, P.TAG)]
    return cv.image(d)


def lion_sneak(frame):
    """사자 살금살금: 갈기 아래로 몸을 세워 앞으로 살짝 숙이고 밝은 앞발을 가슴 앞에 축 늘어뜨린 채 까치발, 꼬리 술은 위로"""
    P = LION
    cv = Cv(P)
    d = []
    up = (0, 1, 0, 1)[frame]
    fx, fy = 20, 4 + up
    far_k, near_k = SNEAK_STEP[frame]
    sneak_leg(cv, far_k, P.FAR, P.FAR)
    sw = (0, 0, -1, -1)[frame]
    lion_tail(cv, [(14, 16), (11, 15), (10, 12), (10 + sw, 8 + up)], (10 + sw, 7 + up))
    cv.rect(16, 11, 23, 14)                                  # 몸통 (갈기에 위가 가려짐)
    cv.rect(15, 14, 22, 15)
    cv.rect(14, 16, 20, 17)
    cv.rect(15, 18, 19, 18)
    cv.cut((22, 15), (14, 17))
    cv.rect(20, 15, 21, 15, P.LIGHT)                         # 밝은 배
    cv.rect(19, 16, 20, 17, P.LIGHT)
    lion_head(cv, fx, fy, lift=up, phase=frame * 0.3)
    fp = (0, 1, 0, 1)[frame]
    np_ = (0, -1, 0, 1)[frame]
    far_arm = Cv(P)                                          # 먼 앞발 (갈기 바로 밑, 가까운 앞발보다 앞으로)
    far_arm.rect(24, fy + 11, 29 + fp, fy + 11, P.FAR)
    far_arm.rect(29 + fp, fy + 11, 30 + fp, fy + 13, P.FAR)
    far_arm.rect(29 + fp, fy + 13, 30 + fp, fy + 13, P.LIGHT)
    sneak_overlay(cv, d, far_arm)
    arm = Cv(P)                                              # 가까운 앞발: 갈기 밑 가슴 앞에 들고 손목이 축
    arm.rect(22, fy + 11, 26 + np_, fy + 12)
    arm.rect(26 + np_, fy + 12, 27 + np_, fy + 14)
    arm.rect(26 + np_, fy + 13, 27 + np_, fy + 14, P.LIGHT)
    sneak_overlay(cv, d, arm, far_arm.px)
    sub = Cv(P)                                              # 가까운 다리 (맨 앞, 겹치면 외곽선)
    sneak_leg(sub, near_k, P.FUR, P.FUR)
    sneak_overlay(cv, d, sub)
    lion_face(d, fx, fy)
    sneak_eyes(d, P, (fx + 2, fx + 7), fy + 3, -1 if frame < 2 else 0)
    return cv.image(d)


def dog_post(px):
    """강아지 마무리: 땅에 닿은 크림 발의 뒤꿈치 1칸을 그늘색으로 (발 모양이 또렷하게)"""
    P = DOG
    for (x, y), c in list(px.items()):
        if y == 22 and c in (P.CREAM, P.CREAM_FAR) and px.get((x - 1, y)) != c and px.get((x + 1, y)) == c:
            px[(x, y)] = P.CREAM_SH if c == P.CREAM else P.CREAM_FAR_SH


def horse_post(px):
    """말 마무리: 흰 양말 다리의 발굽은 밝은 뿔색, 나머지 발굽은 앞쪽 1칸에 윤기"""
    P = HORSE
    pale = set()
    for (x, y), c in list(px.items()):
        if c == P.HOOF and any(px.get(n) == P.SOCK for n in ((x, y - 1), (x - 1, y), (x + 1, y), (x - 1, y - 1), (x + 1, y - 1))):
            pale.add((x, y))
    grow = True
    while grow:                                      # 같은 발굽 덩어리 전체를 밝게
        grow = False
        for (x, y) in list(pale):
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if px.get(n) == P.HOOF and n not in pale:
                    pale.add(n)
                    grow = True
    for p in pale:
        px[p] = P.HOOF_PALE
    for (x, y), c in list(px.items()):
        if c == P.HOOF and px.get((x + 1, y)) != P.HOOF and px.get((x - 1, y)) == P.HOOF:
            px[(x, y)] = P.HOOF_HI


def dog_sit_body(cv, d):
    """앉은 몸 (꼬리·엉덩이·몸·앞다리) — 기본 자세와 행동 시트가 같이 쓴다"""
    P = DOG
    dog_tail(cv, 7, 12)                     # 엉덩이 위 말린 꼬리
    cv.rect(10, 15, 19, 22)                 # 엉덩이 (둥글게)
    cv.cut((10, 15), (11, 15), (10, 16))
    cv.rect(12, 15, 15, 15, P.FUR_HI)       # 엉덩이 윤기
    cv.rect(10, 21, 14, 22, P.CREAM)        # 뒷발
    cv.rect(16, 12, 27, 22)                 # 몸통 (세움)
    cv.rect(19, 14, 26, 17, P.CREAM)        # 크림 가슴
    cv.rect(20, 18, 25, 18, P.CREAM)
    cv.put(27, 15, P.CREAM); cv.put(28, 16, P.CREAM)                         # 가슴 털 복슬
    cv.rect(20, 18, 21, 22, P.FAR); cv.rect(20, 21, 21, 22, P.CREAM_FAR)     # 먼 앞다리
    cv.rect(22, 18, 23, 20, P.CREAM_FAR)                                     # 앞다리 사이 (안쪽 크림)
    cv.rect(24, 18, 25, 22); cv.rect(24, 21, 25, 22, P.CREAM)                # 가까운 앞다리
    cv.rect(16, 19, 19, 20, P.FUR_DK)                                        # 허벅지 아래 그늘
    d += [(14, 17, P.FAR), (15, 18, P.FAR), (15, 19, P.FAR), (15, 20, P.FAR)]      # 뒷다리 허벅지 결


def dog_front_collar(d, hx, top, glint=True):
    """앉은 모습(정면) 목걸이 + 이름표 (반짝)"""
    P = DOG
    d += [(x, top + 10, P.COLLAR) for x in range(hx + 2, hx + 10)]
    d += [(hx + 5, top + 11, SHINE if glint else P.TAG), (hx + 6, top + 11, P.TAG), (hx + 5, top + 12, P.TAG_DK), (hx + 6, top + 12, P.TAG_DK)]


def lion_whiskers(d, fx, fy):
    """수염 자리 점 + 갈기 위로 빼꼼 나온 흰 수염 (가로 두 칸)"""
    P = LION
    d += [(fx + 1, fy + 6, P.WHISK_DOT), (fx + 8, fy + 6, P.WHISK_DOT)]
    d += [(fx - 1, fy + 6, P.WHISK), (fx - 2, fy + 6, P.WHISK), (fx + 10, fy + 6, P.WHISK), (fx + 11, fy + 6, P.WHISK)]


def lion_sit_body(cv, d, chest=True):
    """앉은 몸 (꼬리·엉덩이·몸·앞다리·가슴 갈기) — 기본 자세와 행동 시트가 같이 쓴다"""
    P = LION
    lion_tail(cv, [(12, 22), (8, 22), (5, 22), (3, 20)], (3, 19))
    cv.rect(10, 15, 19, 22)                                 # 엉덩이 (둥글게)
    cv.cut((10, 15), (11, 15), (10, 16))
    cv.rect(12, 15, 15, 15, P.FUR_HI)                       # 엉덩이 윤기
    cv.rect(10, 21, 14, 22, P.LIGHT)                        # 뒷발
    cv.put(12, 22, P.LIGHT_FAR)                             # 발가락 사이
    cv.rect(16, 12, 27, 22)                                 # 몸통 (세움)
    cv.rect(22, 17, 23, 21, P.LIGHT)                        # 앞다리 사이 가슴·배 (밝게)
    cv.rect(20, 17, 21, 22, P.FAR); cv.put(22, 22, P.LIGHT_FAR); cv.put(21, 22, P.LIGHT_FAR)   # 먼 앞다리 + 앞발
    cv.rect(24, 17, 25, 22); cv.put(26, 22, P.LIGHT); cv.put(25, 22, P.LIGHT)                  # 가까운 앞다리 + 앞발
    cv.rect(16, 19, 19, 20, P.FUR_DK)                       # 허벅지 아래 그늘
    if chest:                                               # 가슴까지 늘어진 갈기 (가닥 + 들쭉날쭉한 아랫단)
        for x in range(17, 27):
            s = x % 3
            for y in range(13, 17):
                c = P.MANE_HI if (s == 0 and y < 16) else (P.MANE_DK if (s == 2 and y > 13) else P.MANE)
                cv.put(x, y, c)
            if x % 2 == 0 and 18 <= x <= 25:
                cv.put(x, 17, P.MANE_HI if x % 4 == 0 else P.MANE)
        cv.cut((17, 16), (26, 16))
    d += [(16, 18, P.FAR), (17, 19, P.FAR), (17, 20, P.FAR), (17, 21, P.FAR)]      # 뒷다리 허벅지 결


POST = {id(DOG): dog_post, id(HORSE): horse_post}


def lion_shoulder_mane(cv, xr, by, phase=0, depth=6, drop=5):
    """어깨·가슴 갈기 (진짜 수사자처럼 목·어깨를 덮고 가슴 밑으로 늘어짐): 아래로 늘어진 털 가닥(밝은 가닥·진한 골),
    뒤쪽 끝과 아랫단은 들쭉날쭉한 술 — phase 로 걸음마다 술이 출렁"""
    P = LION
    bottom = by + drop
    for y in range(by - 1, bottom + 1):
        jag = (y + phase) % 3
        xl = xr - depth + (1 if jag == 0 else 0) + (2 if y == by - 1 else 0) + (1 if y == bottom else 0)
        for x in range(xl, xr + 1):
            s = (x + phase) % 3
            if s == 0 and y < bottom:
                c = P.MANE_HI                                 # 밝은 가닥
            elif s == 2 and y > by:
                c = P.MANE_DK                                 # 가닥 사이 골
            else:
                c = P.MANE
            cv.put(x, y, c)
        cv.put(xl, y, P.MANE_TIP if jag == 1 else P.MANE_HI)  # 뒤쪽 술 끝
    for x in range(xr - depth + 2, xr + 1):                   # 아랫단 술 (한 칸씩 들쭉날쭉)
        if (x + phase) % 2 == 0:
            cv.put(x, bottom + 1, P.MANE if (x + phase) % 4 else P.MANE_HI)


# ══════════════════════════════════════════════════════════════════════
def sheets():
    return {
        "dog": {
            "walk": [dog_walk(i) for i in range(4)],
            "run": [dog_run(i) for i in range(6)],
            "idle": [dog_sit(), dog_sit(blink=True)],
            "face": [dog_sit("talk"), dog_sit("surprised"), dog_sit("happy")],
            "sneak": [dog_sneak(i) for i in range(4)],
        },
        "lion": {
            "walk": [lion_walk(i) for i in range(4)],
            "run": [lion_run(i) for i in range(6)],
            "idle": [lion_sit(), lion_sit(blink=True)],
            "face": [lion_sit("talk"), lion_sit("surprised"), lion_sit("happy")],
            "sneak": [lion_sneak(i) for i in range(4)],
        },
        "horse": {
            "walk": [horse_walk(i) for i in range(4)],
            "run": [horse_run(i) for i in range(8)],
            "idle": [horse_stand(), horse_stand(blink=True, swish=1)],
            "face": [horse_stand("talk"), horse_stand("surprised"), horse_stand("happy")],
        },
    }


def main(out, preview=None):
    os.makedirs(out, exist_ok=True)
    all_ = sheets()
    for name, kinds in all_.items():
        for kind, frames in kinds.items():
            sheet = Image.new("RGBA", (W * len(frames), H), CLEAR)
            for i, f in enumerate(frames):
                sheet.alpha_composite(f, (i * W, 0))
            sheet.save(os.path.join(out, f"{name}_{kind}.png"))
            print(f"{name}_{kind}.png  {len(frames)}프레임")
    if not preview:
        return
    S, G, LBL = 6, 10, 70
    rows = [(f"{n} {k}", fr) for n, kinds in all_.items() for k, fr in kinds.items()]
    maxn = max(len(fr) for _, fr in rows)
    pw = LBL + (W * S + G) * maxn + G
    ph = (H * S + G) * len(rows) + G
    prev = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
    dr = ImageDraw.Draw(prev)
    for r, (label, frames) in enumerate(rows):
        y = G + r * (H * S + G)
        dr.text((6, y + H * S // 2 - 6), label, fill=(60, 60, 60, 255))
        for i, f in enumerate(frames):
            prev.alpha_composite(f.resize((W * S, H * S), Image.NEAREST), (LBL + i * (W * S + G), y))
    os.makedirs(os.path.dirname(os.path.abspath(preview)), exist_ok=True)
    prev.save(preview)
    print("미리보기:", preview)


if __name__ == "__main__":
    main(*sys.argv[1:3])
