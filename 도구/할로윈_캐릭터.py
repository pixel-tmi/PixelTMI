"""
Pixel TMI 할로윈 캐릭터 3종 — 유령(ghost) · 호박 잭(pumpkin) · 마녀 고양이(witch).
결: 고양이 오마주·동물 오마주·탈것 도트와 같은 틀 — 한 프레임 34×24칸(앱 아이콘 24도트와 1:1),
    도형을 조립한 뒤 1칸 외곽선을 자동으로 두르고, 무늬(dt)는 그 위에, 효과(fx: 잔상·반짝이)는 몸 뒤에 외곽선 없이.
    모두 오른쪽을 보고, 투명 바탕, 흰 바탕·어두운 바탕 둘 다 읽히게.

  유령   (날기) : 하얀 천 유령. 다리 없이 물결치는 밑단이 프레임마다 출렁, 작은 팔, 볼터치, 반짝이는 큰 눈.
                 밑단 끝은 살짝 비친다(반투명). 달리면 혜성처럼 뒤로 늘어지고 잔상 꼬리.
  호박 잭 (걷기) : 잭오랜턴 머리 + 덩굴 몸 + 짧은 다리. 파낸 얼굴 속이 노랗게 빛나고(촛불 깜빡),
                 초록 꼭지에 돌돌 말린 덩굴. 달리기는 통통 튀는 깡충 뛰기(찌그러짐·늘어남).
  마녀 고양이 (날기) : 보라 고깔모자를 쓴 검은 고양이가 빗자루를 타고 난다. 지푸라기 결 빗자루, 별가루 꼬리.
                 얼굴은 기본 고양이와 같은 문법 (코 없음, 'ω' 입, 수염).

※ 앱(PetView) 약속: idle 0번 = 가만히, 1번 = 아주 잠깐 보이는 깜빡/반짝.
   face = 말하기·놀람·웃음 3칸이고 idle 0번과 같은 자세 (말할 때 face 0 ↔ idle 0 을 번갈아 보여 준다).
   컷인은 face 1번(놀람)의 x13~33·y0~16 을 잘라 확대하고 (20,7)·(25,7) 근처에 눈 번뜩을 그린다 → 눈을 그 근처에 둔다.

사용: python 할로윈_캐릭터.py <출력 폴더> <미리보기.png>
출력 (이름 = ghost · pumpkin · witch):
  <이름>_walk.png  4프레임 (136×24)
  <이름>_run.png   6프레임 (204×24)
  <이름>_idle.png  2프레임 (가만히 · 깜빡/반짝)
  <이름>_face.png  3프레임 (말하기 · 놀람 · 웃음)
"""
import math
import os
import sys

from PIL import Image, ImageDraw

W, H = 34, 24
CLEAR = (0, 0, 0, 0)
SHINE = (255, 255, 255, 255)


def rnd(v):
    return int(math.floor(v + 0.5))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + (c[3] if len(c) > 3 else 255,)


def alpha(c, a):
    return c[:3] + (a,)


# ── 캔버스 ────────────────────────────────────────────────────────────
class Cv:
    """도트 캔버스. px=몸(자동 외곽선) · dt=무늬(몸 위 덧칠) · fx=효과(몸 뒤, 외곽선 없음)
    line_a(x, y) 가 있으면 그 자리 외곽선의 불투명도 (유령 밑단을 비치게)"""

    def __init__(self, line):
        self.line = line
        self.px, self.dt, self.fx = {}, {}, {}
        self.line_a = None

    def _L(self, to):
        return getattr(self, to)

    def rect(self, x0, y0, x1, y1, c, to="px"):
        L = self._L(to)
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                L[(x, y)] = c

    def put(self, x, y, c, to="px"):
        self._L(to)[(x, y)] = c

    def cut(self, *pts):
        for p in pts:
            self.px.pop(p, None)
            self.dt.pop(p, None)

    def ellipse(self, cx, cy, rx, ry, c, to="px", keep=None):
        L = self._L(to)
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 and (keep is None or keep(x, y)):
                    L[(x, y)] = c

    def line_(self, x0, y0, x1, y1, c, to="px", w=1):
        L = self._L(to)
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        flat = abs(x1 - x0) > abs(y1 - y0)
        for i in range(n + 1):
            x, y = rnd(x0 + (x1 - x0) * i / n), rnd(y0 + (y1 - y0) * i / n)
            for k in range(w):
                L[(x, y + k) if flat else (x + k, y)] = c

    def path(self, pts, c, to="px", w=1):
        for a, b in zip(pts, pts[1:]):
            self.line_(a[0], a[1], b[0], b[1], c, to, w)

    def poly(self, pts, c, to="px"):
        L = self._L(to)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
                inside = False
                j = len(pts) - 1
                for i in range(len(pts)):
                    (xi, yi), (xj, yj) = pts[i], pts[j]
                    if (yi > y + 0.5) != (yj > y + 0.5) and x + 0.5 < (xj - xi) * (y + 0.5 - yi) / (yj - yi) + xi:
                        inside = not inside
                    j = i
                if inside:
                    L[(x, y)] = c

    def art(self, x0, y0, rows, pal, to="dt"):
        """글자 그림: pal 의 글자 → 색, 그 밖의 글자는 비움"""
        L = self._L(to)
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch in pal:
                    L[(x0 + dx, y0 + dy)] = pal[ch]

    def overlay(self, o, line=None, edge=True):
        """o 를 몸 위에 얹는다. 맞닿은 몸 쪽에 경계선을 그어 형태가 묻히지 않게"""
        line = line or self.line
        region = set(o.px)
        for p in region:
            self.dt.pop(p, None)
        self.px.update(o.px)
        self.dt.update(o.dt)
        self.fx.update(o.fx)
        if edge:
            for (x, y) in region:
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if n not in region and n in self.px:
                        self.dt[n] = line

    def image(self, dx=0, dy=0):
        tf = lambda d: {(x + dx, y + dy): c for (x, y), c in d.items()}
        px, dt, fx = tf(self.px), tf(self.dt), tf(self.fx)
        im = Image.new("RGBA", (W, H), CLEAR)

        def blend(x, y, c):
            if not (0 <= x < W and 0 <= y < H):
                return
            if c[3] >= 255:
                im.putpixel((x, y), c)
                return
            b = im.getpixel((x, y))
            a, ba = c[3] / 255, b[3] / 255
            oa = a + ba * (1 - a)
            rgb = tuple(int((c[i] * a + b[i] * ba * (1 - a)) / oa) for i in range(3)) if oa else (0, 0, 0)
            im.putpixel((x, y), rgb + (int(oa * 255),))

        for (x, y), c in fx.items():
            blend(x, y, c)
        ring = set()
        for (x, y) in px:
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + ddx, y + ddy)
                if n not in px and 0 <= n[0] < W and 0 <= n[1] < H:
                    ring.add(n)
        for n in ring:
            a = 255 if self.line_a is None else self.line_a(n[0] - dx, n[1] - dy)
            if a >= 255:
                im.putpixel(n, self.line)
            else:
                blend(n[0], n[1], alpha(self.line, a))
        for (x, y), c in px.items():
            blend(x, y, c)
        for (x, y), c in dt.items():
            blend(x, y, c)
        return im


