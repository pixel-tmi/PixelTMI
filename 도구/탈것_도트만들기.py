"""
Pixel TMI 상점 캐릭터 5종 도트 만들기 — 스포츠카 · 용 · 비행기 · 헬기 · UFO.
결: 고양이 오마주와 같은 높이 24칸(= 화면 도트), 진회색 자동 외곽선, 밝은 색 몇 개.
날개·로터·프로펠러·바퀴·불빛이 프레임마다 움직인다. 날아다니는 것은 앱에서 땅 위로 살짝 띄워 그린다.
사용: python 탈것_도트만들기.py <출력 폴더> <미리보기.png>
출력: car, dragon, plane, heli, ufo 마다
  <이름>_walk.png (4프레임, 보통 움직임 — 앱이 140ms마다 넘김)
  <이름>_run.png  (4프레임, 주행 중 전력 — 앱이 60~110ms마다 넘김, 기울기·연기·속도선)
  <이름>_idle.png (2프레임: 0=가만히, 1=깜빡 — 앱이 3.4초마다 0.1초 1번 칸을 보여 준다)
※ 앱(PetView)이 walk·run은 4칸, idle은 2칸으로 나눠 읽으므로 칸 수를 바꾸면 안 된다.
"""
import math
import os
import sys

from PIL import Image, ImageDraw

W, H = 34, 24
LINE = (60, 62, 70, 255)
CLEAR = (0, 0, 0, 0)
WHITE = (246, 246, 246, 255)
GLASS = (150, 210, 250, 255)
GLASS_DK = (100, 168, 228, 255)
GLINT = (240, 250, 255, 255)
TIRE = (40, 40, 46, 255)
HUB = (170, 174, 182, 255)
YEL = (248, 200, 40, 255)
REDL = (232, 50, 40, 255)
EYE = (28, 28, 36, 255)
STEEL = (90, 92, 104, 255)
SPEED = (196, 204, 218, 255)     # 속도선
BLUR = (150, 156, 176, 115)      # 회전 잔상 (반투명 — 밝은 바탕·어두운 바탕 둘 다 보이게 중간 회색)
BLADE = (96, 100, 118, 255)      # 프로펠러·로터 날 (진회색 외곽선과 구별되는 중간 회색)


def rnd(v):
    return int(math.floor(v + 0.5))


class Cv:
    """도트 캔버스. px=몸(자동 외곽선) · dt=무늬(몸 위 덧칠, 외곽선 없음) · fx=효과(연기·잔상, 몸 뒤, 외곽선 없음)"""

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

    def cut(self, *pts):
        for p in pts:
            self.px.pop(p, None)

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

    def poly(self, pts, c, to="px"):
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

    def art(self, x0, y0, rows, pal, to="dt"):
        """글자 그림: pal 의 글자 → 색, '.' 은 비움"""
        L = self._L(to)
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch in pal:
                    L[(x0 + dx, y0 + dy)] = pal[ch]

    def top_light(self, c, skip=(), x0=-99, x1=99):
        """몸의 각 세로줄 맨 윗칸을 밝게 (광택)"""
        tops = {}
        for (x, y) in self.px:
            if x0 <= x <= x1 and (x not in tops or y < tops[x]):
                tops[x] = y
        for x, y in tops.items():
            if self.px[(x, y)] not in skip and (x, y) not in self.dt:
                self.dt[(x, y)] = c

    def overlay(self, o, line=LINE):
        """o 를 몸 위에 얹는다 (날개 등). 맞닿은 몸 쪽에 진회색 경계선을 그어 형태가 묻히지 않게"""
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

    def paste(self, o, dx=0, dy=0, tilt=0.0, cx=17):
        for name in ("px", "dt", "fx"):
            src, dst = getattr(o, name), getattr(self, name)
            for (x, y), c in src.items():
                dst[(x + dx, y + dy + rnd((x - cx) * tilt))] = c

    def image(self, dx=0, dy=0, tilt=0.0, cx=17):
        """dx·dy=통째 이동, tilt=기울기(세로줄마다 밀기: +면 오른쪽(앞)이 내려감)"""
        tf = lambda d: {(x + dx, y + dy + rnd((x - cx) * tilt)): c for (x, y), c in d.items()}
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


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + (c[3] if len(c) > 3 else 255,)


def alpha(c, a):
    return c[:3] + (a,)


