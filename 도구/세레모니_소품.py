"""
Pixel TMI 도착 세레모니 소품 — 목적지에 닿으면 펫이 들고 노는 소품을 고양이·위험표시와 같은 결
(밝은 색 도트 + 자동 1px 진한 외곽선)로 그린다. 위험표시_도트.py 의 Cv 캔버스를 그대로 쓰고,
겹치는 물건 사이에도 외곽선이 생기도록 begin()/end() 묶음 그리기만 더했다.

사용: python 세레모니_소품.py [출력 폴더(assets/pet)] [미리보기.png]
     인자를 빼면 이 파일 위치 기준으로  ../app/src/main/assets/pet  과
     ../../스크린샷/91_세레모니_소품_시안.png  에 저장한다.
출력: prop_<이름>.png — 프레임을 가로로 이어 붙인 시트, 배경 투명.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

OUT = (46, 48, 56, 255)      # 외곽선
CLEAR = (0, 0, 0, 0)
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def c(r, g, b):
    return (r, g, b, 255)


# ── 팔레트 ──
GOLD, GOLD_L, GOLD_W, GOLD_S, GOLD_D = c(246, 192, 44), c(255, 226, 110), c(255, 250, 214), c(222, 150, 26), c(176, 106, 22)
RED, RED_L, RED_D = c(228, 52, 56), c(252, 118, 106), c(168, 30, 42)
BLUE, BLUE_L, BLUE_D = c(64, 134, 232), c(148, 196, 252), c(40, 92, 182)
YEL, YEL_L, YEL_D = c(252, 210, 48), c(255, 240, 150), c(216, 160, 28)
GRN, GRN_L, GRN_D = c(84, 184, 84), c(158, 226, 124), c(44, 128, 64)
ORG, ORG_L, ORG_D = c(246, 132, 38), c(255, 184, 92), c(204, 90, 26)
PINK, PINK_L, PINK_D = c(250, 122, 174), c(255, 188, 216), c(214, 68, 130)
PUR, PUR_L = c(152, 94, 222), c(198, 152, 250)
WHITE = c(252, 252, 252)
WOOD, WOOD_L, WOOD_D = c(178, 114, 62), c(208, 148, 88), c(126, 78, 42)
CARD, CARD_L, CARD_D = c(214, 162, 98), c(238, 202, 146), c(174, 120, 64)
SPK, SPK2 = c(255, 240, 140), c(255, 204, 60)


class Cv:
    def __init__(self, w=24, h=24):
        self.w, self.h = w, h
        self.px = {}
        self.top = {}      # 외곽선 위에 얹는 디테일 (외곽선 계산에서 빠짐)
        self.g = None      # begin()~end() 사이에 모으는 '앞쪽 물건'
        self.gt = None

    def put(self, x, y, col, top=False):
        x, y = int(x), int(y)
        if not (0 <= x < self.w and 0 <= y < self.h):
            return
        if self.g is not None:
            (self.gt if top else self.g)[(x, y)] = col
        else:
            (self.top if top else self.px)[(x, y)] = col

    def erase(self, x, y):
        for d in (self.px, self.top):
            d.pop((x, y), None)

    def fill(self, pts, col, top=False):
        for (x, y) in pts:
            self.put(x, y, col(x, y) if callable(col) else col, top)

    def rect(self, x0, y0, x1, y1, col, top=False):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, col, top)

    def ellipse(self, cx, cy, rx, ry, col, top=False):
        self.fill(ell_pts(cx, cy, rx, ry), col, top)

    # 앞에 겹쳐지는 물건: 뒤 물건과 맞닿는 자리에 외곽선을 그어 떼어 놓는다
    def begin(self):
        self.g, self.gt = {}, {}

    def end(self):
        g, gt = self.g, self.gt
        self.g = self.gt = None
        for (x, y) in g:
            for dx, dy in N4:
                n = (x + dx, y + dy)
                if n not in g and n in self.px:
                    self.px[n] = OUT
                    self.top.pop(n, None)
            self.top.pop((x, y), None)
        self.px.update(g)
        self.top.update(gt)

    def image(self, outline=True):
        im = Image.new("RGBA", (self.w, self.h), CLEAR)
        if outline:
            for (x, y) in list(self.px):
                for dx, dy in N4:
                    n = (x + dx, y + dy)
                    if n not in self.px and 0 <= n[0] < self.w and 0 <= n[1] < self.h:
                        im.putpixel(n, OUT)
        for d in (self.px, self.top):
            for (x, y), col in d.items():
                im.putpixel((x, y), col)
        return im


def ell_pts(cx, cy, rx, ry):
    return {(x, y) for y in range(int(cy - ry) - 1, int(cy + ry) + 2)
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2)
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0}


def rell_pts(cx, cy, rx, ry, deg):
    """기울어진 타원 (deg: 화면 좌표, 0=오른쪽, 90=아래)."""
    a = math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    R = max(rx, ry) + 1
    pts = set()
    for y in range(int(cy - R) - 1, int(cy + R) + 2):
        for x in range(int(cx - R) - 1, int(cx + R) + 2):
            dx, dy = x - cx, y - cy
            u, w = dx * ca + dy * sa, -dx * sa + dy * ca
            if (u / rx) ** 2 + (w / ry) ** 2 <= 1.0:
                pts.add((x, y))
    return pts


def poly_pts(pts):
    """다각형 (꼭짓점은 픽셀 모서리 좌표, 픽셀 중심이 안에 들면 칠함)."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    out = set()
    n = len(pts)
    for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
        for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
            px, py = x + .5, y + .5
            inside = False
            j = n - 1
            for i in range(n):
                xi, yi = pts[i]
                xj, yj = pts[j]
                if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                    inside = not inside
                j = i
            if inside:
                out.add((x, y))
    return out


def line_pts(x0, y0, x1, y1):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    return [(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n)) for i in range(int(n) + 1)]


def art(v, rows, pal, ox=0, oy=0, top=False):
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in pal:
                v.put(ox + x, oy + y, pal[ch], top)


def sparkle(v, x, y, size=2):
    """반짝이 (외곽선 없음): 가운데 흰 점 + 노란 팔."""
    v.put(x, y, WHITE, True)
    for dx, dy in N4:
        v.put(x + dx, y + dy, SPK, True)
        if size >= 2:
            v.put(x + 2 * dx, y + 2 * dy, SPK2, True)


def sheet(frames):
    w, h = frames[0].size
    s = Image.new("RGBA", (w * len(frames), h), CLEAR)
    for i, f in enumerate(frames):
        s.paste(f, (i * w, 0))
    return s


DIG = {   # 3x5 숫자
    "1": [".X.", "XX.", ".X.", ".X.", "XXX"],
    "2": ["XXX", "..X", "XXX", "X..", "XXX"],
    "3": ["XXX", "..X", ".XX", "..X", "XXX"],
}
DIG_BIG1 = [".XX.", "XXX.", ".XX.", ".XX.", ".XX.", ".XX.", "XXXX"]   # 4x7 굵은 1


def digit(v, ch, ox, oy, col, big=False):
    rows = DIG_BIG1 if big else DIG[ch]
    art(v, rows, {"X": col}, ox, oy, top=True)


