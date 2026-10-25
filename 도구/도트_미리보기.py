"""
Sprites.kt 의 도트 그림을 한 장의 PNG로 그려 확인한다 (외부 라이브러리 없음).
사용: python 도트_미리보기.py <Sprites.kt> <출력.png>
"""
import re
import struct
import sys
import zlib

COLORS = {
    "k": (30, 30, 30), "w": (248, 248, 248), "g": (188, 188, 188), "m": (124, 124, 124),
    "r": (248, 56, 0), "y": (248, 184, 0), "p": (248, 164, 192), "b": (60, 188, 252), "n": (172, 124, 0),
}
BG = (210, 230, 210)
PX = 6
GAP = 4


def parse(path):
    src = open(path, encoding="utf-8").read()
    out = []
    for m in re.finditer(r"val (\w+) = (?:\w+ \+ )?listOf\((.*?)\n\s*\)", src, re.S):
        rows = re.findall(r'"([^"]*)"', m.group(2))
        if rows:
            out.append((m.group(1), rows))
    # timiTop + 바퀴 조합 펼치기
    top = next((r for n, r in out if n == "timiTop"), None)
    res = []
    for n, r in out:
        if n in ("TIMI_A", "TIMI_B") and top:
            r = top + r
        if n != "timiTop":
            res.append((n, r))
    return res


def png(path, w, h, pixels):
    raw = b"".join(b"\x00" + bytes(c for px in pixels[y * w:(y + 1) * w] for c in px) for y in range(h))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main(src, dst):
    sprites = parse(src)
    cols = 6
    cell_w = max(max(len(r) for r in rows) for _, rows in sprites) * PX + GAP * 2
    cell_h = max(len(rows) for _, rows in sprites) * PX + GAP * 2
    nrows = (len(sprites) + cols - 1) // cols
    W, H = cols * cell_w, nrows * cell_h
    pix = [BG] * (W * H)
    for i, (name, rows) in enumerate(sprites):
        ox, oy = (i % cols) * cell_w + GAP, (i // cols) * cell_h + GAP
        widths = {len(r) for r in rows}
        if len(widths) > 1:
            print("폭이 다른 줄:", name, sorted(widths))
        for ry, line in enumerate(rows):
            for rx, ch in enumerate(line):
                col = COLORS.get(ch)
                if not col:
                    continue
                for dy in range(PX):
                    for dx in range(PX):
                        x, y = ox + rx * PX + dx, oy + ry * PX + dy
                        if x < W and y < H:
                            pix[y * W + x] = col
    png(dst, W, H, pix)
    print("ok", [n for n, _ in sprites])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
