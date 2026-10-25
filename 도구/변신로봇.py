"""
Pixel TMI 스포츠카 도착 세레모니 — 변신 로봇 도트.
80년대 변신 자동차 로봇 만화에 바치는 오마주이되, 실제 작품의 로고·문장·얼굴·캐릭터는 쓰지 않은 오리지널 디자인.
  · 머리: 빨간 헬멧 + 지붕 샤크핀 안테나 + 파란 고글(바이저) + 은색 입가리개(씩 웃음)
  · 몸: 앞유리 = 가슴(가운데 기둥으로 갈라져 '유리 가슴근육'), 노란 헤드라이트, 은색 복근 판
  · 어깨: 앞바퀴 · 종아리: 뒷바퀴 · 팔: 문짝(빨간 장갑) + 불룩한 은색 '금속 알통'
결: 탈것_도트만들기.py 와 같은 진회색 자동 외곽선 · 밝은 색 몇 개 · 같은 빨강/은색/유리 팔레트.

사용: python 도구\\변신로봇.py <출력 폴더> <미리보기.png>
출력 (한 칸 32×32, 투명 바탕, 오른쪽을 봄):
  car_transform.png — 8프레임(256×32): 0=스포츠카(car_idle 0번과 같은 그림) → 패널이 열리고 바퀴가 접히고
                      뒤쪽에서 다리가 내려와 들어 올린 뒤 일어서고, 문짝이 팔로, 보닛이 갈라지며 머리가 솟음 → 7=영웅 자세
  car_flex.png      — 4프레임(128×32): 0=더블 바이셉스 · 1=사이드 체스트 · 2=어깨 들썩 · 3=씩 웃음 + 고글 번쩍
※ 앱(PetView.drawRobot)이 변신은 175ms×8칸(마지막 칸 유지), 근육 자랑은 260ms×4칸 반복으로 읽으므로 칸 수를 바꾸면 안 된다.
"""
import math
import os
import sys

from PIL import Image, ImageDraw

W, H = 32, 32
LINE = (60, 62, 70, 255)
CLEAR = (0, 0, 0, 0)
WHITE = (246, 246, 246, 255)
GLASS = (150, 210, 250, 255)
GLASS_DK = (100, 168, 228, 255)
GLINT = (240, 250, 255, 255)
TIRE = (40, 40, 46, 255)
YEL = (248, 200, 40, 255)
REDL = (232, 50, 40, 255)
STEEL = (90, 92, 104, 255)
# 스포츠카 (탈것_도트만들기.py 와 같은 값)
RED = (228, 48, 44, 255)
RED_HI = (255, 124, 104, 255)
RED_DK = (166, 30, 36, 255)
WELL = (30, 28, 34, 255)
RIM = (98, 102, 114, 255)
SPOKE = (214, 218, 226, 255)
HEAD = (255, 246, 196, 255)
TAIL = (255, 72, 72, 255)
# 로봇 은색 · 고글
M_HI = (226, 232, 242, 255)
M_ = (180, 188, 204, 255)
M_DK = (124, 132, 152, 255)
VIS_DK = (40, 64, 112, 255)
VIS = (70, 190, 255, 255)
VIS_HI = (190, 242, 255, 255)
MOUTH = (44, 44, 54, 255)
TEETH = (250, 250, 250, 255)
SPARK = (255, 255, 255, 255)
SPARK_TIP = (255, 214, 70, 255)


def rnd(v):
    return int(math.floor(v + 0.5))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + (c[3] if len(c) > 3 else 255,)


def alpha(c, a):
    return c[:3] + (a,)