def puff(cv, cx, cy, r, a=235):
    """연기 한 덩이 (밝은 속 + 회색 테)"""
    core, edge = (246, 246, 250, a), (168, 172, 186, a)
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            d = math.hypot(x - cx, y - cy)
            if d <= r - 0.75:
                cv.fx[(x, y)] = core
            elif d <= r + 0.3:
                cv.fx[(x, y)] = edge


def speed_lines(cv, frame, lines, xmax):
    """뒤로 흘러가는 속도선. lines=[(y, 길이, 위상)]"""
    for y, ln, ph in lines:
        head = xmax - ((frame * 3 + ph) % 9)
        for x in range(head - ln + 1, head + 1):
            if 0 <= x <= xmax:
                cv.fx[(x, y)] = SPEED


# ── 스포츠카: 낮고 매끈한 빨간 차, 광택·바퀴 휠 회전·서스펜션 출렁·배기 연기 ──
RED = (228, 48, 44, 255)
RED_HI = (255, 124, 104, 255)
RED_DK = (166, 30, 36, 255)
WELL = (30, 28, 34, 255)
RIM = (98, 102, 114, 255)
SPOKE = (214, 218, 226, 255)
HEAD = (255, 246, 196, 255)
TAIL = (255, 72, 72, 255)


def wheel(cv, cx, cy, step, blur=False):
    cv.ellipse(cx, cy, 3.45, 3.45, TIRE)
    cv.ellipse(cx, cy, 2.3, 2.3, RIM, to="dt")
    angs = [step * math.pi / 8 + k * math.pi / 2 for k in range(4)]
    if blur:                                          # 빨리 돌면 살이 겹쳐 흐릿 + 반짝점 하나
        angs += [a + math.pi / 4 for a in angs]
    for a in angs:
        for r in (1, 2):
            cv.dt[(cx + rnd(r * math.cos(a)), cy + rnd(r * math.sin(a)))] = shade(SPOKE, 0.8) if blur else SPOKE
    if blur:
        a = step * math.pi / 4
        cv.dt[(cx + rnd(2 * math.cos(a)), cy + rnd(2 * math.sin(a)))] = GLINT
    cv.dt[(cx, cy)] = REDL                            # 센터캡
    cv.dt[(cx - 1, cy - 3)] = (78, 78, 88, 255)       # 타이어 윗면 반짝


def car(frame, mode="walk"):
    run, idle = mode == "run", mode == "idle"
    cv, b = Cv(), Cv()
    b.spans({11: (14, 20), 12: (11, 22), 13: (9, 24), 14: (5, 28), 15: (4, 30),
             16: (4, 32), 17: (4, 32), 18: (4, 32), 19: (5, 31)}, RED)
    b.rect(3, 11, 7, 11, RED_DK); b.rect(6, 12, 6, 13, RED_DK)     # 뒤 날개(스포일러)
    b.put(24, 13, RED_DK)                                            # 사이드미러
    b.rect(3, 19, 4, 19, STEEL)                                      # 머플러
    for wx in (9, 27):                                               # 바퀴 집 (어두운 아치)
        b.ellipse(wx, 19, 4.4, 4.4, WELL, keep=lambda x, y: y <= 19)
    # 유리창 (뒤 쿼터창 · B필러 · 앞창)
    for y, (x0, x1) in {12: (12, 21), 13: (10, 23)}.items():
        for x in range(x0, x1 + 1):
            if x != 17:
                b.dt[(x, y)] = GLASS
    b.dt[(18, 12)] = GLINT; b.dt[(19, 12)] = GLINT; b.dt[(13, 12)] = GLINT
    b.dt[(23, 13)] = GLASS_DK; b.dt[(10, 13)] = GLASS_DK; b.dt[(22, 13)] = GLASS_DK
    b.top_light(RED_HI, skip=(RED_DK, STEEL), x0=5, x1=31)          # 지붕·보닛 윗선 광택
    for x in (13, 14, 15, 26):                                       # 옆구리 반사
        b.dt[(x, 15)] = RED_HI
    for x in range(4, 32):                                           # 아랫단 그늘
        if b.px.get((x, 18)) == RED:
            b.dt[(x, 18)] = RED_DK
    for y in (14, 15, 16, 17):                                       # 문 틈
        b.dt[(22, y)] = RED_DK
    b.dt[(20, 15)] = RED_DK                                          # 손잡이
    b.rect(14, 16, 16, 16, WELL, to="dt")                            # 옆 흡기구
    b.dt[(27, 14)] = GLINT                                           # 보닛 반짝
    b.rect(29, 15, 30, 15, HEAD, to="dt"); b.dt[(31, 16)] = HEAD     # 헤드라이트
    b.rect(30, 18, 32, 18, RED_DK, to="dt")                          # 앞 범퍼 아랫입술
    b.rect(4, 15, 5, 15, TAIL, to="dt"); b.dt[(4, 16)] = TAIL        # 테일램프
    if idle and frame == 1:                                          # 깜빡: 헤드라이트·테일램프 번쩍
        b.rect(29, 15, 30, 15, GLINT, to="dt"); b.dt[(31, 16)] = GLINT
        b.rect(4, 15, 5, 15, (255, 200, 200, 255), to="dt")
        for p in ((33, 14), (32, 13), (33, 12), (33, 16)):
            b.fx[p] = (255, 236, 140, 255)
    # 출렁: 걷기는 살랑, 달리기는 낮게 깔고 잘게 떨림
    bounce = 0 if idle else ([0, 1, 1, 0][frame % 4] if not run else [1, 0, 1, 1][frame % 4])
    cv.paste(b, 0, bounce)
    for wx in (9, 27):
        wheel(cv, wx, 19, 0 if idle else frame, blur=run)
    if run:
        # 배기 연기: 머플러에서 나와 뒤로 커지며 흩어짐 (2덩이 번갈아)
        for k in range(2):
            age = (frame + k * 2) % 4
            px_, py_, r, a = [(2.6, 19.8, 1.2, 250), (1.2, 19.0, 1.9, 235), (-0.2, 17.9, 2.4, 175), (-2.0, 16.9, 2.6, 95)][age]
            puff(cv, px_, py_ + bounce, r, a)
        speed_lines(cv, frame, [(9, 4, 0), (12, 3, 4)], 9)
    return cv.image()