def speed_lines(cv, frame, lines, xmax, col, step=3, loop=9):
    """뒤로 흘러가는 속도선. lines=[(y, 길이, 위상)]"""
    for y, ln, ph in lines:
        head = xmax - ((frame * step + ph) % loop)
        for x in range(head - ln + 1, head + 1):
            if 0 <= x <= xmax:
                cv.fx[(x, y)] = col


def columns(pts):
    """세로줄마다 (맨 위, 맨 아래)"""
    top, bot = {}, {}
    for (x, y) in pts:
        top[x] = min(top.get(x, 99), y)
        bot[x] = max(bot.get(x, -99), y)
    return top, bot


# ══════════════════════════════════════════════════════════════════════
# 1) 유령 — 하얀 천, 물결 밑단, 작은 팔, 볼터치, 반짝 큰 눈
# ══════════════════════════════════════════════════════════════════════
G_LINE = (78, 80, 118, 255)       # 보랏빛 진회색 외곽선 (흰 몸이 흰 바탕에서도 또렷)
G_BODY = (244, 245, 252, 255)
G_HI = (255, 255, 255, 255)
G_SH = (214, 218, 238, 255)       # 그늘 (라벤더 회색)
G_SH2 = (184, 189, 222, 255)      # 밑단 주름 깊은 그늘
G_EYE = (38, 32, 62, 255)
G_EYE2 = (96, 110, 190, 255)      # 눈 아래 푸른 반사
G_BLUSH = (255, 158, 190, 255)
G_MOUTH = (98, 50, 82, 255)
G_TONGUE = (242, 110, 142, 255)
G_FACE_X = (19, 24)               # 두 눈 왼쪽 칸 → 반짝점이 (20,7)·(25,7) (컷인 번뜩 자리)
G_FACE_Y = 7


def ghost_bell(cx=21.5, cy=9.0, R=8.2, lean=0.25, bottom=19.0, amp=1.25, period=5.6, phase=0.0, trail=0.0):
    """종 모양 유령 (가만히·걷기): 위는 둥근 머리, 아래로 갈수록 뒤(왼쪽)로 흐르고, 밑단은 물결"""
    pts = set()
    for y in range(0, H):
        for x in range(-4, W + 2):
            if y <= cy:
                inside = (x - cx) ** 2 + (y - cy) ** 2 <= R * R + 1.0
            else:
                t = y - cy
                c = cx - lean * t
                hw = R + 0.10 * t
                inside = (c - hw - 0.4) <= x <= (c + hw)
            if not inside:
                continue
            yb = bottom + amp * math.cos(2 * math.pi * (x - phase) / period) + trail * min(0.0, x - cx + 2)
            if y <= yb:
                pts.add((x, y))
    return pts


def ghost_paint(cv, pts, cx, cy):
    """몸 칠: 밑단 그늘 · 물결 골에서 올라가는 주름 · 뒤쪽 그늘 · 왼쪽 위 광택"""
    for p in pts:
        cv.px[p] = G_BODY
    top, bot = columns(pts)
    for x, b in bot.items():
        cv.dt[(x, b)] = G_SH
    xs = sorted(bot)
    for i in range(1, len(xs) - 1):          # 밑단이 위로 파인 골 → 주름
        x = xs[i]
        if bot[x] < bot[xs[i - 1]] and bot[x] <= bot[xs[i + 1]]:
            for k in range(1, 4):
                if (x, bot[x] - k) in pts:
                    cv.dt[(x, bot[x] - k)] = G_SH2 if k == 1 else G_SH
    lefts = {}
    for (x, y) in pts:
        lefts[y] = min(lefts.get(y, 99), x)
    for y, x0 in lefts.items():
        if y > cy - 2:
            cv.dt.setdefault((x0, y), G_SH)
            if y > cy + 3:
                cv.dt.setdefault((x0 + 1, y), G_SH)
    for x, y in top.items():
        if x < cx + 1 and y < cy:
            cv.dt[(x, y)] = G_HI
            cv.dt[(x, y + 1)] = G_HI


def ghost_arm(cv, x, y, dirx, up):
    """작은 팔: 몸 옆에서 뭉툭하게 (dirx = +1 앞 · -1 뒤, up = 들린 칸)"""
    cv.rect(x, y - up, x + dirx, y - up + 1, G_BODY)
    cv.put(x + 2 * dirx, y - up - (1 if up > 0 else 0), G_BODY)
    cv.dt[(x + dirx, y - up + 1)] = G_SH