class Cv:
    """도트 캔버스. px=몸(자동 외곽선) · dt=무늬(몸 위 덧칠, 외곽선 없음) · fx=효과(빛·잔상, 몸 뒤, 외곽선 없음)"""

    def __init__(self):
        self.px, self.dt, self.fx = {}, {}, {}

    def _L(self, to):
        return getattr(self, to)

    def rect(self, x0, y0, x1, y1, c, to="px"):
        L = self._L(to)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                L[(x, y)] = c

    def put(self, x, y, c, to="px"):
        self._L(to)[(x, y)] = c

    def ellipse(self, cx, cy, rx, ry, c, to="px", keep=None):
        L = self._L(to)
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0 and (keep is None or keep(x, y)):
                    L[(x, y)] = c

    def spans(self, rows, c, to="px"):
        for y, (x0, x1) in rows.items():
            self.rect(x0, y, x1, y, c, to)

    def line(self, x0, y0, x1, y1, c, to="px"):
        L = self._L(to)
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            L[(rnd(x0 + (x1 - x0) * i / n), rnd(y0 + (y1 - y0) * i / n))] = c

    def seg(self, a, b, r, c, to="px"):
        """굵은 막대 (a→b, 반지름 r) — 팔다리"""
        L = self._L(to)
        (ax, ay), (bx, by) = a, b
        dx, dy = bx - ax, by - ay
        ll = dx * dx + dy * dy or 1e-9
        for y in range(int(min(ay, by) - r) - 1, int(max(ay, by) + r) + 2):
            for x in range(int(min(ax, bx) - r) - 1, int(max(ax, bx) + r) + 2):
                t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / ll))
                if math.hypot(x - (ax + dx * t), y - (ay + dy * t)) <= r:
                    L[(x, y)] = c

    def art(self, x0, y0, rows, pal, to="px"):
        """글자 그림: pal 의 글자 → 색, '.' 은 비움"""
        L = self._L(to)
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch in pal:
                    L[(x0 + dx, y0 + dy)] = pal[ch]

    def top_light(self, c, skip=(), x0=-99, x1=99):
        tops = {}
        for (x, y) in self.px:
            if x0 <= x <= x1 and (x not in tops or y < tops[x]):
                tops[x] = y
        for x, y in tops.items():
            if self.px[(x, y)] not in skip and (x, y) not in self.dt:
                self.dt[(x, y)] = c

    def overlay(self, o, line=LINE):
        """o 를 몸 위에 얹는다. 맞닿은 몸 쪽에 진회색 경계선을 그어 부품이 갈라져 보이게"""
        region = set(o.px)
        for p in region:
            self.dt.pop(p, None)
        self.px.update(o.px)
        self.dt.update(o.dt)
        self.fx.update(o.fx)
        for (x, y) in region:
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in region and n in self.px:
                    self.dt[n] = line

    def under(self, o):
        """o 를 몸 뒤에 깐다 (이미 있는 칸은 그대로)"""
        for p, c in o.px.items():
            if p not in self.px:
                self.px[p] = c
                if p in o.dt:
                    self.dt[p] = o.dt[p]
        for p, c in o.fx.items():
            self.fx.setdefault(p, c)

    def paste(self, o, dx=0, dy=0):
        for name in ("px", "dt", "fx"):
            src, dst = getattr(o, name), getattr(self, name)
            for (x, y), c in src.items():
                dst[(x + dx, y + dy)] = c

    def flat(self):
        """무늬를 몸 색에 녹인 사본 (돌리기 전에)"""
        o = Cv()
        for p, c in self.px.items():
            o.px[p] = self.dt.get(p, c)
        o.fx = dict(self.fx)
        return o

    def rotated(self, ang, pivot, dest, ss=4):
        """ang 도만큼 화면에서 반시계(+면 코가 들림)로 돌린 사본. pivot(원본 좌표) → dest(새 좌표).
        한 칸을 ss×ss 로 쪼개 원본 색을 다수결 — 도트가 덜 깨진다."""
        src = self.flat()
        a = math.radians(ang)
        ca, sa = math.cos(a), math.sin(a)
        (px_, py_), (qx, qy) = pivot, dest
        pts = [((x + u) - px_, (y + v) - py_) for (x, y) in src.px for u in (0, 1) for v in (0, 1)]
        fw = [(qx + dx * ca + dy * sa, qy - dx * sa + dy * ca) for dx, dy in pts]
        X0, X1 = int(min(p[0] for p in fw)) - 1, int(max(p[0] for p in fw)) + 1
        Y0, Y1 = int(min(p[1] for p in fw)) - 1, int(max(p[1] for p in fw)) + 1
        o = Cv()
        for Y in range(Y0, Y1 + 1):
            for X in range(X0, X1 + 1):
                votes = {}
                hits = 0
                for i in range(ss):
                    for j in range(ss):
                        ux, uy = X + (i + 0.5) / ss - qx, Y + (j + 0.5) / ss - qy
                        sx, sy = ux * ca - uy * sa + px_, ux * sa + uy * ca + py_
                        c = src.px.get((math.floor(sx), math.floor(sy)))
                        if c is not None:
                            hits += 1
                            votes[c] = votes.get(c, 0) + 1
                if hits * 2 >= ss * ss:
                    o.px[(X, Y)] = max(votes.items(), key=lambda kv: kv[1])[0]
        return o

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
        for (x, y) in px:
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + ddx, y + ddy)
                if n not in px and 0 <= n[0] < W and 0 <= n[1] < H:
                    im.putpixel(n, LINE)
        for (x, y), c in px.items():
            blend(x, y, c)
        for (x, y), c in dt.items():
            blend(x, y, c)
        return im


