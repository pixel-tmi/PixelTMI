"""
Pixel TMI 동물 3종 (강아지·사자·말) 행동 시트 — 동물_오마주.py 의 몸·머리·색을 그대로 가져다 '진짜 자세'를 그린다.
앱은 대기 동작 <act> 를 하는 동안 pet/<id>_<act>.png 가 있으면 그 그림을 재생하고, 몸 기울이기·늘이기는 뺀다.
  · 2장 = 200ms 마다 번갈아 반복
  · 3장 (howl·roar·yawn·rear) = 순서대로 한 번 → 마지막 장 유지
  · nap·doze 3장 = 0번은 눕기(졸기 시작), 그 뒤 1·2번 번갈아 (숨 쉬기)
규칙: 한 장 34×24 · 오른쪽을 본다 · 기본 시트와 같은 색·몸 크기·땅 높이(발바닥 y=22) · 자동 외곽선 1칸
      · 좌우 1칸 여백 (x=0·33 은 비움) · 흙먼지·음파·땀 같은 효과는 외곽선 없이

사용: python 동물_행동시트.py <출력 폴더> [미리보기.png] [--덮어쓰기] [--전후=<기본 시트 백업 폴더>]
  이미 있는 파일은 건드리지 않는다 (--덮어쓰기 를 줄 때만 새로 씀).
  --전후 를 주면 미리보기 아래에 기본 시트(walk·run·idle·face·sneak) 전(백업)/후(동물_오마주.py 지금 결과) 비교를 붙인다.
  몸·머리·색은 모두 동물_오마주.py 에서 가져오므로, 기본 시트를 고치면 이 스크립트도 다시 돌려 행동 시트를 맞춘다.
출력: dog_wag·dig·sniff·scratch·bow·howl·rollover / lion_roar·yawn·nap·stalk·mane·claws /
      horse_rear·graze·swish·dustroll·stomp·doze
"""
import importlib.util
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("animal_base", os.path.join(_HERE, "동물_오마주.py"))
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)

W, H = A.W, A.H
CLEAR = A.CLEAR
SHINE = A.SHINE
DOG, LION, HORSE = A.DOG, A.LION, A.HORSE

# ── 효과 색 (외곽선 없이) ─────────────────────────────────────────────────
ACT_LINE = (150, 162, 186, 255)      # 음파·움직임 자국 (흰 바탕·어두운 바탕 둘 다 보이게)
DIRT = (150, 98, 58, 255)            # 흙
DIRT_HI = (188, 134, 84, 255)
DIRT_DK = (110, 70, 42, 255)
DUST = (214, 190, 150, 255)          # 흙먼지
DUST_HI = (236, 220, 188, 255)
DUST_DK = (178, 150, 112, 255)
GRASS = (88, 170, 64, 255)
GRASS_DK = (54, 120, 44, 255)
GRASS_HI = (150, 210, 98, 255)
CLAW = (252, 250, 240, 255)          # 사자 발톱
FANG = (252, 252, 246, 255)
FLY = (40, 40, 48, 255)
FLY_WING = (200, 226, 246, 255)
TEAR = (124, 200, 255, 255)


# ══════════════════════════════════════════════════════════════════════
# 캔버스 (동물_오마주.Cv + 모양 몇 개 + 효과 층)
# ══════════════════════════════════════════════════════════════════════
class Cv(A.Cv):
    def __init__(self, pal):
        super().__init__(pal)
        self.d = []          # 얼굴 같은 세부 (외곽선 없음, 몸 위에)
        self.fx = []         # 효과: 빈 칸에만 (몸 뒤)
        self.top = []        # 효과: 맨 위

    def ellipse(self, cx, cy, rx, ry, c=None):
        c = c or self.p.FUR
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.px[(x, y)] = c

    def capsule(self, x0, y0, x1, y1, r0, r1=None, c=None):
        """선분 (x0,y0)→(x1,y1) 둘레 반지름 r0→r1 안의 칸을 칠함 (기울어진 몸통·목)"""
        r1 = r0 if r1 is None else r1
        c = c or self.p.FUR
        L2 = (x1 - x0) ** 2 + (y1 - y0) ** 2 or 1e-9
        R = max(r0, r1)
        for y in range(int(min(y0, y1) - R) - 1, int(max(y0, y1) + R) + 2):
            for x in range(int(min(x0, x1) - R) - 1, int(max(x0, x1) + R) + 2):
                t = max(0.0, min(1.0, ((x - x0) * (x1 - x0) + (y - y0) * (y1 - y0)) / L2))
                px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                if math.hypot(x - px, y - py) <= r0 + (r1 - r0) * t:
                    self.px[(x, y)] = c

    def art(self, x0, y0, rows, pal):
        """문자 그림 (pal: 글자 → 색, '.'·' ' 는 빈칸)"""
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch in pal:
                    self.px[(x0 + i, y0 + j)] = pal[ch]

    def over(self, sub, against=None):
        """sub 를 맨 앞에 얹고, 이미 있던 몸과 맞닿는 곳에 외곽선 1칸 (겹친 다리·앞발)"""
        A.sneak_overlay(self, self.d, sub, against)
        self.d.extend(sub.d)
        sub.d = []
        self.fx.extend(sub.fx)
        self.top.extend(sub.top)

    def image(self, details=()):
        im = super().image(list(self.d) + list(details))
        for x, y, c in self.fx:
            if 0 <= x < W and 0 <= y < H and im.getpixel((x, y))[3] == 0:
                im.putpixel((x, y), c)
        for x, y, c in self.top:
            if 0 <= x < W and 0 <= y < H:
                im.putpixel((x, y), c)
        return im


def line(L, x0, y0, x1, y1, c=ACT_LINE):
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(steps + 1):
        L.append((round(x0 + (x1 - x0) * i / steps), round(y0 + (y1 - y0) * i / steps), c))


def puff(L, cx, cy, r, cols=(DUST, DUST_HI, DUST_DK)):
    """흙먼지 뭉게 (외곽선 없음): 위쪽 밝게, 아래 테 진하게"""
    base, hi, dk = cols
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            dd = math.hypot(x - cx, y - cy)
            if dd <= r:
                c = dk if dd > r - 0.9 and y >= cy else (hi if (y < cy - r * 0.3 and x < cx + r * 0.3) else base)
                L.append((x, y, c))


def pts(L, items, c):
    for x, y in items:
        L.append((x, y, c))


def shine_edge(cv, x0, x1, base, col, bottom=False):
    """x0~x1 각 줄에서 base 색의 맨 위(bottom=True 면 맨 아래) 칸을 col 로 — 기울어진 몸에도 등 윤기·배 그늘"""
    for x in range(x0, x1 + 1):
        ys = [y for (xx, y), c in cv.px.items() if xx == x and c == base]
        if ys:
            cv.px[(x, max(ys) if bottom else min(ys))] = col


# ══════════════════════════════════════════════════════════════════════
# 강아지
# ══════════════════════════════════════════════════════════════════════
DOG_STAND_LEGS = ((10, 0, 0), (20, 0, 0), (12, 0, 0), (18, 0, 0))    # 뒤-가까운, 앞-가까운, 뒤-먼, 앞-먼


def dog_tail_at(cv, x, y, stem):
    """말린 꼬리 + 엉덩이로 이어지는 꼬리 뿌리 (stem = 뿌리 사각형)"""
    A.dog_tail(cv, x, y)
    cv.rect(*stem)


def dog_stand(dx=-1, legs=DOG_STAND_LEGS, tail=(5, 5, (8, 9, 10, 11)), mood="normal", tongue=False, blink=False,
              ears="up", head=(20, 4)):
    """선 강아지 (걷기 시트와 같은 몸). dx = 몸 전체 좌우 이동 (오른쪽 여백 지키기)"""
    P = DOG
    cv = Cv(P)
    hx, top = head[0] + dx, head[1]
    bn, fn, bf, ff = legs
    for (x, s, up) in (bf, ff):
        cv.leg2((x + dx, 16), (x + dx, 19), (x + dx + s, 22 - up), P.FAR, tip=P.CREAM_FAR)
    tx, ty, st = tail
    dog_tail_at(cv, tx + dx, ty, (st[0] + dx, st[1], st[2] + dx, st[3]))
    A.dog_body_side(cv, 11, 9 + dx, 23 + dx)
    for (x, s, up) in (bn, fn):
        cv.leg2((x + dx, 16), (x + dx, 19), (x + dx + s, 22 - up), tip=P.CREAM)
    A.dog_head(cv, hx, top, ears)
    A.dog_face(cv.d, hx, top, mood=mood, blink=blink, tongue=tongue)
    A.dog_neck_collar(cv.d, hx, top)
    return cv, hx, top


def dog_wag(i):
    """살랑살랑 (반복 2장): 웃는 얼굴로 혀 내밀고, 말린 꼬리가 뒤↔앞으로 휙휙 (엉덩이도 같이 씰룩)"""
    if i == 0:
        legs = ((10, -1, 0), (20, 0, 0), (12, -1, 0), (18, 0, 0))
        cv, hx, top = dog_stand(legs=legs, tail=(3, 6, (6, 9, 10, 11)), mood="happy")
        line(cv.top, 9, 3, 10, 4)
        line(cv.top, 10, 6, 11, 6)
    else:
        legs = ((10, 1, 0), (20, 0, 0), (12, 1, 0), (18, 0, 0))
        cv, hx, top = dog_stand(legs=legs, tail=(7, 3, (8, 7, 10, 11)), mood="happy")
        line(cv.top, 4, 4, 5, 3)
        line(cv.top, 3, 7, 4, 7)
    return cv.image()


