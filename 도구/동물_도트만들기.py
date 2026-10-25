"""
Pixel TMI 캐릭터 4종(고양이·강아지·사자·말) 도트 만들기.
스타일: 네모난 몸통 + 검정 1px 외곽선 + 한 가지 털색 + 점 눈 + 분홍 볼.
그림을 베끼지 않고 도형(사각형)을 조립한 뒤 외곽선을 자동으로 두른다.
사용: python 동물_도트만들기.py <출력 폴더> <미리보기.png>
출력: <동물>_walk.png (4프레임 가로 시트), <동물>_idle.png (2프레임: 기본·눈 깜빡)
"""
import os
import sys

from PIL import Image

W, H = 36, 26
INK = (34, 34, 42, 255)
PINK = (240, 140, 160, 255)
EYE = (20, 20, 26, 255)
CLEAR = (0, 0, 0, 0)


class Canvas:
    def __init__(self):
        self.px = {}

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px[(x, y)] = c

    def dot(self, x, y, c):
        self.px[(x, y)] = c

    def clear(self, x, y):
        self.px.pop((x, y), None)

    def image(self, details=()):
        im = Image.new("RGBA", (W, H), CLEAR)
        fill = dict(self.px)
        # 외곽선: 채워진 칸 옆(상하좌우)의 빈칸을 검정으로
        for (x, y) in list(fill):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n not in fill and 0 <= n[0] < W and 0 <= n[1] < H:
                    im.putpixel(n, INK)
        for (x, y), c in fill.items():
            if 0 <= x < W and 0 <= y < H:
                im.putpixel((x, y), c)
        for (x, y, c) in details:
            im.putpixel((x, y), c)
        return im


def legs(cv, xs, top, bottom, lift, color):
    """다리 4개. lift = 들어 올린 다리 번호 집합 (걷기 프레임)"""
    for i, x in enumerate(xs):
        b = bottom - (1 if i in lift else 0)
        cv.rect(x, top, x + 1, b, color)


def face(details, ex, ey, blink=False, blush=True):
    """두 눈(앞에서 보이는 3/4 얼굴) + 볼"""
    for x in (ex, ex + 4):
        if blink:
            details.append((x, ey + 1, EYE))
        else:
            details.append((x, ey, EYE))
            details.append((x, ey + 1, EYE))
    if blush:
        details.append((ex - 1, ey + 2, PINK))
        details.append((ex + 5, ey + 2, PINK))


# ── 동물별 설계 ──

def cat(frame, blink=False):
    fur = (150, 156, 170, 255)        # 밝은 회색 (표본보다 밝게 → 다른 고양이)
    cv = Canvas()
    lift = [set(), {0, 2}, set(), {1, 3}][frame]
    sway = [0, 0, -1, -1][frame]
    cv.rect(7, 12, 23, 18, fur)                       # 몸통
    cv.rect(20, 5, 29, 14, fur)                       # 머리
    for p in ((20, 5), (29, 5)):
        cv.clear(*p)
    cv.rect(21, 2, 22, 4, fur); cv.dot(21, 1, fur)    # 귀
    cv.rect(27, 2, 28, 4, fur); cv.dot(28, 1, fur)
    cv.rect(4 + sway, 4, 5 + sway, 13, fur)           # 꼬리 (위로)
    cv.rect(5, 12, 7, 13, fur)
    legs(cv, (8, 11, 18, 21), 19, 22, lift, fur)
    d = []
    face(d, 23, 9, blink)
    d.append((25, 11, PINK))                          # 코
    d.append((26, 11, PINK))
    # 노란 방울 목걸이 → 표본과 구분되는 포인트
    for x in range(21, 29):
        d.append((x, 14, (230, 70, 60, 255)))
    d.append((25, 15, (250, 200, 60, 255)))
    return cv.image(d)


def dog(frame, blink=False):
    fur = (226, 166, 96, 255)         # 시바 같은 황토색
    cream = (250, 236, 210, 255)
    cv = Canvas()
    lift = [set(), {0, 2}, set(), {1, 3}][frame]
    wag = [0, 1, 0, -1][frame]
    cv.rect(7, 12, 23, 18, fur)
    cv.rect(10, 16, 21, 18, cream)                    # 배
    cv.rect(20, 6, 29, 14, fur)                       # 머리
    cv.rect(29, 10, 31, 13, cream)                    # 주둥이
    cv.clear(20, 6); cv.clear(29, 6)
    cv.rect(21, 3, 23, 5, fur); cv.clear(21, 3)       # 귀
    cv.rect(26, 3, 28, 5, fur); cv.clear(28, 3)
    cv.rect(23, 11, 28, 14, cream)                    # 볼·턱
    # 말린 꼬리
    cv.rect(4, 7 + wag, 6, 8 + wag, fur)
    cv.rect(4, 9, 5, 12, fur)
    cv.rect(5, 12, 7, 13, fur)
    legs(cv, (8, 11, 18, 21), 19, 22, lift, fur)
    d = []
    face(d, 23, 9, blink)
    d.append((31, 10, EYE))                           # 코끝
    return cv.image(d)