def ghost_face(cv, mood="normal", blink=False):
    d = cv.dt
    ey = G_FACE_Y
    for x0 in G_FACE_X:
        if blink:                                    # 감은 눈 ‿
            d[(x0, ey + 1)] = G_EYE; d[(x0 + 1, ey + 2)] = G_EYE; d[(x0 + 2, ey + 1)] = G_EYE
        elif mood == "happy":                        # 웃는 눈 ^
            d[(x0, ey + 2)] = G_EYE; d[(x0 + 1, ey + 1)] = G_EYE; d[(x0 + 2, ey + 2)] = G_EYE
        else:
            # 반짝 큰 눈: 둥근 3×4 (놀라면 3×5) 안에 하얀 반짝점이 갇혀 있고, 아래엔 푸른 반사
            y0 = ey - 1 if mood == "surprised" else ey
            rows = [".D.", "DSD", "DDD", ".B."] if mood != "surprised" else [".D.", "DSD", "DDD", "DDD", ".B."]
            for dy, row in enumerate(rows):
                for dx, ch in enumerate(row):
                    if ch != ".":
                        d[(x0 + dx, y0 + dy)] = {"D": G_EYE, "S": SHINE, "B": G_EYE2}[ch]
    # 볼터치
    bx0, bx1 = G_FACE_X[0] - 2, G_FACE_X[1] + 3
    for x in (bx0, bx0 + 1, bx1, bx1 + 1):
        d[(x, ey + 3)] = G_BLUSH
    mx = G_FACE_X[0] + 3                                # 입 왼쪽 칸 (22)
    my = ey + 4
    if mood == "talk":
        d[(mx, my)] = G_MOUTH; d[(mx + 1, my)] = G_MOUTH
        d[(mx, my + 1)] = G_TONGUE; d[(mx + 1, my + 1)] = G_TONGUE
        d[(mx - 1, my)] = G_MOUTH; d[(mx + 2, my)] = G_MOUTH
    elif mood == "surprised":
        d[(mx, my)] = G_MOUTH; d[(mx + 1, my)] = G_MOUTH
        d[(mx - 1, my + 1)] = G_MOUTH; d[(mx + 2, my + 1)] = G_MOUTH
        d[(mx, my + 1)] = G_TONGUE; d[(mx + 1, my + 1)] = G_TONGUE
        d[(mx, my + 2)] = G_MOUTH; d[(mx + 1, my + 2)] = G_MOUTH
    elif mood == "happy":
        for x in range(mx - 1, mx + 3):
            d[(x, my)] = G_MOUTH
        d[(mx, my + 1)] = G_TONGUE; d[(mx + 1, my + 1)] = G_TONGUE
    else:                                               # 작은 'w' 미소
        d[(mx - 1, my)] = G_MOUTH; d[(mx + 2, my)] = G_MOUTH
        d[(mx, my + 1)] = G_MOUTH; d[(mx + 1, my + 1)] = G_MOUTH


def ghost_translucent(cv, pts, a=190):
    """밑단 맨 끝 칸과 그 아래 외곽선을 반투명하게 (천 끝이 살짝 비친다)"""
    _, bot = columns(pts)
    for x, b in bot.items():
        cv.px[(x, b)] = alpha(cv.px[(x, b)], a)
        cv.dt[(x, b)] = alpha(cv.dt.get((x, b), G_BODY), a)

    def f(x, y):
        b = bot.get(x)
        return 140 if (b is not None and y > b) else 255
    cv.line_a = f


def ghost(mode, frame, mood="normal", blink=False):
    cv = Cv(G_LINE)
    cx, cy = 21.5, 9.0
    if mode == "run":
        # 앞으로 쏠린 몸 + 바람에 뒤로 날리며 들리는 밑단 (빠른 물결)
        pts = ghost_bell(cx, cy, lean=0.85, phase=frame * 5.0 / 6, bottom=18.4, amp=1.3, period=5.0,
                         trail=0.42 + 0.06 * (0, 1, 2, 1, 0, -1)[frame])
        ghost_paint(cv, pts, cx, cy)
        # 잔상: 몸 뒤쪽 윤곽이 두 겹 초승달처럼 따라온다 (반투명 라벤더 — 흰 바탕·어두운 바탕 둘 다 보이게)
        lefts = {}
        for (x, y) in pts:
            lefts[y] = min(lefts.get(y, 99), x)
        for off, a in ((3, 210), (6, 110)):
            for y, x0 in lefts.items():
                if y <= 16 + (off == 3):
                    cv.fx[(x0 - off, y)] = (196, 202, 240, a)
                    if y < 6:
                        cv.fx[(x0 - off + 1, y - 1)] = (196, 202, 240, a)
        # 앞팔은 쭉 앞으로 (슈퍼맨 자세)
        cv.rect(29, 11, 31, 12, G_BODY); cv.put(32, 11, G_BODY)
        cv.dt[(30, 12)] = G_SH; cv.dt[(31, 12)] = G_SH
        face = "happy" if frame in (2, 3) else "normal"
        bob = (0, 0, 1, 1, 1, 0)[frame]
    else:
        if mode == "walk":
            kw = dict(lean=0.32, phase=frame * 5.6 / 4, trail=0.04)
            arms = ((2, 0), (1, 1), (0, 2), (1, 1))[frame]
            bob = (0, 0, 1, 1)[frame]
        else:
            kw = dict(lean=0.0, phase=0.0, bottom=19.2, amp=1.2)
            arms, bob = (1, 1), 0
        pts = ghost_bell(cx, cy, **kw)
        ghost_paint(cv, pts, cx, cy)
        ghost_arm(cv, 30, 12, +1, arms[0])                               # 앞 팔
        ghost_arm(cv, 13 - rnd(kw["lean"] * 3), 12, -1, arms[1])         # 뒤 팔
        face = mood if mode == "face" else "normal"
    ghost_face(cv, mood=face, blink=blink)
    ghost_translucent(cv, pts)
    if mode == "run":
        speed_lines(cv, frame, [(3, 3, 0), (21, 4, 5)], 9, (190, 196, 224, 255))
    return cv.image(dy=bob)