def dog_head_down(cv, hx, top, look_down=True, mood="normal", tongue=False):
    """고개 숙인 머리 (눈은 아래를 봄)"""
    P = DOG
    A.dog_head(cv, hx, top)
    A.dog_face(cv.d, hx, top, mood=mood, tongue=tongue)
    if look_down:
        cv.d = [p for p in cv.d if p[2] != P.EYE]
        for ex in (hx + 3, hx + 8):
            cv.d += [(ex - 1, top + 3, P.LINE), (ex, top + 3, P.LINE), (ex, top + 4, P.EYE)]


def dog_dig(i):
    """땅 파기 (반복 2장): 엉덩이는 번쩍, 가슴·고개는 땅으로 — 앞발 두 짝이 번갈아 파바박, 흙은 뒷다리 사이로 튄다"""
    P = DOG
    cv = Cv(P)
    hx, top = 19, 11
    cv.leg2((12, 13), (12, 18), (12, 22), P.FAR, tip=P.CREAM_FAR)            # 먼 뒷다리 (길게 — 엉덩이가 높다)
    if i == 0:
        cv.leg2((19, 16), (17, 19), (15, 20), P.FAR)                        # 먼 앞발: 배 밑으로 긁어 당김
        cv.rect(14, 19, 15, 20, P.CREAM_FAR)
    else:
        cv.leg2((19, 16), (22, 19), (24, 21), P.FAR, tip=P.CREAM_FAR)      # 먼 앞발: 앞으로 뻗어 땅 긁기
    A.dog_tail(cv, 4, 2)
    cv.rect(7, 5, 9, 8)
    for x in range(8, 23):                                                   # 앞으로 푹 숙인 몸통
        yt = round(8 + (x - 8) / 14 * 6)
        cv.rect(x, yt, x, yt + 5)
    cv.cut((8, 8), (8, 13))
    for x in range(11, 19):
        cv.put(x, round(8 + (x - 8) / 14 * 6) + 5, P.CREAM)                  # 배
    shine_edge(cv, 10, 19, P.FUR, P.FUR_HI)
    cv.leg2((9, 13), (9, 18), (9, 22), tip=P.CREAM)                          # 가까운 뒷다리
    sub = Cv(P)
    if i == 0:
        sub.leg2((21, 17), (24, 20), (26, 21), tip=P.CREAM)                # 가까운 앞발: 앞으로 쭉
    else:
        sub.leg2((21, 17), (18, 19), (16, 20))                              # 가까운 앞발: 배 밑으로 당김
        sub.rect(15, 19, 16, 20, P.CREAM)
    cv.over(sub)
    hd = Cv(P)
    dog_head_down(hd, hx, top, mood="happy", tongue=False)
    A.dog_neck_collar(hd.d, hx, top)
    cv.over(hd)
    # 흙: 앞발 밑 흙더미 + 뒷다리 사이로 튀는 흙덩이
    pts(cv.fx, [(23, 22), (24, 22), (25, 22), (26, 22), (27, 22), (28, 22), (29, 22), (25, 21), (26, 21), (28, 21)], DIRT)
    pts(cv.fx, [(27, 21), (24, 21), (30, 22)], DIRT_DK)
    pts(cv.fx, [(26, 20)], DIRT_HI)
    if i == 0:
        pts(cv.fx, [(5, 17), (6, 17), (5, 18), (3, 14), (4, 14), (7, 20), (2, 19), (3, 19), (6, 12)], DIRT)
        pts(cv.fx, [(6, 18), (4, 15), (3, 20)], DIRT_DK)
        pts(cv.fx, [(5, 16), (3, 13), (6, 11)], DIRT_HI)
    else:
        pts(cv.fx, [(4, 16), (5, 16), (4, 17), (2, 11), (3, 11), (6, 20), (7, 19), (3, 21), (6, 14)], DIRT)
        pts(cv.fx, [(5, 17), (3, 12), (7, 20)], DIRT_DK)
        pts(cv.fx, [(4, 15), (2, 10), (6, 13)], DIRT_HI)
    return cv.image()


def dog_sniff(i):
    """킁킁 (반복 2장): 네 발로 서서 고개를 땅까지 숙이고 코를 벌름 — 코 옆에 킁킁 자국, 콧김에 먼지 폴폴"""
    P = DOG
    cv = Cv(P)
    dy = (0, 1)[i]
    hx, top = 19, 12 + dy
    cv.leg2((11, 16), (11, 19), (11, 22), P.FAR, tip=P.CREAM_FAR)
    cv.leg2((17, 16), (18, 19), (18, 22), P.FAR, tip=P.CREAM_FAR)
    A.dog_tail(cv, 4, 4)
    cv.rect(7, 8, 9, 11)
    for x in range(8, 23):                                                   # 등이 앞으로 살짝 내려감
        yt = round(10 + (x - 8) / 14 * 3)
        cv.rect(x, yt, x, yt + 5)
    cv.cut((8, 10), (8, 15))
    for x in range(11, 19):
        cv.put(x, round(10 + (x - 8) / 14 * 3) + 5, P.CREAM)
    shine_edge(cv, 10, 19, P.FUR, P.FUR_HI)
    cv.leg2((9, 15), (9, 19), (9, 22), tip=P.CREAM)
    cv.leg2((20, 17), (21, 19), (21, 22), tip=P.CREAM)
    hd = Cv(P)
    dog_head_down(hd, hx, top)
    A.dog_neck_collar(hd.d, hx, top)
    nx, ny = hx + 5, top + 6
    hd.d = [p for p in hd.d if p[2] != P.NOSE]
    if i == 0:
        pts(hd.d, [(nx, ny), (nx + 1, ny)], P.NOSE)
        line(hd.top, nx - 4, ny + 1, nx - 5, ny + 2)
        line(hd.top, nx + 5, ny + 1, nx + 6, ny + 2)
    else:
        pts(hd.d, [(nx, ny - 1), (nx + 1, ny - 1), (nx, ny), (nx + 1, ny)], P.NOSE)     # 코 벌름 (위로 씰룩)
        pts(hd.d, [(nx - 1, ny), (nx + 2, ny)], P.MOUTH)
        line(hd.top, nx - 5, ny, nx - 6, ny)
        line(hd.top, nx - 5, ny + 2, nx - 6, ny + 3)
        line(hd.top, nx + 6, ny, nx + 7, ny)
        line(hd.top, nx + 6, ny + 2, nx + 7, ny + 3)
        pts(hd.fx, [(nx - 3, 22), (nx - 4, 22), (nx + 4, 22), (nx + 5, 22), (nx + 5, 21)], DUST_HI)
    cv.over(hd)
    return cv.image()


def dog_scratch(i):
    """벅벅 (반복 2장): 앉아서 뒷발로 귀 뒤를 긁기 — 고개를 발 쪽으로 기울이고 눈은 질끈, 혀는 쏙"""
    P = DOG
    cv = Cv(P)
    hx, top = 18, 5
    A.dog_tail(cv, 6, 14)
    cv.rect(10, 15, 19, 22)                 # 엉덩이
    cv.cut((10, 15), (11, 15), (10, 16))
    cv.rect(9, 21, 12, 22, P.CREAM_FAR)     # 먼 뒷발 (바닥)
    cv.rect(16, 12, 27, 22)                 # 몸통
    cv.rect(19, 14, 26, 17, P.CREAM)
    cv.rect(20, 18, 25, 18, P.CREAM)
    cv.rect(20, 18, 21, 22, P.FAR); cv.rect(20, 21, 21, 22, P.CREAM_FAR)
    cv.rect(22, 18, 23, 20, P.CREAM_FAR)
    cv.rect(24, 18, 25, 22); cv.rect(24, 21, 25, 22, P.CREAM)
    A.dog_head(cv, hx, top, ears="tilt")
    A.dog_face(cv.d, hx, top, mood="happy", tongue=True)
    cv.d = [p for p in cv.d if p[2] != P.EYE]
    for ex in (hx + 3, hx + 8):                                              # 시원해서 질끈 ( > < )
        cv.d += [(ex - 1, top + 2, P.EYE), (ex, top + 3, P.EYE), (ex - 1, top + 4, P.EYE)] if ex == hx + 3 else \
                [(ex + 1, top + 2, P.EYE), (ex, top + 3, P.EYE), (ex + 1, top + 4, P.EYE)]
    A.dog_front_collar(cv.d, hx, top)
    leg = Cv(P)                                                              # 가까운 뒷다리: 허벅지 → 무릎 → 귀 뒤로 쭉
    leg.rect(12, 16, 17, 21)
    leg.cut((12, 16), (17, 21), (12, 21))
    py = (6, 8)[i]
    leg.limb(16, 17, 17, 13, P.FUR, 2)
    leg.limb(17, 13, 16, py + 2, P.FUR, 2)
    leg.rect(15, py, 16, py + 2, P.CREAM)
    cv.over(leg)
    if i == 0:
        line(cv.top, 13, 6, 14, 5)
        line(cv.top, 13, 9, 14, 9)
    else:
        line(cv.top, 13, 8, 14, 7)
        line(cv.top, 13, 11, 14, 11)
        pts(cv.top, [(14, 4), (12, 7)], P.FUR)                              # 날리는 털
    return cv.image()


