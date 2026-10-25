"""
Pixel TMI 기본 캐릭터 — 회색 도트 고양이.
결: 회색 몸 + 진회색 외곽선, 빨간 목걸이 + 노란 방울, 위로 선 꼬리, 3/4 정면 얼굴 + 흰 수염.
그림을 베끼지 않고 도형을 조립한 뒤 외곽선을 자동으로 두른다.
높이 24칸 = 앱의 아이콘 24도트 → 한 칸이 화면 도트 하나로 딱 맞는다.
사용: python 고양이_오마주.py <출력 폴더> <미리보기.png>
출력: cat_walk.png(4프레임) · cat_run.png(전력질주 4프레임) · cat_idle.png(앉기·깜빡 2프레임) · cat_face.png(말하기·놀람·웃음 3프레임)
      cat_climb.png(벽 타기 3프레임 — 이것만 34×32: 위 24칸 몸, 아래 8칸 꼬리 끝)
      cat_sneak.png(살금살금: 두 발로 서서 까치발로 지나가기 4프레임) — 스킨(cat_white·cat_black)도 같은 이름으로
"""
import os
import sys

from PIL import Image

W, H = 34, 24
CH = 32                        # 벽 타기 시트만 세로 32칸: 위 24칸은 몸(다른 시트와 같은 자리), 아래 8칸은 늘어진 꼬리 끝
LINE = (74, 78, 84, 255)       # 진회색 외곽선
FUR = (128, 134, 140, 255)     # 회색 털
FAR = (106, 111, 117, 255)     # 먼 쪽 다리 (조금 어둡게)
LIGHT = (176, 180, 186, 255)   # 주둥이·귀 안
EYE = (22, 22, 26, 255)
SHINE = (250, 250, 250, 255)
WHISK = (196, 200, 206, 255)
RED = (214, 40, 44, 255)
BELL = (246, 196, 40, 255)
NOSE = (236, 150, 160, 255)
CLEAR = (0, 0, 0, 0)


class Cv:
    def __init__(self):
        self.px = {}

    def rect(self, x0, y0, x1, y1, c=None):
        c = c or FUR
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px[(x, y)] = c

    def put(self, x, y, c=None):
        self.px[(x, y)] = c or FUR

    def cut(self, *pts):
        for p in pts:
            self.px.pop(p, None)

    def leg(self, x, y0, y1, slant=0, c=None):
        """2칸 굵기 다리. slant=+1이면 아래 두 줄이 앞으로, -1이면 뒤로"""
        for y in range(y0, y1 + 1):
            dx = slant if y >= y1 - 1 else 0
            self.rect(x + dx, y, x + dx + 1, y, c)

    def image(self, details, h=H):
        """h = 캔버스 세로 (벽 타기만 CH). 세로가 늘면 24칸 아래로 내려간 몸 칸은 자르고(꼬리 tail 칸만 남김) 외곽선으로 마감"""
        if h > H:
            self.px = {p: c for p, c in self.px.items() if p[1] < H or p in getattr(self, "tail", ())}
        im = Image.new("RGBA", (W, h), CLEAR)
        for (x, y) in list(self.px):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n not in self.px and 0 <= n[0] < W and 0 <= n[1] < h:
                    im.putpixel(n, LINE)
        for (x, y), c in self.px.items():
            if 0 <= x < W and 0 <= y < h:
                im.putpixel((x, y), c)
        for x, y, c in details:
            if 0 <= x < W and 0 <= y < h:
                im.putpixel((x, y), c)
        return im


def head(cv, hx, top):
    """3/4 정면 머리 (폭 12, 높이 10) + 뾰족 귀"""
    cv.rect(hx, top, hx + 11, top + 9)
    cv.cut((hx, top), (hx + 11, top), (hx, top + 9), (hx + 11, top + 9))
    # 귀: 바깥쪽이 높은 삼각형
    cv.put(hx, top - 3); cv.rect(hx, top - 2, hx + 1, top - 2); cv.rect(hx, top - 1, hx + 2, top - 1)
    cv.put(hx + 11, top - 3); cv.rect(hx + 10, top - 2, hx + 11, top - 2); cv.rect(hx + 9, top - 1, hx + 11, top - 1)
    cv.put(hx + 1, top - 1, LIGHT); cv.put(hx + 10, top - 1, LIGHT)   # 귀 안


