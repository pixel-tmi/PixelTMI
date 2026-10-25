"""
8비트 효과음 만들기 (외부 라이브러리 없음).
사용: python 효과음_만들기.py <assets\\voice 폴더>
  sfx_pop     말풍선 뽁
  sfx_zing    위험 컷인 찌릭
  sfx_coin    코인 띠링
  sfx_levelup 레벨 업 빠밤
  sfx_hello   티미 등장 뾰로롱
  sfx_firework 도착 폭죽 피융~팡 팡팡
"""
import math
import os
import random
import struct
import sys
import wave

RATE = 16000


def square(freq, t, duty=0.5):
    return 1.0 if (t * freq) % 1.0 < duty else -1.0


def tone(f0, f1, ms, vol=0.35, duty=0.5, decay=True):
    n = int(RATE * ms / 1000)
    out = []
    for i in range(n):
        p = i / n
        f = f0 + (f1 - f0) * p
        env = (1 - p) ** 1.5 if decay else 1.0
        out.append(square(f, i / RATE, duty) * vol * env)
    return out


def silence(ms):
    return [0.0] * int(RATE * ms / 1000)


def boom(ms, vol=0.45):
    """폭죽 터지는 소리: 잡음이 확 퍼졌다 사그라듦 (8비트 잡음 채널)"""
    n = int(RATE * ms / 1000)
    out, hold = [], 0.0
    rnd = random.Random(3)
    for i in range(n):
        p = i / n
        if i % (2 + int(p * 10)) == 0:
            hold = rnd.choice((-1.0, 1.0))
        out.append(hold * vol * (1 - p) ** 2)
    return out


def save(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32000)) for s in samples))


def main(out):
    os.makedirs(out, exist_ok=True)
    save(os.path.join(out, "sfx_pop.wav"), tone(700, 1500, 70, 0.3, 0.25))
    zing = tone(500, 2600, 160, 0.33, 0.5, decay=False) + tone(2600, 2600, 40, 0.25) + silence(30) + tone(3200, 3200, 50, 0.22) + silence(20) + tone(3900, 3900, 80, 0.18)
    save(os.path.join(out, "sfx_zing.wav"), zing)
    save(os.path.join(out, "sfx_coin.wav"), tone(988, 988, 70, 0.3, 0.5, decay=False) + tone(1319, 1319, 260, 0.3))
    lv = []
    for f in (523, 659, 784, 1047):
        lv += tone(f, f, 90, 0.3, 0.5, decay=False)
    lv += tone(1047, 1047, 300, 0.3)
    save(os.path.join(out, "sfx_levelup.wav"), lv)
    hello = []
    for f in (784, 988, 1175, 1568):
        hello += tone(f, f * 1.02, 60, 0.25, 0.25)
    save(os.path.join(out, "sfx_hello.wav"), hello)
    fw = tone(400, 1800, 260, 0.18, 0.25, decay=False) + boom(260) + silence(60) + boom(180, 0.38) + silence(40) + boom(220, 0.4)
    save(os.path.join(out, "sfx_firework.wav"), fw)
    print("sfx ok")


if __name__ == "__main__":
    main(sys.argv[1])