def dog_bow(i):
    """놀자! 절 (반복 2장): 앞다리를 바닥에 쭉 깔고 가슴을 낮추고, 엉덩이·꼬리는 번쩍 — 꼬리 살랑"""
    P = DOG
    cv = Cv(P)
    hx, top = 18, 10
    cv.leg2((13, 13), (13, 18), (13, 22), P.FAR, tip=P.CREAM_FAR)            # 먼 뒷다리
    cv.rect(20, 19, 30, 20, P.FAR); cv.rect(29, 19, 30, 20, P.CREAM_FAR)     # 먼 앞다리 (바닥에 쭉)
    if i == 0:
        A.dog_tail(cv, 3, 2); cv.rect(6, 6, 8, 9)
    else:
        A.dog_tail(cv, 6, 1); cv.rect(7, 5, 9, 9)
    cv.rect(7, 8, 14, 14)                                                    # 번쩍 든 엉덩이
    cv.cut((7, 8), (7, 14))
    for k in range(9):                                                       # 등: 엉덩이 → 낮춘 가슴으로 비스듬히
        cv.rect(13 + k, 9 + (k * 2) // 3, 14 + k, 14 + k // 2)
    cv.rect(19, 15, 24, 20)                                                  # 낮춘 가슴
    cv.rect(13, 14, 17, 15, P.CREAM)
    shine_edge(cv, 9, 20, P.FUR, P.FUR_HI)
    cv.leg2((10, 13), (10, 18), (10, 22), tip=P.CREAM)                       # 가까운 뒷다리
    arm = Cv(P)
    arm.rect(21, 21, 31, 22); arm.rect(30, 21, 31, 22, P.CREAM)              # 가까운 앞다리 (바닥에 쭉)
    cv.over(arm)
    A.dog_head(cv, hx, top)
    A.dog_face(cv.d, hx, top, mood="happy", tongue=True)
    A.dog_neck_collar(cv.d, hx, top)
    if i == 0:
        line(cv.top, 9, 2, 10, 3)
        line(cv.top, 9, 5, 10, 5)
    else:
        line(cv.top, 3, 3, 4, 2)
        line(cv.top, 3, 6, 4, 6)
    return cv.image()


def dog_howl(i):
    """아우우~ (순서대로 3장): 0 앉아서 하늘을 올려다봄 → 1 고개를 젖혀 주둥이를 위로 → 2 주둥이를 하늘로, 눈 감고 입 'o' 로 길게 (음파)"""
    P = DOG
    cv = Cv(P)
    A.dog_sit_body(cv, cv.d)
    if i == 0:
        hx, top = 18, 4
        A.dog_head(cv, hx, top)
        A.dog_face(cv.d, hx, top)
        cv.d = [p for p in cv.d if p[2] != P.EYE]
        for ex in (hx + 3, hx + 8):                                          # 위를 올려다보는 눈
            cv.d += [(ex, top + 2, P.EYE), (ex, top + 3, P.EYE), (ex - 1, top + 2, SHINE)]
        A.dog_front_collar(cv.d, hx, top)
        return cv.image()
    rows = DOG_HOWL_HEADS[i]
    dog_art_head(cv, 17, 14 - len(rows), rows)
    if i == 1:
        cv.d = [p for p in cv.d if p[2] != P.EYE] + [(25, 6, P.EYE), (25, 7, P.EYE), (24, 6, SHINE)]
    cv.d += [(x, 14, P.COLLAR) for x in range(19, 27)]
    cv.d += [(22, 15, SHINE), (23, 15, P.TAG), (22, 16, P.TAG_DK), (23, 16, P.TAG_DK)]
    if i == 2:
        line(cv.fx, 30, 4, 31, 3); line(cv.fx, 31, 6, 32, 6); line(cv.fx, 30, 8, 31, 9)    # 아우우~ 음파
    return cv.image()


def dog_rollover(i):
    """배 만져 줘 (반복 2장): 벌러덩 누워 크림색 배를 보이고 네 발을 하늘로 오므린 채 꼼지락 — 머리는 거꾸로 (귀가 바닥)"""
    P = DOG
    cv = Cv(P)
    w = (0, 1)[i]
    A.dog_tail(cv, 2, 16 + w)                                                # 바닥에서 살랑
    # 먼 다리 (몸 뒤)
    cv.leg2((11, 16), (11, 12), (12 + w, 9), P.FAR)
    cv.rect(13 + w, 8, 14 + w, 9, P.CREAM_FAR)
    cv.leg2((16, 16), (16, 12), (17, 10 + w), P.FAR)
    cv.rect(18, 10 + w, 19, 11 + w, P.CREAM_FAR)
    # 몸통 (등이 바닥, 배가 위)
    cv.ellipse(13.0, 18.8, 7.6, 4.0)
    cv.rect(8, 15, 18, 16, P.CREAM)
    cv.rect(10, 14, 16, 14, P.CREAM)
    leg = Cv(P)                                                              # 가까운 다리 (앞)
    leg.leg2((9, 16), (8, 12), (7 - w, 10))
    leg.rect(5 - w, 9, 6 - w, 10, P.CREAM)
    leg.leg2((18, 16), (19, 12), (20, 10 + 1 - w))
    leg.rect(21, 11 - w, 22, 12 - w, P.CREAM)
    cv.over(leg)
    h = Cv(P)
    body = {"F": P.FUR, "C": P.CREAM, "I": P.EAR_IN}
    det = {"N": (P.CREAM, P.NOSE), "M": (P.CREAM, P.MOUTH), "E": (P.FUR, P.EYE)}
    x0, y0 = 20, 13
    for j, row in enumerate(DOG_ROLL_HEAD):
        for k, ch in enumerate(row):
            if ch in body:
                h.px[(x0 + k, y0 + j)] = body[ch]
            elif ch in det:
                h.px[(x0 + k, y0 + j)] = det[ch][0]
                h.d.append((x0 + k, y0 + j, det[ch][1]))
    h.d += [(x0 + 6, y0 + 4, P.TONGUE_DK), (x0 + 7, y0 + 4, P.TONGUE), (x0 + 7, y0 + 5, P.TONGUE)]   # 입에서 늘어진 혀
    cv.over(h)
    if i == 1:
        line(cv.top, 3, 7, 4, 8)
        line(cv.top, 23, 8, 24, 7)
    else:
        line(cv.top, 9, 6, 10, 5)
        line(cv.top, 16, 6, 16, 7)
    return cv.image()


DOG_HOWL_HEADS = {
    # 고개를 젖혀 주둥이를 위로 (옆얼굴) — F 털 · C 크림 · I 귀 안 · N 코 · M 입 · T 혀 · t 밝은 혀 · E 눈 · W 눈빛
    1: [
        "..............",
        "..F........NN.",
        ".FIF.....hFNNC",
        ".FIIF..hhFFCCC",
        "..FIFFFFFFCCCC",
        "..FFFFFFEFCCMM",
        "..FFFFFFEFFCCC",
        "..FFFFFFFFCCC.",
        "..FFFFFFFCCC..",
        "..FFFFFFCCCC..",
        "...FFFFCCCC...",
        "....CCCCC.....",
    ],
    2: [
        ".........NN...",
        "........FNNF..",
        "..F....hFCCF..",
        ".FIF..hhFCCC..",
        ".FIIF.FFFCMMC.",
        "..FIFFFFFMTTM.",
        "..FFFFFEFFMMC.",
        "..FFFFFFEFCC..",
        "..FFFFFFFFCC..",
        "..FFFFFFFCCC..",
        "..FFFFFFCCCC..",
        "...FFFFCCCC...",
        "....CCCCC.....",
    ],
}


def dog_art_head(cv, x0, y0, rows):
    """문자 그림 머리: 몸 칸(F·C·I) + 얼굴 세부(N·M·T·t·E·W)"""
    P = DOG
    body = {"F": P.FUR, "C": P.CREAM, "I": P.EAR_IN, "h": P.FUR_HI, "s": P.CREAM_SH}
    det = {"N": (P.CREAM, P.NOSE), "M": (P.CREAM, P.MOUTH), "T": (P.CREAM, P.TONGUE_DK), "t": (P.CREAM, P.TONGUE),
           "E": (P.FUR, P.EYE), "W": (P.FUR, SHINE)}
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in body:
                cv.px[(x0 + i, y0 + j)] = body[ch]
            elif ch in det:
                base, c = det[ch]
                cv.px[(x0 + i, y0 + j)] = base
                cv.d.append((x0 + i, y0 + j, c))


DOG_ROLL_HEAD = [
    # 벌러덩 누운 옆얼굴 (위아래 뒤집힘): 턱이 위, 정수리가 바닥, 귀는 바닥으로 축, 웃는 입 + 감은 눈
    "...CCCCC....",
    "..CCCCCCCC..",
    ".FCCMCCCCMC.",
    "FFFCCMMMMCC.",
    "FFFFFFFFFNNC",
    "FFFEEFFFFNN.",
    "FFFFFFFFFF..",
    ".FFIIFFFF...",
    ".FIIF.......",
    "..FF........",
]


def lion_head2(cv, fx, fy, R=6.8, sweep=0.0, lift=0.0, phase=0.0, amp=0.9, bumps=9, jaw=0, ears="up"):
    """사자 머리 (동물_오마주.lion_head 와 같은 모양) + 갈기 크기·출렁임 조절, jaw = 벌린 아래턱 칸 수.
    sweep > 0 = 갈기가 뒤(왼쪽)로 쏠림, < 0 = 앞(오른쪽)으로 쏠림"""
    P = LION
    F, L = P.FUR, P.LIGHT
    A.lion_mane(cv, fx + 4.5, fy + 4.4, sweep, lift, R=R, bumps=bumps, phase=phase, amp=amp)   # 기본 시트와 같은 3겹 갈기
    face = set()
    rows = [(fx + 1, fy, fx + 8), (fx, fy + 1, fx + 9), (fx, fy + 2, fx + 9), (fx, fy + 3, fx + 9), (fx, fy + 4, fx + 9),
            (fx, fy + 5, fx + 9), (fx, fy + 6, fx + 9), (fx + 1, fy + 7, fx + 8), (fx + 2, fy + 8, fx + 7)]
    for k in range(jaw):                                                     # 벌린 입: 턱이 내려감
        rows[-1] = (fx + 1, fy + 8 + k, fx + 8) if k < jaw - 1 else rows[-1]
        rows.append((fx + 2, fy + 9 + k, fx + 7))
    if jaw:
        rows.append((fx + 3, fy + 9 + jaw, fx + 6))
    for x0, y, x1 in rows:
        for x in range(x0, x1 + 1):
            face.add((x, y))
    for (x, y) in face:
        for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + ddx, y + ddy)
            if n not in face and n in cv.px:
                cv.px[n] = P.MANE_DK
    for p in face:
        cv.px[p] = F
    for ox in (fx, fx + 8):                                                  # 동그란 귀
        if ears == "back":                                                   # 납작 젖힌 귀
            cv.rect(ox + (-1 if ox == fx else 1), fy - 1, ox + (0 if ox == fx else 2), fy - 1, F)
        else:
            cv.rect(ox, fy - 2, ox + 1, fy - 1, F)
            cv.put(ox + (1 if ox == fx else 0), fy - 1, P.EAR_IN)
    cv.rect(fx + 3, fy + 5, fx + 6, fy + 5, L)                              # 밝은 주둥이
    cv.rect(fx + 2, fy + 6, fx + 7, fy + 7 + jaw, L)
    cv.rect(fx + 3, fy + 8 + jaw, fx + 6, fy + 8 + jaw, L)
    if jaw:
        cv.rect(fx + 3, fy + 9 + jaw, fx + 6, fy + 9 + jaw, L)
    A.lion_whiskers(cv.d, fx, fy)                                            # 수염 (기본 시트와 같게)