def face(d, hx, top, mood="normal", blink=False):
    ey = top + 4
    for ex in (hx + 3, hx + 8):
        if blink:
            d.append((ex, ey + 1, EYE))
        elif mood == "happy":
            d += [(ex - 1, ey + 1, EYE), (ex, ey, EYE), (ex + 1, ey + 1, EYE)]
        elif mood == "surprised":
            d += [(ex, ey - 1, EYE), (ex, ey, EYE), (ex, ey + 1, EYE), (ex - 1, ey, EYE), (ex - 1, ey - 1, SHINE)]
        else:
            d += [(ex, ey, EYE), (ex, ey + 1, EYE)]
    # 코는 그리지 않는다 (빨간 코 X) — 눈 아래 고양이 입 'ω'만
    mouth = LIGHT if sum(FUR[:3]) < 300 else (72, 50, 60, 255)   # 검은 고양이는 밝은 입선
    if mood in ("talk", "surprised"):
        # 작게 벌린 입 'o'
        d += [(hx + 4, top + 7, mouth), (hx + 7, top + 7, mouth), (hx + 5, top + 8, mouth), (hx + 6, top + 8, mouth),
              (hx + 5, top + 7, (150, 60, 70, 255)), (hx + 6, top + 7, (150, 60, 70, 255))]
    else:
        # ω : 코 아래 가운데에서 양쪽으로 둥글게
        d += [(hx + 3, top + 7, mouth), (hx + 8, top + 7, mouth), (hx + 4, top + 8, mouth), (hx + 7, top + 8, mouth),
              (hx + 5, top + 7, mouth), (hx + 6, top + 7, mouth)]
    # 수염: 볼에서 바깥으로 두 가닥씩 (외곽선 위로 삐져나오게)
    d += [(hx - 1, top + 6, WHISK), (hx - 2, top + 6, WHISK), (hx - 1, top + 7, WHISK), (hx - 2, top + 8, WHISK)]
    d += [(hx + 12, top + 6, WHISK), (hx + 13, top + 6, WHISK), (hx + 12, top + 7, WHISK), (hx + 13, top + 8, WHISK)]


def collar(d, hx, top):
    """앉은 모습(정면): 목 앞을 가로지르는 목걸이 + 가운데 방울"""
    y = top + 9
    for x in range(hx + 2, hx + 10):
        d.append((x, y, RED))
    d += [(hx + 5, y + 1, BELL), (hx + 6, y + 1, BELL), (hx + 5, y + 2, (200, 150, 20, 255)), (hx + 6, y + 2, (200, 150, 20, 255))]


def neck_collar(d, hx, top):
    """서 있을 때(옆모습): 머리 아래 목덜미에 비스듬히 감긴 목걸이 + 앞가슴 쪽 방울 (턱 밑을 가로지르지 않게)"""
    band = [(hx - 1, top + 6), (hx - 1, top + 7), (hx, top + 7), (hx, top + 8), (hx + 1, top + 8),
            (hx + 1, top + 9), (hx + 2, top + 9), (hx + 3, top + 9), (hx + 3, top + 10), (hx + 4, top + 10)]
    d += [(x, y, RED) for x, y in band]
    d += [(hx + 4, top + 11, BELL), (hx + 5, top + 11, BELL), (hx + 4, top + 12, (200, 150, 20, 255))]


def walk(frame, blink=False):
    cv = Cv()
    hx, top = 20, 4
    # 꼬리: 위로 서서 끝이 앞으로 살짝 말림 / 흔들
    if frame in (0, 2):
        cv.rect(6, 4, 7, 12); cv.rect(7, 3, 8, 3); cv.put(9, 4)
    else:
        cv.rect(5, 3, 6, 12); cv.put(6, 2); cv.put(7, 2)
    cv.rect(6, 11, 9, 12)
    # 다리 자리: (뒤-가까운, 앞-가까운, 뒤-먼, 앞-먼) x, 기울기, 들림
    pose = [
        ((9, -1, 0), (21, 1, 0), (13, 0, 0), (17, 0, 0)),   # 가까운 쪽 성큼
        ((11, 0, 0), (19, 0, 1), (11, 0, 0), (19, 0, 0)),   # 지나가기
        ((13, 0, 0), (17, 0, 0), (9, -1, 0), (21, 1, 0)),   # 먼 쪽 성큼
        ((11, 0, 0), (19, 0, 0), (11, 0, 0), (19, 0, 1)),   # 지나가기
    ][frame]
    bn, fn, bf, ff = pose
    # 먼 쪽 다리 (몸 뒤에 먼저)
    cv.leg(bf[0], 16, 22 - bf[2], bf[1], FAR)
    cv.leg(ff[0], 16, 22 - ff[2], ff[1], FAR)
    # 몸통 (짧고 둥글게)
    cv.rect(9, 11, 23, 16)
    cv.cut((9, 11), (9, 16), (23, 16))
    # 가까운 쪽 다리
    cv.leg(bn[0], 16, 22 - bn[2], bn[1])
    cv.leg(fn[0], 16, 22 - fn[2], fn[1])
    head(cv, hx, top)
    d = []
    face(d, hx, top, blink=blink)
    neck_collar(d, hx, top)
    return cv.image(d)


