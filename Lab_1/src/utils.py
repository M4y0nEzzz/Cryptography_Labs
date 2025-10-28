# -*- coding: utf-8 -*-
from __future__ import annotations
from PIL import Image, ImageDraw
import hashlib, json, datetime as dt
from pathlib import Path


def load_image(path: str):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    return img.tobytes(), w, h


def save_image_rgb(rgb_bytes: bytes, w: int, h: int, out_path: str):
    Image.frombytes("RGB", (w,h), rgb_bytes).save(out_path)


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_meta(meta_path: str, algo: str, key: bytes, input_path: str, output_path: str, nonce8: bytes | None):
    meta = {
        "algo": algo,
        "key_hash": sha256_hex(key),
        "nonce": None if nonce8 is None else nonce8.hex(),
        "date": dt.datetime.now().isoformat(timespec="seconds"),
        "input": input_path,
        "output": output_path,
    }
    Path(meta_path).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def write_metrics_json(path: str, obj: dict):
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def histogram_png(rgb_bytes: bytes, w: int, h: int, out_path: str, title: str):
    """
    Простая 3-панельная гистограмма (R/G/B) с использованием только Pillow.
    """
    # Подсчёт частот
    n = w*h
    r_hist = [0]*256; g_hist = [0]*256; b_hist = [0]*256
    it = iter(rgb_bytes)
    for _ in range(n):
        r = next(it); g = next(it); b = next(it)
        r_hist[r] += 1; g_hist[g] += 1; b_hist[b] += 1

    # Размер полотна
    panel_w, panel_h = 256, 100
    gap = 10
    H = 20 + (panel_h + gap)*3 - gap
    W = panel_w
    img = Image.new("RGB", (W, H), (255,255,255))
    draw = ImageDraw.Draw(img)
    draw.text((5,5), title, fill=(0,0,0))

    def draw_hist(hist, y0, color):
        m = max(hist) or 1
        for x in range(256):
            hpx = int(hist[x] / m * (panel_h-1))
            if hpx > 0:
                draw.line((x, y0+panel_h-1, x, y0+panel_h-1-hpx), fill=color)

    y = 20
    draw_hist(r_hist, y, (220,0,0)); y += panel_h + gap
    draw_hist(g_hist, y, (0,180,0)); y += panel_h + gap
    draw_hist(b_hist, y, (0,0,220))

    img.save(out_path)