# ── 용: 귀여운 주황 꼬마 용, 4단 날갯짓 · 꼬리 살랑 · 배 비늘 · 작은 뿔 ──
G = (233, 148, 81, 255)
G_HI = (255, 181, 131, 255)
G_DK = (198, 105, 24, 255)
BELLY = (252, 238, 168, 255)
BELLY_DK = (228, 200, 122, 255)
MEMB = (255, 204, 128, 255)       # 날개막 (살구색)
SPIKE = (255, 164, 60, 255)
HORN = (255, 236, 176, 255)
BLUSH = (250, 144, 166, 255)

# 날개 4자세: 손목(wr) · 손가락 끝 3개 · 뿌리(r). 어깨는 (14,11)
WINGS = [
    {"wr": (16, 0), "f": [(11, 0), (7, 3), (8, 8)], "r": (12, 11)},       # 0 위로 활짝
    {"wr": (11, 4), "f": [(4, 3), (2, 7), (6, 10)], "r": (11, 12)},       # 1 뒤로 펼쳐 내려오는 중
    {"wr": (9, 12), "f": [(2, 14), (3, 19), (8, 19)], "r": (12, 15)},     # 2 아래로 쳐냄
    {"wr": (14, 4), "f": [(11, 3), (9, 6), (11, 9)], "r": (12, 11)},      # 3 접으며 올림
]


def wing(pose):
    cv = Cv()
    sx, sy = 14, 11
    w = WINGS[pose]
    wr, fs, r = w["wr"], w["f"], w["r"]
    pts = [(sx, sy), wr]
    for i, f in enumerate(fs):
        pts.append(f)
        nxt = fs[i + 1] if i + 1 < len(fs) else r
        mx, my = (f[0] + nxt[0]) / 2, (f[1] + nxt[1]) / 2       # 손가락 사이 막은 안쪽으로 오목
        pts.append((mx + (wr[0] - mx) * 0.3, my + (wr[1] - my) * 0.3))
    pts.append(r)
    cv.poly(pts, MEMB)
    cv.line(sx, sy, wr[0], wr[1], G)                             # 팔뼈 (몸 색)
    cv.line(sx + 1, sy, wr[0] + 1, wr[1], G)
    for f in fs:                                                 # 손가락뼈
        cv.line(wr[0], wr[1], f[0], f[1], shade(MEMB, 0.8), to="dt")
    for (x, y) in list(cv.px):                                   # 팔뼈 윗면 광택
        if cv.px[(x, y)] == G and (x, y - 1) not in cv.px:
            cv.dt[(x, y)] = G_HI
    cv.put(wr[0], wr[1] - 1, HORN)                               # 날개 발톱
    return cv


