# -*- coding: utf-8 -*-
from __future__ import annotations

import math
from typing import Tuple
from scipy import stats

def _rgb_to_gray_list(rgb_bytes: bytes, width: int, height: int) -> list[float]:
    gray: list[float] = []
    n_pixels = width * height
    it = iter(rgb_bytes)
    for _ in range(n_pixels):
        r = next(it)
        g = next(it)
        b = next(it)
        y = 0.299 * r + 0.587 * g + 0.114 * b
        gray.append(y)
    return gray


# PSNR
def psnr_rgb(cover: bytes, stego: bytes) -> float:
    if len(cover) != len(stego):
        raise ValueError("PSNR: lengths differ")
    n = len(cover)
    if n == 0:
        return float("nan")
    mse = 0.0
    for a, b in zip(cover, stego):
        d = a - b
        mse += d * d
    mse /= n
    if mse == 0:
        return float("inf")
    max_i = 255.0
    return 10.0 * math.log10((max_i * max_i) / mse)


# SSIM по яркости
def ssim_gray_from_lists(x: list[float], y: list[float]) -> float:
    if len(x) != len(y):
        raise ValueError("SSIM: lengths differ")
    n = len(x)
    if n == 0:
        return float("nan")

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    var_x = 0.0
    var_y = 0.0
    cov_xy = 0.0

    for a, b in zip(x, y):
        dx = a - mean_x
        dy = b - mean_y
        var_x += dx * dx
        var_y += dy * dy
        cov_xy += dx * dy

    var_x /= n
    var_y /= n
    cov_xy /= n

    L = 255.0
    C1 = (0.01 * L) ** 2
    C2 = (0.03 * L) ** 2

    num = (2 * mean_x * mean_y + C1) * (2 * cov_xy + C2)
    den = (mean_x * mean_x + mean_y * mean_y + C1) * (var_x + var_y + C2)
    if den == 0:
        return 1.0
    return num / den


# SSIM по яркости между RGB-изображениями
def ssim_rgb(cover: bytes, stego: bytes, width: int, height: int) -> float:
    if len(cover) != len(stego):
        raise ValueError("SSIM: lengths differ")
    gray_cov = _rgb_to_gray_list(cover, width, height)
    gray_stego = _rgb_to_gray_list(stego, width, height)
    return ssim_gray_from_lists(gray_cov, gray_stego)


# хи_квадрат тест по LSB (пары 2k, 2k+1)
def _channel_histogram(rgb_bytes: bytes, channel: int) -> list[int]:
    if channel not in (0, 1, 2):
        raise ValueError("channel must be 0 (R), 1 (G) or 2 (B)")
    n_pixels = len(rgb_bytes) // 3
    hist = [0] * 256
    base = channel
    for i in range(n_pixels):
        v = rgb_bytes[3 * i + base]
        hist[v] += 1
    return hist
def hi2_lsb_channel(rgb_bytes: bytes, channel: int) -> Tuple[float, int]:
    hist = _channel_histogram(rgb_bytes, channel)
    chi2 = 0.0
    used_pairs = 0

    for k in range(0, 256, 2):
        o0 = hist[k]
        o1 = hist[k + 1]
        s = o0 + o1
        if s == 0:
            continue
        e = s / 2.0
        chi2 += (o0 - e) * (o0 - e) / e + (o1 - e) * (o1 - e) / e
        used_pairs += 1

    df = max(used_pairs - 1, 1)
    return chi2, df
def hi2_lsb_all_channels(rgb_bytes: bytes) -> dict:
    result = {}
    for ch, name in enumerate(("R", "G", "B")):
        chi2, df = hi2_lsb_channel(rgb_bytes, ch)
        p_value = 1 - stats.chi2.cdf(chi2, df)
        result[name] = {"chi2": chi2, "df": df, "p_value": p_value}
    return result


# Вероятность, что хи-квадрат (стего) > хи-квадрат (ковер)
def auc(cover_scores: list[float], stego_scores: list[float]) -> float:
    better = 0
    total = 0

    for s in stego_scores:
        for c in cover_scores:
            total += 1
            if s > c:
                better += 1

    return better / total