# ══════════════════════════════════════════════════════════════════════
# 2) 호박 잭 — 빛나는 잭오랜턴 머리, 덩굴 몸, 짧은 다리, 깡충 달리기
# ══════════════════════════════════════════════════════════════════════
P_LINE = (92, 40, 20, 255)
P_OR = (242, 138, 36, 255)
P_HI = (255, 190, 96, 255)
P_RIB = (214, 106, 28, 255)
P_DK = (194, 88, 22, 255)
P_CARVE = (120, 44, 16, 255)      # 파낸 자리 테두리 (진한 갈색 — 얼굴이 또렷하게)
P_GLOW = (255, 216, 66, 255)
P_GLOW2 = (255, 164, 28, 255)     # 구멍 맨 윗줄 (안벽, 호박색)
P_CORE = (255, 251, 206, 255)     # 촛불 한가운데
P_STEM = (104, 120, 50, 255)
P_STEM_HI = (146, 162, 74, 255)
P_STEM_TIP = (190, 196, 120, 255)
P_VINE = (106, 182, 68, 255)
P_LEAF = (120, 194, 76, 255)
P_LEAF_DK = (78, 146, 56, 255)
P_BODY = (78, 138, 72, 255)       # 덩굴 몸
P_BODY_DK = (54, 102, 56, 255)
P_COLLAR = (126, 194, 80, 255)
P_SHOE = (112, 70, 44, 255)
P_SHOE_HI = (160, 110, 72, 255)

# 얼굴 구멍 모양 (가운데 기준 상대 위치로 찍는다)
P_EYES = {
    "normal": [".X.", "XXX", "XXX"],
    "talk": [".X.", "XXX", "XXX"],
    "blink": ["...", "...", "XXX"],
    "happy": ["...", "XXX", "X.X"],
    "surprised": ["XXX", "XXX", "XXX"],
}
P_MOUTHS = {
    "normal": ["X.........X",
               "XX.XXXXX.XX",
               ".XXXXXXXXX."],
    "blink": ["X.........X",
              "XX.XXXXX.XX",
              ".XXXXXXXXX."],
    "talk": ["...XXXXX...",
             "..XXXXXXX..",
             "...XXXXX..."],
    "surprised": ["....XXX....",
                  "...XXXXX...",
                  "...XXXXX...",
                  "....XXX...."],
    "happy": ["X.........X",
              "XXX.XXX.XXX",
              ".XXXXXXXXX.",
              "...XXXXX..."],
}


def pumpkin_head(cv, cx, cy, rx, ry, vine=0, flicker=0, face="normal", bright=False):
    """잭오랜턴 머리 (cx, cy = 가운데). 둥근 네모(초타원) 몸 + 골 + 광택, 얼굴은 오른쪽으로 쏠린 3/4 정면"""
    body = set()
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            if abs((x - cx) / rx) ** 2.5 + abs((y - cy) / ry) ** 2.2 <= 1.0:
                body.add((x, y))
    top, bot = columns(body)
    sx = rnd(cx)
    ty = top[sx]
    for x in (sx - 1, sx + 2):                         # 꼭지가 앉은 홈
        if top.get(x) == ty:
            body.discard((x, ty))
    for p in body:
        cv.px[p] = P_OR
    # 얼굴 구멍
    fx, fy = sx, int(cy)
    holes = set()
    for dy, row in enumerate(P_EYES[face]):
        for dx, ch in enumerate(row):
            if ch == "X":
                holes.add((fx - 1 + dx, fy - 3 + dy))
                holes.add((fx + 4 + dx, fy - 3 + dy))
    for dy, row in enumerate(P_MOUTHS[face]):
        for dx, ch in enumerate(row):
            if ch == "X":
                holes.add((fx - 3 + dx, fy + 2 + dy))
    holes &= body
    rim = set()
    for (x, y) in holes:
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in body and n not in holes:
                rim.add(n)
    # 골: 오른쪽(얼굴 쪽)이 넓게 퍼진 세로 주름 — 얼굴·테두리는 비켜 간다
    fc = cx + 1.0
    for off in (-0.80, -0.48, 0.42, 0.78):
        for y in range(int(cy - ry), int(cy + ry) + 2):
            v = (y - cy) / ry
            if abs(v) >= 0.9:
                continue
            x = rnd(fc + off * rx * (1 - abs(v) ** 2.2) ** 0.45)
            if (x, y) in body and (x, y) not in holes and (x, y) not in rim:
                cv.dt[(x, y)] = P_RIB
    # 광택(왼쪽 위 덩이·윗선) · 그늘(아랫단·오른쪽 끝)
    for x, y in top.items():
        if (x, y) in body and x < cx + 2:
            cv.dt[(x, y)] = P_HI
    hx = rnd(cx - rx * 0.64)
    for y in range(rnd(cy - ry * 0.55), rnd(cy + ry * 0.05)):
        for x in (hx, hx + 1):
            if (x, y) in body and (x, y) not in cv.dt:
                cv.dt[(x, y)] = P_HI
    for x, y in bot.items():
        if (x, y) in body:
            cv.dt[(x, y)] = P_DK
            if (x, y - 1) in body and abs(x - cx) < rx - 3 and (x, y - 1) not in holes:
                cv.dt[(x, y - 1)] = P_DK
    rights = {}
    for (x, y) in body:
        rights[y] = max(rights.get(y, -99), x)
    for y, x in rights.items():
        if y > cy - ry * 0.4:
            cv.dt[(x, y)] = P_DK
    # 파낸 얼굴: 테두리는 진한 갈색, 속은 노란 빛 (윗줄은 호박색 안벽, 가운데는 하얀 촛불)
    for p in rim:
        cv.dt[p] = P_CARVE
    lit = []
    for (x, y) in sorted(holes, key=lambda p: (p[1], p[0])):
        if (x, y - 1) not in holes:
            c = P_GLOW2
        else:
            c = P_GLOW
            lit.append((x, y))
        cv.dt[(x, y)] = c
    for i, p in enumerate(lit):
        x, y = p
        inner = (x - 1, y) in holes and (x + 1, y) in holes
        if inner and (i + flicker) % 3 != 1:
            cv.dt[p] = P_CORE
    if bright:
        for p in holes:
            cv.dt[p] = P_CORE if (p[0], p[1] - 1) in holes else P_GLOW
    # 꼭지 (뒤로 살짝 꺾임) + 돌돌 덩굴 + 잎
    cv.rect(sx, ty - 2, sx + 1, ty, P_STEM)
    cv.put(sx - 1, ty - 3, P_STEM); cv.put(sx, ty - 3, P_STEM)
    for y in range(ty - 2, ty + 1):
        cv.dt[(sx, y)] = P_STEM_HI
    cv.dt[(sx - 1, ty - 3)] = P_STEM_TIP
    # 덩굴: 꼭지 밑동에서 왼쪽으로 돌돌 말린 가는 줄 (외곽선 없이 — 굵어지면 덩어리로 보인다)
    v = vine
    curl = [(-1, -1), (-2, -2), (-3, -3 + (v > 0)), (-4, -3 + (v > 0)), (-5, -3 + (v != 0)), (-6, -2 + (v < 0)),
            (-6, -1), (-5, 0), (-4, 0), (-4, -1)]
    for i, (dx, dy) in enumerate(curl):
        cv.dt[(sx + dx, ty + dy)] = P_VINE if i % 3 else shade(P_VINE, 0.78)
    leaf = [(2, -1), (3, -1), (4, -1), (3, -2), (4, -2)]
    for (dx, dy) in leaf:
        cv.px[(sx + dx, ty + dy)] = P_LEAF
    cv.dt[(sx + 2, ty - 1)] = P_LEAF_DK; cv.dt[(sx + 3, ty - 1)] = P_LEAF_DK
    return body


