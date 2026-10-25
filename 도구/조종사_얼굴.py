"""
Pixel TMI 기계 캐릭터 조종사 얼굴 — 위험 컷인 띠에 '조종사가 튀어나오는' 클로즈업.
결: 탈것 도트(탈것_도트만들기.py)·고양이 오마주와 같은 진회색 자동 외곽선(1칸), 밝은 색 몇 개, 꼬마 비율(머리 크게).
    3/4 정면(살짝 오른쪽을 봄), 머리 + 어깨 조금. 한 칸 = 가로 32 × 세로 24, 투명 바탕.
    고글·바이저 칸은 머리가 움직이지 않게 두 프레임 모두 같은 자리 → 앱이 그 네모 위로 빛을 쓱 훑는다.
사용: python 조종사_얼굴.py [출력 폴더] [미리보기.png]
    (인자 없으면 이 파일 기준 ../app/src/main/assets/pet 과 ../../스크린샷/81_조종사_시안.png)
출력: pilot_car.png · pilot_plane.png · pilot_heli.png · pilot_ufo.png (각 64×24 = 2프레임: 0 결의 · 1 외침)
      pilots.json — {"car": {"x","y","w","h"}, ...} 고글(바이저) 네모, 얼굴 도트 좌표
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw

W, H = 32, 24
LINE = (60, 62, 70, 255)
CLEAR = (0, 0, 0, 0)
WHITE = (246, 246, 246, 255)
GLINT = (240, 250, 255, 255)
GLASS = (150, 210, 250, 255)
GLASS_DK = (100, 168, 228, 255)
GLASS_MID = (124, 190, 242, 255)
EYE = (28, 28, 36, 255)
STEEL = (90, 92, 104, 255)
HUB = (170, 174, 182, 255)
YEL = (248, 200, 40, 255)
YEL_DK = (214, 150, 30, 255)

SKIN = (255, 216, 180, 255)
SKIN_SH = (238, 182, 146, 255)
BLUSH = (250, 150, 156, 255)
MOUTH = (126, 44, 56, 255)
TONGUE = (240, 112, 126, 255)
TEETH = (252, 252, 252, 255)
LIP = (150, 76, 70, 255)


def rnd(v):
    return int(math.floor(v + 0.5))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + (c[3] if len(c) > 3 else 255,)


class Cv:
    """도트 캔버스. px=몸(자동 외곽선) · dt=무늬(몸 위 덧칠, 외곽선 없음) · fx=효과(몸 뒤) · gl=빛 번짐(맨 위, 반투명)"""

    def __init__(self):
        self.px, self.dt, self.fx, self.gl = {}, {}, {}, {}

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

    def art(self, x0, y0, rows, pal, to="dt"):
        """글자 그림: pal 의 글자 → 색, 그 밖의 글자는 비움"""
        L = self._L(to)
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch in pal:
                    L[(x0 + dx, y0 + dy)] = pal[ch]

    def overlay(self, o, line=LINE):
        """o 를 몸 위에 얹고, 맞닿은 몸 쪽에 진회색 경계선을 긋는다 (얼굴이 어깨에 묻히지 않게)"""
        region = set(o.px)
        for p in region:
            self.dt.pop(p, None)
        self.px.update(o.px)
        self.dt.update(o.dt)
        self.fx.update(o.fx)
        self.gl.update(o.gl)
        for (x, y) in region:
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n not in region and n in self.px:
                    self.dt[n] = line

    def image(self):
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

        for (x, y), c in self.fx.items():
            blend(x, y, c)
        for (x, y) in self.px:
            for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + ddx, y + ddy)
                if n not in self.px and 0 <= n[0] < W and 0 <= n[1] < H:
                    im.putpixel(n, LINE)
        for (x, y), c in self.px.items():
            blend(x, y, c)
        for (x, y), c in self.dt.items():
            blend(x, y, c)
        for (x, y), c in self.gl.items():
            blend(x, y, c)
        return im


def gloss(cv, region_color, hi, dk, hx0=-99, hx1=99, light=(-1, -1)):
    """region_color 덩어리에 윗면 광택(hi)·아랫면/오른쪽 그늘(dk)"""
    own = {p for p, c in cv.px.items() if c == region_color}
    for (x, y) in own:
        if (x, y) in cv.dt:
            continue
        if (x, y - 1) not in own and hx0 <= x <= hx1:
            cv.dt[(x, y)] = hi
        elif (x, y + 1) not in own or (x + 1, y) not in own:
            cv.dt[(x, y)] = dk


def shoulders(cv, c, rows=None):
    """어깨 (아래로 잘린 흉상). 3/4 시점이라 가까운 왼쪽 어깨가 조금 크다"""
    cv.spans(rows or {19: (8, 23), 20: (6, 25), 21: (4, 26), 22: (3, 27), 23: (3, 27)}, c)


# ═══════════════════════════════════════════════════════════════════════
# 1) 변신 로봇 — 80년대 '자동차로 변신하는 로봇' 오마주 (실제 작품의 얼굴·로고·문장은 쓰지 않은 창작)
#    빨간 스포츠카 짝꿍: 빨강·은색 각진 투구 + 뒤로 젖힌 작은 안테나 날개 + 이마 은색 볏·노란 보석
#    + 눈을 가로지르는 파랗게 빛나는 바이저 띠(= 고글 칸) + 가로 숨구멍이 난 은색 마스크
#    가슴엔 스포츠카 앞유리, 어깨엔 노란 헤드라이트. 0 = 결의(V자 눈썹, 가늘게 빛나는 눈)
#    1 = 경보(바이저가 하얗게 번쩍 + 빛 번짐, 마스크 아래턱이 한 칸 열리며 속이 파랗게)
# ═══════════════════════════════════════════════════════════════════════
RED = (228, 48, 44, 255)
RED_HI = (255, 124, 104, 255)
RED_DK = (166, 30, 36, 255)
SIL = (204, 210, 222, 255)
SIL_HI = (242, 246, 252, 255)
SIL_DK = (146, 154, 172, 255)
VENT = (66, 70, 86, 255)
VB = (70, 178, 255, 255)              # 빛나는 바이저
VB_DK = (34, 100, 204, 255)
VB_CORE = (178, 236, 255, 255)
VB_WHITE = (244, 252, 255, 255)
VB_HALO = (110, 200, 255, 110)        # 바이저 빛 번짐 (반투명)
INSIDE = (30, 32, 46, 255)
NECKC = (78, 82, 96, 255)

CAR_GOGGLE = {"x": 13, "y": 8, "w": 14, "h": 3}


def robot(frame):
    alert = frame == 1
    jaw = 1 if alert else 0                       # 경보 땐 아래턱이 한 칸 내려감
    cv = Cv()
    # 어깨: 빨간 장갑 + 은색 목깃 + 스포츠카 앞유리 + 노란 헤드라이트
    shoulders(cv, RED)
    for (x, y) in list(cv.px):
        if (x, y - 1) not in cv.px:
            cv.dt[(x, y)] = RED_HI
    for y in range(21, 24):                       # 어깨 장갑 이음매
        cv.dt[(9, y)] = RED_DK; cv.dt[(22, y)] = RED_DK
    cv.rect(3, 23, 27, 23, RED_DK, to="dt")
    for p in ((5, 21), (6, 21), (25, 21), (26, 21)):
        cv.dt[p] = YEL
    cv.dt[(5, 22)] = YEL_DK; cv.dt[(26, 22)] = YEL_DK
    ws = Cv()                                     # 앞유리 (사다리꼴)
    ws.spans({21: (13, 18), 22: (12, 19), 23: (12, 19)}, GLASS)
    ws.dt[(13, 21)] = GLINT; ws.dt[(14, 21)] = GLINT; ws.dt[(12, 22)] = GLINT
    for p in ((17, 22), (18, 22), (19, 22), (16, 23), (17, 23), (18, 23), (19, 23)):
        ws.dt[p] = GLASS_DK
    cv.overlay(ws)
    ck = Cv()                                     # 은색 목깃 + 목
    ck.spans({19: (10, 21), 20: (9, 22)}, SIL)
    for x in range(10, 22):
        ck.dt[(x, 19)] = SIL_HI
    ck.dt[(9, 20)] = SIL_DK; ck.dt[(22, 20)] = SIL_DK
    ck.spans({17: (12, 17), 18: (12, 17)}, NECKC)
    ck.dt[(13, 17)] = SIL_DK; ck.dt[(13, 18)] = SIL_DK; ck.dt[(16, 18)] = SIL_DK   # 목 피스톤
    cv.overlay(ck)
    # 투구 (빨강, 각지게)
    hm = Cv()
    hm.spans({2: (11, 20), 3: (9, 22), 4: (8, 23), 5: (7, 24), 6: (7, 24), 7: (7, 25),
              8: (7, 12), 9: (7, 12), 10: (7, 12),
              11: (7, 15), 12: (7, 15), 13: (8, 15), 14: (8, 15), 15: (9, 15), 16: (10, 15)}, RED)
    gloss(hm, RED, RED_HI, RED_DK, hx0=7, hx1=21)
    for p in ((10, 3), (9, 4), (8, 5), (11, 3)):
        hm.dt[p] = RED_HI
    hm.dt[(10, 4)] = GLINT; hm.dt[(9, 5)] = GLINT
    for y in range(11, 16):                       # 볼 가리개 이음매
        hm.dt[(12, y)] = RED_DK
    hm.dt[(13, 16)] = RED_DK; hm.dt[(14, 16)] = RED_DK
    # 눈썹 턱 (바이저 위 처마): 0 = 가운데로 내려온 V
    for x in range(13, 26):
        hm.dt[(x, 7)] = RED_DK
    # 귀 원반 (은색 테 + 파란 불)
    hm.ellipse(9.6, 9.6, 2.2, 2.2, SIL, to="dt")
    hm.dt[(9, 9)] = VB; hm.dt[(10, 9)] = VB; hm.dt[(9, 10)] = VB_DK; hm.dt[(10, 10)] = VB if alert else VB_DK
    hm.dt[(8, 8)] = SIL_HI
    # 이마 은색 판 + 노란 보석
    hm.art(18, 4, ["..TT..",
                   ".SSSS.",
                   "SSgYSD"], {"S": SIL, "T": SIL_HI, "D": SIL_DK, "Y": YEL, "g": (255, 244, 170, 255)})
    hm.dt[(20, 5)] = YEL_DK; hm.dt[(21, 5)] = YEL_DK
    cv.overlay(hm)
    # 뒤로 젖힌 작은 안테나 날개 (가까운 쪽은 귀 위, 먼 쪽은 머리 뒤로 살짝)
    fin = Cv()
    fin.art(4, 2, ["S...",
                   "TS..",
                   ".TS.",
                   ".TSS",
                   "..SD"], {"S": SIL, "T": SIL_HI, "D": SIL_DK}, to="px")
    fin.art(22, 1, ["SS.",
                    "TSS",
                    ".TS",
                    "..D"], {"S": SIL, "T": SIL_HI, "D": SIL_DK}, to="px")
    cv.overlay(fin)
    # 은색 마스크 (입 가리개): 위판 + 아래턱, 가로 숨구멍
    up = Cv()
    up.spans({11: (16, 24), 12: (16, 24), 13: (16, 24), 14: (16, 24)}, SIL)
    for x in range(16, 25):
        up.dt[(x, 11)] = SIL_HI
    up.dt[(24, 12)] = SIL_DK; up.dt[(24, 13)] = SIL_DK; up.dt[(24, 14)] = SIL_DK
    for x in range(18, 24):
        up.dt[(x, 13)] = VENT
    up.dt[(17, 12)] = SIL_HI
    cv.overlay(up)
    lo = Cv()
    j0 = 15 + jaw
    lo.spans({j0: (16, 24), j0 + 1: (16, 23), j0 + 2: (17, 22), j0 + 3: (18, 21)}, SIL)
    for x in range(19, 23):
        lo.dt[(x, j0 + 1)] = VENT
    for (x, y) in list(lo.px):
        if (x, y + 1) not in lo.px or (x + 1, y) not in lo.px:
            lo.dt[(x, y)] = SIL_DK
    cv.overlay(lo)
    if alert:                                     # 벌어진 틈: 어두운 속 + 파란 불빛
        gap = Cv()
        gap.spans({15: (17, 23)}, INSIDE)
        for x in range(18, 23):
            gap.dt[(x, 15)] = VB if x not in (18, 22) else VB_DK
        cv.overlay(gap)
    # 바이저 띠 (앞으로 한 칸 튀어나옴)
    vs = Cv()
    vs.spans({8: (13, 26), 9: (13, 26), 10: (13, 26)}, VB)
    for x in range(13, 27):
        vs.dt[(x, 8)] = VB_DK
    if alert:   # 번쩍: 동그랗게 커진 하얀 눈 + 띠는 진한 파랑 그대로
        vs.art(13, 8, ["..cc....cc....",
                       ".cwwc..cwwc...",
                       "..cc....cc...."], {"c": VB_CORE, "w": VB_WHITE})
        vs.dt[(26, 9)] = VB_CORE
    else:       # 결의: 안쪽 끝이 내려간 가는 눈
        vs.art(13, 8, ["..............",
                       ".wcc.....cw...",
                       "...cc...cc...."], {"c": VB_CORE, "w": VB_WHITE})
    cv.overlay(vs)
    if not alert:   # V자 눈썹: 처마가 눈 안쪽 위를 V로 덮음 (바깥 끝만 윗줄이 보임)
        for x in range(16, 22):
            cv.dt[(x, 8)] = RED_DK
        cv.dt[(18, 9)] = RED_DK; cv.dt[(19, 9)] = RED_DK
    else:           # 빛 번짐: 바이저 위·아래·앞으로 반투명 파랑
        for x in range(13, 27):
            for y in (7, 11):
                cv.gl[(x, y)] = VB_HALO
        for y in (8, 9, 10):
            cv.gl[(27, y)] = (140, 220, 255, 150)
        cv.gl[(28, 9)] = (140, 220, 255, 90)
    return cv.image()


# ═══════════════════════════════════════════════════════════════════════
# 2) 비행사 — 갈색 가죽 비행모(귀덮개) + 동그란 고글(파란 렌즈) + 흰 머플러 + 가죽 재킷
# ═══════════════════════════════════════════════════════════════════════
LEATH = (156, 96, 54, 255)
LEATH_HI = (196, 132, 80, 255)
LEATH_DK = (112, 66, 38, 255)
BRASS = (232, 182, 72, 255)
BRASS_DK = (176, 124, 44, 255)
FLEECE = (248, 236, 206, 255)
FLEECE_DK = (222, 202, 160, 255)
JACKET = (126, 80, 48, 255)
JACKET_HI = (160, 108, 66, 255)
SCARF = (252, 252, 252, 255)
SCARF_SH = (214, 222, 236, 255)

PLANE_GOGGLE = {"x": 14, "y": 7, "w": 12, "h": 6}
STRAP = (92, 80, 58, 255)
LID = (110, 64, 50, 255)


def aviator(frame):
    shout = frame == 1
    cv = Cv()
    # 가죽 재킷 어깨 + 털 깃
    shoulders(cv, JACKET)
    for (x, y) in list(cv.px):
        if (x, y - 1) not in cv.px:
            cv.dt[(x, y)] = JACKET_HI
    cv.rect(3, 23, 27, 23, LEATH_DK, to="dt")
    cv.dt[(16, 22)] = LEATH_DK
    fl = Cv()
    fl.spans({18: (9, 23), 19: (7, 24), 20: (7, 12)}, FLEECE)
    fl.spans({20: (20, 24)}, FLEECE)
    for x in range(8, 25, 2):
        fl.dt[(x, 19)] = FLEECE_DK
    cv.overlay(fl)
    # 얼굴
    hd = Cv()
    hd.ellipse(16.6, 10.6, 7.4, 6.8, SKIN)
    hd.dt[(15, 13)] = BLUSH; hd.dt[(16, 13)] = BLUSH; hd.dt[(24, 13)] = BLUSH
    if shout:
        hd.art(19, 13, ["mmmm",
                        "mttm",
                        ".tt."], {"m": MOUTH, "t": TONGUE})
        hd.dt[(19, 13)] = TEETH; hd.dt[(22, 13)] = TEETH
    else:   # 자신만만한 웃음
        hd.art(18, 14, ["l...l",
                        ".lll."], {"l": LIP})
    # 가죽 비행모: 정수리를 덮고 이마 가장자리에 털 안감이 보임
    cap = Cv()
    cap.ellipse(16.0, 8.3, 8.7, 7.7, LEATH, keep=lambda x, y: y <= 6 or (x <= 10 and y <= 11))
    gloss(cap, LEATH, LEATH_HI, LEATH_DK, hx0=7, hx1=23)
    for p in ((10, 2), (11, 1), (9, 3), (12, 1)):
        cap.dt[p] = LEATH_HI
    cap.dt[(11, 2)] = (226, 168, 112, 255)
    for p in ((17, 1), (17, 2), (18, 3), (18, 4), (19, 5)):                # 가운데 솔기
        cap.dt[p] = LEATH_DK
    for x in range(11, 26):                                                 # 이마 털 안감
        if (x, 6) in cap.px:
            cap.dt[(x, 6)] = FLEECE
    for x in range(12, 25, 3):
        if (x, 6) in cap.dt:
            cap.dt[(x, 6)] = FLEECE_DK
    hd.overlay(cap)
    # 귀덮개 (따로 늘어진 덮개 + 앞 가장자리 털 + 똑딱단추)
    fp = Cv()
    fp.spans({8: (9, 12), 9: (8, 13), 10: (8, 13), 11: (8, 13), 12: (8, 13), 13: (8, 13), 14: (9, 13), 15: (10, 12)}, LEATH)
    for (x, y) in list(fp.px):
        if (x + 1, y) not in fp.px:
            fp.dt[(x, y)] = FLEECE
        elif (x, y + 1) not in fp.px or (x - 1, y) not in fp.px:
            fp.dt[(x, y)] = LEATH_DK
    fp.dt[(10, 13)] = BRASS
    hd.overlay(fp)
    # 턱끈 (귀덮개 아래 → 턱 밑, 놋쇠 버클)
    for p in ((12, 15), (12, 16), (13, 16), (14, 16)):
        hd.px[p] = LEATH_DK
    hd.dt[(13, 16)] = BRASS
    # 고글: 놋쇠 테 동그란 렌즈 두 개 + 끈
    gg = Cv()
    gg.ellipse(17.2, 9.8, 3.1, 3.1, BRASS)
    gg.ellipse(23.0, 9.8, 2.1, 3.0, BRASS)
    gg.rect(20, 9, 21, 10, BRASS_DK)                                       # 콧등 다리
    gg.ellipse(17.2, 9.8, 2.1, 2.1, GLASS, to="dt")
    gg.ellipse(23.0, 9.8, 1.2, 2.0, GLASS, to="dt")
    for (x, y) in list(gg.px):
        if gg.px[(x, y)] == BRASS and (x, y) not in gg.dt:
            if (x, y + 1) not in gg.px or (x + 1, y) not in gg.px:
                gg.dt[(x, y)] = BRASS_DK
            elif (x, y - 1) not in gg.px:
                gg.dt[(x, y)] = (252, 222, 130, 255)
    for p in ((18, 11), (19, 10), (19, 11), (24, 10), (24, 11), (23, 11)):  # 렌즈 아래쪽 진한 파랑
        if p in gg.dt:
            gg.dt[p] = GLASS_DK
    if shout:   # 놀라 커진 눈동자
        gg.rect(17, 9, 18, 10, EYE, to="dt"); gg.dt[(17, 9)] = GLINT
        gg.dt[(23, 9)] = EYE; gg.dt[(23, 10)] = EYE
        gg.dt[(15, 8)] = GLINT; gg.dt[(16, 8)] = GLINT; gg.dt[(22, 8)] = GLINT
    else:       # 결의: 눈꺼풀이 반쯤 내려온 눈 (안쪽이 더 낮게)
        gg.art(15, 8, ["LLLL.",
                       "w..LL",
                       "...e."], {"L": LID, "e": EYE, "w": GLINT})
        gg.dt[(18, 9)] = EYE
        gg.art(22, 8, ["LLL",
                       "Le.",
                       ".e."], {"L": LID, "e": EYE})
    hd.overlay(gg)
    for y in (9, 10):                                                       # 고글 끈이 귀덮개 위로
        for x in range(8, 14):
            if (x, y) in hd.px:
                hd.dt[(x, y)] = STRAP
    hd.dt[(9, 9)] = (130, 116, 86, 255)
    cv.overlay(hd)
    # 흰 머플러: 턱 밑을 감고 매듭, 꼬리는 뒤(왼쪽)로 휘날림
    sc = Cv()
    sc.spans({17: (11, 22), 18: (10, 23)}, SCARF)
    tail = [(9, 17), (8, 17), (7, 16), (6, 16), (5, 16), (4, 15), (3, 15), (2, 14)] if not shout else \
           [(9, 17), (8, 16), (7, 16), (6, 15), (5, 15), (4, 14), (3, 13), (2, 13)]
    for x, y in tail:
        sc.put(x, y, SCARF); sc.put(x, y + 1, SCARF)
    sc.put(1, tail[-1][1] + (0 if not shout else 1), SCARF)
    for x in range(10, 24):
        if (x, 18) in sc.px:
            sc.dt[(x, 18)] = SCARF_SH
    for x, y in tail[1::2]:
        sc.dt[(x, y + 1)] = SCARF_SH
    sc.spans({19: (21, 23), 20: (22, 23)}, SCARF)                           # 앞 매듭
    sc.dt[(23, 20)] = SCARF_SH; sc.dt[(21, 19)] = SCARF_SH
    cv.overlay(sc)
    return cv.image()


# ═══════════════════════════════════════════════════════════════════════
# 3) 헬기 조종사 — 노랑·흰 헬멧(노란 헬기 짝꿍, 빨간 줄) + 헤드셋 + 붐 마이크 + 짙은 바이저
# ═══════════════════════════════════════════════════════════════════════
Y_ = (250, 198, 44, 255)
Y_HI = (255, 232, 124, 255)
Y_DK = (214, 150, 30, 255)
STRIPE = (226, 64, 52, 255)
HVIS = (36, 60, 66, 255)
HVIS_HI = (78, 120, 126, 255)
HVIS_EYE = (186, 228, 220, 255)
FSUIT = (66, 98, 168, 255)
FSUIT_HI = (104, 140, 210, 255)
FSUIT_DK = (46, 70, 128, 255)
CUP = (70, 72, 84, 255)
CUP_HI = (120, 124, 138, 255)

HELI_GOGGLE = {"x": 12, "y": 7, "w": 14, "h": 4}


def heli_pilot(frame):
    shout = frame == 1
    cv = Cv()
    # 파란 비행복 어깨 + 깃 + 패치
    shoulders(cv, FSUIT)
    for (x, y) in list(cv.px):
        if (x, y - 1) not in cv.px:
            cv.dt[(x, y)] = FSUIT_HI
    cv.rect(20, 21, 22, 22, Y_, to="dt"); cv.dt[(21, 21)] = STRIPE        # 가슴 패치
    cv.rect(5, 21, 8, 21, STRIPE, to="dt")                                 # 팔 띠
    cv.rect(3, 23, 27, 23, FSUIT_DK, to="dt")
    cl = Cv()                                                              # 비행복 깃
    cl.spans({18: (11, 21), 19: (10, 22)}, FSUIT_HI)
    cl.dt[(16, 19)] = FSUIT_DK
    cv.overlay(cl)
    # 얼굴 (아래가 열린 헬멧이라 코·입·턱이 보임)
    hd = Cv()
    hd.ellipse(17.0, 11.8, 7.0, 6.1, SKIN)
    hd.put(25, 12, SKIN)                                                   # 코끝
    hd.dt[(24, 13)] = SKIN_SH
    hd.dt[(15, 13)] = BLUSH; hd.dt[(16, 13)] = BLUSH
    if shout:
        hd.art(19, 14, ["mmmm",
                        "mttm",
                        ".tt."], {"m": MOUTH, "t": TONGUE})
        hd.dt[(19, 14)] = TEETH; hd.dt[(22, 14)] = TEETH
    else:   # 굳게 다문 입 (한쪽 입꼬리 살짝 위)
        hd.art(19, 15, ["lll.", "...."], {"l": LIP})
        hd.dt[(22, 14)] = LIP
    cv.overlay(hd)
    # 헬멧: 노란 껍데기가 정수리와 옆(턱선까지)을 감싼다 + 흰·빨간 줄
    hm = Cv()
    hm.ellipse(15.6, 9.6, 9.0, 8.3, Y_, keep=lambda x, y: y <= 7 or x <= 13)
    gloss(hm, Y_, Y_HI, Y_DK, hx0=6, hx1=23)
    for p in ((9, 3), (10, 2), (8, 4)):
        hm.dt[p] = Y_HI
    hm.dt[(9, 4)] = GLINT; hm.dt[(10, 3)] = GLINT
    for x, y in ((15, 2), (16, 2), (17, 3), (18, 3), (19, 4), (20, 4), (21, 5), (22, 5)):   # 흰 줄
        if (x, y) in hm.px:
            hm.dt[(x, y)] = WHITE
    for x, y in ((13, 2), (14, 2), (16, 3), (17, 4), (18, 4), (19, 5), (20, 5)):            # 빨간 줄
        if (x, y) in hm.px:
            hm.dt[(x, y)] = STRIPE
    for x in range(13, 25):                                                # 바이저 덮개 턱
        if (x, 6) in hm.px:
            hm.dt[(x, 6)] = Y_DK
    hm.put(24, 6, Y_DK)
    for y in range(11, 17):                                                # 얼굴 둘레 고무 테
        if (13, y) in hm.px:
            hm.dt[(13, y)] = Y_DK
    cv.overlay(hm)
    # 헤드셋 귀컵 (둥근 짙은 컵 + 밝은 테)
    hs = Cv()
    hs.ellipse(9.6, 11.8, 2.6, 3.2, CUP)
    hs.ellipse(9.6, 11.8, 1.5, 2.0, CUP_HI, to="dt")
    hs.dt[(9, 11)] = STEEL; hs.dt[(10, 11)] = STEEL; hs.dt[(9, 12)] = STEEL; hs.dt[(10, 12)] = STEEL
    hs.dt[(8, 9)] = CUP_HI
    cv.overlay(hs)
    # 붐 마이크: 귀컵 → 볼을 따라 → 입꼬리 앞
    for p in ((12, 14), (13, 15), (14, 15), (15, 15)):
        cv.dt[p] = CUP
    mic = Cv()
    mic.rect(16, 15, 17, 16, (40, 40, 46, 255))
    mic.dt[(16, 15)] = (100, 102, 118, 255)
    cv.overlay(mic)
    # 바이저 (짙은 청록 스모크, 앞으로 한 칸 튀어나옴)
    vs = Cv()
    vs.spans({7: (13, 24), 8: (12, 25), 9: (12, 25), 10: (13, 25)}, HVIS)
    for x in range(13, 25):
        vs.dt[(x, 7)] = HVIS_HI
    vs.dt[(25, 8)] = HVIS_HI
    if shout:
        vs.art(15, 8, ["ww...ww",
                       "wp...wp"], {"w": HVIS_EYE, "p": EYE})
    else:
        vs.art(15, 8, ["w.....w",
                       "wwp..pw"], {"w": HVIS_EYE, "p": EYE})
    cv.overlay(vs)
    return cv.image()


# ═══════════════════════════════════════════════════════════════════════
# 4) UFO 외계인 — 초록 꼬마, 반짝이는 큰 검은 아몬드 눈(= 고글), 작은 더듬이, 유리 돔 + 금속 테
# ═══════════════════════════════════════════════════════════════════════
ALIEN = (124, 222, 110, 255)
ALIEN_HI = (178, 244, 150, 255)
ALIEN_DK = (82, 170, 84, 255)
M_HI = (222, 228, 240, 255)
M_ = (176, 184, 200, 255)
M_DK = (124, 132, 152, 255)
RIMBAND = (88, 96, 118, 255)
EYE_SHEEN = (84, 100, 150, 255)
ANT = (255, 120, 180, 255)
LIGHTS = [(255, 84, 84), (255, 214, 60), (110, 240, 120), (90, 200, 255), (255, 120, 220)]

UFO_GOGGLE = {"x": 10, "y": 9, "w": 13, "h": 5}


def alien(frame):
    shout = frame == 1
    cv = Cv()
    # 유리 돔 (밝은 하늘색 원, 오른쪽 그늘·왼쪽 위 반짝)
    cv.ellipse(16, 13.5, 12.4, 12.6, GLASS, keep=lambda x, y: y <= 18)
    for (x, y) in list(cv.px):
        if x >= 23:
            cv.dt[(x, y)] = GLASS_DK
        elif x >= 21:
            cv.dt[(x, y)] = GLASS_MID
    for p in ((7, 6), (6, 7), (6, 8), (5, 9), (8, 5), (9, 4)):
        cv.dt[p] = GLINT
    cv.dt[(26, 6)] = GLINT
    # 외계인 머리: 위가 넓고 턱이 좁은 달걀
    al = Cv()
    al.ellipse(16, 11.0, 7.4, 6.4, ALIEN)
    al.spans({17: (11, 21), 18: (13, 19)}, ALIEN)
    gloss(al, ALIEN, ALIEN_HI, ALIEN_DK, hx0=9, hx1=21)
    al.dt[(11, 7)] = ALIEN_HI; al.dt[(12, 6)] = ALIEN_HI
    # 더듬이
    al.put(17 if shout else 16, 4, ALIEN_DK)               # 돔 안에 쏙 들어가는 짧은 더듬이
    al.rect(16, 2, 17, 3, (255, 236, 90, 255) if shout else ANT)
    al.dt[(16, 2)] = GLINT
    # 큰 아몬드 눈 (바깥 위로 치켜 올라감) — 눈이 곧 '고글'
    pal = {"e": EYE, "w": GLINT, "s": EYE_SHEEN, "b": ALIEN_DK}
    if shout:
        near = ["..eee.",
                ".eweee",
                "eweeee",
                "eeeese",
                ".eess."]
        far = [".ee.",
               "ewee",
               "eeee",
               "eese",
               ".es."]
    else:
        near = ["bb....",
                ".bbbbe",
                "eweeee",
                "eeeese",
                ".eess."]
        far = ["...b",
               "ebbe",
               "ewee",
               "eese",
               ".es."]
    al.art(10, 9, near, pal)
    al.art(19, 9, far, pal)
    # 입
    if shout:
        al.art(16, 15, [".mm.", "mmmm", ".tt."], {"m": MOUTH, "t": TONGUE})
    else:
        al.art(16, 16, ["bbb"], {"b": ALIEN_DK})
    al.dt[(12, 15)] = BLUSH; al.dt[(21, 15)] = BLUSH
    cv.overlay(al)
    # 돔 금속 테 (어깨 자리): 위 밝게 · 불빛 띠 · 아래 그늘
    rm = Cv()
    rm.spans({19: (3, 28), 20: (1, 30), 21: (0, 31), 22: (0, 31), 23: (1, 30)}, M_)
    for x in range(0, 32):
        if (x, 19) in rm.px:
            rm.dt[(x, 19)] = M_HI
        if (x, 21) in rm.px:
            rm.dt[(x, 21)] = RIMBAND
        if (x, 23) in rm.px:
            rm.dt[(x, 23)] = M_DK
    for i, x in enumerate(range(2, 31, 4)):
        col = LIGHTS[i % len(LIGHTS)] + (255,)
        c = col
        if shout:
            c = (255, 84, 84, 255) if i % 2 == 0 else (255, 214, 60, 255)
        rm.dt[(x, 21)] = c; rm.dt[(x + 1, 21)] = c
    rm.dt[(6, 19)] = GLINT; rm.dt[(7, 19)] = GLINT
    cv.overlay(rm)
    if shout:   # 더듬이 끝 번쩍 불꽃
        for q in ((14, 2), (19, 2), (14, 4), (19, 4), (15, 1), (18, 1)):
            cv.gl[q] = (255, 236, 90, 170)
    return cv.image()


PILOTS = {
    "car": (robot, CAR_GOGGLE),
    "plane": (aviator, PLANE_GOGGLE),
    "heli": (heli_pilot, HELI_GOGGLE),
    "ufo": (alien, UFO_GOGGLE),
}


def main(out=None, preview=None):
    here = os.path.dirname(os.path.abspath(__file__))
    out = out or os.path.join(here, "..", "app", "src", "main", "assets", "pet")
    preview = preview or os.path.join(here, "..", "..", "스크린샷", "81_조종사_시안.png")
    os.makedirs(out, exist_ok=True)
    rows = []
    for name, (fn, rect) in PILOTS.items():
        frames = [fn(i) for i in range(2)]
        sheet = Image.new("RGBA", (W * 2, H), CLEAR)
        for i, f in enumerate(frames):
            sheet.alpha_composite(f, (i * W, 0))
        sheet.save(os.path.join(out, f"pilot_{name}.png"))
        rows.append((name, frames, rect))
    with open(os.path.join(out, "pilots.json"), "w", encoding="utf-8") as fp:
        json.dump({n: r for n, (_, r) in PILOTS.items()}, fp, ensure_ascii=False, indent=2)
        fp.write("\n")
    # 미리보기: 줄마다 한 조종사 — 흰 바탕 0·1 | 어두운 바탕 0·1 | 디버그(고글 네모) 0·1 | 컷인 흉내(빛 지나감)
    S, GAP, TOP, LEFT = 10, 12, 28, 70
    cols = 7
    pw = LEFT + cols * (W * S + GAP) + 10
    ph = TOP + len(rows) * (H * S + GAP) + 10
    prev = Image.new("RGBA", (pw, ph), (236, 236, 240, 255))
    dr = ImageDraw.Draw(prev)
    heads = ["white f0", "white f1", "dark f0", "dark f1", "debug f0", "debug f1", "cut-in mock (f1)"]
    for i, t in enumerate(heads):
        dr.text((LEFT + i * (W * S + GAP) + 4, 8), t, fill=(40, 40, 40, 255))
    for r, (name, frames, rect) in enumerate(rows):
        y = TOP + r * (H * S + GAP)
        dr.text((8, y + H * S // 2 - 6), name, fill=(40, 40, 40, 255))
        for ci in range(cols):
            x = LEFT + ci * (W * S + GAP)
            fr = frames[ci % 2] if ci < 6 else frames[1]
            if ci < 2:
                bg = (255, 255, 255, 255)
            elif ci < 4:
                bg = (26, 26, 34, 255)
            elif ci < 6:
                bg = (150, 150, 158, 255)
            else:
                bg = (40, 20, 22, 255)
            tile = Image.new("RGBA", (W * S, H * S), bg)
            tile.alpha_composite(fr.resize((W * S, H * S), Image.NEAREST))
            td = ImageDraw.Draw(tile)
            gx0, gy0 = rect["x"] * S, rect["y"] * S
            gx1, gy1 = (rect["x"] + rect["w"]) * S - 1, (rect["y"] + rect["h"]) * S - 1
            if 4 <= ci < 6:
                for k in range(1, W):
                    td.line([(k * S, 0), (k * S, H * S)], fill=(0, 0, 0, 28))
                for k in range(1, H):
                    td.line([(0, k * S), (W * S, k * S)], fill=(0, 0, 0, 28))
                td.rectangle([gx0, gy0, gx1, gy1], outline=(0, 255, 255, 255), width=2)
                td.text((gx0 + 2, gy1 + 4), f"{rect['x']},{rect['y']} {rect['w']}x{rect['h']}", fill=(0, 255, 255, 255))
            if ci == 6:   # 앱과 같은 식으로 빛 띠 한 장면 (k=0.45)
                gl = Image.new("RGBA", (W * S, H * S), CLEAR)
                gd = ImageDraw.Draw(gl)
                gw, gh = gx1 - gx0 + 1, gy1 - gy0 + 1
                sx = gx0 - gh + (gw + gh * 2) * 0.45
                gd.polygon([(sx, gy1), (sx + 3 * S, gy1), (sx + 3 * S + gh, gy0), (sx + gh, gy0)], fill=(255, 255, 255, 230))
                gd.rectangle([sx + 5 * S, gy0, sx + 6 * S, gy1], fill=(255, 255, 255, 153))
                mask = Image.new("L", (W * S, H * S), 0)
                ImageDraw.Draw(mask).rectangle([gx0, gy0, gx1, gy1], fill=255)
                clip = Image.new("RGBA", (W * S, H * S), CLEAR)
                clip.paste(gl, (0, 0), mask)
                tile.alpha_composite(clip)
            prev.alpha_composite(tile, (x, y))
    os.makedirs(os.path.dirname(os.path.abspath(preview)), exist_ok=True)
    prev.save(preview)
    print("ok", list(PILOTS))


if __name__ == "__main__":
    main(*sys.argv[1:3])