def lion_eyes(d, fx, fy, kind):
    """kind: fierce(힘준 눈썹) · squeeze(> <) · sleep(일자) · heavy(졸린 반눈) · normal"""
    P = LION
    e1, e2, ey = fx + 2, fx + 7, fy + 3
    if kind == "squeeze":
        d += [(e1 - 1, ey - 1, P.EYE), (e1, ey, P.EYE), (e1 - 1, ey + 1, P.EYE),
              (e2 + 1, ey - 1, P.EYE), (e2, ey, P.EYE), (e2 + 1, ey + 1, P.EYE)]
    elif kind == "sleep":
        d += [(e1 - 1, ey + 1, P.EYE), (e1, ey + 1, P.EYE), (e1 + 1, ey + 1, P.EYE),
              (e2 - 1, ey + 1, P.EYE), (e2, ey + 1, P.EYE), (e2 + 1, ey + 1, P.EYE)]
    elif kind == "heavy":
        d += [(e1 - 1, ey, P.LINE), (e1, ey, P.LINE), (e1 + 1, ey, P.LINE), (e1, ey + 1, P.EYE),
              (e2 - 1, ey, P.LINE), (e2, ey, P.LINE), (e2 + 1, ey, P.LINE), (e2, ey + 1, P.EYE)]
    else:
        d += [(e1, ey, P.EYE), (e1, ey + 1, P.EYE), (e2, ey, P.EYE), (e2, ey + 1, P.EYE)]
        if kind == "fierce":
            d += [(e1 - 1, ey - 2, P.LINE), (e1, ey - 1, P.LINE), (e2 + 1, ey - 2, P.LINE), (e2, ey - 1, P.LINE)]


def lion_mouth(d, fx, fy, kind, size):
    """벌린 입. kind = roar(옆으로 넓게, 송곳니) · yawn(세로로 길게, 혀 말림). size 0~3"""
    P = LION
    m, inn, T = P.MOUTH, P.MOUTH_IN, P.TONGUE
    d += [(fx + 4, fy + 4, m), (fx + 5, fy + 4, m)]                          # 코 (입이 커지면 한 칸 위)
    if size == 0:                                                            # 작게 'o'
        d += [(fx + 4, fy + 6, m), (fx + 5, fy + 6, m), (fx + 3, fy + 7, m), (fx + 4, fy + 7, inn), (fx + 5, fy + 7, inn),
              (fx + 6, fy + 7, m), (fx + 4, fy + 8, m), (fx + 5, fy + 8, m)]
        return
    top = fy + 6 if size == 1 else fy + 5
    bot = fy + 8 + size if kind == "yawn" else fy + 7 + size
    x0, x1 = (fx + 3, fx + 6) if size == 1 else (fx + 2, fx + 7)
    for y in range(top, bot + 1):
        for x in range(x0, x1 + 1):
            edge = y in (top, bot) or x in (x0, x1)
            corner = y in (top, bot) and x in (x0, x1)
            if corner:
                continue
            d.append((x, y, m if edge else inn))
    if size >= 2:
        d += [(x0 + 1, top + 1, FANG), (x1 - 1, top + 1, FANG)]              # 윗 송곳니
        d += [(x0 + 1, bot - 1, FANG), (x1 - 1, bot - 1, FANG)] if kind == "roar" else []
    tx0, tx1 = x0 + (2 if kind == "roar" and size >= 2 else 1), x1 - (2 if kind == "roar" and size >= 2 else 1)
    for x in range(tx0, tx1 + 1):                                           # 혀
        d.append((x, bot - 1, T))
    if kind == "yawn" and size >= 2:
        d += [(x0 + 1, bot - 2, T), (x1 - 1, bot - 2, T)]                    # 말린 혀 끝


def lion_stand(cv, dx=0, legs=None, by=11, tail=None):
    """선 사자 몸 (걷기 시트와 같은 크기) — 다리·꼬리만 바꿔 그림. 먼 다리 → 꼬리 → 몸 → 가까운 다리"""
    legs = legs or (((10, 0), (10, 19), (10, 22)), ((20, 0), (20, 19), (20, 22)),
                    ((12, 0), (12, 19), (12, 22)), ((18, 0), (18, 19), (18, 22)))
    bn, fn, bf, ff = legs
    for t, k, f in (bf, ff):
        A.lion_leg(cv, (t[0] + dx, by + 5), (k[0] + dx, k[1]), (f[0] + dx, f[1]), far=True)
    if tail:
        A.lion_tail(cv, *tail)
    A.lion_body_side(cv, by, 8 + dx, 24 + dx)
    A.lion_shoulder_mane(cv, 20 + dx, by)                                    # 어깨·가슴 갈기 (기본 시트와 같게)
    for t, k, f in (bn, fn):
        A.lion_leg(cv, (t[0] + dx, by + 5), (k[0] + dx, k[1]), (f[0] + dx, f[1]))


def lion_roar(i):
    """어흥 (순서대로 3장): 앞발로 버티고 입을 점점 크게 → 갈기가 부풀어 오름 → 마지막 장은 송곳니를 다 드러낸 포효 (음파)"""
    P = LION
    cv = Cv(P)
    dx = -3
    legs = (((10, 0), (9, 19), (8, 22)), ((20, 0), (21, 19), (22, 22)),
            ((12, 0), (11, 19), (10, 22)), ((18, 0), (19, 19), (20, 22)))
    tail = [([(5, 12), (3, 11), (3, 8), (4, 5)], (4, 4)),
            ([(5, 12), (3, 11), (3, 8), (4, 5)], (4, 4)),
            ([(5, 12), (3, 10), (4, 7), (6, 5)], (6, 4))][i]
    lion_stand(cv, dx, legs, tail=tail)
    fx, fy = 17, 5
    R = (6.8, 7.2, 7.6)[i]
    lion_head2(cv, fx, fy, R=R, sweep=(0, 0.6, 1.0)[i], amp=(0.9, 1.1, 1.4)[i], phase=i * 0.4, jaw=(0, 1, 2)[i])
    lion_eyes(cv.d, fx, fy, "squeeze" if i == 2 else "fierce")
    lion_mouth(cv.d, fx, fy, "roar", (0, 2, 3)[i])
    if i == 2:                                                               # 어흥! 음파
        line(cv.fx, 30, 8, 31, 7); line(cv.fx, 31, 12, 32, 12); line(cv.fx, 30, 16, 31, 17)
        line(cv.fx, 31, 4, 32, 3); line(cv.fx, 31, 20, 32, 21)
    return cv.image()


def lion_yawn(i):
    """하암~ (순서대로 3장): 앉아서 졸린 눈 → 고개를 살짝 젖히며 입이 벌어짐 → 송곳니가 다 보이게 쩍, 눈은 질끈 + 눈물 찔끔"""
    P = LION
    cv = Cv(P)
    A.lion_sit_body(cv, cv.d)
    fx, fy = (19, 18, 18)[i], 4
    lion_head2(cv, fx, fy, jaw=(0, 1, 3)[i], ears="up" if i == 0 else "back", phase=0.2 * i)
    lion_eyes(cv.d, fx, fy, ("heavy", "squeeze", "squeeze")[i])
    lion_mouth(cv.d, fx, fy, "yawn", (0, 2, 3)[i])
    if i == 2:
        cv.d += [(fx + 9, fy + 4, TEAR), (fx + 9, fy + 5, TEAR)]
    return cv.image()