# ════════════════════════════ 소품 ════════════════════════════

# ── 트로피: 금 컵 + 양쪽 손잡이 + 나무 받침, 둘째 프레임은 반짝 ──
def trophy(shine):
    v = Cv()
    for cx in (3.5, 19.5):                                    # 손잡이 고리 (컵 뒤)
        ring = ell_pts(cx, 6.5, 3.4, 3.4) - ell_pts(cx, 6.5, 1.5, 1.5)
        v.fill(ring, lambda x, y: GOLD_L if y < 6 else GOLD_S)
    v.begin()
    rows = {1: (4, 19), 2: (5, 18), 3: (5, 18), 4: (5, 18), 5: (5, 18), 6: (6, 17), 7: (6, 17),
            8: (7, 16), 9: (8, 15), 10: (9, 14), 11: (10, 13)}
    for y, (a, b) in rows.items():
        for x in range(a, b + 1):
            col = GOLD
            if x <= a + 1:
                col = GOLD_L
            elif x >= b - 1:
                col = GOLD_S
            v.put(x, y, col)
    v.rect(4, 1, 19, 1, GOLD_L)
    v.rect(6, 2, 17, 2, GOLD_D)                               # 컵 안쪽 그늘
    v.rect(11, 12, 12, 14, GOLD); v.rect(12, 12, 12, 14, GOLD_S)
    v.rect(9, 15, 14, 15, GOLD_L); v.rect(8, 16, 15, 16, GOLD_S)
    v.rect(6, 17, 17, 21, WOOD); v.rect(6, 17, 17, 17, WOOD_L); v.rect(6, 21, 17, 21, WOOD_D)
    v.rect(9, 18, 14, 19, GOLD_L); v.rect(9, 19, 14, 19, GOLD)
    v.end()
    art(v, ["..X..", "XXXXX", ".XXX.", ".X.X."], {"X": GOLD_S}, 9, 4, top=True)   # 별 무늬
    if shine:
        v.rect(7, 3, 7, 8, GOLD_W, top=True); v.put(8, 3, GOLD_W, True)
        sparkle(v, 8, 4, 2)
        sparkle(v, 20, 14, 1)
        sparkle(v, 2, 13, 1)
    else:
        v.rect(7, 3, 7, 6, GOLD_W, top=True)
    return v.image()