def spark(cv, x, y, big=False):
    """철컥 불꽃: 흰 점 + 노란 끝 (외곽선 없음 — 밝은 바탕에선 노란 끝, 어두운 바탕에선 흰 점이 보인다)"""
    cv.dt[(x, y)] = SPARK
    if big:
        for ax, ay in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cv.dt[(x + ax, y + ay)] = SPARK
        for ax, ay in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            cv.dt[(x + ax, y + ay)] = SPARK_TIP
    else:
        for ax, ay in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            cv.dt[(x + ax, y + ay)] = SPARK_TIP


def shade_part(cv, hi, dk, base=None):
    """부품 위쪽 가장자리 밝게 · 아래쪽 어둡게"""
    for (x, y), c in list(cv.px.items()):
        if base is not None and c != base:
            continue
        if (x, y) in cv.dt:
            continue
        if (x, y - 1) not in cv.px:
            cv.dt[(x, y)] = hi
        elif (x, y + 1) not in cv.px:
            cv.dt[(x, y)] = dk


# ═════════════════ 1. 스포츠카 (탈것_도트만들기.car 와 같은 그림, 원래 34×24 좌표) ═════════════════

def wheel(cv, cx, cy, rx=3.45, step=0):
    """옆에서 본 바퀴. rx 가 작아지면 바퀴가 돌아 접히는 중(옆으로 눕는 중)"""
    cv.ellipse(cx, cy, rx, 3.45, TIRE)
    if rx >= 3:
        cv.ellipse(cx, cy, 2.3, 2.3, RIM, to="dt")
        for k in range(4):
            a = step * math.pi / 8 + k * math.pi / 2
            for r in (1, 2):
                cv.dt[(cx + rnd(r * math.cos(a)), cy + rnd(r * math.sin(a)))] = SPOKE
        cv.dt[(cx, cy)] = REDL
        cv.dt[(cx - 1, cy - 3)] = (78, 78, 88, 255)
    elif rx >= 1.6:
        cv.ellipse(cx, cy, max(1.0, rx - 1.1), 2.3, RIM, to="dt")
        for y in range(cy - 2, cy + 3):
            cv.dt[(cx, y)] = SPOKE
        cv.dt[(cx, cy)] = REDL
    else:
        for y in range(cy - 2, cy + 3):
            cv.dt[(cx, y)] = (70, 70, 80, 255)


def car_body(seams=False, spoiler_up=0, hood_up=False, flash=False, door_out=False, mech=False):
    """바퀴 뺀 차체 (원래 좌표). mech=뒤 바퀴 집 속 기계(은색 피스톤)가 드러남 (다리가 나오는 곳)"""
    b = Cv()
    b.spans({11: (14, 20), 12: (11, 22), 13: (9, 24), 14: (5, 28), 15: (4, 30),
             16: (4, 32), 17: (4, 32), 18: (4, 32), 19: (5, 31)}, RED)
    b.rect(3, 11 - spoiler_up, 7, 11 - spoiler_up, RED_DK)
    b.rect(6, 12 - spoiler_up, 6, 13, RED_DK)
    b.put(24, 13, RED_DK)
    b.rect(3, 19, 4, 19, STEEL)
    for wx in (9, 27):
        if mech and wx == 27:                  # 앞 바퀴 집은 그대로 (바퀴가 돌아 눕는 중)
            b.ellipse(wx, 19, 4.4, 4.4, WELL, keep=lambda x, y: y <= 19)
            continue
        b.ellipse(wx, 19, 4.4, 4.4, M_DK if mech else WELL, keep=lambda x, y: y <= 19)
        if mech:
            for y in range(16, 20):
                b.px[(wx, y)] = M_
            b.px[(wx - 2, 18)] = STEEL; b.px[(wx + 2, 18)] = STEEL
            b.px[(wx - 2, 19)] = STEEL; b.px[(wx + 2, 19)] = STEEL
    for y, (x0, x1) in {12: (12, 21), 13: (10, 23)}.items():
        for x in range(x0, x1 + 1):
            if x != 17:
                b.dt[(x, y)] = GLASS
    b.dt[(18, 12)] = GLINT; b.dt[(19, 12)] = GLINT; b.dt[(13, 12)] = GLINT
    b.dt[(23, 13)] = GLASS_DK; b.dt[(10, 13)] = GLASS_DK; b.dt[(22, 13)] = GLASS_DK
    b.top_light(RED_HI, skip=(RED_DK, STEEL), x0=5, x1=31)
    for x in (13, 14, 15, 26):
        b.dt[(x, 15)] = RED_HI
    for x in range(4, 32):
        if b.px.get((x, 18)) == RED:
            b.dt[(x, 18)] = RED_DK
    for y in (14, 15, 16, 17):
        b.dt[(22, y)] = RED_DK
    b.dt[(20, 15)] = RED_DK
    b.rect(14, 16, 16, 16, WELL, to="dt")
    b.dt[(27, 14)] = GLINT
    b.rect(29, 15, 30, 15, HEAD, to="dt"); b.dt[(31, 16)] = HEAD
    b.rect(30, 18, 32, 18, RED_DK, to="dt")
    b.rect(4, 15, 5, 15, TAIL, to="dt"); b.dt[(4, 16)] = TAIL
    if flash:
        b.rect(29, 15, 30, 15, GLINT, to="dt"); b.dt[(31, 16)] = GLINT
        b.rect(4, 15, 5, 15, (255, 200, 200, 255), to="dt")
        for p in ((33, 14), (34, 13), (34, 16), (33, 17)):
            b.fx[p] = (255, 236, 140, 255)
    if seams:                         # 패널 틈이 갈라짐 (문 · 보닛 · 트렁크)
        for y in range(14, 19):
            b.dt[(16, y)] = LINE; b.dt[(22, y)] = LINE
        for x in range(23, 29):
            b.dt[(x, 14)] = LINE
        for y in range(14, 19):
            b.dt[(11, y)] = LINE
    if door_out:                      # 문짝이 한 칸 튀어나옴 (밝은 테)
        for x in range(17, 22):
            b.dt[(x, 14)] = RED_HI
        for y in range(15, 18):
            b.dt[(17, y)] = RED_HI
    if hood_up:                       # 보닛 뒤쪽이 들림
        for x in range(23, 27):
            b.px[(x, 13)] = RED
            b.dt[(x, 13)] = RED_HI
        b.dt[(23, 14)] = LINE; b.dt[(24, 14)] = LINE
    return b