def pumpkin_legs(cv, legs):
    """legs = [(엉덩이 x, 엉덩이 y, 발 x, 발 y, 먼쪽?)] — 짧은 2칸 다리 + 앞코 신발"""
    for hx, hy, fx, fy, far in legs:
        c = P_BODY_DK if far else P_BODY
        cv.line_(hx, hy, fx, fy - 1, c, w=2)
        s = P_SHOE if not far else shade(P_SHOE, 0.8)
        cv.rect(fx, fy, fx + 2, fy, s)
        cv.put(fx, fy - 1, s); cv.put(fx + 1, fy - 1, s)
        if not far:
            cv.dt[(fx, fy - 1)] = P_SHOE_HI


def pumpkin_body(cv, bx, by, arms):
    """덩굴 몸 (bx = 가운데, by = 윗줄) + 잎 목깃 + 덩굴 팔 + 잎사귀 손"""
    cv.rect(bx - 3, by, bx + 3, by + 3, P_BODY)
    cv.cut((bx - 3, by + 3), (bx + 3, by + 3))
    for x in range(bx - 3, bx + 4):
        cv.dt[(x, by + 1)] = P_COLLAR if (x - bx) % 2 == 0 else P_BODY
    cv.dt[(bx - 3, by + 2)] = P_BODY_DK
    (fa, ba) = arms
    cv.line_(bx + 3, by + 2, fa[0], fa[1], P_BODY)
    cv.line_(bx - 3, by + 2, ba[0], ba[1], P_BODY_DK)
    cv.put(fa[0], fa[1], P_COLLAR); cv.put(ba[0], ba[1], P_LEAF_DK)


def pumpkin(mode, frame, mood="normal", blink=False):
    cv = Cv(P_LINE)
    cx, cy, rx, ry = 20.0, 10.5, 8.7, 6.0
    oy, sq, vine, flicker = 0, 0.0, 0, frame
    if mode in ("idle", "face"):
        legs = [(17, 19, 16, 22, True), (20, 19, 20, 22, False)]
        arms = ((25, 19), (14, 19))
        face = mood if mode == "face" else ("blink" if blink else "normal")
        flicker = 0
    elif mode == "walk":
        oy = (0, -1, 0, -1)[frame]
        vine = (0, -1, 0, 1)[frame]
        pose = [((17, 19, 13, 22), (20, 19, 22, 22)),        # 먼 다리 뒤 · 가까운 다리 앞 (성큼)
                ((17, 19, 16, 22), (20, 19, 19, 21)),        # 지나가기 (가까운 발 듦)
                ((17, 19, 20, 22), (20, 19, 16, 22)),        # 먼 다리 앞 · 가까운 다리 뒤
                ((17, 19, 17, 21), (20, 19, 19, 22))][frame]  # 지나가기 (먼 발 듦)
        (f0, n0) = pose
        legs = [(f0[0], f0[1] + oy, f0[2], f0[3], True), (n0[0], n0[1] + oy, n0[2], n0[3], False)]
        arms = (((26, 19 + oy), (13, 18 + oy)), ((25, 20 + oy), (14, 19 + oy)),
                ((25, 18 + oy), (13, 20 + oy)), ((25, 20 + oy), (14, 19 + oy)))[frame]
        face = "normal"
    else:   # run: 깡충 6장 — 쪼그려 착지 → 박차기(늘어남) → 오름 → 꼭대기 → 내려옴 → 발 닿기
        oy = (1, -1, -2, -2, -1, 0)[frame]
        sq = (0.8, -0.5, -0.2, 0.0, -0.2, 0.3)[frame]
        vine = (1, -1, -1, 0, 1, 1)[frame]
        legs_by = [
            [(17, 19, 14, 22, True), (20, 19, 21, 22, False)],      # 쪼그림: 다리 벌려 꾹
            [(17, 19, 14, 22, True), (20, 19, 17, 22, False)],      # 박차기: 다리 쭉 (뒤로 밂)
            [(17, 19, 13, 20, True), (20, 19, 16, 21, False)],      # 오름: 발 뒤로 접음
            [(17, 19, 16, 20, True), (20, 19, 20, 20, False)],      # 꼭대기: 발 모음
            [(17, 19, 18, 21, True), (20, 19, 22, 21, False)],      # 내려옴: 발 앞으로 뻗음
            [(17, 19, 16, 22, True), (20, 19, 20, 22, False)],      # 발 닿기
        ][frame]
        legs = [(a, b + oy, c, min(d, 22) if b + oy < d else b + oy + 1, e) for a, b, c, d, e in legs_by]
        arms = [((26, 18 + oy), (13, 18 + oy)), ((26, 16 + oy), (13, 21 + oy)), ((26, 15 + oy), (13, 15 + oy)),
                ((26, 15 + oy), (13, 16 + oy)), ((26, 17 + oy), (13, 16 + oy)), ((26, 19 + oy), (13, 19 + oy))][frame]
        face = "happy" if frame in (2, 3) else "normal"
    pumpkin_legs(cv, [l for l in legs if l[4]])
    pumpkin_body(cv, 18, 16 + oy, arms)
    pumpkin_legs(cv, [l for l in legs if not l[4]])
    head = Cv(P_LINE)
    pumpkin_head(head, cx, cy + oy + sq * 0.5, rx + sq * 0.9, ry - sq, vine=vine, flicker=flicker, face=face,
                 bright=(mode == "idle" and blink))
    cv.overlay(head, edge=True)
    if mode == "idle" and blink:
        # 반짝: 촛불이 확 타오르며 빛가루 몇 점
        for p in ((30, 5), (31, 4), (31, 6), (32, 5), (10, 3), (30, 13)):
            cv.fx[p] = (255, 210, 80, 255)
        cv.fx[(31, 5)] = (255, 250, 214, 255)
    if mode == "run":
        speed_lines(cv, frame, [(7, 3, 0), (13, 4, 4)], 8, (214, 194, 168, 255))
        if frame == 0:                                         # 착지 먼지
            for p, a in (((12, 22), 220), ((11, 21), 150), ((26, 22), 220), ((27, 21), 150)):
                cv.fx[p] = (200, 188, 170, a)
    return cv.image()


