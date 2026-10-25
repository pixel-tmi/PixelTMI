"""
Kenney Pixel Vehicle Pack(CC0)의 차량 하나를 펫 스타일로 바꾸고 4프레임 주행 동작을 만든다.
사용: python 자동차_프레임만들기.py <차량.png> <출력 시트.png> <미리보기.png>
- 몸통: 회색 3단 음영 (참고: 회색 고양이 도트)
- 창문: 진회색 + 반짝 점 / 포인트: 빨간 미등, 노란 전조등
- 4프레임: 바퀴 반짝점 회전 + 차체 1px 통통 + 배기 연기
"""
import colorsys
import sys

from PIL import Image, ImageDraw

INK = (40, 42, 46, 255)
HI = (214, 218, 224, 255)
MID = (138, 144, 152, 255)
DARK = (96, 102, 110, 255)
GLASS = (58, 64, 72, 255)
GLINT = (236, 240, 244, 255)
RED = (232, 64, 48, 255)
YELLOW = (248, 192, 48, 255)
SMOKE = (190, 194, 200, 255)


def recolor(im):
    im = im.convert("RGBA")
    src = im.load()
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    px = out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = src[x, y]
            if a == 0:
                continue
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            lum = 0.3 * r + 0.59 * g + 0.11 * b
            if s < 0.25 and lum < 70:
                px[x, y] = INK
            elif s < 0.2 and lum > 200:
                px[x, y] = HI
            elif 0.5 < h < 0.7 and l > 0.6:
                px[x, y] = GLASS
            else:
                px[x, y] = MID if lum > 110 else DARK
    return out


def wheel_rows(im):
    """바퀴가 있는 아래쪽 행 범위 (INK가 몰린 곳)"""
    px = im.load()
    rows = [y for y in range(im.height) if sum(1 for x in range(im.width) if px[x, y] == INK) >= 4]
    return min(rows), im.height - 1


def accents(im):
    px = im.load()
    w, h = im.size
    # 창문 반짝점: 유리 덩어리마다 왼쪽 위 한 칸
    seen = set()
    for y in range(h):
        for x in range(w):
            if px[x, y] == GLASS and (x, y) not in seen:
                stack, blob = [(x, y)], []
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in seen or not (0 <= cx < w and 0 <= cy < h) or px[cx, cy] != GLASS:
                        continue
                    seen.add((cx, cy))
                    blob.append((cx, cy))
                    stack += [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]
                if len(blob) >= 3:
                    bx, by = min(blob, key=lambda p: (p[1], p[0]))
                    px[bx, by] = GLINT
    # 미등(맨 뒤 차체 중간 높이)·전조등(맨 앞)
    body = [(x, y) for y in range(h) for x in range(w) if px[x, y] in (MID, DARK, HI)]
    mid_y = sorted(y for _, y in body)[len(body) // 2]
    rear = min(x for x, y in body if abs(y - mid_y) <= 1)
    front = max(x for x, y in body if abs(y - mid_y) <= 1)
    for dy in (0, 1):
        if (rear, mid_y + dy) in body:
            px[rear, mid_y + dy] = RED
        if (front, mid_y - 1 + dy) in body:
            px[front, mid_y - 1 + dy] = YELLOW
    return im


def frames(base):
    w, h = base.size
    top_wheel, _ = wheel_rows(base)
    sheet_w = w + 4  # 왼쪽에 배기 연기 자리
    out = []
    for i in range(4):
        f = Image.new("RGBA", (sheet_w, h + 1), (0, 0, 0, 0))
        bounce = 1 if i % 2 == 1 else 0
        body = base.crop((0, 0, w, top_wheel))
        wheels = base.crop((0, top_wheel, w, h))
        f.alpha_composite(wheels, (4, top_wheel + 1))
        f.alpha_composite(body, (4, 1 - bounce))
        px = f.load()
        # 바퀴 반짝점 돌기: 바퀴 INK 덩어리의 위/오른쪽/아래/왼쪽 한 칸을 밝게
        for cx in range(4, sheet_w):
            pass
        cols = [x for x in range(4, sheet_w) if any(px[x, y] == INK for y in range(top_wheel + 1, h + 1))]
        groups, cur = [], []
        for x in cols:
            if cur and x != cur[-1] + 1:
                groups.append(cur)
                cur = []
            cur.append(x)
        if cur:
            groups.append(cur)
        for g in groups:
            if len(g) < 3:
                continue
            gx = g[len(g) // 2]
            ys = [y for y in range(top_wheel + 1, h + 1) if px[gx, y] == INK]
            if not ys:
                continue
            gy = (min(ys) + max(ys)) // 2
            spot = [(gx, gy - 1), (gx + 1, gy), (gx, gy + 1), (gx - 1, gy)][i]
            if 0 <= spot[0] < sheet_w and 0 <= spot[1] <= h and px[spot] == INK:
                px[spot] = SMOKE
        # 배기 연기 (뒤쪽, 프레임마다 위치 바뀜)
        d = ImageDraw.Draw(f)
        sy = h - 3
        puffs = [[(2, sy)], [(1, sy - 1), (3, sy)], [(0, sy - 2), (2, sy - 1)], [(1, sy - 2)]][i]
        for x, y in puffs:
            d.point((x, y), fill=SMOKE)
        out.append(f)
    return out


def main(src, sheet_path, preview_path):
    base = accents(recolor(Image.open(src)))
    fs = frames(base)
    fw, fh = fs[0].size
    sheet = Image.new("RGBA", (fw * 4, fh), (0, 0, 0, 0))
    for i, f in enumerate(fs):
        sheet.alpha_composite(f, (i * fw, 0))
    sheet.save(sheet_path)
    S = 10
    prev = Image.new("RGBA", (fw * 4 * S + 50, fh * S + 20), (255, 255, 255, 255))
    for i, f in enumerate(fs):
        prev.alpha_composite(f.resize((fw * S, fh * S), Image.NEAREST), (10 + i * (fw * S + 10), 10))
    prev.save(preview_path)
    print("frame", fw, fh)


if __name__ == "__main__":
    main(*sys.argv[1:4])