def car_side(wheel_rx=3.45, body_dy=0, **kw):
    cv = Cv()
    cv.paste(car_body(**kw), 0, body_dy)
    for wx in (9, 27):
        wheel(cv, wx, 19, rx=wheel_rx)
    return cv


# ═════════════════ 2. 로봇 부품 ═════════════════
PAL = {"k": M_DK, "s": M_, "l": M_HI, "h": RED_HI, "r": RED, "d": RED_DK, "e": STEEL,
       "b": VIS_DK, "v": VIS, "V": VIS_HI, "m": MOUTH, "t": TEETH, "Y": HEAD, "y": YEL,
       "g": GLASS, "G": GLASS_DK, "w": GLINT}


def head(x0, y0, mouth="smile", visor="on", rows_shown=99):
    """머리 9×9 (오른쪽 앞을 봄). mouth: smile(씩)/grin(이 보이게 활짝)/flat · visor: off/on/flash"""
    rows = ["...kl....",      # 지붕 샤크핀 안테나
            "..kll....",
            ".hhhhhhhh",
            "rrrrrrrrr",
            "dbvvvvvVb",      # 고글(바이저)
            "dbvvvvvvb",
            "drslllllr",      # 은색 입가리개
            ".dsssssss",
            "..dkkkkk."]
    if visor == "off":
        rows[4] = "dbbbbbbbb"; rows[5] = "dbbbbbbbb"
    elif visor == "flash":
        rows[4] = "dbVVVVVVV"; rows[5] = "dbvVVVVVv"
    if mouth == "smile":                       # 오른쪽 입꼬리가 올라간 씩 웃음
        rows[6] = "drslllllm"; rows[7] = ".dsmmmmms"
    elif mouth == "grin":                      # 이를 드러낸 활짝 웃음
        rows[6] = "drmttttmr"; rows[7] = ".dsmmmmss"
    else:
        rows[7] = ".dssmmmss"
    if rows_shown < 9:
        rows = rows[:rows_shown]
    cv = Cv()
    cv.art(x0, y0, rows, PAL)
    if visor == "on" and rows_shown >= 6:
        cv.dt[(x0 + 7, y0 + 4)] = WHITE
    if visor == "flash":                       # 고글 번쩍: 양옆으로 빛줄기
        for x in range(x0 - 3, x0 + 13):
            if not (x0 <= x <= x0 + 8):
                d = min(abs(x - x0), abs(x - x0 - 8))
                cv.fx[(x, y0 + 4)] = alpha(VIS_HI, max(90, 255 - d * 50))
                cv.fx[(x, y0 + 5)] = alpha(VIS, max(70, 220 - d * 50))
        for p in ((x0 + 11, y0 + 1), (x0 + 12, y0 + 2), (x0 + 13, y0 + 0)):
            cv.fx[p] = VIS_HI
    return cv


