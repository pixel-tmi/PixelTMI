"""
Pixel TMI 상점용 배경 테마 6종 도트 만들기 — 우주 · 공룡시대 · 조선시대 · 할로윈 · 벚꽃길 · 여름 바다.

결: 기본 배경(PetView.buildBackdrop)과 같다. 1픽셀 = 1도트, 높이 130칸,
    앱이 최근접(계단)으로 확대해서 옅게(알파 105/255 ≈ 41%) 흰 차 화면 위에 그린다.
  - 가로 640칸. 좌우로 이어 붙여도 이음새가 없다 (앱이 가로로 반복해 깐다).
    → 모든 그림을 '가로로 감기는' 그림판에 그리고, 땅 높이도 640칸 주기 물결로만 만든다.
  - 하늘은 투명 (차 화면이 흰색이니 흰 하늘은 안 그린다).
  - 맨 아래 줄 = 고양이가 걷는 땅선. 맨 아래 줄은 전부 땅색으로 꽉 찬다.
  - 키 큰 것들은 아래 110줄 안에 (위쪽 20줄은 거의 비워 둔다).
  - 옅게 그려도 보이도록 실루엣마다 테마 색의 진한 외곽선을 두른다.

사용: python 배경_테마.py [출력 폴더] [미리보기.png]
  인자가 없으면 이 파일 기준 ../app/src/main/assets/bg 와 ../../스크린샷/78_배경_테마_시안.png 에 저장.
출력: <테마>.png      640×130, 투명 배경, 가로 반복용
      <테마>_icon.png 48×48, 액자 안 작은 장면 (불투명, 상점 칸용)
테마: space(우주) · dino(공룡시대) · joseon(조선시대) · halloween(할로윈) · cherry(벚꽃길) · beach(여름 바다)
"""
import math
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont

W, H = 640, 130          # 띠 크기 (1픽셀 = 1도트)
GY = H - 1               # 맨 아래 줄 = 땅선
CLEAR = (0, 0, 0, 0)
PREVIEW_ALPHA = 0.40     # 미리보기의 '앱 느낌' 옅기 (앱은 105/255 ≈ 0.41)


def C(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)


BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def on(x, y, t):
    """4×4 바이어 점묘: 비율 t(0~1)만큼 점을 켠다"""
    return BAYER[int(y) % 4][int(x) % 4] < t * 16


def rd(v):
    return int(math.floor(v + 0.5))


def wd(a, b):
    """가로로 감기는 띠에서 a-b 거리 (−W/2 ~ W/2)"""
    d = (a - b) % W
    return d - W if d > W / 2 else d


def bez(pts, t):
    pts = list(pts)
    while len(pts) > 1:
        pts = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in zip(pts, pts[1:])]
    return pts[0]


def wave(x, terms):
    """이음새 없는 물결: terms = [(640칸 안의 주기 수 k, 크기, 위상)]"""
    return sum(a * math.sin(2 * math.pi * k * x / W + p) for k, a, p in terms)


def hsh(x, y, n):
    """자리마다 고정된 주사위 (점 무늬용)"""
    return ((x * 73856093) ^ (y * 19349663) ^ 0x5bd1e995) % n