def limb(cv, x0, y0, x1, y1, c=None):
    """비스듬한 2칸 굵기 다리 (위 끝 → 아래 끝)"""
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(steps + 1):
        x = round(x0 + (x1 - x0) * i / steps)
        y = round(y0 + (y1 - y0) * i / steps)
        cv.rect(x, y, x + 1, y, c)


def run(frame):
    """전력질주 4장: 뻗기 → 모으기 → 밀기 → 공중. 꼬리는 뒤로 휘날린다"""
    cv = Cv()
    oy = (0, -1, 0, -2)[frame]                          # 몸이 들썩
    hx, top = 21, 4 + oy
    by = 11 + oy                                        # 몸통 윗줄
    leg_top = by + 5
    # (뒤-먼, 앞-먼, 뒤-가까운, 앞-가까운) 다리 아래 끝
    feet = [
        ((8, 22), (24, 21), (6, 21), (26, 22)),          # 뻗기: 앞발 쭉, 뒷발 쭉
        ((15, 22), (17, 21), (13, 21), (19, 22)),        # 모으기: 배 밑에 나란히
        ((12, 21), (22, 21), (8, 22), (19, 22)),         # 밀기
        ((9, 19), (24, 19), (8, 20), (25, 20)),          # 공중: 다리 접고 붕
    ][frame]
    tops = ((13, leg_top), (19, leg_top), (11, leg_top), (21, leg_top))
    for (t, f), c in zip(zip(tops[:2], feet[:2]), (FAR, FAR)):
        limb(cv, t[0], t[1], f[0], f[1], c)
    # 꼬리: 뒤로 휘날림
    tail = [(9, by + 1), (6, by), (4, by - 1), (2, by - 2 - (frame % 2))]
    for (ax, ay), (bx, bby) in zip(tail, tail[1:]):
        limb(cv, ax, ay, bx, bby)
    # 몸통 (길게 늘여서)
    cv.rect(9, by, 24, by + 5)
    cv.cut((9, by), (9, by + 5), (24, by + 5))
    for t, f in zip(tops[2:], feet[2:]):
        limb(cv, t[0], t[1], f[0], f[1])
    head(cv, hx, top)
    d = []
    face(d, hx, top)
    neck_collar(d, hx, top)
    return cv.image(d)


def climb(frame):
    """벽 타기 (등판이 보이는 大자): 0·1 = 팔다리 번갈아 뻗기, 2 = 철푸덕 붙는 순간(쫙 펼침).
    세로 32칸: 몸은 위 24칸 그대로, 늘어진 꼬리는 아래 8칸까지 내려와 끝이 옆으로 살짝 말린다 (프레임마다 좌우로 살랑)"""
    cv = Cv()
    cx = 17
    # 팔다리 끝 (왼팔, 오른팔, 왼다리, 오른다리)
    ends = [
        ((7, 3), (28, 9), (9, 23), (25, 18)),
        ((6, 9), (27, 3), (9, 18), (25, 23)),
        ((5, 5), (29, 5), (7, 23), (27, 23)),
    ][frame]
    tops = ((13, 13), (21, 13), (14, 19), (20, 19))
    for (t, e) in zip(tops, ends):
        limb(cv, t[0], t[1], e[0], e[1])
    side = (1, -1, 1)[frame]                                 # 꼬리 끝이 말리는 쪽 (프레임마다 살랑)
    t = Cv()
    t.rect(cx, 19, cx + 1, 27)                               # 늘어진 꼬리 (2칸 굵기)
    for x, y in ((18, 28), (19, 28), (20, 28), (20, 27), (21, 27), (21, 26)):   # 끝은 J자로 말려 올라감
        t.put(x if side > 0 else 2 * cx + 1 - x, y)
    cv.px.update(t.px)
    cv.tail = set(t.px)
    cv.rect(13, 11, 21, 19)                                  # 등
    cv.cut((13, 11), (21, 11), (13, 19), (21, 19))
    cv.rect(12, 3, 22, 10)                                   # 뒤통수
    cv.cut((12, 3), (22, 3))
    cv.put(12, 1); cv.rect(12, 2, 13, 2); cv.put(22, 1); cv.rect(21, 2, 22, 2)   # 귀 뒤
    d = [(x, 11, RED) for x in range(14, 21)]                 # 목걸이 뒷줄
    d += [(cx, y, FAR) for y in range(12, 19)]                # 등줄기
    for e in ends:                                           # 발톱 (밝게)
        d.append((e[0], e[1], LIGHT))
    return cv.image(d, h=CH)