def lion_nap(i):
    """낮잠 (3장): 0 = 엎드리는 중 (뒷다리 접고 앞발을 내밀며 고개가 떨어짐) · 1·2 = 앞발 위에 턱을 괴고 납작 엎드려 쿨쿨 (눈은 일자, 등이 1칸 들썩)"""
    P = LION
    cv = Cv(P)
    if i == 0:
        A.lion_tail(cv, [(9, 19), (6, 21), (4, 21), (3, 19)], (3, 18))
        cv.rect(8, 15, 17, 22)                                               # 접은 뒷다리·엉덩이
        cv.cut((8, 15), (9, 15), (8, 16))
        cv.rect(8, 21, 12, 22, P.LIGHT)
        cv.rect(14, 13, 25, 20)                                              # 반쯤 내려간 몸
        cv.rect(20, 18, 21, 22, P.FAR); cv.rect(22, 21, 23, 22, P.FAR)      # 먼 앞발 (앞으로 내미는 중)
        A.lion_leg(cv, (24, 17), (25, 20), (26, 22))
        A.lion_shoulder_mane(cv, 19, 13, depth=5, drop=4)
        fx, fy = 19, 7
        lion_head2(cv, fx, fy, phase=0.3)
        A.lion_face(cv.d, fx, fy)
        cv.d = [p for p in cv.d if p[2] != P.EYE]                           # 졸린 반눈으로 바꿈
        lion_eyes(cv.d, fx, fy, "heavy")
        cv.d += [(16, 17, P.FAR), (16, 18, P.FAR), (15, 19, P.FAR)]
        return cv.image()
    up = i - 1
    A.lion_tail(cv, [(8, 20), (5, 21), (3, 21), (3, 19)], (3, 18))
    for x in range(6, 22):                                                   # 납작 엎드린 몸 (등이 숨 따라 1칸)
        yt = 15 - up if 8 <= x <= 17 else 16 - up if x in (7, 18, 19) else 17
        cv.rect(x, yt, x, 21)
    cv.rect(5, 19, 6, 21)
    cv.rect(11, 21, 15, 22, P.LIGHT)                                         # 접은 뒷발 (몸 밑으로 빼꼼)
    cv.rect(8, 21, 10, 22)
    cv.rect(21, 20, 30, 21, P.FAR); cv.rect(29, 20, 30, 21, P.LIGHT)        # 먼 앞발 (앞으로 쭉)
    paw = Cv(P)
    paw.rect(20, 21, 31, 22); paw.rect(29, 21, 31, 22, P.LIGHT)              # 가까운 앞발
    A.lion_shoulder_mane(cv, 18, 15 - up, depth=6, drop=4)
    cv.over(paw)
    fx, fy = 18, 10
    hd = Cv(P)
    lion_head2(hd, fx, fy, R=6.6, phase=0.2)
    lion_eyes(hd.d, fx, fy, "sleep")
    m = P.MOUTH
    hd.d += [(fx + 4, fy + 5, m), (fx + 5, fy + 5, m), (fx + 3, fy + 7, m), (fx + 4, fy + 6, m), (fx + 5, fy + 6, m), (fx + 6, fy + 7, m)]
    cv.over(hd)
    cv.d += [(12, 18 - up, P.FAR), (13, 19 - up, P.FAR), (14, 19 - up, P.FAR)]   # 접은 허벅지 결
    return cv.image()


def lion_stalk(i):
    """슬금슬금 (반복 2장): 배가 땅에 닿을 듯 납작 엎드려, 어깨뼈가 솟고 고개는 등 높이로 — 앞발을 한 발씩 살며시 내딛음"""
    P = LION
    cv = Cv(P)
    by = 13
    lift_near = i == 0
    # 먼 다리 (짧게 접힌 다리 — 몸이 낮다)
    cv.rect(13, 18, 14, 22, P.FAR); cv.put(15, 22, P.FAR)                   # 먼 뒷다리
    if lift_near:
        cv.rect(20, 18, 21, 22, P.FAR); cv.put(22, 22, P.FAR)               # 먼 앞다리 (디딤)
    else:
        cv.limb(20, 18, 23, 20, P.FAR, 2); cv.rect(23, 20, 25, 21, P.FAR)  # 먼 앞발 살며시 내딛기
    sw = (0, 1)[i]
    A.lion_tail(cv, [(7, by + 2), (4, by + 2), (3, by + 3), (3, by + 1 - sw)], (3, by - sw))   # 낮게 깔린 꼬리, 끝만 까딱
    for x in range(7, 25):                                                   # 납작한 몸 (등 y=13, 배 y=18)
        cv.rect(x, by, x, by + 5)
    cv.cut((7, by), (7, by + 5), (24, by + 5))
    cv.rect(10, by + 5, 19, by + 5, P.LIGHT)
    cv.rect(18, by - 1, 22, by - 1)                                          # 솟은 어깨뼈
    cv.rect(19, by - 2, 21, by - 2)
    cv.rect(8, by - 1, 12, by - 1)                                           # 엉덩이 둥글게
    A.lion_shoulder_mane(cv, 19, by, phase=i, depth=6, drop=4)
    cv.rect(8, 16, 12, 18)                                                   # 접은 허벅지
    cv.rect(9, 18, 10, 22); cv.put(11, 22)                                   # 가까운 뒷다리
    if lift_near:
        cv.limb(22, 18, 25, 20, P.FUR, 2); cv.rect(25, 20, 27, 21)          # 가까운 앞발 살며시 내딛기
    else:
        cv.rect(22, 18, 23, 22); cv.put(24, 22)                              # 가까운 앞다리 (디딤)
    fx, fy = 19, 8
    hd = Cv(P)
    lion_head2(hd, fx, fy, R=6.2, sweep=1.2, phase=0.6, amp=0.8)
    A.lion_face(hd.d, fx, fy)
    A.sneak_eyes(hd.d, P, (fx + 2, fx + 7), fy + 3, 0)
    cv.over(hd)
    cv.d += [(11, 16, P.FAR), (12, 17, P.FAR)]                               # 허벅지 결
    return cv.image()


def lion_mane(i):
    """부르르 (반복 2장): 갈기를 좌우로 털어 부풀림 — 눈은 질끈, 털 부스러기가 날린다"""
    P = LION
    cv = Cv(P)
    lion_stand(cv, -1, tail=([(7, 12), (4, 12), (3, 10), (3 + i, 6)], (3 + i, 5)))
    s = (1, -1)[i]
    fx, fy = (17, 17)[i], 5
    lion_head2(cv, fx, fy, R=7.2, sweep=1.4 * s, amp=1.3, bumps=11, phase=(0.0, 1.4)[i])
    lion_eyes(cv.d, fx, fy, "squeeze")
    m = P.MOUTH
    cv.d += [(fx + 4, fy + 5, m), (fx + 5, fy + 5, m), (fx + 3, fy + 7, m), (fx + 4, fy + 6, m), (fx + 5, fy + 6, m), (fx + 6, fy + 7, m)]
    if i == 0:                                                               # 터는 방향 반대쪽에 움직임 자국 + 날리는 털
        line(cv.fx, 8, 3, 9, 2); line(cv.fx, 7, 6, 8, 6)
        pts(cv.fx, [(10, 1), (30, 2), (31, 14)], P.MANE_HI)
    else:
        line(cv.fx, 31, 3, 32, 2); line(cv.fx, 31, 7, 32, 7)
        pts(cv.fx, [(10, 2), (12, 0), (31, 16)], P.MANE_HI)
    return cv.image()


def lion_claws(i):
    """앞발 휙! (반복 2장): 0 = 가까운 앞발을 번쩍 들어 발톱을 쫙 · 1 = 앞으로 할퀴어 내림 (발톱 자국 세 줄)"""
    P = LION
    cv = Cv(P)
    dx = -3
    legs = (((10, 0), (9, 19), (8, 22)), ((20, 0), (20, 19), (20, 22)),
            ((12, 0), (12, 19), (12, 22)), ((18, 0), (19, 19), (19, 22)))
    bf, ff = legs[2], legs[3]
    for t, k, f in (bf, ff):
        A.lion_leg(cv, (t[0] + dx, 16), (k[0] + dx, k[1]), (f[0] + dx, f[1]), far=True)
    A.lion_tail(cv, [(5, 12), (3, 11), (3, 8), (4 + i, 5)], (4 + i, 4))
    A.lion_body_side(cv, 11, 5, 21)
    A.lion_shoulder_mane(cv, 17, 11)
    t, k, f = legs[0]
    A.lion_leg(cv, (t[0] + dx, 16), (k[0] + dx, k[1]), (f[0] + dx, f[1]))
    fx, fy = 16, 4
    lion_head2(cv, fx, fy, R=7.0, sweep=1, phase=0.3, jaw=1)
    lion_eyes(cv.d, fx, fy, "fierce")
    lion_mouth(cv.d, fx, fy, "roar", 2)
    arm = Cv(P)
    if i == 0:                                                               # 번쩍 든 앞발 (갈기 앞, 머리 높이)
        arm.limb(19, 15, 24, 11, P.FUR, 3)
        arm.limb(24, 11, 26, 7, P.FUR, 3)
        arm.rect(25, 4, 28, 7, P.FUR)
        arm.rect(26, 4, 28, 5, P.LIGHT)
        arm.d += [(29, 3, CLAW), (29, 5, CLAW), (29, 7, CLAW), (28, 3, CLAW)]
    else:                                                                    # 앞으로 할퀴어 내린 앞발
        arm.limb(19, 15, 25, 17, P.FUR, 3)
        arm.rect(25, 16, 28, 19, P.FUR)
        arm.rect(27, 17, 28, 19, P.LIGHT)
        arm.d += [(29, 17, CLAW), (29, 19, CLAW), (28, 20, CLAW), (29, 16, CLAW)]
        for k in range(3):                                                   # 발톱 자국 세 줄 (위에서 아래로 할퀸 자리)
            line(arm.fx, 30, 6 + k * 3, 32, 8 + k * 3, ACT_LINE)
    for (x, y) in list(arm.px):
        if x >= 29:
            arm.px.pop((x, y))
    cv.over(arm)
    cv.px.update({(x, y): CLAW for (x, y, c) in arm.d if c == CLAW and (x, y) not in cv.px})
    return cv.image()