def torso(x0, y0, pec=None, puff=False):
    """앞에서 본 몸통 13×9: 앞유리 '유리 가슴근육' · 헤드라이트 · 은색 복근. pec='L'/'R' = 그쪽 가슴이 들썩"""
    rows = [".hhhhhhhhhhh.",
            "rrYyrrrrrYyrr",
            "rgwgggdgwgggr",
            "rgggggdgggggr",
            "dGGGGGdGGGGGd",
            ".drrrrdrrrrd.",
            "..rlsrdrlsr..",
            "..dkkrdrkkd..",
            "...ddddddd..."]
    g = [list(r) for r in rows]
    if pec:
        cols = range(1, 6) if pec == "L" else range(7, 12)
        for c in cols:
            g[1][c], g[2][c], g[3][c], g[4][c] = g[2][c], g[3][c], g[4][c], "r"
        g[1][2], g[1][3], g[1][9], g[1][10] = "Y", "y", "Y", "y"
    cv = Cv()
    cv.art(x0, y0, ["".join(r) for r in g], PAL)
    if puff:                                   # 가슴 쭉: 양옆으로 한 칸씩 부풀고 유리에 반짝
        for y in range(y0 + 1, y0 + 5):
            cv.put(x0 - 1, y, RED_DK if y == y0 + 4 else RED)
            cv.put(x0 + 13, y, RED_DK if y == y0 + 4 else RED)
        cv.put(x0 + 2, y0 + 2, GLINT); cv.put(x0 + 9, y0 + 2, GLINT)
    return cv


def hips(x0, y0):
    """은색 허리띠 + 빨간 버클"""
    cv = Cv()
    cv.art(x0, y0, ["..lsssrsssk..",
                    "..kssdddssk.."], PAL)
    return cv


def shoulder_wheel(cx, cy, r=2.8):
    """어깨 바퀴 (= 앞바퀴): 차 바퀴와 같은 결 — 검은 타이어 · 회색 휠 · 흰 살 · 빨간 센터캡"""
    cv = Cv()
    cv.ellipse(cx, cy, r, r, TIRE)
    cv.ellipse(cx, cy, r - 1.05, r - 1.05, RIM, to="dt")
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        cv.dt[(cx + d[0], cy + d[1])] = SPOKE
    cv.dt[(cx, cy)] = REDL
    cv.dt[(cx - 1, cy - rnd(r))] = (90, 90, 102, 255)
    return cv


def leg(hip, knee, foot, toe=1, calf_wheel=True, far=False):
    """다리: 허벅지(빨강) · 무릎(은색) · 정강이(빨강) + 종아리 바퀴(= 뒷바퀴) · 발(은색)"""
    cv = Cv()
    k = 0.86 if far else 1.0
    cv.seg(hip, knee, 1.8, shade(RED, k))
    cv.seg(knee, foot, 1.8, shade(RED, k))
    shade_part(cv, shade(RED_HI, k), shade(RED_DK, k))
    kx, ky = rnd(knee[0]), rnd(knee[1])
    cv.rect(kx - 1, ky - 1, kx + 1, ky, shade(M_, k))
    cv.dt.pop((kx - 1, ky), None); cv.dt.pop((kx, ky), None); cv.dt.pop((kx + 1, ky), None)
    cv.dt[(kx - 1, ky - 1)] = shade(M_HI, k); cv.dt[(kx, ky - 1)] = shade(M_HI, k)
    fx, fy = rnd(foot[0]), rnd(foot[1])
    cv.rect(fx - 2, fy, fx + 2, fy + 1, shade(M_, k))
    for x in range(fx - 2, fx + 3):
        cv.dt.pop((x, fy), None)
    cv.dt[(fx - 2, fy)] = shade(M_HI, k); cv.dt[(fx - 1, fy)] = shade(M_HI, k)
    cv.rect(fx - 2, fy + 1, fx + 2, fy + 1, shade(M_DK, k), to="dt")
    if toe > 0:
        cv.put(fx + 3, fy + 1, shade(M_, k)); cv.dt[(fx + 3, fy + 1)] = shade(M_DK, k)
    if calf_wheel:
        sx, sy = (knee[0] + foot[0]) / 2, (knee[1] + foot[1]) / 2
        wx = rnd(sx - 2) if not far else rnd(sx + 2)
        cv.ellipse(wx, rnd(sy), 1.6, 1.9, TIRE)
        cv.dt[(wx, rnd(sy))] = RIM
    return cv