def punch(frame):
    """냥냥 펀치 (옆모습): 0 = 앞발 들어 준비, 1 = 쭉 뻗어 퍽"""
    cv = Cv()
    hx, top = 20, 4
    cv.rect(6, 4, 7, 12); cv.rect(7, 3, 8, 3); cv.put(9, 4)   # 꼬리 바짝
    cv.rect(6, 11, 9, 12)
    cv.leg(11, 16, 22, -1, FAR)
    cv.leg(17, 16, 22, 0, FAR)
    cv.rect(9, 11, 23, 16)
    cv.cut((9, 11), (9, 16), (23, 16))
    cv.leg(9, 16, 22, -1)
    if frame == 0:
        cv.leg(21, 16, 21, 0)                                # 앞발 접어 장전 (몸을 웅크림)
    else:
        cv.rect(23, 15, 32, 16)                              # 앞발 쭉! (턱 아래로)
        cv.rect(32, 14, 33, 17)
    head(cv, hx, top)
    d = []
    face(d, hx, top, mood="happy" if frame == 1 else "normal")
    neck_collar(d, hx, top)
    if frame == 1:
        d += [(33, 15, LIGHT), (33, 16, LIGHT)]                    # 발바닥
    else:
        d += [(21, 17, LIGHT), (22, 17, LIGHT)]
    return cv.image(d)


def sit_base(cv, hx, top):
    """앉은 몸통 (꼬리·엉덩이·몸·먼 앞다리) — 세수·손 흔들기가 같이 쓴다"""
    cv.rect(8, 21, 14, 22); cv.rect(7, 18, 8, 21); cv.put(8, 17)
    cv.rect(12, 15, 19, 22)
    cv.cut((12, 15), (12, 16), (13, 15))
    cv.rect(16, 12, 27, 22)
    cv.leg(21, 17, 22, 0, FAR)


def groom(frame):
    """세수: 앞발을 입에 대고 핥기 (0 = 발 올림 + 혀, 1 = 발 살짝 내리고 눈 감기)"""
    cv = Cv()
    hx, top = 18, 4
    sit_base(cv, hx, top)
    cv.leg(25, 18, 22)
    if frame == 0:
        limb(cv, 26, 18, 30, 12)                                   # 앞발을 입가로
    else:
        limb(cv, 26, 18, 30, 15)
    head(cv, hx, top)
    d = []
    face(d, hx, top, blink=True)
    collar(d, hx, top)
    if frame == 0:
        d += [(24, 12, (240, 120, 140, 255)), (25, 12, (240, 120, 140, 255)), (30, 12, LIGHT), (31, 12, LIGHT), (30, 11, LIGHT)]   # 혀 낼름 + 발바닥
    else:
        d += [(30, 15, LIGHT), (31, 15, LIGHT)]
    return cv.image(d)


def wave(frame):
    """행운 고양이처럼 손 흔들기 (앞발을 머리 옆으로 들어 까딱)"""
    cv = Cv()
    hx, top = 18, 4
    sit_base(cv, hx, top)
    cv.leg(24, 16, 22)
    tip = (31, 5) if frame == 0 else (32, 8)
    limb(cv, 27, 15, tip[0], tip[1])
    head(cv, hx, top)
    d = []
    face(d, hx, top, mood="happy")
    collar(d, hx, top)
    d += [(tip[0], tip[1], LIGHT), (tip[0] + 1, tip[1], LIGHT), (tip[0], tip[1] - 1, LIGHT), (tip[0] + 1, tip[1] - 1, LIGHT)]
    return cv.image(d)