# ─────────────────────────────── 그림판 ───────────────────────────────
class Pic:
    """투명 그림판. wrap=True 면 가로가 감긴다(띠 배경용)."""

    def __init__(self, w, h, wrap=False):
        self.w, self.h, self.wrap = int(w), int(h), wrap
        self.im = Image.new("RGBA", (self.w, self.h), CLEAR)
        self.p = self.im.load()
        self.ax, self.ay = self.w // 2, self.h - 1      # 기준점(땅에 닿는 점)

    def _q(self, x, y):
        x, y = int(math.floor(x)), int(math.floor(y))
        if self.wrap:
            x %= self.w
        if 0 <= x < self.w and 0 <= y < self.h:
            return x, y
        return None

    def px(self, x, y, c):
        q = self._q(x, y)
        if q and c:
            self.p[q] = c

    def get(self, x, y):
        q = self._q(x, y)
        return self.p[q] if q else CLEAR

    def hline(self, x0, x1, y, c):
        for x in range(rd(x0), rd(x1) + 1):
            self.px(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(rd(y0), rd(y1) + 1):
            self.px(x, y, c)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(rd(y0), rd(y1) + 1):
            self.hline(x0, x1, y, c)

    def ell(self, cx, cy, rx, ry, c, fn=None):
        """채운 타원 (도트용으로 반 칸 넉넉히). fn(dx,dy,x,y) → 색"""
        ex, ey = rx + 0.4, ry + 0.4
        for y in range(int(math.floor(cy - ey)), int(math.ceil(cy + ey)) + 1):
            for x in range(int(math.floor(cx - ex)), int(math.ceil(cx + ex)) + 1):
                dx, dy = x - cx, y - cy
                if (dx / ex) ** 2 + (dy / ey) ** 2 <= 1.0:
                    self.px(x, y, fn(dx, dy, x, y) if fn else c)

    def line(self, x0, y0, x1, y1, c, w=1):
        n = int(max(abs(x1 - x0), abs(y1 - y0)))
        for i in range(n + 1):
            t = i / n if n else 0
            x, y = rd(x0 + (x1 - x0) * t), rd(y0 + (y1 - y0) * t)
            for oy in range(w):
                for ox in range(w):
                    self.px(x + ox - (w - 1) // 2, y + oy - (w - 1) // 2, c)

    def path(self, pts, c, dotted=0):
        """1픽셀 곡선 (베지어). dotted=n 이면 n칸마다 한 점"""
        L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        n = max(2, int(L * 2.5))
        last = None
        k = 0
        for i in range(n + 1):
            x, y = bez(pts, i / n)
            q = (rd(x), rd(y))
            if q != last:
                if not dotted or k % dotted == 0:
                    self.px(q[0], q[1], c)
                k += 1
                last = q

    def curve(self, pts, r0, r1, c, fn=None):
        """베지어를 따라 굵기 r0→r1 로 원을 찍은 굵은 곡선 (목·꼬리·줄기)"""
        L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        n = max(2, int(L * 2))
        for i in range(n + 1):
            t = i / n
            x, y = bez(pts, t)
            r = r0 + (r1 - r0) * t
            if r < 0.6:
                xx, yy = rd(x), rd(y)
                self.px(xx, yy, fn(0, 0, xx, yy) if fn else c)
            else:
                self.ell(x, y, r, r, c, fn)

    def poly(self, pts, c, fn=None):
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(int(math.floor(min(ys))), int(math.ceil(max(ys))) + 1):
            yc = y + 1e-4
            xs = []
            for i in range(n):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(rd(xs[i]), rd(xs[i + 1]) + 1):
                    self.px(x, y, fn(x, y) if fn else c)

    def art(self, rows, pal, x0=0, y0=0, flip=False):
        for j, row in enumerate(rows):
            if flip:
                row = row[::-1]
            for i, ch in enumerate(row):
                c = pal.get(ch)
                if c:
                    self.px(x0 + i, y0 + j, c)

    def outline(self, c, diag=False):
        """그림 둘레에 1칸 외곽선 (그림판 가장자리는 비워 둘 것)"""
        a = Image.new("L", (self.w + 2, self.h + 2), 0)       # 1칸 여백 → 반대편으로 감겨 넘어가지 않게
        a.paste(self.im.getchannel("A"), (1, 1))
        dil = a
        sh = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if diag:
            sh += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dx, dy in sh:
            dil = ImageChops.lighter(dil, ImageChops.offset(a, dx, dy))
        ring = ImageChops.subtract(dil, a).crop((1, 1, self.w + 1, self.h + 1))
        self.im.paste(Image.new("RGBA", self.im.size, c), (0, 0), ring)
        self.p = self.im.load()

    def paste(self, o, x, y):
        x, y = int(x), int(y)
        for off in ((-self.w, 0, self.w) if self.wrap else (0,)):
            xx = x + off
            if xx >= self.w or xx + o.w <= 0:
                continue
            self.im.paste(o.im, (xx, y), o.im)
        self.p = self.im.load()

    def place(self, o, x, y):
        """o 의 기준점(ax, ay)이 (x, y)에 오게 붙인다"""
        self.paste(o, rd(x) - o.ax, rd(y) - o.ay)


def crop(P, m=1):
    bb = P.im.getbbox()
    if not bb:
        return P
    x0, y0, x1, y1 = bb
    x0, y0 = max(0, x0 - m), max(0, y0 - m)
    x1, y1 = min(P.w, x1 + m), min(P.h, y1 + m)
    Q = Pic(x1 - x0, y1 - y0)
    Q.im = P.im.crop((x0, y0, x1, y1))
    Q.p = Q.im.load()
    Q.ax, Q.ay = P.ax - x0, P.ay - y0
    return Q


def sprite(rows, pal, out=None, flip=False, diag=False):
    """글자 그림 → 그림 (기준점 = 맨 아래 줄 가운데)"""
    w, h = max(len(r) for r in rows), len(rows)
    P = Pic(w + 4, h + 4)
    P.art(rows, pal, 2, 2, flip)
    if out:
        P.outline(out, diag)
    P.ax, P.ay = 2 + w // 2, 2 + h - 1
    return crop(P)


def center(P):
    """기준점을 그림 가운데로"""
    P.ax, P.ay = P.w // 2, P.h // 2
    return P


def fill_profile(S, tops, bottom, color_fn, edge=None):
    """열마다 tops[x] ~ bottom 을 칠한다. edge 가 있으면 윗선(옆 계단 포함)을 그 색으로."""
    for x in range(W):
        t = tops[x]
        if t > bottom:
            continue
        nb = max(tops[(x - 1) % W], tops[(x + 1) % W]) - 1
        ee = max(t, nb) if edge else t - 1
        for y in range(t, bottom + 1):
            if edge and y <= ee:
                S.px(x, y, edge)
            else:
                c = color_fn(x, y, y - t)
                if c:
                    S.px(x, y, c)


def sphere_light(dx, dy, r):
    """구 위의 밝기 (왼쪽 위에서 빛)"""
    nx, ny = dx / (r + 0.4), dy / (r + 0.4)
    z = math.sqrt(max(0.0, 1 - nx * nx - ny * ny))
    return -0.5 * nx - 0.55 * ny + 0.65 * z


# ─────────────────────────────── 아이콘 공통 ───────────────────────────────
def icon_sky(cols):
    I = Pic(48, 48)
    n = len(cols)
    for y in range(48):
        t = y / 47 * (n - 1)
        i = min(n - 2, int(t))
        f = t - i
        for x in range(48):
            I.px(x, y, cols[i + 1] if on(x, y, f) else cols[i])
    return I


def icon_frame(I, out, light, dark):
    for i in range(48):
        for q in ((i, 0), (i, 47), (0, i), (47, i)):
            I.px(q[0], q[1], out)
    for i in range(1, 47):
        I.px(i, 1, light)
        I.px(1, i, light)
        I.px(i, 46, dark)
        I.px(46, i, dark)
    for q in ((1, 1), (46, 1), (1, 46), (46, 46)):
        I.px(q[0], q[1], out)
    return I


def icon_ground(I, y0, top, fill, fn=None):
    for x in range(48):
        I.px(x, y0, top)
        for y in range(y0 + 1, 48):
            I.px(x, y, fn(x, y) if fn else fill)


# ═══════════════════════════════ 1. 우주 ═══════════════════════════════
SP = dict(
    OUT=C("3e3a64"), GOLD=C("eeb23a"), BLUE=C("7a88e2"), PINK=C("e27cba"), LAV=C("a49ae0"), WARM=C("fff0b8"),
    W=C("f4f4fa"), w=C("c8cae0"), s=C("9a9cbc"), R=C("e04c4c"), r=C("b03a4c"), B=C("62acee"), b=C("3c72c4"),
    V=C("f4b040"), v=C("d0802c"), L=C("fff2c0"), P=C("aeb0cc"),
    Y=C("fae264"), O=C("f6982e"), D=C("e85a32"),
    G0=C("6c6896"), G1=C("d6d4e8"), G2=C("bcb9d4"), G3=C("a09dc0"), G4=C("8482aa"),
)

ROCKET = [
    ".....R.....",
    "....RRr....",
    "...RRRrr...",
    "...WWWww...",
    "..WWWWWww..",
    "..WWsssww..",
    "..WsBBbsw..",
    "..WsBbbsw..",
    "..WWsssww..",
    "..WWWWWww..",
    "..WWWWWww..",
    "..WRRRrrw..",
    "..WWWWWww..",
    ".RWWWWWwwr.",
    "RRWWWWWwwrr",
    "RRRWWWwwrrr",
    "RR.sssss.rr",
    "....OYO....",
    "....OYO....",
    "....DOD....",
    ".....D.....",
]

ASTRO = [
    "....WWWWW.....",
    "...WWWWWWw....",
    "..WWVVVVVww...",
    "..WVLVVVVvw..W",
    "..WVVVVVVvw.WW",
    "..WWvvvvvww.Ww",
    "...WWWWWww.Ww.",
    ".PWWWWWWWwWw..",
    "sPWWWRBWWww...",
    "s.PWWWWWWw....",
    "W..WWWWWww....",
    "...WWsssww....",
    "...WWW.WWw....",
    "...WWW..WWw...",
    "..WWWs...WWs..",
    "..sss.....ss..",
]

LANDER = [
    "......ssssss......",
    ".....sWWWWWWs.....",
    ".....sWbbWWWs..s..",
    ".....sWbBWWws.ss..",
    "....VVVVVVVVVVV...",
    "....VvVvVvVvVvV...",
    "....VVVVVVVVVVV...",
    "......sOOOOOs.....",
]
LANDER_LEGS = [
    "....s.........s...",
    "....s.........s...",
    "...s...........s..",
    "...s...........s..",
    "..s.............s.",
    ".sss...........sss",
]

FLAG = [
    "OOOO....",
    "OOOOOO..",
    "VVVVVVVV",
    "OOOOOO..",
    "OOOO....",
]


def sp_ringed(r, rx, ry, tilt, body, ring, out):
    base, light, dark, band = body
    ro, ri, rg = ring
    m = 3
    w = int(2 * rx) + 2 * m + 2
    h = int(2 * max(r, ry + abs(tilt) * rx)) + 2 * m + 2
    P = Pic(w, h)
    cx, cy = w // 2, h // 2

    def ringpass(front):
        for y in range(h):
            for x in range(w):
                dx, dy = x - cx, y - cy
                yy = dy - dx * tilt
                q = (dx / (rx + 0.4)) ** 2 + (yy / (ry + 0.4)) ** 2
                if 0.50 <= q <= 1.0 and ((yy > 0) == front):
                    col = ro if q > 0.80 else ri
                    if 0.68 < q <= 0.78:
                        col = rg
                    P.px(x, y, col)

    ringpass(False)
    bw = max(2.0, r / 3.2)

    def pf(dx, dy, x, y):
        lit = sphere_light(dx, dy, r)
        k = int(math.floor((dy + 0.12 * dx + r) / bw))
        col = band if k % 2 else base
        if lit > 0.78 and on(x, y, (lit - 0.78) * 5):
            col = light
        if lit < 0.22 and on(x, y, (0.22 - lit) * 3 + 0.25):
            col = dark
        return col

    P.ell(cx, cy, r, r, base, pf)
    ringpass(True)
    P.outline(out)
    P.ax, P.ay = cx, cy
    return crop(P)


def sp_planet(r, base, light, dark, spot, out, seed=1, spots=3):
    R = random.Random(seed)
    P = Pic(2 * r + 6, 2 * r + 6)
    c = r + 3
    sp = [(R.uniform(-r * 0.6, r * 0.5), R.uniform(-r * 0.6, r * 0.6), R.uniform(0.6, r * 0.28)) for _ in range(spots)]

    def f(dx, dy, x, y):
        lit = sphere_light(dx, dy, r)
        col = base
        for sx, sy, sr in sp:
            if (dx - sx) ** 2 + (dy - sy) ** 2 <= (sr + 0.3) ** 2:
                col = spot
        if lit > 0.8 and on(x, y, (lit - 0.8) * 5):
            col = light
        if lit < 0.22 and on(x, y, (0.22 - lit) * 3 + 0.25):
            col = dark
        return col

    P.ell(c, c, r, r, base, f)
    P.outline(out)
    P.ax = P.ay = c
    return crop(P)


def sp_earth(r, out):
    SEA, SEA2, LAND, LAND2, CLOUD = C("5a8ee4"), C("3e6cc0"), C("6cbc64"), C("4c9a50"), C("f4f6fa")
    P = Pic(2 * r + 6, 2 * r + 6)
    c = r + 3

    def f(dx, dy, x, y):
        land = math.sin(dx * 0.8 + 1.2) * math.cos(dy * 0.9 - 0.4) + 0.4 * math.sin(dx * 1.9 - dy * 1.3) > 0.3
        nx, ny = dx / (r + 0.4), dy / (r + 0.4)
        dark = (nx * 0.6 + ny * 0.6) > 0.42
        col = (LAND2 if dark else LAND) if land else (SEA2 if dark else SEA)
        if not land and abs(dy - dx * 0.3 + 2) < 0.6:
            col = CLOUD
        return col

    P.ell(c, c, r, r, SEA, f)
    P.outline(out)
    P.ax = P.ay = c
    return crop(P)


def sp_crescent(r, out, face=True):
    MOON, MOON2, BLUSH = C("f8d260"), C("e6aa46"), C("f09cae")
    n = 2 * r + 8
    P = Pic(n, n)
    c = n // 2
    for y in range(n):
        for x in range(n):
            dx, dy = x - c, y - c
            inm = dx * dx + dy * dy <= (r + 0.4) ** 2
            cut = (dx - 0.48 * r) ** 2 + (dy + 0.28 * r) ** 2 <= (0.84 * r + 0.4) ** 2
            if inm and not cut:
                col = MOON
                if math.hypot(dx, dy) > r - 1.6 and dx < 0 and on(x, y, 0.5):
                    col = MOON2
                P.px(x, y, col)
    if face:
        ex, ey = c - rd(0.55 * r), c - rd(0.02 * r)
        for dx, dy in ((-2, 0), (-1, 1), (0, 1), (1, 0)):          # 감은 눈 ∪
            P.px(ex + dx, ey + dy, out)
        mx, my = c - rd(0.42 * r), c + rd(0.42 * r)
        for dx, dy in ((-1, 0), (0, 1), (1, 1), (2, 0)):           # 입 ‿
            P.px(mx + dx, my + dy, out)
        P.px(ex - 3, ey + 3, BLUSH)
        P.px(ex - 2, ey + 3, BLUSH)
    P.outline(out)
    P.ax = P.ay = c
    return crop(P)


def sp_satellite(out):
    PAN, PAN2, BODY, BODY2, GRAY, DISH, RED = C("5a7cd8"), C("38589e"), C("e8b44a"), C("c08834"), C("9a9cb8"), C("e2e4f0"), C("e04c4c")
    P = Pic(36, 20)
    cx, cy = 18, 12
    P.hline(cx - 12, cx + 12, cy, GRAY)
    for x0 in (cx - 15, cx + 7):
        for y in range(cy - 2, cy + 3):
            for x in range(x0, x0 + 9):
                col = PAN2 if ((x - x0) % 3 == 2 or y == cy) else PAN
                P.px(x, y, col)
    for y in range(cy - 3, cy + 4):
        for x in range(cx - 3, cx + 4):
            col = BODY
            if (y - cy) % 3 == 2 or (x == cx + 3 and on(x, y, 0.5)):
                col = BODY2
            P.px(x, y, col)
    P.vline(cx, cy - 5, cy - 4, GRAY)
    P.hline(cx - 3, cx + 3, cy - 6, DISH)
    P.hline(cx - 2, cx + 2, cy - 5, DISH)
    P.vline(cx, cy - 8, cy - 7, GRAY)
    P.px(cx, cy - 9, RED)
    P.outline(out)
    return center(crop(P))


def theme_space():
    K = SP
    OUT = K["OUT"]
    S = Pic(W, H, True)
    R = random.Random(7)

    # 달 표면 높이 (주기 물결 + 가장자리가 솟은 큰 구덩이 + 바위 혹)
    big = [(150, 28), (452, 36)]
    rocks = [(R.randrange(W), R.uniform(1.0, 2.4)) for _ in range(16)]

    def hgt(x):
        h = 10 + wave(x, [(2, 2.4, 0.6), (5, 1.4, 2.1), (13, 0.7, 0.4)])
        for cx, w in big:
            d = abs(wd(x, cx)) / (w / 2)
            h += 2.8 * math.exp(-((d - 1.0) / 0.25) ** 2)
            if d < 1:
                h -= 3.2 * (1 - d * d)
        for cx, a in rocks:
            d = abs(wd(x, cx))
            h += a * max(0.0, 1 - (d / 2.6) ** 2)
        return h

    surf = [GY - rd(hgt(x)) for x in range(W)]

    # 별 (가장 뒤)
    def star(x, y, k, col):
        S.px(x, y, col)
        if k >= 1:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                S.px(x + dx, y + dy, col)
        if k >= 2:
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                S.px(x + dx, y + dy, col)
            S.px(x, y, K["WARM"])

    def pick():
        q = R.random()
        return K["GOLD"] if q < 0.5 else K["BLUE"] if q < 0.85 else K["PINK"]

    for _ in range(64):
        x, y = R.randrange(W), R.randint(18, 106)
        if y < surf[x] - 6:
            q = R.random()
            star(x, y, 0 if q < 0.72 else 1 if q < 0.94 else 2, pick())
    for cx, cy, n in [(34, 72, 11), (300, 96, 9), (386, 34, 8), (606, 94, 10)]:
        for i in range(n):
            x, y = rd(cx + R.gauss(0, 7)), rd(cy + R.gauss(0, 5))
            if y < surf[x % W] - 5:
                star(x, y, 0 if i % 3 else 1, pick())
        star(cx, cy, 2, K["GOLD"])
    # 별자리 (국자 모양) 점선
    dip = [(224, 32), (233, 29), (242, 31), (250, 27), (252, 35), (264, 37), (266, 28)]
    for a, b in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 3)]:
        (x0, y0), (x1, y1) = dip[a], dip[b]
        n = max(abs(x1 - x0), abs(y1 - y0))
        for i in range(2, n - 1, 2):
            S.px(rd(x0 + (x1 - x0) * i / n), rd(y0 + (y1 - y0) * i / n), K["LAV"])
    for x, y in dip:
        star(x, y, 1, K["GOLD"])

    # 혜성 (꼬리 세 갈래가 점점 옅어짐)
    hx, hy = 68, 40
    for i in range(1, 38):
        t = i / 38
        for col, off in ((K["GOLD"], 0.0), (K["BLUE"], -2.2), (K["PINK"], 2.2)):
            x, y = hx - i, rd(hy - i * 0.42 + off * t)
            if on(x, y, (1 - t) * 0.95):
                S.px(x, y, col)
    head = Pic(9, 9)
    head.ell(4, 4, 2, 2, K["WARM"])
    head.px(3, 3, C("ffffff"))
    head.outline(OUT)
    S.place(center(head), hx, hy)

    # 행성들
    S.place(sp_ringed(15, 30, 6.5, 0.18, (C("eeaa62"), C("f8d290"), C("c47a4c"), C("d88a54")),
                      (C("b4a0e6"), C("9686d2"), C("6e60ac")), OUT), 122, 56)
    S.place(sp_ringed(8, 16, 3.8, -0.30, (C("62c4c8"), C("a6e6e2"), C("3e8e9c"), C("4eaab4")),
                      (C("ee9cc6"), C("d478a8"), C("b05a8a")), OUT), 508, 66)
    S.place(sp_planet(5, C("de6a50"), C("f4a07e"), C("a84a40"), C("c25844"), OUT, seed=4), 398, 82)
    S.place(sp_earth(7, OUT), 622, 34)
    S.place(sp_crescent(12, OUT), 336, 44)
    S.place(sp_satellite(OUT), 446, 36)

    # 로켓 + 연기
    rk = sprite(ROCKET, K, OUT)
    rx, ry = 206, 76
    S.place(rk, rx, ry)
    for i, (dx, dy, r) in enumerate([(-1, 5, 1.6), (-3, 10, 2.2), (-6, 16, 2.8), (-10, 22, 3.2)]):
        puff = Pic(12, 12)
        puff.ell(5, 5, r, r * 0.85, C("dcdcea"), lambda ddx, ddy, x, y: C("f6f6fc") if ddy < -0.5 and ddx < 0.5 else C("dcdcea"))
        puff.outline(OUT)
        S.place(center(crop(puff)), rx + dx, ry + dy)
    S.place(rk, rx, ry)

    # 우주인 (둥둥) + 줄
    S.place(sprite(ASTRO, K, OUT), 574, 78)

    # 달 표면
    G0, G1, G2, G3, G4 = K["G0"], K["G1"], K["G2"], K["G3"], K["G4"]

    def gfill(x, y, d):
        if d == 1:
            return G1
        if hsh(x, y, 11) == 0:
            return G3
        if d > 6 and on(x, y, 0.35):
            return G3
        return G2

    fill_profile(S, surf, GY, gfill, G0)
    # 구덩이 (윗테 진하게, 안쪽 위는 그늘, 아래 테두리는 밝게)
    for cx, rx_ in [(58, 7), (104, 4), (244, 9), (326, 3.5), (522, 7.5), (586, 4.5), (200, 3), (380, 5)]:
        top = min(surf[(cx + d) % W] for d in range(-int(rx_) - 1, int(rx_) + 2))
        ry_ = max(1.3, rx_ * 0.3)
        cy = min(top + ry_ + 3, GY - ry_ - 2)
        S.ell(cx, cy, rx_ + 1, ry_ + 0.6, G0, lambda dx, dy, x, y: G0 if dy < 0 else None)
        S.ell(cx, cy, rx_, ry_, G3, lambda dx, dy, x, y: G4 if dy < 0.3 else G3)
        S.hline(cx - rx_ * 0.75, cx + rx_ * 0.75, rd(cy + ry_ + 1), G1)
    # 착륙선 + 깃발
    ld = sprite(LANDER, K, OUT)
    lx = 296
    base = max(surf[(lx + d) % W] for d in range(-9, 10))
    S.place(ld, lx, base - 5)
    S.place(sprite(LANDER_LEGS, {"s": K["OUT"]}), lx, base)
    fl = Pic(13, 18)
    fl.art(FLAG, K, 3, 2)
    fl.outline(OUT)
    fl.vline(2, 1, 16, OUT)
    fl.ax, fl.ay = 2, 16
    fx = 322
    S.place(fl, fx, surf[fx] + 1)

    # ── 아이콘 ──
    I = icon_sky([C("1e2044"), C("2c2e62"), C("3a3a78")])
    R2 = random.Random(3)
    for _ in range(26):
        x, y = R2.randrange(2, 46), R2.randrange(2, 36)
        I.px(x, y, C("f6d878") if R2.random() < 0.6 else C("aab6ff"))
    for x, y in ((8, 30), (40, 8)):
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            I.px(x + dx, y + dy, C("fff0b8"))
    I.place(sp_ringed(7, 14, 3.4, 0.2, (C("eeaa62"), C("f8d290"), C("c47a4c"), C("d88a54")),
                      (C("b4a0e6"), C("9686d2"), C("6e60ac")), OUT), 16, 15)
    I.place(sp_crescent(5, OUT, face=False), 39, 13)
    icon_ground(I, 39, G0, G2, lambda x, y: G1 if y == 40 else (G3 if hsh(x, y, 7) == 0 else G2))
    for x in range(48):
        bump = rd(1.2 * math.sin(x * 0.35) + 0.8 * math.sin(x * 0.9 + 1))
        for y in range(39 - max(0, bump), 39):
            I.px(x, y, G2)
        if bump > 0:
            I.px(x, 39 - bump, G0)
    I.ell(14, 43, 4, 1.2, G4, lambda dx, dy, x, y: G4 if dy < 0 else G3)
    I.place(sprite(ASTRO, K, OUT), 31, 36)
    icon_frame(I, OUT, C("7c78b8"), C("26244a"))
    return S, I


# ═══════════════════════════════ 2. 공룡시대 ═══════════════════════════════
DN = dict(
    OUT=C("3c3226"),
    MT=C("c4ccd8"), MT_E=C("98a4b8"),
    HL=C("acd09a"), HL2=C("98c088"), HL_E=C("6e9a68"),
    RK=C("9a7a6c"), RK_L=C("b8968a"), RK_D=C("7a5e56"), CR=C("5a4440"),
    LV=C("f06a30"), LV2=C("fac046"),
    SM=C("c4c0c8"), SM_L=C("e2dee4"), SM_D=C("a29ea8"),
    TR=C("a4744a"), TR2=C("80583a"), FR=C("4c9c54"), FR2=C("347a44"), FR3=C("78c068"),
    BR=C("78b498"), BR2=C("5a9680"), BR3=C("a2d0b0"), BR4=C("4c8270"),
    TX=C("d48a50"), TX2=C("a86a40"), TX3=C("f0c48c"), MOUTH=C("963c48"), TOOTH=C("fbf6e8"),
    PT=C("b07ca4"), PT2=C("8a5c84"), PT3=C("d4a8c4"),
    GR=C("ccaa7a"), GR2=C("b89462"), GR3=C("a4804e"), GR_E=C("7e6040"),
    ST=C("a8a4a0"), ST2=C("8a8682"), ST3=C("cac6c0"),
    EGG=C("f4ead0"), EGG2=C("94bc7c"), NEST=C("9a6c40"), NEST2=C("74502e"),
)


def dn_volcano(base_half, h, crater_half, K, out, lava=True, seed=2):
    R = random.Random(seed)
    w = base_half * 2 + 8
    P = Pic(w, h + 6)
    cx, gy = w // 2, h + 4
    top = gy - h
    for y in range(top, gy + 1):
        t = (y - top) / h
        half = crater_half + (base_half - crater_half) * (t ** 1.7)
        for x in range(rd(cx - half), rd(cx + half) + 1):
            u = (x - cx) / max(half, 1)
            col = K["RK"]
            if u < -0.25 and on(x, y, min(1, (-0.25 - u) * 2.2)):
                col = K["RK_L"]
            if u > 0.30 and on(x, y, min(1, (u - 0.30) * 2.4)):
                col = K["RK_D"]
            if hsh(x, y, 23) == 0:
                col = K["RK_D"]
            P.px(x, y, col)
    # 분화구: 윗변 가운데를 파고 안쪽에 불빛
    for x in range(cx - crater_half + 2, cx + crater_half - 1):
        P.px(x, top, None)
        P.p[x, top] = CLEAR
    for x in range(cx - crater_half + 3, cx + crater_half - 2):
        P.px(x, top + 1, K["CR"])
    for x in range(cx - crater_half + 5, cx + crater_half - 4):
        P.px(x, top + 1, K["LV"])
    P.px(cx, top + 1, K["LV2"])
    P.px(cx - 1, top + 1, K["LV2"])
    if lava:
        for sx, ln, drift, ph in [(-crater_half + 4, h * 0.55, -0.35, 0.0), (1, h * 0.75, 0.15, 1.7), (crater_half - 4, h * 0.42, 0.45, 3.1)]:
            x = cx + sx
            for i in range(int(ln)):
                y = top + 2 + i
                x += drift * 0.5 + 0.45 * math.sin(i * 0.33 + ph)
                wdt = 2 if i < ln * 0.55 else 1
                for k in range(wdt):
                    P.px(rd(x) + k, y, K["LV2"] if (i < ln * 0.3 and k == 0) else K["LV"])
    P.outline(out)
    P.ax, P.ay = cx, gy
    return crop(P)