def arm(shoulder, elbow, hand, bulge=1.0, boff=1.0, bdir=1, far=False):
    """팔: 위팔(은색 관절) + 불룩한 빨간 '금속 알통' · 아래팔(은색) · 주먹(빨강).
    알통은 아래팔이 접히는 쪽으로(bdir=1) 또는 바깥쪽으로(bdir=-1) 불룩."""
    k = 0.86 if far else 1.0
    cv = Cv()
    cv.seg(shoulder, elbow, 1.6, shade(M_, k))
    shade_part(cv, shade(M_HI, k), shade(M_DK, k))
    fo = Cv()
    fo.seg(elbow, hand, 1.7, shade(M_, k))
    shade_part(fo, shade(M_HI, k), shade(M_DK, k))
    cv.overlay(fo)
    if bulge > 0:
        mx, my = (shoulder[0] * 0.45 + elbow[0] * 0.55), (shoulder[1] * 0.45 + elbow[1] * 0.55)
        ux, uy = elbow[0] - shoulder[0], elbow[1] - shoulder[1]
        L = math.hypot(ux, uy) or 1
        nx, ny = -uy / L, ux / L
        hx, hy = hand[0] - elbow[0], hand[1] - elbow[1]
        if (nx * hx + ny * hy) * bdir < 0:
            nx, ny = -nx, -ny
        off = (0.9 + bulge * 0.5) * boff
        bx, by = mx + nx * off, my + ny * off
        r = 1.5 + bulge * 0.65
        bm = Cv()
        bm.ellipse(bx, by, r, r, shade(RED, k))
        shade_part(bm, shade(RED_HI, k), shade(RED_DK, k))
        top = min(bm.px, key=lambda p: (p[1] + p[0] * 0.35))
        bm.dt[top] = GLINT
        if (top[0] + 1, top[1] + 1) in bm.px:
            bm.dt[(top[0] + 1, top[1] + 1)] = GLINT if bulge >= 1.4 else shade(RED_HI, k)
        cv.overlay(bm)
    fx, fy = rnd(hand[0]), rnd(hand[1])
    fs = Cv()
    fs.rect(fx - 1, fy - 1, fx + 1, fy + 1, shade(RED, k))
    fs.rect(fx - 1, fy - 1, fx + 1, fy - 1, shade(RED_HI, k), to="dt")
    fs.rect(fx - 1, fy + 1, fx + 1, fy + 1, shade(RED_DK, k), to="dt")
    fs.dt[(fx, fy)] = shade(RED_DK, k)
    cv.overlay(fs)
    return cv


# ═════════════════ 3. 로봇 자세 ═════════════════

def robot(pose):
    """pose: dict — 관절 좌표와 표정. 뒤→앞 순서로 쌓는다.
    legL/legR=(엉덩이, 무릎, 발) · arms=((어깨, 팔꿈치, 주먹[, 알통크기, 알통방향, 먼팔]), …)
    dy=통째 내림 · shrug=어깨 들썩 · pec=가슴 들썩 · puff=가슴 쭉 · wheels=어깨 바퀴 자리 · head=머리 자리"""
    cv = Cv()
    dy = pose.get("dy", 0)
    sh = pose.get("shrug", 0)                 # 어깨만 들썩 (몸통·팔·바퀴가 위로)
    o = lambda p: (p[0], p[1] + dy)
    cv.under(leg(*pose["legR"], far=True))
    cv.overlay(leg(*pose["legL"]))
    cv.overlay(hips(10, 19 + dy))
    cv.overlay(torso(10, 10 + dy - sh, pec=pose.get("pec"), puff=pose.get("puff", False)))
    for extra in pose.get("under_arm", ()):
        cv.overlay(extra)
    for a in pose.get("arms", ()):
        cv.overlay(arm(o(a[0]), o(a[1]), o(a[2]), bulge=a[3] if len(a) > 3 else pose.get("bulge", 1.0),
                       boff=pose.get("boff", 1.0), bdir=a[4] if len(a) > 4 else 1,
                       far=a[5] if len(a) > 5 else False))
    for c in pose.get("wheels", ((9, 12), (23, 12))):
        cv.overlay(shoulder_wheel(c[0], c[1] + dy - sh, r=pose.get("wheel_r", 2.3)))
    hx, hy = pose.get("head", (12, 1))
    cv.overlay(head(hx, hy + dy, mouth=pose.get("mouth", "smile"), visor=pose.get("visor", "on"),
                    rows_shown=pose.get("head_rows", 99)))
    return cv


LEGS = {"legL": ((13, 21), (11, 25), (10, 29)), "legR": ((19, 21), (21, 25), (22, 29))}
HERO = dict(LEGS, arms=(((9, 13), (5, 17), (10, 20)), ((23, 13), (27, 17), (22, 20))),
            mouth="smile", visor="on", bulge=1.0, boff=0.8)


# ═════════════════ 4. 변신 8프레임 ═════════════════

