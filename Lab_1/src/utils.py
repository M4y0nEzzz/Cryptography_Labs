# -*- coding: utf-8 -*-
from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
import hashlib
import json
import datetime as dt
from pathlib import Path


# ================== Загрузка и сохранение изображений ==================

def load_image(path: str):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    return img.tobytes(), w, h


def save_image_rgb(rgb_bytes: bytes, w: int, h: int, out_path: str):
    if len(rgb_bytes) != w * h * 3:
        raise ValueError(
            f"Размер данных {len(rgb_bytes)} не совпадает с {w*h*3} (w={w}, h={h})"
        )
    img = Image.frombytes("RGB", (w, h), rgb_bytes)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)


# ================== Метаданные и хэш ==================

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_meta(
    meta_path: str,
    algo: str,
    key: bytes,
    input_path: str,
    output_path: str,
    nonce_or_iv: bytes | None,
):
    meta = {
        "algo": algo,
        "key_hash": sha256_hex(key),
        "nonce_or_iv": None if nonce_or_iv is None else nonce_or_iv.hex(),
        "date": dt.datetime.now().isoformat(timespec="seconds"),
        "input": input_path,
        "output": output_path,
    }
    Path(meta_path).parent.mkdir(parents=True, exist_ok=True)
    Path(meta_path).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def write_metrics_json(path: str, obj: dict):
    """Сохраняет словарь метрик в JSON-файл."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


# ================== Гистограммы ==================

def histogram_png(rgb_bytes: bytes, w: int, h: int, out_path: str, title: str):
    if len(rgb_bytes) != w * h * 3:
        raise ValueError("Размер данных не совпадает с w*h*3")

    # Подсчёт частот
    n = w * h
    r_hist = [0] * 256
    g_hist = [0] * 256
    b_hist = [0] * 256

    it = iter(rgb_bytes)
    for _ in range(n):
        r = next(it)
        g = next(it)
        b = next(it)
        r_hist[r] += 1
        g_hist[g] += 1
        b_hist[b] += 1

    # Параметры панели
    panel_w, panel_h = 256, 100
    gap = 10
    header_h = 20
    total_h = header_h + (panel_h + gap) * 3 - gap

    img = Image.new("RGB", (panel_w, total_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Заголовок
    try:
        font = ImageFont.load_default()
        draw.text((5, 2), title, fill=(0, 0, 0), font=font)
    except Exception:
        draw.text((5, 2), title, fill=(0, 0, 0))

    # Функция для рисования панели
    def draw_hist(hist, y0, color):
        m = max(hist) or 1
        for x in range(256):
            hpx = int(hist[x] / m * (panel_h - 1))
            if hpx > 0:
                draw.line(
                    (x, y0 + panel_h - 1, x, y0 + panel_h - 1 - hpx),
                    fill=color,
                )

    y = header_h
    draw_hist(r_hist, y, (220, 0, 0))
    y += panel_h + gap
    draw_hist(g_hist, y, (0, 180, 0))
    y += panel_h + gap
    draw_hist(b_hist, y, (0, 0, 220))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