# ══════════════════════════════════════════════════════════════════════
# 3) 마녀 고양이 — 보라 고깔모자 + 검은 고양이 + 빗자루 + 별가루
# ══════════════════════════════════════════════════════════════════════
C_LINE = (20, 18, 28, 255)
C_FUR = (62, 60, 78, 255)
C_FAR = (44, 42, 58, 255)
C_RIM = (100, 98, 126, 255)       # 등·머리 윗선 (어두운 바탕에서도 실루엣이 보이게)
C_LIGHT = (114, 112, 136, 255)    # 귀 안·입선·발바닥
C_EYE = (250, 206, 60, 255)
C_WHISK = (200, 204, 214, 255)
C_COLLAR = (246, 140, 40, 255)
C_BELL = (252, 214, 70, 255)
C_BELL_DK = (204, 156, 30, 255)
HAT = (130, 72, 194, 255)
HAT_HI = (172, 120, 232, 255)
HAT_DK = (92, 46, 144, 255)
HAT_BAND = (246, 142, 40, 255)
HAT_STAR = (255, 226, 96, 255)
WOOD = (162, 104, 56, 255)
WOOD_HI = (206, 150, 88, 255)
STRAW = (238, 198, 102, 255)
STRAW_DK = (196, 148, 60, 255)
STRAW_HI = (252, 234, 164, 255)
TIE = (130, 72, 194, 255)
STAR = (250, 196, 46)
STAR_CORE = (255, 250, 214)
W_HX, W_TOP = 17, 6               # 머리 왼쪽 위 → 눈이 (20,10)·(25,10)


def cat_head(cv, hx, top):
    """기본 고양이와 같은 3/4 정면 머리 (폭 12, 높이 10) + 뾰족 귀"""
    cv.rect(hx, top, hx + 11, top + 9, C_FUR)
    cv.cut((hx, top), (hx + 11, top), (hx, top + 9), (hx + 11, top + 9))
    cv.put(hx, top - 3, C_FUR); cv.rect(hx, top - 2, hx + 1, top - 2, C_FUR); cv.rect(hx, top - 1, hx + 2, top - 1, C_FUR)
    cv.put(hx + 11, top - 3, C_FUR); cv.rect(hx + 10, top - 2, hx + 11, top - 2, C_FUR); cv.rect(hx + 9, top - 1, hx + 11, top - 1, C_FUR)
    cv.dt[(hx + 1, top - 2)] = C_LIGHT; cv.dt[(hx + 10, top - 2)] = C_LIGHT


def cat_face(cv, hx, top, mood="normal", blink=False):
    """기본 고양이 face() 그대로 — 코 없음, ω 입, 수염"""
    d = cv.dt
    ey = top + 4
    for ex in (hx + 3, hx + 8):
        if blink:
            d[(ex, ey + 1)] = C_EYE
            d[(ex - 1, ey + 1)] = shade(C_EYE, 0.72)
        elif mood == "happy":
            d[(ex - 1, ey + 1)] = C_EYE; d[(ex, ey)] = C_EYE; d[(ex + 1, ey + 1)] = C_EYE
        elif mood == "surprised":
            d[(ex, ey - 1)] = C_EYE; d[(ex, ey)] = C_EYE; d[(ex, ey + 1)] = C_EYE; d[(ex - 1, ey)] = C_EYE
            d[(ex - 1, ey - 1)] = SHINE; d[(ex - 1, ey + 1)] = C_EYE
        else:
            d[(ex, ey)] = C_EYE; d[(ex, ey + 1)] = C_EYE
    m = C_LIGHT
    if mood in ("talk", "surprised"):
        d[(hx + 4, top + 7)] = m; d[(hx + 7, top + 7)] = m; d[(hx + 5, top + 8)] = m; d[(hx + 6, top + 8)] = m
        d[(hx + 5, top + 7)] = (150, 60, 70, 255); d[(hx + 6, top + 7)] = (150, 60, 70, 255)
    else:
        d[(hx + 3, top + 7)] = m; d[(hx + 8, top + 7)] = m; d[(hx + 4, top + 8)] = m; d[(hx + 7, top + 8)] = m
        d[(hx + 5, top + 7)] = m; d[(hx + 6, top + 7)] = m
    for p in ((hx - 1, top + 6), (hx - 2, top + 6), (hx - 1, top + 7), (hx - 2, top + 8),
              (hx + 12, top + 6), (hx + 13, top + 6), (hx + 12, top + 7), (hx + 13, top + 8)):
        d[p] = C_WHISK


