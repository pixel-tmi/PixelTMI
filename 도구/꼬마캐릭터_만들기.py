"""
Pixel TMI SD(꼬마) 캐릭터 4종 — 두 발로 서고 옷을 입은 큰 머리 동물.
결: 기획 단계에서 준 두 번째 표본(크림색 꼬마 고양이)처럼 큰 머리·표정·부드러운 자주색 외곽선.
베끼지 않도록 도형 조립 + 자동 외곽선, 옷·색은 우리 것으로.
사용: python 꼬마캐릭터_만들기.py <출력 폴더> <미리보기.png>
출력: chibi_<동물>_walk.png(4프레임) · chibi_<동물>_idle.png(2프레임) · chibi_<동물>_face.png(말하기·놀람·웃음 3프레임)
"""
import os
import sys

from PIL import Image

W, H = 28, 32
LINE = (66, 42, 62, 255)       # 부드러운 자주 외곽선
EYE = (40, 26, 36, 255)
PINK = (246, 150, 168, 255)
MOUTH = (150, 60, 70, 255)
PANTS = (92, 52, 52, 255)
CLEAR = (0, 0, 0, 0)


class Cv:
    def __init__(self):
        self.px = {}

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px[(x, y)] = c

    def put(self, x, y, c):
        self.px[(x, y)] = c

    def cut(self, *pts):
        for p in pts:
            self.px.pop(p, None)

    def image(self, details):
        im = Image.new("RGBA", (W, H), CLEAR)
        for (x, y) in list(self.px):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n not in self.px and 0 <= n[0] < W and 0 <= n[1] < H:
                    im.putpixel(n, LINE)
        for (x, y), c in self.px.items():
            if 0 <= x < W and 0 <= y < H:
                im.putpixel((x, y), c)
        for x, y, c in details:
            if 0 <= x < W and 0 <= y < H:
                im.putpixel((x, y), c)
        return im


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + (255,)


def body(cv, fur, shirt, stripe, frame):
    """몸통·팔·다리. frame 0~3 걷기 (1·3은 한 칸 들썩)"""
    bob = 1 if frame in (1, 3) else 0
    y0 = 17 - bob
    cv.rect(10, y0, 17, y0 + 6, shirt)                       # 티셔츠
    cv.rect(10, y0 + 3, 17, y0 + 3, stripe)                  # 줄무늬
    swing = [0, 1, 0, -1][frame]
    cv.rect(8, y0 + 1 - swing, 9, y0 + 4 - swing, shade(shirt, 0.8))   # 뒤팔
    cv.put(8, y0 + 5 - swing, shade(fur, 0.85))
    cv.rect(18, y0 + 1 + swing, 19, y0 + 4 + swing, shirt)  # 앞팔
    cv.put(19, y0 + 5 + swing, fur)
    step = [0, 1, 0, -1][frame]
    cv.rect(10 - step, y0 + 7, 12 - step, 29 - bob, PANTS)  # 뒷다리
    cv.rect(15 + step, y0 + 7, 17 + step, 29 - bob, shade(PANTS, 1.15))  # 앞다리
    return y0


def head(cv, fur, frame):
    bob = 1 if frame in (1, 3) else 0
    top = 4 - bob
    cv.rect(6, top, 21, top + 12, fur)
    cv.cut((6, top), (21, top), (6, top + 12), (21, top + 12))
    return top


def face(d, top, mood, blink, eyes=(14, 18), cheek=True):
    ey = top + 6
    for ex in eyes:
        if blink:
            d.append((ex, ey + 1, EYE))
        elif mood == "surprised":
            d += [(ex, ey - 1, EYE), (ex, ey, EYE), (ex, ey + 1, EYE)]
        elif mood == "happy":
            d += [(ex - 1, ey + 1, EYE), (ex, ey, EYE), (ex + 1, ey + 1, EYE)]
        else:
            d += [(ex, ey, EYE), (ex, ey + 1, EYE)]
    if cheek:
        d += [(eyes[0] - 2, ey + 3, PINK), (eyes[1] + 2, ey + 3, PINK)]
    mx = (eyes[0] + eyes[1]) // 2
    if mood == "talk":
        d += [(mx, ey + 4, MOUTH), (mx + 1, ey + 4, MOUTH), (mx, ey + 5, MOUTH), (mx + 1, ey + 5, PINK)]
    elif mood == "surprised":
        d += [(mx, ey + 4, MOUTH), (mx, ey + 5, MOUTH), (mx + 1, ey + 4, MOUTH), (mx + 1, ey + 5, MOUTH)]
    else:
        d += [(mx - 1, ey + 4, MOUTH), (mx, ey + 5, MOUTH), (mx + 1, ey + 5, MOUTH), (mx + 2, ey + 4, MOUTH)]


def cat(frame=0, mood="normal", blink=False):
    fur, shirt, stripe = (250, 240, 214, 255), (64, 120, 200, 255), (250, 250, 250, 255)   # 파란 줄무늬 티
    cv = Cv()
    body(cv, fur, shirt, stripe, frame)
    top = head(cv, fur, frame)
    cv.rect(7, top - 3, 9, top - 1, fur); cv.cut((7, top - 3))            # 귀
    cv.rect(18, top - 3, 20, top - 1, fur); cv.cut((20, top - 3))
    tail = [0, 1, 0, 1][frame]
    cv.rect(4, 19 - tail, 5, 24, fur); cv.rect(5, 24, 9, 25, fur)        # 꼬리
    d = [(8, top - 2, PINK), (19, top - 2, PINK)]
    face(d, top, mood, blink)
    return cv.image(d)


