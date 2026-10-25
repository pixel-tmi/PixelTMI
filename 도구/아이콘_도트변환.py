"""
Pixelarticons SVG(24x24, 직각 경로) → 도트 글자 그림(k/.)으로 바꾼다.
사용: python 아이콘_도트변환.py <svg 폴더> <미리보기.png> <출력.kt>
"""
import os
import re
import sys

from PIL import Image, ImageChops, ImageDraw

S = 8  # 내부 확대 배율


def subpaths(d):
    toks = re.findall(r"[MmHhVvLlZz]|-?\d+(?:\.\d+)?", d)
    i, x, y = 0, 0.0, 0.0
    cur, out, start = [], [], (0.0, 0.0)
    cmd = None
    while i < len(toks):
        t = toks[i]
        if re.match(r"[A-Za-z]", t):
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    out.append(cur)
                cur = []
                x, y = start
            continue
        v = float(t)
        if cmd in "Mm":
            nx = float(toks[i]); ny = float(toks[i + 1]); i += 2
            if cmd == "m":
                nx += x; ny += y
            if cur:
                out.append(cur)
            x, y = nx, ny
            start = (x, y)
            cur = [(x, y)]
            cmd = "l" if cmd == "m" else "L"
            continue
        if cmd in "Ll":
            nx = float(toks[i]); ny = float(toks[i + 1]); i += 2
            if cmd == "l":
                nx += x; ny += y
            x, y = nx, ny
        elif cmd == "H":
            x = v; i += 1
        elif cmd == "h":
            x += v; i += 1
        elif cmd == "V":
            y = v; i += 1
        elif cmd == "v":
            y += v; i += 1
        else:
            i += 1
            continue
        cur.append((x, y))
    if cur:
        out.append(cur)
    return out


def raster(svg_path):
    src = open(svg_path, encoding="utf-8").read()
    mask = Image.new("1", (24 * S, 24 * S), 0)
    for d in re.findall(r'd="([^"]+)"', src):
        for poly in subpaths(d):
            if len(poly) < 3:
                continue
            m = Image.new("1", mask.size, 0)
            ImageDraw.Draw(m).polygon([(px * S, py * S) for px, py in poly], fill=1)
            mask = ImageChops.logical_xor(mask, m)
    rows = []
    for r in range(24):
        rows.append("".join("k" if mask.getpixel((c * S + S // 2, r * S + S // 2)) else "." for c in range(24)))
    return rows


def main(folder, preview, kt):
    names = sorted(f[:-4] for f in os.listdir(folder) if f.endswith(".svg"))
    grids = {n: raster(os.path.join(folder, n + ".svg")) for n in names}
    # 미리보기
    P, cols = 6, 7
    cell = 24 * P + 16
    img = Image.new("RGB", (cols * cell, ((len(names) + cols - 1) // cols) * (cell + 14)), (230, 230, 230))
    dr = ImageDraw.Draw(img)
    for i, n in enumerate(names):
        ox, oy = (i % cols) * cell + 8, (i // cols) * (cell + 14) + 18
        dr.text((ox, oy - 14), n, fill=(0, 0, 0))
        for r, line in enumerate(grids[n]):
            for c, ch in enumerate(line):
                if ch == "k":
                    dr.rectangle([ox + c * P, oy + r * P, ox + c * P + P - 1, oy + r * P + P - 1], fill=(30, 30, 30))
    img.save(preview)
    # Kotlin
    def ident(n):
        return n.upper().replace("-", "_")
    lines = ["package kr.incar.base.ui.pixel", "", "/**", " * Pixelarticons (MIT, Gerrit Halfmann) 24x24 아이콘을 도트 글자 그림으로 변환한 것.",
             " * 라이선스: assets/licenses/Pixelarticons_MIT.txt · 생성: 베이스앱\\\\도구\\\\아이콘_도트변환.py", " */", "object Icons {"]
    for n in names:
        lines.append(f"    val {ident(n)} = listOf(")
        for row in grids[n]:
            lines.append(f'        "{row}",')
        lines.append("    )")
    lines.append("}")
    open(kt, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("ok", len(names))


if __name__ == "__main__":
    main(*sys.argv[1:4])
