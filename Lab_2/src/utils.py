# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw


def load_image(path: str | Path) -> tuple[bytes, int, int]:
    path = Path(path)
    img = Image.open(path).convert("RGB")
    w, h = img.size
    return img.tobytes(), w, h


def save_image_rgb(rgb_bytes: bytes, width: int, height: int, out_path: str | Path) -> None:
    out_path = Path(out_path)
    img = Image.frombytes("RGB", (width, height), rgb_bytes)
    img.save(out_path)


def histogram_png(
    rgb_bytes: bytes,
    width: int,
    height: int,
    out_path: str | Path,
    title: str = "",
) -> None:
    out_path = Path(out_path)

    n_pixels = width * height
    r_hist = [0] * 256
    g_hist = [0] * 256
    b_hist = [0] * 256

    it = iter(rgb_bytes)
    for _ in range(n_pixels):
        r = next(it)
        g = next(it)
        b = next(it)
        r_hist[r] += 1
        g_hist[g] += 1
        b_hist[b] += 1

    panel_w, panel_h = 256, 100
    gap = 10
    H = 20 + (panel_h + gap) * 3 - gap
    W = panel_w

    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    if title:
        draw.text((5, 5), title, fill=(0, 0, 0))

    def draw_hist(hist: list[int], y0: int, color: tuple[int, int, int]) -> None:
        m = max(hist) or 1
        for x in range(256):
            hpx = int(hist[x] / m * (panel_h - 1))
            if hpx > 0:
                draw.line((x, y0 + panel_h - 1, x, y0 + panel_h - 1 - hpx), fill=color)

    y = 20
    draw_hist(r_hist, y, (220, 0, 0))
    y += panel_h + gap
    draw_hist(g_hist, y, (0, 180, 0))
    y += panel_h + gap
    draw_hist(b_hist, y, (0, 0, 220))

    img.save(out_path)


def diff_map_png(
    cover_bytes: bytes,
    stego_bytes: bytes,
    width: int,
    height: int,
    out_path: str | Path,
) -> None:
    if len(cover_bytes) != len(stego_bytes):
        raise ValueError("diff_map: lengths differ")

    out_path = Path(out_path)
    n_pixels = width * height
    it_cov = iter(cover_bytes)
    it_stego = iter(stego_bytes)

    diff_vals = bytearray()
    for _ in range(n_pixels):
        r1 = next(it_cov); g1 = next(it_cov); b1 = next(it_cov)
        r2 = next(it_stego); g2 = next(it_stego); b2 = next(it_stego)
        dr = abs(r1 - r2)
        dg = abs(g1 - g2)
        db = abs(b1 - b2)

        d = max(dr, dg, db)
        diff_vals.append(d)

    img = Image.frombytes("L", (width, height), bytes(diff_vals))
    img.save(out_path)