def dragon(frame, mode="walk"):
    run, idle = mode == "run", mode == "idle"
    cv = Cv()
    pose = 3 if idle else frame % 4
    bob = 0 if idle else [1, 0, -1, 0][pose]
    sway = 0 if run else ([0, -1, -1, 0][frame % 4] if not idle else [0, -1][frame % 2])
    # 꼬리: 몸 뒤에서 위로 말려 올라가는 끝 (달릴 땐 뒤로 쭉)
    tail = [(9, 16, 2.3), (6.4, 16.6, 1.8), (4.3, 15.8, 1.4), (2.9, 14.2 + sway * 0.6, 1.1)]
    tx, ty = 1, 11 + sway
    if run:
        tail = [(9, 16, 2.3), (6.2, 15.8, 1.8), (4.1, 15.2, 1.4), (2.4, 14.6, 1.1)]
        tx, ty = 0, 12
    for x, y, r in tail:
        cv.ellipse(x, y, r, r, G)
    cv.art(tx, ty, [".s.", "sss", ".s."], {"s": SPIKE}, to="px")  # 꼬리 끝 가시
    # 몸 · 목 · 머리 (머리를 크게 — 꼬마 비율)
    cv.ellipse(14.5, 15.2, 6.4, 4.6, G)
    cv.rect(18, 10, 21, 14, G)
    cv.ellipse(24.5, 8.2, 6.2, 5.0, G)
    cv.ellipse(29.4, 9.8, 2.7, 2.1, G)
    # 다리 (날 땐 대롱대롱, 달릴 땐 뒤로 접음) · 팔
    lx = -1 if run else 0
    cv.ellipse(11.5 + lx, 17.6, 2.6, 2.2, G)
    cv.rect(10 + lx, 19, 12 + lx, 20, G)
    cv.rect(18, 18, 19, 20 if not run else 19, G)
    cv.put(21, 15, G); cv.put(21, 16, G)
    # 등 가시 · 뿔
    tops = {}
    for (x, y) in cv.px:
        tops[x] = min(tops.get(x, 99), y)
    for x in (10, 13, 16, 6):
        cv.put(x, tops[x] - 1, SPIKE)
    cv.put(21, 3, HORN); cv.put(20, 2, HORN); cv.put(26, 3, HORN); cv.put(26, 2, HORN)
    # 무늬: 배 비늘 · 광택 · 그늘
    cv.ellipse(17, 16.2, 3.7, 2.7, BELLY, to="dt", keep=lambda x, y: (x, y) in cv.px)
    for (x, y) in list(cv.dt):
        if cv.dt[(x, y)] == BELLY and y in (15, 17) and (x + 1, y) in cv.dt:
            cv.dt[(x, y)] = BELLY_DK
    cv.top_light(G_HI, skip=(SPIKE, HORN), x0=18, x1=31)
    for (x, y) in list(cv.px):
        if cv.px[(x, y)] == G and (x, y + 1) not in cv.px and (x, y) not in cv.dt:
            cv.dt[(x, y)] = G_DK
    cv.dt[(10 + lx, 20)] = HORN; cv.dt[(12 + lx, 20)] = HORN; cv.dt[(19, 20 if not run else 19)] = HORN   # 발톱
    # 얼굴: 큰 눈 · 볼터치 · 콧구멍 · 웃는 입
    if idle and frame == 1:
        cv.dt[(25, 9)] = EYE; cv.dt[(26, 9)] = EYE; cv.dt[(24, 8)] = EYE   # 눈 감음 (^)
    else:
        cv.rect(25, 7, 26, 9, EYE, to="dt")
        cv.dt[(25, 7)] = GLINT; cv.dt[(26, 9)] = (70, 84, 120, 255)
    cv.dt[(23, 10)] = BLUSH; cv.dt[(24, 10)] = BLUSH
    cv.dt[(31, 9)] = G_DK
    cv.dt[(28, 11)] = G_DK; cv.dt[(29, 11)] = G_DK; cv.dt[(27, 10)] = G_DK
    # 가까운 쪽 날개 (몸 위에 얹고 경계선)
    cv.overlay(wing(pose))
    if run:
        speed_lines(cv, frame, [(6, 3, 0), (20, 4, 5)], 6)
    return cv.image(dy=bob, tilt=0.12 if run else 0.0, cx=17)