def witch_hat(cv, hx, top, sweep=0, flap=0):
    """고깔모자: 챙(머리 윗줄을 덮음) + 원뿔(꼭대기가 뒤로 sweep 칸) + 꺾여 뒤로 처진 끝 (flap = 펄럭)"""
    h = Cv(C_LINE)
    by = top                                      # 챙 아랫줄 = 머리 윗줄
    h.rect(hx - 2, by, hx + 13, by, HAT)
    h.rect(hx - 1, by - 1, hx + 12, by - 1, HAT)
    bx0, bx1 = hx + 2, hx + 9                     # 원뿔 밑변
    ax = hx + 6 - sweep                           # 꼭대기 (2칸, 1번 줄)
    h.poly([(bx0, by - 1), (bx1 + 1, by - 1), (ax + 2, 1), (ax, 1)], HAT)
    h.rect(ax, 1, ax + 1, 1, HAT)
    # 꺾인 끝: 꼭대기에서 위로 솟았다가 뒤(왼쪽)로 축 처짐, 끝에 별 방울 (flap = 펄럭)
    tip = [(ax + 1, 0), (ax, 0), (ax - 1, 0), (ax - 2, 0 + (flap > 0)), (ax - 3, 1 + (flap > 0)),
           (ax - 4, 2 + (flap > 0) - (flap < 0))]
    for (x, y) in tip:
        h.put(x, y, HAT)
    # 무늬: 띠 · 광택(왼쪽 면) · 그늘(오른쪽 면) · 챙 아랫면 그늘
    for x in range(bx0 - 1, bx1 + 3):
        if (x, by - 2) in h.px:
            h.dt[(x, by - 2)] = HAT_BAND
    for (x, y) in list(h.px):
        if y < by - 2:
            if (x - 1, y) not in h.px:
                h.dt[(x, y)] = HAT_HI
            elif (x + 1, y) not in h.px:
                h.dt[(x, y)] = HAT_DK
    for x in range(hx - 2, hx + 14):
        if (x, by) in h.px:
            h.dt[(x, by)] = HAT_DK
    h.dt[(hx - 1, by - 1)] = HAT_HI; h.dt[(hx, by - 1)] = HAT_HI; h.dt[(hx + 1, by - 1)] = HAT_HI
    h.dt[(ax + 1, by - 4)] = HAT_STAR                     # 별 장식
    h.dt[tip[-1]] = HAT_STAR                              # 끝 방울
    cv.overlay(h, edge=True)


def broom(cv, y, x0=11, x1=33, rise=0, flutter=0):
    """빗자루: 자루(앞이 rise 칸 들림) + 묶은 띠 + 지푸라기 다발 (결 · 들쭉날쭉 끝)"""
    cv.line_(x0, y, x1, y - rise, WOOD)
    cv.put(x1, y - rise - 1, WOOD)                             # 앞 끝 살짝 들린 손잡이
    for x in range(x0 + 2, x1, 3):
        yy = rnd(y - rise * (x - x0) / (x1 - x0))
        cv.dt[(x, yy)] = WOOD_HI
    bx = x0 - 2                                                # 묶은 띠 왼쪽 칸
    fan = [(bx + 0.5, y - 1.6), (bx + 0.5, y + 2.6), (bx - 7, y + 4.6 + flutter * 0.5),
           (bx - 8.2, y + 1.0), (bx - 7, y - 3.6 - flutter * 0.5)]
    straw = Cv(C_LINE)
    straw.poly(fan, STRAW)
    for k, off in enumerate((-3, -1.3, 0.4, 2.1, 3.6)):        # 결: 묶은 곳에서 뒤로 퍼지는 진한 줄
        straw.line_(bx - 1, y + 0.5 + off * 0.35, bx - 8, y + 0.5 + off * 1.15, STRAW_DK, to="dt")
    for (x, yy) in list(straw.px):
        if (x, yy - 1) not in straw.px:
            straw.dt[(x, yy)] = STRAW_HI
    xmin = min(x for x, _ in straw.px)
    for yy in range(y - 5, y + 6):                             # 들쭉날쭉 끝 (프레임마다 다르게)
        if (yy + flutter) % 2 == 0:
            straw.cut((xmin, yy))
    for p, c in straw.px.items():
        cv.px[p] = c
    cv.dt.update(straw.dt)
    cv.rect(bx, y - 2, bx + 1, y + 2, TIE)                     # 묶은 띠
    cv.dt[(bx, y - 2)] = HAT_HI
    cv.dt[(bx + 1, y + 2)] = HAT_DK


def star_fx(cv, x, y, size, a):
    if size >= 2:
        for (dx, dy) in ((0, -2), (0, -1), (-2, 0), (-1, 0), (1, 0), (2, 0), (0, 1), (0, 2)):
            cv.fx[(x + dx, y + dy)] = STAR + (a,)
        cv.fx[(x, y)] = STAR_CORE + (a,)
    elif size == 1:
        for (dx, dy) in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            cv.fx[(x + dx, y + dy)] = STAR + (a,)
        cv.fx[(x, y)] = STAR_CORE + (a,)
    else:
        cv.fx[(x, y)] = STAR + (a,)


