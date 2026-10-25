"""
Pixel TMI 할로윈 캐릭터 행동 시트 — 유령(ghost) · 호박 잭(pumpkin) · 마녀 고양이(witch).
할로윈_캐릭터.py 의 몸·색·얼굴 부품을 그대로 가져와(import) 행동마다 진짜 프레임을 새로 그린다.
(원본 생성기는 건드리지 않는다 — 기본 시트 walk/run/idle/face 는 그쪽에서 만든다)

앱 약속: 행동 <act> 를 하는 동안 pet/<id>_<act>.png 가 있으면 그 시트를 재생
         (왼쪽→오른쪽 약 200ms 마다. 3장짜리 '한 번' 행동은 순서대로 한 번 → 마지막 장 유지, 2장은 반복).
         앱이 회전·이동·크기 변화는 따로 주므로 그림은 캐릭터 자신의 자세·표정만 바꾼다.
규칙: 한 프레임 34×24 · 투명 · 오른쪽을 본다 · 기본 시트와 같은 크기·바닥선 · 좌우 1칸 여백 (x=0·33 비움)
      몸은 자동 1칸 외곽선, 효과(반짝이·서리·먼지·소리선)는 외곽선 없이 맨 앞(top)에.

  유령   ghost_boo      3장(한 번) 보통 → 팔 들고 입 벌림 → 큰 "왁!" 얼굴 (눈 동그랗게)
         ghost_peekaboo 3장(한 번) 두 손으로 눈 가림 → 손가락 사이로 빼꼼 → 손 활짝 + 활짝 웃음
         ghost_chill    2장(반복) 볼 빵빵 → 후우~ 서리 입김 (하늘색 김 + 작은 눈송이)
         ghost_wisp     2장(반복) 두 손에 파란 도깨비불, 얼굴이 아래에서 비친다 (불꽃 일렁)
  호박 잭 pumpkin_grin   2장(반복) 활짝 웃는 얼굴(촛불 환하게) / 윙크
         pumpkin_seeds  2장(반복) 입 벌려 호박씨 퉤! / 입 다물고 오물오물
         pumpkin_bounce 2장(반복) 착지 찌그러짐 / 공중에서 쭉 늘어남 (꼭지 까딱)
         pumpkin_glow   2장(반복) 눈·입이 뜨거운 주황노랑으로 이글 / 은은하게
  마녀 고양이 witch_sweep  2장(반복) 땅에 서서 빗자루로 왼쪽·오른쪽 싹싹 + 먼지
         witch_potion   2장(반복) 보글보글 물약병, 보라·초록 거품이 올라감
         witch_hattip   3장(한 번) 모자 챙에 손 → 모자 들어 꾸벅 → 윙크
         witch_sparkle  2장(반복) 요술봉 번쩍, 끝에서 별 반짝

사용: python 할로윈_행동시트.py <출력 폴더> [미리보기.png] [--덮어쓰기]
      이미 있는 파일은 건너뛴다 (--덮어쓰기 를 주면 새로 쓴다).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import 할로윈_캐릭터 as base  # noqa: E402
from 할로윈_캐릭터 import (  # noqa: E402
    W, H, CLEAR, SHINE, rnd, shade, alpha, Cv, columns,
    ghost_bell, ghost_paint, ghost_translucent,
    G_LINE, G_BODY, G_HI, G_SH, G_SH2, G_EYE, G_EYE2, G_BLUSH, G_MOUTH, G_TONGUE, G_FACE_X, G_FACE_Y,
    pumpkin_legs, pumpkin_body,
    P_LINE, P_OR, P_HI, P_RIB, P_DK, P_CARVE, P_GLOW, P_GLOW2, P_CORE, P_STEM, P_STEM_HI, P_STEM_TIP,
    P_VINE, P_LEAF, P_LEAF_DK, P_EYES, P_MOUTHS,
    C_LINE, C_FUR, C_FAR, C_RIM, C_LIGHT, C_EYE, C_COLLAR, C_BELL, C_BELL_DK,
    WOOD, WOOD_HI, STRAW, STRAW_DK, STRAW_HI, TIE, HAT_HI, HAT_DK, STAR, STAR_CORE, W_HX, W_TOP,
    cat_head, cat_face, witch_hat, star_fx, sparkles,
)

# ── 공통 효과 색 ──────────────────────────────────────────────────────
ACT_LINE = (150, 162, 186, 255)       # 소리선·움직임 자국 (흰 바탕·어두운 바탕 둘 다 보이는 회청색)
STAR_EDGE = (246, 140, 36, 255)
STAR_FILL = (255, 222, 70, 255)
STAR_WHITE = (255, 255, 236, 255)
DUST = (226, 214, 190, 220)           # 흙먼지 (반투명)
DUST_EDGE = (170, 152, 124, 200)
FROST = (190, 234, 255, 235)          # 서리 입김
FROST_EDGE = (110, 178, 230, 235)
FROST_HI = (240, 252, 255, 255)
SNOW = (150, 212, 252, 255)


def blend_px(im, x, y, c):
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


class Cv2(Cv):
    """할로윈 Cv + top(맨 앞 효과, 외곽선 없음) + props(외곽선 색이 다른 소품: 몸 위에 따로 얹음)"""

    def __init__(self, line):
        super().__init__(line)
        self.top = {}
        self.props = []

    def overlay(self, o, line=None, edge=True):
        super().overlay(o, line, edge)
        self.top.update(getattr(o, "top", {}))

    def image(self, dx=0, dy=0):
        im = super().image(dx, dy)
        for p in self.props:
            im.alpha_composite(p.image(dx, dy))
        for (x, y), c in self.top.items():
            blend_px(im, x + dx, y + dy, c)
        return im


def moved(src, dx=0, dy=0):
    out = Cv2(src.line)
    for name in ("px", "dt", "fx", "top"):
        getattr(out, name).update({(x + dx, y + dy): c for (x, y), c in getattr(src, name, {}).items()})
    return out


def rotated(src, ang, pivot):
    """캔버스 통째 회전 (+ = 화면 시계 방향). 가장 가까운 칸 뽑기 — 구멍 없이 채워짐"""
    out = Cv2(src.line)
    layers = ("px", "dt", "fx", "top")
    pts = [p for name in layers for p in getattr(src, name, {})]
    if not pts:
        return out
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    px0, py0 = pivot
    R = max(math.hypot(x - px0, y - py0) for x, y in pts) + 2
    for ty in range(int(py0 - R) - 1, int(py0 + R) + 2):
        for tx in range(int(px0 - R) - 1, int(px0 + R) + 2):
            ddx, ddy = tx - px0, ty - py0
            k = (rnd(px0 + ddx * ca + ddy * sa), rnd(py0 - ddx * sa + ddy * ca))
            for name in layers:
                L = getattr(src, name, {})
                if k in L:
                    getattr(out, name)[(tx, ty)] = L[k]
    return out


def tiny_star(cv, x, y, size=1):
    """반짝 별 (맨 앞). size 0 = 점 · 1 = + · 2 = 큰 네 갈래(주황 테)"""
    T = cv.top
    if size >= 2:
        for k in (1, 2):
            for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
                T[(x + dx, y + dy)] = STAR_FILL if k == 1 else STAR_EDGE
        T[(x, y)] = STAR_WHITE
    elif size == 1:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            T[(x + dx, y + dy)] = STAR_FILL
        T[(x, y)] = STAR_WHITE
    else:
        T[(x, y)] = STAR_FILL


def puff(cv, cx, cy, r, fill, edge, hi=None, to="top"):
    """둥근 김·먼지 덩이 (테두리 진하게, 왼쪽 위 밝게)"""
    L = getattr(cv, to)
    cells = [(x, y) for y in range(int(cy - r) - 1, int(cy + r) + 2) for x in range(int(cx - r) - 1, int(cx + r) + 2)
             if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.3]
    s = set(cells)
    for (x, y) in cells:
        rim = any(n not in s for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
        L[(x, y)] = edge if rim else fill
    if hi and r >= 1.4:
        L[(rnd(cx - r * 0.35), rnd(cy - r * 0.35))] = hi


def dust_cloud(cv, cx, cy, r):
    """흙먼지 구름: 연한 베이지 덩이, 아랫단만 진하게 (테두리 고리처럼 보이지 않게)"""
    cells = [(x, y) for y in range(int(cy - r) - 1, int(cy + r) + 2) for x in range(int(cx - r) - 1, int(cx + r) + 2)
             if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 0.3 and 1 <= x <= 32]
    s = set(cells)
    for (x, y) in cells:
        cv.top[(x, y)] = DUST_EDGE if (x, y + 1) not in s else DUST
    if r >= 1.4:
        cv.top[(rnd(cx - r * 0.4), rnd(cy - r * 0.4))] = (248, 242, 228, 235)


def check_margin(name, frames):
    bad = []
    for k, f in enumerate(frames):
        a = f.getchannel("A")
        if any(a.getpixel((0, y)) or a.getpixel((W - 1, y)) for y in range(H)):
            bad.append(k)
    if bad:
        print(f"  !! 여백 침범: {name} 프레임 {bad}")
    return not bad


# ══════════════════════════════════════════════════════════════════════
# 1) 유령
# ══════════════════════════════════════════════════════════════════════
G_CX, G_CY = 21.5, 9.0
G_IN = (62, 22, 54, 255)              # 크게 벌린 입 속
G_LIT = (206, 244, 255, 255)          # 도깨비불에 비친 얼굴 (아래쪽)
G_LIT2 = (150, 226, 248, 255)
WISP_LINE = (22, 74, 128, 255)
WISP_OUT = (52, 168, 226, 255)
WISP_MID = (120, 224, 250, 255)
WISP_CORE = (232, 252, 255, 255)


def g_body(**kw):
    cv = Cv2(G_LINE)
    args = dict(lean=0.0, phase=0.0, bottom=19.2, amp=1.2)
    args.update(kw)
    pts = ghost_bell(G_CX, G_CY, **args)
    ghost_paint(cv, pts, G_CX, G_CY)
    return cv, pts


def g_limb(segs, hand=(), fingers=(), w=2):
    """팔 한 짝 (몸색). segs = 꺾은선, hand = 손 칸들, fingers = 손가락 칸들. 아랫면 그늘"""
    a = Cv2(G_LINE)
    for p, q in zip(segs, segs[1:]):
        a.line_(p[0], p[1], q[0], q[1], G_BODY, w=w)
    for p in tuple(hand) + tuple(fingers):
        a.px[p] = G_BODY
    for (x, y) in list(a.px):
        if (x, y + 1) not in a.px:
            a.dt[(x, y)] = G_SH
    return a


def g_attach(cv, arm, over=False):
    """over=False: 몸 밖으로 뻗은 팔 (실루엣이 이어짐) · True: 몸 앞을 지나는 팔 (경계선을 그어 모양을 살림)"""
    if over:
        cv.overlay(arm, edge=True)
    else:
        for p, c in arm.px.items():
            cv.px[p] = c
            cv.dt.pop(p, None)
        cv.dt.update(arm.dt)


def g_eyes(cv, kind="normal"):
    d = cv.dt
    ey = G_FACE_Y
    for i, x0 in enumerate(G_FACE_X):
        if kind == "happy":
            d[(x0, ey + 2)] = G_EYE; d[(x0 + 1, ey + 1)] = G_EYE; d[(x0 + 2, ey + 2)] = G_EYE
        elif kind == "squeeze":                       # > <  (힘껏 불기)
            if i == 0:
                d[(x0, ey)] = G_EYE; d[(x0 + 1, ey + 1)] = G_EYE; d[(x0 + 2, ey + 1)] = G_EYE; d[(x0, ey + 2)] = G_EYE
            else:
                d[(x0 + 2, ey)] = G_EYE; d[(x0 + 1, ey + 1)] = G_EYE; d[(x0, ey + 1)] = G_EYE; d[(x0 + 2, ey + 2)] = G_EYE
        else:
            rows = {
                "normal": (ey, [".D.", "DSD", "DDD", ".B."]),
                "wide": (ey - 1, [".D.", "DSD", "DDD", "DDD", ".B."]),
                "boo": (ey - 1, ["DDD", "DSD", "DDD", "DDD", ".D."]),
                "lit": (ey, [".D.", "DDD", "DSD", ".C."]),
                "side": (ey, [".D.", "DDS", "DDD", ".B."]),
            }[kind]
            y0, rr = rows
            for dy, row in enumerate(rr):
                for dx, ch in enumerate(row):
                    if ch != ".":
                        d[(x0 + dx, y0 + dy)] = {"D": G_EYE, "S": SHINE, "B": G_EYE2, "C": G_LIT2}[ch]
    if kind == "boo":                                 # 장난꾸러기 V 눈썹
        for p in ((18, 4), (19, 4), (20, 4), (21, 5), (24, 5), (25, 4), (26, 4), (27, 4)):
            d[p] = G_EYE


def g_blush(cv, big=False):
    ey = G_FACE_Y
    bx0, bx1 = G_FACE_X[0] - 2, G_FACE_X[1] + 3
    for x in (bx0, bx0 + 1, bx1, bx1 + 1):
        cv.dt[(x, ey + 3)] = G_BLUSH
    if big:
        for x in (bx0, bx0 + 1, bx1, bx1 + 1):
            cv.dt[(x, ey + 4)] = G_BLUSH
        cv.dt[(bx1 + 2, ey + 3)] = G_BLUSH


def g_mouth(cv, kind="w"):
    d = cv.dt
    mx, my = G_FACE_X[0] + 3, G_FACE_Y + 4          # (22, 11)
    M, T, I = G_MOUTH, G_TONGUE, G_IN
    if kind == "w":
        d[(mx - 1, my)] = M; d[(mx + 2, my)] = M; d[(mx, my + 1)] = M; d[(mx + 1, my + 1)] = M
    elif kind == "o":                                  # 작게 벌린 입
        rows = [".MM.", "MIIM", ".MM."]
        cv.art(mx - 1, my, rows, {"M": M, "I": I})
    elif kind == "boo":                                # 크게 벌린 '왁!' 입
        rows = [".MMMM.", "MIIIIM", "MIIIIM", "MITTIM", ".MMMM."]
        cv.art(mx - 2, my, rows, {"M": M, "I": I, "T": T})
    elif kind == "grin":                               # 활짝 웃는 D 입
        rows = ["MMMMMM", ".MTTM.", "..MM.."]
        cv.art(mx - 2, my, rows, {"M": M, "T": T})
    elif kind == "pursed":                             # 앞쪽으로 오므린 '후' 입
        rows = [".M.", "MIM", ".M."]
        cv.art(mx + 3, my, rows, {"M": M, "I": I})
    elif kind == "spooky":                             # 도깨비불 앞 으스스 미소
        rows = ["M....M", ".MIIM."]
        cv.art(mx - 2, my, rows, {"M": M, "I": I})


def g_finish(cv, pts, dy=0):
    ghost_translucent(cv, pts)
    return cv.image(dy=dy)


def g_art_limb(rows, x0, y0):
    """글자 그림 팔: o = 몸색 · s = 그늘 · h = 밝은 윗면"""
    a = Cv2(G_LINE)
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch in "osh":
                p = (x0 + dx, y0 + dy)
                a.px[p] = G_BODY
                if ch == "s":
                    a.dt[p] = G_SH
                elif ch == "h":
                    a.dt[p] = G_HI
    return a


def ghost_boo(i):
    if i == 0:          # 보통: 팔을 살짝 내려 힘 모으기, 장난스러운 미소
        cv, pts = g_body()
        g_attach(cv, g_limb([(29, 13), (30, 14)], hand=[(31, 14), (31, 13)]))
        g_attach(cv, g_limb([(13, 13), (12, 14)], hand=[(11, 14), (11, 13)]))
        g_eyes(cv, "normal"); g_blush(cv); g_mouth(cv, "w")
        return g_finish(cv, pts)
    if i == 1:          # 팔 들어 올리는 중 (손이 어깨 높이), 눈 커지고 입이 열린다
        cv, pts = g_body(bottom=19.0, amp=1.3)
        g_attach(cv, g_art_limb(["hh.",
                                 "oos",
                                 ".os",
                                 ".os",
                                 ".s."], 29, 7), over=True)
        g_attach(cv, g_art_limb([".hh",
                                 "soo",
                                 "so.",
                                 "so.",
                                 ".s."], 11, 7), over=True)
        g_eyes(cv, "wide"); g_blush(cv); g_mouth(cv, "o")
        return g_finish(cv, pts)
    # 왁!: 두 팔 번쩍 (손가락 쫙 — 머리 옆에 경계선으로 떨어져 보이게), 눈 동그랗게 + 장난 눈썹, 입 크게, 밑단 펄럭
    cv, pts = g_body(bottom=19.6, amp=1.6, period=4.6, phase=1.0)
    g_attach(cv, g_art_limb([".hh",
                             "hoo",
                             "ooo",
                             "sos",
                             ".os",
                             ".os",
                             ".os",
                             "os.",
                             "s.."], 29, 3), over=True)
    g_attach(cv, g_art_limb(["hh.",
                             "ooh",
                             "ooo",
                             "sos",
                             "so.",
                             "so.",
                             "so.",
                             ".so",
                             "..s"], 11, 3), over=True)
    g_eyes(cv, "wide")
    for p in ((18, 4), (19, 4), (20, 5), (25, 5), (26, 4), (27, 4)):      # 장난꾸러기 눈썹
        cv.dt[p] = G_EYE
    g_blush(cv, big=True); g_mouth(cv, "boo")
    return g_finish(cv, pts)


G_FINGER = (120, 122, 166, 255)       # 손가락 사이 틈


def g_hand(x0, y0, slot=False):
    """눈을 가리는 손 (5×5): 손끝 세 개가 위로 · 손가락 사이 진한 틈 · 아래는 손바닥.
    slot = 손가락을 벌려 가운데 세 칸이 비고 그 틈으로 눈이 보인다"""
    rows = ["h.h.h",
            "ofofo",
            "ofofo",
            "ooooo",
            ".sss."]
    a = Cv2(G_LINE)
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            p = (x0 + dx, y0 + dy)
            if ch in "ohsf":
                a.px[p] = G_BODY
                a.dt[p] = {"o": G_BODY, "h": G_HI, "s": G_SH, "f": G_FINGER}[ch]
    if slot:
        for dx, dy in [(2, 0)] + [(dx, dy) for dx in (1, 2, 3) for dy in (1, 2, 3)]:
            a.px.pop((x0 + dx, y0 + dy), None)
            a.dt.pop((x0 + dx, y0 + dy), None)
    return a


def ghost_peekaboo(i):
    cv, pts = g_body()
    if i < 2:
        # 두 손으로 눈 가림 — 손이 몸 앞을 지나므로 경계선을 그어 모양을 살린다 (팔뚝은 아래 바깥으로)
        g_attach(cv, g_limb([(16, 11), (14, 13)]), over=True)
        g_attach(cv, g_limb([(27, 11), (29, 13)]), over=True)
        g_attach(cv, g_hand(17, 6), over=True)
        g_attach(cv, g_hand(23, 6, slot=(i == 1)), over=True)
        if i == 1:      # 빼꼼: 앞손 손가락이 벌어져 그 틈으로 눈이 반짝
            for p_, c_ in (((25, 6), G_BODY), ((24, 7), G_BODY), ((25, 7), G_EYE), ((26, 7), G_BODY),
                           ((24, 8), G_EYE), ((25, 8), SHINE), ((26, 8), G_EYE),
                           ((24, 9), G_EYE), ((25, 9), G_EYE), ((26, 9), G_EYE)):
                cv.dt[p_] = c_
        g_blush(cv)
        g_mouth(cv, "w")
        if i == 1:
            tiny_star(cv, 30, 3, 0)
        return g_finish(cv, pts)
    # 까꿍!: 두 팔 활짝 펼치고 (손바닥 쫙) 활짝 웃음
    g_attach(cv, g_limb([(29, 11), (30, 9)], hand=[(31, 9), (31, 8), (30, 8)], fingers=[(31, 7), (29, 7)]))
    g_attach(cv, g_limb([(13, 11), (12, 9)], hand=[(11, 9), (11, 8), (12, 8)], fingers=[(11, 7), (13, 7)]))
    g_eyes(cv, "normal"); g_blush(cv, big=True); g_mouth(cv, "grin")
    tiny_star(cv, 30, 4, 1); tiny_star(cv, 12, 3, 1); tiny_star(cv, 32, 11, 0)
    return g_finish(cv, pts, dy=-1)


def snowflake(cv, x, y, big):
    if big:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cv.top[(x + dx, y + dy)] = SNOW
        cv.top[(x, y)] = SHINE
    else:
        cv.top[(x, y)] = SNOW


def ghost_chill(i):
    """0 = 볼 빵빵 (숨 머금기) · 1 = 후우~ 서리 입김. 둘을 번갈아 → 후! 후! 차가운 입김"""
    cv, pts = g_body()
    if i == 0:
        for p in ((30, 9), (30, 10), (30, 11), (30, 12), (12, 9), (12, 10), (12, 11), (12, 12)):   # 볼이 양옆으로 부풂
            cv.px[p] = G_BODY
        cv.dt[(12, 12)] = G_SH; cv.dt[(12, 11)] = G_SH
        g_attach(cv, g_limb([(29, 14), (30, 15)], hand=[(31, 15)]))
        g_attach(cv, g_limb([(13, 14), (12, 15)], hand=[(11, 15)]))
        g_eyes(cv, "squeeze")
        for x in (16, 17, 18, 27, 28, 29):                       # 빵빵한 볼 = 큰 볼터치
            cv.dt[(x, 10)] = G_BLUSH; cv.dt[(x, 11)] = G_BLUSH
        cv.dt[(22, 12)] = G_MOUTH; cv.dt[(23, 12)] = G_MOUTH; cv.dt[(24, 12)] = G_MOUTH   # 꾹 다문 입
        snowflake(cv, 31, 4, False); snowflake(cv, 29, 1, False)  # 남은 눈송이
    else:
        g_attach(cv, g_limb([(29, 13), (30, 14)], hand=[(31, 14)]))
        g_attach(cv, g_limb([(13, 13), (12, 14)], hand=[(11, 14)]))
        g_eyes(cv, "squeeze")
        g_blush(cv)
        cv.art(24, 11, ["MM", "MM"], {"M": G_MOUTH})                          # 오므린 '후' 입
        # 서리 입김: 입에서 앞으로 점점 커지며 퍼지는 하늘색 김 + 작은 눈송이
        puff(cv, 27.4, 12.2, 0.9, FROST, FROST_EDGE)
        puff(cv, 29.6, 11.6, 1.3, FROST, FROST_EDGE, FROST_HI)
        puff(cv, 31.2, 13.8, 1.0, FROST, FROST_EDGE)
        puff(cv, 31.4, 9.4, 0.8, FROST, FROST_EDGE)
        snowflake(cv, 29, 6, True); snowflake(cv, 31, 17, True); snowflake(cv, 32, 3, False); snowflake(cv, 27, 16, False)
    return g_finish(cv, pts)


def wisp_flame(i):
    """도깨비불: 동그란 밑동 + 일렁이는 끝 (프레임마다 끝이 좌우로) · 바깥 파랑 → 안 하늘 → 속 하양"""
    f = Cv2(WISP_LINE)
    if i == 0:
        rows = ["....X",
                "...XX",
                "..XXX",
                ".XXXX",
                "XXXXX",
                "XXXXX",
                ".XXX."]
    else:
        rows = [".X...",
                ".XX..",
                "XXXX.",
                "XXXXX",
                "XXXXX",
                "XXXXX",
                ".XXX."]
    x0, y0 = 27, 7
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == "X":
                f.px[(x0 + dx, y0 + dy)] = WISP_OUT
    for (x, y) in list(f.px):
        if all(n in f.px for n in ((x + 1, y), (x - 1, y), (x, y - 1))):
            f.dt[(x, y)] = WISP_MID
    for p in ((x0 + 2, y0 + 5), (x0 + 1, y0 + 5), (x0 + 2, y0 + 4)):
        f.dt[p] = WISP_CORE
    return f


def ghost_wisp(i):
    cv, pts = g_body()
    for (x, y) in pts:                                       # 머리 꼭대기는 그늘 (빛이 아래에서 온다)
        if y <= 2 or (y <= 4 and x <= 17):
            cv.dt[(x, y)] = G_SH
    # 두 손이 불꽃 밑을 받친다 (몸 앞을 지나므로 경계선)
    g_attach(cv, g_limb([(29, 16), (30, 15)]), over=False)
    g_attach(cv, g_art_limb(["hh", "os"], 30, 14), over=True)
    g_attach(cv, g_art_limb(["hhh", "oss"], 26, 14), over=True)
    g_attach(cv, g_limb([(13, 13), (12, 14)], hand=[(11, 14)]))
    g_eyes(cv, "normal")
    for x0 in G_FACE_X:                                       # 눈 아래 반사가 하늘빛으로
        cv.dt[(x0 + 1, G_FACE_Y + 3)] = G_LIT2
    g_blush(cv)
    g_mouth(cv, "spooky")
    fl = wisp_flame(i)
    cv.props.append(fl)
    near_fl = {(x + dx, y + dy) for (x, y) in fl.px for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    # 아래에서 비치는 푸른 빛 (반투명, 몸 위로) + 불티
    r2 = 26 if i == 0 else 18
    for y in range(4, 22):
        for x in range(14, 33):
            d2 = (x - 29) ** 2 + (y - 12) ** 2
            if d2 <= r2 and (x, y) in cv.px and (x, y) not in near_fl:
                cv.top.setdefault((x, y), (120, 220, 250, 70 if d2 > r2 * 0.45 else 110))
    if i == 0:
        cv.top[(25, 5)] = WISP_MID; cv.top[(32, 6)] = WISP_CORE
    else:
        cv.top[(32, 4)] = WISP_MID; cv.top[(26, 3)] = WISP_CORE
    return g_finish(cv, pts)


# ══════════════════════════════════════════════════════════════════════
# 2) 호박 잭
# ══════════════════════════════════════════════════════════════════════
P_HOT = (255, 236, 120, 255)
P_HOT_RIM = (255, 170, 40, 255)
P_DIM = (170, 60, 18, 255)            # 은은: 구멍 속이 어둑하고 가운데만 불씨처럼
P_DIM2 = (104, 36, 14, 255)
P_DIM_CORE = (250, 150, 40, 255)
P_AURA = (255, 184, 60, 110)
SEED = (244, 232, 182, 255)
SEED_DK = (196, 160, 92, 255)

PK_EYE = {
    "tri": [".X.", "XXX", "XXX"],
    "arch": ["...", "XXX", "X.X"],
    "line": ["...", "...", "XXX"],
    "wink": ["...", "X.X", ".X."],
    "big": ["XXX", "XXX", "XXX"],
}
PK_MOUTH = {
    "normal": (-3, P_MOUTHS["normal"]),
    "grin": (-4, ["X...........X",
                  "XX.XXX.XXX.XX",
                  ".XXXXXXXXXXX.",
                  "...XXXXXXX..."]),
    "smirk": (-3, ["..........X",
                   ".........XX",
                   "X.XXXXXXXX.",
                   ".XXXXXXXX.."]),
    "spit": (-1, ["..XXX..",
                  ".XXXXX.",
                  ".XXXXX.",
                  "..XXX.."]),
    "chew": (-2, ["X.......X",
                  ".XXXXXXX."]),
    "chew2": (-2, [".........",
                   "XXXXXXXXX"]),
    "oh": (-1, ["..XXX..",
                ".XXXXX.",
                "..XXX.."]),
    "line": (-3, ["X.........X",
                  ".XXXXXXXXX."]),
}


def pk_head(cv, cx, cy, rx, ry, vine=0, flicker=0, eyes=("tri", "tri"), mouth="normal", glow="normal",
            stem="normal", leaf_up=False):
    """할로윈_캐릭터.pumpkin_head 와 같은 머리 — 눈 두 짝·입 모양·빛 세기·꼭지 자세를 고를 수 있게"""
    body = set()
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            if abs((x - cx) / rx) ** 2.5 + abs((y - cy) / ry) ** 2.2 <= 1.0:
                body.add((x, y))
    top, bot = columns(body)
    sx = rnd(cx)
    ty = top[sx]
    for x in (sx - 1, sx + 2):
        if top.get(x) == ty:
            body.discard((x, ty))
    for p in body:
        cv.px[p] = P_OR
    fx, fy = sx, int(cy)
    holes, hot = set(), set()                        # hot = 얇아서 묻히기 쉬운 구멍 → 노랗게 밝힌다 (이름 끝 '!')
    for k, ex in enumerate((fx - 1, fx + 4)):
        name = eyes[k].rstrip("!")
        for dy, row in enumerate(PK_EYE[name]):
            for dx, ch in enumerate(row):
                if ch == "X":
                    holes.add((ex + dx, fy - 3 + dy))
                    if eyes[k].endswith("!"):
                        hot.add((ex + dx, fy - 3 + dy))
    ox, mrows = PK_MOUTH[mouth]
    for dy, row in enumerate(mrows):
        for dx, ch in enumerate(row):
            if ch == "X":
                holes.add((fx + ox + dx, fy + 2 + dy))
    holes &= body
    rim = set()
    for (x, y) in holes:
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n in body and n not in holes:
                rim.add(n)
    fc = cx + 1.0
    for off in (-0.80, -0.48, 0.42, 0.78):
        for y in range(int(cy - ry), int(cy + ry) + 2):
            v = (y - cy) / ry
            if abs(v) >= 0.9:
                continue
            x = rnd(fc + off * rx * (1 - abs(v) ** 2.2) ** 0.45)
            if (x, y) in body and (x, y) not in holes and (x, y) not in rim:
                cv.dt[(x, y)] = P_RIB
    for x, y in top.items():
        if (x, y) in body and x < cx + 2:
            cv.dt[(x, y)] = P_HI
    hx = rnd(cx - rx * 0.64)
    for y in range(rnd(cy - ry * 0.55), rnd(cy + ry * 0.05)):
        for x in (hx, hx + 1):
            if (x, y) in body and (x, y) not in cv.dt:
                cv.dt[(x, y)] = P_HI
    for x, y in bot.items():
        if (x, y) in body:
            cv.dt[(x, y)] = P_DK
            if (x, y - 1) in body and abs(x - cx) < rx - 3 and (x, y - 1) not in holes:
                cv.dt[(x, y - 1)] = P_DK
    rights = {}
    for (x, y) in body:
        rights[y] = max(rights.get(y, -99), x)
    for y, x in rights.items():
        if y > cy - ry * 0.4:
            cv.dt[(x, y)] = P_DK
    # 얼굴 빛
    if glow == "hot":
        # 이글이글: 구멍은 하얗게 타오르고, 테두리까지 빛이 번지며, 둘레 호박 살도 밝아진다
        for p in rim:
            cv.dt[p] = P_HOT_RIM
        for (x, y) in rim:
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in body and n not in holes and n not in rim:
                    cv.dt[n] = P_HI
        for p in holes:
            cv.dt[p] = P_HOT if (p[0], p[1] - 1) not in holes else P_CORE
    elif glow == "dim":
        for p in rim:
            cv.dt[p] = P_CARVE
        for (x, y) in holes:
            if (x, y - 1) not in holes:
                cv.dt[(x, y)] = P_DIM2
            elif (x - 1, y) in holes and (x + 1, y) in holes and (x, y - 1) in holes:
                cv.dt[(x, y)] = P_DIM_CORE
            else:
                cv.dt[(x, y)] = P_DIM
    else:
        for p in rim:
            cv.dt[p] = P_CARVE
        lit = []
        for (x, y) in sorted(holes, key=lambda p: (p[1], p[0])):
            if (x, y - 1) not in holes:
                c = P_GLOW2
            else:
                c = P_GLOW
                lit.append((x, y))
            cv.dt[(x, y)] = c
        for k, p in enumerate(lit):
            x, y = p
            inner = (x - 1, y) in holes and (x + 1, y) in holes
            if inner and (k + flicker) % 3 != 1:
                cv.dt[p] = P_CORE
        if glow == "bright":
            for p in holes:
                cv.dt[p] = P_CORE if (p[0], p[1] - 1) in holes else P_GLOW
    for p in hot & holes:
        cv.dt[p] = P_GLOW
    # 꼭지 + 덩굴 + 잎 (stem: normal · squash = 짧고 앞으로 꺾임 · stretch = 뒤로 휙 젖힘)
    if stem == "squash":
        cv.rect(sx, ty - 1, sx + 1, ty, P_STEM)
        cv.put(sx + 1, ty - 2, P_STEM); cv.put(sx + 2, ty - 2, P_STEM)
        cv.dt[(sx, ty - 1)] = P_STEM_HI; cv.dt[(sx, ty)] = P_STEM_HI
        cv.dt[(sx + 2, ty - 2)] = P_STEM_TIP
    elif stem == "stretch":
        cv.rect(sx, ty - 2, sx + 1, ty, P_STEM)
        cv.put(sx - 1, ty - 3, P_STEM); cv.put(sx - 2, ty - 3, P_STEM)
        for y in range(ty - 2, ty + 1):
            cv.dt[(sx, y)] = P_STEM_HI
        cv.dt[(sx - 2, ty - 3)] = P_STEM_TIP
    else:
        cv.rect(sx, ty - 2, sx + 1, ty, P_STEM)
        cv.put(sx - 1, ty - 3, P_STEM); cv.put(sx, ty - 3, P_STEM)
        for y in range(ty - 2, ty + 1):
            cv.dt[(sx, y)] = P_STEM_HI
        cv.dt[(sx - 1, ty - 3)] = P_STEM_TIP
    v = vine
    curl = [(-1, -1), (-2, -2), (-3, -3 + (v > 0)), (-4, -3 + (v > 0)), (-5, -3 + (v != 0)), (-6, -2 + (v < 0)),
            (-6, -1), (-5, 0), (-4, 0), (-4, -1)]
    for k, (dx, dy) in enumerate(curl):
        if (sx + dx, ty + dy) not in cv.px:
            cv.dt[(sx + dx, ty + dy)] = P_VINE if k % 3 else shade(P_VINE, 0.78)
    if leaf_up:
        leaf = [(2, -2), (3, -2), (3, -3), (4, -3), (4, -4)]
        dk = [(2, -2), (3, -2)]
    else:
        leaf = [(2, -1), (3, -1), (4, -1), (3, -2), (4, -2)]
        dk = [(2, -1), (3, -1)]
    for (dx, dy) in leaf:
        cv.px[(sx + dx, ty + dy)] = P_LEAF
    for (dx, dy) in dk:
        cv.dt[(sx + dx, ty + dy)] = P_LEAF_DK
    return body, holes


def pk_frame(head_kw, oy=0, sq=0.0, legs=None, arms=None, vine=0):
    """호박 잭 한 장: 먼 다리 → 덩굴 몸·팔 → 가까운 다리 → 머리(경계선 두르고 얹기)"""
    cv = Cv2(P_LINE)
    cx, cy, rx, ry = 20.0, 10.5, 8.7, 6.0
    legs = legs or [(17, 19, 16, 22, True), (20, 19, 20, 22, False)]
    arms = arms or ((25, 19), (14, 19))
    pumpkin_legs(cv, [l for l in legs if l[4]])
    pumpkin_body(cv, 18, 16 + oy, arms)
    pumpkin_legs(cv, [l for l in legs if not l[4]])
    head = Cv2(P_LINE)
    body, holes = pk_head(head, cx, cy + oy + sq * 0.5, rx + sq * 0.9, ry - sq, vine=vine, **head_kw)
    cv.overlay(head, edge=True)
    return cv, body, holes


def pumpkin_grin(i):
    if i == 0:      # 활짝: 눈웃음 + 이 드러낸 큰 웃음, 촛불 환하게 + 빛가루
        cv, body, holes = pk_frame(dict(eyes=("arch", "arch"), mouth="grin", glow="bright"))
        tiny_star(cv, 31, 4, 1); tiny_star(cv, 9, 5, 1); tiny_star(cv, 31, 15, 0)
    else:           # 윙크: 앞눈 찡긋(∩) + 한쪽 입꼬리 올린 미소 (빛은 평소대로)
        cv, body, holes = pk_frame(dict(eyes=("tri", "line!"), mouth="smirk", glow="normal", flicker=1))
        tiny_star(cv, 30, 5, 1)
    return cv.image()


def seed(cv, x, y):
    """날아가는 호박씨 (오른쪽이 둥근 머리, 왼쪽이 뾰족) — 맨 앞, 연노랑 + 황토 테"""
    for p, c in (((x, y), SEED_DK), ((x + 1, y - 1), SEED_DK), ((x + 1, y), SEED), ((x + 2, y - 1), SEED),
                 ((x + 2, y), SEED), ((x + 3, y - 1), SEED_DK), ((x + 3, y), SEED_DK), ((x + 1, y + 1), SEED_DK),
                 ((x + 2, y + 1), SEED_DK), ((x + 2, y - 2), SEED_DK)):
        cv.top[p] = c


def pumpkin_seeds(i):
    if i == 0:      # 퉤!: 동그랗게 벌린 입 + 날아가는 호박씨 + 속도선
        cv, body, holes = pk_frame(dict(eyes=("arch", "tri"), mouth="spit", glow="normal"))
        seed(cv, 29, 13)
        cv.line_(25, 11, 26, 11, ACT_LINE, to="fx")
        cv.top[(30, 16)] = ACT_LINE; cv.top[(31, 17)] = ACT_LINE
        cv.top[(30, 9)] = ACT_LINE; cv.top[(31, 8)] = ACT_LINE
    else:           # 오물오물: 입 다물고 씹기 (입이 한쪽으로 쏠림), 눈웃음, 씹는 표시
        cv, body, holes = pk_frame(dict(eyes=("arch", "arch"), mouth="chew", glow="normal", flicker=2))
        cv.top[(30, 14)] = ACT_LINE; cv.top[(31, 13)] = ACT_LINE
        cv.top[(10, 14)] = ACT_LINE; cv.top[(9, 13)] = ACT_LINE
    return cv.image()


def pumpkin_bounce(i):
    if i == 0:      # 착지: 꾹 찌그러짐 · 다리 벌려 버팀 · 꼭지 앞으로 꺾임 · 먼지
        oy, sq = 1, 0.8
        legs = [(17, 20, 14, 22, True), (20, 20, 21, 22, False)]
        arms = ((27, 20), (12, 20))
        cv, body, holes = pk_frame(dict(eyes=("arch", "arch"), mouth="normal", glow="normal", stem="squash"),
                                   oy=oy, sq=sq, legs=legs, arms=arms, vine=1)
        for (x, y, r) in ((10.6, 21.4, 1.6), (27.0, 21.4, 1.6), (7.6, 22.2, 0.9), (30.2, 22.2, 0.9)):
            dust_cloud(cv, x, y, r)
    else:           # 공중: 쭉 늘어남 · 발 대롱 · 팔 번쩍 · 꼭지 뒤로 · 잎 펄럭
        oy, sq = 0, -0.6
        legs = [(17, 19, 16, 21, True), (20, 19, 20, 21, False)]
        arms = ((29, 14), (10, 14))
        cv, body, holes = pk_frame(dict(eyes=("big", "big"), mouth="oh", glow="bright", stem="stretch", leaf_up=True),
                                   oy=oy, sq=sq, legs=legs, arms=arms, vine=-1)
        for x in (15, 23):
            cv.top[(x, 23)] = ACT_LINE
    return cv.image()


def pumpkin_glow(i):
    if i == 0:      # 이글: 뜨거운 주황노랑 + 둘레로 번지는 빛 + 불티
        cv, body, holes = pk_frame(dict(eyes=("tri", "tri"), mouth="normal", glow="hot"))
        ring = set()
        for (x, y) in body:
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    if abs(dx) + abs(dy) <= 2:
                        n = (x + dx, y + dy)
                        if n not in body and 1 <= n[0] <= 32:
                            ring.add(n)
        for p in ring:
            cv.fx[p] = P_AURA
        for p in ((31, 3), (10, 2)):
            tiny_star(cv, *p, 0)
        cv.top[(29, 1)] = (255, 236, 120, 255)
    else:           # 은은: 깊은 주황, 빛 번짐 없음
        cv, body, holes = pk_frame(dict(eyes=("tri", "tri"), mouth="normal", glow="dim"))
    return cv.image()


# ══════════════════════════════════════════════════════════════════════
# 3) 마녀 고양이
# ══════════════════════════════════════════════════════════════════════
GLASS = (206, 236, 246, 255)
GLASS_HI = (255, 255, 255, 255)
CORK = (150, 96, 52, 255)
POT_G = (110, 226, 86, 255)
POT_G_DK = (60, 168, 66, 255)
POT_P = (176, 112, 246, 255)
POT_P_DK = (120, 70, 196, 255)
WAND = (236, 226, 246, 255)


def broom_short(cv, y, x0=12, x1=31, rise=0, flutter=0):
    """할로윈_캐릭터.broom 과 같은 빗자루 — 좌우 1칸 여백이 남게 자루·지푸라기를 조금 짧게"""
    cv.line_(x0, y, x1, y - rise, WOOD)
    cv.put(x1, y - rise - 1, WOOD)
    for x in range(x0 + 2, x1, 3):
        yy = rnd(y - rise * (x - x0) / (x1 - x0))
        cv.dt[(x, yy)] = WOOD_HI
    bx = x0 - 2
    fan = [(bx + 0.5, y - 1.6), (bx + 0.5, y + 2.6), (bx - 6.4, y + 4.4 + flutter * 0.5),
           (bx - 7.4, y + 1.0), (bx - 6.4, y - 3.4 - flutter * 0.5)]
    straw = Cv2(C_LINE)
    straw.poly(fan, STRAW)
    for off in (-3, -1.3, 0.4, 2.1, 3.6):
        straw.line_(bx - 1, y + 0.5 + off * 0.35, bx - 7, y + 0.5 + off * 1.1, STRAW_DK, to="dt")
    for (x, yy) in list(straw.px):
        if (x, yy - 1) not in straw.px:
            straw.dt[(x, yy)] = STRAW_HI
    xmin = min(x for x, _ in straw.px)
    for yy in range(y - 5, y + 6):
        if (yy + flutter) % 2 == 0:
            straw.cut((xmin, yy))
    for p, c in straw.px.items():
        cv.px[p] = c
    cv.dt.update({p: c for p, c in straw.dt.items() if p in straw.px})
    cv.rect(bx, y - 2, bx + 1, y + 2, TIE)
    cv.dt[(bx, y - 2)] = HAT_HI
    cv.dt[(bx + 1, y + 2)] = HAT_DK


def paw_arm(segs, tip=None, col=C_FUR, w=2):
    """고양이 앞발 (몸 앞을 지나므로 경계선을 두르고 얹는다). tip = 발바닥 칸"""
    a = Cv2(C_LINE)
    for p, q in zip(segs, segs[1:]):
        a.line_(p[0], p[1], q[0], q[1], col, w=w)
    for (x, y) in list(a.px):
        if (x, y - 1) not in a.px and col == C_FUR:
            a.dt[(x, y)] = C_RIM
    for p in (tip or ()):
        a.px[p] = col
        a.dt[p] = C_LIGHT
    return a


def hat_cv(hx, top, sweep=1, flap=0):
    d = Cv2(C_LINE)
    witch_hat(d, hx, top, sweep=sweep, flap=flap)
    return d


def wink_eye(cv, hx, top):
    """앞눈 찡긋 (^) — cat_face 가 그린 앞눈을 털색으로 지우고 다시 그림"""
    ex, ey = hx + 8, top + 4
    for p in ((ex, ey), (ex, ey + 1), (ex - 1, ey), (ex - 1, ey - 1), (ex - 1, ey + 1)):
        if cv.dt.get(p) in (C_EYE, SHINE):
            cv.dt[p] = C_FUR
    cv.dt[(ex - 1, ey + 1)] = C_EYE; cv.dt[(ex, ey)] = C_EYE; cv.dt[(ex + 1, ey + 1)] = C_EYE


def witch_air(frame=0, near=None, mood="normal", head_dy=0, hat_fn=None, after=None, wink=False):
    """빗자루에 앉은 마녀 고양이 (idle 과 같은 자세·자리). near = 가까운 앞발 Cv (None 이면 자루 잡기)"""
    cv = Cv2(C_LINE)
    hx, top = W_HX, W_TOP + head_dy
    by = 20
    cv.path([(12, 16), (10, 15), (9, 13), (9, 11), (10, 9), (12, 9)], C_FUR, w=2)
    cv.line_(21, 15, 26, by - 1, C_FAR, w=2)                          # 먼 앞발: 자루 잡기
    cv.ellipse(15.5, 15.6, 5.0, 3.9, C_FUR)
    cv.rect(17, 13, 21, 18, C_FUR)
    broom_short(cv, by)
    cv.ellipse(15.0, 17.6, 3.1, 2.4, C_FUR)
    cv.line_(15, 20, 16, 22, C_FUR, w=2)
    cv.rect(16, 23, 17, 23, C_FUR)
    if near is None:
        cv.line_(20, 15, 23, by - 1, C_FUR, w=2)
    cat_head(cv, hx, top)
    for (x, y) in list(cv.px):
        if cv.px[(x, y)] == C_FUR and (x, y - 1) not in cv.px and (x, y) not in cv.dt:
            cv.dt[(x, y)] = C_RIM
    if near is None:
        cv.dt[(23, by - 1)] = C_LIGHT; cv.dt[(24, by - 1)] = C_LIGHT
    cv.dt[(26, by - 1)] = C_FAR
    cv.dt[(16, 23)] = C_LIGHT; cv.dt[(17, 23)] = C_LIGHT
    cv.dt[(16, 18)] = C_FAR; cv.dt[(17, 19)] = C_FAR
    cat_face(cv, hx, top, mood=mood)
    if wink:
        wink_eye(cv, hx, top)
    for p in ((hx - 1, top + 7), (hx, top + 8), (hx + 1, top + 9), (hx + 2, top + 9), (hx + 2, top + 10)):
        if p in cv.px:
            cv.dt[p] = C_COLLAR
    cv.dt[(hx + 3, top + 10)] = C_BELL; cv.dt[(hx + 3, top + 11)] = C_BELL_DK
    h = hat_fn(hx, top) if hat_fn else hat_cv(hx, top)
    cv.overlay(h, edge=True)
    if near is not None:
        cv.overlay(near, edge=True)
    sparkles(cv, 0 if frame % 2 == 0 else 2, 4)
    if after:
        after(cv)
    return cv


def potion_bottle(i):
    b = Cv2(C_LINE)
    rows = [".CC.",
            ".GG.",
            ".GG.",
            "GLLG",
            "LLLL",
            "LLLL",
            ".LL."]
    x0, y0 = 27, 12
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch != ".":
                b.px[(x0 + dx, y0 + dy)] = {"C": CORK, "G": GLASS, "L": POT_G}[ch]
    # 물약 결: 아랫단 진하게, 보라 소용돌이, 유리 반짝
    for p in ((28, 18), (29, 17), (30, 17)):
        b.dt[p] = POT_G_DK
    swirl = [(28, 16), (29, 15)] if i == 0 else [(29, 16), (28, 15)]
    for p in swirl:
        b.dt[p] = POT_P
    b.dt[(27, 16)] = GLASS_HI
    b.dt[(28, 13)] = GLASS_HI
    b.dt[(29, 12)] = shade(CORK, 0.75)
    return b


def witch_potion(i):
    def extra(cv):
        cv.props.append(potion_bottle(i))
        # 거품: 병 입구에서 위로 (보라·초록 번갈아, 프레임마다 위로 한 칸씩 올라감)
        bub = [(29, 10, 0, POT_P), (31, 7, 1, POT_G), (29, 3, 1, POT_P), (32, 1, 0, POT_G)] if i == 0 else \
              [(30, 9, 0, POT_G), (30, 6, 1, POT_P), (31, 2, 1, POT_G), (28, 0, 0, POT_P)]
        for (x, y, big, c) in bub:
            if big:
                for p in ((x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)):
                    cv.top[p] = c
                cv.top[(x, y)] = GLASS_HI
            else:
                cv.top[(x, y)] = c
    near = paw_arm([(21, 17), (26, 17)], tip=[(27, 17), (27, 16)])
    return witch_air(i, near=near, mood="happy", after=extra).image()


def witch_hattip(i):
    hx = W_HX
    if i == 0:      # 모자 챙에 손
        near = paw_arm([(22, 17), (27, 16), (29, 13), (29, 9)], tip=[(30, 8), (29, 7), (30, 7)])
        return witch_air(0, near=near, mood="normal").image()
    if i == 1:      # 모자 들어 꾸벅: 고개 2칸 숙이고, 모자는 챙을 잡혀 1칸 들리며 앞으로 기울고, 눈은 웃음
        def hat_fn(hx_, top_):
            h = hat_cv(hx_, top_)
            h = moved(h, 0, -1)
            return rotated(h, 14, (hx_ + 6, top_ - 1))
        near = paw_arm([(22, 18), (27, 17), (29, 14), (30, 10)], tip=[(30, 9), (31, 9), (30, 10)])
        return witch_air(2, near=near, mood="happy", head_dy=2, hat_fn=hat_fn).image()
    # 윙크: 모자 제자리, 발은 다시 자루, 앞눈 찡긋 + 반짝
    def extra(cv):
        tiny_star(cv, 31, 7, 1)
    return witch_air(0, near=None, mood="talk", wink=True, after=extra).image()


def witch_sparkle(i):
    def extra(cv):
        # 요술봉: 발에서 위로 (흰 막대 + 외곽선은 소품으로), 끝에 별
        w = Cv2(C_LINE)
        top_y = 4 if i == 0 else 5
        w.line_(29, 9, 30, top_y, WAND)
        cv.props.append(w)
        if i == 0:
            tiny_star(cv, 30, top_y - 2, 2)
            tiny_star(cv, 26, 1, 0); tiny_star(cv, 32, 7, 0); tiny_star(cv, 27, 4, 0)
        else:
            tiny_star(cv, 30, top_y - 2, 1)
            tiny_star(cv, 27, 1, 1); tiny_star(cv, 32, 1, 0); tiny_star(cv, 32, 8, 0)
    near = paw_arm([(22, 17), (27, 16), (29, 13), (29, 11)], tip=[(29, 10), (30, 10), (30, 11)])
    return witch_air(i, near=near, mood="happy" if i == 1 else "normal", after=extra).image()


def witch_sweep(i):
    """땅에 선 마녀 고양이: 두 발로 서서 빗자루를 앞에 쥐고 쓸기 (지푸라기가 앞뒤로)"""
    cv = Cv2(C_LINE)
    hx, top = W_HX, W_TOP
    # 꼬리 (뒤에서 위로 말림)
    cv.path([(17, 20), (14, 20), (12, 18), (11, 15), (12, 12), (14, 11)], C_FUR, w=2)
    # 먼 뒷발
    cv.rect(16, 22, 18, 23, C_FAR)
    # 몸통 (서 있는 둥근 배)
    cv.ellipse(20.6, 18.4, 4.3, 4.3, C_FUR)
    # 빗자루: 몸 오른쪽에 세워 쥔다. 자루 위끝은 얼굴 옆으로 솟고, 지푸라기는 땅에 닿아 좌우로 쓴다
    #   0 = 지푸라기를 뒤(왼쪽)로 쓸기 (자루 / 로 기울어짐) · 1 = 앞(오른쪽)으로 쓸기 (자루가 곧게 섬)
    if i == 0:
        (tx, ty_), (bx, by) = (31, 6), (26, 17)
    else:
        (tx, ty_), (bx, by) = (29, 6), (29, 17)

    def hx_at(y):                                   # 자루 위 y 줄의 x
        return rnd(bx + (tx - bx) * (by - y) / (by - ty_))
    cv.line_(tx, ty_, bx, by, WOOD)
    for y in range(ty_, by, 3):
        cv.dt[(hx_at(y), y)] = WOOD_HI
    # 가까운 뒷발
    cv.rect(21, 22, 23, 23, C_FUR)
    cat_head(cv, hx, top)
    for (x, y) in list(cv.px):
        if cv.px[(x, y)] == C_FUR and (x, y - 1) not in cv.px and (x, y) not in cv.dt:
            cv.dt[(x, y)] = C_RIM
    cv.dt[(22, 23)] = C_LIGHT; cv.dt[(23, 23)] = C_LIGHT
    cat_face(cv, hx, top, mood="happy")
    for p in ((hx - 1, top + 7), (hx, top + 8), (hx + 1, top + 9), (hx + 2, top + 9), (hx + 2, top + 10)):
        if p in cv.px:
            cv.dt[p] = C_COLLAR
    cv.dt[(hx + 3, top + 10)] = C_BELL; cv.dt[(hx + 3, top + 11)] = C_BELL_DK
    cv.overlay(hat_cv(hx, top), edge=True)
    # 자루 (얼굴 옆을 지나 머리보다 앞에) — 경계선을 둘러 얹기
    stick = Cv2(C_LINE)
    for y in range(ty_, by + 1):
        x = hx_at(y)
        if (x, y) not in cv.px or x >= hx + 12:
            stick.px[(x, y)] = WOOD
            stick.dt[(x, y)] = WOOD_HI if y % 3 == 0 else WOOD
    cv.overlay(stick, edge=True)
    # 지푸라기 다발 (묶은 띠 + 아래로 퍼지며 땅에 끌림)
    st = Cv2(C_LINE)
    if i == 0:
        fan = [(bx - 1.4, by + 1.5), (bx + 1.6, by + 1.5), (bx + 2.2, 23.5), (bx - 5.2, 23.5)]
    else:
        fan = [(bx - 1.6, by + 1.5), (bx + 1.4, by + 1.5), (bx + 3.4, 23.5), (bx - 3.0, 23.5)]
    st.poly(fan, STRAW)
    for (x, y) in list(st.px):
        if (x, y - 1) not in st.px:
            st.dt[(x, y)] = STRAW_HI
    xs = sorted({x for x, _ in st.px})
    for x in xs:                                    # 결: 아래로 퍼지는 진한 줄
        if (x - bx) % 2 == 1:
            for y in range(by + 3, 24):
                if (x, y) in st.px:
                    st.dt[(x, y)] = STRAW_DK
    for x in xs:                                    # 들쭉날쭉 끝
        if (x + i) % 3 == 0:
            st.cut((x, 23))
    st.rect(bx - 1, by, bx + 1, by + 1, TIE)
    st.dt[(bx - 1, by)] = HAT_HI; st.dt[(bx, by)] = HAT_HI; st.dt[(bx + 1, by + 1)] = HAT_DK
    cv.overlay(st, edge=True)
    # 앞발 둘: 아래 손은 가슴에서 뻗어 꼭 쥐고, 위 손(먼 발)은 얼굴 옆에서 자루를 잡는다
    g = hx_at(16)
    near = paw_arm([(20, 17), (g - 1, 16)], tip=[(g - 1, 16), (g, 16), (g - 1, 17), (g, 17)])
    cv.overlay(near, edge=True)
    u = hx_at(12)
    far = Cv2(C_LINE)
    for p in ((u - 1, 12), (u, 12), (u - 1, 13), (u, 13)):
        far.px[p] = C_FAR
    far.dt[(u, 12)] = C_LIGHT
    cv.overlay(far, edge=True)
    # 먼지: 쓰는 쪽으로 풀풀
    if i == 0:
        for (x, y, r) in ((18.0, 21.6, 1.6), (15.2, 22.4, 1.0), (16.0, 19.0, 0.7)):
            dust_cloud(cv, x, y, r)
    else:
        for (x, y, r) in ((31.4, 20.8, 1.3), (31.6, 17.8, 0.8), (30.4, 15.6, 0.5)):
            dust_cloud(cv, x, y, r)
    return cv.image()


# ══════════════════════════════════════════════════════════════════════
ACTIONS = [
    ("ghost_boo", ghost_boo, 3, "한 번: 보통 → 팔 들고 입 벌림 → 왁!"),
    ("ghost_peekaboo", ghost_peekaboo, 3, "한 번: 눈 가림 → 빼꼼 → 까꿍!"),
    ("ghost_chill", ghost_chill, 2, "반복: 볼 빵빵 후우~ 서리 입김"),
    ("ghost_wisp", ghost_wisp, 2, "반복: 두 손에 도깨비불"),
    ("pumpkin_grin", pumpkin_grin, 2, "반복: 활짝(환하게) / 윙크"),
    ("pumpkin_seeds", pumpkin_seeds, 2, "반복: 퉤! / 오물오물"),
    ("pumpkin_bounce", pumpkin_bounce, 2, "반복: 착지 찌그러짐 / 공중 늘어남"),
    ("pumpkin_glow", pumpkin_glow, 2, "반복: 이글이글 / 은은"),
    ("witch_sweep", witch_sweep, 2, "반복: 땅에서 싹싹 (앞 / 뒤)"),
    ("witch_potion", witch_potion, 2, "반복: 보글보글 물약"),
    ("witch_hattip", witch_hattip, 3, "한 번: 챙 잡기 → 꾸벅 → 윙크"),
    ("witch_sparkle", witch_sparkle, 2, "반복: 요술봉 반짝"),
]


def sheets():
    return [(name, [fn(i) for i in range(n)], note) for name, fn, n, note in ACTIONS]


def _font(size):
    for f in ("malgunbd.ttf", "malgun.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def preview(all_, path, S=6):
    """라벨 붙은 ×S 미리보기: 왼쪽 흰 바탕 · 오른쪽 어두운 바탕 · 맨 오른쪽 1× 실제 크기"""
    G, LBL = 12, 370
    maxn = max(len(fr) for _, fr, _ in all_)
    cell = W * S + G
    one = (W * 2 + 6) * maxn + 16                  # 2× 실제 느낌 칸
    pw = LBL + cell * maxn + 24 + cell * maxn + one + G
    ph = 50 + (H * S + G + 8) * len(all_) + G
    prev = Image.new("RGBA", (pw, ph), (255, 255, 255, 255))
    dr = ImageDraw.Draw(prev)
    f1, f2 = _font(22), _font(15)
    dr.text((12, 12), "할로윈 행동 시트 (×6) — 흰 바탕 · 어두운 바탕 · 오른쪽 끝은 ×2", fill=(30, 30, 40, 255), font=f1)
    dark_x0 = LBL + cell * maxn + 24
    for r, (name, frames, note) in enumerate(all_):
        y = 50 + r * (H * S + G + 8)
        dr.text((12, y + 34), name, fill=(20, 20, 30, 255), font=f1)
        dr.text((12, y + 66), f"{len(frames)}장 · {note}", fill=(70, 70, 80, 255), font=f2)
        dr.rectangle([dark_x0 - 6, y - 4, dark_x0 + cell * maxn - 6, y + H * S + 4], fill=(36, 40, 58, 255))
        for i, f in enumerate(frames):
            big = f.resize((W * S, H * S), Image.NEAREST)
            x = LBL + i * cell
            dr.rectangle([x - 1, y - 1, x + W * S, y + H * S], outline=(226, 226, 232, 255))
            prev.alpha_composite(big, (x, y))
            prev.alpha_composite(big, (dark_x0 + i * cell, y))
            sm = f.resize((W * 2, H * 2), Image.NEAREST)
            ox = dark_x0 + cell * maxn + 10 + i * (W * 2 + 6)
            prev.alpha_composite(sm, (ox, y + 20))
            bg = Image.new("RGBA", sm.size, (36, 40, 58, 255))
            bg.alpha_composite(sm)
            prev.alpha_composite(bg, (ox, y + 20 + H * 2 + 6))
            dr.text((x + 4, y + 2), str(i), fill=(160, 160, 170, 255), font=f2)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    prev.convert("RGB").save(path)
    print("미리보기:", path)


def main(argv):
    force = "--덮어쓰기" in argv or "--force" in argv
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return
    out = args[0]
    os.makedirs(out, exist_ok=True)
    all_ = sheets()
    ok = True
    for name, frames, _ in all_:
        ok &= check_margin(name, frames)
        p = os.path.join(out, f"{name}.png")
        if os.path.exists(p) and not force:
            print(f"{name}.png  이미 있음 → 건너뜀 (--덮어쓰기 로 새로 쓰기)")
            continue
        sheet = Image.new("RGBA", (W * len(frames), H), CLEAR)
        for i, f in enumerate(frames):
            sheet.alpha_composite(f, (i * W, 0))
        sheet.save(p)
        print(f"{name}.png  {len(frames)}프레임")
    if len(args) > 1:
        preview(all_, args[1])
    if not ok:
        print("!! 여백 규칙을 어긴 시트가 있습니다")


if __name__ == "__main__":
    main(sys.argv[1:])