def dn_smoke(puffs, K, out):
    P = Pic(80, 70)
    ox, oy = 20, 64
    for dx, dy, r in puffs:
        P.ell(ox + dx, oy + dy, r, r * 0.9, K["SM"],
              lambda ddx, ddy, x, y, r=r: K["SM_L"] if (ddx + ddy) < -r * 0.5 else (K["SM_D"] if ddy > r * 0.45 and on(x, y, 0.6) else K["SM"]))
    P.outline(out)
    P.ax, P.ay = ox, oy
    return crop(P)


def palm(h, lean, flen, K, out, nf=7, coconuts=False, seed=0, droop=0.55):
    R = random.Random(seed)
    m = flen + abs(lean) + 6
    P = Pic(2 * m + 10, h + flen + 12)
    bx, gy = P.w // 2, P.h - 3
    top = (bx + lean, gy - h)
    pts = [(bx, gy), (bx + lean * 0.12, gy - h * 0.55), top]

    def tf(dx, dy, x, y):
        if dx > 0.4:
            return K["TR2"]
        return K["TR2"] if y % 3 == 0 else K["TR"]

    P.curve(pts, 1.6, 1.0, K["TR"], tf)
    angs = [172, 146, 118, 88, 58, 30, 4][:nf] if nf >= 7 else [160, 120, 60, 20, 95][:nf]
    fronds = [(a, 1.0) for a in angs] + ([(132, 0.6), (64, 0.6)] if nf >= 7 else [])
    for a, lk in fronds:
        a += R.uniform(-7, 7)
        L = flen * R.uniform(0.88, 1.05) * lk
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        steps = int(L * 2)
        last = None
        for i in range(steps + 1):
            t = i / steps
            x = top[0] + ca * L * t
            y = top[1] - sa * L * t + droop * L * t * t
            r = 1.2 * (1 - t) + 0.4
            P.ell(x, y, r, r, K["FR"])
            q = (rd(x), rd(y))
            if q == last:
                continue
            last = q
            if 0.12 < t < 0.95 and q[0] % 2 == 0:                     # 늘어진 잎줄 (깃털처럼)
                lf = 3 if t < 0.55 else 2
                for k in range(1, lf + 1):
                    P.px(q[0] - (1 if ca > 0 else -1) * (k // 2), q[1] + rd(r) + k, K["FR2"] if k == lf else K["FR"])
            if t < 0.7 and q[0] % 3 == 1:
                P.px(q[0], q[1] - 1, K["FR3"])
    if coconuts:
        for dx, dy in ((-1, 2), (1, 2), (0, 3)):
            P.ell(top[0] + dx, top[1] + dy, 1, 1, K.get("CO", K["TR2"]))
    P.ell(top[0], top[1], 1.5, 1.2, K["FR2"])
    P.outline(out)
    P.ax, P.ay = bx, gy
    return crop(P)


def fern(size, K, out, seed=0):
    R = random.Random(seed)
    P = Pic(size * 3 + 10, size * 2 + 8)
    bx, gy = P.w // 2, P.h - 3
    n = 5 + size // 6
    for i in range(n):
        a = math.radians(25 + 130 * i / (n - 1) + R.uniform(-6, 6))
        L = size * R.uniform(0.75, 1.0) * (1.0 if 0.25 < i / (n - 1) < 0.75 else 0.8)
        ca, sa = math.cos(a), math.sin(a)
        steps = int(L * 2.2)
        for j in range(steps + 1):
            t = j / steps
            x = bx + ca * L * t
            y = gy - sa * L * t + 0.5 * L * t * t * (1.2 - sa)
            P.px(rd(x), rd(y), K["FR"])
            if 0.15 < t < 0.92 and j % 2 == 0:
                lf = 2 if t < 0.6 else 1
                for k in range(1, lf + 1):
                    P.px(rd(x - sa * k), rd(y - ca * k * 0.6 - k * 0.5), K["FR3"] if k == lf else K["FR"])
                    P.px(rd(x + sa * k), rd(y + ca * k * 0.6 - k * 0.3), K["FR2"])
    P.outline(out)
    P.ax, P.ay = bx, gy
    return crop(P)


def dn_brachio(s, K, out):
    P = Pic(int(90 * s) + 12, int(90 * s) + 12)
    gy = P.h - 3
    bx = int(P.w * 0.56)
    by = gy - 22 * s
    B, B2, B3, B4 = K["BR"], K["BR2"], K["BR3"], K["BR4"]

    def bf(dx, dy, x, y):
        if y > by + 4 * s and on(x, y, min(1.0, (y - (by + 4 * s)) / (6 * s))):
            return B2
        if hsh(x, y, 17) == 0 and y < by + 2 * s:
            return B4
        return B

    for lx in (bx - 15 * s, bx + 8 * s):                       # 먼 다리
        P.rect(lx, by, lx + 3.5 * s, gy, B2)
    P.curve([(bx + 14 * s, by - 2 * s), (bx + 30 * s, by + 1 * s), (bx + 46 * s, by + 13 * s)], 6 * s, 0.6, B, bf)
    P.ell(bx - 6 * s, by - 3 * s, 15 * s, 11 * s, B, bf)
    P.ell(bx + 8 * s, by + 1 * s, 13 * s, 9 * s, B, bf)
    P.curve([(bx - 13 * s, by - 6 * s), (bx - 21 * s, by - 30 * s), (bx - 24 * s, by - 50 * s)], 6 * s, 3 * s, B, bf)
    hx, hy = bx - 28 * s, by - 52 * s
    P.ell(hx, hy, 5 * s, 3.2 * s, B)
    P.ell(hx + 2 * s, hy - 2 * s, 3 * s, 2.6 * s, B)
    for lx in (bx - 11 * s, bx + 12 * s):                       # 가까운 다리
        P.rect(lx, by + 2 * s, lx + 4.5 * s, gy, B)
        P.vline(lx + 4.5 * s, by + 6 * s, gy, B2)
        P.hline(lx, lx + 4.5 * s, gy, B3)
    # 등 무늬 · 배 밝은 선
    for k in range(5):
        P.ell(bx - 10 * s + k * 6 * s, by - 9 * s + abs(k - 1.5) * 0.8 * s, 1.4 * s, 1.0 * s, B4)
    P.px(hx - 2 * s, hy - 1 * s, out)
    P.px(hx - 5 * s, hy + 1 * s, B2)
    P.outline(out)
    P.ax, P.ay = bx, gy
    return crop(P)


def dn_trex(s, K, out, flip=True):
    P = Pic(int(80 * s) + 10, int(56 * s) + 10)
    gy = P.h - 3
    hx, hy = int(P.w * 0.55), gy - 21 * s
    B, B2, BL = K["TX"], K["TX2"], K["TX3"]

    def bf(dx, dy, x, y):
        if dy > 2.5 * s and on(x, y, 0.75):
            return BL
        return B

    # 먼 다리 (뒤로 내디딤)
    P.ell(hx + 4 * s, hy + 2 * s, 4.5 * s, 6 * s, B2)
    P.curve([(hx + 6 * s, hy + 6 * s), (hx + 10 * s, hy + 12 * s), (hx + 9 * s, gy - 1)], 2.2 * s, 1.6 * s, B2)
    P.rect(hx + 7 * s, gy - 1, hx + 13 * s, gy, B2)
    # 꼬리 · 몸통
    P.curve([(hx + 4 * s, hy - 2 * s), (hx + 18 * s, hy - 4 * s), (hx + 33 * s, hy + 1 * s)], 7 * s, 0.7, B)
    P.curve([(hx + 2 * s, hy), (hx - 6 * s, hy - 5 * s), (hx - 10 * s, hy - 11 * s)], 8 * s, 6 * s, B, bf)
    # 머리 (입 벌림: 입속을 먼저 칠하고 아래턱을 얹는다)
    P.ell(hx - 17 * s, hy - 17 * s, 8 * s, 5.5 * s, B)
    P.rect(hx - 27 * s, hy - 20 * s, hx - 17 * s, hy - 14 * s, B)
    P.poly([(hx - 11 * s, hy - 14 * s), (hx - 27 * s, hy - 14 * s), (hx - 27 * s, hy - 10 * s), (hx - 11 * s, hy - 11 * s)], K["MOUTH"])
    P.poly([(hx - 11 * s, hy - 11 * s), (hx - 27 * s, hy - 9.5 * s), (hx - 27 * s, hy - 7.5 * s), (hx - 11 * s, hy - 8 * s)], B)
    for x in range(rd(hx - 26 * s), rd(hx - 14 * s), 2):
        P.px(x, rd(hy - 13 * s), K["TOOTH"])
    for x in range(rd(hx - 26 * s), rd(hx - 16 * s), 3):
        P.px(x, rd(hy - 11 * s), K["TOOTH"])
    P.rect(hx - 16 * s, hy - 21 * s, hx - 15 * s, hy - 20 * s, out)          # 눈
    P.hline(hx - 17 * s, hx - 14 * s, rd(hy - 22 * s), K["TX2"])             # 눈썹뼈
    P.px(hx - 25 * s, hy - 19 * s, B2)                                       # 콧구멍
    # 등 줄무늬
    for k in range(5):
        x0, y0 = hx + 2 * s + k * 5 * s, hy - 7 * s + k * 0.6 * s
        P.line(x0, y0, x0 + 1.5 * s, y0 + 3 * s, B2)
    # 가까운 다리 (앞으로) · 팔
    P.ell(hx - 1 * s, hy + 3 * s, 5.5 * s, 7 * s, B)
    P.curve([(hx - 1 * s, hy + 8 * s), (hx - 2 * s, hy + 14 * s), (hx - 5 * s, gy - 1)], 2.5 * s, 1.8 * s, B)
    P.rect(hx - 10 * s, gy - 1, hx - 3 * s, gy, B)
    P.px(hx - 11 * s, gy, K["TOOTH"])
    P.line(hx - 13 * s, hy - 6 * s, hx - 16 * s, hy - 3 * s, B2, 2)
    P.px(hx - 17 * s, hy - 3 * s, B2)
    P.outline(out)
    P.ax, P.ay = hx, gy
    Q = crop(P)
    if flip:
        Q.im = Q.im.transpose(Image.FLIP_LEFT_RIGHT)
        Q.p = Q.im.load()
        Q.ax = Q.w - 1 - Q.ax
    return Q


def dn_ptero(K, out, s=1.0, up=True):
    P = Pic(int(46 * s) + 8, int(34 * s) + 8)
    cx, cy = P.w * 0.42, P.h * 0.55
    B, B2, B3 = K["PT"], K["PT2"], K["PT3"]
    t = -1 if up else 1                                   # 날개: 위로 젖힘 / 아래로 내림
    # 먼 날개 (진하게)
    P.poly([(cx - 1 * s, cy - 0.5 * s), (cx - 6 * s, cy + t * 9 * s), (cx - 15 * s, cy + t * 13 * s),
            (cx - 10 * s, cy + t * 5 * s), (cx - 5 * s, cy + 1.2 * s)], B2)
    # 몸통 · 다리
    P.ell(cx, cy, 5 * s, 1.8 * s, B)
    P.line(cx - 5 * s, cy + 1 * s, cx - 8 * s, cy + 2 * s, B2)
    # 가까운 날개
    P.poly([(cx + 2 * s, cy - 0.5 * s), (cx - 1 * s, cy + t * 10 * s), (cx - 9 * s, cy + t * 15 * s),
            (cx - 5 * s, cy + t * 5 * s), (cx - 1 * s, cy + 1.4 * s)], B)
    # 목 · 머리 · 긴 부리 · 뒤로 뻗은 볏
    P.line(cx + 4 * s, cy - 1 * s, cx + 6 * s, cy - 2 * s, B, max(1, rd(2 * s)))
    P.ell(cx + 7.5 * s, cy - 2.5 * s, 2.4 * s, 1.8 * s, B)
    P.poly([(cx + 9 * s, cy - 3.2 * s), (cx + 18 * s, cy - 1.6 * s), (cx + 9 * s, cy - 1.2 * s)], B3)
    P.poly([(cx + 6.5 * s, cy - 3.5 * s), (cx + 0.5 * s, cy - 7.5 * s), (cx + 7.5 * s, cy - 4.5 * s)], B2)
    P.px(cx + 8 * s, cy - 3 * s, out)
    P.outline(out)
    return center(crop(P))


def dn_nest(K, out):
    P = Pic(22, 12)
    P.ell(11, 8, 8, 2.4, K["NEST"], lambda dx, dy, x, y: K["NEST2"] if (x + 2 * y) % 3 == 0 else K["NEST"])
    for ex, ey in ((7, 5), (15, 5)):
        P.ell(ex, ey, 1.6, 2.2, K["EGG"])
        P.px(ex, ey - 1, K["EGG2"])
        P.px(ex + 1, ey + 1, K["EGG2"])
    # 가운데 알은 깨지고 아기 공룡이 빼꼼
    P.ell(11, 2, 1.6, 1.6, K["BR"])
    P.px(13, 2, K["BR"])
    P.px(14, 2, K["BR"])
    P.px(12, 1, K["OUT"])
    P.ell(11, 6, 1.8, 1.5, K["EGG"])
    for x in (9, 11, 13):
        P.px(x, 4, K["EGG"])
    P.ell(11, 9, 8, 1.4, K["NEST"], lambda dx, dy, x, y: K["NEST2"] if (x + y) % 2 == 0 else K["NEST"])
    P.outline(out)
    P.ax, P.ay = 11, 10
    return crop(P)


def dn_rock(rx, ry, K, out):
    P = Pic(2 * rx + 6, 2 * ry + 6)
    c = rx + 3
    P.ell(c, ry + 3, rx, ry, K["ST"], lambda dx, dy, x, y: K["ST3"] if dx + dy < -ry * 0.6 else (K["ST2"] if dx + dy > ry * 0.5 else K["ST"]))
    P.outline(out)
    P.ax, P.ay = c, 2 * ry + 3
    return crop(P)


def theme_dino():
    K = DN
    OUT = K["OUT"]
    S = Pic(W, H, True)
    R = random.Random(3)
    tops = [GY - rd(36 + wave(x, [(3, 8, 0.2), (7, 4, 1.7), (16, 1.6, 0.5)])) for x in range(W)]
    fill_profile(S, tops, GY, lambda x, y, d: K["MT"], K["MT_E"])
    vx = 456
    S.place(dn_smoke([(0, -4, 2.5), (2, -9, 3.5), (5, -15, 4.2), (9, -22, 5), (15, -29, 5.5), (22, -35, 5), (30, -40, 4.2), (37, -43, 3)], K, OUT), vx + 1, GY - 67)
    S.place(dn_volcano(80, 64, 11, K, OUT), vx, GY - 2)
    tops2 = [GY - rd(22 + wave(x, [(4, 5, 1.0), (9, 2.6, 0.3), (21, 1.0, 2.0)])) for x in range(W)]
    fill_profile(S, tops2, GY, lambda x, y, d: K["HL2"] if on(x, y, min(1, d / 26)) else K["HL"], K["HL_E"])

    gh = [rd(7 + wave(x, [(3, 1.4, 0.4), (8, 0.9, 2.2), (19, 0.5, 1.0)])) for x in range(W)]
    gs = [GY - h for h in gh]

    def gfill(x, y, d):
        if d == 1:
            return K["GR"]
        band = (y + rd(wave(x, [(6, 1.2, 0.0), (15, 0.6, 1.0)]))) % 4
        if band == 0:
            return K["GR2"]
        if d > 4 and on(x, y, 0.3):
            return K["GR3"]
        return K["GR"]

    # 뒤쪽 야자 · 고사리
    for x, h, lean, fl in [(36, 44, 5, 15), (238, 36, -4, 13), (566, 46, -6, 15), (614, 30, 3, 11)]:
        S.place(palm(h, lean, fl, K, OUT, seed=x), x, gs[x] + 1)
    S.place(dn_ptero(K, OUT, 1.0, True), 262, 40)
    S.place(dn_ptero(K, OUT, 0.62, True), 556, 34)
    S.place(dn_ptero(K, OUT, 0.5, False), 590, 26)
    S.place(dn_brachio(0.86, K, OUT), 140, gs[140] + 1)
    S.place(dn_trex(1.0, K, OUT, flip=False), 334, gs[334] + 1)
    fill_profile(S, gs, GY, gfill, K["GR_E"])
    for x, sz in [(84, 12), (196, 10), (276, 9), (372, 13), (398, 8), (544, 11), (600, 9), (12, 8)]:
        S.place(fern(sz, K, OUT, seed=x), x, gs[x] + 2)
    S.place(dn_nest(K, OUT), 214, gs[214] + 3)
    for x, rx_, ry_ in [(64, 4, 2), (120, 2, 1), (300, 3, 2), (420, 5, 3), (508, 3, 2), (590, 2, 1), (168, 3, 1)]:
        S.place(dn_rock(rx_, ry_, K, OUT), x, gs[x] + 4)
    for _ in range(40):
        x = R.randrange(W)
        y = R.randint(gs[x] + 3, GY - 1)
        S.px(x, y, K["ST2"])

    # ── 아이콘 ──
    I = icon_sky([C("fde8c8"), C("f8d2a4"), C("f2b88a")])
    I.place(dn_smoke([(0, -2, 1.2), (1, -5, 1.8), (3, -9, 2.2), (6, -13, 2.4), (10, -16, 2)], K, OUT), 30, 21)
    I.place(dn_volcano(20, 20, 5, K, OUT, lava=False, seed=5), 30, 41)
    I.place(dn_ptero(K, OUT, 0.42, True), 12, 10)
    I.place(palm(18, -2, 8, K, OUT, nf=5, seed=9), 41, 42)
    icon_ground(I, 40, K["GR_E"], K["GR"], lambda x, y: K["GR2"] if (y + (x // 5)) % 3 == 0 else K["GR"])
    I.place(dn_brachio(0.36, K, OUT), 14, 43)
    icon_frame(I, OUT, C("fff4dc"), C("a07850"))
    return S, I


# ═══════════════════════════════ 3. 조선시대 ═══════════════════════════════
JS = dict(
    OUT=C("34343e"),
    M1=C("cad2ce"), M1B=C("b8c4c0"), M1E=C("98a6a4"), M2=C("a2b2ae"), M2B=C("8fa09c"), M2E=C("6a7c7c"), M3=C("7e9290"),
    T1=C("5c6478"), T2=C("4a5064"), T3=C("383c4c"), TEND=C("8c94a8"), DAN=C("4e9a84"), DAN2=C("e05a48"),
    ST=C("cac4b4"), ST2=C("a49e90"), ST3=C("e0dccf"), DOOR=C("4a4048"),
    RED=C("b8443a"), RED2=C("8e3430"),
    WALL=C("f2ecdc"), WOOD=C("8e6440"), WOOD2=C("6e4a2e"), PAPER=C("e8d8b0"),
    MUD=C("d4b488"), STRAW=C("dcb460"), STRAW2=C("b48c40"), STRAW3=C("ecd090"),
    GOURD=C("f2f0d6"), VINE=C("5a9a4a"),
    TR=C("a85a3e"), TR2=C("7c4030"), N1=C("3e7a58"), N2=C("62a070"), N3=C("2c5a44"),
    KW=C("f6f0e0"), KR=C("e04c3c"), KB=C("4c7ccc"),
    k=C("2e2a30"), S=C("f2c8a0"), Y=C("f4c84c"), R=C("e04c3c"), B=C("5a86d0"), w=C("f4f0e4"),
    CW=C("f6f6f6"), CK=C("2e2e36"), CR=C("e0403c"), CL=C("8a8a94"),
    JAR=C("8a4e34"), JAR2=C("643826"), JAR3=C("b67c58"),
    GD=C("ccb08a"), GD2=C("b49670"), GD_E=C("8c7050"), GRASS=C("6aa05a"),
)

KITE = [                     # 방패연: 위에 붉은 꼭지(동그라미), 가운데 방구멍, 아래 파란 치마
    "WWWWWWWWWW",
    "WWWWRRWWWW",
    "WWWRRRRWWW",
    "WWWRRRRWWW",
    "WWWWRRWWWW",
    "WWWWWWWWWW",
    "WWWW..WWWW",
    "WWW....WWW",
    "WWWW..WWWW",
    "WWWWWWWWWW",
    "BBBBBBBBBB",
    "BBBBBBBBBB",
]

KID = [
    "..kk...",
    ".kkkk..",
    ".kSSS..",
    "..SS..S",
    ".YYYYS.",
    "YYRYY..",
    ".YYY...",
    ".BBBB..",
    ".BBBB..",
    ".B..B..",
    ".w..w..",
]

CRANE = [
    ".........kkk.....",
    "........kWWW.....",
    ".......WWWW......",
    "......WWWW.......",
    ".R...WWWWW.......",
    "Rkkk.WWWWWWkk....",
    "....kWWWWWWWkLLLL",
    ".......WWW.......",
]


def tiled_roof(P, cx, eave_y, half, ridge_half, height, K, lift=3, thick=2, under=True):
    ridge_y = eave_y - height
    for dx in range(-half, half + 1):
        a = abs(dx)
        t = 0.0 if a <= ridge_half else (a - ridge_half) / max(1, half - ridge_half)
        up = lift * t ** 2.6
        top = rd(ridge_y + (eave_y - ridge_y) * (1 - (1 - t) ** 2) - up)
        bot = rd(eave_y + thick - up)
        for y in range(top, bot + 1):
            col = K["T2"] if (dx % 2 == 0 and y > top) else K["T1"]
            if y == bot:
                col = K["TEND"] if dx % 2 else K["T3"]
            P.px(cx + dx, y, col)
        if under and a <= half - 3:
            P.px(cx + dx, bot + 1, K["DAN"] if dx % 3 else K["DAN2"])
    for dx in range(-ridge_half - 1, ridge_half + 2):
        e = 1 if abs(dx) >= ridge_half else 0
        P.px(cx + dx, ridge_y - 1 - e, K["T3"])
        P.px(cx + dx, ridge_y - e, K["T3"])


def js_gate(K, out):
    P = Pic(120, 74)
    cx, gy = 60, 71
    bt = gy - 19
    for y in range(bt, gy + 1):
        half = 29 + (y - bt) * 2 / 19
        row = (y - bt) // 4
        for x in range(rd(cx - half), rd(cx + half) + 1):
            col = K["ST"]
            if (y - bt) % 4 == 3 or (x + row * 3) % 7 == 0:
                col = K["ST2"]
            P.px(x, y, col)
    ar, acy = 6.5, gy - 8
    for y in range(gy - 18, gy + 1):
        for x in range(cx - 10, cx + 11):
            dx, dy = x - cx, y - acy
            r2 = dx * dx + min(dy, 0) ** 2
            if r2 <= (ar + 0.4) ** 2:
                P.px(x, y, K["RED2"] if abs(dx) >= 5 else K["DOOR"])
            elif r2 <= (ar + 2.3) ** 2:
                P.px(x, y, K["ST3"] if (math.atan2(dy, dx) * 6) % 2 > 0.3 else K["ST2"])
    # 아래층
    def storey(y0, y1, half):
        P.rect(cx - half, y0, cx + half, y1, K["DOOR"])
        for x in range(cx - half, cx + half + 1, 6):
            P.vline(x, y0, y1, K["RED"])
        P.vline(cx + half, y0, y1, K["RED"])
        P.hline(cx - half, cx + half, y1, K["WOOD"])
        P.hline(cx - half, cx + half, y0, K["DAN"])
        for x in range(cx - half, cx + half + 1, 3):
            P.px(x, y0, K["DAN2"] if x % 2 else K["ST3"])
    storey(bt - 7, bt - 1, 23)
    tiled_roof(P, cx, bt - 9, 35, 21, 6, K, lift=3, thick=2)
    storey(bt - 21, bt - 15, 17)
    tiled_roof(P, cx, bt - 23, 30, 13, 10, K, lift=4, thick=3)
    P.outline(out)
    P.ax, P.ay = cx, gy
    return crop(P)


def js_hanok(wid, K, out):
    P = Pic(wid + 26, 46)
    cx, gy = P.w // 2, 43
    hw = wid // 2
    wt = gy - 11
    P.rect(cx - hw - 2, gy - 1, cx + hw + 2, gy, K["ST"])
    P.hline(cx - hw - 2, cx + hw + 2, gy - 1, K["ST2"])
    P.rect(cx - hw, wt, cx + hw, gy - 2, K["WALL"])
    n = max(2, round(wid / 7))
    posts = [rd(cx - hw + i * wid / n) for i in range(n + 1)]
    for i, x in enumerate(posts):
        P.vline(x, wt, gy - 2, K["WOOD"])
        if i < n:
            x2 = posts[i + 1]
            door = (i == n // 2)
            y0, y1 = (wt + 2, gy - 3) if door else (wt + 2, wt + 6)
            if x2 - x >= 4:
                P.rect(x + 1, y0, x2 - 1, y1, K["PAPER"])
                for gx in range(x + 2, x2 - 1, 2):
                    P.vline(gx, y0, y1, K["WOOD2"])
                P.hline(x + 1, x2 - 1, (y0 + y1) // 2, K["WOOD2"])
    P.hline(cx - hw, cx + hw, wt, K["WOOD2"])
    P.hline(cx - hw, cx + hw, gy - 2, K["WOOD"])
    tiled_roof(P, cx, wt - 3, hw + 7, max(3, hw - 5), 6 + wid // 14, K, lift=3, thick=2)
    P.outline(out)
    P.ax, P.ay = cx, gy
    return crop(P)


def js_choga(wid, K, out):
    P = Pic(wid + 18, 40)
    cx, gy = P.w // 2, 37
    hw = wid // 2
    wt = gy - 10
    P.rect(cx - hw, wt, cx + hw, gy - 1, K["MUD"])
    P.hline(cx - hw - 1, cx + hw + 1, gy, K["ST2"])
    for x in (cx - hw, cx + hw, cx + 2):
        P.vline(x, wt, gy - 1, K["WOOD"])
    P.rect(cx - hw + 3, wt + 3, cx - hw + 6, gy - 1, K["WOOD2"])
    P.rect(cx + 5, wt + 3, cx + 8, wt + 6, K["PAPER"])
    P.vline(cx + 6, wt + 3, wt + 6, K["WOOD"])
    half = hw + 4
    for dx in range(-half, half + 1):
        t = dx / (half + 0.5)
        top = rd(wt - 1 - 9 * (max(0.0, 1 - t * t) ** 0.6))
        bot = wt + 1 + (1 if (dx * 7) % 3 == 0 else 0)
        for y in range(top, bot + 1):
            col = K["STRAW"]
            if (dx + y) % 5 == 0 or (dx - y) % 5 == 0:
                col = K["STRAW2"]
            elif y < top + 2 and on(cx + dx, y, 0.5):
                col = K["STRAW3"]
            if y == bot:
                col = K["STRAW2"]
            P.px(cx + dx, y, col)
    # 지붕 위 박 넝쿨 + 하얀 박 두 덩이
    for dx in range(-hw + 1, hw - 2):
        t = dx / (half + 0.5)
        P.px(cx + dx, rd(wt - 1 - 9 * (max(0.0, 1 - t * t) ** 0.6)) + 2 + (1 if dx % 4 < 2 else 0), K["VINE"])
    P.outline(out)
    for gx, gyy, r in ((cx - 5, wt - 9, 2.6), (cx + 4, wt - 8, 2.2)):
        P.ell(gx, gyy, r + 1, r * 0.8 + 1, out)
        P.ell(gx, gyy, r, r * 0.8, K["GOURD"], lambda dx, dy, x, y: C("d8d4b4") if dx + dy > 0.8 else K["GOURD"])
        P.px(gx - 1, gyy - 1, C("ffffff"))
        P.px(gx, gyy - rd(r * 0.8) - 1, K["VINE"])
    P.ax, P.ay = cx, gy
    return crop(P)


def pine(h, lean, K, out, seed=0):
    R = random.Random(seed)
    P = Pic(70, h + 14)
    bx, gy = 35, h + 10
    top = (bx + lean, gy - h)
    mid = (bx - lean * 0.7, gy - h * 0.5)
    pts = [(bx, gy), mid, top]
    P.curve(pts, 1.8, 1.0, K["TR"], lambda dx, dy, x, y: K["TR2"] if dx > 0.3 or y % 4 == 0 else K["TR"])
    pads = []
    for k, tt in enumerate((0.5, 0.64, 0.78, 0.9)):
        p = bez(pts, tt)
        side = -1 if k % 2 == 0 else 1
        L = (11 - k * 2) * (h / 46) + R.uniform(-1, 1)
        end = (p[0] + side * L, p[1] - 2 - R.uniform(0, 2))
        P.line(p[0], p[1], end[0], end[1], K["TR2"])
        pads.append((end[0] - side * 1.5, end[1] - 1, L * 0.6 + 3.5, 2.2))
    pads.append((top[0], top[1] - 1, 6.5 * (h / 46) + 2, 2.6))

    def nf(dx, dy, x, y):
        if dy < -0.8 and on(x, y, 0.55):
            return K["N2"]
        if dy > 1.2:
            return K["N3"]
        return K["N1"]

    for x, y, rx, ry in pads:
        P.ell(x, y, rx, ry, K["N1"], nf)
        P.ell(x + rx * 0.35, y - ry * 0.7, rx * 0.55, ry * 0.7, K["N1"], nf)
    P.outline(out)
    P.ax, P.ay = bx, gy
    return crop(P)


def js_jar(rx, h, K, out):
    """장독 하나: 어깨가 넓은 몸통 + 입술 + 뚜껑 + 왼쪽 윤기"""
    P = Pic(2 * rx + 8, h + 10)
    cx, gy = P.w // 2, P.h - 3
    cy, ry = gy - h * 0.45, h * 0.47
    P.ell(cx, cy, rx, ry, K["JAR"],
          lambda dx, dy, x, y: K["JAR3"] if -rx * 0.62 < dx < -rx * 0.28 and -ry * 0.6 < dy < ry * 0.25
          else (K["JAR2"] if dx > rx * 0.42 or dy > ry * 0.6 else K["JAR"]))
    P.hline(cx - rx * 0.45, cx + rx * 0.45, gy, K["JAR2"])
    top = rd(cy - ry)
    P.hline(cx - rx * 0.5, cx + rx * 0.5, top - 1, K["JAR2"])
    P.hline(cx - rx * 0.62, cx + rx * 0.62, top - 2, K["JAR"])
    P.hline(cx - rx * 0.36, cx + rx * 0.36, top - 3, K["JAR"])
    P.px(cx, top - 4, K["JAR2"])
    P.px(cx - rd(rx * 0.3), top - 2, K["JAR3"])
    P.outline(out)
    P.ax, P.ay = cx, gy
    return crop(P)


def js_onggi(K, out):
    """장독대: 돌단 위 크고 작은 장독 셋"""
    P = Pic(36, 20)
    gy = 16
    P.rect(1, gy, 34, gy + 1, K["ST"])
    P.hline(1, 34, gy, K["ST3"])
    P.outline(out)
    for x, rx, h in ((7, 4, 8), (18, 5, 11), (29, 3, 7)):
        P.place(js_jar(rx, h, K, out), x, gy - 1)
    P.ax, P.ay = 18, gy + 1
    return crop(P)


def js_kite(K, out):
    pal = {"W": K["KW"], "R": K["KR"], "B": K["KB"]}
    P = Pic(16, 18)
    P.art(KITE, pal, 3, 3)
    P.outline(out)
    for i in range(10):                                  # 대나무 살 (대각선 하나)
        y = 3 + rd(i * 11 / 9)
        if P.get(3 + i, y) == pal["W"]:
            P.px(3 + i, y, C("cdb48c"))
    return crop(P)


def js_mountains(S, peaks, base_y, fill, fill2, edge, mist, tex=None, seed=0, jag=0.0):
    """수묵 산: 봉우리마다 어깨 봉우리를 붙이고, 오른쪽 비탈은 그늘, 능선 먹선, 아래는 안개로 흐려짐"""
    R = random.Random(seed)
    allp = []
    for i, (px_, ph, pw) in enumerate(peaks):
        allp.append((px_, ph, pw, True, i % 3 == 1))
        for side in (-1, 1):
            if R.random() < 0.85:
                allp.append((px_ + side * pw * R.uniform(0.32, 0.5), ph * R.uniform(0.5, 0.72), pw * R.uniform(0.38, 0.55), False, R.random() < 0.4))
    prof = []
    for x in range(W):
        h = 0.0
        for px_, ph, pw, _, round_top in allp:
            d = abs(wd(x, px_)) / pw
            if d < 1:
                # 뾰족 봉우리 / 둥근 봉우리 (수묵화의 바위산·흙산)
                h = max(h, ph * ((1 - d ** 1.8) ** 1.7 if round_top else (1 - d) ** 1.5))
        if h > 0.5:
            h += jag * wave(x, [(37, 1.0, 0.3), (61, 0.6, 1.1)])
        prof.append(h)
    tops = [base_y - rd(h) if h > 0.5 else 999 for h in prof]
    mb = [base_y + rd(2.5 * math.sin(2 * math.pi * 5 * x / W + seed) + 1.5 * math.sin(2 * math.pi * 13 * x / W + 2 * seed)) for x in range(W)]

    def vis(x, y):
        fade = (y - (mb[x] - mist)) / mist
        return not (fade > 0 and not on(x, y, 1 - fade))

    body = set()
    for x in range(W):
        t = tops[x]
        if t >= 999:
            continue
        slope = prof[(x + 1) % W] - prof[(x - 1) % W]
        nb = max(min(tops[(x - 1) % W], base_y), min(tops[(x + 1) % W], base_y)) - 1
        for y in range(t, base_y + 1):
            if not vis(x, y):
                continue
            if y <= max(t, nb):
                S.px(x, y, edge)
                continue
            c = fill
            if slope < -0.3 and on(x, y, min(1.0, -slope * 0.5)):
                c = fill2
            if tex and hsh(x, y // 3, 11) == 0 and y - t < 16:
                c = tex
            S.px(x, y, c)
            body.add((x, y))
    # 능선 먹선: 큰 봉우리 꼭대기에서 비탈 안쪽으로 한두 줄
    for px_, ph, pw, main, _ in allp:
        if not main:
            continue
        x0 = rd(px_) % W
        y0 = tops[x0] + 1
        for side in ((-1, 1) if ph > 55 else (R.choice((-1, 1)),)):
            pts = [(x0, y0), (x0 + side * pw * 0.12, y0 + ph * 0.25), (x0 + side * pw * 0.3, y0 + ph * 0.5)]
            L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
            n = int(L * 2)
            for i in range(n + 1):
                x, y = bez(pts, i / n)
                q = (rd(x) % W, rd(y))
                if q in body and (i // 3) % 4 != 3:
                    S.px(q[0], q[1], edge)
    return tops


def fort_wall(S, x0, x1, height, K):
    top = GY - height
    for x in range(x0, x1 + 1):
        for y in range(top, GY + 1):
            row = (y - top) // 3
            col = K["ST"]
            if (y - top) % 3 == 2 or (x + row * 4) % 8 == 0:
                col = K["ST2"]
            S.px(x, y, col)
        S.px(x, top, K["ST2"])
        k = (x - x0) % 8
        if k < 6:                                         # 여장 (총안 있는 낮은 담)
            for y in range(top - 4, top):
                S.px(x, y, K["ST"] if not (k == 3 and y == top - 2) else K["DOOR"])
            S.px(x, top - 5, K["T3"])
    for y in range(top - 5, GY + 1):
        S.px(x0 - 1, y, K["OUT"])
        S.px(x1 + 1, y, K["OUT"])
    for x in range(x0 - 1, x1 + 2):
        if S.get(x, top - 6)[3] == 0 and (x - x0) % 8 < 6:
            S.px(x, top - 6, K["OUT"])
        elif (x - x0) % 8 >= 6:
            S.px(x, top - 1, K["OUT"]) if S.get(x, top - 1)[3] == 0 else None


def tile_wall(S, x0, x1, gy, K):
    """기와 얹은 담장"""
    for x in range(x0, x1 + 1):
        for y in range(gy - 7, gy + 1):
            col = K["WALL"]
            if y >= gy - 2:
                col = K["ST2"] if (x + y) % 4 == 0 else K["ST"]
            elif (x - x0) % 10 in (4, 5) and gy - 6 <= y <= gy - 4:
                col = K["ST2"]
            S.px(x, y, col)
        S.px(x, gy - 8, K["T1"] if x % 2 else K["T2"])
        S.px(x, gy - 9, K["T3"])
    for x in (x0 - 1, x1 + 1):
        S.px(x, gy - 8, K["TEND"])
        S.px(x, gy - 9, K["T3"])
    for x in range(x0 - 1, x1 + 2):
        S.px(x, gy - 10, K["OUT"])
    for y in range(gy - 7, gy + 1):
        S.px(x0 - 1, y, K["OUT"])
        S.px(x1 + 1, y, K["OUT"])


def theme_joseon():
    K = JS
    OUT = K["OUT"]
    S = Pic(W, H, True)
    R = random.Random(11)
    far = [(28, 56, 40), (88, 72, 46), (150, 51, 38), (214, 65, 42), (288, 46, 36), (356, 68, 46),
           (420, 54, 40), (500, 76, 48), (566, 53, 36), (616, 63, 40)]
    js_mountains(S, far, 114, K["M1"], K["M1B"], K["M1E"], 20, tex=K["M1E"], seed=1, jag=0.8)
    near = [(60, 40, 34), (122, 30, 30), (250, 44, 38), (330, 34, 30), (462, 46, 40), (540, 32, 28), (600, 38, 32)]
    js_mountains(S, near, 120, K["M2"], K["M2B"], K["M2E"], 14, tex=K["M3"], seed=2, jag=0.6)
    # 학 두 마리
    cranepal = {"W": K["CW"], "k": K["CK"], "R": K["CR"], "L": K["CL"]}
    S.place(sprite(CRANE, cranepal, OUT), 178, 46)
    S.place(sprite(CRANE, cranepal, OUT), 204, 36)

    gh = [rd(5 + wave(x, [(3, 1.0, 0.5), (7, 0.6, 2.0)])) for x in range(W)]
    gs = [GY - h for h in gh]
    # 성곽 + 문
    fort_wall(S, 250, 410, 16, K)
    S.place(js_gate(K, OUT), 330, GY - 2)
    # 한옥 두 채 + 담장 + 장독대
    tile_wall(S, 76, 200, GY - 3, K)
    S.place(js_hanok(40, K, OUT), 116, GY - 3)
    S.place(js_hanok(26, K, OUT), 172, GY - 3)
    S.place(js_onggi(K, OUT), 214, GY - 3)
    # 초가집 + 싸리 울타리
    S.place(js_choga(30, K, OUT), 512, GY - 3)
    for x in range(532, 556):
        if x % 3 == 0:
            S.vline(x, GY - 9, GY - 3, K["WOOD"])
        S.px(x, GY - 7, K["WOOD2"])
        S.px(x, GY - 5, K["WOOD2"])
    # 소나무
    for x, h, lean in [(34, 50, 6), (232, 34, -4), (452, 42, 5), (604, 54, -7)]:
        S.place(pine(h, lean, K, OUT, seed=x), x, GY - 2)
    # 땅 (흙길)
    fill_profile(S, gs, GY, lambda x, y, d: K["GD2"] if (d > 2 and on(x, y, 0.25)) or hsh(x, y, 13) == 0 else K["GD"], K["GD_E"])
    for _ in range(26):
        x = R.randrange(W)
        S.px(x, gs[x] - 1, K["GRASS"])
        S.px(x + 1, gs[x] - 2, K["GRASS"])
        S.px(x + 2, gs[x] - 1, K["GRASS"])
    # 연 날리는 아이
    kid = sprite(KID, K, OUT)
    kx = 578
    S.place(kid, kx, GY - 1)
    hand = (kx + 3, GY - 1 - 7)
    kite = js_kite(K, OUT)
    kpos = (612, 36)
    S.path([hand, (hand[0] + 22, hand[1] - 22), (kpos[0], kpos[1] + 8)], C("8a7e72"))
    S.place(center(kite), kpos[0], kpos[1])

    # ── 아이콘 ──
    I = icon_sky([C("f6efde"), C("eee2c6")])
    for x in range(48):
        h = max(22 * max(0.0, 1 - abs(x - 14) / 16) ** 1.3, 16 * max(0.0, 1 - abs(x - 36) / 14) ** 1.3)
        for y in range(rd(36 - h), 37):
            if y == rd(36 - h):
                I.px(x, y, K["M1E"])
            elif on(x, y, 1 - max(0, (y - 26) / 10)):
                I.px(x, y, K["M1"])
    I.path([(47, 34), (43, 26), (38, 18)], C("8a7e72"))
    I.place(center(js_kite(K, OUT)), 37, 12)
    icon_ground(I, 41, K["GD_E"], K["GD"])
    I.place(pine(26, 3, K, OUT, seed=5), 7, 43)
    I.place(js_hanok(24, K, OUT), 29, 42)
    icon_frame(I, OUT, C("fffaf0"), C("9a8c70"))
    return S, I


# ═══════════════════════════════ 4. 할로윈 ═══════════════════════════════
HW = dict(
    OUT=C("2c2236"),
    MO=C("f6a03e"), MO2=C("e8842e"), MO3=C("fac470"), MOC=C("e48a34"),
    HILL=C("6e5a86"), HILL2=C("5e4c74"), HILL_E=C("3e3052"),
    HS=C("5a4874"), HS2=C("4a3a62"), RF=C("3e3054"), RF2=C("332846"), WIN=C("fad050"), WIN2=C("f29a3a"), TRIM=C("7c6a96"),
    TREE=C("4a3a52"),
    PU=C("f08a2c"), PU2=C("d06a22"), PU3=C("f8b060"), FACE=C("5c2a1c"), GLOW=C("fad850"), STEM=C("5e8a3c"),
    GV=C("a8a4b8"), GV2=C("86829a"), GV3=C("c8c4d4"),
    BAT=C("3a2c48"), EYE=C("f8c040"),
    GH=C("f6f6fc"), GH2=C("d2d2e6"), BLUSH=C("f0a0b8"),
    WEB=C("9a8eae"), FENCE=C("4a3e5a"),
    GD=C("7a6a8c"), GD2=C("6a5a7c"), GD_E=C("3e3052"), GRASS=C("5e7a5a"),
    OWL=C("9a7a62"), OWL2=C("6e5644"),
)

BAT_UP = [
    "k...........k",
    "kk..k...k..kk",
    ".kk.kkkkk.kk.",
    ".kkkkekekkkk.",
    "..kkkkkkkkk..",
    "....kkkkk....",
    ".....k.k.....",
]
BAT_DN = [
    "....k...k....",
    "....kkkkk....",
    "..kkkekekkk..",
    ".kkkkkkkkkkk.",
    "kk.kkk.kkk.kk",
    "k...k...k...k",
]
GHOST = [
    "...WWWWW...",
    "..WWWWWWW..",
    ".WWWWWWWWW.",
    ".WWkWWWkWW.",
    ".WWkWWWkWW.",
    "WWWWWWWWWWw",
    "WpWWWkWWWpw",
    "WWWWWWWWWww",
    "WWWWWWWWWww",
    "WWWWWWWWWww",
    "WWWWWWWWwww",
    "WW.WWW.WWw.",
    "W...W...w..",
]
WITCH = [
    "..kk..............",
    "...kkk............",
    "....kkk...........",
    ".....kkk..........",
    "....kkkkkk........",
    "..kkkkkkkkkk......",
    ".......kkgg.......",
    "......kkkkg.......",
    ".....kkkkkk.......",
    "....kkkkkkkk......",
    "OO..kkkkkkkk......",
    "OOObbbbbbbbbbbbbbb",
    "OO....kk..kk......",
    ".O.....k...k......",
]
OWL = [
    "o...o",
    "ooooo",
    "oYoYo",
    "ooboo",
    "oOOOo",
    "oOOOo",
    ".ooo.",
]


def hw_moon(r, K, out):
    P = Pic(2 * r + 6, 2 * r + 6)
    c = r + 3
    craters = [(-r * 0.35, -r * 0.2, r * 0.18), (r * 0.3, r * 0.25, r * 0.22), (r * 0.15, -r * 0.5, r * 0.12), (-r * 0.4, r * 0.45, r * 0.12)]

    def f(dx, dy, x, y):
        lit = sphere_light(dx, dy, r)
        col = K["MO"]
        for cx, cy, cr in craters:
            dd = (dx - cx) ** 2 + (dy - cy) ** 2
            if dd <= (cr + 0.3) ** 2:
                col = K["MOC"]
                if dd >= (cr - 0.9) ** 2 and (dx - cx) + (dy - cy) > 0:
                    col = K["MO3"]
        if lit > 0.82 and on(x, y, (lit - 0.82) * 5):
            col = K["MO3"]
        if lit < 0.2 and on(x, y, (0.2 - lit) * 3 + 0.3):
            col = K["MO2"]
        return col

    P.ell(c, c, r, r, K["MO"], f)
    P.outline(out)
    P.ax = P.ay = c
    return crop(P)


def hw_house(K, out):
    P = Pic(70, 64)
    cx, gy = 34, 61
    HS, HS2, RF, RF2, WIN, TRIM = K["HS"], K["HS2"], K["RF"], K["RF2"], K["WIN"], K["TRIM"]

    def wall(x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                P.px(x, y, HS2 if (x - x0) % 3 == 0 else HS)

    def roof(pts):
        P.poly(pts, RF, lambda x, y: RF2 if y % 2 == 0 and on(x, y, 0.5) else RF)

    def window(x, y, w, h, lit=True, boarded=False):
        P.rect(x - 1, y - 1, x + w, y + h, TRIM)
        P.rect(x, y, x + w - 1, y + h - 1, WIN if lit else K["OUT"])
        if lit:
            P.rect(x, y + h - 2, x + w - 1, y + h - 1, K["WIN2"])
            P.vline(x + w // 2, y, y + h - 1, TRIM)
            P.hline(x, x + w - 1, y + h // 2 - 1, TRIM)
        if boarded:
            P.line(x - 1, y, x + w, y + h - 1, C("8a6a4e"))
            P.line(x - 1, y + h - 2, x + w, y + 1, C("8a6a4e"))

    # 오른쪽 날개 (낮음)
    wall(cx + 9, gy - 13, cx + 21, gy)
    roof([(cx + 7, gy - 13), (cx + 15, gy - 21), (cx + 23, gy - 13)])
    window(cx + 13, gy - 10, 4, 4, lit=False, boarded=True)
    # 본채
    wall(cx - 13, gy - 22, cx + 9, gy)
    roof([(cx - 16, gy - 22), (cx - 1, gy - 37), (cx + 12, gy - 22)])
    P.rect(cx + 4, gy - 40, cx + 6, gy - 30, HS2)                    # 굴뚝 (살짝 기울게)
    P.rect(cx + 3, gy - 41, cx + 6, gy - 40, RF)
    window(cx - 3, gy - 30, 3, 3)                                       # 다락 둥근창
    window(cx - 10, gy - 18, 4, 5)
    window(cx + 3, gy - 18, 4, 5)
    P.rect(cx - 3, gy - 8, cx + 1, gy, K["OUT"])                        # 문
    P.hline(cx - 2, cx, gy - 9, K["OUT"])
    P.px(cx, gy - 4, K["WIN"])
    P.poly([(cx - 6, gy - 10), (cx - 1, gy - 13), (cx + 4, gy - 10)], RF)  # 현관 지붕
    # 왼쪽 탑
    wall(cx - 22, gy - 32, cx - 13, gy)
    roof([(cx - 25, gy - 32), (cx - 17.5, gy - 50), (cx - 10, gy - 32)])
    window(cx - 19, gy - 27, 3, 4)
    window(cx - 19, gy - 14, 3, 4, lit=False)
    P.vline(cx - 17, gy - 54, gy - 50, K["OUT"])                        # 풍향계
    P.hline(cx - 19, cx - 15, gy - 53, K["OUT"])
    P.outline(out)
    P.ax, P.ay = cx, gy
    return crop(P)


def hw_tree(h, K, seed=4):
    R = random.Random(seed)
    P = Pic(96, h + 10)
    bx, gy = 48, h + 7
    T = K["TREE"]
    tips = []

    def branch(x, y, ang, L, w, depth):
        ex, ey = x + math.cos(ang) * L, y - math.sin(ang) * L
        bend = R.uniform(-0.3, 0.3) * L
        mx = (x + ex) / 2 + math.cos(ang + math.pi / 2) * bend
        my = (y + ey) / 2 - math.sin(ang + math.pi / 2) * bend
        P.curve([(x, y), (mx, my), (ex, ey)], w, max(0.3, w * 0.55), T)
        if depth > 0:
            for da in (R.uniform(0.35, 0.75), -R.uniform(0.35, 0.75)):
                branch(ex, ey, ang + da, L * R.uniform(0.58, 0.72), w * 0.55, depth - 1)
        else:
            cdir = 1 if math.cos(ang) > 0 else -1
            P.px(rd(ex + cdir), rd(ey - 1), T)
            P.px(rd(ex + cdir * 2), rd(ey), T)
            tips.append((ex, ey))

    top = (bx + 4, gy - h * 0.42)
    if h > 40:
        hw_web(P, top[0] + 1, top[1] - 13, 10, K["WEB"])      # 가지 사이 거미줄 (가지보다 먼저 → 가지가 위로)
    w0 = max(1.6, h / 20)
    P.curve([(bx, gy), (bx - 5 * h / 66, gy - h * 0.2), top], w0, w0 * 0.75, T)
    for dx in (-4, -2, 3, 5):
        P.line(bx, gy - 2, bx + dx * h / 66, gy, T)
    branch(top[0], top[1], math.radians(112), h * 0.36, w0 * 0.68, 3 if h > 40 else 2)
    branch(top[0], top[1], math.radians(40), h * 0.32, w0 * 0.62, 3 if h > 40 else 2)
    side = bez([(bx, gy), (bx - 5 * h / 66, gy - h * 0.2), top], 0.7)
    if h > 40:
        branch(side[0], side[1], math.radians(172), h * 0.42, 1.6, 2)
    P.ax, P.ay = bx, gy
    P.side = side
    P.fork = top
    return P


def hw_perch(P, x, y0, y1):
    """가지 위 앉을 자리: x 열에서 y0~y1 사이 첫 불투명 칸"""
    for y in range(int(y0), int(y1)):
        if P.get(x, y)[3]:
            return y
    return int(y1)


def hw_web(P, cx, cy, r, col):
    angs = [math.radians(a + 20) for a in range(0, 360, 45)]
    for a in angs:
        P.line(cx, cy, cx + math.cos(a) * r, cy + math.sin(a) * r, col)
    for rr in (r * 0.42, r * 0.8):
        pts = [(cx + math.cos(a) * rr, cy + math.sin(a) * rr) for a in angs]
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            m = ((a[0] + b[0]) / 2 - (a[0] + b[0] - 2 * cx) * 0.08, (a[1] + b[1]) / 2 - (a[1] + b[1] - 2 * cy) * 0.08)
            P.path([a, m, b], col)


def hw_grave(kind, K, out):
    P = Pic(18, 20)
    cx, gy = 8, 17
    G, G2, G3 = K["GV"], K["GV2"], K["GV3"]
    if kind == 0:
        P.rect(cx - 4, gy - 8, cx + 4, gy, G)
        P.ell(cx, gy - 8, 4, 3, G)
        P.vline(cx + 4, gy - 8, gy, G2)
        P.hline(cx - 2, cx + 1, gy - 7, G2)
        P.hline(cx - 2, cx + 1, gy - 5, G2)
        P.px(cx - 3, gy - 10, G3)
    elif kind == 1:
        P.rect(cx - 1, gy - 13, cx + 1, gy, G)
        P.rect(cx - 4, gy - 10, cx + 4, gy - 8, G)
        P.vline(cx + 1, gy - 13, gy, G2)
        P.px(cx - 1, gy - 13, G3)
    elif kind == 2:
        P.poly([(cx - 3, gy - 7), (cx + 3, gy - 8), (cx + 4, gy), (cx - 3, gy)], G)
        P.vline(cx + 3, gy - 7, gy, G2)
        P.hline(cx - 1, cx + 1, gy - 5, G2)
    else:
        P.poly([(cx - 3, gy - 10), (cx, gy - 14), (cx + 3, gy - 10), (cx + 3, gy), (cx - 3, gy)], G)
        P.vline(cx + 3, gy - 10, gy, G2)
        P.px(cx, gy - 8, G2)
        P.hline(cx - 1, cx + 1, gy - 7, G2)
    P.outline(out)
    P.ax, P.ay = cx, gy
    return crop(P)


def hw_pumpkin(rx, ry, K, out, face=True, seed=0):
    P = Pic(2 * rx + 8, 2 * ry + 10)
    cx, cy = P.w // 2, P.h - ry - 3

    def f(dx, dy, x, y):
        u = abs(dx) / (rx + 0.4)
        col = K["PU"]
        if 0.38 < u < 0.52 or u > 0.86:
            col = K["PU2"]
        if dx < -rx * 0.55 and dy < 0 and on(x, y, 0.5) and u < 0.86:
            col = K["PU3"]
        return col

    P.ell(cx, cy, rx, ry, K["PU"], f)
    P.rect(cx, cy - ry - 2, cx + 1, cy - ry, K["STEM"])
    P.px(cx + 2, cy - ry - 2, K["STEM"])
    if face:
        ey = cy - max(1, ry // 3)
        ex = max(2, rd(rx * 0.45))
        for sx in (-1, 1):
            x0 = cx + sx * ex
            P.px(x0, ey, K["FACE"])
            P.px(x0 - 1, ey + 1, K["FACE"])
            P.px(x0, ey + 1, K["GLOW"] if rx >= 6 else K["FACE"])
            P.px(x0 + 1, ey + 1, K["FACE"])
        my = cy + max(1, ry // 3)
        for dx in range(-ex - 1, ex + 2):
            P.px(cx + dx, my, K["FACE"])
            if dx % 2 == 0:
                P.px(cx + dx, my + 1, K["FACE"])
            elif rx >= 6:
                P.px(cx + dx, my - 1, K["FACE"])
        if rx >= 6:
            for dx in range(-ex + 1, ex, 2):
                P.px(cx + dx, my, K["GLOW"])
    P.outline(out)
    P.ax, P.ay = cx, cy + ry
    return crop(P)


def theme_halloween():
    K = HW
    OUT = K["OUT"]
    S = Pic(W, H, True)
    R = random.Random(13)
    mx = 470
    S.place(hw_moon(22, K, OUT), mx, 46)
    batpal = {"k": K["BAT"], "e": K["EYE"]}
    # 언덕 + 땅
    def hgt(x):
        h = 6 + wave(x, [(3, 1.3, 0.2), (8, 0.8, 1.5), (17, 0.5, 0.9)])
        d = wd(x, mx) / 58
        h += 27 * math.exp(-d * d * 1.6)
        return h

    gs = [GY - rd(hgt(x)) for x in range(W)]
    # 집 (언덕 위, 달 앞)
    house = hw_house(K, OUT)
    S.place(house, mx - 2, gs[mx] + 2)

    def gfill(x, y, d):
        if hsh(x, y, 9) == 0:
            return K["GD2"]
        if d > 3 and on(x, y, 0.3):
            return K["GD2"]
        return K["GD"]

    # 철 울타리 (무덤 뒤)
    for x in range(178, 306):
        gy0 = gs[x]
        if (x - 178) % 4 == 0 and x not in (222, 226, 270):
            hh = 12 if (x - 178) % 8 == 0 else 10
            if x == 250:
                S.line(x, gy0, x + 2, gy0 - hh, K["FENCE"])
                continue
            S.vline(x, gy0 - hh, gy0, K["FENCE"])
            S.px(x - 1, gy0 - hh + 1, K["FENCE"])
            S.px(x + 1, gy0 - hh + 1, K["FENCE"])
            S.px(x, gy0 - hh - 1, K["FENCE"])
        if not 219 < x < 229:
            S.px(x, gy0 - 8, K["FENCE"])
            S.px(x, gy0 - 3, K["FENCE"])
    fill_profile(S, gs, GY, gfill, K["GD_E"])
    # 꼬부랑 나무 (거미줄은 가지 사이) + 매달린 거미 + 부엉이
    tr = hw_tree(66, K)
    tx = 118
    owl = sprite(OWL, {"o": K["OWL"], "O": C("c4a88a"), "Y": K["EYE"], "b": K["OWL2"]}, OUT)
    sx, sy = tr.side
    owx = rd(sx - 13)
    tr.place(owl, owx, hw_perch(tr, owx, sy - 12, sy + 10) + 1)
    S.place(tr, tx, gs[tx] + 1)
    ox, oy = tx - tr.ax, gs[tx] + 1 - tr.ay
    fx, fy = tr.fork
    spid_x, spid_y = rd(ox + fx + 17), rd(oy + fy - 2)
    top_y = hw_perch(S, spid_x, oy + fy - 30, oy + fy)
    S.vline(spid_x, top_y, spid_y, K["WEB"])
    for dx, dy in ((0, 0), (0, 1), (-1, 0), (1, 0), (-1, 1), (1, 1), (0, 2), (-2, -1), (2, -1), (-2, 1), (2, 1), (-2, 3), (2, 3)):
        S.px(spid_x + dx, spid_y + 1 + dy, K["BAT"])
    # 언덕길 (집 문까지 디딤돌) + 언덕 위 작은 마른 나무
    for i in range(16):
        t = i / 15
        x, _ = bez([(418, 0), (440, 0), (452, 0), (mx - 4, 0)], t)
        x = rd(x)
        y = gs[x] + 2 + rd(2.2 * math.sin(t * 5.5))
        S.hline(x, x + 1, y, K["GV"])
        S.hline(x, x + 1, y + 1, K["GV2"])
    S.place(hw_tree(24, K, seed=9), 526, gs[526] + 1)
    # 마녀 (빗자루)
    S.place(sprite(WITCH, {"k": K["BAT"], "g": C("8cc070"), "b": C("8a6a4e"), "O": C("d8a050")}), 64, 40)
    # 무덤
    for x, kind in [(192, 0), (212, 1), (236, 3), (258, 0), (280, 2), (298, 1)]:
        S.place(hw_grave(kind, K, OUT), x, gs[x] + 2)
    # 호박 등불
    for x, rx_, ry_ in [(48, 8, 6), (66, 5, 4), (322, 6, 5), (338, 4, 3), (586, 7, 5), (606, 5, 4), (626, 4, 3), (400, 5, 4)]:
        S.place(hw_pumpkin(rx_, ry_, K, OUT, face=rx_ >= 5, seed=x), x, gs[x] + 3)
    # 유령
    S.place(sprite(GHOST, {"W": K["GH"], "w": K["GH2"], "k": K["OUT"], "p": K["BLUSH"]}, OUT), 296, 76)
    # 박쥐
    for x, y, up in [(426, 30, True), (512, 26, False), (538, 50, True), (446, 62, False), (166, 40, True), (188, 30, False), (366, 46, True), (624, 66, False)]:
        S.place(sprite(BAT_UP if up else BAT_DN, batpal), x, y)
    for _ in range(30):
        x = R.randrange(W)
        S.px(x, gs[x] - 1, K["GRASS"])
        S.px(x + 1, gs[x] - 2, K["GRASS"])

    # ── 아이콘 ──
    I = icon_sky([C("3a2a58"), C("5a3a70"), C("8a4a72"), C("c8645a")])
    I.place(hw_moon(11, K, OUT), 30, 17)
    I.place(sprite(BAT_UP, batpal), 13, 10)
    I.place(sprite(BAT_DN, batpal), 40, 31)
    icon_ground(I, 40, K["GD_E"], K["GD"], lambda x, y: K["GD2"] if hsh(x, y, 5) == 0 else K["GD"])
    I.place(hw_grave(0, K, OUT), 34, 42)
    I.place(hw_grave(1, K, OUT), 42, 42)
    I.place(hw_pumpkin(7, 5, K, OUT), 15, 44)
    icon_frame(I, OUT, C("9a7ab8"), C("1c1424"))
    return S, I


# ═══════════════════════════════ 5. 벚꽃길 ═══════════════════════════════
CH = dict(
    OUT=C("7a4e5e"),
    HL=C("bcdcae"), HL_E=C("8ab884"), HLP=C("f4b8cc"),
    TR=C("7c5248"), TR2=C("5c3a36"),
    PK=C("f4a8c4"), PK2=C("fad0e0"), PK3=C("e07ca6"),
    RV=C("8cc4ec"), RV2=C("6aa6dc"), RV3=C("c4e4f8"),
    BK=C("94c88a"), BK2=C("74ac70"),
    PATH=C("ecd4b0"), PATH2=C("d8bc94"), PATH_E=C("b4946c"),
    BR=C("c8c2b6"), BR2=C("a49e92"), BR3=C("e4e0d6"), RAIL=C("8a6a52"),
    LP=C("4e5e5a"), LG=C("fae2a0"),
    BN=C("b07c52"), BN2=C("8a5a3a"),
    DK=C("8a6e5a"), DK2=C("f4f0e4"), DG=C("4e8a64"), DY=C("f6d24a"), DO=C("f09a3a"),
)

DUCK = [
    "..GG.....",
    ".OGkG....",
    "..GGG...B",
    "...BBBBBB",
    "...BWWWBB",
    "....BBBB.",
]
CHICK = [
    ".YY..",
    "OYkY.",
    ".YYYY",
    "..YYY",
]


def cherry_tree(h, spread, K, out, seed=0):
    """벚나무: 줄기가 Y자로 갈라져 올라가고, 위에 뭉게구름 같은 꽃송이 덩어리"""
    R = random.Random(seed)
    P = Pic(2 * spread + 30, h + 20)
    bx, gy = P.w // 2, P.h - 3
    fork = (bx + R.uniform(-1.5, 1.5), gy - h * 0.36)
    tw = max(1.0, 2.4 * spread / 26)
    P.curve([(bx, gy), (bx - 1, gy - h * 0.2), fork], tw, tw * 0.8, K["TR"], lambda dx, dy, x, y: K["TR2"] if dx > 0.5 else K["TR"])
    if spread > 12:
        P.line(bx - 3, gy, bx, gy - 2, K["TR"])
        P.line(bx + 3, gy, bx, gy - 2, K["TR"])
    cy0 = fork[1] - spread * 0.5 - 3
    rx0, ry0 = spread * 0.8, spread * 0.36
    for ex, ey in ((fork[0] - spread * 0.5, cy0 + 2), (fork[0] + spread * 0.52, cy0), (fork[0] + 1, cy0 - 5)):
        mx, my = (fork[0] + ex) / 2, (fork[1] + ey) / 2 + 1
        P.curve([fork, (mx, my), (ex, ey)], tw * 0.7, 0.6, K["TR"], lambda dx, dy, x, y: K["TR2"] if dx > 0.4 else K["TR"])
    blobs = []
    n = 7 + spread // 4
    for i in range(n):                                     # 위쪽 테두리 (뭉게뭉게)
        a = math.pi * (0.02 + 0.96 * i / (n - 1))
        blobs.append((fork[0] + math.cos(a) * rx0 * R.uniform(0.85, 1.0), cy0 - math.sin(a) * ry0 * R.uniform(0.8, 1.0) + 1,
                      spread * R.uniform(0.22, 0.3)))
    for _ in range(4 + spread // 6):                       # 속을 채움
        blobs.append((fork[0] + R.uniform(-rx0 * 0.6, rx0 * 0.6), cy0 + R.uniform(-ry0 * 0.4, ry0 * 0.5), spread * R.uniform(0.25, 0.33)))
    m = 4 + spread // 5
    for i in range(m):                                     # 아래 테두리: 늘어진 작은 꽃송이 (버섯 모양 방지)
        u = -1 + 2 * (i + 0.5) / m
        droop = (abs(u) ** 1.5) * spread * 0.12
        blobs.append((fork[0] + u * rx0 * 1.05, cy0 + ry0 * 0.55 + droop + R.uniform(-1, 1.5), spread * R.uniform(0.13, 0.19)))
    blobs.sort(key=lambda b: b[1])

    def bf(dx, dy, x, y, r):
        if y > cy0 + ry0 * 0.55 and on(x, y, min(1.0, (y - cy0 - ry0 * 0.55) / 4 + 0.35)):
            return K["PK3"]
        if dy < -r * 0.3 and dx < r * 0.35 and on(x, y, 0.6):
            return K["PK2"]
        if dy > r * 0.5 and on(x, y, 0.45):
            return K["PK3"]
        return K["PK"]

    for x, y, r in blobs:
        P.ell(x, y, r, r * 0.82, K["PK"], lambda dx, dy, xx, yy, r=r: bf(dx, dy, xx, yy, r))
    for _ in range(int(spread * 3)):
        x, y, r = R.choice(blobs)
        qx, qy = rd(x + R.uniform(-r, r)), rd(y + R.uniform(-r * 0.7, r * 0.7))
        if P.get(qx, qy)[3] and P.get(qx, qy) != K["TR"]:
            if qy < cy0:
                P.px(qx, qy, K["PK2"])
                P.px(qx + 1, qy, K["PK2"]) if R.random() < 0.3 else None
            else:
                P.px(qx, qy, K["PK3"])
    P.outline(out)
    P.ax, P.ay = bx, gy
    return crop(P)


def ch_lamp(h, K, out):
    P = Pic(9, h + 8)
    cx, gy = 4, h + 5
    P.vline(cx, gy - h, gy, K["LP"])
    P.hline(cx - 1, cx + 1, gy, K["LP"])
    P.hline(cx - 1, cx + 1, gy - 1, K["LP"])
    P.hline(cx - 2, cx + 2, gy - h - 1, K["LP"])
    P.rect(cx - 1, gy - h - 4, cx + 1, gy - h - 2, K["LG"])
    P.hline(cx - 2, cx + 2, gy - h - 5, K["LP"])
    P.px(cx, gy - h - 6, K["LP"])
    P.outline(out)
    P.ax, P.ay = cx, gy
    return crop(P)


def ch_bench(K, out):
    rows = [
        "bbbbbbbbbbbb",
        "BBBBBBBBBBBB",
        "............",
        "bbbbbbbbbbbb",
        "BBBBBBBBBBBB",
        ".k........k.",
        ".k........k.",
    ]
    return sprite(rows, {"b": K["BN"], "B": K["BN2"], "k": K["LP"]}, out)


def ch_bridge(K, out):
    P = Pic(116, 34)
    cx, wl = 58, 30
    half = 42
    for dx in range(-half - 12, half + 13):
        u = max(-1.0, min(1.0, dx / half))
        deck = rd(12 - 6 * (1 - u * u))
        for y in range(deck, wl + 1):
            ay = wl - y
            if (dx / 23.5) ** 2 + (ay / 15.5) ** 2 < 1.0:        # 홍예 (아치 구멍)
                continue
            if abs(dx) > half - 4 + (y - deck) * 0.55:          # 양끝: 아래로 넓어지는 돌 받침
                continue
            col = K["BR"]
            row = (y - deck) // 3
            if (y - deck) % 3 == 2 or (dx + row * 3) % 7 == 0:
                col = K["BR2"]
            if (dx / 25.5) ** 2 + (ay / 17.5) ** 2 < 1.0 and ay >= 0:
                col = K["BR3"] if (math.atan2(ay, dx) * 8) % 2 > 0.4 else K["BR2"]
            P.px(cx + dx, y, col)
        if abs(dx) <= half - 4:
            P.px(cx + dx, deck, K["BR2"])
        if abs(dx) < half - 5:
            P.px(cx + dx, deck - 4, K["RAIL"])
            if dx % 6 == 0:
                for k in range(1, 4):
                    P.px(cx + dx, deck - k, K["RAIL"])
    P.outline(out)
    P.ax, P.ay = cx, wl
    return crop(P)


def theme_cherry():
    K = CH
    OUT = K["OUT"]
    S = Pic(W, H, True)
    R = random.Random(17)
    # 먼 언덕 + 분홍 점 나무
    tops = [GY - rd(30 + wave(x, [(3, 5, 0.7), (7, 3, 0.1), (15, 1.4, 2.0)])) for x in range(W)]
    fill_profile(S, tops, GY, lambda x, y, d: K["HLP"] if hsh(x, y, 29) == 0 and d < 10 else K["HL"], K["HL_E"])
    for _ in range(26):
        x = R.randrange(W)
        y = tops[x] + R.randint(1, 4)
        S.ell(x, y, 2.2, 1.6, K["HLP"])
    # 먼 강둑 작은 벚나무
    far_bank = 106
    for x in [14, 104, 226, 404, 486, 532, 624]:
        S.place(cherry_tree(12, 9, K, OUT, seed=x + 1), x, far_bank)
    S.rect(0, far_bank - 1, W - 1, far_bank + 1, K["BK"])
    S.hline(0, W - 1, far_bank - 2, K["HL_E"])
    # 강
    r0, r1 = 108, 117
    for y in range(r0, r1 + 1):
        for x in range(W):
            col = K["RV"] if y < 112 else K["RV2"]
            if y == r0:
                col = K["RV2"]
            elif y == 112 and on(x, y, 0.5):
                col = K["RV"]
            S.px(x, y, col)
    for y in range(r0 + 1, r1):
        for x in range(W):
            if (x * 7 + y * 13) % 29 == 0:
                for k in range(2 + (y - r0) // 3):
                    S.px(x + k, y, K["RV3"])
    # 다리 + 물그림자
    bxp = 320
    br = ch_bridge(K, OUT)
    S.place(br, bxp, r1)
    for y in range(r1 - 7, r1 + 1):
        for x in range(bxp - 24, bxp + 25):
            dx = x - bxp
            if (dx / 23.5) ** 2 + ((r1 - y) / 15.5) ** 2 < 1.0 and S.get(x, y) in (K["RV"], K["RV2"], K["RV3"]) and on(x, y, 0.5):
                S.px(x, y, K["RV2"])
    # 오리 가족
    duckpal = {"G": K["DG"], "O": K["DO"], "k": OUT, "B": K["DK"], "W": K["DK2"], "Y": K["DY"]}
    S.place(sprite(DUCK, duckpal, OUT), 470, 115)
    S.place(sprite(CHICK, duckpal, OUT), 482, 115)
    S.place(sprite(CHICK, duckpal, OUT), 490, 116)
    # 이쪽 둑 (풀) + 길
    gs = [GY - 6 for _ in range(W)]
    S.rect(0, r1 + 1, W - 1, GY, K["BK"])
    for x in range(W):
        if hsh(x, r1 + 2, 4) == 0:
            S.px(x, r1 + 1, K["BK2"])
    fill_profile(S, gs, GY, lambda x, y, d: K["PATH2"] if hsh(x, y, 7) == 0 else K["PATH"], K["PATH_E"])
    # 가로등 · 벤치
    for x in (118, 252, 392, 520):
        S.place(ch_lamp(24, K, OUT), x, GY - 3)
    S.place(ch_bench(K, OUT), 226, GY - 2)
    # 큰 벚나무
    for x, h, sp in [(58, 52, 29), (180, 46, 25), (446, 54, 30), (578, 48, 27)]:
        S.place(cherry_tree(h, sp, K, OUT, seed=x), x, r1 + 4)
    # 꽃잎 (하늘 · 길)
    for _ in range(90):
        x, y = R.randrange(W), R.randint(36, 121)
        if S.get(x, y)[3] == 0:
            col = K["PK3"] if R.random() < 0.6 else K["PK"]
            S.px(x, y, col)
            if R.random() < 0.6:
                S.px(x + 1, y + (1 if R.random() < 0.5 else 0), col)
    for _ in range(50):
        x = R.randrange(W)
        S.px(x, R.randint(GY - 4, GY - 1), K["PK3"] if R.random() < 0.5 else K["PK"])

    # ── 아이콘 ──
    I = icon_sky([C("e4f0fa"), C("f6e6ee")])
    for x in range(48):
        h = rd(6 + 2 * math.sin(x * 0.2))
        for y in range(34 - h, 34):
            I.px(x, y, K["HL_E"] if y == 34 - h else K["HL"])
    for y in range(34, 39):
        for x in range(48):
            I.px(x, y, K["RV3"] if (x * 5 + y * 3) % 11 == 0 else (K["RV"] if y < 36 else K["RV2"]))
    icon_ground(I, 39, K["PATH_E"], K["PATH"])
    I.rect(0, 39, 47, 40, K["BK"])
    I.place(ch_lamp(16, K, OUT), 39, 44)
    I.place(cherry_tree(26, 17, K, OUT, seed=3), 19, 41)
    R3 = random.Random(5)
    for _ in range(14):
        x, y = R3.randrange(3, 45), R3.randrange(3, 44)
        I.px(x, y, K["PK3"])
    icon_frame(I, OUT, C("fff4f8"), C("b08a98"))
    return S, I


# ═══════════════════════════════ 6. 여름 바다 ═══════════════════════════════
BC = dict(
    OUT=C("344a6a"),
    SEA1=C("9ad2ec"), SEA2=C("6ab4e2"), SEA3=C("4c98d2"), SEAH=C("d0eefa"), SEA_E=C("4a86b8"),
    FOAM=C("f6fcff"), FOAM2=C("bfe6f4"),
    SAND=C("f2daa4"), SAND2=C("e2c286"), SAND3=C("cca86c"), WET=C("d8bc88"),
    TR=C("b07c4c"), TR2=C("885a36"), FR=C("4cae5e"), FR2=C("2e8648"), FR3=C("80cc78"), CO=C("6e4628"),
    LW=C("f6f4ee"), LW2=C("d6d4ce"), LR=C("e05444"), LR2=C("b03c34"), LL=C("fad64e"), LD=C("3e4a5e"),
    RK=C("9a9eaa"), RK2=C("7a7e8c"), RK3=C("bcc0ca"),
    HULL=C("d8584a"), HULL2=C("a8403a"), SAIL=C("fbfbf6"), SAIL2=C("dcdcd4"), SAILB=C("f6c84a"),
    UR=C("ee5a4c"), UW=C("fbf6ee"), UB=C("4c9ad6"), POLE=C("8a8a96"),
    TOW=C("4cb4c4"), TOW2=C("f6f0e4"),
    SUN=C("f6c030"), CLOUD=C("fbfcfe"), CLOUD_E=C("a6bcd4"),
    ISL=C("7aae8e"), ISL2=C("5a8e72"),
    GULL=C("7a8494"),
    CRAB=C("e05a3c"), STARF=C("f09a4a"), SHELL=C("f4b4c0"),
    BL1=C("ee5a4c"), BL2=C("f6d24a"), BL3=C("4c9ad6"),
)

CASTLE = [
    ".......r.......",
    ".......rr......",
    ".......k.......",
    "......sss......",
    "s.s...sSs...s.s",
    "sss...sss...sss",
    "sSs.s.sss.s.sSs",
    "sssssssssssssss",
    "sSsssssSsssssSs",
    "sssssskkksssss.",
    "sssssskkkssssss",
    "SSSSSSSSSSSSSSS",
]
CRAB = [
    "r.......r",
    "rr.k.k.rr",
    ".rrrrrrr.",
    "rrrrrrrrr",
    ".r.r.r.r.",
]
STARF = [
    "..o..",
    "..o..",
    "ooooo",
    ".ooo.",
    "o...o",
]
GULL = [
    ".gg...gg.",
    "g..g.g..g",
    "....g....",
]


def bc_lighthouse(K, out, h=44):
    P = Pic(30, h + 22)
    cx, gy = 15, h + 19
    top = gy - h
    for y in range(top, gy + 1):
        half = 3.2 + 2.6 * (y - top) / h
        band = ((gy - y) // 7) % 2
        for x in range(rd(cx - half), rd(cx + half) + 1):
            dark = x > cx + half * 0.35
            if band:
                col = K["LR2"] if dark else K["LR"]
            else:
                col = K["LW2"] if dark else K["LW"]
            P.px(x, y, col)
    P.rect(cx - 1, gy - 4, cx + 1, gy, K["LD"])
    P.px(cx, gy - 5, K["LD"])
    P.px(cx, gy - 18, K["LD"])
    P.px(cx, gy - 30, K["LD"])
    # 전망대 · 등불 · 지붕
    P.rect(cx - 6, top - 1, cx + 6, top, K["LD"])
    for x in range(cx - 6, cx + 7, 2):
        P.px(x, top - 2, K["LD"])
    P.hline(cx - 6, cx + 6, top - 3, K["LD"])
    P.rect(cx - 3, top - 7, cx + 3, top - 3, K["LL"])
    P.vline(cx - 3, top - 7, top - 3, K["LD"])
    P.vline(cx + 3, top - 7, top - 3, K["LD"])
    P.vline(cx, top - 7, top - 3, K["LD"])
    P.ell(cx, top - 8, 4, 2.4, K["LR"], lambda dx, dy, x, y: K["LR"] if dy <= 0.5 else None)
    P.hline(cx - 4, cx + 4, top - 8, K["LR2"])
    P.vline(cx, top - 12, top - 11, K["LD"])
    P.outline(out)
    P.ax, P.ay = cx, gy
    return crop(P)


def bc_sailboat(K, out, s=1.0):
    P = Pic(int(34 * s) + 6, int(36 * s) + 6)
    cx, wl = P.w // 2 - 1, P.h - 3
    P.poly([(cx - 12 * s, wl - 4 * s), (cx + 13 * s, wl - 4 * s), (cx + 9 * s, wl), (cx - 8 * s, wl)], K["HULL"])
    P.hline(cx - 11 * s, cx + 12 * s, rd(wl - 3 * s), K["SAIL"])
    P.hline(cx - 7 * s, cx + 8 * s, wl, K["HULL2"])
    P.vline(cx, wl - 30 * s, wl - 5 * s, K["LD"])
    P.poly([(cx + 1, wl - 29 * s), (cx + 1, wl - 6 * s), (cx + 12 * s, wl - 6 * s)], K["SAIL"],
           lambda x, y: K["SAIL2"] if x < cx + 3 and on(x, y, 0.5) else K["SAIL"])
    P.poly([(cx - 1, wl - 26 * s), (cx - 1, wl - 6 * s), (cx - 10 * s, wl - 6 * s)], K["SAILB"],
           lambda x, y: K["SAIL"] if (wl - y) % 5 == 0 else K["SAILB"])
    P.rect(cx + 1, wl - 31 * s, cx + 3 * s, wl - 30 * s, K["LR"])
    P.outline(out)
    P.ax, P.ay = cx, wl
    return crop(P)


def bc_umbrella(K, out, r=12):
    P = Pic(2 * r + 8, r + 24)
    cx, gy = P.w // 2, P.h - 3
    ty = gy - r - 10
    P.line(cx, ty, cx + 2, gy, K["POLE"])
    for dx in range(-r, r + 1):
        u = dx / (r + 0.5)
        top = rd(ty - (r * 0.55) * math.sqrt(max(0.0, 1 - u * u)))
        bot = ty + (1 if (dx + r) % 6 in (2, 3) else 0)
        seg = int((dx + r) / ((2 * r + 1) / 6))
        for y in range(top, bot + 1):
            P.px(cx + dx, y, K["UR"] if seg % 2 == 0 else K["UW"])
    P.px(cx, rd(ty - r * 0.55) - 1, K["POLE"])
    P.outline(out)
    P.ax, P.ay = cx + 2, gy
    return crop(P)


def bc_ball(K, out, r=3):
    P = Pic(2 * r + 6, 2 * r + 6)
    c = r + 3

    def f(dx, dy, x, y):
        a = (math.atan2(dy, dx) + math.pi) / (2 * math.pi)
        if dx * dx + dy * dy <= 1:
            return K["UW"]
        return (K["BL1"], K["UW"], K["BL2"], K["BL3"])[int(a * 4) % 4]

    P.ell(c, c, r, r, K["UW"], f)
    P.outline(out)
    P.ax, P.ay = c, c + r
    return crop(P)


def bc_cloud(blobs, K):
    P = Pic(60, 24)
    for x, y, r in blobs:
        P.ell(x, y, r, r * 0.8, K["CLOUD"])
    P.outline(K["CLOUD_E"])
    return center(crop(P))


def theme_beach():
    K = BC
    OUT = K["OUT"]
    S = Pic(W, H, True)
    R = random.Random(19)
    hz, shore = 97, 115
    # 해 · 구름 · 갈매기
    sx, sy = 300, 28
    S.ell(sx, sy, 5, 5, K["SUN"])
    for k in range(8):
        a = k * math.pi / 4
        for r in (7.5, 8.5):
            S.px(rd(sx + math.cos(a) * r), rd(sy + math.sin(a) * r), K["SUN"])
    S.place(bc_cloud([(10, 12, 5), (17, 9, 6), (25, 12, 5), (18, 14, 5)], K), 166, 40)
    S.place(bc_cloud([(10, 12, 4), (16, 10, 5), (22, 12, 4)], K), 516, 30)
    for x, y in [(252, 54), (266, 48), (424, 44), (436, 50)]:
        S.place(sprite(GULL, {"g": K["GULL"]}), x, y)
    # 먼 섬
    for x in range(118, 162):
        u = (x - 140) / 22
        hh = rd(6 * max(0.0, 1 - u * u) ** 0.7)
        for y in range(hz - hh, hz):
            S.px(x, y, K["ISL2"] if y == hz - hh else K["ISL"])
    S.vline(146, hz - 11, hz - 6, K["ISL2"])
    for dx, dy in ((-2, 0), (-1, -1), (1, -1), (2, 0), (0, -1)):
        S.px(146 + dx, hz - 11 + dy, K["ISL2"])
    # 바다
    for y in range(hz, shore + 1):
        t = (y - hz) / (shore - hz)
        for x in range(W):
            col = K["SEA1"]
            if on(x, y, min(1, t * 1.6)):
                col = K["SEA2"]
            if on(x, y, max(0, t * 1.8 - 0.9)):
                col = K["SEA3"]
            if y == hz:
                col = K["SEA_E"]
            S.px(x, y, col)
    for _ in range(70):
        x, y = R.randrange(W), R.randint(hz + 2, shore - 2)
        ln = 2 + (y - hz) // 5
        S.hline(x, x + ln, y, K["SEAH"])
        if R.random() < 0.4:
            S.hline(x + 1, x + ln - 1, y + 1, K["SEA3"])
    # 등대 + 바위
    lx = 568
    for x, y, rx, ry in [(552, 112, 9, 5), (582, 113, 10, 5), (566, 108, 9, 6), (596, 116, 6, 3), (540, 116, 5, 3)]:
        rk = Pic(2 * rx + 6, 2 * ry + 6)
        rk.ell(rx + 3, ry + 3, rx, ry, K["RK"], lambda dx, dy, xx, yy: K["RK3"] if dx + dy < -ry * 0.5 else (K["RK2"] if dy > ry * 0.3 else K["RK"]))
        rk.outline(OUT)
        S.place(center(crop(rk)), x, y)
    S.place(bc_lighthouse(K, OUT), lx, 106)
    # 돛단배
    S.place(bc_sailboat(K, OUT), 392, 108)
    for x in range(380, 406):
        if x % 3:
            S.px(x, 110, K["SEA3"])
    # 모래 + 파도 거품
    gs = []
    for x in range(W):
        fy = shore + rd(1.3 * math.sin(2 * math.pi * 9 * x / W) + 0.8 * math.sin(2 * math.pi * 21 * x / W + 1))
        gs.append(fy)
        S.px(x, fy - 1, K["FOAM2"])
        S.px(x, fy, K["FOAM"])
        S.px(x, fy + 1, K["FOAM"] if hsh(x, 1, 3) else K["FOAM2"])
        for y in range(fy + 2, H):
            col = K["WET"] if y <= fy + 3 else K["SAND"]
            if y > fy + 3 and hsh(x, y, 9) == 0:
                col = K["SAND2"]
            if y > fy + 3 and hsh(x, y, 31) == 0:
                col = K["SAND3"]
            S.px(x, y, col)
        if hsh(x, 7, 5) == 0:
            S.px(x, fy - 2, K["FOAM2"])
    # 야자수
    for x, h, lean, fl in [(48, 54, 9, 16), (84, 40, -6, 13), (472, 46, -7, 15)]:
        S.place(palm(h, lean, fl, K, OUT, coconuts=True, seed=x), x, GY - 2)
    # 파라솔 · 수건 · 공 · 모래성 · 게 · 불가사리 · 조개
    for y, (x0, x1) in zip(range(GY - 4, GY), [(186, 210), (185, 209), (184, 208), (183, 207)]):
        for x in range(x0, x1 + 1):
            S.px(x, y, K["TOW"] if ((x - x0) // 4) % 2 == 0 else K["TOW2"])
    for x in range(183, 211):
        S.px(x, GY - 5, OUT if 186 <= x <= 210 else None)
    S.place(bc_umbrella(K, OUT), 200, GY - 3)
    S.place(bc_ball(K, OUT), 232, GY - 1)
    S.place(sprite(CASTLE, {"s": K["SAND2"], "S": K["SAND3"], "k": C("8a6a44"), "r": K["LR"]}, OUT), 292, GY - 1)
    bucket = Pic(10, 10)
    bucket.poly([(2, 3), (7, 3), (6, 7), (3, 7)], K["UB"])
    bucket.path([(2, 3), (4.5, 0), (7, 3)], K["POLE"])
    bucket.outline(OUT)
    bucket.ax, bucket.ay = 4, 7
    S.place(crop(bucket), 310, GY - 1)
    S.place(sprite(CRAB, {"r": K["CRAB"], "k": OUT}, OUT), 346, GY - 2)
    S.place(sprite(STARF, {"o": K["STARF"]}, OUT), 140, GY - 2)
    S.place(sprite(STARF, {"o": K["STARF"]}, OUT), 620, GY - 1)
    for _ in range(14):
        x = R.randrange(W)
        y = R.randint(gs[x] + 4, GY - 1)
        S.px(x, y, K["SHELL"])
        S.px(x + 1, y, K["SHELL"])

    # ── 아이콘 ──
    I = icon_sky([C("a8dcf6"), C("d4eefa")])
    I.ell(36, 10, 4, 4, K["SUN"])
    for k in range(8):
        a = k * math.pi / 4
        I.px(rd(36 + math.cos(a) * 6.5), rd(10 + math.sin(a) * 6.5), K["SUN"])
    for y in range(28, 37):
        for x in range(48):
            I.px(x, y, K["SEA_E"] if y == 28 else (K["SEA2"] if y > 31 else K["SEA1"]))
    for x in range(48):
        I.px(x, 37, K["FOAM"])
    icon_ground(I, 38, K["WET"], K["SAND"], lambda x, y: K["SAND2"] if hsh(x, y, 6) == 0 else K["SAND"])
    I.place(bc_sailboat(K, OUT, 0.42), 39, 33)
    I.place(palm(26, 3, 10, K, OUT, nf=5, coconuts=True, seed=4), 9, 45)
    I.place(bc_umbrella(K, OUT, 7), 28, 45)
    icon_frame(I, OUT, C("f0faff"), C("6a8aa8"))
    return S, I


# ─────────────────────────────── 점검 · 미리보기 ───────────────────────────────
THEMES = [
    ("space", "우주", theme_space),
    ("dino", "공룡시대", theme_dino),
    ("joseon", "조선시대", theme_joseon),
    ("halloween", "할로윈", theme_halloween),
    ("cherry", "벚꽃길", theme_cherry),
    ("beach", "여름 바다", theme_beach),
]


def check(im, key):
    a = im.getchannel("A")
    bottom = sum(1 for x in range(W) if a.getpixel((x, GY)) == 255)
    top20 = sum(1 for y in range(20) for x in range(W) if a.getpixel((x, y)) > 0)
    semi = sum(a.histogram()[1:255])
    print(f"  {key:10s} 맨아래줄 {bottom}/{W} 칸 · 위20줄 점 {top20}개 · 반투명 {semi}")


def over_white(im, alpha):
    a = im.getchannel("A").point(lambda v: int(v * alpha))
    base = Image.new("RGB", im.size, (255, 255, 255))
    base.paste(im.convert("RGB"), (0, 0), a)
    return base


def font(sz):
    for f in ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, sz)
    return ImageFont.load_default()


def preview(results, path):
    Z, pad = 3, 24
    sw, sh = W * Z, H * Z
    head = 170
    block = head + sh + 14 + sh + 36
    img = Image.new("RGB", (sw + 2 * pad, pad + block * len(results)), (236, 238, 242))
    d = ImageDraw.Draw(img)
    f1, f2 = font(34), font(20)
    y = pad
    for key, name, strip, icon in results:
        ic = icon.resize((144, 144), Image.NEAREST)
        img.paste(ic, (pad, y + 6))
        d.text((pad + 170, y + 26), f"{name}  ({key})", fill=(40, 40, 52), font=f1)
        d.text((pad + 170, y + 80), "위: ×3 원본 (흰 바탕)   아래: ×3, 40% 옅게 (앱에서 보이는 느낌) — 아래 줄은 반 칸(320) 밀어서 이음새가 한가운데",
               fill=(90, 92, 104), font=f2)
        d.text((pad + 170, y + 110), "아이콘 48×48 (×3 확대)", fill=(90, 92, 104), font=f2)
        y += head
        big = strip.resize((sw, sh), Image.NEAREST)
        img.paste(over_white(big, 1.0), (pad, y))
        y += sh + 14
        rolled = ImageChops.offset(strip, W // 2, 0).resize((sw, sh), Image.NEAREST)
        img.paste(over_white(rolled, PREVIEW_ALPHA), (pad, y))
        mx = pad + sw // 2
        d.polygon([(mx - 8, y - 12), (mx + 8, y - 12), (mx, y - 2)], fill=(220, 90, 90))
        y += sh + 36
    img.save(path)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(here, "..", "app", "src", "main", "assets", "bg"))
    prev = sys.argv[2] if len(sys.argv) > 2 else os.path.normpath(os.path.join(here, "..", "..", "스크린샷", "78_배경_테마_시안.png"))
    os.makedirs(out_dir, exist_ok=True)
    res = []
    for key, name, fn in THEMES:
        strip, icon = fn()
        check(strip.im, key)
        strip.im.save(os.path.join(out_dir, key + ".png"), optimize=True)
        icon.im.save(os.path.join(out_dir, key + "_icon.png"), optimize=True)
        res.append((key, name, strip.im, icon.im))
    preview(res, prev)
    print("저장:", out_dir)
    print("미리보기:", prev)


if __name__ == "__main__":
    main()