def top_car(x0, y0):
    """선 채로 위에서 본 차 (코가 위): 보닛 · 앞유리 · 지붕 · 뒷유리 — 13×16"""
    rows = ["..rhhhhhhhr..",
            ".YyrrrrrrryY.",
            "rrrrrrhrrrrrr",
            "rrrrrrhrrrrrr",
            "drrrrrhrrrrrd",
            "drgggggggggrd",
            "drgwgggggggrd",
            "drrgggggggrrd",
            "drrrrrrrrrrrd",
            "drrrhhhhhrrrd",
            "drrrrrrrrrrrd",
            "drrGGGGGGGrrd",
            "drrrGGGGGrrrd",
            ".rrrrrrrrrrr.",
            ".drrrrrrrrrd.",
            "..ddddddddd.."]
    cv = Cv()
    cv.art(x0, y0, rows, PAL)
    return cv


def transform(f):
    cv = Cv()
    if f == 0:
        cv.paste(car_side(), -2, 8)
    elif f == 1:
        # 깨어남: 차가 통 튀고 · 패널 틈이 갈라지고 · 스포일러 들림 · 바퀴가 돌아 눕기 시작 · 헤드라이트 번쩍
        cv.paste(car_side(wheel_rx=2.4, body_dy=-1, seams=True, spoiler_up=1, hood_up=True, flash=True, door_out=True), -2, 8)
        spark(cv, 14, 21); spark(cv, 25, 20)
    elif f == 2:
        # 뒤쪽 바퀴 집에서 다리가 내려와 차를 들어 올림 · 코가 살짝 들림 · 앞바퀴는 접혀 눕고
        body = car_body(seams=True, spoiler_up=1, door_out=True, mech=True)
        wheel(body, 27, 19, rx=2.0)
        rb = body.rotated(14, pivot=(6.0, 20.0), dest=(6.0, 21.0))
        cv.under(leg((12, 20), (13, 25), (13, 29), far=True, calf_wheel=False))
        cv.overlay(leg((9, 20), (8, 25), (8, 29), calf_wheel=False))
        w = Cv(); wheel(w, 6, 25, rx=2.0)
        cv.overlay(w)
        cv.overlay(rb)
        spark(cv, 16, 22, big=True); spark(cv, 3, 21)
    elif f == 3:
        # 일어서는 중: 차 앞쪽 2/3 가 43° 들림 · 다리 쭉 · 뒷바퀴는 종아리로
        body = car_body(seams=True, door_out=True, mech=True)
        for p in [p for p in body.px if p[0] < 12]:
            body.px.pop(p); body.dt.pop(p, None)
        for p in [p for p in body.dt if p[0] < 12]:
            body.dt.pop(p)
        wheel(body, 27, 19, rx=3.0)
        rb = body.rotated(43, pivot=(12.0, 20.0), dest=(12.0, 21.0))
        cv.under(leg((15, 21), (17, 25), (19, 29), far=True))
        cv.overlay(leg((12, 21), (11, 25), (10, 29)))
        cv.overlay(rb)
        spark(cv, 9, 16); spark(cv, 25, 14, big=True)
    elif f == 4:
        # 섰다: 위에서 본 차 모양 몸통 (보닛이 위) · 앞바퀴가 어깨 자리 · 문짝은 아직 옆구리
        cv.under(leg((18, 21), (19, 25), (19, 29), far=True))
        cv.overlay(leg((14, 21), (13, 25), (12, 29)))
        cv.overlay(top_car(10, 5))
        for wx in (8, 24):
            t = Cv(); t.rect(wx, 7, wx + 1, 10, TIRE); t.dt[(wx, 7)] = (90, 90, 102, 255)
            cv.overlay(t)
        spark(cv, 9, 13, big=True); spark(cv, 23, 17)
    elif f == 5:
        # 펼침: 보닛이 좌우로 갈라져 어깨로 · 그 사이로 머리가 솟는 중 · 문짝이 내려와 팔이 됨
        pose = dict(HERO)
        pose.update({
            "legL": ((13, 21), (12, 25), (11, 29)),
            "legR": ((19, 21), (20, 25), (21, 29)),
            "arms": (((9, 13), (8, 17), (8, 21)), ((23, 13), (24, 17), (24, 21))),
            "visor": "off", "mouth": "flat", "head": (12, 4), "head_rows": 6, "bulge": 0.2, "boff": 0.3,
            "wheels": (),
        })
        cv = robot(pose)
        for sx in (8, 20):
            h = Cv(); h.rect(sx, 8, sx + 4, 10, RED); h.rect(sx, 8, sx + 4, 8, RED_HI, to="dt")
            h.dt[(sx + 1 if sx < 16 else sx + 3, 9)] = YEL
            h.rect(sx if sx < 16 else sx + 4, 11, sx if sx < 16 else sx + 4, 12, TIRE)
            cv.overlay(h)
        spark(cv, 16, 7, big=True); spark(cv, 5, 17)
    elif f == 6:
        # 머리 쏙 · 고글 켜짐 · 팔을 허리로 가져가며 살짝 웅크림
        pose = dict(HERO)
        pose.update({
            "dy": 1,
            "legL": ((13, 21), (10, 25), (10, 29)),
            "legR": ((19, 21), (22, 25), (22, 29)),
            "arms": (((9, 13), (6, 17), (8, 21)), ((23, 13), (26, 17), (24, 21))),
            "visor": "on", "mouth": "flat", "bulge": 0.5,
        })
        cv = robot(pose)
        spark(cv, 26, 3)
    else:
        cv = robot(HERO)
        cv.dt[(19, 5)] = WHITE
        cv.dt[(18, 12)] = WHITE
    return cv.image()