# ── 비행기: 흰 몸 + 파란 줄, 프로펠러 잔상 회전 · 항법등 깜빡 · 창문 줄 · 달릴 땐 살짝 기울기 ──
BLUE = (52, 120, 220, 255)
BLUE_HI = (120, 178, 248, 255)
BLUE_DK = (36, 88, 176, 255)
WHITE_SH = (212, 218, 230, 255)


def plane(frame, mode="walk"):
    run, idle = mode == "run", mode == "idle"
    cv = Cv()
    f = frame % 4
    cv.spans({3: (3, 5), 4: (3, 6), 5: (3, 6), 6: (3, 7), 7: (3, 8), 8: (3, 9), 9: (3, 10)}, BLUE)   # 꼬리 날개
    cv.spans({9: (19, 24), 10: (6, 26), 11: (4, 28), 12: (3, 29), 13: (3, 29), 14: (5, 28), 15: (9, 26)}, WHITE)
    cv.rect(1, 12, 6, 12, BLUE_DK)                     # 수평 꼬리날개
    tipy = 19 if not run else 21                       # 달릴 땐 기울어(뱅크) 가까운 날개가 더 내려와 보임
    wing_pts = [(15, 14), (23, 14), (14, tipy), (10, tipy)]
    cv.rect(30, 12, 30, 13, REDL)                      # 스피너
    # 무늬
    for x in range(4, 29):
        if cv.px.get((x, 13)) == WHITE:
            cv.dt[(x, 13)] = BLUE                      # 파란 줄
        if cv.px.get((x, 14)) == WHITE:
            cv.dt[(x, 14)] = WHITE_SH
    for x in (8, 10, 12, 14, 16):                      # 창문 줄
        cv.dt[(x, 11)] = GLASS_DK
    cv.art(21, 9, ["GGG..", "GGGGG", ".GGGGG"], {"G": GLASS})   # 조종석 앞유리
    cv.dt[(21, 9)] = GLINT; cv.dt[(22, 10)] = GLINT
    cv.dt[(26, 11)] = GLASS_DK
    cv.top_light(GLINT, skip=(BLUE, BLUE_DK, GLASS, REDL), x0=6, x1=19)   # 동체 윗선 반짝
    for y in range(3, 10):                             # 꼬리날개 앞선 광택
        xs = [x for (x, yy) in cv.px if yy == y and cv.px[(x, yy)] == BLUE]
        if xs:
            cv.dt[(max(xs), y)] = BLUE_HI
    cv.rect(3, 6, 6, 6, YEL, to="dt")                  # 꼬리 띠
    wg = Cv()                                          # 주날개: 동체 아래로 비스듬히 뻗은 가까운 날개
    wg.poly(wing_pts, BLUE)
    for (x, y) in list(wg.px):
        if (x + 1, y) not in wg.px:
            wg.dt[(x, y)] = BLUE_HI                    # 앞전 광택
        elif (x - 1, y) not in wg.px or (x, y + 1) not in wg.px:
            wg.dt[(x, y)] = BLUE_DK
    cv.overlay(wg)
    # 항법등: 날개 끝 빨강 · 꼬리 위 초록 · 등 위 경광등
    if idle:
        on_r = on_g = beacon = frame == 1
    else:
        on_r, on_g, beacon = f in (0, 1), f in (2, 3), f == 0 or (run and f == 2)
    cv.put(11, tipy, (255, 70, 60, 255) if on_r else (150, 40, 40, 255))
    if on_r and not idle:
        cv.fx[(10, tipy + 1)] = (255, 110, 90, 120); cv.fx[(12, tipy + 1)] = (255, 110, 90, 120)
    cv.put(3, 2, (90, 240, 120, 255) if on_g else (40, 120, 60, 255))
    cv.put(20, 8, (255, 80, 60, 255) if beacon else (160, 50, 50, 255))
    if beacon:
        cv.fx[(20, 6)] = (255, 110, 90, 150)
    # 프로펠러: 잔상 원판 + 날이 돈다 (끝은 노랑) — 외곽선 없이 가늘게
    blade = BLADE
    PX = 32
    if idle:
        for y in range(6, 20):
            cv.dt[(PX, y)] = blade
        cv.dt[(PX, 5)] = YEL; cv.dt[(PX, 20)] = YEL
    else:
        for y in range(4, 22):
            cv.fx[(PX, y)] = BLUR
            cv.fx[(PX + 1, y)] = alpha(BLUR, 50)
        L = [8, 5, 1, 5][f] if not run else [8, 2, 6, 1][f]
        for y in range(12 - L, 14 + L):
            cv.dt[(PX, y)] = blade
        if L >= 3:
            cv.dt[(PX, 12 - L)] = YEL; cv.dt[(PX, 13 + L)] = YEL
        else:
            cv.dt[(PX + 1, 12)] = blade; cv.dt[(PX + 1, 13)] = blade
        if run:
            speed_lines(cv, frame, [(7, 3, 0), (15, 4, 4), (19, 3, 7)], 8)
    bob = 0 if idle or run else [0, 0, -1, -1][f]
    return cv.image(dy=bob + (1 if run else 0), tilt=0.07 if run else 0.0, cx=17)