def horse_neck2(cv, base, poll, r=2.6, stream=0, phase=0):
    """기울어진 목 (기갑 base → 머리 뒤 poll). 위쪽 가장자리에 진한 갈기, stream = 뒤로 휘날리는 갈기 길이"""
    P = HORSE
    (x0, y0), (x1, y1) = base, poll
    L = math.hypot(x1 - x0, y1 - y0) or 1
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = uy, -ux                                                         # 목의 '위쪽' 법선 (갈기 쪽)
    if ny > 0:
        nx, ny = -nx, -ny
    R = r + stream + 1
    for y in range(int(min(y0, y1) - R) - 1, int(max(y0, y1) + R) + 2):
        for x in range(int(min(x0, x1) - R) - 1, int(max(x0, x1) + R) + 2):
            t = (x - x0) * ux + (y - y0) * uy
            if t < -0.5 or t > L + 0.5:
                continue
            off = (x - x0) * nx + (y - y0) * ny
            along = abs((x - x0) * uy - (y - y0) * ux)
            if along <= r:
                if off > r - 1.7:
                    k = (round(t) + phase) % 3
                    cv.put(x, y, P.MANE_HI if k == 0 else (P.MANE_DK if k == 1 and off <= r - 0.8 else P.MANE))
                else:
                    cv.put(x, y, P.FUR_HI if off > r - 2.7 else P.FUR)        # 목덜미 윤기
            elif stream and off > 0 and along <= r + stream and (round(t) + phase) % 3 != 0:
                cv.put(x, y, P.MANE_HI if along > r + stream - 1 else P.MANE)


def horse_legs4(cv, legs, sock=True):
    """legs = (뒤-먼, 앞-먼, 뒤-가까운, 앞-가까운) 각각 (위, 무릎, 발굽). 먼 다리는 먼저 그리고 가까운 다리는 겹쳐 그림"""
    P = HORSE
    for k, (t, kn, f) in enumerate(legs):
        if k < 2:
            cv.leg2(t, kn, f, P.FAR, tip=P.HOOF)


def horse_near_legs(cv, legs, sock=True):
    P = HORSE
    for k, (t, kn, f) in enumerate(legs[2:]):
        cv.leg2(t, kn, f, tip=P.HOOF)
        if k == 0 and sock:                                                  # 뒷다리 흰 양말 (발굽 바로 위)
            fx_, fy_ = f
            kx_, ky_ = kn
            if abs(fx_ - kx_) > abs(fy_ - ky_):
                sx = 1 if fx_ < kx_ else -1
                cv.rect(fx_ + sx, fy_, fx_ + sx, fy_ + 1, P.SOCK)
            else:
                cv.rect(fx_, fy_ - 1, fx_ + 1, fy_ - 1, P.SOCK)


HORSE_STAND_LEGS = (((11, 14), (10, 18), (11, 22)), ((18, 14), (18, 18), (18, 22)),
                    ((9, 14), (8, 18), (9, 22)), ((20, 14), (20, 18), (20, 22)))


HORSE_TAIL = [(7, 10), (4, 11), (2, 14), (2, 18), (3, 21)]


def horse_ears(cv, hx, top, kind):
    """귀 모양 바꾸기: up(쫑긋) · side(옆으로 축 — 졸 때·풀 뜯을 때) · back(뒤로 젖힘 — 짜증) · flick(가까운 귀만 뒤로 휙)"""
    for ox, s in ((hx + 1, 1), (hx + 7, -1)):
        cv.cut((ox, top - 2), (ox, top - 1), (ox + s, top - 1))
    for ox, s in ((hx + 1, 1), (hx + 7, -1)):
        k = kind
        if kind == "flick":
            k = "back" if s == 1 else "up"
        if k == "up":
            cv.put(ox, top - 2); cv.rect(ox, top - 1, ox + s, top - 1)
        elif k == "side":
            cv.rect(ox - s * 2, top, ox - s, top); cv.put(ox - s * 2, top + 1)
        elif k == "back":
            cv.rect(ox - s * 2, top - 1, ox, top - 1); cv.put(ox - s * 2, top - 2)


def horse_rest(mood="normal", ears="up", legs=HORSE_STAND_LEGS, tail=HORSE_TAIL, tail_w=(3, 3, 2, 2), top=3, tail_front=False, hx=23):
    """선 말 (기본 시트와 같은 몸) — 다리·꼬리·귀만 바꿔 그림 (귀를 옆·뒤로 눕히면 hx=22 로 오른쪽 여백 지키기)"""
    P = HORSE
    cv = Cv(P)
    by = 9
    horse_legs4(cv, legs)
    if not tail_front:
        A.horse_tail(cv, tail, tail_w)
    A.horse_neck(cv, hx, top, by)
    A.horse_body(cv, by)
    horse_near_legs(cv, legs)
    if tail_front:                                                           # 꼬리를 몸 쪽으로 휘두름 (뒷다리 앞을 지나감)
        t = Cv(P)
        A.horse_tail(t, tail, tail_w)
        cv.over(t)
    A.horse_head(cv, hx, top)
    horse_ears(cv, hx, top, ears)
    return cv, hx, top


def horse_graze(i):
    """풀 뜯기 (반복 2장): 몸통은 수평 그대로, 목만 땅까지 내려 주둥이를 풀에 — 0 풀을 뜯고 1 고개를 살짝 들어 오물오물 (입에 풀)"""
    P = HORSE
    cv = Cv(P)
    by = 9
    hx, top = 22, 13 - i
    horse_legs4(cv, HORSE_STAND_LEGS)
    A.horse_tail(cv, HORSE_TAIL, (3, 3, 2, 2))
    A.horse_body(cv, by)
    horse_neck2(cv, (16, 11), (hx + 1, top + 3), r=2.7)
    cv.rect(hx - 1, top - 1, hx + 1, top + 1, P.MANE)                        # 귀 뒤 갈기
    horse_near_legs(cv, HORSE_STAND_LEGS)
    hd = Cv(P)
    A.horse_head(hd, hx, top)
    horse_ears(hd, hx, top, "side")
    A.horse_face(hd.d, hx, top, blink=True)
    m = P.MOUTH
    hd.d = [p for p in hd.d if p[1] != top + 8]
    if i == 0:
        hd.d += [(hx + 3, top + 8, m), (hx + 4, top + 8, m), (hx + 5, top + 8, m)]
    else:                                                                    # 오물오물 + 입가에 풀
        hd.d += [(hx + 3, top + 8, m), (hx + 4, top + 8, P.MOUTH_IN), (hx + 5, top + 8, m)]
        hd.top += [(hx + 6, top + 8, GRASS), (hx + 7, top + 9, GRASS_DK), (hx + 2, top + 9, GRASS)]
    cv.over(hd)
    for gx, gh in ((21, 2), (23, 3), (25, 2), (28, 3), (30, 2)):            # 풀 (외곽선 없음): 주둥이 밑
        for k in range(gh):
            cv.fx.append((gx, 22 - k, GRASS if k < gh - 1 else GRASS_HI))
        cv.fx.append((gx + 1, 22, GRASS_DK))
    return cv.image()


def horse_swish(i):
    """꼬리 휙휙 (반복 2장): 엉덩이에 앉은 파리를 꼬리로 휙 — 0 꼬리를 뒤로 크게 · 1 몸 쪽으로 휘감음, 가까운 귀가 뒤로 쫑긋"""
    if i == 0:
        cv, hx, top = horse_rest(ears="up", tail=[(7, 10), (4, 9), (2, 11), (2, 15), (3, 18)], tail_w=(3, 3, 2, 2))
        line(cv.fx, 4, 19, 5, 21); line(cv.fx, 6, 18, 7, 20)
        pts(cv.top, [(9, 6)], FLY); pts(cv.top, [(9, 5), (10, 5)], FLY_WING)
    else:
        cv, hx, top = horse_rest(ears="flick", tail=[(7, 10), (6, 13), (7, 16), (9, 19), (11, 20)], tail_w=(3, 3, 2, 2), tail_front=True)
        line(cv.fx, 3, 12, 4, 14); line(cv.fx, 3, 16, 4, 18)
        pts(cv.top, [(5, 5)], FLY); pts(cv.top, [(4, 4), (5, 4)], FLY_WING)
    A.horse_face(cv.d, hx, top)
    return cv.image()


