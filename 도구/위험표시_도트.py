"""
Pixel TMI 길 위 그림 — 위험 표시 · 레이싱 결승 깃발 · 코인을 고양이와 같은 결(컬러 도트 + 진한 외곽선)로 그린다.
예전 검은 선 픽토그램이 캐릭터 옆에서 따로 놀아서("돌 같은 거"), 색을 넣고 움직임 프레임을 붙였다.
사용: python 위험표시_도트.py <출력 폴더(assets/pet)> <미리보기.png> [새18종_미리보기.png]
출력: haz_<종류>.png (24x24 프레임을 가로로 이어 붙임) · flag_race.png (32x32 x 4프레임) · coin_spin.png (16x16 x 4프레임)
2차 추가(18종): emergency fire breakdown animal pedestrian flood fog jam signal rockfall wrong_way road_closed
               hail snow wind tsunami wildfire avalanche — 기존 10종 그림 함수는 그대로라 결과도 그대로다.
"""
import math
import sys

from PIL import Image

OUT = (46, 48, 56, 255)      # 외곽선
CLEAR = (0, 0, 0, 0)


def c(r, g, b):
    return (r, g, b, 255)


class Cv:
    def __init__(self, w=24, h=24):
        self.w, self.h = w, h
        self.px = {}
        self.top = {}      # 외곽선 위에 얹는 디테일 (외곽선 계산에서 빠짐)

    def put(self, x, y, col, top=False):
        if 0 <= x < self.w and 0 <= y < self.h:
            (self.top if top else self.px)[(x, y)] = col

    def rect(self, x0, y0, x1, y1, col, top=False):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, col, top)

    def ellipse(self, cx, cy, rx, ry, col, top=False):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.put(x, y, col, top)

    def tri(self, pts, col, top=False):
        (x0, y0), (x1, y1), (x2, y2) = pts
        def side(ax, ay, bx, by, px, py):
            return (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        for y in range(min(y0, y1, y2), max(y0, y1, y2) + 1):
            for x in range(min(x0, x1, x2), max(x0, x1, x2) + 1):
                s1 = side(x0, y0, x1, y1, x + .5, y + .5)
                s2 = side(x1, y1, x2, y2, x + .5, y + .5)
                s3 = side(x2, y2, x0, y0, x + .5, y + .5)
                if (s1 >= 0 and s2 >= 0 and s3 >= 0) or (s1 <= 0 and s2 <= 0 and s3 <= 0):
                    self.put(x, y, col, top)

    def image(self, outline=True):
        im = Image.new("RGBA", (self.w, self.h), CLEAR)
        if outline:
            for (x, y) in list(self.px):
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + dx, y + dy)
                    if n not in self.px and 0 <= n[0] < self.w and 0 <= n[1] < self.h:
                        im.putpixel(n, OUT)
        for d in (self.px, self.top):
            for (x, y), col in d.items():
                im.putpixel((x, y), col)
        return im


def sheet(frames):
    w, h = frames[0].size
    s = Image.new("RGBA", (w * len(frames), h), CLEAR)
    for i, f in enumerate(frames):
        s.paste(f, (i * w, 0))
    return s


# ── 단속 카메라: 기둥 위 회색 상자 + 렌즈, 둘째 프레임은 찰칵 섬광 ──
def camera(flash):
    v = Cv()
    v.rect(11, 13, 12, 23, c(150, 156, 166))
    v.rect(11, 13, 11, 23, c(186, 192, 200))
    v.rect(9, 22, 14, 23, c(120, 126, 136))
    v.rect(3, 4, 20, 12, c(218, 222, 228))
    v.rect(3, 4, 20, 5, c(240, 242, 246))
    v.rect(3, 11, 20, 12, c(168, 174, 184))
    v.rect(16, 2, 20, 3, c(180, 186, 196))          # 차양
    v.ellipse(8, 8, 3.2, 3.2, c(40, 44, 54), top=True)
    v.ellipse(8, 8, 2.0, 2.0, c(70, 120, 190), top=True)
    v.put(7, 7, c(210, 236, 255), top=True)
    v.rect(13, 9, 19, 10, c(246, 196, 40), top=True)  # 노란 '단속' 띠
    for x in (14, 16, 18):
        v.put(x, 9, c(46, 48, 56), top=True)
    v.put(18, 6, c(230, 40, 40), top=True)           # 빨간 불
    v.put(19, 6, c(255, 120, 110), top=True)
    if flash:
        for dx, dy in ((-5, 0), (-4, -3), (-4, 3), (0, -5), (0, 5), (-6, 0), (-3, -4), (-3, 4)):
            v.put(8 + dx, 8 + dy, c(255, 250, 200), top=True)
        v.put(1, 8, c(255, 230, 110), top=True); v.put(8, 1, c(255, 230, 110), top=True); v.put(8, 15, c(255, 230, 110), top=True)
        v.ellipse(8, 8, 2.0, 2.0, c(255, 255, 240), top=True)
    return v.image()


# ── 비구름: 흰 구름 + 떨어지는 파란 빗방울 ──
def rain(phase):
    v = Cv()
    for (cx, cy, r) in ((7, 9, 4.6), (12, 6, 5.4), (17, 9, 4.6), (12, 10, 5.0)):
        v.ellipse(cx, cy, r, r * 0.92, c(236, 240, 248))
    v.rect(3, 10, 21, 13, c(236, 240, 248))
    for x in range(3, 22):
        v.put(x, 13, c(176, 186, 204)); v.put(x, 12, c(204, 212, 226))
    for (x, y) in ((9, 3), (10, 2), (11, 2), (8, 4)):
        v.put(x, y, c(255, 255, 255), top=True)
    for i, x in enumerate((5, 9, 13, 17, 20)):
        y = 15 + ((i * 3 + phase * 3) % 8)
        v.put(x, y, c(60, 150, 240)); v.put(x, y + 1, c(60, 150, 240)); v.put(x - 1, y + 1, c(150, 200, 255))
    return v.image()


# ── 포트홀: 차선 그려진 아스팔트에 깊게 패인 구멍(물 고임) + 금 + 튄 조각 + 고깔 ──
def pothole(phase):
    v = Cv()
    v.ellipse(11.5, 18.5, 11.5, 5.2, c(96, 100, 110))
    for (x, y) in ((3, 17), (6, 21), (18, 15), (20, 20), (14, 22), (9, 15)):
        v.put(x, y, c(124, 128, 138))
    v.rect(1, 18, 4, 19, c(240, 240, 236))                     # 흰 차선
    v.ellipse(11.5, 18.8, 6.6, 3.0, c(34, 30, 32), top=True)   # 구멍
    for x in range(6, 18):
        v.put(x, 16, c(140, 104, 70), top=True)                # 안쪽 벽(흙)
    v.ellipse(12.5, 20.0, 3.6, 1.2, c(60, 110, 176), top=True)  # 고인 물
    v.put(11 + phase, 20, c(170, 210, 250), top=True)
    for (x, y) in ((4, 15), (3, 14), (19, 21), (20, 22), (18, 16), (19, 15), (5, 22)):
        v.put(x, y, c(40, 40, 46), top=True)                   # 금
    v.put(16, 11 - phase, c(124, 128, 138)); v.put(7, 12 + phase, c(124, 128, 138))   # 튄 조각
    # 작은 고깔 (오른쪽)
    v.tri(((20, 6), (17, 15), (23, 15)), c(244, 120, 40))
    v.rect(19, 9, 21, 10, c(250, 250, 250), top=True)
    v.rect(16, 15, 23, 16, c(200, 86, 30))
    return v.image()