# ── 헬기: 노란 몸, 메인 로터 잔상(긴 날·짧은 날) · 꼬리 로터 회전 · 스키드 · 유리 반짝 ──
Y_ = (250, 198, 44, 255)
Y_HI = (255, 232, 124, 255)
Y_DK = (214, 150, 30, 255)
STRIPE = (226, 64, 52, 255)


def heli(frame, mode="walk"):
    run, idle = mode == "run", mode == "idle"
    cv = Cv()
    f = frame % 4
    cv.spans({11: (4, 15), 12: (4, 15), 13: (9, 15)}, Y_)          # 꼬리 붐
    cv.spans({8: (3, 3), 9: (2, 4), 10: (2, 4), 11: (2, 4), 12: (2, 4), 13: (3, 4)}, Y_)   # 꼬리 날개
    cv.rect(8, 14, 10, 14, Y_DK)                                    # 수평 안정판
    cv.ellipse(21.5, 14, 7.4, 4.9, Y_)                              # 몸통
    cv.rect(16, 9, 21, 9, Y_DK)                                     # 엔진 덮개
    cv.rect(20, 6, 21, 8, STEEL)                                    # 마스트
    cv.rect(13, 21, 29, 21, STEEL); cv.put(30, 20, STEEL)           # 스키드
    cv.rect(16, 19, 16, 20, STEEL); cv.rect(26, 19, 26, 20, STEEL)
    # 무늬: 유리 · 반짝 · 줄 · 그늘
    cv.ellipse(25.2, 12.6, 4.3, 3.4, GLASS, to="dt", keep=lambda x, y: (x, y) in cv.px and x >= 23)
    for p in ((27, 11), (28, 12), (28, 13)):
        if p in cv.dt:
            cv.dt[p] = GLASS_DK
    cv.dt[(24, 10)] = GLINT; cv.dt[(23, 11)] = GLINT
    if (idle and frame == 1) or (not idle and f == 1):              # 유리에 빛이 스침
        cv.dt[(25, 11)] = GLINT; cv.dt[(24, 12)] = GLINT; cv.dt[(26, 10)] = GLINT
    cv.rect(17, 11, 20, 13, GLASS, to="dt"); cv.dt[(17, 11)] = GLINT  # 옆창
    for y in (11, 12, 13, 14):
        cv.dt[(21, y)] = Y_DK                                       # 문 틈
    cv.top_light(Y_HI, skip=(STEEL, Y_DK), x0=2, x1=24)
    for x in range(14, 30):
        if cv.px.get((x, 16)) == Y_:
            cv.dt[(x, 16)] = STRIPE
        for y in (17, 18):
            if cv.px.get((x, y)) == Y_:
                cv.dt[(x, y)] = Y_DK
    cv.rect(6, 11, 7, 12, STRIPE, to="dt")                          # 꼬리 띠
    # 경광등 (배 아래)
    on = (frame == 1) if idle else (f in (0, 2) if run else f == 0)
    cv.put(21, 19, (255, 70, 60, 255) if on else (150, 44, 44, 255))
    if on:
        cv.fx[(20, 20)] = (255, 110, 90, 120); cv.fx[(22, 20)] = (255, 110, 90, 120)
    # 메인 로터: 외곽선 없는 가는 날 + 반투명 잔상
    cv.rect(18, 5, 23, 5, STEEL)                                    # 허브
    blade = BLADE
    tip = (196, 200, 214, 255)
    if idle:                                                        # 멈춘 로터: 끝이 살짝 처짐
        for x in range(4, 31):
            cv.dt[(x, 4)] = blade
        for x in (1, 2, 3, 31, 32, 33):
            cv.dt[(x, 5)] = blade
    else:
        for x in range(1, 34):
            cv.fx[(x, 4)] = BLUR
        for x in range(6, 29):
            cv.fx[(x, 3)] = alpha(BLUR, 40)
        span = [(1, 33), (7, 29), (16, 25), (11, 33)][f] if not run else [(1, 33), (14, 27), (4, 33), (17, 24)][f]
        for x in range(span[0], span[1] + 1):
            cv.dt[(x, 4)] = blade
        cv.dt[(span[0], 4)] = tip; cv.dt[(span[1], 4)] = tip
        cv.dt[(20, 3)] = blade; cv.dt[(21, 3)] = blade              # 허브 위 캡
    # 꼬리 로터 (중심 3,8): 반투명 원판 + 날 회전
    tr = BLADE
    if not idle:
        for y in range(4, 13):
            for x in range(0, 8):
                if 1.5 < math.hypot(x - 3, y - 8) <= 3.2:
                    cv.fx[(x, y)] = alpha(BLUR, 80)
    a = (0 if idle else f) * math.pi / 4 + (math.pi / 8 if idle else 0)
    for r in (-3, -2, -1, 1, 2, 3):
        cv.dt[(3 + rnd(r * math.sin(a)), 8 - rnd(r * math.cos(a)))] = tr
    cv.dt[(3, 8)] = HUB
    if run:
        speed_lines(cv, frame, [(16, 4, 0), (19, 3, 4)], 11)
    bob = 0 if idle or run else [0, -1, -1, 0][f]
    return cv.image(dy=bob, tilt=0.1 if run else 0.0, cx=18)