def lion(frame, blink=False):
    fur = (236, 186, 80, 255)         # 금빛
    mane = (196, 112, 48, 255)        # 갈기
    cv = Canvas()
    lift = [set(), {0, 2}, set(), {1, 3}][frame]
    sway = [0, 0, -1, -1][frame]
    cv.rect(7, 12, 23, 18, fur)
    cv.rect(18, 3, 31, 16, mane)                      # 갈기 (머리보다 크게)
    for p in ((18, 3), (31, 3), (18, 16), (31, 16), (19, 3), (30, 3)):
        cv.clear(*p)
    cv.rect(20, 5, 29, 14, fur)                       # 얼굴
    cv.clear(20, 5); cv.clear(29, 5)
    cv.rect(4 + sway, 6, 5 + sway, 13, fur)           # 꼬리
    cv.rect(3 + sway, 4, 6 + sway, 6, mane)           # 꼬리 끝 털뭉치
    cv.rect(5, 12, 7, 13, fur)
    legs(cv, (8, 11, 18, 21), 19, 22, lift, fur)
    d = []
    face(d, 23, 9, blink)
    d.append((25, 11, PINK)); d.append((26, 11, PINK))
    return cv.image(d)


def horse(frame, blink=False):
    fur = (176, 120, 80, 255)         # 밤색
    mane = (90, 60, 44, 255)
    cv = Canvas()
    lift = [set(), {0, 2}, set(), {1, 3}][frame]
    sway = [0, 1, 0, -1][frame]
    cv.rect(6, 10, 24, 16, fur)                       # 몸통 (높게)
    cv.rect(21, 4, 25, 12, fur)                       # 목
    cv.rect(22, 1, 31, 7, fur)                        # 머리 (길쭉)
    cv.rect(30, 4, 32, 7, fur)                        # 주둥이
    cv.clear(22, 1); cv.clear(31, 1)
    cv.rect(23, 0, 24, 0, fur)                        # 귀
    cv.rect(20, 2, 21, 10, mane)                      # 갈기
    cv.rect(2 + sway, 11, 4 + sway, 19, mane)         # 꼬리 (아래로)
    cv.rect(4, 10, 6, 12, mane)
    legs(cv, (7, 10, 20, 23), 17, 24, lift, fur)
    d = []
    for x in (26,):                                   # 말은 옆얼굴 → 눈 하나
        if blink:
            d.append((x, 4, EYE))
        else:
            d.append((x, 3, EYE)); d.append((x, 4, EYE))
    d.append((25, 6, PINK))
    d.append((32, 6, EYE))                            # 콧구멍
    for y in (17, 18):                                # 발굽 (다리 끝 진하게)
        pass
    return cv.image(d)


ANIMALS = {"cat": cat, "dog": dog, "lion": lion, "horse": horse}


def main(out, preview):
    os.makedirs(out, exist_ok=True)
    rows = []
    for name, fn in ANIMALS.items():
        walk = [fn(i) for i in range(4)]
        idle = [fn(0), fn(0, blink=True)]
        for kind, frames in (("walk", walk), ("idle", idle)):
            sheet = Image.new("RGBA", (W * len(frames), H), CLEAR)
            for i, f in enumerate(frames):
                sheet.alpha_composite(f, (i * W, 0))
            sheet.save(os.path.join(out, f"{name}_{kind}.png"))
        rows.append(walk + idle)
    S = 6
    prev = Image.new("RGBA", ((W * S + 12) * 6 + 12, (H * S + 12) * len(rows) + 12), (255, 255, 255, 255))
    for r, frames in enumerate(rows):
        for i, f in enumerate(frames):
            prev.alpha_composite(f.resize((W * S, H * S), Image.NEAREST), (12 + i * (W * S + 12), 12 + r * (H * S + 12)))
    prev.save(preview)
    print("ok", list(ANIMALS))


if __name__ == "__main__":
    main(*sys.argv[1:3])