def horse_stomp(i):
    """쿵쿵 (반복 2장): 0 가까운 앞발을 무릎 꺾어 번쩍 · 1 쾅 내려찍기 (흙먼지 + 충격선) — 귀는 뒤로 (안달)"""
    P = HORSE
    if i == 0:
        legs = (HORSE_STAND_LEGS[0], HORSE_STAND_LEGS[1], HORSE_STAND_LEGS[2], ((20, 14), (23, 16), (22, 19)))
        cv, hx, top = horse_rest(ears="back", legs=legs, top=2, hx=22)
        line(cv.fx, 25, 18, 26, 17); line(cv.fx, 25, 20, 26, 20)
    else:
        cv, hx, top = horse_rest(ears="back", top=3, hx=22)
        puff(cv.fx, 17.5, 21.0, 2.0)
        puff(cv.fx, 24.0, 21.0, 2.2)
        pts(cv.fx, [(15, 18), (26, 17), (27, 19)], DUST_DK)
        line(cv.fx, 18, 17, 17, 16); line(cv.fx, 23, 17, 24, 16); line(cv.fx, 21, 17, 21, 16)
    A.horse_face(cv.d, hx, top)
    cv.d += [(hx + 1, top + 1, P.LINE), (hx + 2, top + 1, P.LINE), (hx + 7, top + 1, P.LINE), (hx + 6, top + 1, P.LINE)]   # 찌푸린 눈썹
    return cv.image()


def horse_doze(i):
    """선 채로 졸기 (3장): 0 = 고개가 스르르 내려가며 눈이 감김 · 1·2 = 목을 수평으로 떨군 채 눈은 일자,
    아랫입술이 축 처지고 뒷발 하나를 발끝으로 세워 쉬는 진짜 말 자세 — 등이 1칸 들썩 (숨)"""
    P = HORSE
    cv = Cv(P)
    by = 9
    hx = 22
    top = (6, 8, 8)[i]
    rest = i > 0
    horse_legs4(cv, HORSE_STAND_LEGS)
    A.horse_tail(cv, [(7, 10), (5, 12), (4, 15), (4, 18), (4, 21)], (3, 3, 2, 2))
    A.horse_body(cv, by)
    if i == 2:
        cv.rect(10, by - 1, 18, by - 1)                                      # 숨 들이쉼: 등이 1칸
    horse_neck2(cv, (16, 11), (hx + 1, top + 3), r=2.7)
    cv.rect(hx - 1, top - 1, hx + 1, top + 1, P.MANE)
    if rest:                                                                 # 가까운 뒷다리: 발끝만 땅에 (쉬는 다리)
        cv.leg2((9, 14), (9, 18), (11, 20))
        cv.rect(10, 20, 11, 20, P.SOCK)
        cv.put(11, 21, P.HOOF); cv.put(12, 21, P.HOOF); cv.put(12, 22, P.HOOF)
        cv.cut((7, 10))                                                      # 그쪽 엉덩이가 살짝 처짐
    else:
        cv.leg2((9, 14), (8, 18), (9, 22), tip=P.HOOF)
        cv.rect(9, 21, 10, 21, P.SOCK)
    cv.leg2((20, 14), (20, 18), (20, 22), tip=P.HOOF)
    hd = Cv(P)
    A.horse_head(hd, hx, top)
    horse_ears(hd, hx, top, "side" if rest else "up")
    A.horse_face(hd.d, hx, top, blink=True)
    m = P.MOUTH
    hd.d = [p for p in hd.d if p[1] != top + 8]
    if rest:                                                                 # 감은 눈 (일자) + 축 처진 아랫입술
        hd.d = [p for p in hd.d if p[2] != P.EYE]
        hd.d += [(hx + 1, top + 3, P.EYE), (hx + 2, top + 3, P.EYE), (hx + 6, top + 3, P.EYE), (hx + 7, top + 3, P.EYE)]
        hd.d += [(hx + 3, top + 8, m), (hx + 4, top + 8, m), (hx + 5, top + 8, m)]
        hd.px[(hx + 4, top + 9)] = P.MUZ
        hd.px[(hx + 3, top + 9)] = P.MUZ
    else:
        hd.d += [(hx + 3, top + 8, m), (hx + 4, top + 8, m), (hx + 5, top + 8, m)]
    cv.over(hd)
    return cv.image()


def horse_rear(i):
    """앞발 들기 (순서대로 3장): 0 무게를 뒤로 (뒷발을 몸 밑으로 딛고 앞이 가벼워짐) → 1 앞발이 땅에서 뜸 → 2 번쩍 일어섬
    (앞다리는 무릎을 꺾어 가슴 앞에 접고, 갈기·꼬리가 휘날림)"""
    P = HORSE
    cv = Cv(P)
    G = 22
    if i == 0:
        hip, sh, hx, top = (10, 12), (20, 11), 22, 3
        legs = (((11, 14), (12, 18), (14, G)), ((18, 14), (18, 18), (18, G)),
                ((9, 14), (10, 18), (12, G)), ((20, 14), (21, 18), (21, G)))
        tail = [(7, 11), (4, 12), (3, 15), (3, 19), (4, 21)]
    elif i == 1:
        hip, sh, hx, top = (11, 14), (19, 9), 21, 3
        legs = (((12, 16), (13, 19), (15, G)), ((18, 12), (21, 15), (20, 18)),
                ((10, 16), (10, 19), (12, G)), ((20, 12), (23, 14), (23, 17)))
        tail = [(9, 14), (6, 15), (4, 17), (3, 20), (4, 22)]
    else:
        hip, sh, hx, top = (12, 16), (17, 8), 20, 3
        legs = (((13, 17), (15, 20), (15, G)), ((17, 11), (20, 11), (20, 14)),
                ((11, 17), (10, 20), (12, G)), ((19, 11), (22, 12), (22, 15)))
        tail = [(10, 17), (7, 18), (5, 19), (3, 21), (2, 22)]
    horse_legs4(cv, legs)
    A.horse_tail(cv, tail, (3, 3, 2, 2))
    cv.capsule(hip[0], hip[1], sh[0], sh[1], (3.3, 3.6, 3.8)[i], 3.0)
    shine_edge(cv, hip[0] - 1, sh[0], P.FUR, P.FUR_HI)
    shine_edge(cv, hip[0] + 1, sh[0] - 1, P.FUR, P.FUR_DK, bottom=True)
    withers = (sh[0] - 1, sh[1] - 1)
    horse_neck2(cv, withers, (hx + 1, top + 3), r=2.6, stream=(0, 1, 2)[i], phase=i)
    cv.rect(hx - 1, top - 1, hx + 1, top + 1, P.MANE)
    horse_near_legs(cv, legs)
    hd = Cv(P)
    A.horse_head(hd, hx, top)
    horse_ears(hd, hx, top, "back" if i == 2 else "up")
    A.horse_face(hd.d, hx, top, mood=("normal", "talk", "talk")[i])
    cv.over(hd)
    if i == 2:                                                               # 히이잉! 기운 자국
        line(cv.fx, hx + 10, top + 4, hx + 11, top + 4)
        line(cv.fx, hx + 9, top + 8, hx + 10, top + 9)
        line(cv.fx, hx + 9, top, hx + 10, top - 1)
    return cv.image()


def horse_dustroll(i):
    """흙 목욕 (반복 2장): 벌러덩 누워 등을 흙에 비비며 네 다리를 허공에 버둥 — 0 다리를 접고 · 1 다리를 차올림 (흙먼지 폴폴)"""
    P = HORSE
    cv = Cv(P)
    s = (0, 1)[i]
    if i == 0:                                                               # 먼 다리 (몸 뒤)
        cv.leg2((11, 16), (9, 12), (11, 9), P.FAR, tip=P.HOOF)
        cv.leg2((17, 16), (19, 12), (18, 9), P.FAR, tip=P.HOOF)
    else:
        cv.leg2((11, 16), (11, 12), (13, 8), P.FAR, tip=P.HOOF)
        cv.leg2((17, 16), (18, 11), (20, 8), P.FAR, tip=P.HOOF)
    A.horse_tail(cv, [(6, 19), (4, 20), (3, 21), (2, 22)] if i == 0 else [(6, 19), (4, 18), (3, 17), (2, 18)], (3, 2, 2))
    cv.capsule(8.5 + s, 18.7, 19.0 + s, 18.7, 3.3)                          # 등이 바닥 (배가 위)
    leg = Cv(P)
    if i == 0:
        leg.leg2((9, 16), (6, 13), (7, 10), tip=P.HOOF)
        leg.rect(6, 11, 7, 11, P.SOCK)
        leg.leg2((19, 16), (21, 13), (20, 10), tip=P.HOOF)
    else:
        leg.leg2((10, 16), (8, 12), (8, 8), tip=P.HOOF)
        leg.rect(8, 9, 9, 9, P.SOCK)
        leg.leg2((19, 16), (22, 12), (23, 9), tip=P.HOOF)
    cv.over(leg)
    h = Cv(P)
    body = {"F": P.FUR, "U": P.MUZ, "M": P.MANE}
    det = {"n": (P.MUZ, P.NOSTRIL), "E": (P.FUR, P.EYE)}
    x0, y0 = 20 + s, 15
    for j, row in enumerate(HORSE_ROLL_HEAD):
        for k, ch in enumerate(row):
            if ch in body:
                h.px[(x0 + k, y0 + j)] = body[ch]
            elif ch in det:
                h.px[(x0 + k, y0 + j)] = det[ch][0]
                h.d.append((x0 + k, y0 + j, det[ch][1]))
    h.d += [(x0 + 6, y0 + 1, P.MOUTH), (x0 + 7, y0 + 1, P.MOUTH)]          # 입 (기분 좋게 헤)
    cv.over(h)
    if i == 0:                                                               # 흙먼지
        puff(cv.fx, 4.0, 20.0, 2.4); puff(cv.fx, 30.5, 20.5, 1.8); puff(cv.fx, 6.5, 15.5, 1.3)
        pts(cv.fx, [(14, 12), (24, 11), (3, 14), (28, 15)], DUST_DK)
    else:
        puff(cv.fx, 3.0, 19.0, 1.8); puff(cv.fx, 31.0, 19.5, 1.6); puff(cv.fx, 27.0, 13.5, 1.3)
        pts(cv.fx, [(15, 11), (5, 13), (31, 14), (25, 6)], DUST_DK)
    return cv.image()