# ── UFO: 금속 접시, 테두리 불빛 줄달음 · 유리 돔 속 꼬마 외계인(깜빡) · 둥실 흔들 ──
M_HI = (222, 228, 240, 255)
M_ = (176, 184, 200, 255)
M_DK = (124, 132, 152, 255)
RIMBAND = (88, 96, 118, 255)
ALIEN = (124, 222, 110, 255)
BEAM = (120, 244, 222, 255)
LIGHTS = [(255, 84, 84), (255, 214, 60), (110, 240, 120), (90, 200, 255), (255, 120, 220)]


def ufo(frame, mode="walk"):
    run, idle = mode == "run", mode == "idle"
    cv = Cv()
    f = frame % 4
    cv.ellipse(16.5, 11, 6.6, 6.4, GLASS)                           # 유리 돔
    cv.spans({12: (9, 24), 13: (6, 27), 14: (3, 30), 15: (1, 32), 16: (2, 31),
              17: (6, 27), 18: (10, 23)}, M_)                       # 접시
    cv.rect(13, 19, 20, 19, M_DK)                                   # 빔 구멍
    # 돔 무늬: 오른쪽 그늘 · 왼쪽 위 반짝
    for (x, y), c in list(cv.px.items()):
        if c == GLASS and x >= 21:
            cv.dt[(x, y)] = GLASS_DK
    for p in ((12, 7), (11, 8), (11, 9), (13, 6)):
        cv.dt[p] = GLINT
    # 외계인 (안테나 공이 살랑, 가끔 깜빡)
    blink = idle and frame == 1
    ant = 0 if idle else [0, 1, 0, -1][f]
    look = 0 if idle else [0, 0, 1, 1][f]                # 두리번 (눈 반짝점 이동)
    pal = {"g": ALIEN, "e": EYE, "w": GLINT, "m": (200, 70, 110, 255), "d": shade(ALIEN, 0.75)}
    rows = ["..gggg..",
            ".gggggg.",
            ("gweggweg" if look <= 0 else "gewggewg") if not blink else "gggggggg",
            "geeggeeg",
            ".ggmmgg.",
            "dggggggd"]
    cv.art(13, 7, rows, pal)
    cv.dt[(16 + ant, 5)] = (255, 120, 180, 255); cv.dt[(17 + ant, 5)] = (255, 120, 180, 255)
    cv.dt[(16 if ant <= 0 else 17, 6)] = shade(ALIEN, 0.75)
    # 접시 무늬: 위 밝게 · 테 띠 어둡게 · 아래 그늘
    for x in range(1, 33):
        if cv.px.get((x, 12)) == M_:
            cv.dt[(x, 12)] = M_HI
        if cv.px.get((x, 13)) == M_ and 8 < x < 25:
            cv.dt[(x, 13)] = M_HI
        if cv.px.get((x, 15)) == M_:
            cv.dt[(x, 15)] = RIMBAND
        for y in (16, 17, 18):
            if cv.px.get((x, y)) == M_:
                cv.dt[(x, y)] = M_DK
    cv.dt[(10, 12)] = GLINT; cv.dt[(11, 12)] = GLINT; cv.dt[(7, 13)] = GLINT
    # 테두리 불빛 줄달음: 밝은 불 + 꼬리 불이 오른쪽으로 달린다
    for i, x in enumerate((2, 6, 10, 14, 18, 22, 26, 30)):
        col = LIGHTS[i % len(LIGHTS)] + (255,)
        if idle:
            lv = 2 if (i % 2) == frame % 2 else 0
        else:
            k = (i - f) % 4
            lv = 2 if k == 0 else 1 if k == 3 else 0
            if run and k == 2:
                lv = 2
        c = col if lv == 2 else shade(col, 0.72) if lv == 1 else (62, 68, 86, 255)
        cv.dt[(x, 15)] = c; cv.dt[(x + 1, 15)] = c
        if lv == 2:
            cv.dt[(x, 15)] = shade(col, 1.0)[:3] + (255,)
            cv.dt[(x + 1, 15)] = tuple(min(255, v + 90) for v in col[:3]) + (255,)
            cv.dt[(x, 14)] = col[:3] + (140,); cv.dt[(x + 1, 14)] = col[:3] + (140,)
    # 빔 구멍 빛 + 아래로 새는 빛
    glow = BEAM if (run or f % 2 == 0) else shade(BEAM, 0.8)
    cv.rect(14, 19, 19, 19, glow, to="dt")
    cv.dt[(15, 19)] = GLINT
    if not idle:
        for x in range(13, 21):
            cv.fx[(x, 20)] = alpha(BEAM, 130 if run else 90)
        if run or f % 2 == 0:
            for x in range(14, 20):
                cv.fx[(x, 21)] = alpha(BEAM, 60)
    if run:
        speed_lines(cv, frame, [(10, 4, 0), (18, 3, 5)], 7)
    bob = 0 if idle else [0, -1, -1, 0][f]
    tilt = 0.0 if idle else ([0.0, 0.06, 0.0, -0.06][f] if not run else 0.12)
    return cv.image(dy=bob + (1 if run else 0), tilt=tilt, cx=16.5)