# ── 사고: 앞이 찌그러진 빨간 차 + 연기 + 불꽃 + 삼각대 ──
def accident(phase):
    v = Cv()
    v.rect(3, 13, 19, 18, c(220, 52, 52))
    v.rect(6, 9, 15, 12, c(220, 52, 52))
    v.rect(7, 10, 10, 12, c(170, 216, 246)); v.rect(12, 10, 14, 12, c(170, 216, 246))
    v.rect(3, 13, 19, 13, c(244, 110, 104))
    for (x, y) in ((19, 13), (20, 15), (19, 16), (20, 17), (18, 14)):
        v.put(x, y, c(160, 34, 34))                           # 찌그러진 앞
    v.put(3, 15, c(255, 230, 120), top=True)                  # 뒷등
    for wx in (6, 16):
        v.ellipse(wx, 19, 2.3, 2.3, c(36, 36, 40))
        v.put(wx, 19, c(170, 170, 176), top=True)
    off = phase
    for (cx, cy, r, col) in ((18, 9 - off, 1.6, (176, 178, 186)), (20, 5 - off, 2.0, (196, 198, 206)), (17, 1 - off, 1.4, (218, 220, 226))):
        v.ellipse(cx, cy, r, r, c(*col), top=True)        # 피어오르는 연기 (외곽선 없이 옅게)
    star = c(255, 220, 60) if phase == 0 else c(255, 150, 40)
    for (x, y) in ((22, 12), (23, 11), (22, 10), (21, 11), (23, 13)):
        v.put(x, y, star, top=True)
    v.tri(((1, 16), (-1, 22), (4, 22)), c(232, 40, 40))       # 삼각대
    v.put(1, 20, c(255, 255, 255), top=True)
    return v.image()


# ── 급정거 다발: 뒷모습 차 + 번쩍이는 빨간 브레이크등 + 스키드 자국 ──
def hardbrake(phase):
    v = Cv()
    v.rect(4, 9, 19, 17, c(236, 238, 242))
    v.rect(6, 5, 17, 8, c(236, 238, 242))
    v.rect(7, 6, 16, 8, c(70, 90, 120))                       # 뒷유리
    v.rect(4, 15, 19, 17, c(196, 200, 208))
    v.rect(9, 12, 14, 13, c(250, 220, 90), top=True)          # 번호판
    v.rect(4, 18, 6, 20, c(36, 36, 40)); v.rect(17, 18, 19, 20, c(36, 36, 40))
    lamp = c(255, 40, 40) if phase == 0 else c(170, 40, 40)
    v.rect(4, 10, 6, 11, lamp, top=True); v.rect(17, 10, 19, 11, lamp, top=True)
    if phase == 0:
        for (x, y) in ((2, 10), (2, 11), (3, 9), (21, 10), (21, 11), (20, 9), (11, 4), (12, 4)):
            v.put(x, y, c(255, 130, 110), top=True)
        v.rect(11, 4, 12, 4, c(255, 50, 50), top=True)        # 보조 제동등
    for y in range(21, 24):
        v.put(5 + (y % 2), y, c(40, 40, 46), top=True); v.put(18 - (y % 2), y, c(40, 40, 46), top=True)
    return v.image()


# ── 낙하물: 상자 + 타이어 + 흩어진 조각 ──
def debris(phase):
    v = Cv()
    v.rect(2, 11, 11, 20, c(200, 146, 84))
    v.rect(2, 11, 11, 12, c(226, 178, 112))
    v.rect(6, 11, 7, 20, c(236, 214, 160), top=True)          # 테이프
    v.rect(9, 17, 10, 18, c(150, 100, 52), top=True)
    v.ellipse(17, 16, 5, 5.2, c(40, 40, 46))
    v.ellipse(17, 16, 2.4, 2.6, c(150, 154, 162), top=True)
    v.put(17, 16, c(90, 94, 100), top=True)
    for (x, y) in ((14, 12), (20, 13), (15, 20), (19, 19)):
        v.put(x, y, c(70, 70, 78), top=True)                  # 트레드
    v.put(1, 22, c(226, 178, 112)); v.put(13, 23, c(150, 154, 162)); v.put(22, 22 - phase, c(200, 146, 84))
    return v.image()