HORSE_ROLL_HEAD = [
    # 벌러덩 누운 옆얼굴 (위아래 뒤집힘): 턱·주둥이가 위, 정수리·귀가 바닥 — U 밝은 주둥이 · n 콧구멍 · M 갈기 · E 감은 눈
    "....FFUUUU.",
    "...FFFUUUnU",
    "..FFFFFUUUU",
    ".FFFFFFFUUU",
    "MFFEEFFFFF.",
    "MMFFFFFF...",
    ".MFFFF.....",
    "..FF.......",
]


# ══════════════════════════════════════════════════════════════════════
def action_sheets():
    return {
        "dog_wag": [dog_wag(i) for i in range(2)],
        "dog_dig": [dog_dig(i) for i in range(2)],
        "dog_sniff": [dog_sniff(i) for i in range(2)],
        "dog_scratch": [dog_scratch(i) for i in range(2)],
        "dog_bow": [dog_bow(i) for i in range(2)],
        "dog_howl": [dog_howl(i) for i in range(3)],
        "dog_rollover": [dog_rollover(i) for i in range(2)],
        "lion_roar": [lion_roar(i) for i in range(3)],
        "lion_yawn": [lion_yawn(i) for i in range(3)],
        "lion_nap": [lion_nap(i) for i in range(3)],
        "lion_stalk": [lion_stalk(i) for i in range(2)],
        "lion_mane": [lion_mane(i) for i in range(2)],
        "lion_claws": [lion_claws(i) for i in range(2)],
        "horse_rear": [horse_rear(i) for i in range(3)],
        "horse_graze": [horse_graze(i) for i in range(2)],
        "horse_swish": [horse_swish(i) for i in range(2)],
        "horse_dustroll": [horse_dustroll(i) for i in range(2)],
        "horse_stomp": [horse_stomp(i) for i in range(2)],
        "horse_doze": [horse_doze(i) for i in range(3)],
    }


def check_margin(name, frames):
    bad = []
    for k, f in enumerate(frames):
        a = f.getchannel("A")
        if any(a.getpixel((0, y)) or a.getpixel((W - 1, y)) for y in range(H)):
            bad.append(k)
    if bad:
        print(f"  !! 여백 침범: {name} 프레임 {bad}")
    return not bad


ACT_KO = {
    "dog_wag": "살랑살랑", "dog_dig": "땅 파기", "dog_sniff": "킁킁", "dog_scratch": "뒷발로 벅벅", "dog_bow": "놀자! 절",
    "dog_howl": "아우우~ (한 번)", "dog_rollover": "배 만져 줘",
    "lion_roar": "어흥 (한 번)", "lion_yawn": "하암~ (한 번)", "lion_nap": "낮잠 (0=눕기)", "lion_stalk": "슬금슬금",
    "lion_mane": "갈기 부르르", "lion_claws": "앞발 휙",
    "horse_rear": "앞발 들기 (한 번)", "horse_graze": "풀 뜯기", "horse_swish": "꼬리 휙휙", "horse_dustroll": "흙 목욕",
    "horse_stomp": "쿵쿵", "horse_doze": "선 채로 졸기",
}


def _font(size, bold=False):
    for name in (("malgunbd.ttf", "malgun.ttf") if bold else ("malgun.ttf",)) + ("arial.ttf",):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def preview(rows, path, ref=None, compare=None):
    """×6 미리보기: 왼쪽 흰 바탕, 오른쪽 어두운 바탕. ref = 비교용 기본 자세 (맨 앞 칸, 빨간 테)"""
    S, G, LBL, HEAD = 6, 10, 200, 44
    maxn = max(len(fr) for _, fr in rows) + (1 if ref else 0)
    half = LBL + (W * S + G) * maxn + G
    pw, ph = half * 2, HEAD + (H * S + G) * len(rows) + G
    prev = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
    dr = ImageDraw.Draw(prev)
    dr.rectangle([half, 0, pw, ph], fill=(36, 36, 44, 255))
    f_name, f_ko, f_head = _font(19, True), _font(17), _font(18, True)
    for ox, ink in ((0, (40, 40, 40, 255)), (half, (230, 230, 240, 255))):
        dr.text((ox + 8, 12), "동물 행동 시트 ×6", fill=ink, font=f_head)
        heads = (["기본 자세(비교)"] if ref else []) + [f"{k}번" for k in range(maxn - (1 if ref else 0))]
        for k, t in enumerate(heads):
            dr.text((ox + LBL + k * (W * S + G) + 4, 14), t, fill=ink, font=f_ko)
    for r, (label, frames) in enumerate(rows):
        y = HEAD + G + r * (H * S + G)
        cells = ([ref[label.split("_")[0]]] if ref else []) + list(frames)
        for ox, ink, sub, box in ((0, (40, 40, 40, 255), (110, 110, 120, 255), (226, 226, 232, 255)),
                                  (half, (235, 235, 245, 255), (170, 170, 185, 255), (70, 70, 84, 255))):
            dr.text((ox + 8, y + H * S // 2 - 30), label, fill=ink, font=f_name)
            dr.text((ox + 8, y + H * S // 2 - 4), f"{ACT_KO.get(label, '')}", fill=sub, font=f_ko)
            dr.text((ox + 8, y + H * S // 2 + 18), f"{len(frames)}프레임", fill=sub, font=f_ko)
            for k, f in enumerate(cells):
                x = ox + LBL + k * (W * S + G)
                dr.rectangle([x - 1, y - 1, x + W * S, y + H * S], outline=(200, 120, 120, 255) if (ref and k == 0) else box)
                dr.line([(x, y + 23 * S), (x + W * S - 1, y + 23 * S)], fill=(255, 214, 214, 255) if ox == 0 else (84, 66, 76, 255))
                prev.alpha_composite(f.resize((W * S, H * S), Image.NEAREST), (x, y))
    if compare:
        prev = _append_compare(prev, compare)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    prev.convert("RGB").save(path)
    print("미리보기:", path)


def _append_compare(top, compare):
    """기본 시트 전/후 (×6, 흰 바탕): compare = [(이름, 전 프레임들, 후 프레임들)]"""
    S, G, LBL, HEAD = 6, 10, 200, 60
    maxn = max(max(len(b), len(a)) for _, b, a in compare)
    w = max(top.width, LBL + (W * S + G) * maxn + G)
    h = HEAD + (H * S + G) * 2 * len(compare) + G * len(compare) + G
    out = Image.new("RGBA", (w, top.height + h), (255, 255, 255, 255))
    out.alpha_composite(top, (0, 0))
    dr = ImageDraw.Draw(out)
    y = top.height
    dr.rectangle([0, y, w, y + 4], fill=(120, 120, 140, 255))
    dr.text((8, y + 18), "기본 시트 전 → 후 (디테일 업그레이드, ×6 흰 바탕) — 위 줄 = 전(v1), 아래 줄 = 후", fill=(40, 40, 40, 255), font=_font(20, True))
    y += HEAD
    f_name, f_ko = _font(19, True), _font(17)
    for name, before, after in compare:
        for tag, frames, box in (("전", before, (180, 180, 190, 255)), ("후", after, (200, 120, 120, 255))):
            dr.text((8, y + H * S // 2 - 22), name, fill=(40, 40, 40, 255), font=f_name)
            dr.text((8, y + H * S // 2 + 4), f"{tag} · {len(frames)}프레임", fill=(110, 110, 120, 255), font=f_ko)
            for k, f in enumerate(frames):
                x = LBL + k * (W * S + G)
                dr.rectangle([x - 1, y - 1, x + W * S, y + H * S], outline=box)
                out.alpha_composite(f.resize((W * S, H * S), Image.NEAREST), (x, y))
            y += H * S + G
        y += G
    return out


def _frames(sheet):
    return [sheet.crop((k * W, 0, k * W + W, H)) for k in range(sheet.width // W)]


def main(argv):
    force = "--덮어쓰기" in argv
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 1
    out = args[0]
    prev_path = args[1] if len(args) > 1 else None
    os.makedirs(out, exist_ok=True)
    acts = action_sheets()
    for name, frames in acts.items():
        check_margin(name, frames)
        path = os.path.join(out, f"{name}.png")
        if os.path.exists(path) and not force:
            print(f"{name}.png  이미 있음 — 건너뜀 (--덮어쓰기 로 새로 씀)")
            continue
        sheet = Image.new("RGBA", (W * len(frames), H), CLEAR)
        for k, f in enumerate(frames):
            sheet.alpha_composite(f, (k * W, 0))
        sheet.save(path)
        print(f"{name}.png  {len(frames)}프레임")
    if prev_path:
        ref = {"dog": A.dog_sit(), "lion": A.lion_sit(), "horse": A.horse_stand()}
        compare = None
        old = next((a.split("=", 1)[1] for a in argv if a.startswith("--전후=")), None)
        if old:                                      # 기본 시트 전(백업 폴더) / 후(지금 생성기) 비교 칸 붙이기
            compare = []
            for an, kinds in A.sheets().items():
                for kind, frames in kinds.items():
                    bp = os.path.join(old, f"{an}_{kind}.png")
                    if os.path.exists(bp):
                        compare.append((f"{an}_{kind}", _frames(Image.open(bp).convert("RGBA")), frames))
        preview(list(acts.items()), prev_path, ref, compare)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