# ── 왕관: 세 봉우리 + 진주 + 보석 띠, 둘째 프레임은 반짝 ──
def crown(shine):
    v = Cv()
    pts = [(2, 6), (7, 11), (11.5, 5), (16, 11), (21, 6)]

    def top_y(x):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                return round(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
        return 99
    for x in range(2, 22):
        for y in range(top_y(x), 19):
            col = GOLD
            if x <= 3:
                col = GOLD_L
            elif x >= 20:
                col = GOLD_S
            v.put(x, y, col)
    for x in range(2, 22):                                    # 봉우리 테두리 밝게
        v.put(x, top_y(x), GOLD_L)
    v.rect(2, 13, 21, 13, GOLD_L); v.rect(2, 14, 21, 17, GOLD); v.rect(2, 18, 21, 18, GOLD_S)
    v.rect(2, 14, 2, 17, GOLD_L); v.rect(21, 14, 21, 17, GOLD_S)
    PE, PS = c(252, 248, 238), c(214, 206, 196)
    for (x0, y0, s) in ((1, 3, 3), (10, 2, 4), (20, 3, 3)):  # 봉우리 위 진주 (네모 + 4방향 외곽선 = 동글)
        v.rect(x0, y0, x0 + s - 1, y0 + s - 1, PE)
        v.rect(x0 + 1, y0 + s - 1, x0 + s - 1, y0 + s - 1, PS)
        v.rect(x0 + s - 1, y0 + 1, x0 + s - 1, y0 + s - 1, PS)
        v.put(x0, y0, WHITE)
    # 보석: 가운데 빨강, 양옆 파랑
    v.rect(10, 14, 13, 17, RED); v.erase(10, 14); v.erase(13, 14); v.erase(10, 17); v.erase(13, 17)
    v.put(10, 14, GOLD); v.put(13, 14, GOLD); v.put(10, 17, GOLD); v.put(13, 17, GOLD)
    v.rect(10, 14, 13, 17, OUT, top=True)
    for p in ((10, 14), (13, 14), (10, 17), (13, 17)):
        v.top.pop(p, None)
    v.rect(11, 15, 12, 16, RED, top=True); v.put(11, 15, RED_L, True); v.put(11, 14, RED, True); v.put(12, 14, RED, True)
    v.put(11, 17, RED_D, True); v.put(12, 17, RED_D, True); v.put(10, 15, RED, True); v.put(10, 16, RED, True)
    v.put(13, 15, RED_D, True); v.put(13, 16, RED_D, True); v.put(11, 14, WHITE, True)
    for gx in (5, 18):
        for (dx, dy) in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
            v.put(gx + dx, 15 + dy, BLUE, True)
        v.put(gx, 14, BLUE_L, True); v.put(gx - 1, 15, BLUE_L, True); v.put(gx, 16, BLUE_D, True); v.put(gx + 1, 15, BLUE_D, True)
    v.rect(11, 8, 12, 9, RED, top=True); v.put(11, 8, RED_L, True)   # 가운데 봉우리 작은 보석
    if shine:
        sparkle(v, 16, 4, 2)
        sparkle(v, 5, 11, 1)
        v.put(3, 9, GOLD_W, True); v.put(3, 10, GOLD_W, True)
    return v.image()


# ── 메달: 빨간 리본 두 갈래 + 금메달 + '1' ──
def medal():
    v = Cv()
    v.fill(poly_pts([(3, 1), (9, 1), (14, 12), (8, 12)]), RED_D)
    v.fill(poly_pts([(5.5, 1), (6.5, 1), (11.5, 12), (10.5, 12)]), RED)
    v.begin()
    v.fill(poly_pts([(15, 1), (21, 1), (16, 12), (10, 12)]), RED)
    v.fill(poly_pts([(17.5, 1), (18.5, 1), (13.5, 12), (12.5, 12)]), RED_L)
    v.end()
    v.begin()
    v.rect(10, 9, 13, 10, GOLD_S)                             # 고리
    v.ellipse(11.5, 16, 6.5, 6.5, GOLD_S)
    v.ellipse(11.5, 16, 5.4, 5.4, GOLD)
    v.ellipse(11.0, 15.5, 4.2, 4.2, GOLD_L)
    v.ellipse(11.5, 16, 3.6, 3.6, GOLD)
    v.end()
    for (x, y) in ((7, 13), (8, 12), (9, 11), (7, 14)):
        v.put(x, y, GOLD_W, True)
    art(v, [".X.", "XX.", ".X.", ".X.", ".X.", "XXX"], {"X": GOLD_D}, 10, 13, top=True)
    return v.image()


# ── 시상대 (32x24): 가운데 1등이 가장 높고, 2·3등 양옆 ──
def podium():
    v = Cv(32, 24)
    FR, FR_S = c(246, 246, 250), c(206, 210, 222)
    blocks = [(1, 10, 10, c(196, 204, 218), c(150, 158, 176)),
              (11, 20, 4, GOLD, GOLD_S),
              (21, 30, 14, c(226, 152, 96), c(178, 104, 58))]
    for (x0, x1, yt, top, top_d) in blocks:
        v.rect(x0, yt, x1, 22, FR)
        v.rect(x0, yt, x1, yt + 1, top)
        v.rect(x0, yt + 2, x1, yt + 2, top_d)
        v.rect(x0, 22, x1, 22, FR_S)
        v.rect(x1, yt + 3, x1, 21, FR_S)
    v.rect(11, 10, 11, 22, OUT, top=True)                    # 블록 사이 경계
    v.rect(20, 14, 20, 22, OUT, top=True)
    digit(v, "1", 14, 10, GOLD_D, big=True)
    digit(v, "2", 4, 15, c(120, 128, 146))
    digit(v, "3", 24, 17, c(178, 104, 58))
    v.put(12, 4, GOLD_W, True); v.put(13, 4, GOLD_W, True); v.put(2, 10, WHITE, True); v.put(22, 14, c(250, 200, 160), True)
    return v.image()


# ── 케이크: 분홍 크림 + 스펀지 + 초 세 개, 불꽃 일렁 ──
def cake(phase):
    v = Cv()
    SP, SP_D, CR = c(248, 214, 152), c(220, 174, 110), c(255, 250, 240)
    candles = ((6, BLUE, BLUE_L), (11, PUR, PUR_L), (16, GRN, GRN_L))
    for (x0, col, coll) in candles:
        v.rect(x0, 6, x0 + 1, 10, col)
        for y in (7, 9):
            v.put(x0, y, WHITE); v.put(x0 + 1, y - 1, WHITE)
        v.put(x0, 6, coll)
    v.fill(ell_pts(11.5, 21, 10.5, 1.9), c(214, 224, 238))
    v.begin()
    v.rect(3, 13, 20, 20, SP)
    v.rect(3, 17, 20, 17, CR)
    v.rect(3, 20, 20, 20, SP_D)
    v.rect(20, 13, 20, 19, SP_D)
    v.rect(3, 11, 20, 13, PINK)
    for (x, y1) in ((4, 15), (5, 15), (8, 14), (12, 16), (13, 16), (17, 14), (19, 15)):
        v.rect(x, 13, x, y1, PINK)
    v.rect(4, 11, 15, 11, PINK_L)
    v.rect(20, 11, 20, 13, PINK_D)
    v.end()
    for (x, y, col) in ((5, 12, RED), (9, 12, YEL), (14, 12, BLUE_L), (18, 12, RED), (7, 13, GRN_L), (16, 13, YEL)):
        v.put(x, y, col, True)                               # 스프링클
    for (x0, _, _) in candles:
        v.put(x0, 5, c(70, 60, 60), True)                    # 심지
        if phase == 0:
            fl = {(x0, 4): ORG, (x0 + 1, 4): ORG, (x0, 3): YEL, (x0 + 1, 3): ORG, (x0, 2): YEL_L, (x0, 1): YEL_L}
        else:
            fl = {(x0, 4): ORG, (x0 + 1, 4): ORG, (x0, 3): ORG, (x0 + 1, 3): YEL, (x0 + 1, 2): YEL_L}
        for (x, y), col in fl.items():
            v.put(x, y, col)
        v.put(x0, 5, c(70, 60, 60))
    return v.image()


# ── 풍선 셋: 빨강·파랑·노랑, 끈이 한 점에 모이고 살랑 ──
def balloons(phase):
    v = Cv()
    specs = [((RED, RED_L, RED_D), 12, 5.5), ((BLUE, BLUE_L, BLUE_D), 6.5, 8.5), ((YEL, YEL_L, YEL_D), 17.5, 8.5)]
    sway = [(0, 0), (0, 0), (0, 0)] if phase == 0 else [(1, 0), (1, -1), (1, 1)]
    knots = []
    for ((col, coll, cold), cx, cy), (dx, dy) in zip(specs, sway):
        cx, cy = cx + dx, cy + dy
        v.begin()
        pts = ell_pts(cx, cy, 3.6, 4.4)
        v.fill(pts, lambda x, y, cx=cx, cy=cy: cold if (x - cx) + (y - cy) * 0.8 > 3.2 else col)
        kx, ky = round(cx), int(cy + 4.4) + 1
        v.put(kx, ky, cold); v.put(kx - 1, ky + 1, cold); v.put(kx, ky + 1, cold); v.put(kx + 1, ky + 1, cold)
        v.end()
        for (x, y) in ((round(cx) - 2, round(cy) - 2), (round(cx) - 2, round(cy) - 1), (round(cx) - 1, round(cy) - 3)):
            v.put(x, y, WHITE, True)
        v.put(round(cx) - 1, round(cy) - 2, coll, True)
        knots.append((kx, ky + 2))
    tie = (12 + phase, 20)
    for (kx, ky) in knots:
        for (x, y) in line_pts(kx, ky, tie[0], tie[1]):
            if (x, y) not in v.px:
                v.put(x, y, c(96, 96, 108), True)
    v.put(tie[0], 21, c(96, 96, 108), True); v.put(tie[0] - phase, 22, c(96, 96, 108), True)
    return v.image()


# ── 원반: 빨간 프리스비, 반사광이 테를 따라 돈다 ──
def frisbee(phase):
    v = Cv()
    cx, cy, tilt = 11.5, 11.0, -12                           # 비스듬히 기운 원반 (윗면이 넓게 보이게)
    ang = math.radians(tilt)

    def on(rx, ry, th, dx=0.0, dy=0.0):                       # 기운 타원 위의 한 점
        a = math.radians(th)
        u, w = math.cos(a) * rx, math.sin(a) * ry
        return round(cx + dx + u * math.cos(ang) - w * math.sin(ang)), round(cy + dy + u * math.sin(ang) + w * math.cos(ang))
    v.fill(rell_pts(cx, cy + 1.3, 10.3, 5.4, tilt), RED_D)   # 옆면 두께
    top = rell_pts(cx, cy, 10.3, 5.4, tilt)
    v.fill(top, RED)
    lip = top - rell_pts(cx, cy, 8.8, 4.3, tilt)
    v.fill(lip, lambda x, y: RED_L if (-(x - cx) * math.sin(ang) + (y - cy) * math.cos(ang)) < 0.5 else RED)
    v.fill(rell_pts(cx, cy + 0.3, 6.0, 3.0, tilt) - rell_pts(cx, cy + 0.3, 4.8, 2.2, tilt), RED_D)   # 홈 고리
    v.fill(rell_pts(cx - 0.4, cy - 0.2, 2.6, 1.2, tilt), RED_L)                                     # 가운데 볼록
    ths = range(195, 250, 9) if phase == 0 else range(290, 345, 9)
    for th in ths:                                           # 테를 따라 도는 반사광
        v.put(*on(9.5, 4.85, th), WHITE, True)
    for th in ((205, 230) if phase == 0 else (300, 325)):
        v.put(*on(3.6, 1.8, th + 180), c(255, 196, 186), True)
    sw = c(150, 160, 182)                                    # 휙휙 도는 바람결 호
    arcs = ((200, 250), (20, 70)) if phase == 0 else ((290, 340), (110, 160))
    for (a0, a1) in arcs:
        for th in range(a0, a1 + 1, 5):
            x, y = on(11.9, 7.2, th, 0, 0.6)
            if (x, y) not in v.px:
                v.put(x, y, sw, True)
    return v.image()


# ── 골판지 상자: 0=날개 열린 빈 상자, 1=앞면+날개만(고양이가 뒤에서 고개 내밀 자리) ──
def box(full):
    v = Cv()
    IN, IN2 = c(118, 78, 42), c(150, 100, 56)
    if full:
        v.fill(poly_pts([(7, 4), (17, 4), (18, 10), (6, 10)]), CARD_L)       # 뒷날개
        v.rect(7, 4, 16, 4, c(250, 222, 176))
        v.begin()
        v.fill(poly_pts([(6, 10), (18, 10), (20, 13), (4, 13)]), IN)       # 상자 속
        v.rect(6, 10, 17, 10, IN2)
        v.end()
    v.begin()
    v.fill(poly_pts([(6, 10), (4, 13), (1, 12), (2, 7)]), CARD_L)          # 왼 날개
    v.end()
    v.begin()
    v.fill(poly_pts([(18, 10), (20, 13), (23, 12), (22, 7)]), CARD)        # 오른 날개
    v.end()
    v.begin()
    v.rect(4, 15, 19, 22, CARD)                                          # 앞면
    v.rect(19, 15, 19, 22, CARD_D)
    v.rect(4, 22, 19, 22, CARD_D)
    v.end()
    v.begin()
    v.rect(4, 13, 19, 15, CARD_L)                                        # 앞쪽 날개(접혀 내려옴)
    v.rect(4, 15, 19, 15, c(250, 222, 176))
    v.end()
    v.rect(14, 18, 17, 20, WHITE, top=True)                              # 송장 스티커
    v.rect(15, 19, 16, 19, c(150, 156, 170), top=True)
    TP = c(246, 228, 190)                                                # 뜯긴 테이프
    v.rect(11, 13, 12, 15, TP, top=True); v.put(11, 16, TP, True)
    v.rect(6, 18, 9, 18, CARD_D, top=True); v.rect(6, 20, 8, 20, CARD_D, top=True)   # 인쇄 줄
    return v.image()


# ── 당근: 주황 몸통 + 초록 잎 ──
def carrot():
    v = Cv()
    T, P = (15.5, 8.0), (4.0, 21.0)
    ax, ay = P[0] - T[0], P[1] - T[1]
    L2 = ax * ax + ay * ay
    L = math.sqrt(L2)
    for deg, ln in ((-95, 7.0), (-52, 8.4), (-10, 6.8)):
        a = math.radians(deg)
        cx, cy = T[0] + math.cos(a) * (ln / 2 + 1), T[1] + math.sin(a) * (ln / 2 + 1)
        v.fill(rell_pts(cx, cy, ln / 2, 1.8, deg), GRN)
        for k in range(1, int(ln) - 1):
            v.put(round(T[0] + math.cos(a) * (k + 1.5)), round(T[1] + math.sin(a) * (k + 1.5)), GRN_L)
    v.begin()
    W0 = 4.0
    for y in range(24):
        for x in range(24):
            qx, qy = x - T[0], y - T[1]
            t = (qx * ax + qy * ay) / L2
            d = (qx * ay - qy * ax) / L
            if t < 0:
                ok = qx * qx + qy * qy <= W0 * W0
                w = W0
            elif t <= 1:
                w = W0 * (1 - t) + 0.45
                ok = abs(d) <= w
            else:
                ok = False
            if ok:
                col = ORG
                if d < -w * 0.4:
                    col = ORG_L
                elif d > w * 0.5:
                    col = ORG_D
                v.put(x, y, col)
    v.end()
    for i, t in enumerate((0.2, 0.38, 0.56, 0.74)):
        bx, by = T[0] + ax * t, T[1] + ay * t
        w = W0 * (1 - t)
        s = 1 if i % 2 == 0 else -1
        for k in range(2):
            dd = s * (w - 0.6 - k)
            x = round(bx + ay / L * dd)
            y = round(by - ax / L * dd)
            v.put(x, y, ORG_D, True)
    return v.image()


# ── 보물상자: 0=닫힘, 1=열림 + 반짝이는 금화 ──
def chest(opened):
    v = Cv()
    BAND, BAND_S = GOLD, GOLD_S
    if opened:
        v.rect(3, 3, 20, 9, WOOD_D)                              # 열린 뚜껑 안쪽
        v.rect(5, 5, 18, 9, c(156, 40, 52))                      # 붉은 안감
        v.rect(3, 3, 20, 3, BAND)
        v.rect(6, 3, 7, 9, BAND_S); v.rect(16, 3, 17, 9, BAND_S)
        v.begin()                                                # 금화 더미
        v.ellipse(11.5, 12, 8.4, 3.2, GOLD)
        for (x, y) in ((6, 11), (9, 10), (13, 10), (16, 11), (11, 12), (8, 12), (15, 12)):
            v.put(x, y, GOLD_L); v.put(x + 1, y, GOLD_S)
        v.end()
        v.rect(10, 9, 11, 10, RED, top=True); v.put(10, 9, RED_L, True)   # 보석 한 알
        v.put(17, 10, BLUE, True); v.put(17, 9, BLUE_L, True)
    else:
        v.ellipse(11.5, 9.5, 8.5, 3.2, WOOD)                    # 둥근 뚜껑
        v.rect(3, 9, 20, 12, WOOD)
        v.ellipse(11.5, 9.0, 7.0, 2.0, WOOD_L)
        v.rect(3, 12, 20, 12, WOOD_D)
        v.rect(6, 7, 7, 12, BAND); v.rect(16, 7, 17, 12, BAND)
        v.put(6, 7, GOLD_L); v.put(16, 7, GOLD_L)
    v.begin()
    v.rect(3, 13, 20, 21, WOOD)
    v.rect(3, 13, 20, 13, BAND)
    v.rect(3, 17, 20, 17, WOOD_D)
    v.rect(3, 21, 20, 21, BAND_S)
    v.rect(6, 13, 7, 21, BAND); v.rect(16, 13, 17, 21, BAND)
    v.rect(7, 14, 7, 21, BAND_S); v.rect(17, 14, 17, 21, BAND_S)
    v.rect(20, 14, 20, 20, WOOD_D)
    v.end()
    v.begin()
    v.rect(10, 12 if not opened else 13, 13, 16, GOLD)          # 자물쇠
    v.rect(10, 12 if not opened else 13, 13, 12 if not opened else 13, GOLD_L)
    v.end()
    v.rect(11, 14, 12, 14, c(60, 40, 30), top=True); v.put(11, 15, c(60, 40, 30), True)
    if opened:
        sparkle(v, 7, 7, 2)
        sparkle(v, 16, 6, 1)
        sparkle(v, 21, 11, 1)
        v.put(13, 11, GOLD_W, True); v.put(8, 11, GOLD_W, True)
    return v.image()


# ── 마녀 가마솥: 검은 솥 + 초록 물약, 거품이 보글보글 ──
def cauldron(phase):
    v = Cv()
    IR, IR_L, IR_D = c(78, 80, 100), c(126, 130, 154), c(60, 62, 80)
    PO, PO_L, PO_D = c(110, 214, 64), c(186, 250, 120), c(60, 160, 50)
    v.rect(6, 20, 7, 22, IR_D); v.rect(16, 20, 17, 22, IR_D)
    v.begin()
    v.fill(ell_pts(11.5, 15.5, 9.6, 6.6), lambda x, y: IR_L if (x - 11.5) < -5 and y < 16 else (IR_D if y > 18 else IR))
    v.end()
    v.begin()
    v.ellipse(11.5, 10.5, 10.4, 2.6, IR_L)
    v.ellipse(11.5, 10.3, 8.4, 1.6, PO)
    v.end()
    v.rect(6, 10, 15, 10, PO_L, top=True)
    v.rect(16, 12, 17, 14, PO, top=True); v.put(17, 15, PO, True); v.put(16, 12, PO_L, True)   # 넘쳐흐른 물약
    v.put(3, 12, c(170, 174, 196), True); v.put(4, 13, c(170, 174, 196), True)
    bubbles = ((7, 7, 1.4), (14, 5, 1.9), (10, 1.5, 1.0), (18, 8, 0.9)) if phase == 0 else \
              ((8, 5, 1.4), (15, 2.5, 1.9), (11, 8, 1.0), (5, 8, 0.9))
    for (bx, by, r) in bubbles:
        v.begin()
        v.ellipse(bx, by, r, r, PO)
        v.end()
        v.put(round(bx - r * 0.5), round(by - r * 0.5), PO_L, True)
    v.put(5, 10, PO_D, True); v.put(17, 10, PO_D, True)
    return v.image()


# ── 호박 사탕바구니: 주황 호박 양동이 + 손잡이 + 사탕 ──
def candybag():
    v = Cv()
    HD = PUR
    for x in range(2, 22):                                    # 보라 손잡이 (포물선, 사탕 뒤)
        t = (x - 11.5) / 9.5
        v.put(x, round(1 + 9 * t * t), HD)
    v.put(2, 11, HD); v.put(21, 11, HD)
    v.begin()
    v.fill(ell_pts(11.5, 15.5, 9.6, 7.0), lambda x, y: ORG_L if x < 6 and y < 16 else ORG)
    v.end()
    for x0 in (7, 16):                                        # 호박 골
        for y in range(10, 22):
            dx = 0 if 12 < y < 19 else (1 if x0 < 11 else -1)
            if (x0 + dx, y) in v.px:
                v.put(x0 + dx, y, ORG_D, True)
    v.begin()
    v.ellipse(11.5, 10.0, 7.6, 1.8, c(96, 42, 20))           # 입구
    v.end()
    # 사탕: 입구에서 위로 삐죽
    v.begin()
    v.rect(6, 7, 9, 8, PINK); v.put(5, 6, PINK_L); v.put(5, 9, PINK_L); v.put(10, 6, PINK_L); v.put(10, 9, PINK_L)
    v.put(7, 7, PINK_L)
    v.end()
    v.begin()
    v.rect(14, 3, 14, 9, WHITE)                               # 막대사탕
    v.end()
    v.begin()
    v.ellipse(14, 3.5, 2.4, 2.4, RED)
    v.end()
    v.put(13, 3, WHITE, True); v.put(14, 4, WHITE, True); v.put(15, 3, WHITE, True); v.put(14, 2, RED_L, True)
    v.begin()
    v.rect(10, 8, 12, 9, BLUE); v.put(10, 8, BLUE_L)
    v.end()
    v.begin()
    v.rect(16, 8, 18, 9, GRN); v.put(16, 8, GRN_L)
    v.end()
    v.rect(5, 10, 18, 10, c(96, 42, 20), top=True)            # 앞 테두리가 사탕 밑동을 가림
    v.rect(4, 11, 19, 11, ORG_D, top=True)
    # 호박 얼굴
    F = c(70, 34, 20)
    for (x, y) in ((7, 15), (8, 15), (9, 15), (8, 14), (14, 15), (15, 15), (16, 15), (15, 14)):   # 세모 눈
        v.put(x, y, F, True)
    for (x, y) in ((6, 17), (17, 17)):                        # 씩 웃는 입 (이빨 두 개)
        v.put(x, y, F, True)
    v.rect(7, 18, 16, 18, F, True); v.rect(9, 19, 14, 19, F, True)
    v.put(10, 18, ORG_L, True); v.put(13, 18, ORG_L, True)
    return v.image()


# ── 공룡 뼈 화석: 흙 둔덕에 반쯤 묻힌 큰 뼈 + 암모나이트 ──
def fossil():
    v = Cv()
    BO, BO_S, BO_W = c(244, 236, 212), c(204, 190, 158), c(255, 252, 240)
    DI, DI_D, DI_L = c(156, 108, 66), c(118, 80, 48), c(186, 138, 90)
    # 뼈 (흙 뒤에서 비스듬히 솟음)
    for (x, y) in line_pts(6, 17, 16, 7):
        v.rect(x - 1, y, x + 1, y, BO)
    for (kx, ky) in ((15, 4.5), (18.5, 7.5)):
        v.ellipse(kx, ky, 1.9, 1.9, BO)
    for (x, y) in line_pts(6, 16, 15, 7):
        v.put(x + 1, y, BO_S)
    v.put(14, 4, BO_W); v.put(17, 7, BO_W); v.put(9, 13, BO_W); v.put(10, 12, BO_W)
    v.begin()
    pts = {p for p in ell_pts(11.5, 22.5, 10.8, 9.0) if p[1] <= 21}
    v.fill(pts, lambda x, y: DI_L if y < 17 and x < 11 else (DI_D if y >= 20 else DI))
    v.end()
    for (x, y) in ((4, 19), (8, 17), (17, 18), (20, 20), (13, 20), (6, 21)):
        v.put(x, y, DI_D, True)
    for (x, y) in ((3, 17), (19, 16)):
        v.put(x, y, c(170, 170, 178), True); v.put(x + 1, y, c(136, 136, 146), True)
    # 암모나이트 소용돌이
    for (x, y) in ((14, 16), (15, 16), (16, 17), (16, 18), (15, 19), (14, 19), (13, 18), (13, 17), (14, 17), (15, 18)):
        v.put(x, y, BO_S, True)
    v.put(14, 18, DI_D, True)
    # 흙 속 작은 뼛조각
    v.rect(5, 19, 7, 19, BO_S, top=True); v.put(4, 18, BO_S, True); v.put(8, 20, BO_S, True)
    return v.image()


# ── 물고기: 파란 물고기가 펄떡 (몸을 휘며 들썩) ──
FISH = [
    "..........FF.........",
    ".........FFFF........",
    "......DDDDDDDDD...TT.",
    "....DDBBBBBBBBBD.TTT.",
    "...DBWWBBBBBBBBBBTTTT",
    "..DBWKKBGBBBBBBBTTTT.",
    ".BBBBKKBGBBBBBBBBTT..",
    "MBBBBBBBGBBBBBBBTTT..",
    ".LLLLLLGLLLLLLLLTTTT.",
    "..LLLLLLLLLLLLLL.TTTT",
    "....LLLLLLLLLL....TT.",
    "........ff...........",
]


def fish(phase):
    v = Cv()
    pal = {"B": BLUE, "D": BLUE_D, "L": c(196, 228, 255), "W": WHITE, "K": c(30, 34, 46), "G": BLUE_D,
           "F": c(76, 166, 246), "T": c(76, 166, 246), "M": BLUE_D, "f": c(76, 166, 246)}
    bend = 2.6 if phase == 0 else -2.6
    oy = 9 if phase == 0 else 5
    ox = 1
    w = len(FISH[0])
    for y, row in enumerate(FISH):
        for x, ch in enumerate(row):
            if ch in pal:
                off = round(bend * ((x - w / 2) / (w / 2)) ** 2)
                top = ch in "WKG"
                v.put(ox + x, oy + y - off, pal[ch], top)
                if top:
                    v.put(ox + x, oy + y - off, pal[ch])
    if phase == 1:
        for (x, y) in ((3, 2), (2, 4), (20, 1), (22, 3), (11, 20), (13, 21)):
            v.put(x, y, c(120, 190, 250), True)
        v.put(3, 1, c(200, 236, 255), True); v.put(21, 1, c(200, 236, 255), True)
    else:
        for (x, y) in ((1, 22), (3, 22), (19, 22), (21, 22)):
            v.put(x, y, c(120, 190, 250), True)
    return v.image()


# ── 선물상자: 빨간 상자 + 노란 리본, 둘째 프레임은 뚜껑이 퐁 + 반짝이 ──
def gift(pop):
    v = Cv()
    dy = -5 if pop else 0
    dx = 1 if pop else 0
    v.begin()
    v.rect(4, 13, 19, 21, RED)
    v.rect(4, 13, 4, 21, RED_L); v.rect(19, 13, 19, 21, RED_D); v.rect(4, 21, 19, 21, RED_D)
    v.rect(11, 13, 12, 21, YEL); v.rect(11, 13, 11, 21, YEL_L)
    v.end()
    if pop:
        v.rect(5, 13, 18, 13, c(110, 20, 30), top=True)      # 열린 입구
        v.rect(11, 13, 12, 13, YEL_D, top=True)
    v.begin()
    v.rect(3 + dx, 10 + dy, 20 + dx, 12 + dy, RED)           # 뚜껑
    v.rect(3 + dx, 10 + dy, 20 + dx, 10 + dy, RED_L)
    v.rect(3 + dx, 12 + dy, 20 + dx, 12 + dy, RED_D)
    v.rect(11 + dx, 10 + dy, 12 + dx, 12 + dy, YEL); v.put(11 + dx, 10 + dy, YEL_L)
    v.end()
    v.begin()                                                # 리본 고리 둘
    for sx in (-1, 1):
        lc = (11.5 + dx + sx * 3.6, 7.2 + dy)
        v.fill(rell_pts(lc[0], lc[1], 3.2, 2.0, -20 * sx), lambda x, y, lc=lc: YEL_L if y < lc[1] - 0.5 else YEL)
    v.end()
    for sx in (-1, 1):                                       # 고리 안쪽 접힌 그늘
        bx = round(11.5 + dx + sx * 2.6)
        v.put(bx, 7 + dy, YEL_D, True); v.put(bx + sx, 7 + dy, YEL_D, True)
    v.begin()                                                # 가운데 매듭
    v.rect(11 + dx, 7 + dy, 12 + dx, 9 + dy, YEL_D)
    v.put(11 + dx, 7 + dy, YEL)
    v.end()
    if pop:
        for (x, y, s) in ((11, 9, 2), (4, 9, 1), (19, 8, 1), (7, 11, 1), (16, 11, 1), (2, 5, 1), (22, 4, 1)):
            sparkle(v, x, y, s)
        for (x, y, col) in ((8, 8, PINK), (15, 7, BLUE_L), (14, 10, GRN_L), (9, 10, YEL)):
            v.put(x, y, col, True)
    return v.image()


# ── 꽃가루 (8x8 x4): 색·기울기가 다른 조각 ──
def confetti(i):
    v = Cv(8, 8)
    if i == 0:
        v.rect(2, 3, 5, 4, RED); v.rect(2, 3, 5, 3, RED_L)
    elif i == 1:
        for k in range(3):
            v.rect(2 + k, 5 - k, 3 + k, 5 - k, BLUE)
            v.put(2 + k, 5 - k, BLUE_L)
    elif i == 2:
        v.rect(3, 2, 4, 5, YEL); v.rect(3, 2, 3, 5, YEL_L)
    else:
        for (x, y) in ((3, 2), (4, 3), (2, 3), (3, 3), (3, 4), (4, 4), (5, 4), (4, 5)):
            v.put(x, y, GRN)
        v.put(3, 2, GRN_L); v.put(2, 3, GRN_L)
    return v.image()


# ── 하트 (16x16): 분홍 하트, 둘째 프레임은 크게 두근 ──
HEART_S = [
    ".XXX..XXX.",
    "XXXXXXXXXX",
    "XXXXXXXXXX",
    "XXXXXXXXXX",
    ".XXXXXXXX.",
    "..XXXXXX..",
    "...XXXX...",
    "....XX....",
]
HEART_B = [
    "..XXX....XXX..",
    ".XXXXX..XXXXX.",
    "XXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXX",
    ".XXXXXXXXXXXX.",
    "..XXXXXXXXXX..",
    "...XXXXXXXX...",
    "....XXXXXX....",
    ".....XXXX.....",
    "......XX......",
]


def heart(big):
    v = Cv(16, 16)
    rows, ox, oy = (HEART_B, 1, 2) if big else (HEART_S, 3, 4)
    w = len(rows[0])
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "X":
                col = PINK
                if x + y > w + len(rows) * 0.45:
                    col = PINK_D
                v.put(ox + x, oy + y, col)
    if big:
        for (x, y) in ((2, 1), (3, 1), (1, 2), (1, 3)):
            v.put(ox + x, oy + y, WHITE, True)
        v.put(ox + 4, oy + 1, PINK_L, True); v.put(ox + 2, oy + 2, PINK_L, True)
    else:
        for (x, y) in ((1, 1), (2, 1), (1, 2)):
            v.put(ox + x, oy + y, WHITE, True)
    return v.image()


# ── 헬기장 (32x12): 둥근 패드 + 노란 테 + H ──
def helipad():
    v = Cv(32, 12)
    AS, AS_L = c(98, 104, 118), c(130, 136, 150)
    v.ellipse(15.5, 5.6, 15.0, 4.9, AS)
    v.fill({p for p in ell_pts(15.5, 5.6, 15.0, 4.9) if p[1] <= 2}, AS_L)
    ring = ell_pts(15.5, 5.6, 12.4, 3.9) - ell_pts(15.5, 5.6, 11.0, 3.0)
    v.fill(ring, YEL, top=True)
    W = c(250, 250, 250)
    v.rect(12, 3, 13, 8, W, top=True); v.rect(18, 3, 19, 8, W, top=True); v.rect(14, 5, 17, 6, W, top=True)
    for th in (0, 60, 120, 180, 240, 300):
        a = math.radians(th)
        x, y = round(15.5 + math.cos(a) * 14.2), round(5.6 + math.sin(a) * 4.4)
        v.put(x, y, c(150, 255, 150) if th % 120 == 0 else c(255, 250, 200), True)
    return v.image()


# ── 무대 조명 (16x16): 비스듬히 아래를 비추는 조명 머리 ──
def spotlight():
    v = Cv(16, 16)
    BD, BD_L, BD_D = c(70, 74, 92), c(150, 156, 178), c(52, 54, 70)
    GR, GR_L = c(176, 182, 198), c(218, 222, 232)
    deg = 28                                                 # 오른쪽 아래를 겨눈 긴 깡통
    ax, ay = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    cx, cy = 6.0, 7.4
    v.rect(3, 1, 7, 1, GR_L); v.rect(4, 2, 6, 2, GR)          # 걸이
    v.rect(4, 3, 5, 6, GR)                                   # U자 받침 팔 (깡통 뒤)
    body = {}
    for y in range(16):
        for x in range(16):
            u = (x - cx) * ax + (y - cy) * ay
            w = -(x - cx) * ay + (y - cy) * ax
            half = 2.3 + (u + 5.4) / 8.4 * 0.8               # 앞으로 갈수록 살짝 넓어짐
            if -5.4 <= u <= 3.0 and abs(w) <= half:
                col = BD
                if -half * 0.75 <= w <= -half * 0.2:
                    col = BD_L                               # 원통 윗면 광택 줄
                elif w > half * 0.55:
                    col = BD_D
                if round(u) in (-4, -2) and col != BD_L:
                    col = BD_D                               # 방열 홈
                body[(x, y)] = col
            elif 3.0 < u <= 4.0 and abs(w) <= 3.6:
                body[(x, y)] = BD_D                          # 앞 테
    v.begin()
    for (x, y), col in body.items():
        v.put(x, y, col)
    v.end()
    lx, ly = cx + ax * 4.3, cy + ay * 4.3
    v.begin()
    v.fill(rell_pts(lx, ly, 1.0, 3.1, deg), c(255, 230, 110))   # 렌즈
    v.end()
    v.fill(rell_pts(lx + 0.2, ly + 0.1, 0.5, 1.7, deg), WHITE, top=True)
    v.rect(4, 6, 5, 7, GR_L, top=True)                      # 회전축 볼트
    RAY = c(255, 222, 90)
    for k, (dw) in enumerate((-2.2, 0.0, 2.2)):              # 앞으로 뻗는 빛살 세 줄
        for t in (1.8, 2.8, 3.8):
            u = 4.3 + t
            x = round(cx + ax * u - ay * dw * (1 + t * 0.25))
            y = round(cy + ay * u + ax * dw * (1 + t * 0.25))
            if (x, y) not in v.px:
                v.put(x, y, RAY if t < 3.5 else c(255, 240, 170), True)
    return v.image()


# ── 피냐타: 별 모양 줄무늬 + 술, 둘째 프레임은 금 가고 사탕이 터져 나옴 ──
def pinata(broken):
    v = Cv()
    cx, cy, R, r = 12.0, 13.5, 9.6, 4.6
    pts = []
    for i in range(10):
        a = math.radians(-90 + i * 36)
        rr = R if i % 2 == 0 else r
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    star = poly_pts(pts)
    cols = [PINK, YEL, c(80, 196, 236), GRN, ORG, PUR]
    body = {(x, y): cols[((y - 3) // 2) % len(cols)] for (x, y) in star}
    for (x, y) in star:                                       # 오른쪽 아래 가장자리 그늘
        if (x + 1, y) not in star and (x, y + 1) not in star:
            r_, g_, b_, _ = body[(x, y)]
            body[(x, y)] = c(int(r_ * .8), int(g_ * .8), int(b_ * .8))
    tass = {}                                                 # 뾰족한 끝마다 색 술
    for i, col in zip((2, 4, 6, 8), (RED, BLUE, YEL, GRN)):
        tx, ty = pts[i]
        x, y = int(tx) - (1 if tx > cx else 0), int(ty) - (1 if ty > cy else 0)
        sx = 1 if tx > cx else -1
        for p in ((x + sx, y), (x + sx, y + 1), (x + 2 * sx, y + 1), (x + sx, y + 2)):
            tass[p] = col
    hl = {(11, 5): WHITE, (10, 7): WHITE, (9, 9): WHITE}
    ROPE = c(176, 128, 72)
    if not broken:
        v.rect(11, 0, 11, 4, ROPE)                            # 매단 줄
        v.begin()
        for p, col in body.items():
            v.put(*p, col)
        v.end()
        for d in (tass, hl):
            for p, col in d.items():
                v.put(*p, col, True)
        return v.image()
    # 깨짐: 별을 2칸 올리고 아랫배에 뻥 뚫린 구멍 + 금, 구멍 아래로 사탕이 쏟아진다
    up = 2
    v.rect(11, 0, 11, 2, ROPE)
    hole = {(x, y) for (x, y) in star if 15 <= y <= 18 and abs(x - 11.5) <= 1.0 + (0.6 if y == 16 else 0) + ((x + y) % 2) * 0.6}
    v.begin()
    for p, col in body.items():
        v.put(p[0], p[1] - up, col)
    v.end()
    for (x, y) in hole:
        v.put(x, y - up, c(84, 40, 60))                       # 속이 보이는 구멍
    for (x, y) in hole:                                       # 구멍 가장자리는 외곽선 색으로 들쭉날쭉
        for dx, dy in N4:
            n = (x + dx, y + dy)
            if n not in hole and n in star:
                v.put(n[0], n[1] - up, OUT)
    for p, col in tass.items():
        v.put(p[0], p[1] - up, col, True)
    for (x, y) in line_pts(10, 14, 8, 12) + line_pts(13, 14, 15, 12) + line_pts(11, 14, 11, 12):   # 구멍에서 뻗은 금
        if (x, y) in star:
            v.put(x, y - up, OUT, True)
    v.put(11, 5 - up, WHITE, True); v.put(10, 7 - up, WHITE, True)
    for (x, y, col) in ((10, 18, PINK), (5, 21, BLUE), (16, 21, GRN), (11, 22, RED)):
        v.begin()                                             # 포장 사탕: 몸통 3칸 + 흰 리본 끝
        v.rect(x, y, x + 2, y, col)
        v.end()
        v.put(x, y, WHITE, True)
        v.put(x - 1, y - 1, WHITE, True); v.put(x - 1, y + 1, WHITE, True)
        v.put(x + 3, y - 1, WHITE, True); v.put(x + 3, y + 1, WHITE, True)
    for (x, y) in ((11, 15), (13, 17), (8, 17), (15, 18)):
        v.put(x, y, SPK2, True)
    sparkle(v, 20, 15, 1); sparkle(v, 2, 15, 1)
    return v.image()


# ── 미스터리 서클 (48x16): 풀밭에 눌린 원 무늬, 위에서 비스듬히 ──
def cropcircle():
    v = Cv(48, 16)
    GR_, GR_D, GR_L = c(86, 164, 70), c(58, 128, 54), c(130, 200, 94)
    FL, FL_D = c(232, 228, 140), c(202, 196, 108)
    cx, cy = 23.5, 7.5
    field = ell_pts(cx, cy, 23.2, 6.9)
    v.fill(field, GR_)
    for (x, y) in field:                                      # 서 있는 풀 (짧은 세로 획, 듬성듬성)
        if (x * 7 + y * 13) % 19 == 0 and (x, y - 1) in field:
            v.put(x, y, GR_D, True); v.put(x, y - 1, GR_D, True)
        elif (x * 11 + y * 5) % 29 == 0:
            v.put(x, y, GR_L, True)
    def flat(pts, col=FL):
        v.fill(pts, col, top=True)
    flat(ell_pts(cx, cy, 11.2, 5.1))                          # 큰 원 (눌린 밀)
    flat(ell_pts(cx, cy, 9.0, 3.9), GR_)                      # 서 있는 고리
    flat(ell_pts(cx, cy, 7.8, 3.2))
    flat(ell_pts(cx, cy, 2.6, 1.0), GR_)                      # 가운데 남긴 점
    for th in range(0, 360, 30):                              # 눌린 방향 결 (소용돌이)
        a = math.radians(th)
        for rr in (4.4, 6.0):
            b = a + rr * 0.12
            v.put(round(cx + math.cos(b) * rr), round(cy + math.sin(b) * rr * 0.42), FL_D, True)
    v.rect(7, 7, 12, 8, FL, True); v.rect(35, 7, 40, 8, FL, True)   # 양옆으로 뻗는 길
    for sx in (6.0, 41.0):                                    # 양옆 작은 원
        flat(ell_pts(sx, cy, 3.6, 2.2))
        flat(ell_pts(sx, cy, 1.3, 0.6), GR_)
    v.put(1, 7, FL, True); v.put(1, 8, FL, True); v.put(46, 7, FL, True); v.put(46, 8, FL, True)
    return v.image()


# ── 세차 거품: 비누 거품 뭉치, 방울이 둥실 ──
def carwash(phase):
    v = Cv()
    FO, FO_S = c(250, 252, 255), c(206, 226, 248)
    BU, BU_R, IRI = c(226, 244, 255), c(150, 206, 248), c(232, 190, 250)
    v.begin()
    for (fx, fy, rx, ry) in ((5, 20, 4.2, 2.6), (11.5, 19, 5.2, 3.2), (18.5, 20, 4.4, 2.6), (8, 17.5, 2.6, 2.0), (15, 17, 3.0, 2.2)):
        v.ellipse(fx, fy, rx, ry, FO)
    for x in range(2, 22):
        if (x, 22) in v.g:
            v.put(x, 22, FO_S)
    v.end()
    v.put(9, 16, FO_S, True); v.put(16, 15, FO_S, True); v.put(6, 19, FO_S, True); v.put(19, 19, FO_S, True)
    bubs = ((7, 11, 3.2), (15.5, 8, 4.0), (11, 2.5, 1.8), (20, 14, 1.8), (3.5, 5, 1.5)) if phase == 0 else \
           ((6.5, 9, 3.2), (16, 6.5, 4.0), (10, 13.5, 1.6), (20.5, 11, 1.8), (4, 2.5, 1.5))
    for (bx, by, r) in bubs:
        v.begin()
        pts = ell_pts(bx, by, r, r)
        inner = ell_pts(bx, by, max(r - 1.1, 0.4), max(r - 1.1, 0.4))
        v.fill(pts, lambda x, y: BU if (x, y) in inner else BU_R)
        v.end()
        ix, iy = round(bx - r * 0.45), round(by - r * 0.45)
        v.put(ix, iy, WHITE, True)
        if r >= 3:
            v.put(ix + 1, iy - 1, WHITE, True); v.put(ix - 1, iy + 1, WHITE, True)
            v.put(round(bx + r * 0.5), round(by + r * 0.5), IRI, True)
    if phase == 0:
        sparkle(v, 21, 3, 1)
    else:
        sparkle(v, 2, 13, 1)
    return v.image()


# ════════════════════════════ 목록 ════════════════════════════
def build():
    return [
        ("trophy", "트로피", [trophy(False), trophy(True)]),
        ("crown", "왕관", [crown(False), crown(True)]),
        ("medal", "메달", [medal()]),
        ("podium", "시상대", [podium()]),
        ("cake", "케이크", [cake(0), cake(1)]),
        ("balloons", "풍선", [balloons(0), balloons(1)]),
        ("frisbee", "원반", [frisbee(0), frisbee(1)]),
        ("box", "상자(1=앞면만)", [box(True), box(False)]),
        ("carrot", "당근", [carrot()]),
        ("chest", "보물상자", [chest(False), chest(True)]),
        ("cauldron", "가마솥", [cauldron(0), cauldron(1)]),
        ("candybag", "사탕바구니", [candybag()]),
        ("fossil", "화석", [fossil()]),
        ("fish", "물고기", [fish(0), fish(1)]),
        ("gift", "선물", [gift(False), gift(True)]),
        ("confetti", "꽃가루 8x8", [confetti(i) for i in range(4)]),
        ("heart", "하트 16x16", [heart(False), heart(True)]),
        ("helipad", "헬기장 32x12", [helipad()]),
        ("spotlight", "조명 16x16", [spotlight()]),
        ("pinata", "피냐타", [pinata(False), pinata(True)]),
        ("cropcircle", "미스터리서클 48x16", [cropcircle()]),
        ("carwash", "세차거품", [carwash(0), carwash(1)]),
    ]


def preview(items, path, S=8, cols=4):
    """8배 확대 · 흰 바탕 · 프레임 나란히 + 이름(한글 / 파일명·크기)."""
    try:
        font = ImageFont.truetype("malgunbd.ttf", 30)
        small = ImageFont.truetype("malgunbd.ttf", 22)
    except OSError:
        font = small = ImageFont.load_default()
    cell_w, cell_h = 62 * S, (24 + 14) * S
    rows = (len(items) + cols - 1) // cols
    pv = Image.new("RGBA", (cols * cell_w, rows * cell_h), (255, 255, 255, 255))
    d = ImageDraw.Draw(pv)
    for i, (name, ko, frames) in enumerate(items):
        x0 = (i % cols) * cell_w + 4 * S
        y0 = (i // cols) * cell_h + 11 * S
        fw, fh = frames[0].size
        gap = 4
        if fw * len(frames) + gap * (len(frames) - 1) > 56:
            gap = 2
        for j, f in enumerate(frames):
            pv.alpha_composite(f.resize((fw * S, fh * S), Image.NEAREST), (x0 + j * (fw + gap) * S, y0 + (24 - fh) * S))
        d.text((x0, y0 - 10 * S), ko, fill=(40, 40, 46, 255), font=font)
        d.text((x0, y0 - 5 * S), f"prop_{name}.png  {fw}x{fh} × {len(frames)}", fill=(110, 112, 124, 255), font=small)
    pv.convert("RGB").save(path)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    base = os.path.dirname(here)
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base, "app", "src", "main", "assets", "pet")
    pv = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(base), "스크린샷", "91_세레모니_소품_시안.png")
    items = build()
    for name, _, frames in items:
        sheet(frames).save(os.path.join(out, f"prop_{name}.png"))
    preview(items, pv)
    print("ok", len(items))


if __name__ == "__main__":
    main()