ITEMS = {"car": car, "dragon": dragon, "plane": plane, "heli": heli, "ufo": ufo}
KINDS = (("walk", 4), ("run", 4), ("idle", 2))


def main(out, preview):
    os.makedirs(out, exist_ok=True)
    rows = []
    for name, fn in ITEMS.items():
        row = []
        for kind, n in KINDS:
            frames = [fn(i, kind) for i in range(n)]
            sheet = Image.new("RGBA", (W * n, H), CLEAR)
            for i, f in enumerate(frames):
                sheet.alpha_composite(f, (i * W, 0))
            sheet.save(os.path.join(out, f"{name}_{kind}.png"))
            row.append((kind, frames))
        rows.append((name, row))
    # 미리보기: 줄마다 한 캐릭터 — walk 4 | run 4 | idle 2, 6배 확대, 흰 바탕
    S, GAP, SEC, TOP, LEFT = 6, 10, 40, 30, 90
    total = sum(n for _, n in KINDS)
    pw = LEFT + total * (W * S + GAP) + (len(KINDS) - 1) * SEC + 10
    ph = TOP + len(rows) * (H * S + GAP) + 10
    prev = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
    dr = ImageDraw.Draw(prev)
    for r, (name, row) in enumerate(rows):
        x = LEFT
        y = TOP + r * (H * S + GAP)
        dr.text((10, y + H * S // 2 - 6), name, fill=(40, 40, 40, 255))
        for kind, frames in row:
            if r == 0:
                dr.text((x, 8), f"{kind} ({len(frames)})", fill=(40, 40, 40, 255))
            for f in frames:
                dr.rectangle([x - 1, y - 1, x + W * S, y + H * S], outline=(232, 232, 236, 255))
                prev.alpha_composite(f.resize((W * S, H * S), Image.NEAREST), (x, y))
                x += W * S + GAP
            x += SEC
    os.makedirs(os.path.dirname(os.path.abspath(preview)), exist_ok=True)
    prev.save(preview)
    print("ok", list(ITEMS), [k for k, _ in KINDS])


if __name__ == "__main__":
    main(*sys.argv[1:3])