# ═════════════════ 5. 근육 자랑 4프레임 ═════════════════
DBL = dict(LEGS, arms=(((9, 13), (2, 13), (3, 5)), ((23, 13), (30, 13), (29, 5))), bulge=2.1, boff=1.5)


def flex(f):
    if f == 0:      # 더블 바이셉스 (씩 웃음)
        cv = robot(dict(DBL, mouth="smile"))
    elif f == 1:    # 사이드 체스트: 가슴 쭉 내밀고 두 주먹을 허리 앞에서 맞잡고, 가까운 팔 알통을 바깥으로 꽉
        cv = robot(dict(
            legL=((13, 21), (12, 25), (11, 29)),
            legR=((19, 21), (17, 25), (19, 29)),
            arms=(((9, 13), (9, 17), (14, 19), 0.5, 1, True), ((23, 13), (25, 18), (17, 19), 2.3, -1)),
            puff=True, mouth="grin", boff=1.1, head=(13, 1)))
        cv.dt[(28, 12)] = WHITE; cv.dt[(29, 11)] = SPARK_TIP; cv.dt[(27, 11)] = SPARK_TIP   # 알통 반짝
    elif f == 2:    # 어깨 들썩 (가슴도 들썩)
        cv = robot(dict(DBL, arms=(((9, 12), (2, 11), (3, 3)), ((23, 12), (30, 11), (29, 3))),
                        shrug=1, pec="L", bulge=2.3, mouth="smile"))
        for x, y in ((10, 2), (11, 3), (10, 5), (22, 2), (21, 3), (22, 5)):   # 들썩 자국
            cv.dt[(x, y)] = (150, 156, 176, 255)
    else:           # 씩 웃음 + 고글 번쩍
        cv = robot(dict(DBL, mouth="grin", visor="flash", pec="R"))
    return cv.image()


# ═════════════════ 6. 저장 · 미리보기 ═════════════════

def sheet(frames):
    s = Image.new("RGBA", (W * len(frames), H), CLEAR)
    for i, f in enumerate(frames):
        s.alpha_composite(f, (i * W, 0))
    return s


def main(out, preview):
    os.makedirs(out, exist_ok=True)
    tr = [transform(i) for i in range(8)]
    fl = [flex(i) for i in range(4)]
    sheet(tr).save(os.path.join(out, "car_transform.png"))
    sheet(fl).save(os.path.join(out, "car_flex.png"))
    # 미리보기: 8배 확대, 흰 바탕, 위 줄=변신 8칸 · 아래 줄=근육 자랑 4칸
    S, GAP, TOP, LEFT, ROWGAP = 8, 12, 26, 12, 34
    pw = LEFT * 2 + 8 * (W * S + GAP) - GAP
    ph = TOP + 2 * (H * S) + ROWGAP + 16
    prev = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
    dr = ImageDraw.Draw(prev)
    for r, (name, frames) in enumerate((("car_transform (8)", tr), ("car_flex (4)", fl))):
        y = TOP + r * (H * S + ROWGAP)
        dr.text((LEFT, y - 16), name, fill=(40, 40, 40, 255))
        for i, f in enumerate(frames):
            x = LEFT + i * (W * S + GAP)
            dr.rectangle([x - 1, y - 1, x + W * S, y + H * S], outline=(228, 228, 234, 255))
            prev.alpha_composite(f.resize((W * S, H * S), Image.NEAREST), (x, y))
            dr.text((x + 3, y + 2), str(i), fill=(170, 170, 180, 255))
    os.makedirs(os.path.dirname(os.path.abspath(preview)), exist_ok=True)
    prev.save(preview)
    print("ok", "car_transform", len(tr), "car_flex", len(fl))


if __name__ == "__main__":
    main(*sys.argv[1:3])
