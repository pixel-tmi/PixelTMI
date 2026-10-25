"""
Pixel TMI 공룡 5종 — 티라노(trex) · 트리케라톱스(trike) · 익룡(ptero) · 스테고사우루스(stego) · 브라키오사우루스(brachio).
결: 고양이·동물 오마주와 같은 결 — 한 가지 몸 색 + 같은 계열 진한 외곽선(자동 1칸), 큰 머리 꼬마 비율,
    2×2 점 눈 + 반짝, 무섭지 않게 웃는 얼굴. 그림을 베끼지 않고 도형을 조립한 뒤 외곽선을 자동으로 두른다.
한 프레임 = 가로 34 × 세로 24칸 (앱 아이콘 24도트와 1:1), 오른쪽을 본다. 시트는 왼쪽→오른쪽 한 줄.

사용: python 공룡_캐릭터.py <출력 폴더> [기본 미리보기.png] [행동 미리보기.png]
출력 (trex · trike · ptero · stego · brachio):
  <id>_walk.png  걷기 4프레임 (익룡은 날갯짓 4프레임)
  <id>_run.png   성격 있는 달리기 6프레임 (티라노 쿵쿵 앞으로 숙인 질주 · 트리케라톱스 뿔 돌진 · 익룡 빠른 날갯짓 · 스테고 뒤뚱뒤뚱 · 브라키오 목 끄덕 느린 구보)
  <id>_idle.png  가만히 2프레임 (0 가만히/앉기 · 1 눈 깜빡)
  <id>_face.png  표정 3프레임 (말하기 · 놀람 · 웃음) — idle 0번과 같은 자세 (앱이 말할 때 둘을 번갈아 보여 줘도 몸이 안 튄다)
  <id>_climb.png 벽 타기 3프레임 (걷는 넷만): 등판이 보이는 大자 2장 + 철푸덕 1장 — cat_climb.png와 같은 배치.
                 이 시트만 프레임이 34×32 (102×32): 몸은 위 24칸 그대로, 아래 8칸에 꼬리 끝이 가늘게 마무리된다
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 34, 24
CH = 32                               # 벽 타기 시트만 세로 32칸: 위 24칸은 몸(옆모습 시트와 같은 자리), 아래 8칸은 늘어진 꼬리 끝
CLEAR = (0, 0, 0, 0)
SHINE = (255, 255, 255, 255)
SPEED = (196, 204, 218, 255)          # 속도선
DUST = (226, 214, 190, 215)           # 흙먼지 (반투명 — 흰 바탕·어두운 바탕 둘 다)
DUST_EDGE = (176, 160, 134, 190)


def rnd(v):
    return int(math.floor(v + 0.5))


class Pal:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# ── 캔버스 ────────────────────────────────────────────────────────────
class Cv:
    """도트 캔버스. px = 몸(자동 외곽선) · dt = 무늬(몸 위 덧칠, 외곽선 없음) · fx = 효과(먼지·속도선, 몸 뒤, 외곽선 없음)"""

    def __init__(self, P):
        self.P = P
        self.px, self.dt, self.fx = {}, {}, {}
        self.top = {}                  # 맨 앞 효과 (별·땀·음파 — 몸 위에, 외곽선 없음)
        self.tail = set()              # 24칸 아래로 내려가도 남길 칸 (벽 타기 꼬리)

    def _L(self, to):
        return getattr(self, to)

    def rect(self, x0, y0, x1, y1, c=None, to="px"):
        c = c or self.P.BODY
        L = self._L(to)
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                L[(x, y)] = c

    def put(self, x, y, c=None, to="px"):
        self._L(to)[(x, y)] = c or self.P.BODY

    def cut(self, *pts):
        for p in pts:
            self.px.pop(p, None)
            self.dt.pop(p, None)

    def ellipse(self, cx, cy, rx, ry, c=None, to="px", keep=None):
        c = c or self.P.BODY
        L = self._L(to)
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 and (keep is None or keep(x, y)):
                    L[(x, y)] = c

    def oval(self, cx, cy, rx, ry, ang, c=None, to="px"):
        """기울어진 타원 (ang 도, +면 시계 방향 = 오른쪽이 내려감)"""
        c = c or self.P.BODY
        L = self._L(to)
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        R = max(rx, ry)
        for y in range(int(cy - R) - 1, int(cy + R) + 2):
            for x in range(int(cx - R) - 1, int(cx + R) + 2):
                u = (x - cx) * ca + (y - cy) * sa
                v = -(x - cx) * sa + (y - cy) * ca
                if (u / rx) ** 2 + (v / ry) ** 2 <= 1.0:
                    L[(x, y)] = c

    def capsule(self, x0, y0, x1, y1, r0, r1=None, c=None, to="px", keep=None):
        """두 점을 잇는 둥근 막대 (굵기가 r0 → r1 로 가늘어짐) — 꼬리·다리·목"""
        r1 = r0 if r1 is None else r1
        c = c or self.P.BODY
        L = self._L(to)
        dx, dy = x1 - x0, y1 - y0
        ll = dx * dx + dy * dy
        R = max(r0, r1)
        for y in range(int(min(y0, y1) - R) - 1, int(max(y0, y1) + R) + 2):
            for x in range(int(min(x0, x1) - R) - 1, int(max(x0, x1) + R) + 2):
                t = 0.0 if ll == 0 else max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / ll))
                if math.hypot(x - (x0 + dx * t), y - (y0 + dy * t)) <= r0 + (r1 - r0) * t and (keep is None or keep(x, y)):
                    L[(x, y)] = c

    def path(self, pts, rs, c=None, to="px"):
        for i in range(len(pts) - 1):
            self.capsule(*pts[i], *pts[i + 1], rs[i], rs[i + 1], c, to)

    def poly(self, pts, c=None, to="px"):
        c = c or self.P.BODY
        L = self._L(to)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            for x in range(int(min(xs)) - 1, int(max(xs)) + 2):
                inside = False
                j = len(pts) - 1
                for i in range(len(pts)):
                    (xi, yi), (xj, yj) = pts[i], pts[j]
                    if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                        inside = not inside
                    j = i
                if inside:
                    L[(x, y)] = c

    def line(self, x0, y0, x1, y1, c, to="dt"):
        L = self._L(to)
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(int(n) + 1):
            L[(rnd(x0 + (x1 - x0) * i / n), rnd(y0 + (y1 - y0) * i / n))] = c

    def art(self, x0, y0, rows, pal, to="px"):
        """글자 그림: pal 의 글자 → 색, '.' 은 비움"""
        L = self._L(to)
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch in pal:
                    L[(x0 + dx, y0 + dy)] = pal[ch]

    def overlay(self, o, edge=True):
        """o 를 몸 위에 얹는다 (가까운 다리·날개). 맞닿은 몸 쪽에 외곽선 1칸을 그어 따로 보이게"""
        region = set(o.px)
        for p in region:
            self.dt.pop(p, None)
        self.px.update(o.px)
        self.dt.update(o.dt)
        self.fx.update(o.fx)
        self.top.update(o.top)
        if edge:
            for (x, y) in region:
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if n not in region and n in self.px:
                        self.dt[n] = self.P.LINE

    def paste(self, o, dx=0, dy=0, tilt=0.0, cx=17):
        """o 를 통째로 옮겨 붙인다. tilt = 앞(오른쪽)이 내려가게 세로줄마다 밀기 (앞으로 숙이기)"""
        for name in ("px", "dt", "fx", "top"):
            src, dst = getattr(o, name), getattr(self, name)
            for (x, y), c in src.items():
                dst[(x + dx, y + dy + rnd((x - cx) * tilt))] = c

    def finish(self):
        """몸 색 칸의 윗선은 밝게, 아랫선은 어둡게 (작은 화면에서도 덩어리가 입체로)"""
        P = self.P
        for (x, y), c in list(self.px.items()):
            if c != P.BODY or (x, y) in self.dt:
                continue
            if (x, y - 1) not in self.px:
                self.dt[(x, y)] = P.HI
            elif (x, y + 1) not in self.px:
                self.dt[(x, y)] = P.DK

    def image(self, dx=0, dy=0, tilt=0.0, cx=17, h=H):
        """h = 캔버스 세로. 24보다 크면(벽 타기) 24칸 아래로 내려간 몸 칸은 자르고 꼬리(tail) 칸만 남긴 뒤 외곽선으로 마감"""
        tf = lambda d: {(x + dx, y + dy + rnd((x - cx) * tilt)): c for (x, y), c in d.items()}
        px, dt, fx = tf(self.px), tf(self.dt), tf(self.fx)
        if h > H:
            px = {p: c for p, c in px.items() if p[1] < H or p in self.tail}
            dt = {p: c for p, c in dt.items() if p[1] < H or p in px}
        im = Image.new("RGBA", (W, h), CLEAR)

        def blend(x, y, c):
            if not (0 <= x < W and 0 <= y < h):
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
        for (x, y) in px:
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + ddx, y + ddy)
                if n not in px and 0 <= n[0] < W and 0 <= n[1] < h:
                    im.putpixel(n, self.P.LINE)
        for (x, y), c in px.items():
            blend(x, y, c)
        for (x, y), c in dt.items():
            blend(x, y, c)
        for (x, y), c in tf(self.top).items():
            blend(x, y, c)
        return im


def puff(cv, cx, cy, r, a=215):
    """흙먼지 한 덩이 (밝은 속 + 진한 테)"""
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            d = math.hypot(x - cx, y - cy)
            if d <= r - 0.7:
                cv.fx[(x, y)] = DUST[:3] + (a,)
            elif d <= r + 0.3:
                cv.fx[(x, y)] = DUST_EDGE[:3] + (min(255, a - 20),)


def speed_lines(cv, frame, lines, xmax, step=3, loop=9):
    """뒤로 흘러가는 속도선. lines = [(y, 길이, 위상)]"""
    for y, ln, ph in lines:
        head = xmax - ((frame * step + ph) % loop)
        for x in range(head - ln + 1, head + 1):
            if 0 <= x <= xmax:
                cv.fx[(x, y)] = SPEED


def eye2(cv, ex, ey, mood="normal", blink=False):
    """2×2 점 눈 + 왼쪽 위 반짝 (용과 같은 문법). (ex, ey) = 눈 왼쪽 위 칸"""
    P = cv.P
    E = P.EYE
    d = cv.dt
    if blink:
        d[(ex - 1, ey + 1)] = E; d[(ex, ey + 1)] = E; d[(ex + 1, ey + 1)] = E
    elif mood == "happy":       # ^
        d[(ex - 1, ey + 1)] = E; d[(ex, ey)] = E; d[(ex + 1, ey)] = E; d[(ex + 2, ey + 1)] = E
    elif mood == "surprised":   # 위로 한 칸 더 커진 동그란 눈 + 반짝 두 점
        d[(ex, ey - 1)] = SHINE; d[(ex + 1, ey - 1)] = E
        d[(ex, ey)] = E; d[(ex + 1, ey)] = E
        d[(ex, ey + 1)] = E; d[(ex + 1, ey + 1)] = SHINE
    else:
        d[(ex, ey)] = SHINE; d[(ex + 1, ey)] = E; d[(ex, ey + 1)] = E; d[(ex + 1, ey + 1)] = E


def stump(cv, top, foot, col, r=1.45, thigh=None):
    """굵은 기둥 다리 + 흰 발톱 두 개 (트리케라톱스·스테고·브라키오). foot = (발 x, 들림). thigh = (rx, ry) 허벅지"""
    P = cv.P
    tx, ty = top
    fx, lift = foot
    fy = 22 - lift
    if thigh:
        cv.ellipse(tx, ty - 1.2, thigh[0], thigh[1], col)
    cv.capsule(tx, ty, fx, fy - 1, r, r - 0.1, col)
    cv.rect(rnd(fx) - 1, fy - 1, rnd(fx) + 1, fy, col)
    cv.dt[(rnd(fx) + 1, fy)] = P.CLAW
    cv.dt[(rnd(fx) - 1, fy)] = P.CLAW


def hang_tail(cv, pts, rs, deco=None):
    """벽 타기 꼬리: 몸 뒤로 늘어져 24칸 아래까지 가늘게 내려오고 끝이 옆으로 살짝 휜다 (deco = 꼬리에 붙는 가시 등)"""
    t = Cv(cv.P)
    if deco:                                   # 가시 등은 먼저 깔고 꼬리를 위에 (가시가 꼬리 뒤에서 삐죽)
        deco(t)
    t.path(pts, rs)
    cv.px.update(t.px)
    cv.dt.update(t.dt)
    cv.tail |= set(t.px)


def climb_feet(cv, ends):
    """벽에 붙은 손발 끝: 발톱 밝게"""
    for e in ends:
        cv.dt[e] = cv.P.CLAW


# ══════════════════════════════════════════════════════════════════════
# 티라노: 통통한 초록 몸 + 크림 배, 큰 머리·짧은 팔, 이빨 보이게 씩 웃음
# ══════════════════════════════════════════════════════════════════════
TREX = Pal(
    LINE=(34, 82, 44, 255),
    BODY=(108, 192, 86, 255),
    HI=(166, 228, 124, 255),
    DK=(80, 158, 70, 255),
    FAR=(84, 158, 70, 255),
    SPOT=(78, 152, 66, 255),
    BELLY=(250, 238, 172, 255),
    CLAW=(252, 246, 222, 255),
    TOOTH=(255, 255, 255, 255),
    MOUTH=(130, 44, 56, 255),
    TONGUE=(242, 116, 130, 255),
    EYE=(24, 30, 28, 255),
    BLUSH=(252, 150, 160, 255),
    NOSE=(52, 110, 58, 255),
    MLINE=(40, 92, 50, 255),
)

TREX_HEAD = [          # 15 × 10, 오른쪽이 주둥이 (b = 턱 밑 크림)
    "....hhhhhhh....",
    "..hhgggggggghh.",
    ".hgggggggggggg.",
    "gggggggggggggg.",
    "ggggggggggggggg",
    "ggggggggggggggg",
    "ggggggggggggggg",
    "gggggggggggggg.",
    "bbbbgggggggg...",
    ".bbbbbbbbb.....",
]
TREX_HEAD_OPEN = TREX_HEAD[:6] + [     # 아래턱이 2칸 내려간 입
    "gggggmmmmmmmmmg",
    "ggggggmmmmmmmm.",
    "gggggggmmmmmm..",
    "ggggggggggggg..",
    "bbbbgggggggg...",
    ".bbbbbbbbb.....",
]


def trex_head(cv, x, y, mood="normal", blink=False, open_=False):
    P = cv.P
    cv.art(x, y, TREX_HEAD_OPEN if open_ else TREX_HEAD, {"g": P.BODY, "h": P.HI, "b": P.BELLY, "m": P.MOUTH})
    d = cv.dt
    eye2(cv, x + 8, y + 2, mood, blink)
    d[(x + 13, y + 3)] = P.NOSE                                    # 콧구멍
    d[(x + 6, y + 5)] = P.BLUSH; d[(x + 7, y + 5)] = P.BLUSH       # 볼터치
    d[(x + 4, y + 5)] = P.MLINE                                    # 입꼬리 (씩)
    if open_:
        for k in (6, 8, 10, 12):                                   # 윗니 (아래로)
            d[(x + k, y + 6)] = P.TOOTH
        for k in range(8, 12):                                     # 혀
            d[(x + k, y + 8)] = P.TONGUE
        d[(x + 9, y + 7)] = P.TONGUE; d[(x + 10, y + 7)] = P.TONGUE
    else:
        for k in range(5, 15):
            d[(x + k, y + 6)] = P.MLINE
        for k in (6, 8, 10, 12):                                   # 이빨 (입선 아래로 삐죽)
            d[(x + k, y + 7)] = P.TOOTH


def trex_leg(cv, hip, foot, col, thigh=True):
    """통통한 허벅지 + 굵은 정강이 + 앞으로 뻗은 발 (발톱 밝게). foot = (발 x, 들림)"""
    P = cv.P
    hx, hy = hip
    fx, lift = foot
    fy = 22 - lift
    if thigh:
        cv.ellipse(hx, hy, 2.9, 3.3, col)
    cv.capsule(hx + 0.3, hy + 1.5, fx + 0.5, fy - 1.3, 1.3, 1.05, col)
    cv.rect(fx - 1, fy - 1, fx + 2, fy, col)
    cv.put(fx + 3, fy, col)
    cv.dt[(fx + 3, fy)] = P.CLAW
    cv.dt[(fx + 1, fy)] = P.CLAW if lift == 0 else col


def trex_upper(P, sway=0.0, mood="normal", blink=False, open_=False):
    u = Cv(P)
    u.path([(11, 13.5), (6.5, 12.2), (1.8, 9.2 + sway)], [3.1, 2.0, 0.85])     # 꼬리
    u.ellipse(15.5, 13.8, 6.6, 4.8)                                             # 몸통
    u.ellipse(20.6, 11.6, 3.3, 3.6)                                             # 목·가슴
    trex_head(u, 18, 1, mood, blink, open_)
    u.ellipse(20.2, 15.4, 3.6, 3.7, P.BELLY, to="dt", keep=lambda x, y: (x, y) in u.px and y >= 12)
    for x, y in ((9, 10), (10, 10), (13, 9), (14, 9), (17, 9), (5, 11)):        # 등 무늬
        if (x, y) in u.px and (x, y - 1) in u.px:
            u.dt[(x, y)] = P.SPOT
    return u


def trex_frame(near, far, bob=0, sway=0.0, arm=0, tilt=0.0, mood="normal", blink=False, open_=False, dust=()):
    P = TREX
    cv = Cv(P)
    hy = 15.5 + bob
    trex_leg(cv, (16.2, hy), far, P.FAR, thigh=False)
    cv.paste(trex_upper(P, sway, mood, blink, open_), 0, bob, tilt, 15)
    s = Cv(P)
    trex_leg(s, (13.4, hy), near, P.BODY)
    cv.overlay(s)
    a = Cv(P)                                                     # 짧은 팔
    ay = 13.2 + bob + rnd((23 - 15) * tilt)
    a.capsule(22.4, ay, 24.4, ay + 0.8 + arm, 0.8, 0.7)
    a.dt[(25, rnd(ay + 0.8 + arm))] = P.CLAW
    cv.overlay(a)
    for (x, y, r, al) in dust:
        puff(cv, x, y, r, al)
    cv.finish()
    return cv.image()


def trex_walk(i):
    near, far = [((16, 0), (12, 0)), ((13, 0), (15, 2)), ((11, 0), (18, 0)), ((14, 2), (15, 0))][i]
    return trex_frame(near, far, bob=(0, -1, 0, -1)[i], sway=(0, 1, 0, -1)[i], arm=(0, 1, 0, 1)[i])


def trex_run(i):
    """쿵쿵 질주 6장: 앞으로 숙인 몸, 큰 보폭, 발 디딜 때마다 흙먼지 · 꼬리는 위아래로 휙휙 · 입 벌려 신남"""
    near, far = [((18, 0), (9, 2)), ((14, 0), (12, 4)), ((10, 1), (17, 3)),
                 ((9, 2), (19, 0)), ((12, 4), (15, 0)), ((17, 3), (11, 1))][i]
    dust = []
    if i in (0, 3):
        fx = near[0] if i == 0 else far[0]
        dust = [(fx - 2, 21.5, 1.4, 225), (fx + 5, 21.5, 1.2, 205)]
    elif i in (1, 4):
        fx = (near[0] if i == 1 else far[0]) - 3
        dust = [(fx - 2, 20.6, 1.9, 150)]
    return trex_frame(near, far, bob=(1, 0, 0, 1, 0, 0)[i], sway=(-2, 0, 2, -2, 0, 2)[i], arm=(0, 1, 0, 0, 1, 0)[i],   # 머리 높이는 1칸씩만
                      tilt=0.10, open_=True, dust=dust)


def trex_sit(mood="normal", blink=False):
    """앉기: 꼬리를 바닥에 깔고 엉덩이로 앉아 고개를 든다"""
    P = TREX
    cv = Cv(P)
    open_ = mood in ("talk", "surprised", "happy")
    cv.path([(11, 19.5), (6, 20.8), (1.2, 21.6)], [2.8, 1.8, 0.8])            # 바닥에 깐 꼬리
    cv.rect(19, 21, 23, 22, P.FAR); cv.dt[(23, 22)] = P.CLAW                  # 먼 발
    cv.ellipse(15.8, 15.8, 5.6, 5.0)                                          # 몸통 (세움)
    cv.ellipse(18.6, 11.4, 3.6, 4.0)                                          # 가슴·목
    trex_head(cv, 18, 1, mood, blink, open_)
    cv.ellipse(19.6, 15.0, 3.0, 4.6, P.BELLY, to="dt", keep=lambda x, y: (x, y) in cv.px and y >= 11)
    for x, y in ((11, 13), (12, 12), (14, 11)):
        if (x, y) in cv.px:
            cv.dt[(x, y)] = P.SPOT
    s = Cv(P)                                                                 # 허벅지 + 납작한 발
    s.ellipse(14.2, 18.2, 3.6, 3.2)
    s.rect(15, 21, 20, 22)
    s.put(21, 22)
    s.dt[(21, 22)] = P.CLAW; s.dt[(19, 22)] = P.CLAW
    cv.overlay(s)
    a = Cv(P)                                                                 # 짧은 팔 (가슴 앞에 모음)
    a.capsule(21.6, 13.2, 23.6, 14.2, 0.8, 0.7)
    a.dt[(24, 14)] = P.CLAW
    cv.overlay(a)
    cv.finish()
    return cv.image()


def trex_climb(i):
    """벽 타기 = 위에서 내려다본 티라노가 위쪽으로 걸어 올라감 (고양이 大자 등판과 다르게).
    머리는 위(주둥이가 위), 짧은 팔, 큰 뒷다리가 번갈아 디딤, 꼬리는 아래 24~31칸까지 늘어짐.
    0 = 왼발 앞 · 1 = 오른발 앞 · 2 = 두 발 다 디딘 착지 자세. 발자국은 앱이 그린다"""
    P = TREX
    cv = Cv(P)
    feet = [((8.6, 12.6), (25.2, 21.4)), ((8.8, 21.4), (25.4, 12.6)), ((8.2, 18.8), (25.8, 18.8))][i]
    arm = [(-1, 1), (1, -1), (0, 0)][i]                       # 팔은 다리와 반대로 살짝
    tsw = (1, -1, 0)[i]                                       # 꼬리는 디딘 발 반대쪽으로 살랑
    hang_tail(cv, [(17, 19.0), (17 + tsw * 0.8, 23.6), (17 + tsw * 1.8, 27.4), (17 + tsw * 2.4, 30.4)],
              [2.8, 2.0, 1.2, 0.5])
    cv.ellipse(17, 14.8, 4.4, 5.6)                            # 몸통 (위에서 본 통통한 타원)
    cv.rect(15, 8, 19, 10)                                    # 목
    cv.ellipse(17, 6.4, 5.0, 2.9)                             # 머리 뒤 (턱 근육으로 넓게 — 큰 머리)
    cv.ellipse(17, 4.0, 3.7, 3.7)                             # 주둥이 (위로 길쭉)
    for x, y in ((17, 9), (16, 12), (18, 14), (16, 16), (18, 18), (17 + tsw, 23), (17 + tsw * 2, 26)):
        cv.dt[(x, y)] = P.SPOT                                # 등 무늬
    for (fx, fy), hx, sd in zip(feet, (12.6, 21.4), (-1, 1)):  # 뒷다리: 허벅지 → 옆으로 → 발 (발가락 셋이 위로)
        s = Cv(P)
        s.ellipse(hx, 17.8, 2.2, 3.0)
        s.capsule(hx + sd * 1.2, 17.6, fx, fy, 1.45, 1.25)
        s.ellipse(fx, fy, 1.6, 1.3)
        for tx, ty in ((fx - 1.2, fy - 1.9), (fx, fy - 2.4), (fx + 1.2, fy - 1.9)):
            s.put(rnd(tx), rnd(ty))
            s.dt[(rnd(tx), rnd(ty))] = P.CLAW
        cv.overlay(s)
    for (sx, sy), (ex, ey), d in zip(((13.2, 11.2), (20.8, 11.2)), ((10.0, 9.6), (24.0, 9.6)), arm):   # 짧은 팔
        s = Cv(P)
        s.capsule(sx, sy, ex, ey + d, 0.85, 0.7)
        s.dt[(rnd(ex), rnd(ey + d))] = P.CLAW
        cv.overlay(s)
    cv.finish()
    for x in (13, 21):                                         # 눈 (머리 양옆, 마지막에 또렷하게)
        cv.dt[(x, 5)] = P.EYE
        cv.dt[(x, 4)] = SHINE
    cv.dt[(16, 1)] = P.NOSE; cv.dt[(18, 1)] = P.NOSE          # 콧구멍
    return cv.image(h=CH)


# ══════════════════════════════════════════════════════════════════════
# 트리케라톱스: 청록 몸 + 산호색 프릴(노란 점 테두리) + 상아색 뿔 세 개, 튼튼한 네 다리
# ══════════════════════════════════════════════════════════════════════
TRIKE = Pal(
    LINE=(22, 70, 96, 255),
    BODY=(76, 172, 204, 255),
    HI=(138, 212, 236, 255),
    DK=(54, 138, 176, 255),
    FAR=(58, 144, 180, 255),
    BELLY=(206, 240, 246, 255),
    FRILL=(246, 132, 118, 255),
    FRILL_HI=(255, 178, 152, 255),
    FRILL_DK=(214, 98, 92, 255),
    RIM=(255, 228, 140, 255),
    HORN=(252, 244, 214, 255),
    HORN_DK=(206, 192, 150, 255),
    BEAK=(244, 232, 196, 255),
    BEAK_DK=(204, 186, 140, 255),
    CLAW=(240, 248, 250, 255),
    EYE=(22, 30, 40, 255),
    BLUSH=(252, 150, 160, 255),
    MOUTH=(30, 82, 108, 255),
    MOUTH_IN=(150, 52, 70, 255),
)

TRIKE_HEAD = [     # 14 × 12 — H 가까운 이마 뿔 · D 먼 이마 뿔 · N 코뿔 · k 부리 · c 볼·턱
    "........D..H..",
    ".......DD.HH..",
    "......DD.HH...",
    ".....DD.HH....",
    "..ggDDgHHgg.N.",
    ".gggggggggggN.",
    "gggggggggggNN.",
    "gggggggggggggk",
    "ggggggggggkkkk",
    "cccccccccgkkk.",
    ".cccccccckk...",
    "..cccccc......",
]


def trike_frill(cv, cx, cy):
    """머리 뒤 반달 프릴: 산호색 + 가장자리 노란 점 + 안쪽 밝은 무늬"""
    P = cv.P
    rx, ry = 5.6, 7.0
    cv.ellipse(cx, cy, rx, ry, P.FRILL, keep=lambda x, y: x <= cx + 2.5)
    for k in range(7):                                       # 테두리 점 (위 → 뒤 → 아래)
        a = math.radians(-80 - k * 25)
        x, y = rnd(cx + (rx - 1.1) * math.cos(a)), rnd(cy + (ry - 1.1) * math.sin(a))
        if (x, y) in cv.px:
            cv.dt[(x, y)] = P.RIM
    cv.ellipse(cx + 0.5, cy + 0.3, 2.6, 3.6, P.FRILL_HI, to="dt", keep=lambda x, y: (x, y) in cv.px and x <= cx + 1)


def trike_head(cv, hx, hy, mood="normal", blink=False, eye=True):
    """옆얼굴 도트 그림 (hx, hy = 왼쪽 위). 머리는 프릴 위에 얹고 경계선"""
    P = cv.P
    h = Cv(P)
    h.art(hx, hy, TRIKE_HEAD, {"g": P.BODY, "c": P.BELLY, "H": P.HORN, "D": P.HORN_DK, "N": P.HORN, "k": P.BEAK})
    d = h.dt
    for (x, y), c in list(h.px.items()):                     # 부리 아랫면 그늘
        if c == P.BEAK and (x, y + 1) not in h.px:
            d[(x, y)] = P.BEAK_DK
    if eye:
        eye2(h, hx + 5, hy + 5, mood, blink)
    d[(hx + 3, hy + 8)] = P.BLUSH; d[(hx + 4, hy + 8)] = P.BLUSH
    if mood in ("talk", "surprised"):                         # 부리를 벌림
        for p in ((hx + 10, hy + 9), (hx + 11, hy + 9), (hx + 9, hy + 9), (hx + 10, hy + 10)):
            d[p] = P.MOUTH_IN
        d[(hx + 8, hy + 9)] = P.MOUTH
        if mood == "surprised":
            d[(hx + 11, hy + 9)] = P.BEAK_DK
    elif mood == "happy":
        for p in ((hx + 6, hy + 8), (hx + 7, hy + 9), (hx + 8, hy + 9), (hx + 9, hy + 9)):
            d[p] = P.MOUTH
        d[(hx + 10, hy + 9)] = P.MOUTH_IN
    else:
        for p in ((hx + 7, hy + 9), (hx + 8, hy + 9), (hx + 9, hy + 9)):
            d[p] = P.MOUTH
    cv.overlay(h)


def trike_frame(legs, bob=0, head_dy=0, tilt=0.0, sway=0, mood="normal", blink=False, dust=()):
    """legs = (가까운 뒷발, 가까운 앞발, 먼 뒷발, 먼 앞발) 각각 (발 x, 들림)"""
    P = TRIKE
    cv = Cv(P)
    nh, nf, fh, ff = legs
    ly = 17 + bob
    stump(cv, (11, ly), fh, P.FAR, 1.5)
    stump(cv, (20.2, ly), ff, P.FAR, 1.5)
    u = Cv(P)
    u.path([(7, 14.5), (3.2, 15.8 + sway * 0.5), (0.6, 16.6 + sway)], [2.3, 1.3, 0.6])   # 짧은 꼬리
    u.ellipse(12.8, 14.6, 8.2, 5.0)                                                    # 통통한 몸
    u.ellipse(12.6, 17.8, 5.5, 1.5, P.BELLY, to="dt", keep=lambda x, y: (x, y) in u.px and (x, y + 1) in u.px)
    trike_frill(u, 19.4, 8.6 + head_dy)
    trike_head(u, 19, 2 + head_dy, mood, blink)
    cv.paste(u, 0, bob, tilt, 15)
    s = Cv(P)
    stump(s, (8.4, ly), nh, P.BODY, 1.5, thigh=(3.0, 3.2))
    cv.overlay(s)
    s = Cv(P)
    stump(s, (17.8, ly), nf, P.BODY, 1.5)
    cv.overlay(s)
    for (x, y, r, al) in dust:
        puff(cv, x, y, r, al)
    cv.finish()
    return cv.image()


def trike_walk(i):
    A = [(2, 0), (0, 0), (-2, 0), (0, 1)][i]           # 가까운 뒷발 + 먼 앞발 (대각선 짝)
    B = [(-2, 0), (0, 1), (2, 0), (0, 0)][i]           # 가까운 앞발 + 먼 뒷발
    legs = ((8.4 + A[0], A[1]), (17.8 + B[0], B[1]), (11 + B[0], B[1]), (20.2 + A[0], A[1]))
    return trike_frame(legs, bob=(0, -1, 0, -1)[i], sway=(0, 1, 0, -1)[i])


def trike_run(i):
    """뿔 돌진 6장: 고개를 숙여 뿔을 앞으로, 앞다리 쭉 뻗고 뒷다리로 박차는 통통 바운드 · 뒤로 흙먼지"""
    legs = [
        ((5, 0), (21, 2), (8, 1), (23, 1)),        # 0 뒷발 박차고 앞발 뻗음
        ((7, 2), (20, 0), (10, 3), (22, 0)),       # 1 앞발 착지
        ((10, 3), (17, 0), (13, 2), (19, 0)),      # 2 앞발 지탱, 뒷발 당겨옴 (몸 낮게)
        ((12, 0), (15, 1), (14, 0), (17, 2)),      # 3 뒷발 착지, 앞발 뒤로
        ((10, 0), (18, 3), (12, 0), (20, 3)),      # 4 뒷발 지탱, 앞발 들어 올림
        ((7, 0), (21, 3), (9, 1), (23, 2)),        # 5 뒷발 밀기, 앞발 앞으로
    ][i]
    dust = []
    if i in (0, 5):
        dust = [(3, 21.0, 1.6, 205), (0.5, 19.8, 1.2, 140)]
    elif i == 3:
        dust = [(9, 21.3, 1.3, 205)]
    elif i in (1, 4):
        dust = [(1.5, 20.0, 2.0, 125)]
    return trike_frame(legs, bob=(-1, 0, 1, 0, -1, -1)[i], head_dy=2, tilt=0.06, sway=(1, 0, -1, 0, 1, 0)[i], dust=dust)


def trike_stand(mood="normal", blink=False):
    return trike_frame(((8.4, 0), (17.8, 0), (11, 0), (20.2, 0)), mood=mood, blink=blink)


def trike_climb(i):
    """벽 타기 (등판 大자): 뒤에서 보면 커다란 프릴 부채가 위에 · 굵은 네 다리를 쫙"""
    P = TRIKE
    cv = Cv(P)
    arms = [((4, 9), (29, 14)), ((4, 14), (29, 9)), ((3, 11), (30, 11))][i]
    legs = [((8, 23), (26, 18)), ((8, 18), (26, 23)), ((6, 23), (28, 23))][i]
    tsw = (1, -1, 0)[i]
    d = 1 if tsw >= 0 else -1
    hang_tail(cv, [(17, 18), (17 + tsw * 0.7, 21.6), (17 + tsw * 1.3, 24.8), (17 + tsw * 1.6 + d * 1.0, 27.2)],
              [2.2, 1.7, 1.1, 0.45])                                         # 짧은 꼬리
    for (sx, sy), end in zip(((13, 17.5), (21, 17.5)), legs):
        cv.capsule(sx, sy, end[0], end[1], 1.75, 1.5)
    for (sx, sy), end in zip(((12.5, 12.5), (21.5, 12.5)), arms):
        cv.capsule(sx, sy, end[0], end[1], 1.6, 1.4)
    cv.ellipse(17, 14.8, 6.0, 5.8)                                             # 등
    f = Cv(P)                                                                  # 프릴 부채 (뒤에서)
    f.ellipse(17, 9.0, 9.2, 8.0, P.FRILL, keep=lambda x, y: y <= 10)
    for k in range(9):
        a = math.radians(-180 + k * 22.5)
        x, y = rnd(17 + 8.0 * math.cos(a)), rnd(9.0 + 6.9 * math.sin(a))
        if (x, y) in f.px:
            f.dt[(x, y)] = P.RIM
    f.ellipse(17, 10.0, 5.0, 4.8, P.FRILL_HI, to="dt", keep=lambda x, y: (x, y) in f.px)
    f.ellipse(17, 10.4, 2.2, 2.6, P.FRILL_DK, to="dt", keep=lambda x, y: (x, y) in f.px)
    cv.overlay(f)
    for y in range(12, 20):                                                    # 등줄기
        cv.dt[(17, y)] = P.DK
    climb_feet(cv, arms + legs)
    cv.finish()
    return cv.image(h=CH)


# ══════════════════════════════════════════════════════════════════════
# 익룡: 분홍 몸 + 크림색 날개막 + 청록 볏 + 노란 부리, 용처럼 날갯짓 (주황 용과 안 겹치게 분홍)
# ══════════════════════════════════════════════════════════════════════
PTERO = Pal(
    LINE=(122, 40, 80, 255),
    BODY=(242, 136, 172, 255),
    HI=(255, 188, 212, 255),
    DK=(210, 100, 142, 255),
    FAR=(214, 108, 148, 255),
    BELLY=(255, 232, 242, 255),
    MEMB=(255, 236, 178, 255),
    MEMB_DK=(240, 204, 132, 255),
    CREST=(58, 184, 196, 255),
    CREST_HI=(132, 224, 228, 255),
    BEAK=(255, 210, 84, 255),
    BEAK_DK=(220, 156, 46, 255),
    CLAW=(255, 248, 228, 255),
    EYE=(44, 20, 34, 255),
    BLUSH=(255, 120, 150, 255),
    MOUTH_IN=(150, 40, 66, 255),
)

# 날개 자세: (손목, 날개 끝, 날개막 뿌리). 어깨는 (17.5, 12.5). 뿌리는 등·옆구리에 붙여 몸이 가려지지 않게.
# 어떤 자세에서도 날개가 배 아래(y 17 밑)로 내려가지 않는다 — 배 밑에서 뭔가 튀어나와 보이지 않게
PT_WING = {
    "up": ((16.0, 2.6), (9.0, 1.0), (12.8, 11.8)),
    "high": ((12.6, 5.4), (3.0, 5.0), (12.6, 12.0)),
    "glide": ((11.6, 8.4), (1.6, 11.0), (12.6, 13.2)),
    "mid": ((12.0, 11.6), (2.0, 13.4), (13.0, 16.0)),
    "down": ((12.4, 13.4), (3.6, 15.8), (13.4, 16.4)),          # 내려친 날개도 배 선(17) 위에서 몸 옆·뒤로 (배 밑으로 안 삐져나오게)
    "fold": ((15.4, 5.2), (9.0, 3.2), (13.2, 11.8)),
}


def pt_wing(P, pose):
    """가까운 날개: 크림색 날개막 + 2칸 팔뼈(앞전) + 가는 손가락, 손목 발톱"""
    w = Cv(P)
    S = (17.5, 12.5)
    wr, tip, root = PT_WING[pose]
    mx, my = (tip[0] + root[0]) / 2, (tip[1] + root[1]) / 2          # 날개막 뒷전은 안쪽으로 살짝 오목
    mid = (mx + (wr[0] - mx) * 0.22, my + (wr[1] - my) * 0.22)
    w.poly([S, wr, tip, mid, root], P.MEMB)
    w.capsule(*S, *wr, 0.85, 0.7)                                     # 팔뼈 (앞전, 2칸)
    w.capsule(*wr, *tip, 0.55, 0.3)                                   # 긴 손가락
    for (x, y), c in list(w.px.items()):                              # 날개막 뒷전 그늘
        if c == P.MEMB and ((x, y + 1) not in w.px or (x - 1, y) not in w.px):
            w.dt[(x, y)] = P.MEMB_DK
    w.dt[(rnd(wr[0]), rnd(wr[1]) - 1)] = P.CLAW                       # 손목 발톱
    return w


def ptero_frame(pose, bob=0, tilt=0.0, mood="normal", blink=False, run=False, frame=0):
    P = PTERO
    cv = Cv(P)
    open_ = mood in ("talk", "surprised")
    cv.capsule(11.6, 14.8, 8.2, 15.8, 1.0, 0.4)                       # 짧은 꼬리
    cv.poly([(22.6, 5.0), (13.4, 0.8), (13.2, 2.8), (21.0, 8.8)], P.CREST)   # 볏 (머리 뒤로 쭉)
    cv.ellipse(15.6, 14.0, 5.0, 3.3)                                  # 몸통
    cv.capsule(19.2, 12.6, 21.6, 10.4, 1.8, 1.7)                      # 목
    cv.ellipse(23.4, 8.2, 3.6, 3.4)                                   # 머리 (크게)
    if open_:                                                         # 부리 끝은 x ≤ 31 (외곽선이 32, 오른쪽 끝 1칸 비움)
        cv.poly([(25.8, 6.6), (32.0, 8.8), (31.4, 9.6), (25.8, 9.5)], P.BEAK)
        cv.poly([(25.8, 9.4), (30.6, 10.3), (30.6, 11.2), (25.8, 11.6)], P.MOUTH_IN)
        cv.poly([(25.8, 11.0), (30.8, 11.2), (30.2, 12.4), (25.8, 12.4)], P.BEAK)
    else:
        cv.poly([(25.8, 6.6), (32.0, 9.0), (32.0, 10.2), (25.8, 11.6)], P.BEAK)
    for (x, y), c in list(cv.px.items()):                             # 볏 윗선 · 부리 아랫면
        if c == P.CREST and (x, y - 1) not in cv.px:
            cv.dt[(x, y)] = P.CREST_HI
        if c == P.BEAK and (x, y + 1) not in cv.px:
            cv.dt[(x, y)] = P.BEAK_DK
    if not open_:                                                      # 입선 (끝이 살짝 올라감)
        for x in range(27, 31):
            cv.dt[(x, 10)] = P.BEAK_DK
        cv.dt[(26, 9)] = P.BEAK_DK
        if mood == "happy":
            cv.dt[(26, 9)] = P.MOUTH_IN; cv.dt[(27, 10)] = P.MOUTH_IN
    cv.ellipse(16.2, 15.4, 3.6, 1.7, P.BELLY, to="dt", keep=lambda x, y: (x, y) in cv.px and cv.px[(x, y)] == P.BODY)
    eye2(cv, 22, 7, mood, blink)
    cv.dt[(21, 10)] = P.BLUSH; cv.dt[(22, 10)] = P.BLUSH
    cv.overlay(pt_wing(P, pose))
    for p_, c_ in (((12, 16), P.DK), ((13, 16), P.DK), ((11, 16), P.CLAW)):   # 발: 배 뒤쪽에 꼭 접어 넣은 모양 (밖으로 안 나옴, 모든 프레임 같음)
        if p_ in cv.px:
            cv.dt[p_] = c_
    if run:
        speed_lines(cv, frame, [(5, 4, 0), (19, 3, 5), (14, 3, 2)], 8)
    cv.finish()
    return cv.image(dy=bob, tilt=tilt, cx=17)


def ptero_walk(i):
    return ptero_frame(("up", "high", "down", "fold")[i], bob=(1, 0, -1, 0)[i])


def ptero_run(i):
    """빠른 날갯짓 6장 (앞으로 숙여 쌩): 올림 → 뒤로 펼침 → 수평 → 아래로 → 쳐냄 → 접으며 올림"""
    pose = ("up", "high", "glide", "mid", "down", "fold")[i]
    return ptero_frame(pose, bob=(1, 1, 0, -1, -1, 0)[i], tilt=0.12, run=True, frame=i)


def ptero_idle(mood="normal", blink=False):
    return ptero_frame("fold", mood=mood, blink=blink)


# ══════════════════════════════════════════════════════════════════════
# 스테고사우루스: 연두 몸 + 주황 등판 두 줄(엇갈림) + 꼬리 가시, 작은 머리, 뒤뚱뒤뚱
# ══════════════════════════════════════════════════════════════════════
STEGO = Pal(
    LINE=(70, 96, 30, 255),
    BODY=(182, 208, 90, 255),
    HI=(220, 236, 142, 255),
    DK=(144, 174, 66, 255),
    FAR=(150, 178, 70, 255),
    BELLY=(248, 244, 192, 255),
    PLATE=(250, 148, 58, 255),
    PLATE_HI=(255, 202, 116, 255),
    PLATE_DK=(204, 98, 36, 255),
    PLATE_FAR=(214, 112, 44, 255),
    CLAW=(252, 250, 226, 255),
    EYE=(30, 34, 22, 255),
    BLUSH=(252, 150, 150, 255),
    MOUTH=(84, 110, 40, 255),
    MOUTH_IN=(150, 56, 60, 255),
)

ST_BODY = (14.6, 14.4, 9.0, 5.2)       # 몸통 타원 (cx, cy, rx, ry)


def st_top(x):
    cx, cy, rx, ry = ST_BODY
    t = (x - cx) / rx
    return cy - ry * math.sqrt(max(0.0, 1 - t * t))


def st_plate(cv, x, base, h, col, hi=None):
    """등판 한 장: 폭 3칸, 끝이 뾰족한 오각형 (x = 가운데 칸)"""
    for k in range(h + 2):
        y = base - h + k
        if k == 0:
            cv.put(x, y, col)
        else:
            cv.rect(x - 1, y, x + 1, y, col)
    if hi:
        cv.dt[(x, base - h)] = hi
        cv.dt[(x - 1, base - h + 1)] = hi
        cv.dt[(x - 1, base - h + 2)] = hi


def stego_frame(legs, bob=0, tilt=0.0, plate_dy=0, sway=0, mood="normal", blink=False, head_dy=0, dust=()):
    """legs = (가까운 뒷발, 가까운 앞발, 먼 뒷발, 먼 앞발) 각각 (발 x, 들림)"""
    P = STEGO
    cv = Cv(P)
    nh, nf, fh, ff = legs
    stump(cv, (11.8, 17 + bob), fh, P.FAR, 1.45)
    stump(cv, (20.6, 18 + bob), ff, P.FAR, 1.35)
    u = Cv(P)
    for x, h in ((10, 4), (15, 5), (20, 3)):                                   # 먼 줄 등판 (어둡게, 사이사이)
        st_plate(u, x, rnd(st_top(x)) + 1 + plate_dy, h, P.PLATE_FAR)
    tip = (1.6, 9.2 + sway)                                                     # 꼬리 + 가시 넷
    u.path([(8, 14.0), (4.6, 12.0 + sway * 0.4), tip], [2.7, 1.7, 0.9])
    u.capsule(tip[0] + 0.8, tip[1], tip[0] - 0.8, tip[1] - 4.4, 0.65, 0.2, P.PLATE)
    u.capsule(tip[0] + 3.2, tip[1] + 1.2, tip[0] + 2.8, tip[1] - 3.4, 0.65, 0.2, P.PLATE)
    cx, cy, rx, ry = ST_BODY
    u.ellipse(cx, cy, rx, ry, keep=lambda x, y: y <= 19)                       # 몸통 (높은 등)
    u.ellipse(14.6, 18.6, 6.5, 1.5, P.BELLY, to="dt", keep=lambda x, y: (x, y) in u.px and (x, y + 1) in u.px and u.px[(x, y)] == P.BODY)
    hy = 15.6 + head_dy                                                         # 목 + 작은 머리 (낮게)
    u.capsule(21.5, 14.6, 25.4, hy, 2.4, 2.2)
    u.ellipse(27.6, hy, 3.9, 3.2)
    u.put(31, rnd(hy) + 1); u.put(31, rnd(hy))
    eye2(u, 27, rnd(hy) - 2, mood, blink)
    u.dt[(25, rnd(hy) + 1)] = P.BLUSH; u.dt[(26, rnd(hy) + 1)] = P.BLUSH
    my = rnd(hy) + 1
    if mood in ("talk", "surprised"):
        for p in ((29, my), (30, my), (29, my + 1), (30, my + 1)):
            u.dt[p] = P.MOUTH_IN
        u.dt[(28, my)] = P.MOUTH; u.dt[(31, my)] = P.MOUTH
    elif mood == "happy":
        for p in ((28, my), (29, my + 1), (30, my + 1), (31, my)):
            u.dt[p] = P.MOUTH
        u.dt[(29, my)] = P.MOUTH_IN; u.dt[(30, my)] = P.MOUTH_IN
    else:
        for p in ((28, my), (29, my + 1), (30, my + 1), (31, my + 1)):
            u.dt[p] = P.MOUTH
    pl = Cv(P)                                                                  # 가까운 줄 등판 (경계선으로 한 장씩 또렷)
    for x, h in ((7, 4), (12, 6), (17, 6), (22, 3)):
        st_plate(pl, x, rnd(st_top(x)) + 1 + plate_dy, h, P.PLATE, P.PLATE_HI)
    u.overlay(pl)
    for (x, y), c in list(u.px.items()):                                       # 가시 끝은 밝게
        if c == P.PLATE and (x, y - 1) not in u.px and x < 7:
            u.dt[(x, y)] = P.PLATE_HI
    cv.paste(u, 0, bob, tilt, 15)
    s = Cv(P)
    stump(s, (9.4, 17 + bob), nh, P.BODY, 1.5, thigh=(3.1, 3.4))
    cv.overlay(s)
    s = Cv(P)
    stump(s, (18.6, 18 + bob), nf, P.BODY, 1.4)
    cv.overlay(s)
    for (x, y, r, al) in dust:
        puff(cv, x, y, r, al)
    cv.finish()
    return cv.image()


def stego_walk(i):
    A = [(2, 0), (0, 0), (-2, 0), (0, 1)][i]
    B = [(-2, 0), (0, 1), (2, 0), (0, 0)][i]
    legs = ((9.4 + A[0], A[1]), (18.6 + B[0], B[1]), (11.8 + B[0], B[1]), (20.6 + A[0], A[1]))
    return stego_frame(legs, bob=(0, -1, 0, -1)[i], sway=(0, 1, 0, -1)[i])


def stego_run(i):
    """뒤뚱뒤뚱 6장: 짧은 다리로 종종, 몸이 앞뒤로 기우뚱 · 등판이 출렁 · 꼬리 가시 흔들"""
    legs = [
        ((11, 0), (17, 2), (12, 2), (22, 0)),
        ((9, 0), (19, 1), (13, 1), (20, 0)),
        ((7, 1), (21, 0), (14, 0), (18, 1)),
        ((10, 2), (20, 0), (11, 0), (19, 2)),
        ((12, 1), (18, 0), (10, 0), (21, 1)),
        ((13, 0), (16, 1), (9, 1), (22, 0)),
    ][i]
    tilt = (0.03, 0.015, -0.015, -0.03, -0.015, 0.015)[i]      # 기우뚱은 꼬리 쪽만 (머리는 몸 들썩을 따라 1칸씩만)
    dust = [(5, 21.0, 1.7, 190)] if i in (0, 3) else []
    return stego_frame(legs, bob=(0, -1, -1, 0, -1, -1)[i], tilt=tilt, plate_dy=(0, 1, 0, 0, 1, 0)[i],
                       sway=(-2, -1, 1, 2, 1, -1)[i], head_dy=0, dust=dust)


def stego_stand(mood="normal", blink=False):
    return stego_frame(((9.4, 0), (18.6, 0), (11.8, 0), (20.6, 0)), mood=mood, blink=blink)


def stego_climb(i):
    """벽 타기 (등판 大자): 등줄기를 따라 지그재그 등판(몸 밖으로 삐죽) · 꼬리 끝 가시가 양옆으로"""
    P = STEGO
    cv = Cv(P)
    arms = [((8, 4), (27, 10)), ((7, 10), (26, 4)), ((6, 6), (28, 6))][i]
    legs = [((9, 23), (25, 18)), ((9, 18), (25, 23)), ((7, 23), (27, 23))][i]
    tsw = (1, -1, 0)[i]
    tx, ty = 17 + tsw * 1.2, 25.2

    def spikes(t):                                                             # 꼬리 끝 가시: X자로 뻗은 두 쌍 (끝은 밝게)
        for s_ in (-1, 1):
            for (y0, x1, y1) in ((-0.6, 4.2, -2.6), (1.0, 4.0, 3.2)):
                t.capsule(tx, ty + y0, tx + s_ * x1, ty + y1, 0.65, 0.2, P.PLATE)
                t.dt[(rnd(tx + s_ * x1), rnd(ty + y1))] = P.CLAW
        t.capsule(tx, ty, tx + tsw * 0.2, 27.6, 1.1, 0.45)                    # 꼬리 끝 (가시 위에)
    hang_tail(cv, [(17, 17.5), (17 + tsw * 0.6, 21.4), (tx, ty)], [2.3, 1.75, 1.1], spikes)   # 꼬리
    for (sx, sy), end in zip(((13, 17), (21, 17)), legs):
        cv.capsule(sx, sy, end[0], end[1], 1.7, 1.5)
    for (sx, sy), end in zip(((12.6, 10.5), (21.4, 10.5)), arms):
        cv.capsule(sx, sy, end[0], end[1], 1.5, 1.3)
    cv.ellipse(17, 12.8, 5.8, 6.6)                                             # 등
    cv.ellipse(17, 3.6, 3.4, 2.8)                                              # 작은 뒤통수
    cv.rect(16, 5, 18, 7)
    for k, (x, y) in enumerate(((15.5, 7), (18.5, 9), (15.5, 11), (18.5, 13), (15.5, 15), (18.5, 17))):   # 등판: 지그재그 두 줄
        for yy in range(y - 2, y + 3):
            half = 2 - abs(yy - y)
            for xx in range(int(x - half - 0.5) + 1, int(x + half + 0.5) + 1):
                edge = abs(xx - x) + abs(yy - y) >= 1.9
                cv.dt[(xx, yy)] = P.PLATE_DK if edge and (xx > x or yy > y) else (P.PLATE_HI if edge else P.PLATE)
    climb_feet(cv, arms + legs)
    cv.finish()
    return cv.image(h=CH)


# ══════════════════════════════════════════════════════════════════════
# 브라키오사우루스: 연보라 몸 + 진보라 점무늬, 앞으로 휜 긴 목 끝에 작은 머리(코 혹), 긴 꼬리, 순한 눈
# ══════════════════════════════════════════════════════════════════════
BRACHIO = Pal(
    LINE=(70, 58, 132, 255),
    BODY=(170, 160, 234, 255),
    HI=(212, 204, 252, 255),
    DK=(136, 124, 204, 255),
    FAR=(144, 132, 210, 255),
    SPOT=(136, 122, 208, 255),
    BELLY=(236, 232, 254, 255),
    CLAW=(250, 248, 255, 255),
    EYE=(32, 26, 54, 255),
    BLUSH=(255, 154, 182, 255),
    MOUTH=(92, 76, 156, 255),
    MOUTH_IN=(150, 56, 82, 255),
)


BRACHIO_HEAD = [      # 9 × 7 — 동그란 작은 머리 + 이마 위 콧등 혹 (h)
    "...hhh...",
    "..hgggh..",
    ".gggggggh",
    "ggggggggg",
    "ggggggggg",
    "ggggggggg",
    ".ggggggg.",
]


def brachio_head(cv, hx, hy, mood="normal", blink=False, eye=True):
    """작은 머리 (hx, hy = 왼쪽 위): 둥근 머리 + 콧등 혹 + 순한 눈 + 볼터치"""
    P = cv.P
    cv.art(hx, hy, BRACHIO_HEAD, {"g": P.BODY, "h": P.HI})
    if eye:
        eye2(cv, hx + 4, hy + 2, mood, blink)
    cv.dt[(hx + 2, hy + 4)] = P.BLUSH; cv.dt[(hx + 3, hy + 4)] = P.BLUSH
    my = hy + 5
    if mood in ("talk", "surprised"):
        cv.dt[(hx + 5, my)] = P.MOUTH_IN; cv.dt[(hx + 6, my)] = P.MOUTH_IN; cv.dt[(hx + 7, my)] = P.MOUTH
        cv.dt[(hx + 5, my + 1)] = P.MOUTH_IN; cv.dt[(hx + 6, my + 1)] = P.MOUTH_IN
        cv.dt[(hx + 4, my)] = P.MOUTH
    elif mood == "happy":
        for p in ((hx + 4, my - 1), (hx + 5, my), (hx + 6, my), (hx + 7, my), (hx + 8, my - 1)):
            cv.dt[p] = P.MOUTH
        cv.dt[(hx + 6, my + 1)] = P.MOUTH_IN
    else:
        for p in ((hx + 4, my - 1), (hx + 5, my), (hx + 6, my), (hx + 7, my)):
            cv.dt[p] = P.MOUTH


def brachio_frame(legs, bob=0, neck=0, sway=0, mood="normal", blink=False, dust=()):
    """legs = (가까운 뒷발, 가까운 앞발, 먼 뒷발, 먼 앞발). neck = 머리 높이 끄덕 (+ 아래)"""
    P = BRACHIO
    cv = Cv(P)
    nh, nf, fh, ff = legs
    stump(cv, (10.6, 16.6 + bob), fh, P.FAR, 1.4)
    stump(cv, (17.6, 15.4 + bob), ff, P.FAR, 1.4)
    u = Cv(P)
    # 긴 꼬리: 엉덩이에서 뒤로 내려오며 가늘어져 뾰족하게 끝남 — 프레임 왼쪽 끝에서 1칸 띄움 (외곽선까지 x ≥ 1)
    u.path([(7.2, 14.2), (4.8, 15.6 + sway * 0.4), (3.2, 17.4 + sway * 0.6), (2.6, 19.4 + sway * 0.8)], [2.2, 1.5, 0.95, 0.4])
    u.oval(12.8, 14.0, 7.0, 4.3, -13)                                        # 몸통 (앞이 높게 기욺)
    hx, hy = 23, 1 + neck                                                    # 주둥이도 오른쪽 끝에서 1칸 띄움 (x ≤ 32)
    u.path([(16.6, 11.8), (19.6, 8.4 + neck * 0.4), (22.6, 5.6 + neck)], [2.4, 1.8, 1.6])  # 앞으로 휜 긴 목
    brachio_head(u, hx, hy, mood, blink)
    u.oval(12.8, 17.2, 5.0, 1.4, -13, P.BELLY, to="dt")
    for p in list(u.dt):
        if p not in u.px or (p[0], p[1] + 1) not in u.px:
            if u.dt[p] == P.BELLY:
                del u.dt[p]
    for x, y in ((8, 12), (9, 12), (12, 11), (13, 11), (15, 9), (16, 9), (10, 14), (14, 13), (6, 15)):   # 등 점무늬
        if (x, y) in u.px and (x, y - 1) in u.px:
            u.dt[(x, y)] = P.SPOT
    cv.paste(u, 0, bob)
    s = Cv(P)
    stump(s, (8.4, 16.6 + bob), nh, P.BODY, 1.55, thigh=(2.9, 3.2))
    cv.overlay(s)
    s = Cv(P)
    stump(s, (15.4, 15.4 + bob), nf, P.BODY, 1.5)
    cv.overlay(s)
    for (x, y, r, al) in dust:
        puff(cv, x, y, r, al)
    cv.finish()
    return cv.image()


def brachio_walk(i):
    A = [(2, 0), (0, 0), (-2, 0), (0, 1)][i]
    B = [(-2, 0), (0, 1), (2, 0), (0, 0)][i]
    legs = ((8.4 + A[0], A[1]), (15.4 + B[0], B[1]), (10.6 + B[0], B[1]), (17.6 + A[0], A[1]))
    bob = (0, -1, 0, -1)[i]
    return brachio_frame(legs, bob=bob, neck=-bob, sway=(0, 1, 0, -1)[i])        # 몸만 들썩, 머리는 제자리 (2배 화면에서도 깜빡임 없음)


def brachio_run(i):
    """느릿느릿 구보 6장: 대각선 다리 짝으로 쿵·쿵, 디딜 때 몸이 내려앉고 긴 목은 한 박자 늦게 끄덕"""
    A = [(2, 0), (0, 0), (-2, 0), (-2, 0), (0, 2), (2, 1)][i]       # 가까운 뒷발 + 먼 앞발
    B = [(-2, 0), (0, 2), (2, 1), (2, 0), (0, 0), (-2, 0)][i]       # 가까운 앞발 + 먼 뒷발
    legs = ((8.4 + A[0], A[1]), (15.4 + B[0], B[1]), (10.6 + B[0], B[1]), (17.6 + A[0], A[1]))
    dust = [(5, 21.0, 1.7, 190)] if i in (0, 3) else []
    bob = (1, 0, -1, 1, 0, -1)[i]
    head = (0, 1, 1, 0, 1, 1)[i]                                                   # 머리 높이: 1칸씩만 끄덕 (한 장만 튀지 않게)
    return brachio_frame(legs, bob=bob, neck=head - bob, sway=(1, 0, -1, 1, 0, -1)[i], dust=dust)


def brachio_stand(mood="normal", blink=False):
    return brachio_frame(((8.4, 0), (15.4, 0), (10.6, 0), (17.6, 0)), mood=mood, blink=blink)


def brachio_climb(i):
    """벽 타기 (등판 大자): 가운데로 쭉 뻗은 긴 목 끝에 동그란 머리 · 네 다리 쫙 · 늘어진 긴 꼬리"""
    P = BRACHIO
    cv = Cv(P)
    arms = [((8, 8), (27, 13)), ((7, 13), (26, 8)), ((6, 10), (28, 10))][i]
    legs = [((10, 23), (25, 19)), ((9, 19), (24, 23)), ((8, 23), (26, 23))][i]
    tsw = (1, -1, 0)[i]
    d = 1 if tsw >= 0 else -1
    hang_tail(cv, [(17, 18.5), (17 + tsw * 0.6, 21.6), (17 + tsw * 1.3, 24.8), (17 + tsw * 2.0 + d * 1.0, 27.8),
                   (17 + tsw * 2.0 + d * 3.0, 29.8)], [2.4, 1.9, 1.4, 0.9, 0.4])           # 길게 늘어진 꼬리
    for (sx, sy), end in zip(((13.4, 17.6), (20.6, 17.6)), legs):
        cv.capsule(sx, sy, end[0], end[1], 1.8, 1.55)
    for (sx, sy), end in zip(((12.8, 12.8), (21.2, 12.8)), arms):
        cv.capsule(sx, sy, end[0], end[1], 1.65, 1.4)
    cv.ellipse(17, 14.9, 6.2, 5.4)                                           # 등
    cv.capsule(17, 10.0, 17, 5.8, 1.75, 1.55)                                # 긴 목
    cv.ellipse(17, 3.5, 3.5, 2.8)                                            # 동그란 뒤통수
    for x, y in ((15, 12), (16, 12), (19, 13), (16, 16), (17, 16), (18, 18), (14, 15), (20, 16), (17, 8)):
        cv.dt[(x, y)] = P.SPOT
    climb_feet(cv, arms + legs)
    cv.finish()
    return cv.image(h=CH)


# ══════════════════════════════════════════════════════════════════════
# 행동 시트 — 앱이 그 행동을 하는 동안 pet/<id>_<act>.png 를 재생 (2장은 반복, 3장은 순서대로 한 번 → 마지막 장 유지)
# 규칙: 34×24 · 오른쪽을 본다 · 기본 시트와 같은 색·몸 크기 · 자동 외곽선 · 좌우 1칸 여백 (x=0·33 은 비움)
# ══════════════════════════════════════════════════════════════════════
ACT_LINE = (150, 162, 186, 255)        # 음파·휘두름 자국 (흰 바탕·어두운 바탕 둘 다 보이는 회청색)
STAR_EDGE = (246, 140, 36, 255)
STAR_FILL = (255, 222, 70, 255)
STAR_CORE = (255, 255, 236, 255)
SWEAT = (124, 200, 255, 255)
SWEAT_DK = (52, 118, 200, 255)
LEAF = (96, 178, 72, 255)
LEAF_DK = (58, 124, 48, 255)
LEAF_HI = (156, 214, 104, 255)


def rot_pt(p, ang, pivot):
    """점 p 를 pivot 둘레로 ang 도 회전 (+ = 화면에서 시계 방향 → 주둥이가 내려감)"""
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    dx, dy = p[0] - pivot[0], p[1] - pivot[1]
    return (pivot[0] + dx * ca - dy * sa, pivot[1] + dx * sa + dy * ca)


def rotated(src, ang, pivot):
    """캔버스 통째 회전 (가장 가까운 칸 뽑기 — 구멍 없이 채워짐). 외곽선은 나중에 자동으로 다시 둘러진다"""
    out = Cv(src.P)
    layers = ("px", "dt", "fx", "top")
    pts = [p for name in layers for p in getattr(src, name)]
    if not pts:
        return out
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    px0, py0 = pivot
    R = max(math.hypot(x - px0, y - py0) for x, y in pts) + 2
    for ty in range(int(py0 - R) - 1, int(py0 + R) + 2):
        for tx in range(int(px0 - R) - 1, int(px0 + R) + 2):
            dx, dy = tx - px0, ty - py0
            k = (rnd(px0 + dx * ca + dy * sa), rnd(py0 - dx * sa + dy * ca))
            for name in layers:
                L = getattr(src, name)
                if k in L:
                    getattr(out, name)[(tx, ty)] = L[k]
    return out


def merge(dst, src):
    for name in ("px", "dt", "fx", "top"):
        getattr(dst, name).update(getattr(src, name))


def star(cv, cx, cy, big=True):
    """부딪힘 별 (맨 앞): 노란 네 갈래 + 주황 테 + 하얀 속"""
    cx, cy = rnd(cx), rnd(cy)
    T = cv.top
    arms = 3 if big else 2
    for k in range(1, arms + 1):
        for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            T[(cx + dx, cy + dy)] = STAR_FILL if k < arms else STAR_EDGE
    for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        T[(cx + dx, cy + dy)] = STAR_FILL
        if big:
            T[(cx + 2 * dx, cy + 2 * dy)] = STAR_EDGE
    T[(cx, cy)] = STAR_CORE


def sparkle(cv, cx, cy):
    """작은 반짝 (+)"""
    cx, cy = rnd(cx), rnd(cy)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        cv.top[(cx + dx, cy + dy)] = STAR_FILL
    cv.top[(cx, cy)] = STAR_CORE


def sweat_drop(cv, x, y):
    """땀방울 (위가 뾰족한 물방울)"""
    for p, c in (((x, y), SWEAT_DK), ((x, y + 1), SWEAT), ((x - 1, y + 2), SWEAT_DK), ((x, y + 2), SWEAT), ((x + 1, y + 2), SWEAT_DK),
                 ((x - 1, y + 3), SWEAT_DK), ((x, y + 3), SHINE), ((x + 1, y + 3), SWEAT_DK), ((x, y + 4), SWEAT_DK)):
        cv.top[p] = c
    cv.top[(x, y + 2)] = SHINE


def act_line(cv, x0, y0, x1, y1, col=ACT_LINE, layer="top"):
    cv.line(x0, y0, x1, y1, col, to=layer)


def arc_marks(cv, cx, cy, r, a0, a1, n=3, ln=2, col=ACT_LINE):
    """중심에서 바깥으로 뻗는 짧은 선 n개 (음파·부딪힘)"""
    for k in range(n):
        a = math.radians(a0 + (a1 - a0) * k / max(1, n - 1))
        x0, y0 = cx + r * math.cos(a), cy + r * math.sin(a)
        x1, y1 = cx + (r + ln) * math.cos(a), cy + (r + ln) * math.sin(a)
        act_line(cv, x0, y0, x1, y1, col)


def squeeze_eye(cv, ex, ey):
    """질끈 감은 눈 ( > )"""
    E = cv.P.EYE
    cv.dt[(ex, ey - 1)] = E; cv.dt[(ex + 1, ey)] = E; cv.dt[(ex, ey + 1)] = E


def fierce_brow(cv, ex, ey):
    """앞으로 내려간 눈썹 (힘줌)"""
    L = cv.P.LINE
    cv.dt[(ex - 1, ey - 2)] = L; cv.dt[(ex, ey - 2)] = L; cv.dt[(ex + 1, ey - 1)] = L


def put_eye(cv, ex, ey, mood="normal", blink=False):
    if mood == "sleep":                                            # 잠든 눈: 가로 일자선
        for dx in (-1, 0, 1, 2):
            cv.dt[(ex + dx, ey + 1)] = cv.P.EYE
        return
    if mood == "squeeze":
        squeeze_eye(cv, ex, ey)
        return
    eye2(cv, ex, ey, "normal" if mood == "fierce" else mood, blink)
    if mood == "fierce":
        fierce_brow(cv, ex, ey)


def check_margin(name, frames):
    """좌우 1칸 여백 검사 (x=0·33 에 칠한 칸이 있으면 알림)"""
    bad = []
    for k, f in enumerate(frames):
        a = f.getchannel("A")
        if any(a.getpixel((0, y)) or a.getpixel((W - 1, y)) for y in range(f.height)):
            bad.append(k)
    if bad:
        print(f"  !! 여백 침범: {name} 프레임 {bad}")


# ── 소품: 만화 고기 · 파란 물고기 (따로 그려 외곽선 색도 따로) ────────────
MEATP = Pal(LINE=(70, 38, 24, 255), BODY=(184, 96, 54, 255), HI=(222, 136, 82, 255), DK=(138, 66, 36, 255))
BONE = (252, 250, 240, 255)
BONE_DK = (214, 206, 186, 255)
MEAT_SHINE = (246, 186, 132, 255)
FISHP = Pal(LINE=(46, 48, 56, 255), BODY=(64, 134, 232, 255), HI=(40, 92, 182, 255), DK=(196, 228, 255, 255))
FISH_FIN = (76, 166, 246, 255)


def meat_cv(cx, cy, ang=0.0, s=1.0, bone=True):
    """뼈다귀 만화 고기: 갈색 고기 덩이 + 양쪽으로 삐죽 나온 하얀 뼈 (끝이 둥근 혹 두 개)"""
    c = Cv(MEATP)
    L = 4.4 * s
    if bone:
        c.capsule(cx - L, cy, cx + L, cy, 0.8 * s, 0.8 * s, BONE)
        for e in (-1, 1):
            for o in (-1, 1):
                c.ellipse(cx + e * L, cy + o * 0.95 * s, 1.15 * s, 1.0 * s, BONE)
    c.ellipse(cx - 0.3 * s, cy, 3.3 * s, 2.7 * s)
    r = rotated(c, ang, (cx, cy))
    for (x, y), col in list(r.px.items()):
        if col == BONE and (x, y + 1) not in r.px:
            r.dt[(x, y)] = BONE_DK
    r.finish()
    sx, sy = rot_pt((cx - 1.4 * s, cy - 1.1 * s), ang, (cx, cy))
    r.dt[(rnd(sx), rnd(sy))] = MEAT_SHINE
    if s > 1.4:
        r.dt[(rnd(sx) + 1, rnd(sy))] = MEAT_SHINE
    return r


def fish_cv(cx, cy, ang=0.0):
    """prop_fish 와 같은 결의 작은 파란 물고기 (오른쪽이 머리): 진한 등 · 밝은 배 · 꼬리지느러미 · 흰 눈"""
    c = Cv(FISHP)
    c.ellipse(cx, cy, 3.1, 1.7)
    c.poly([(cx - 2.4, cy), (cx - 5.0, cy - 2.2), (cx - 5.0, cy + 2.2)], FISH_FIN)
    c.put(rnd(cx), rnd(cy) - 2, FISH_FIN)                                 # 등지느러미
    r = rotated(c, ang, (cx, cy))
    r.finish()
    ex, ey = rot_pt((cx + 1.6, cy - 0.4), ang, (cx, cy))
    r.dt[(rnd(ex), rnd(ey))] = SHINE
    return r


def prop_meat():
    """prop_meat.png 24×24 한 장: 앱이 던져 주는 만화 고기"""
    m = meat_cv(17, 12, -32, s=1.85)
    return m.image().crop((5, 0, 29, 24))


# ── 티라노: 머리 장치 (위턱·아래턱 따로 돌림 → 크게 벌린 입, 고개 들기) ────
TREX_SKULL = TREX_HEAD[:7]
TREX_JAW = TREX_HEAD[7:]


def trex_head_rig(P, x, y, up=0.0, jaw=0.0, mood="normal", blink=False):
    """up = 고개 (- = 주둥이 위로), jaw = 입 벌림 각도 (아래턱만 더 돌림). 눈은 돌린 뒤 또렷하게 다시 찍는다"""
    pal = {"g": P.BODY, "h": P.HI, "b": P.BELLY}
    hinge = (x + 3.5, y + 6.5)
    sk = Cv(P)
    sk.art(x, y, TREX_SKULL, pal)
    sk.dt[(x + 13, y + 3)] = P.NOSE
    sk.dt[(x + 6, y + 5)] = P.BLUSH; sk.dt[(x + 7, y + 5)] = P.BLUSH
    sk.dt[(x + 4, y + 5)] = P.MLINE
    jw = Cv(P)
    jw.art(x, y + 7, TREX_JAW, pal)
    head = Cv(P)
    if jaw <= 0:
        for k in range(5, 15):
            sk.dt[(x + k, y + 6)] = P.MLINE
        for k in (6, 8, 10, 12):
            jw.dt[(x + k, y + 7)] = P.TOOTH
        both = Cv(P)
        merge(both, jw)
        merge(both, sk)
        merge(head, rotated(both, up, hinge))
    else:
        for k in (6, 8, 10, 12):                                   # 윗니
            sk.dt[(x + k, y + 6)] = P.TOOTH
        for k in (8, 11):                                          # 아랫니
            jw.dt[(x + k, y + 7)] = P.TOOTH
        a = rot_pt((x + 14.4, y + 6.4), up, hinge)
        b = rot_pt((x + 13.4, y + 7.0), up + jaw, hinge)
        m = Cv(P)
        m.poly([(x + 2.2, y + 6.6), a, b], P.MOUTH)                # 입 안
        t0, t1 = rot_pt((x + 6.5, y + 6.2), up + jaw, hinge), rot_pt((x + 10.5, y + 6.2), up + jaw, hinge)
        m.capsule(*t0, *t1, 0.75, 0.6, P.TONGUE)                   # 혀
        merge(head, m)
        merge(head, rotated(jw, up + jaw, hinge))
        merge(head, rotated(sk, up, hinge))
    ex, ey = rot_pt((x + 8.5, y + 2.5), up, hinge)
    put_eye(head, rnd(ex - 0.5), rnd(ey - 0.5), mood, blink)
    head.hinge = hinge
    head.mouth = (rot_pt((x + 14.4, y + 6.4), up, hinge), rot_pt((x + 13.4, y + 7.0), up + jaw, hinge))
    return head


def trex_pose(near=(13, 0), far=(16, 0), bob=0, tilt=0.0, sway=0.0, head=None, hx=17, hy=1, arm=0,
              arms_up=None, dust=(), throat=False, under=None, cheeks=False):
    """행동용 티라노: 걷기와 같은 몸 · 꼬리 끝은 x≥2, 주둥이는 x≤31 (좌우 여백). head = trex_head_rig 인자.
    under(u, h) = 머리 뒤에 깔 것 (입 속 고기 등)"""
    P = TREX
    cv = Cv(P)
    hyb = 15.5 + bob
    trex_leg(cv, (16.2, hyb), far, P.FAR, thigh=False)
    if arms_up:                                                    # 먼 팔 (몸 뒤)
        (fa0, fa1) = arms_up[0]
        cv.capsule(*fa0, *fa1, 0.75, 0.65, P.FAR)
        cv.dt[(rnd(fa1[0]), rnd(fa1[1]))] = P.CLAW
    u = Cv(P)
    u.path([(11, 13.5), (6.6, 12.2), (3.0, 9.2 + sway)], [3.1, 2.0, 0.85])     # 꼬리 (끝은 x≥2)
    u.ellipse(15.5, 13.8, 6.6, 4.8)
    u.ellipse(19.9, 11.6, 3.3, 3.6)
    body = set(u.px)
    h = trex_head_rig(P, hx, hy, **(head or {}))
    if under:
        under(u, h)
    merge(u, h)
    u.ellipse(19.6, 15.4, 3.6, 3.7, P.BELLY, to="dt", keep=lambda x, y: (x, y) in body and (x, y) not in h.px and y >= 12)
    for x, y in ((9, 10), (10, 10), (13, 9), (14, 9), (17, 9), (6, 11)):
        if (x, y) in u.px and (x, y - 1) in u.px and (x, y) not in h.px:
            u.dt[(x, y)] = P.SPOT
    if cheeks:                                                     # 볼 빵빵 (턱 뒤쪽이 둥글게 부풀어 아래로 볼록)
        u.ellipse(hx + 4.8, hy + 9.0, 3.3, 2.5)
        for dx in (0, 1):
            u.dt[(rnd(hx + 4.4) + dx, rnd(hy + 8.6))] = P.BLUSH
    if throat:                                                     # 꿀꺽 넘어가는 목 혹 (목 앞으로 볼록)
        u.ellipse(23.4, 12.8, 2.0, 1.8, P.BELLY)
        for (x, y) in list(u.px):
            if u.px[(x, y)] == P.BELLY and math.hypot(x - 23.4, y - 12.8) > 1.3 and x >= 22:
                u.dt[(x, y)] = (226, 206, 132, 255)
    cv.paste(u, 0, bob, tilt, 15)
    s = Cv(P)
    trex_leg(s, (13.4, hyb), near, P.BODY)
    cv.overlay(s)
    a = Cv(P)
    if arms_up:
        (na0, na1) = arms_up[1]
        a.capsule(*na0, *na1, 0.8, 0.7)
        a.dt[(rnd(na1[0]), rnd(na1[1]))] = P.CLAW
    else:
        ay = 13.2 + bob + rnd((23 - 15) * tilt)
        a.capsule(22.4, ay, 24.4, ay + 0.8 + arm, 0.8, 0.7)
        a.dt[(25, rnd(ay + 0.8 + arm))] = P.CLAW
    cv.overlay(a)
    for (x, y, r, al) in dust:
        puff(cv, x, y, r, al)
    cv.finish()
    cv.head = h
    return cv


def trex_meat(i):
    """만화 고기 우걱우걱 (순서대로 4장, 고기는 앱이 prop_meat.png 로 따로 그려 한 입씩 줄임 — 시트엔 고기 없음):
    0 입을 쩍 벌려 덥석 (앞으로 숙임) → 1 입 다물고 볼 빵빵 오물오물 (웃으며 질끈) → 2 고개 젖혀 꿀꺽 (목 혹) → 3 만족 트림 (눈 반달, 작게 벌린 입)"""
    if i == 0:
        return trex_pose(head=dict(up=-6, jaw=44), hy=2, tilt=0.05, arm=-1).image()
    if i == 1:
        cv = trex_pose(head=dict(up=2, jaw=0, mood="happy"), hy=1, cheeks=True)
        return cv.image()
    if i == 2:
        return trex_pose(head=dict(up=-26, jaw=0, mood="squeeze"), hy=3, throat=True).image()
    cv = trex_pose(head=dict(up=-10, jaw=12, mood="happy"), hy=3)
    a, b = cv.head.mouth                                           # 꺼억 — 작은 트림 방울
    bx_, by_ = rnd(min(a[0] + 0.5, 30.0)), rnd(a[1] - 2.6)
    for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
        cv.top[(bx_ + dx, by_ + dy)] = (176, 184, 202, 255) if abs(dx) + abs(dy) == 2 else (240, 244, 250, 255)
    cv.top[(bx_, by_)] = (252, 252, 255, 255)
    return cv.image()


# ── 트리케라톱스: 머리 + 프릴을 한 덩이로 돌리기 ─────────────────────────
def trike_head_group(P, hx, hy, ang=0.0, mood="normal", blink=False):
    g = Cv(P)
    trike_frill(g, hx + 0.4, hy + 6.6)
    trike_head(g, hx, hy, mood if mood not in ("fierce", "squeeze") else "normal", blink, eye=False)
    pivot = (hx + 1.6, hy + 8.0)
    r = rotated(g, ang, pivot)
    ex, ey = rot_pt((hx + 5.5, hy + 5.5), ang, pivot)
    put_eye(r, rnd(ex - 0.5), rnd(ey - 0.5), mood, blink)
    r.horn = rot_pt((hx + 11, hy + 0), ang, pivot)                 # 가까운 이마 뿔 끝
    r.horn2 = rot_pt((hx + 12, hy + 4), ang, pivot)                # 코뿔 끝
    r.beak = rot_pt((hx + 12.5, hy + 8.5), ang, pivot)
    return r


def trike_pose(legs, bob=0, tilt=0.0, sway=0, ang=0.0, head_dx=0, head_dy=0, mood="normal", blink=False, dust=(), body_rx=8.2, body_dx=0,
               folded=False, body_dy=0.0, body_ry=5.0):
    """행동용 트리케라톱스. legs = (가까운 뒷발, 가까운 앞발, 먼 뒷발, 먼 앞발) 각각 (발 x, 들림). 꼬리 끝 x≈3.6 (짧게)"""
    P = TRIKE
    cv = Cv(P)
    nh, nf, fh, ff = legs
    ly = 17 + bob
    if not folded:
        stump(cv, (11 + body_dx, ly), fh, P.FAR, 1.5)
        stump(cv, (20.2 + body_dx, ly), ff, P.FAR, 1.5)
    u = Cv(P)
    bd = body_dy
    u.path([(7 + body_dx, 14.5 + bd), (4.4 + body_dx, 15.6 + bd + sway * 0.5), (3.6 + body_dx, 16.2 + bd + sway)], [2.3, 1.3, 0.55])
    u.ellipse(12.8 + body_dx, 14.6 + bd + (5.0 - body_ry), body_rx, body_ry)
    if not folded:
        u.ellipse(12.6 + body_dx, 17.8 + bd, body_rx - 2.7, 1.5, P.BELLY, to="dt", keep=lambda x, y: (x, y) in u.px and (x, y + 1) in u.px)
    g = trike_head_group(P, 19 + head_dx, 2 + head_dy, ang, mood, blink)
    u.overlay(g)
    cv.paste(u, 0, bob, tilt, 15)
    tl = lambda x: rnd((x - 15) * tilt)
    s = Cv(P)
    if folded:                                                     # 접은 다리 (배 밑에 꼭)
        s.ellipse(8.8 + body_dx, 20.2, 3.0, 1.8)
        s.dt[(rnd(8.8 + body_dx) + 2, 21)] = P.CLAW
        cv.overlay(s)
        s = Cv(P)
        s.ellipse(18.0 + body_dx, 20.8, 2.3, 1.3)
        s.dt[(rnd(18.0 + body_dx) + 2, 21)] = P.CLAW
        cv.overlay(s)
    else:
        stump(s, (8.4 + body_dx, ly), nh, P.BODY, 1.5, thigh=(3.0, 3.2))
        cv.overlay(s)
        s = Cv(P)
        stump(s, (17.8 + body_dx, ly + tl(17.8)), nf, P.BODY, 1.5)
        cv.overlay(s)
    for (x, y, r, al) in dust:
        puff(cv, x, y, r, al)
    cv.finish()
    cv.head = g
    cv.tl = tl
    return cv


def trike_headbutt(i):
    """박치기 (순서대로 3장): 0 뒷발에 힘 싣고 고개 번쩍 (뒤로 젖힘) → 1 고개 숙여 앞으로 돌진 → 2 쾅! 뿔 앞으로 · 몸이 눌림 · 뿔 끝에 별"""
    P = TRIKE
    if i == 0:
        cv = trike_pose(((9.0, 0), (19.0, 4), (11.6, 0), (21.2, 3)), bob=0, tilt=-0.12, ang=-16, head_dy=-1, mood="fierce", sway=1)
        return cv.image(dx=-2)
    if i == 1:
        cv = trike_pose(((5.0, 0), (21.6, 2), (7.6, 1), (23.6, 1)), bob=0, tilt=0.08, ang=22, head_dx=-1, head_dy=2, mood="fierce", sway=-1,
                        dust=[(5.2, 21.2, 1.5, 200), (7.8, 21.6, 1.1, 170)])
        for y, ln, x1 in ((6, 3, 7), (11, 3, 6), (15, 3, 6)):      # 돌진 속도선 (뒤로, dx -2 뒤에도 x ≥ 1)
            act_line(cv, x1 - ln + 1, y, x1, y, SPEED, "fx")
        return cv.image(dx=-2)
    cv = trike_pose(((8.6, 0), (20.4, 0), (11.0, 0), (22.4, 0)), bob=1, tilt=0.06, ang=28, head_dx=-1, head_dy=3, mood="squeeze", body_rx=7.5, body_dx=1)
    hx_, hy_ = cv.head.horn
    sx_, sy_ = min(hx_ + 1.2, 31.0), hy_ + 0.6                     # 별은 화면 안쪽 (dx -2 뒤 x ≤ 29)
    star(cv, sx_, sy_)
    arc_marks(cv, sx_, sy_, 3.4, -150, -60, n=3, ln=1, col=STAR_EDGE)
    return cv.image(dx=-2)


# ── 스테고: 꼬리 모양을 바꿔 그리는 행동용 몸 ──────────────────────────────
def st_spikes(t, pts, n_len=3.8, both=False, col=None):
    """꼬리 끝 가시 (꼬리 끝 방향 기준 '위'쪽으로 뒤를 향해 두 개, both = 아래쪽도)"""
    P = t.P
    col = col or P.PLATE
    (ax, ay), (bx, by) = pts[-2], pts[-1]
    L = math.hypot(bx - ax, by - ay) or 1
    dx, dy = (bx - ax) / L, (by - ay) / L                          # 꼬리 끝 방향
    nx, ny = dy, -dx                                               # 꼬리의 '위' (오른손 법선)
    if ny > 0:
        nx, ny = -nx, -ny
    for back in (0.6, 2.6):
        x0, y0 = bx - dx * back, by - dy * back
        for side in ((1, -1) if both else (1,)):
            ex, ey = x0 + side * nx * n_len + dx * 1.2, y0 + side * ny * n_len + dy * 1.2
            t.capsule(x0, y0, ex, ey, 0.75, 0.22, col)
            t.dt[(rnd(ex), rnd(ey))] = P.CLAW


def stego_pose(legs=((9.4, 0), (18.6, 0), (11.8, 0), (20.6, 0)), bob=0, tilt=0.0, tail=None, spikes_both=False,
               head=(27.6, 15.6), mood="normal", blink=False, glow=False, plate_dy=0, folded=False, dust=(), mouth=None, breathe=False):
    """행동용 스테고. tail = (점들, 굵기들) — 끝에 가시가 붙는다. head = (머리 중심 x, y)"""
    P = STEGO
    cv = Cv(P)
    nh, nf, fh, ff = legs
    PL, PLH, PLF = (P.PLATE, P.PLATE_HI, P.PLATE_FAR) if not glow else ((255, 84, 52, 255), (255, 214, 120, 255), (226, 60, 44, 255))
    if not folded:
        stump(cv, (11.8, 17 + bob), fh, P.FAR, 1.45)
        stump(cv, (20.6, 18 + bob), ff, P.FAR, 1.35)
    u = Cv(P)
    for x, h in ((10, 4), (15, 5), (20, 3)):
        st_plate(u, x, rnd(st_top(x)) + 1 + plate_dy, h, PLF)
    pts, rs = tail or ([(8, 14.0), (5.4, 12.0), (2.8, 9.4)], [2.7, 1.7, 0.9])
    t = Cv(P)
    st_spikes(t, pts, both=spikes_both)
    t.path(pts, rs)
    merge(u, t)
    cx, cy, rx, ry = ST_BODY
    u.ellipse(cx, cy, rx, ry, keep=lambda x, y: y <= 19)
    if breathe:                                                    # 숨 들이쉼: 등만 1칸 볼록
        u.ellipse(cx, cy - 0.5, rx - 0.3, ry + 0.5, keep=lambda x, y: y <= 19)
    u.ellipse(14.6, 18.6, 6.5, 1.5, P.BELLY, to="dt", keep=lambda x, y: (x, y) in u.px and (x, y + 1) in u.px and u.px[(x, y)] == P.BODY)
    hx, hy = head
    u.capsule(21.5, 14.6, hx - 2.2, hy, 2.4, 2.2)
    u.ellipse(hx, hy, 3.9, 3.2)
    u.put(rnd(hx) + 3, rnd(hy) + 1); u.put(rnd(hx) + 3, rnd(hy))
    ix, iy = rnd(hx) - 1, rnd(hy) - 2
    put_eye(u, ix, iy, mood, blink)
    u.dt[(ix - 2, iy + 3)] = P.BLUSH; u.dt[(ix - 1, iy + 3)] = P.BLUSH
    my = rnd(hy) + 1
    mx = rnd(hx)
    if mouth == "open":
        for p in ((mx + 1, my), (mx + 2, my), (mx + 1, my + 1), (mx + 2, my + 1)):
            u.dt[p] = P.MOUTH_IN
        u.dt[(mx, my)] = P.MOUTH; u.dt[(mx + 3, my)] = P.MOUTH
    elif mouth == "smile" or mood == "happy":
        for p in ((mx, my), (mx + 1, my + 1), (mx + 2, my + 1), (mx + 3, my)):
            u.dt[p] = P.MOUTH
    else:
        for p in ((mx, my), (mx + 1, my + 1), (mx + 2, my + 1), (mx + 3, my + 1)):
            u.dt[p] = P.MOUTH
    pl = Cv(P)
    for x, h in ((7, 4), (12, 6), (17, 6), (22, 3)):
        st_plate(pl, x, rnd(st_top(x)) + 1 + plate_dy, h, PL, PLH)
    u.overlay(pl)
    cv.paste(u, 0, bob, tilt, 15)
    s = Cv(P)
    if folded:                                                     # 다리를 접고 엎드림
        s.ellipse(10.0, 19.0 + bob, 3.0, 2.2)
        s.rect(8, 21, 12, 22)
        s.dt[(12, 22)] = P.CLAW; s.dt[(10, 22)] = P.CLAW
        cv.overlay(s)
        s = Cv(P)
        s.rect(18, 20, 22, 22)
        s.dt[(22, 22)] = P.CLAW; s.dt[(20, 22)] = P.CLAW
        cv.overlay(s)
    else:
        stump(s, (9.4, 17 + bob), nh, P.BODY, 1.5, thigh=(3.1, 3.4))
        cv.overlay(s)
        s = Cv(P)
        stump(s, (18.6, 18 + bob), nf, P.BODY, 1.4)
        cv.overlay(s)
    for (x, y, r, al) in dust:
        puff(cv, x, y, r, al)
    cv.finish()
    cv.tail_pts = pts
    return cv


def stego_tailswing(i):
    """꼬리 가시 휘두르기 (순서대로 3장): 0 꼬리를 등 위로 높이 치켜듦 → 1 휙! 휘두르는 중 (자국) → 2 탁! 가시 쫙 펴고 내려침 (별)"""
    if i == 0:
        tail = ([(8, 13.4), (5.4, 9.8), (5.0, 5.6), (6.8, 2.6)], [2.7, 2.0, 1.3, 0.85])
        cv = stego_pose(tail=tail, tilt=0.04, head=(27.6, 16.4), mood="fierce", bob=0,
                        legs=((10.4, 0), (18.6, 0), (12.6, 0), (20.6, 0)))
        return cv.image()
    if i == 1:
        tail = ([(8, 14.0), (5.2, 13.0), (2.8, 12.0)], [2.7, 1.8, 0.95])
        cv = stego_pose(tail=tail, head=(27.6, 16.0), mood="fierce", legs=((9.4, 0), (18.6, 0), (11.8, 0), (20.6, 0)))
        for r_, a0, a1 in ((7.6, -100, -160), (9.2, -96, -150)):    # 휘두른 자국 (치켜든 곳 → 지금 자리)
            pts_ = [(8 + r_ * math.cos(math.radians(a)), 13.6 + r_ * math.sin(math.radians(a))) for a in range(a0, a1 - 1, -6)]
            for (x0, y0), (x1, y1) in zip(pts_, pts_[1:]):
                if min(x0, x1) >= 1:
                    act_line(cv, x0, y0, x1, y1, ACT_LINE, "fx")
        return cv.image()
    tail = ([(8, 14.6), (5.8, 16.4), (4.4, 17.6)], [2.7, 1.8, 0.95])
    cv = stego_pose(tail=tail, tilt=-0.03, spikes_both=True, head=(27.6, 15.4), mood="squeeze",
                    legs=((8.6, 0), (19.2, 0), (11.2, 0), (21.2, 0)))
    star(cv, 4, 20, big=True)
    return cv.image()


# ── 익룡: 머리(볏·부리)를 한 덩이로 돌리기 ─────────────────────────────────
def ptero_head_group(P, ang=0.0, open_=False, mood="normal", blink=False, pivot=(21.4, 10.6)):
    g = Cv(P)
    g.poly([(22.6, 5.0), (13.4, 0.8), (13.2, 2.8), (21.0, 8.8)], P.CREST)
    g.ellipse(23.4, 8.2, 3.6, 3.4)
    if open_:
        g.poly([(25.8, 6.6), (32.0, 8.8), (31.4, 9.6), (25.8, 9.5)], P.BEAK)
        g.poly([(25.8, 9.4), (30.6, 10.3), (30.6, 11.2), (25.8, 11.6)], P.MOUTH_IN)
        g.poly([(25.8, 11.0), (30.8, 11.2), (30.2, 12.4), (25.8, 12.4)], P.BEAK)
    else:
        g.poly([(25.8, 6.6), (32.0, 9.0), (32.0, 10.2), (25.8, 11.6)], P.BEAK)
    for (x, y), c in list(g.px.items()):
        if c == P.CREST and (x, y - 1) not in g.px:
            g.dt[(x, y)] = P.CREST_HI
        if c == P.BEAK and (x, y + 1) not in g.px:
            g.dt[(x, y)] = P.BEAK_DK
    if not open_:
        for x in range(27, 31):
            g.dt[(x, 10)] = P.BEAK_DK
        g.dt[(26, 9)] = P.BEAK_DK
    g.dt[(21, 10)] = P.BLUSH; g.dt[(22, 10)] = P.BLUSH
    r = rotated(g, ang, pivot)
    ex, ey = rot_pt((22.5, 7.5), ang, pivot)
    put_eye(r, rnd(ex - 0.5), rnd(ey - 0.5), mood, blink)
    r.tip = rot_pt((31.4, 9.6), ang, pivot)
    r.mid = rot_pt((28.6, 9.8), ang, pivot)
    return r


def ptero_pose(pose="high", bob=0, tilt=0.0, ang=0.0, open_=False, mood="normal", blink=False, throat=False, dy=0):
    """행동용 익룡 (공중): 머리 덩이를 돌릴 수 있다. throat = 꿀꺽 목 혹"""
    P = PTERO
    cv = Cv(P)
    cv.capsule(11.6, 14.8, 8.2, 15.8, 1.0, 0.4)
    cv.ellipse(15.6, 14.0, 5.0, 3.3)
    cv.capsule(19.2, 12.6, 21.6, 10.4, 1.8, 1.7)
    g = ptero_head_group(P, ang, open_, mood, blink)
    merge(cv, g)
    if throat:                                                     # 꿀꺽 목 혹 (목 앞으로 볼록)
        cv.ellipse(22.6, 12.8, 1.9, 1.8, P.BELLY)
        for (x, y) in list(cv.px):
            if cv.px[(x, y)] == P.BELLY and math.hypot(x - 22.6, y - 12.8) > 1.2:
                cv.dt[(x, y)] = P.HI
    cv.ellipse(16.2, 15.4, 3.6, 1.7, P.BELLY, to="dt", keep=lambda x, y: (x, y) in cv.px and cv.px[(x, y)] == P.BODY)
    for p_, c_ in (((12, 16), P.DK), ((13, 16), P.DK), ((11, 16), P.CLAW)):
        if p_ in cv.px:
            cv.dt[p_] = c_
    cv.overlay(pt_wing(P, pose))
    cv.finish()
    cv.head = g
    cv.dy = dy
    return cv


def ptero_fisheat(i):
    """물고기 먹기 (공중, 날개 펼침, 순서대로 3장): 0 물고기를 부리에 가로로 물고 → 1 고개를 휙 젖혀 물고기가 부리 위로 붕 → 2 꿀꺽 (부리 위로 다물고 목 혹 · 반짝)"""
    if i == 0:
        cv = ptero_pose("high", ang=6, open_=False)
        img = cv.image(dy=2)
        tx, ty = cv.head.mid
        img.alpha_composite(fish_cv(tx + 0.4, ty + 3.4, 84).image(dy=0), (0, 0))
        return img
    if i == 1:
        cv = ptero_pose("high", ang=-36, open_=True)
        img = cv.image(dy=5)
        tx, ty = cv.head.tip
        f = fish_cv(min(tx - 2.2, 25.4), max(ty + 5 - 4.4, 2.6), 196)    # 부리 위로 붕 뜬 물고기 (옆으로 누워 빙글)
        img.alpha_composite(f.image())
        return img
    cv = ptero_pose("high", ang=-32, open_=False, mood="happy", throat=True)
    tx, ty = cv.head.tip
    sparkle(cv, min(tx + 1.0, 31), ty - 2.0)
    return cv.image(dy=5)


# ── 티라노 나머지 행동 ────────────────────────────────────────────────────
def trex_roar(i):
    """포효 (순서대로 3장): 고개가 점점 들리고 입이 점점 크게 → 마지막 장은 크게 어흥 (음파)"""
    up, jaw, hy = [(-8, 14, 2), (-18, 28, 3), (-26, 44, 4)][i]
    cv = trex_pose(head=dict(up=up, jaw=jaw, mood="squeeze" if i == 2 else "normal"), hx=16, hy=hy, arm=-1, bob=0 if i < 2 else 1)
    if i == 2:
        a, b = cv.head.mouth
        mx, my = (a[0] + b[0]) / 2 + 0.5, (a[1] + b[1]) / 2
        arc_marks(cv, mx, my, 1.8, -70, 10, n=3, ln=2)
    return cv.image()


def trex_chomp(i):
    """와작 (반복 2장): 0 입을 쩍 벌림 → 1 콱 다묾 (딱! 반짝)"""
    if i == 0:
        return trex_pose(head=dict(up=-10, jaw=40), hy=2).image()
    cv = trex_pose(head=dict(up=4, jaw=0, mood="squeeze"), hy=1)
    sparkle(cv, 31, 2)
    act_line(cv, 29, 0, 29, 1)
    act_line(cv, 31, 5, 32, 5)
    return cv.image()


def trex_stomp(i):
    """쿵쿵 (반복 2장): 0 한 발을 번쩍 → 1 쾅 내려찍고 몸이 출렁 (흙먼지 · 충격선)"""
    if i == 0:
        return trex_pose(near=(19, 3), far=(12, 0), bob=-1, tilt=-0.04, arm=-1, head=dict(up=-6, jaw=0)).image()
    cv = trex_pose(near=(15, 0), far=(12, 0), bob=1, tilt=0.02, head=dict(up=2, jaw=18),
                   dust=[(12.0, 21.4, 1.7, 225), (21.4, 21.4, 1.6, 215)])
    for x0, y0, x1, y1 in ((11, 18, 10, 16), (17, 17, 17, 15), (22, 18, 23, 16)):
        act_line(cv, x0, y0, x1, y1)
    return cv.image()


def trex_shortarms(i):
    """짧은 팔 개그 (반복 2장): 작은 팔을 머리 쪽으로 낑낑 뻗지만 닿지 않음 — 1번 장엔 땀방울"""
    w = (0, 1)[i]
    arms = (((21.8, 13.8), (24.6, 12.4 - w * 0.5)), ((22.4, 14.4), (25.8, 13.0 - w * 0.5)))   # 가슴 앞 빈 곳으로 쭉 (턱과 2칸 틈 — 끝내 못 닿음)
    cv = trex_pose(head=dict(up=-18, jaw=0, mood="normal" if i == 0 else "squeeze"), hy=2, arms_up=arms)
    if i == 1:
        sweat_drop(cv, 15, 0)
        act_line(cv, 26, 12, 27, 12)
        act_line(cv, 25, 14, 26, 14)
    return cv.image()


def trex_nap(i):
    """낮잠 (3장): 0 = 눕는 중 (다리 접으며 몸이 내려가고 고개가 떨어짐) · 1·2 = 바닥에 납작 엎드려 쿨쿨 (눈은 일자, 배가 1칸 들썩).
    앱은 처음·끝에 0번, 그 사이엔 1·2번을 번갈아 보여 준다"""
    P = TREX
    if i == 0:
        return trex_pose(near=(14, 0), far=(16, 0), bob=3, sway=2, head=dict(up=12, jaw=0, mood="sleep"), hy=5).image()
    cv = Cv(P)
    up = i - 1
    cv.path([(9.4, 18.6), (5.4, 20.6), (3.2, 21.2), (2.8, 19.6)], [2.6, 1.7, 0.9, 0.45])     # 바닥에 만 꼬리
    cv.rect(18, 21, 21, 22, P.FAR)
    cv.ellipse(14.4, 17.8 - up * 0.5, 7.0, 3.8 + up * 0.5)                                    # 엎드린 몸 (숨)
    cv.ellipse(19.4, 16.6, 3.2, 3.2)
    body = set(cv.px)
    h = trex_head_rig(P, 17, 12, up=3, jaw=0, mood="sleep")
    merge(cv, h)
    for x, y in ((9, 15 - up), (10, 15 - up), (13, 14 - up), (14, 14 - up), (17, 14 - up)):
        if (x, y) in body and (x, y) not in h.px:
            cv.dt[(x, y)] = P.SPOT
    s = Cv(P)                                                                                  # 접은 뒷다리
    s.ellipse(12.2, 18.6, 3.0, 2.5)
    s.rect(12, 21, 16, 22)
    s.put(17, 22)
    s.dt[(17, 22)] = P.CLAW; s.dt[(15, 22)] = P.CLAW
    cv.overlay(s)
    cv.finish()
    return cv.image()


# ── 트리케라톱스 나머지 행동 ──────────────────────────────────────────────
def trike_charge(i):
    """뿔 돌진 (반복 2장): 고개를 낮춰 뿔을 앞으로, 다리는 질주 · 뒤로 흙먼지와 속도선"""
    legs = [((5, 0), (21, 2), (8, 1), (23, 1)), ((12, 0), (16, 1), (14, 0), (18, 2))][i]
    cv = trike_pose(legs, bob=(-1, 0)[i], tilt=0.07, ang=24, head_dx=-1, head_dy=2, mood="fierce", sway=(1, -1)[i],
                    dust=[(5.4, 21.0, 1.6, 205)] if i == 0 else [(9.6, 21.3, 1.3, 205), (5.0, 20.4, 1.9, 120)])
    for y, x1 in ((6 + i, 7), (11, 6), (15 - i, 7)):
        act_line(cv, x1 - 2, y, x1, y, SPEED, "fx")
    return cv.image(dx=-2)


def trike_headshake(i):
    """머리 흔들기 (반복 2장): 프릴째 고개를 이쪽 · 저쪽으로 갸웃"""
    ang = (-14, 12)[i]
    cv = trike_pose(((8.4, 0), (17.8, 0), (11, 0), (20.2, 0)), ang=ang, head_dx=-1, head_dy=(0, 1)[i], mood="happy")
    for x0, y0, x1, y1 in (((15, 2, 14, 1), (16, 0, 16, 0)) if i == 0 else ((28, 1, 29, 0), (30, 3, 31, 2))):
        act_line(cv, x0, y0, x1, y1)
    return cv.image(dx=-1)


def fern(cv, x, y, h=5, lean=1, layer="top"):
    """작은 고사리 (줄기 + 양옆 잎) — 아래 (x, y) 에서 위로"""
    L = getattr(cv, layer)
    y = rnd(y)
    for k in range(h):
        sx = rnd(x + lean * k * 0.35)
        L[(sx, y - k)] = LEAF_DK
        if k % 2 == 1:
            L[(sx - 1, y - k)] = LEAF
            L[(sx + 1, y - k - 1)] = LEAF
    L[(rnd(x + lean * (h - 1) * 0.35), y - h)] = LEAF_HI


def trike_graze(i):
    """풀 뜯기 (반복 2장): 고개를 땅까지 숙여 고사리를 물고 → 오물오물 (고사리가 짧아짐)"""
    cv = trike_pose(((8.4, 0), (17.8, 0), (11, 0), (20.2, 0)), ang=38, head_dx=-2, head_dy=3, mood="talk" if i == 0 else "happy")
    bx, by = cv.head.beak
    if i == 0:
        fern(cv, bx + 0.4, 22, h=6, lean=-1)
    else:
        fern(cv, bx - 0.6, by + 1.2, h=3, lean=1)
        fern(cv, bx + 1.4, 22, h=2, lean=0)
    return cv.image(dx=-2)


MUD = (132, 92, 58, 255)
MUD_HI = (170, 126, 84, 255)
MUD_DK = (96, 64, 40, 255)


def trike_wallow(i):
    """진흙 목욕 (반복 2장): 진흙 웅덩이에 옆으로 드러누워 다리를 버둥 · 흙탕물 튐"""
    P = TRIKE
    cv = Cv(P)
    for y in range(19, 24):                                                    # 진흙 웅덩이 (몸 뒤)
        for x in range(2, 32):
            d = ((x - 16.5) / 14.4) ** 2 + ((y - 21.8) / 2.2) ** 2
            if d <= 1.0:
                cv.fx[(x, y)] = MUD_DK if d > 0.72 else (MUD_HI if y == 20 else MUD)
    u = Cv(P)
    u.path([(7, 17.4), (4.6, 18.4), (3.6, 18.8)], [2.2, 1.2, 0.5])
    u.ellipse(13.2, 16.8, 8.0, 4.4)
    u.ellipse(13.0, 19.4, 5.6, 1.4, P.BELLY, to="dt", keep=lambda x, y: (x, y) in u.px)
    g = trike_head_group(P, 18, 6, 14, "happy")
    u.overlay(g)
    for x, y in ((9, 14), (14, 13), (17, 16), (6, 17)):                       # 진흙 얼룩
        if (x, y) in u.px:
            u.dt[(x, y)] = MUD
    r = rotated(u, (-6, 5)[i], (15, 18))
    merge(cv, r)
    kick = (0, 1)[i]
    for (t, e) in ((((18.4, 18.6), (23.0, 15.6 + kick * 3))), (((9.2, 19.0), (4.6, 16.2 + (1 - kick) * 3)))):   # 버둥대는 다리
        s = Cv(P)
        s.capsule(*t, *e, 1.45, 1.3)
        s.dt[(rnd(e[0]), rnd(e[1]))] = P.CLAW
        cv.overlay(s)
    for (x, y) in (((5, 17), (28, 18), (26, 16)) if i == 0 else ((4, 15), (29, 17), (8, 17))):  # 흙탕물 방울
        cv.top[(x, y)] = MUD
        cv.top[(x, y + 1)] = MUD_DK
    cv.finish()
    return cv.image(dx=-1)


# ── 스테고 나머지 행동 ─────────────────────────────────────────────────────
def plant(cv, x, y):
    """낮은 풀 한 포기 (땅에서 위로)"""
    for dx, h in ((-2, 2), (-1, 3), (0, 4), (1, 3), (2, 2)):
        for k in range(h):
            cv.top[(x + dx, y - k)] = LEAF if k < h - 1 else LEAF_HI
        cv.top[(x + dx, y)] = LEAF_DK


def stego_graze(i):
    """풀 뜯기 (반복 2장): 고개를 땅의 풀까지 숙여 덥석 → 오물오물 (입에 잎)"""
    cv = stego_pose(head=(27.8, 19.0), mouth="open" if i == 0 else None, mood="normal" if i == 0 else "happy")
    plant(cv, 30, 22)
    if i == 1:
        cv.top[(31, 20)] = LEAF; cv.top[(32, 19)] = LEAF_HI
    return cv.image()


def stego_nap(i):
    """낮잠 (3장): 0 = 눕는 중 (다리를 굽혀 몸이 내려가고 고개가 처짐) · 1·2 = 다리 접고 납작 엎드려 쿨쿨 (눈은 일자, 등이 1칸 들썩)"""
    if i == 0:
        return stego_pose(bob=2, head=(27.6, 18.4 - 2), mood="sleep").image()
    return stego_pose(folded=True, bob=3, head=(27.6, 19.6 - 3), mood="sleep", breathe=i == 2, plate_dy=-1 if i == 2 else 0).image()


def stego_sunbask(i):
    """햇볕 쬐기 (반복 2장): 눈 감고 흐뭇하게 서 있기 — 1번 장엔 등판이 빨갛게 달아오름 (등판 = 체온 조절판)"""
    cv = stego_pose(mood="happy", glow=i == 1)
    if i == 1:
        for x0 in (11, 16, 21):                                                # 아지랑이
            for k in range(3):
                cv.fx[(x0 + (k % 2), 2 - k)] = (255, 170, 110, 200)
    return cv.image()


# ── 브라키오: 목·머리를 자유롭게 (머리는 돌려 그리고 눈은 또렷하게) ───────
def brachio_head_rig(P, hx, hy, ang=0.0, jaw=0, mood="normal", blink=False, flip=False):
    rows = list(BRACHIO_HEAD)
    if jaw:
        rows = BRACHIO_HEAD[:5] + ["ggggmmmmm"] + (["gggggmmm."] if jaw > 1 else []) + ["gggggggg.", ".gggggg.."]
    if flip:
        rows = [r[::-1] for r in rows]
    g = Cv(P)
    g.art(hx, hy, rows, {"g": P.BODY, "h": P.HI, "m": P.MOUTH_IN})
    fx_ = (lambda c: hx + 8 - c) if flip else (lambda c: hx + c)
    g.dt[(fx_(2), hy + 4)] = P.BLUSH; g.dt[(fx_(3), hy + 4)] = P.BLUSH
    if jaw:
        g.dt[(fx_(6), hy + 5 + jaw - 1)] = (240, 120, 140, 255)
        g.dt[(fx_(4), hy + 4)] = P.MOUTH
    elif mood == "happy":
        for c, r in ((4, 4), (5, 5), (6, 5), (7, 5), (8, 4)):
            g.dt[(fx_(c), hy + r)] = P.MOUTH
    else:
        for c, r in ((4, 4), (5, 5), (6, 5), (7, 5)):
            g.dt[(fx_(c), hy + r)] = P.MOUTH
    pivot = ((hx + 7.0) if flip else (hx + 1.5), hy + 5.0)
    r = rotated(g, ang, pivot)
    ex, ey = rot_pt(((hx + 3.5) if flip else (hx + 4.5), hy + 2.5), ang, pivot)
    put_eye(r, rnd(ex - 0.5), rnd(ey - 0.5), mood, blink)
    r.snout = rot_pt(((hx + 0.5) if flip else (hx + 8.5), hy + 4.5), ang, pivot)
    return r


def brachio_pose(legs=((8.4, 0), (15.4, 0), (10.6, 0), (17.6, 0)), bob=0, neck=None, head=(23, 1), ang=0.0, jaw=0,
                 mood="normal", blink=False, sway=0, folded=False, flip=False, body=None, tail=None):
    """행동용 브라키오 (좌우 1칸 여백 유지). neck = 목 점들, head = 머리 왼쪽 위"""
    P = BRACHIO
    cv = Cv(P)
    nh, nf, fh, ff = legs
    if not folded:
        stump(cv, (10.6, 16.6 + bob), fh, P.FAR, 1.4)
        stump(cv, (17.6, 15.4 + bob), ff, P.FAR, 1.4)
    u = Cv(P)
    tp, tr = tail or ([(7.2, 14.2), (4.8, 15.6 + sway * 0.4), (3.2, 17.4 + sway * 0.6), (2.6, 19.4 + sway * 0.8)], [2.2, 1.5, 0.95, 0.4])
    u.path(tp, tr)
    bx, by, brx, bry, bang = body or (12.8, 14.0, 7.0, 4.3, -13)
    u.oval(bx, by, brx, bry, bang)
    npts = neck or [(16.6, 11.8), (19.6, 8.4), (22.6, 5.6)]
    u.path(npts, [2.4, 1.8, 1.6, 1.5][:len(npts)])
    body_px = set(u.px)
    h = brachio_head_rig(P, head[0], head[1], ang, jaw, mood, blink, flip)
    merge(u, h)
    for x, y in ((8, 12), (9, 12), (12, 11), (13, 11), (15, 9), (16, 9), (10, 14), (14, 13), (6, 15)):
        y2 = y + (by - 14.0)
        if (x, rnd(y2)) in body_px and (x, rnd(y2) - 1) in u.px and (x, rnd(y2)) not in h.px:
            u.dt[(x, rnd(y2))] = P.SPOT
    cv.paste(u, 0, bob)
    s = Cv(P)
    if folded:
        s.ellipse(8.6, 20.4, 2.6, 1.6)
        cv.overlay(s)
        s = Cv(P)
        s.ellipse(17.0, 20.6, 2.4, 1.5)
        s.dt[(19, 21)] = P.CLAW
        cv.overlay(s)
    else:
        stump(s, (8.4, 16.6 + bob), nh, P.BODY, 1.55, thigh=(2.9, 3.2))
        cv.overlay(s)
        s = Cv(P)
        stump(s, (15.4, 15.4 + bob), nf, P.BODY, 1.5)
        cv.overlay(s)
    cv.finish()
    cv.head = h
    return cv


def brachio_reach(i):
    """높은 잎 따 먹기 (순서대로 3장): 목이 점점 서서 거의 수직 → 입을 위로 쭉 → 마지막 장은 잎을 물고 오물오물"""
    if i == 0:
        cv = brachio_pose(neck=[(16.6, 11.8), (19.0, 8.0), (20.8, 6.6)], head=(20, 2), ang=-26)
    else:
        cv = brachio_pose(neck=[(16.6, 11.8), (17.6, 8.8), (18.4, 7.0)], head=(17, 2), ang=-60,
                          jaw=1 if i == 1 else 0, mood="happy" if i == 2 else "normal")
    if i == 2:
        sx, sy = cv.head.snout
        for p, c in (((0, 0), LEAF), ((1, -1), LEAF), ((1, 0), LEAF_DK), ((2, -1), LEAF_HI), ((0, -1), LEAF_HI)):
            cv.top[(rnd(sx) + p[0], rnd(sy) + p[1])] = c
    return cv.image()


def brachio_bellow(i):
    """우렁찬 울음 (반복 2장): 고개를 들고 입을 벌림 → 더 크게 (음파)"""
    cv = brachio_pose(neck=[(16.6, 11.8), (19.0, 8.6), (21.0, 7.0)], head=(20, 2), ang=(-22, -28)[i], jaw=(1, 2)[i],
                      mood="normal" if i == 0 else "squeeze")
    sx, sy = cv.head.snout
    arc_marks(cv, sx + 0.6, sy - 0.4, 1.4 + i * 0.6, -80, 0, n=3, ln=1 + i)
    return cv.image()


def brachio_drink(i):
    """물 마시기 (반복 2장): 긴 목을 땅까지 내려 웅덩이를 할짝 (혀) → 잔물결"""
    cv = brachio_pose(neck=[(16.6, 12.6), (20.8, 14.2), (23.6, 17.2)], head=(22, 12), ang=40, mood="happy" if i else "normal")
    for x in range(25, 33):                                                    # 웅덩이 (머리 앞 땅바닥)
        for y in (22, 23):
            d = ((x - 28.6) / 3.8) ** 2 + ((y - 22.6) / 1.1) ** 2
            if d <= 1.0:
                cv.fx[(x, y)] = (110, 178, 240, 235) if d > 0.4 or y == 23 else (200, 236, 255, 235)
    sx, sy = cv.head.snout
    if i == 0:
        cv.top[(rnd(sx), rnd(sy) + 1)] = (240, 120, 140, 255)
    else:
        cv.fx[(25, 21)] = (200, 236, 255, 235); cv.fx[(32, 21)] = (200, 236, 255, 235)
    return cv.image()


def brachio_nap(i):
    """낮잠 (3장): 0 = 눕는 중 (다리를 굽혀 몸이 내려가고 목이 처짐) · 1·2 = 다리 접고 엎드려 긴 목을 앞으로 둥글게 말아
    머리를 가슴 앞 땅에 (몸 쪽을 보며) 내려놓고 쿨쿨 (눈은 일자, 가슴이 1칸 들썩)"""
    P = BRACHIO
    if i == 0:
        cv = brachio_pose(bob=2, neck=[(16.6, 12.0), (19.8, 10.4), (22.2, 10.8)], head=(21, 7), ang=24, mood="sleep")
        return cv.image()
    cv = Cv(P)
    up = i - 1
    cv.path([(7.6, 18.6), (4.8, 20.4), (2.8, 21.4)], [2.3, 1.4, 0.5])                        # 꼬리
    cv.path([(18.6, 15.0), (23.6, 12.6), (27.4, 14.6), (27.6, 18.4)], [2.3, 1.9, 1.7, 1.6])  # 앞으로 둥글게 만 목
    cv.oval(12.6, 17.6 - up * 0.4, 7.0, 3.8 + up * 0.4, -3)                                   # 엎드린 몸 (숨)
    for x, y in ((8, 15), (9, 15), (12, 14), (13, 14), (16, 15), (10, 17)):
        y -= up
        if (x, y) in cv.px and (x, y - 1) in cv.px:
            cv.dt[(x, y)] = P.SPOT
    s_ = Cv(P)                                                                                # 접은 다리
    s_.ellipse(8.6, 20.6, 2.6, 1.5)
    cv.overlay(s_)
    h = brachio_head_rig(P, 19, 16, 0, 0, "sleep", False, flip=True)                          # 몸 쪽을 보고 누운 머리
    cv.overlay(h)
    cv.finish()
    return cv.image()


def trike_nap(i):
    """낮잠 (3장): 0 = 눕는 중 (다리를 굽혀 몸이 내려가고 고개가 처짐) · 1·2 = 다리 접고 엎드려 턱을 땅에 대고 쿨쿨 (눈은 일자, 등이 1칸 들썩)"""
    if i == 0:
        cv = trike_pose(((8.4, 0), (17.8, 0), (11, 0), (20.2, 0)), bob=2, ang=12, head_dy=3, mood="sleep")
        return cv.image(dx=-1)
    up = i - 1
    cv = trike_pose(((8.4, 0), (17.8, 0), (11, 0), (20.2, 0)), folded=True, body_dy=3.4, body_ry=4.0 + up * 0.6,
                    ang=16, head_dy=8, mood="sleep")
    return cv.image(dx=-1)


def brachio_graze(i):
    """풀 뜯기 (반복 2장): 몸은 수평 그대로, 긴 목만 땅까지 숙여 낮은 고사리를 덥석 → 오물오물 (입에 잎)"""
    cv = brachio_pose(neck=[(16.6, 12.6), (20.8, 14.2), (23.6, 17.2)], head=(22, 12), ang=40, jaw=1 if i == 0 else 0,
                      mood="normal" if i == 0 else "happy")
    sx, sy = cv.head.snout
    fern(cv, 29.4, 22, h=4, lean=1)
    fern(cv, 31.4, 22, h=3, lean=0)
    if i == 1:
        for p, c in (((0, 1), LEAF), ((1, 1), LEAF_HI), ((1, 2), LEAF_DK)):
            cv.top[(rnd(sx) + p[0], rnd(sy) + p[1])] = c
    return cv.image()


# ── 익룡 나머지 행동 ──────────────────────────────────────────────────────
PT_WING["flat"] = ((11.6, 9.4), (1.6, 10.6), (12.4, 14.6))          # 활공: 날개를 넓고 평평하게 (날개막이 보이게)
PT_WING["tuck"] = ((13.2, 10.8), (5.4, 12.2), (13.2, 13.8))         # 급강하: 날개를 몸에 바짝 접음


def ptero_glide(i):
    """활공 (반복 2장): 날개를 넓게 펴고 미끄러지듯 · 앞뒤로 살짝 기울기"""
    cv = ptero_pose("flat", mood="happy" if i else "normal")
    return cv.image(dy=(1, 0)[i], tilt=(0.04, -0.04)[i])


def ptero_dive(i):
    """급강하 (반복 2장): 날개를 뒤로 접고 부리를 아래로 · 유선형으로 쌩 (속도선)"""
    cv = ptero_pose("tuck", mood="fierce")
    r = rotated(cv, 40 + (0, 3)[i], (18, 12))
    r.tail = set()
    out = Cv(PTERO)
    merge(out, r)
    for k, (x, y) in enumerate(((6, 3), (10, 1), (3, 8))):                 # 속도선 (위·뒤로)
        x += (i * 1)
        out.line(x, y, x + 2, y + 2, SPEED, to="fx")
    return out.image(dy=1)


def ptero_perch(i):
    """땅에서 네 발로 걷기 (반복 2장): 접은 날개를 앞다리로 짚는 진짜 익룡 걸음 — 한 걸음 · 다른 걸음"""
    P = PTERO
    cv = Cv(P)
    step = (0, 1)[i]
    ff = (19.0, 21.6)[step], (21.6, 19.0)[step]                             # (먼 앞발, 가까운 앞발) x
    hh = (14.0, 11.6)[step], (11.6, 14.0)[step]                             # (먼 뒷발, 가까운 뒷발) x
    cv.capsule(18.6, 15.0, ff[0], 22, 0.8, 0.7, P.FAR)                      # 먼 앞다리 (접은 날개 팔)
    cv.capsule(13.0, 17.0, hh[0], 22, 0.7, 0.6, P.FAR)                      # 먼 뒷다리
    cv.capsule(11.6, 15.8, 8.2, 16.8, 1.0, 0.4)                             # 꼬리
    cv.ellipse(15.6, 15.2, 5.0, 3.2)                                        # 몸통
    cv.capsule(19.4, 13.6, 21.6, 10.6, 1.8, 1.7)                            # 목
    g = ptero_head_group(P, 0, False, "normal", False)
    merge(cv, g)
    cv.ellipse(16.2, 16.6, 3.6, 1.6, P.BELLY, to="dt", keep=lambda x, y: (x, y) in cv.px and cv.px[(x, y)] == P.BODY)
    s = Cv(P)                                                               # 가까운 뒷다리
    s.capsule(13.6, 17.2, hh[1], 22, 0.75, 0.65)
    s.put(rnd(hh[1]) + 1, 22, P.CLAW)
    cv.overlay(s)
    w = Cv(P)                                                               # 가까운 앞다리 = 접은 날개 (팔뼈로 짚고, 긴 손가락은 등 위로 접힘)
    w.poly([(18.4, 13.6), (ff[1] - 0.4, 20.4), (14.6, 9.6)], P.MEMB)
    w.capsule(18.6, 14.4, ff[1], 21.6, 0.85, 0.75)
    w.capsule(ff[1], 21.0, 14.4, 9.4, 0.55, 0.35)
    w.put(rnd(ff[1]) + 1, 22, P.CLAW)
    cv.overlay(w)
    cv.finish()
    return cv.image()


# ══════════════════════════════════════════════════════════════════════
def action_sheets():
    return {
        # 대표 동작 4종 (사용자 우선)
        "trike_headbutt": [trike_headbutt(i) for i in range(3)],
        "stego_tailswing": [stego_tailswing(i) for i in range(3)],
        "ptero_fisheat": [ptero_fisheat(i) for i in range(3)],
        "trex_meat": [trex_meat(i) for i in range(4)],
        # 티라노
        "trex_roar": [trex_roar(i) for i in range(3)],
        "trex_chomp": [trex_chomp(i) for i in range(2)],
        "trex_stomp": [trex_stomp(i) for i in range(2)],
        "trex_shortarms": [trex_shortarms(i) for i in range(2)],
        "trex_nap": [trex_nap(i) for i in range(3)],
        # 트리케라톱스
        "trike_charge": [trike_charge(i) for i in range(2)],
        "trike_headshake": [trike_headshake(i) for i in range(2)],
        "trike_graze": [trike_graze(i) for i in range(2)],
        "trike_wallow": [trike_wallow(i) for i in range(2)],
        "trike_nap": [trike_nap(i) for i in range(3)],
        # 스테고
        "stego_graze": [stego_graze(i) for i in range(2)],
        "stego_nap": [stego_nap(i) for i in range(3)],
        "stego_sunbask": [stego_sunbask(i) for i in range(2)],
        # 브라키오
        "brachio_reach": [brachio_reach(i) for i in range(3)],
        "brachio_bellow": [brachio_bellow(i) for i in range(2)],
        "brachio_drink": [brachio_drink(i) for i in range(2)],
        "brachio_nap": [brachio_nap(i) for i in range(3)],
        "brachio_graze": [brachio_graze(i) for i in range(2)],
        # 익룡
        "ptero_glide": [ptero_glide(i) for i in range(2)],
        "ptero_dive": [ptero_dive(i) for i in range(2)],
        "ptero_perch": [ptero_perch(i) for i in range(2)],
    }


# ══════════════════════════════════════════════════════════════════════
def sheets():
    return {
        "trex": {
            "walk": [trex_walk(i) for i in range(4)],
            "run": [trex_run(i) for i in range(6)],
            "idle": [trex_sit(), trex_sit(blink=True)],
            "face": [trex_sit("talk"), trex_sit("surprised"), trex_sit("happy")],
            "climb": [trex_climb(i) for i in range(3)],
        },
        "trike": {
            "walk": [trike_walk(i) for i in range(4)],
            "run": [trike_run(i) for i in range(6)],
            "idle": [trike_stand(), trike_stand(blink=True)],
            "face": [trike_stand("talk"), trike_stand("surprised"), trike_stand("happy")],
            "climb": [trike_climb(i) for i in range(3)],
        },
        "ptero": {
            "walk": [ptero_walk(i) for i in range(4)],
            "run": [ptero_run(i) for i in range(6)],
            "idle": [ptero_idle(), ptero_idle(blink=True)],
            "face": [ptero_idle("talk"), ptero_idle("surprised"), ptero_idle("happy")],
        },
        "stego": {
            "walk": [stego_walk(i) for i in range(4)],
            "run": [stego_run(i) for i in range(6)],
            "idle": [stego_stand(), stego_stand(blink=True)],
            "face": [stego_stand("talk"), stego_stand("surprised"), stego_stand("happy")],
            "climb": [stego_climb(i) for i in range(3)],
        },
        "brachio": {
            "walk": [brachio_walk(i) for i in range(4)],
            "run": [brachio_run(i) for i in range(6)],
            "idle": [brachio_stand(), brachio_stand(blink=True)],
            "face": [brachio_stand("talk"), brachio_stand("surprised"), brachio_stand("happy")],
            "climb": [brachio_climb(i) for i in range(3)],
        },
    }


def save_sheet(out, name, frames):
    sheet = Image.new("RGBA", (W * len(frames), frames[0].height), CLEAR)
    for i, f in enumerate(frames):
        sheet.alpha_composite(f, (i * W, 0))
    sheet.save(os.path.join(out, f"{name}.png"))


def preview_rows(rows, path, dark=False):
    """rows = [(이름, 프레임들)] → ×6 미리보기 (dark = 흰 바탕 옆에 어두운 바탕도 나란히)"""
    S, G, LBL = 6, 10, 200
    maxn = max(len(fr) for _, fr in rows)
    half = LBL + (W * S + G) * maxn + G
    pw = half * (2 if dark else 1)
    ph = sum(fr[0].height * S + G for _, fr in rows) + G
    prev = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
    dr = ImageDraw.Draw(prev)
    if dark:
        dr.rectangle([half, 0, pw, ph], fill=(36, 36, 44, 255))
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font = None
    y = G
    for label, frames in rows:
        fh = frames[0].height
        for ox, ink, box in ((0, (50, 50, 50, 255), (232, 232, 236, 255)), (half, (225, 225, 235, 255), (70, 70, 84, 255)))[: 2 if dark else 1]:
            dr.text((ox + 8, y + H * S // 2 - 10), label, fill=ink, font=font)
            for i, f in enumerate(frames):
                x = ox + LBL + i * (W * S + G)
                dr.rectangle([x - 1, y - 1, x + f.width * S, y + fh * S], outline=box)
                if fh > H:   # 몸(24칸)과 꼬리 칸 경계 표시
                    dr.line([(x, y + H * S), (x + W * S - 1, y + H * S)], fill=(255, 205, 205, 255))
                prev.alpha_composite(f.resize((f.width * S, fh * S), Image.NEAREST), (x, y))
        y += fh * S + G
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    prev.save(path)
    print("preview:", path)


def main(out, preview=None, act_preview=None):
    """기본 시트 + 행동 시트 + prop_meat.png 를 out 에 쓴다. preview = 기본 시트 미리보기, act_preview = 행동 시트 미리보기 (흰·어두운 바탕)"""
    os.makedirs(out, exist_ok=True)
    all_ = sheets()
    for name, kinds in all_.items():
        for kind, frames in kinds.items():
            save_sheet(out, f"{name}_{kind}", frames)
            print(f"{name}_{kind}.png  {len(frames)} frames")
    acts = action_sheets()
    for name, frames in acts.items():
        save_sheet(out, name, frames)
        check_margin(name, frames)
        print(f"{name}.png  {len(frames)} frames")
    meat = prop_meat()
    meat.save(os.path.join(out, "prop_meat.png"))
    print("prop_meat.png  24x24")
    if preview:
        preview_rows([(f"{n} {k}", fr) for n, kinds in all_.items() for k, fr in kinds.items()], preview)
    if act_preview:
        rows = [(n, fr) for n, fr in acts.items()]
        rows.append(("prop_meat (24x24)", [meat]))
        preview_rows(rows, act_preview, dark=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