# ── 공사: 줄무늬 바리케이드 + 노란 경광등(깜빡) + 고깔 ──
def construction(phase):
    v = Cv()
    v.rect(3, 15, 4, 22, c(200, 200, 206)); v.rect(17, 15, 18, 22, c(200, 200, 206))
    v.rect(1, 9, 20, 14, c(250, 250, 250))
    for x in range(1, 21):
        for y in range(9, 15):
            if ((x + y) // 3) % 2 == 0:
                v.put(x, y, c(244, 110, 30))
    v.rect(9, 6, 12, 8, c(70, 70, 78))
    lamp = c(255, 214, 40) if phase == 0 else c(150, 120, 40)
    v.ellipse(10.5, 5, 1.8, 1.6, lamp, top=True)
    if phase == 0:
        for (x, y) in ((7, 4), (14, 4), (10, 1), (11, 1), (7, 6), (14, 6)):
            v.put(x, y, c(255, 240, 140), top=True)
    v.tri(((21, 13), (18, 22), (24, 22)), c(244, 120, 40))
    v.rect(20, 17, 22, 18, c(250, 250, 250), top=True)
    v.rect(17, 22, 23, 23, c(200, 86, 30))
    return v.image()


# ── 결빙: 반짝이는 얼음판 + 눈송이 ──
def ice(phase):
    v = Cv()
    v.ellipse(11.5, 19.5, 11, 3.8, c(170, 224, 248))
    for (x0, x1, y) in ((4, 8, 18), (13, 18, 20), (8, 10, 21)):
        for x in range(x0, x1 + 1):
            v.put(x, y, c(240, 252, 255), top=True)
    cx, cy = 11, 8
    for d in range(-5, 6):
        v.put(cx + d, cy, c(250, 252, 255)); v.put(cx, cy + d, c(250, 252, 255))
        if abs(d) <= 3:
            v.put(cx + d, cy + d, c(250, 252, 255)); v.put(cx + d, cy - d, c(250, 252, 255))
    v.put(cx, cy, c(120, 190, 240), top=True)
    sx, sy = (19, 3) if phase == 0 else (3, 12)
    for (dx, dy) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        v.put(sx + dx, sy + dy, c(255, 255, 255), top=True)
    return v.image()


# ── 과속방지턱: 노랑·검정 줄무늬 둔덕 ──
def bump(phase):
    v = Cv()
    v.rect(0, 20, 23, 22, c(100, 104, 114))
    v.ellipse(11.5, 21, 11, 8, c(250, 204, 40))
    for y in range(12, 21):
        for x in range(0, 24):
            if (x, y) in v.px and ((x - y) // 3) % 2 == 0:
                v.put(x, y, c(52, 52, 58))
    v.rect(0, 20, 23, 22, c(100, 104, 114))
    for x in range(5, 19):
        if (x, 14) in v.px:
            v.put(x, 14, c(255, 236, 140), top=True) if ((x - 14) // 3) % 2 else None
    v.rect(2, 21, 5, 21, c(240, 240, 236), top=True); v.rect(18, 21, 21, 21, c(240, 240, 236), top=True)
    return v.image()


# ── 어린이 보호구역: 빨간 테 삼각 표지 + 걸어가는 두 아이 ──
def school(phase):
    v = Cv()
    v.rect(11, 15, 12, 23, c(170, 176, 186))
    v.tri(((11, 0), (0, 17), (23, 17)), c(226, 40, 40))
    v.tri(((11, 4), (4, 15), (19, 15)), c(252, 214, 40))
    k = c(40, 40, 46)
    b = phase
    # 큰 아이
    v.put(9, 7, k, True); v.rect(8, 8, 10, 11, k, True); v.put(8, 12 + b, k, True); v.put(10, 13 - b, k, True)
    v.rect(7, 9, 7, 10, c(226, 40, 40), True)                  # 빨간 책가방
    # 작은 아이
    v.put(14, 9, k, True); v.rect(13, 10, 15, 12, k, True); v.put(13, 13 - b, k, True); v.put(15, 13 + b - 1, k, True)
    v.put(12, 10, k, True)                                    # 손 잡기
    return v.image()


# ════════ 2차 추가 (18종): 긴급차·화재·고장·동물·보행자·침수·안개·정체·신호고장·낙석·역주행·통제 · 우박·폭설·강풍·해일·산불·눈사태 ════════
K = c(40, 40, 46)
GLASS = c(170, 216, 246)


def line(v, x0, y0, x1, y1, col, w=1, top=False):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        x = round(x0 + (x1 - x0) * i / n)
        y = round(y0 + (y1 - y0) * i / n)
        for dx in range(w):
            v.put(x + dx, y, col, top)


def wheel(v, x, y, r=2.3):
    v.ellipse(x, y, r, r, c(36, 36, 40))
    v.put(x, y, c(170, 170, 176), top=True)


# ── 구급차: 흰 차체 + 빨간 십자·띠 + 지붕 경광등 빨강/파랑 번갈아 ──
def emergency(phase):
    v = Cv()
    W, WS, R = c(248, 248, 250), c(204, 208, 218), c(228, 44, 44)
    v.rect(2, 7, 14, 18, W)
    v.rect(15, 10, 20, 18, W)
    v.rect(21, 13, 22, 18, W)
    v.rect(16, 11, 19, 13, GLASS, top=True)
    v.put(20, 12, GLASS, top=True); v.put(20, 13, GLASS, top=True)
    v.rect(2, 17, 22, 18, WS)
    v.rect(2, 15, 22, 15, R, top=True)
    v.rect(7, 8, 8, 13, R, top=True); v.rect(5, 10, 10, 11, R, top=True)
    v.put(22, 14, c(255, 220, 90), top=True)
    v.rect(4, 5, 11, 6, c(120, 126, 136))
    red = c(255, 50, 50) if phase == 0 else c(140, 40, 46)
    blue = c(50, 80, 150) if phase == 0 else c(60, 150, 255)
    v.rect(4, 5, 7, 6, red); v.rect(8, 5, 11, 6, blue)
    if phase == 0:
        for (x, y) in ((2, 4), (3, 2), (5, 1), (6, 2), (1, 6), (8, 3)):
            v.put(x, y, c(255, 110, 100), top=True)
    else:
        for (x, y) in ((13, 4), (12, 2), (10, 1), (9, 2), (14, 6), (7, 3)):
            v.put(x, y, c(120, 190, 255), top=True)
    wheel(v, 6, 19); wheel(v, 18, 19)
    return v.image()


# ── 차량 화재: 그을린 차 위로 일렁이는 불길 + 위로 오르는 검은 연기 ──
def fire(phase):
    v = Cv()
    sm1, sm2 = c(130, 132, 142), c(170, 172, 182)
    up = phase
    for (cx, cy, r, col) in ((9, 4 - up, 3.0, sm1), (14, 3 - up, 3.4, sm2), (18, 6 - up, 2.4, sm1), (5, 7 - up, 2.0, sm2)):
        v.ellipse(cx, cy, r, r * 0.9, col)
    body = c(78, 82, 92)
    v.rect(2, 15, 21, 19, body)
    v.rect(5, 12, 16, 14, body)
    v.rect(2, 15, 21, 15, c(112, 116, 126))
    wheel(v, 6, 20); wheel(v, 17, 20)
    tongues = [((4, 14), (6, 6), (9, 14)), ((7, 14), (11, 2), (15, 14)), ((12, 14), (17, 5), (19, 14))] if phase == 0 else \
              [((4, 14), (5, 4), (9, 14)), ((7, 14), (12, 4), (15, 14)), ((12, 14), (16, 7), (19, 14))]
    for t in tongues:
        v.tri(t, c(236, 70, 34))
    v.ellipse(11.5, 13, 7, 2.6, c(236, 70, 34))
    for (a, tip, b) in tongues:
        v.tri(((a[0] + 1, 14), (tip[0], tip[1] + 3), (b[0] - 1, 14)), c(252, 150, 30), top=True)
    v.ellipse(11.5, 13.4, 5, 1.6, c(252, 150, 30), top=True)
    mid = tongues[1][1]
    v.tri(((9, 14), (mid[0], mid[1] + 6), (13, 14)), c(255, 232, 100), top=True)
    v.rect(9, 13, 14, 14, c(255, 232, 100), top=True)
    for (x, y) in ((3, 9 + up), (20, 8 + up)):
        v.put(x, y, c(255, 190, 60), top=True)
    return v.image()


# ── 고장 차량: 갓길에 선 파란 차 · 보닛에서 김 · 비상등 깜빡 · 뒤에 삼각대 · 스패너 ──
def breakdown(phase):
    v = Cv()
    B, BL, BD = c(72, 138, 228), c(140, 188, 248), c(48, 98, 178)
    up = phase
    st, stl = c(206, 212, 224), c(232, 236, 244)
    # 보닛에서 뭉게뭉게 오르는 김 (둘째 프레임에 위로 퍼짐)
    puffs = ((18.5, 11, 1.6, 1.2), (20.5, 9.5, 1.9, 1.6), (18.5, 7.5, 1.4, 1.2)) if phase == 0 else \
            ((19, 10.5, 1.4, 1.0), (20.5, 7.5, 2.0, 1.6), (18, 5, 1.6, 1.3), (21.5, 4, 1.2, 1.1))
    for (cx, cy, rx, ry) in puffs:
        v.ellipse(cx, cy, rx, ry, st)
    for (cx, cy, rx, ry) in puffs:
        v.put(int(cx) - 1, int(cy) - 1, stl, top=True)
    v.rect(8, 13, 21, 18, B)
    v.rect(10, 9, 15, 12, B)
    v.rect(11, 10, 12, 12, GLASS, top=True); v.rect(14, 10, 15, 12, GLASS, top=True)
    v.rect(8, 13, 21, 13, BL, top=True)
    v.rect(8, 17, 21, 18, BD, top=True)
    # 고장 표시 스패너 (왼쪽 위)
    g, gl = c(176, 182, 194), c(220, 224, 232)
    head = [(x, y) for y in range(0, 6) for x in range(0, 6) if (x - 2.5) ** 2 + (y - 2.5) ** 2 <= 2.4 ** 2]
    for (x, y) in head:
        if (x, y) not in ((1, 1), (2, 2), (1, 2), (2, 1), (0, 1), (1, 0)):   # 입 벌린 머리
            v.put(x, y, g)
    for i in range(3):
        v.put(4 + i, 5 + i, g); v.put(5 + i, 5 + i, g)        # 손잡이
    v.put(3, 4, gl, top=True); v.put(5, 6, gl, top=True)
    wheel(v, 10, 19); wheel(v, 18, 19)
    on = phase == 0
    amber = c(255, 184, 30) if on else c(150, 112, 52)
    v.rect(8, 14, 8, 15, amber, top=True); v.rect(21, 14, 21, 15, amber, top=True)
    if on:
        for (x, y) in ((22, 13), (23, 14), (22, 16), (9, 12)):
            v.put(x, y, c(255, 210, 90), top=True)
    # 차 뒤 삼각대 (속이 빈 빨간 삼각형)
    v.tri(((3, 12), (-1, 20), (7, 20)), c(232, 40, 40))
    v.tri(((3, 15), (1, 19), (5, 19)), c(255, 255, 255), top=True)
    v.rect(2, 21, 4, 21, c(120, 126, 136))
    return v.image()


def art(v, rows, pal, ox=0, oy=0, top=False):
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in pal:
                v.put(ox + x, oy + y, pal[ch], top)


# ── 고라니: 갈색 몸 + 큰 귀, 뛰어오름(쭉 뻗음) ↔ 착지(모음) ──
DEER = [
    [  # 쭉 뻗어 공중
        "........................",
        "...................bb...",
        "...................bb...",
        "..................bbbb..",
        "..................bbbbbd",
        ".................bbbb...",
        "................bbb.....",
        "...w...bbbbbbbbbbb......",
        "...wbbbbbbbbbbbbbbb.....",
        "....bbbbbbbbbbbbbbb.....",
        "....bbbbbbbbbbbbbb......",
        ".....bblllllllbbb.......",
        "....bb.........bbb......",
        "...bb............bb.....",
        "..bb..............bb....",
        ".bb................bb...",
        ".d..................d...",
    ],
    [  # 다리를 배 밑으로 모음 (도약 준비)
        "........................",
        "...................bb...",
        "...................bb...",
        "..................bbbb..",
        "..................bbbbbd",
        ".................bbbb...",
        "................bbb.....",
        "...w...bbbbbbbbbbb......",
        "...wbbbbbbbbbbbbbbb.....",
        "....bbbbbbbbbbbbbbb.....",
        "....bbbbbbbbbbbbbb......",
        ".....bblllllllbbb.......",
        ".....bb......bb.b.......",
        "......bb....bb...b......",
        ".......bb..bb.....b.....",
        "........d.d......bb.....",
        ".................d......",
    ],
]


def animal(phase):
    v = Cv()
    pal = {"b": c(184, 128, 74), "l": c(236, 206, 160), "d": c(70, 50, 36), "w": c(250, 250, 250)}
    oy = 3 if phase == 0 else 5
    art(v, DEER[phase], pal, 0, oy)
    v.put(20, 4 + oy, K, top=True)
    v.put(19, 1 + oy, c(236, 160, 140), top=True)
    return v.image()


# ── 보행자: 횡단보도 위를 걷는 사람, 팔다리 번갈아 ──
def pedestrian(phase):
    v = Cv()
    # 운전석에서 본 횡단보도 (원근으로 벌어지는 흰 줄)
    for y in range(18, 23):
        t = (y - 18) / 4.0
        left, right = round(4 - 4 * t), round(19 + 4 * t)
        for x in range(left, right + 1):
            u = (x - left) / float(right - left + 1)
            white = int(u * 7) % 2 == 0
            v.put(x, y, c(246, 246, 242) if white else c(100, 104, 114))
    skin, hair, shirt, pants = c(252, 212, 172), c(70, 52, 40), c(60, 130, 230), c(52, 60, 96)
    v.ellipse(12, 4, 2.6, 2.6, skin)
    v.rect(10, 1, 13, 2, hair); v.put(10, 3, hair); v.put(9, 4, hair)
    v.put(13, 4, K, top=True)
    v.rect(10, 7, 13, 13, shirt)
    if phase == 0:
        line(v, 10, 8, 7, 12, shirt, 1); line(v, 13, 8, 16, 12, shirt, 1)
        v.put(7, 13, skin); v.put(16, 13, skin)
        line(v, 10, 14, 7, 19, pants, 2); line(v, 12, 14, 15, 19, pants, 2)
        v.rect(6, 19, 8, 19, K); v.rect(15, 19, 17, 19, K)
    else:
        line(v, 10, 8, 9, 12, shirt, 1); line(v, 13, 8, 14, 12, shirt, 1)
        v.put(9, 13, skin); v.put(14, 13, skin)
        line(v, 10, 14, 10, 19, pants, 2); line(v, 12, 14, 13, 17, pants, 2); v.put(12, 18, pants); v.put(12, 19, pants)
        v.rect(10, 19, 12, 19, K); v.rect(12, 19, 14, 19, K)
    return v.image()


# ── 침수: 출렁이는 물에 반쯤 잠긴 차 + 퍼지는 물결 ──
def flood(phase):
    v = Cv()
    car, carl = c(250, 190, 40), c(255, 224, 120)
    v.rect(3, 12, 18, 15, car)
    v.rect(6, 8, 15, 11, car)
    v.rect(7, 9, 9, 11, GLASS, top=True); v.rect(11, 9, 14, 11, GLASS, top=True)
    v.rect(6, 8, 15, 8, carl, top=True)
    deep, mid, light = c(48, 112, 196), c(76, 148, 230), c(176, 216, 252)
    for x in range(0, 24):
        top_y = 14 + (1 if (x + phase * 2) % 6 < 3 else 0)
        for y in range(top_y, 22):
            v.put(x, y, mid if y < 18 else deep)
    for x in range(0, 24):
        if (x + phase * 2) % 6 == 1:
            v.put(x, 14, light, top=True)
    for (x0, y) in ((2 - phase, 17), (16 + phase, 17), (8 + phase, 20)):
        v.rect(x0, y, x0 + 3, y, light, top=True)
    for (x, y) in ((1 + phase, 13), (20 - phase, 12)):
        v.put(x, y, light, top=True)
    return v.image()


# ── 안개: 흐린 차 앞모습 + 노란 전조등, 옅은 안개 띠가 흘러감 ──
def fog(phase):
    v = Cv()
    body = c(104, 116, 142)
    v.rect(4, 11, 19, 18, body)
    v.rect(6, 7, 17, 10, body)
    v.rect(7, 8, 16, 10, c(150, 168, 194), top=True)
    v.rect(4, 19, 6, 20, c(60, 64, 74)); v.rect(17, 19, 19, 20, c(60, 64, 74))
    v.rect(9, 15, 14, 16, c(70, 78, 98), top=True)
    lamp = c(255, 232, 110)
    v.rect(5, 13, 7, 14, lamp, top=True); v.rect(16, 13, 18, 14, lamp, top=True)
    im = v.image()
    # 반투명 안개 띠: 차 위에서는 비쳐 보이게 섞고, 빈 곳은 옅은 푸른 회색
    mist_c, mist_hl, edge = (206, 216, 232), (234, 240, 248), (150, 164, 190)
    s = 2 if phase else 0
    cells = {}
    for (x0, x1, y) in ((2 + s, 16 + s, 3), (7 - s, 23 - s, 9), (0 + s, 15 + s, 15), (9 - s, 23 - s, 20)):
        for x in range(x0, x1 + 1):
            wy = y + (1 if (x + s) % 8 >= 4 else 0)
            end = x in (x0, x1)
            cells[(x, wy)] = mist_hl
            if not end:
                cells[(x, wy + 1)] = mist_c
    px = im.load()
    for (x, y), col in cells.items():
        if not (0 <= x < 24 and 0 <= y < 24):
            continue
        r, g, b, a = px[x, y]
        if a == 0:
            px[x, y] = col + (255,)
        else:
            k = 0.62
            px[x, y] = (int(r * (1 - k) + col[0] * k), int(g * (1 - k) + col[1] * k), int(b * (1 - k) + col[2] * k), 255)
    for (x, y) in list(cells):
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            n = (x + dx, y + dy)
            if n not in cells and 0 <= n[0] < 24 and 0 <= n[1] < 24 and px[n][3] == 0:
                px[n] = edge + (255,)
    # 안개를 뚫고 나오는 전조등
    for (x, y) in ((6, 13), (17, 13)):
        px[x, y] = (255, 246, 180, 255)
    return im


# ── 정체: 범퍼 붙인 차 세 대 + 깜빡이는 브레이크등 ──
def jam(phase):
    v = Cv()
    cars = [(0, 2, c(72, 138, 228), c(140, 188, 248)),
            (7, 1, c(250, 190, 40), c(255, 226, 130)),
            (14, 0, c(220, 52, 52), c(244, 110, 104))]
    owned = []
    for i, (x0, oy, col, hl) in enumerate(cars):
        y0 = 12 - oy
        mine = set()
        for (ax, ay, bx, by) in ((x0, y0 + 4, x0 + 9, y0 + 8), (x0 + 2, y0 + 1, x0 + 7, y0 + 3), (x0 + 3, y0, x0 + 6, y0)):
            for yy in range(ay, by + 1):
                for xx in range(ax, bx + 1):
                    mine.add((xx, yy))
        # 앞차가 뒷차 코를 가리는 자리에 외곽선
        for (xx, yy) in mine:
            for dx, dy in ((-1, 0), (0, -1), (0, 1)):
                n = (xx + dx, yy + dy)
                if n in v.px and n not in mine:
                    v.put(n[0], n[1], OUT)
        for (xx, yy) in mine:
            v.put(xx, yy, col)
        v.rect(x0, y0 + 4, x0 + 9, y0 + 4, hl, top=True)
        v.rect(x0 + 3, y0 + 1, x0 + 4, y0 + 3, GLASS, top=True); v.rect(x0 + 6, y0 + 1, x0 + 7, y0 + 3, GLASS, top=True)
        v.put(x0 + 3, y0 + 9, c(36, 36, 40)); v.put(x0 + 4, y0 + 9, c(36, 36, 40))
        v.put(x0 + 8, y0 + 9, c(36, 36, 40)); v.put(x0 + 9, y0 + 9, c(36, 36, 40))
        on = phase == 0
        v.rect(x0, y0 + 5, x0, y0 + 6, c(255, 30, 30) if on else c(130, 30, 34), top=True)
        if on and i > 0:
            v.put(x0 - 1, y0 + 5, c(255, 120, 100), top=True)
    if phase == 0:
        v.put(0, 13, c(255, 120, 100), top=True)
    return v.image()


# ── 신호등 고장: 꺼진 신호등 + 노란불 깜빡 + 튀는 불꽃 ──
def signal(phase):
    v = Cv()
    v.rect(11, 18, 12, 23, c(150, 156, 166)); v.rect(9, 22, 14, 23, c(120, 126, 136))
    v.rect(8, 1, 15, 17, c(70, 74, 86))
    v.rect(8, 1, 8, 17, c(100, 104, 118))
    v.ellipse(11.5, 4, 2.2, 2.2, c(110, 44, 44), top=True)
    amber = c(255, 190, 30) if phase == 0 else c(120, 100, 44)
    v.ellipse(11.5, 9, 2.2, 2.2, amber, top=True)
    v.ellipse(11.5, 14, 2.2, 2.2, c(40, 90, 64), top=True)
    if phase == 0:
        v.put(11, 8, c(255, 240, 170), top=True)
        for (x, y) in ((5, 9), (6, 7), (6, 11), (18, 9), (17, 7), (17, 11)):
            v.put(x, y, c(255, 210, 90), top=True)
    # 옆구리에서 튀는 불꽃 (번개 모양 → 별 모양)
    sp, sw = c(255, 222, 50), c(255, 255, 230)
    if phase == 0:
        for p in ((17, 3), (18, 2), (19, 3), (20, 2), (21, 1), (19, 4), (20, 5)):
            v.put(*p, sp, top=True)
        v.put(19, 3, sw, top=True)
    else:
        cx, cy = 20, 4
        for (dx, dy) in ((0, -2), (0, 2), (-2, 0), (2, 0), (-1, -1), (1, 1), (1, -1), (-1, 1)):
            v.put(cx + dx, cy + dy, sp, top=True)
        v.put(cx, cy, sw, top=True)
        v.put(17, 1, sp, top=True); v.put(22, 8, sp, top=True)
    line(v, 10, 3, 13, 5, K, top=True)                        # 깨진 빨간 렌즈
    v.put(16, 5, K, top=True); v.put(17, 5, K, top=True)      # 끊긴 전선
    return v.image()


# ── 낙석: 비탈에서 굴러떨어지는 바위 + 길 위 잔돌 ──
def rockfall(phase):
    v = Cv()
    v.tri(((0, 1), (0, 23), (13, 23)), c(156, 120, 86))
    for (x, y) in ((1, 6), (2, 10), (4, 15), (6, 19), (1, 14), (3, 20)):
        v.put(x, y, c(120, 90, 64), top=True)
    rock, rl = c(146, 146, 154), c(194, 194, 202)
    pos = ((10, 7, 2.6), (16, 14, 2.2)) if phase == 0 else ((12, 10, 2.6), (18, 17, 2.2))
    for (cx, cy, r) in pos:
        v.ellipse(cx, cy, r, r * 0.9, rock)
        v.put(cx - 1, cy - 1, rl, top=True)
    for (x0, x1, y) in ((13, 15, 22), (17, 18, 22), (20, 22, 22), (19, 20, 21)):
        v.rect(x0, y, x1, y, rock)
    for (x, y) in (((8, 4), (13, 11)) if phase == 0 else ((10, 7), (15, 14))):
        v.put(x, y, c(120, 120, 128), top=True)
    return v.image()


# ── 역주행: 정면으로 다가오는 차 + 빨간 X 경고 깜빡 ──
def wrong_way(phase):
    v = Cv()
    body = c(140, 90, 210)
    v.rect(3, 12, 20, 19, body)
    v.rect(6, 8, 17, 11, body)
    v.rect(7, 9, 16, 11, GLASS, top=True)
    v.rect(3, 12, 20, 12, c(180, 140, 236), top=True)
    v.rect(9, 16, 14, 17, c(60, 60, 70), top=True)
    v.rect(3, 20, 5, 21, c(36, 36, 40)); v.rect(18, 20, 20, 21, c(36, 36, 40))
    lamp = c(255, 250, 200) if phase == 0 else c(255, 210, 80)
    v.rect(4, 14, 6, 15, lamp, top=True); v.rect(17, 14, 19, 15, lamp, top=True)
    if phase == 0:                                            # 상향등 번쩍 (마주 오는 느낌)
        for (x, y) in ((1, 13), (1, 16), (0, 14), (22, 13), (22, 16), (23, 15)):
            v.put(x, y, c(255, 230, 110), top=True)
    if phase == 0:
        R = c(232, 36, 36)
        for d in range(5):
            v.put(15 + d, 1 + d, R); v.put(16 + d, 1 + d, R)
            v.put(19 - d, 1 + d, R); v.put(20 - d, 1 + d, R)
    else:
        R = c(232, 36, 36)
        for d in range(5):
            v.put(2 + d, 1 + d, R); v.put(3 + d, 1 + d, R)
            v.put(6 - d, 1 + d, R); v.put(7 - d, 1 + d, R)
    return v.image()


# ── 도로 통제: 빨강·흰 막이 + 진입금지 표지 + 번쩍이는 빨간 등 ──
def road_closed(phase):
    v = Cv()
    v.rect(11, 10, 12, 13, c(170, 176, 186))
    v.ellipse(11.5, 5.5, 5.4, 5.4, c(226, 36, 36))
    v.rect(8, 5, 15, 6, c(255, 255, 255), top=True)
    v.rect(3, 18, 4, 22, c(200, 200, 206)); v.rect(19, 18, 20, 22, c(200, 200, 206))
    v.rect(1, 14, 22, 17, c(250, 250, 250))
    for x in range(1, 23):
        if (x // 3) % 2 == 0:
            for y in range(14, 18):
                v.put(x, y, c(226, 40, 40))
    lit, dim = c(255, 60, 50), c(140, 50, 50)
    v.rect(1, 12, 2, 13, lit if phase == 0 else dim)
    v.rect(21, 12, 22, 13, dim if phase == 0 else lit)
    gx = 1 if phase == 0 else 22
    for (dx, dy) in ((-1, -2), (1, -2), (0, -3)):
        x = gx + dx
        v.put(x, 12 + dy, c(255, 140, 120), top=True)
    return v.image()


# ── 우박: 먹구름 + 얼음 알갱이가 차 지붕에 튀김 ──
def hail(phase):
    v = Cv()
    cl, cd, ch = c(140, 148, 168), c(112, 120, 140), c(176, 184, 200)
    for (cx, cy, r) in ((7, 4.5, 3.2), (12, 3, 3.8), (17, 4.5, 3.2)):
        v.ellipse(cx, cy, r, r * 0.85, cl)
    v.rect(4, 4, 20, 6, cl)
    v.rect(4, 6, 20, 6, cd)
    v.rect(10, 0, 13, 0, ch, top=True)
    car = c(72, 138, 228)
    v.rect(2, 17, 21, 20, car)
    v.rect(6, 14, 16, 16, car)
    v.rect(7, 15, 9, 16, GLASS, top=True); v.rect(11, 15, 15, 16, GLASS, top=True)
    v.rect(2, 17, 21, 17, c(140, 188, 248), top=True)
    wheel(v, 6, 21, 1.8); wheel(v, 17, 21, 1.8)
    ice, il = c(226, 240, 252), c(255, 255, 255)
    balls = ((4, 9), (10, 10), (17, 9), (21, 13)) if phase == 0 else ((5, 11), (13, 9), (18, 11), (2, 13))
    for (x, y) in balls:
        v.rect(x, y, x + 1, y + 1, ice)
        v.put(x, y, il, top=True)
    # 지붕에 맞고 튀는 표시
    hit = ((11, 12), (13, 12), (10, 11)) if phase == 1 else ((19, 15), (21, 15))
    for (x, y) in hit:
        v.put(x, y, c(120, 180, 240), top=True)
    return v.image()


# ── 폭설: 눈 쌓인 차 + 길 위 눈더미 + 펑펑 내리는 눈 ──
def snow(phase):
    v = Cv()
    car = c(220, 52, 52)
    v.rect(3, 14, 20, 19, car)
    v.rect(6, 10, 16, 13, car)
    v.rect(7, 11, 9, 13, GLASS, top=True); v.rect(11, 11, 15, 13, GLASS, top=True)
    S = c(250, 252, 255)
    v.ellipse(11, 9.5, 6.5, 1.8, S)
    v.rect(16, 13, 21, 13, S); v.put(3, 13, S); v.put(4, 13, S)
    v.ellipse(11.5, 21.5, 12, 2.6, S)
    wheel(v, 7, 20); wheel(v, 16, 20)
    v.ellipse(11.5, 22, 12, 1.8, S)
    big = ((4, 2), (13, 1), (20, 5), (9, 5)) if phase == 0 else ((5, 4), (14, 3), (20, 8), (9, 1))
    arm, mid = c(150, 196, 246), c(96, 150, 224)
    for (x, y) in big:                                        # 펑펑 내리는 눈송이 (+ 모양)
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            v.put(x + dx, y + dy, arm, top=True)
        v.put(x, y, mid, top=True)
    small = ((17, 1), (1, 7), (22, 10), (1, 1)) if phase == 0 else ((17, 3), (2, 9), (22, 1), (11, 0))
    for (x, y) in small:
        v.put(x, y, mid, top=True)
    return v.image()


# ── 강풍: 휘어진 나무 + 바람자루 + 휘몰아치는 바람결 ──
def wind(phase):
    v = Cv()
    v.rect(2, 3, 2, 22, c(170, 176, 186)); v.rect(1, 22, 3, 23, c(120, 126, 136))
    sock = c(244, 110, 30)
    if phase == 0:
        for i, x in enumerate(range(3, 13)):
            h = 2 - i // 4
            v.rect(x, 3 + i // 5, x, 3 + i // 5 + h + 1, sock if (x // 3) % 2 == 1 else c(250, 250, 250))
    else:
        for i, x in enumerate(range(3, 12)):
            h = 2 - i // 4
            v.rect(x, 3 + i // 3, x, 3 + i // 3 + h + 1, sock if (x // 3) % 2 == 1 else c(250, 250, 250))
    gust = c(120, 170, 220)
    s = phase * 2
    for (x0, y, ln) in ((6 + s, 10, 9), (9 - s, 13, 10), (5 + s, 17, 7)):
        v.rect(x0, y, x0 + ln, y, gust, top=True)
        v.put(x0 + ln + 1, y - 1, gust, top=True)
    trunk = c(140, 96, 60)
    bend = 1 - phase
    line(v, 17, 23, 17 + bend, 18, trunk, 2)
    line(v, 17 + bend, 18, 18 + bend * 2, 16, trunk, 2)
    v.ellipse(18.5 + bend * 1.5, 12.5, 3.4, 4.0, c(80, 170, 80))
    v.put(17 + bend, 10, c(140, 210, 120), top=True); v.put(18 + bend, 10, c(140, 210, 120), top=True)
    v.put(22, 6 + phase * 3, c(90, 180, 80)); v.put(14 + phase * 4, 20 - phase, c(90, 180, 80))
    return v.image()


# ── 해일: 말려 오는 큰 파도가 해안 방파제 위로 ──
def tsunami(phase):
    v = Cv()
    deep, mid, light, foam = c(40, 104, 196), c(70, 148, 230), c(150, 204, 250), c(252, 253, 255)
    cx, cy = 11 + phase, 11
    for y in range(24):
        for x in range(24):
            if ((x - cx) / 9.0) ** 2 + ((y - cy) / 9.0) ** 2 <= 1 and y >= 2:
                inner = ((x - (cx + 3)) / 4.2) ** 2 + ((y - (cy + 2)) / 4.0) ** 2 <= 1
                if inner or (x > cx + 2 and y > cy + 1):
                    continue
                v.put(x, y, mid if (x - cx) + (y - cy) < 2 else deep)
    v.rect(0, 19, 23, 21, deep)
    v.rect(17, 17, 23, 21, c(170, 174, 184))
    v.rect(17, 17, 23, 17, c(200, 204, 212), top=True)
    for x in range(17, 24):
        if x % 3 == 0:
            v.put(x, 19, c(130, 134, 144), top=True)
    for (x, y) in ((cx - 3, 3), (cx - 1, 2), (cx + 1, 2), (cx + 3, 3), (cx + 5, 4), (cx + 6, 6), (cx + 7, 8)):
        v.put(x, y, foam, top=True)
    for (x, y) in ((cx + 8, 9 + phase), (cx + 9, 11), (cx + 7, 12 - phase)):
        v.put(x, y, light, top=True)
    for x in range(0, 17):
        if (x + phase * 2) % 5 == 0:
            v.put(x, 19, light, top=True)
    return v.image()


# ── 산불: 언덕 위 불붙은 소나무 + 크게 피어오르는 연기 ──
def wildfire(phase):
    v = Cv()
    sm1, sm2 = c(140, 142, 152), c(176, 178, 188)
    up = phase
    for (cx, cy, r, col) in ((12, 6 - up, 3.0, sm1), (16, 3 - up, 3.2, sm2), (20, 5 - up, 2.6, sm1), (8, 8 - up, 2.2, sm2)):
        v.ellipse(cx, cy, r, r * 0.9, col)
    v.ellipse(11.5, 23, 13, 6, c(120, 160, 72))
    pine, pd = c(48, 120, 72), c(32, 90, 56)
    for (x, base) in ((5, 21), (12, 18), (19, 21)):
        v.tri(((x, base - 9), (x - 3, base - 1), (x + 3, base - 1)), pine)
        v.rect(x, base - 1, x, base, c(120, 80, 50))
    fl = [(5, 12), (12, 9), (19, 12)]
    for i, (x, y) in enumerate(fl):
        h = 3 if (i + phase) % 2 == 0 else 2
        v.tri(((x - 2, y + 3), (x, y - h), (x + 2, y + 3)), c(240, 80, 30))
        v.put(x, y + 1, c(255, 200, 50), top=True); v.put(x, y + 2, c(255, 200, 50), top=True)
    return v.image()


# ── 눈사태: 산비탈을 쏟아져 내려 길을 덮는 눈덩이 ──
def avalanche(phase):
    v = Cv()
    rockc, rockd = c(104, 116, 146), c(82, 92, 120)
    v.tri(((7, 1), (-7, 21), (21, 21)), rockc)
    for (x, y) in ((3, 12), (1, 16), (6, 17), (4, 19)):
        v.put(x, y, rockd, top=True)
    S, Ss = c(248, 251, 255), c(206, 222, 244)
    v.tri(((7, 1), (4, 6), (10, 6)), S)
    for (x, y) in ((5, 6), (7, 7), (9, 6)):
        v.put(x, y, S)
    # 비탈을 타고 쏟아지는 눈 띠
    for y in range(4, 22):
        ex = 7 + (y - 1) * 14 / 20.0
        wob = (1 if (y + phase) % 3 == 0 else 0)
        for x in range(int(ex - 4 - wob), int(ex + 2 + wob)):
            v.put(x, y, S)
        v.put(int(ex - 4 - wob), y, Ss, top=True)
    v.ellipse(15, 21, 8.5, 2.6, S)                           # 길을 덮은 눈더미
    chunks = ((14, 7, 1.6), (19, 13, 1.8), (22, 18, 1.3)) if phase == 0 else ((15, 9, 1.6), (21, 15, 1.8), (13, 4, 1.2))
    for (x, y, r) in chunks:
        v.ellipse(x, y, r, r * 0.9, S)
        v.put(x, y + 1, Ss, top=True)
    v.rect(0, 22, 23, 23, c(100, 104, 114))
    v.rect(1, 22, 4, 22, c(240, 240, 236), top=True)
    v.ellipse(15, 21.6, 8.5, 1.6, S)
    return v.image()


# ── 레이싱 결승 깃발: 은색 깃대 + 펄럭이는 체크 깃발 4프레임 ──
def race_flag(phase):
    v = Cv(32, 32)
    v.rect(2, 2, 3, 31, c(206, 210, 218))
    v.rect(3, 2, 3, 31, c(150, 156, 166))
    v.ellipse(2.5, 1.5, 1.6, 1.4, c(250, 200, 50))
    v.put(2, 1, c(255, 240, 160), top=True)
    for x in range(4, 30):
        t = (x - 4) / 25.0
        off = int(round(math.sin(phase * math.pi / 2 + t * 5.2) * 2.2 * t + t * 1.5))
        slope = math.cos(phase * math.pi / 2 + t * 5.2)
        for y in range(0, 16):
            yy = 3 + y + off
            sq = ((x - 4) // 4 + y // 4) % 2
            base = (34, 34, 40) if sq else (246, 246, 246)
            if slope < -0.35:
                base = tuple(int(ch * 0.78) for ch in base)
            elif slope > 0.6 and not sq:
                base = (255, 255, 255)
            v.put(x, yy, c(*base))
    return v.image()


# ── 코인: 빙글 도는 금화 4프레임 ──
def coin(phase):
    v = Cv(16, 16)
    rx = [6.5, 4.5, 1.6, 4.5][phase]
    v.ellipse(7.5, 7.5, rx, 6.5, c(240, 180, 30))
    if rx > 2:
        v.ellipse(7.5, 7.5, max(1, rx - 2), 4.5, c(252, 214, 70), top=True)
        v.rect(7, 5, 8, 10, c(220, 150, 20), top=True)
        v.put(int(7.5 - rx / 2), 4, c(255, 250, 210), top=True)
    else:
        v.rect(7, 2, 8, 13, c(200, 136, 20), top=True)
    return v.image()


ART = {
    "camera": [camera(False), camera(True)],
    "rain": [rain(0), rain(1)],
    "pothole": [pothole(0), pothole(1)],
    "accident": [accident(0), accident(1)],
    "hard_brake": [hardbrake(0), hardbrake(1)],
    "debris": [debris(0), debris(1)],
    "construction": [construction(0), construction(1)],
    "ice": [ice(0), ice(1)],
    "bump": [bump(0), bump(0)],
    "school": [school(0), school(1)],
    # ── 2차 추가 18종 ──
    "emergency": [emergency(0), emergency(1)],
    "fire": [fire(0), fire(1)],
    "breakdown": [breakdown(0), breakdown(1)],
    "animal": [animal(0), animal(1)],
    "pedestrian": [pedestrian(0), pedestrian(1)],
    "flood": [flood(0), flood(1)],
    "fog": [fog(0), fog(1)],
    "jam": [jam(0), jam(1)],
    "signal": [signal(0), signal(1)],
    "rockfall": [rockfall(0), rockfall(1)],
    "wrong_way": [wrong_way(0), wrong_way(1)],
    "road_closed": [road_closed(0), road_closed(1)],
    "hail": [hail(0), hail(1)],
    "snow": [snow(0), snow(1)],
    "wind": [wind(0), wind(1)],
    "tsunami": [tsunami(0), tsunami(1)],
    "wildfire": [wildfire(0), wildfire(1)],
    "avalanche": [avalanche(0), avalanche(1)],
}

NEW = ["emergency", "fire", "breakdown", "animal", "pedestrian", "flood", "fog", "jam", "signal",
       "rockfall", "wrong_way", "road_closed", "hail", "snow", "wind", "tsunami", "wildfire", "avalanche"]
NEW_KO = {
    "emergency": "긴급차량", "fire": "차량 화재", "breakdown": "고장 차량", "animal": "야생동물(고라니)",
    "pedestrian": "보행자", "flood": "침수", "fog": "안개", "jam": "정체", "signal": "신호등 고장",
    "rockfall": "낙석", "wrong_way": "역주행", "road_closed": "도로 통제", "hail": "우박", "snow": "폭설",
    "wind": "강풍", "tsunami": "해일·쓰나미", "wildfire": "산불", "avalanche": "눈사태",
}


def new_preview(path, S=8, cols=6):
    """새로 넣은 위험 표시만: 8배 확대, 흰 바탕, 두 프레임 나란히 + 이름."""
    from PIL import ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("malgunbd.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    cell_w, cell_h = (24 * 2 + 4 + 10) * S, (24 + 12) * S
    rows = (len(NEW) + cols - 1) // cols
    pv = Image.new("RGBA", (cols * cell_w, rows * cell_h), (255, 255, 255, 255))
    d = ImageDraw.Draw(pv)
    for i, name in enumerate(NEW):
        x0 = (i % cols) * cell_w + 5 * S
        y0 = (i // cols) * cell_h + 8 * S
        for j, f in enumerate(ART[name]):
            pv.alpha_composite(f.resize((24 * S, 24 * S), Image.NEAREST), (x0 + j * 28 * S, y0))
        d.text((x0, y0 - 6 * S), f"{NEW_KO[name]}  haz_{name}", fill=(40, 40, 46, 255), font=font)
    pv.convert("RGB").save(path)


def main():
    out, preview = sys.argv[1], sys.argv[2]
    for name, frames in ART.items():
        sheet(frames).save(f"{out}/haz_{name}.png")
    flag = [race_flag(i) for i in range(4)]
    sheet(flag).save(f"{out}/flag_race.png")
    coins = [coin(i) for i in range(4)]
    sheet(coins).save(f"{out}/coin_spin.png")
    # 미리보기: 8배 확대, 흰 바탕 — 첫 줄은 기존 10종 + 깃발 + 코인, 아래 줄부터 새 18종 (한 줄 12칸)
    S = 8
    old = [ART[n] for n in ART if n not in NEW]
    new = [ART[n] for n in NEW]
    cols = len(old) + 2
    bands = 1 + (len(new) + cols - 1) // cols
    pv = Image.new("RGBA", (cols * 34 * S, bands * 2 * 34 * S), (255, 255, 255, 255))

    def tile(frames, col, band):
        for j, f in enumerate(frames):
            big = f.resize((24 * S, 24 * S), Image.NEAREST)
            pv.alpha_composite(big, (col * 34 * S + 5 * S, (band * 2 + j) * 34 * S + 5 * S))

    for i, frames in enumerate(old):
        tile(frames, i, 0)
    for j, f in enumerate(flag[:2]):
        pv.alpha_composite(f.resize((32 * S, 32 * S), Image.NEAREST), (len(old) * 34 * S, j * 34 * S))
    for j, f in enumerate(coins[:2]):
        pv.alpha_composite(f.resize((16 * S, 16 * S), Image.NEAREST), ((len(old) + 1) * 34 * S + 8 * S, j * 34 * S + 8 * S))
    for i, frames in enumerate(new):
        tile(frames, i % cols, 1 + i // cols)
    pv.convert("RGB").resize((pv.width // 2, pv.height // 2), Image.NEAREST).save(preview)
    if len(sys.argv) > 3:
        new_preview(sys.argv[3])
    print("ok", len(ART))


if __name__ == "__main__":
    main()