def sparkles(cv, frame, n, fast=False):
    """빗자루 끝에서 나와 뒤로 흩어지는 별가루 (n 프레임 고리, 두 줄기 엇갈려)"""
    paths = ([(4, 13), (2, 11), (1, 8), (0, 6)], [(6, 11), (5, 8), (3, 6), (2, 4)])
    sizes = (2, 1, 0, 0)
    alphas = (255, 240, 210, 150)
    if fast:   # 빨리 날 땐 더 길게 흩날린다 (6칸 고리 — 어느 프레임이든 별이 하나는 보이게)
        paths = ([(3, 10), (1, 9), (0, 7), (0, 5), (1, 3), (0, 1)], [(7, 9), (5, 7), (4, 5), (3, 3), (2, 2), (1, 0)])
        sizes = (2, 1, 1, 0, 0, 0)
        alphas = (255, 245, 220, 200, 160, 110)
    for k, path in enumerate(paths):
        age = (frame + k * (n // 2)) % n
        if age < len(path):
            x, y = path[age]
            star_fx(cv, x, y, sizes[age], alphas[age])


def witch(mode, frame, mood="normal", blink=False):
    cv = Cv(C_LINE)
    hx, top = W_HX, W_TOP
    if mode in ("idle", "face"):
        bob, sweep, flap, flutter, rise, tail = 0, 1, 0, 0, 0, "up"
    elif mode == "walk":
        bob = (0, 0, 1, 1)[frame]
        sweep, flap, flutter = 2, (0, 1, 1, 0)[frame], frame % 2
        rise, tail = 0, ("up", "up2", "up", "up2")[frame]
    else:
        bob = (0, 1, 1, 0, 0, 1)[frame]
        sweep, flap, flutter = 3, (1, -1, 1, -1, 1, -1)[frame], frame % 2
        rise, tail = 1, ("back", "back2", "back", "back2", "back", "back2")[frame]
    by = 20                                                     # 자루 높이
    tails = {
        "up": [(12, 16), (10, 15), (9, 13), (9, 11), (10, 9), (12, 9)],
        "up2": [(12, 16), (10, 15), (9, 13), (8, 11), (9, 9), (11, 8)],
        "back": [(12, 16), (9, 15), (6, 14), (4, 13)],
        "back2": [(12, 16), (9, 15), (6, 15), (4, 15)],
    }[tail]
    cv.path(tails, C_FUR, w=2)
    # 먼 앞발 (자루 너머에서 앞쪽을 잡음)
    cv.line_(21, 15, 26, by - 1, C_FAR, w=2)
    # 몸통: 자루에 걸터앉은 둥근 몸
    cv.ellipse(15.5, 15.6, 5.0, 3.9, C_FUR)
    cv.rect(17, 13, 21, 18, C_FUR)
    # 빗자루 (몸 앞을 지나간다)
    broom(cv, by, rise=rise, flutter=flutter)
    # 가까운 뒷다리: 허벅지 + 자루 아래로 늘어진 다리
    cv.ellipse(15.0, 17.6, 3.1, 2.4, C_FUR)
    sw = {"idle": 0, "face": 0, "walk": (0, 1, 0, -1)[frame % 4], "run": -1}[mode]   # 늘어진 다리 대롱대롱
    cv.line_(15, 20, 16 + sw, 22, C_FUR, w=2)
    cv.rect(16 + sw, 23, 17 + sw, 23, C_FUR)
    # 가까운 앞발: 가슴에서 자루로 뻗어 꼭 잡음
    cv.line_(20, 15, 23, by - 1, C_FUR, w=2)
    cat_head(cv, hx, top)
    for (x, y) in list(cv.px):                                  # 윗선 광택 (머리·등·꼬리)
        if cv.px[(x, y)] == C_FUR and (x, y - 1) not in cv.px and (x, y) not in cv.dt:
            cv.dt[(x, y)] = C_RIM
    cv.dt[(23, by - 1)] = C_LIGHT; cv.dt[(24, by - 1)] = C_LIGHT   # 앞발 발바닥 (자루 위)
    cv.dt[(16 + sw, 23)] = C_LIGHT; cv.dt[(17 + sw, 23)] = C_LIGHT     # 뒷발
    cv.dt[(16, 18)] = C_FAR; cv.dt[(17, 19)] = C_FAR               # 허벅지 결
    face = mood if mode in ("idle", "face") else ("happy" if (mode == "run" and frame in (1, 4)) else "normal")
    cat_face(cv, hx, top, mood=face, blink=blink)
    for p in ((hx - 1, top + 7), (hx, top + 8), (hx + 1, top + 9), (hx + 2, top + 9), (hx + 2, top + 10)):
        cv.dt[p] = C_COLLAR                                     # 주황 목걸이 + 방울
    cv.dt[(hx + 3, top + 10)] = C_BELL; cv.dt[(hx + 3, top + 11)] = C_BELL_DK
    witch_hat(cv, hx, top, sweep=sweep, flap=flap)
    sparkles(cv, 0 if mode in ("idle", "face") else frame, 6 if mode == "run" else 4, fast=(mode == "run"))
    if mode == "run":
        speed_lines(cv, frame, [(4, 3, 2), (22, 3, 6)], 10, (200, 190, 228, 255))
    return cv.image(dy=bob)


# ══════════════════════════════════════════════════════════════════════
def sheets():
    out = {}
    for name, fn, nrun in (("ghost", ghost, 6), ("pumpkin", pumpkin, 6), ("witch", witch, 6)):
        out[name] = {
            "walk": [fn("walk", i) for i in range(4)],
            "run": [fn("run", i) for i in range(nrun)],
            "idle": [fn("idle", 0), fn("idle", 1, blink=True)],
            "face": [fn("face", 0, "talk"), fn("face", 0, "surprised"), fn("face", 0, "happy")],
        }
    return out


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
    S, G, LBL = 6, 10, 90
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
            x = LBL + i * (W * S + G)
            dr.rectangle([x - 1, y - 1, x + W * S, y + H * S], outline=(232, 232, 236, 255))
            prev.alpha_composite(f.resize((W * S, H * S), Image.NEAREST), (x, y))
    os.makedirs(os.path.dirname(os.path.abspath(preview)), exist_ok=True)
    prev.save(preview)
    print("미리보기:", preview)


if __name__ == "__main__":
    main(*sys.argv[1:3])