def stretch(frame):
    """기지개: 앞다리 쭉 내밀고 엉덩이 번쩍 (0 = 쭉, 1 = 꼬리까지 부르르)"""
    cv = Cv()
    hx, top = 21, 9
    if frame == 0:
        cv.rect(5, 2, 6, 10); cv.put(6, 1); cv.put(7, 1)          # 꼬리 번쩍
    else:
        cv.rect(4, 3, 5, 10); cv.rect(5, 2, 7, 2)
    cv.rect(6, 8, 13, 14)                                          # 엉덩이 (높게)
    cv.cut((6, 8), (13, 8))
    cv.leg(7, 14, 22, 0, FAR); cv.leg(11, 14, 22)                  # 뒷다리 쭉
    for i in range(10):                                            # 등 (비스듬히 내려감)
        cv.rect(12 + i, 10 + i // 2, 13 + i, 15 + i // 3)
    cv.rect(21, 20, 32, 21, FAR)                                   # 먼 앞다리 쭉
    cv.rect(21, 21, 33, 22)                                        # 앞다리 쭉
    head(cv, hx, top)
    d = []
    face(d, hx, top, blink=True)
    neck_collar(d, hx, top)
    return cv.image(d)


def sleep(frame):
    """동그랗게 말려 자기 (숨 쉴 때마다 1칸 들썩)"""
    cv = Cv()
    up = frame
    cv.rect(7, 14 - up, 25, 22)                                    # 둥근 몸
    cv.cut((7, 14 - up), (25, 14 - up), (7, 22), (25, 22))
    cv.rect(5, 20, 24, 22)                                         # 앞을 감싼 꼬리
    hx, top = 17, 11 - up
    head(cv, hx, top)
    d = []
    face(d, hx, top, blink=True)
    d = [p for p in d if not (p[2] == WHISK)]                      # 자는 얼굴은 수염 접기
    d += [(x, 21, FAR) for x in range(8, 23)]                      # 꼬리 줄무늬
    return cv.image(d)


def eat(frame):
    """밥 먹기: 고개 숙여 냠냠 (0 = 그릇에 코 박기, 1 = 오물오물 살짝 듦). 밥그릇은 앱에서 그린다"""
    cv = Cv()
    hx, top = 21, 10 - frame
    cv.rect(6, 4, 7, 12); cv.rect(7, 3, 8, 3); cv.put(9, 4)       # 꼬리 살랑
    cv.rect(6, 11, 9, 12)
    cv.leg(11, 16, 22, 0, FAR); cv.leg(17, 16, 22, 0, FAR)
    cv.rect(9, 11, 23, 16)
    cv.cut((9, 11), (9, 16))
    cv.leg(9, 16, 22); cv.leg(20, 16, 22)
    head(cv, hx, top)
    d = []
    face(d, hx, top, mood="happy" if frame == 1 else "normal", blink=frame == 0)
    neck_collar(d, hx, top)
    return cv.image(d)


def pounce(frame):
    """덮치기: 0 = 엉덩이 씰룩 웅크림(눈 반짝), 1 = 폴짝 날아오르기"""
    cv = Cv()
    if frame == 0:
        hx, top = 21, 8
        cv.rect(4, 13, 8, 14); cv.put(3, 12)                       # 꼬리 낮게 씰룩
        cv.rect(8, 13, 23, 19)                                     # 납작 웅크린 몸
        cv.cut((8, 13), (23, 13))
        cv.leg(9, 19, 22, 0, FAR); cv.leg(12, 19, 22)
        cv.leg(19, 19, 22, 1, FAR); cv.leg(22, 19, 22, 1)
        head(cv, hx, top)
        d = []
        face(d, hx, top, mood="surprised")
        neck_collar(d, hx, top)
    else:
        hx, top = 21, 3
        cv.rect(2, 8, 7, 9); cv.put(1, 7)                          # 꼬리 뒤로
        cv.rect(7, 8, 23, 13)
        cv.cut((7, 8), (7, 13))
        limb(cv, 9, 13, 4, 18, FAR); limb(cv, 12, 13, 6, 19)      # 뒷다리 뒤로 쭉
        limb(cv, 22, 12, 31, 16, FAR); limb(cv, 23, 13, 33, 17)   # 앞발 앞으로 쭉
        head(cv, hx, top)
        d = []
        face(d, hx, top, mood="happy")
        neck_collar(d, hx, top)
    return cv.image(d)


def sneak_eyes(d, hx, top, look):
    """살금살금 눈: 반쯤 감은 눈꺼풀(가로 2칸) 아래 눈동자 1칸이 한쪽으로 힐끔 (look = -1 뒤, 0 앞)"""
    ey = top + 4
    for ex in (hx + 3, hx + 8):
        d += [(ex - 1, ey, LINE), (ex, ey, LINE), (ex + look, ey + 1, EYE)]


def overlay(cv, d, sub, against=None):
    """겹친 팔다리: sub(Cv)의 칸을 몸 위에 얹고, 이미 있던 몸(against를 주면 그 칸만)과 맞닿는 곳에 외곽선 1칸을 둘러 따로 보이게"""
    against = cv.px if against is None else against
    for (x, y) in sub.px:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in cv.px and n in against and n not in sub.px:
                d.append((n[0], n[1], LINE))
    d[:] = [p for p in d if (p[0], p[1]) not in sub.px]                    # 앞서 그은 선이 새 팔다리를 덮지 않게
    cv.px.update(sub.px)


def sneak(frame):
    """살금살금 (두 발로 서서 까치발): 작은 몸을 세워 앞으로 살짝 숙이고, 앞발 두 짝은 턱 밑 가슴 앞에 들어 손목을 축 늘어뜨린 채
    무릎 굽혀 발끝으로 한 발씩 들어 걷는다. 꼬리는 물음표처럼 서고 눈은 옆으로 힐끔.
    0 = 가까운 발 듦 · 1 = 지나가기(몸 1칸 낮춤) · 2 = 먼 발 듦 · 3 = 지나가기"""
    cv = Cv()
    d = []
    up = (0, 1, 0, 1)[frame]
    hx, top = 18, 4 + up
    hip = 17
    # 꼬리: 엉덩이에서 뒤로 살짝 나와 위로 선 물음표 (흔들)
    sw = (0, 0, -1, -1)[frame]
    limb(cv, 14, 16, 11 + sw, 14)
    cv.rect(10 + sw, 7 + up, 11 + sw, 14)
    cv.rect(11 + sw, 6 + up, 12 + sw, 6 + up); cv.put(13 + sw, 7 + up)

    def leg(c, kind, col):
        """kind: lift = 무릎을 엉덩이 높이로 들고 발끝은 아래로(공중) / sup = 몸 밑에서 까치발로 버팀 / front·rear = 앞·뒤로 디딘 까치발"""
        if kind == "lift":
            c.rect(18, hip, 23, hip + 1, col)                                 # 허벅지 (무릎을 몸 앞으로 번쩍)
            c.rect(22, hip + 2, 23, hip + 2, col)                             # 정강이 (아래로 대롱)
            c.put(22, hip + 3, col)                                           # 뾰족 발끝 (땅에서 2칸 뜸)
            return
        t, k, f = {"sup": ((15, hip), (16, 19), (15, 21)),
                   "front": ((18, hip), (20, 19), (20, 21)), "rear": ((15, hip), (14, 19), (13, 21))}[kind]
        limb(c, *t, *k, col); limb(c, *k, *f, col)
        c.put(f[0] + 1, f[1] + 1, col)                                        # 뾰족 발끝 (까치발)

    far_k, near_k = [("sup", "lift"), ("rear", "front"), ("lift", "sup"), ("front", "rear")][frame]
    leg(cv, far_k, FAR)
    # 먼 앞발 (몸 뒤, 가까운 앞발보다 두 칸 앞)
    fp = (0, 1, 0, 1)[frame]
    cv.rect(23, top + 11, 28 + fp, top + 11, FAR); cv.rect(28 + fp, top + 11, 29 + fp, top + 13, FAR)
    # 몸통 (작고 세로로 — 위가 앞으로 기욺)
    cv.rect(17, top + 7, 23, 14)
    cv.rect(15, 14, 22, 15)
    cv.rect(14, 16, 20, hip)
    cv.rect(15, hip + 1, 19, hip + 1)
    cv.cut((22, 15), (14, hip), (15, 14))
    # 가까운 앞발: 가슴 앞으로 쏙 내밀고 손목이 축 처짐
    np_ = (0, -1, 0, 1)[frame]
    cv.rect(23, top + 11, 26 + np_, top + 12); cv.rect(26 + np_, top + 12, 27 + np_, top + 14)
    head(cv, hx, top)
    # 가까운 다리 (맨 앞 — 몸·앞발과 겹치는 곳에 외곽선)
    sub = Cv()
    leg(sub, near_k, None)
    overlay(cv, d, sub)
    face(d, hx, top)
    d[:] = [p for p in d if p[2] != EYE and not (p[2] == WHISK and (p[0], p[1]) in cv.px)]   # 기본 눈·몸에 겹친 수염 빼기
    sneak_eyes(d, hx, top, -1 if frame < 2 else 0)
    d += [(x, top + 9, RED) for x in range(hx + 2, hx + 10)]                     # 목걸이
    d += [(hx + 4, top + 10, BELL), (hx + 5, top + 10, BELL)]                     # 방울
    # 축 늘어진 앞발 끝은 밝게 (작은 화면에서도 '든 앞발'이 보이게)
    d += [(26 + np_, top + 13, LIGHT), (27 + np_, top + 13, LIGHT), (26 + np_, top + 14, LIGHT), (27 + np_, top + 14, LIGHT)]
    d += [(28 + fp, top + 13, LIGHT), (29 + fp, top + 13, LIGHT)]
    return cv.image(d)


def sit(mood="normal", blink=False):
    cv = Cv()
    hx, top = 18, 4
    # 바닥에 말린 꼬리
    cv.rect(8, 21, 14, 22); cv.rect(7, 18, 8, 21); cv.put(8, 17)
    # 뒷다리 엉덩이 (둥글게)
    cv.rect(12, 15, 19, 22)
    cv.cut((12, 15), (12, 16), (13, 15))
    # 몸통 (세워서)
    cv.rect(16, 12, 27, 22)
    # 앞다리 두 개
    cv.leg(21, 17, 22, 0, FAR)
    cv.leg(25, 16, 22)
    head(cv, hx, top)
    d = []
    face(d, hx, top, mood=mood, blink=blink)
    collar(d, hx, top)
    return cv.image(d)


# 코인으로 여는 외관(스킨): 털·먼 다리·주둥이·외곽선·눈 색
SKINS = {
    "cat": None,
    "cat_white": ((236, 236, 230, 255), (210, 210, 204, 255), (250, 250, 246, 255), (96, 98, 104, 255), (22, 22, 26, 255)),
    "cat_black": ((58, 58, 66, 255), (44, 44, 52, 255), (104, 104, 116, 255), (16, 16, 20, 255), (250, 206, 60, 255)),
}


def main(out, preview):
    global FUR, FAR, LIGHT, LINE, EYE
    base = (FUR, FAR, LIGHT, LINE, EYE)
    for skin, cols in SKINS.items():
        FUR, FAR, LIGHT, LINE, EYE = cols or base
        render(out, preview if skin == "cat" else None, skin)
    FUR, FAR, LIGHT, LINE, EYE = base


def render(out, preview, name):
    os.makedirs(out, exist_ok=True)
    walks = [walk(i) for i in range(4)]
    runs = [run(i) for i in range(4)]
    idle = [sit(), sit(blink=True)]
    faces = [sit("talk"), sit("surprised"), sit("happy")]
    climbs = [climb(i) for i in range(3)]
    punches = [punch(i) for i in range(2)]
    acts = {k: [fn(i) for i in range(2)] for k, fn in (("groom", groom), ("wave", wave), ("stretch", stretch), ("sleep", sleep), ("pounce", pounce), ("eat", eat))}
    sneaks = [sneak(i) for i in range(4)]
    for kind, frames in (("walk", walks), ("run", runs), ("idle", idle), ("face", faces), ("climb", climbs), ("punch", punches), *acts.items(), ("sneak", sneaks)):
        sheet = Image.new("RGBA", (W * len(frames), frames[0].height), CLEAR)
        for i, f in enumerate(frames):
            sheet.alpha_composite(f, (i * W, 0))
        sheet.save(os.path.join(out, f"{name}_{kind}.png"))
    if not preview:
        return
    S = 8
    row = walks + runs + idle + faces + climbs + punches + sum(acts.values(), [])
    prev = Image.new("RGBA", ((W * S + 12) * len(row) + 12, CH * S + 24), (255, 255, 255, 255))
    for i, f in enumerate(row):
        prev.alpha_composite(f.resize((f.width * S, f.height * S), Image.NEAREST), (12 + i * (W * S + 12), 12))
    prev.save(preview)
    print("ok")


if __name__ == "__main__":
    main(*sys.argv[1:3])