def dog(frame=0, mood="normal", blink=False):
    fur, shirt, stripe = (232, 178, 112, 255), (220, 70, 64, 255), (250, 220, 120, 255)   # 빨간 티 + 노란 줄
    ear = shade(fur, 0.72)
    cv = Cv()
    body(cv, fur, shirt, stripe, frame)
    top = head(cv, fur, frame)
    cv.rect(11, top + 8, 18, top + 12, (252, 236, 210, 255))             # 주둥이·턱 크림 (가운데 아래)
    cv.cut((11, top + 8), (18, top + 8))
    cv.rect(4, top + 1, 6, top + 7, ear)                                 # 늘어진 귀
    cv.rect(21, top + 1, 23, top + 7, ear)
    wag = [0, 1, 0, -1][frame]
    cv.rect(5 + wag, 18, 6 + wag, 21, fur); cv.rect(6, 21, 9, 22, fur)    # 흔드는 꼬리
    d = [(14, top + 8, EYE), (15, top + 8, EYE)]                         # 코 (가운데)
    face(d, top, mood, blink, eyes=(12, 17))
    return cv.image(d)


def lion(frame=0, mood="normal", blink=False):
    fur, mane, shirt, stripe = (248, 206, 110, 255), (214, 128, 56, 255), (70, 160, 110, 255), (250, 250, 250, 255)
    cv = Cv()
    bob = 1 if frame in (1, 3) else 0
    top = 4 - bob
    import math
    cx, cy, r = 13.5, top + 6.5, 10.4                                    # 둥근 갈기 + 삐죽한 끝
    for y in range(top - 5, top + 18):
        for x in range(1, 27):
            ang = math.atan2(y - cy, x - cx)
            rr = r + (1.2 if int((ang + math.pi) / (math.pi / 6)) % 2 == 0 else 0)
            if (x - cx) ** 2 + (y - cy) ** 2 <= rr * rr:
                if y <= top + 13:
                    cv.put(x, y, mane)
    body(cv, fur, shirt, stripe, frame)
    head(cv, fur, frame)
    cv.rect(6, top - 2, 7, top - 1, fur); cv.rect(20, top - 2, 21, top - 1, fur)   # 작은 귀
    cv.rect(3, 20, 4, 25, fur); cv.rect(2, 18, 5, 20, mane)              # 꼬리 털뭉치
    d = []
    face(d, top, mood, blink)
    return cv.image(d)


def horse(frame=0, mood="normal", blink=False):
    fur, mane, shirt, stripe = (196, 138, 92, 255), (100, 64, 48, 255), (240, 190, 60, 255), (250, 250, 250, 255)
    cv = Cv()
    body(cv, fur, shirt, stripe, frame)
    top = head(cv, fur, frame)
    cv.rect(10, top + 10, 17, top + 14, shade(fur, 1.18))                # 주둥이 (아래 가운데)
    cv.cut((10, top + 14), (17, top + 14))
    cv.rect(8, top - 4, 9, top - 1, fur); cv.rect(17, top - 4, 18, top - 1, fur)   # 쫑긋 귀
    cv.rect(12, top - 2, 14, top + 1, mane)                              # 앞머리 (작게)
    cv.rect(4, 18, 6, 26, mane)                                          # 꼬리
    d = [(12, top + 12, EYE), (15, top + 12, EYE)]                       # 콧구멍
    face(d, top - 1, mood, blink, eyes=(11, 16), cheek=False)
    return cv.image(d)


ANIMALS = {"cat": cat, "dog": dog, "lion": lion, "horse": horse}


def main(out, preview):
    os.makedirs(out, exist_ok=True)
    rows = []
    for name, fn in ANIMALS.items():
        walk = [fn(i) for i in range(4)]
        idle = [fn(0), fn(0, blink=True)]
        faces = [fn(0, "talk"), fn(0, "surprised"), fn(0, "happy")]
        for kind, frames in (("walk", walk), ("idle", idle), ("face", faces)):
            sheet = Image.new("RGBA", (W * len(frames), H), CLEAR)
            for i, f in enumerate(frames):
                sheet.alpha_composite(f, (i * W, 0))
            sheet.save(os.path.join(out, f"chibi_{name}_{kind}.png"))
        rows.append(walk + [idle[1]] + faces)
    S = 6
    n = len(rows[0])
    prev = Image.new("RGBA", ((W * S + 10) * n + 10, (H * S + 10) * len(rows) + 10), (128, 124, 134, 255))
    for r, frames in enumerate(rows):
        for i, f in enumerate(frames):
            prev.alpha_composite(f.resize((W * S, H * S), Image.NEAREST), (10 + i * (W * S + 10), 10 + r * (H * S + 10)))
    prev.save(preview)
    print("ok")


if __name__ == "__main__":
    main(*sys.argv[1:3])
