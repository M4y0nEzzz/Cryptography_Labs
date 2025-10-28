# -*- coding: utf-8 -*-
import math


# Преобразования
def rgb_to_gray(r: int, g: int, b: int) -> int:
    y = int(0.299 * r + 0.587 * g + 0.114 * b + 0.5)
    if y < 0:
        y = 0
    if y > 255:
        y = 255
    return y


# Энтропия (через Шенона по распределению байтов)
def shannon_entropy(data: bytes) -> float:
    counts = [0] * 256
    total = len(data)
    for b in data:
        counts[b] += 1
    ent = 0.0
    for c in counts:
        if c:
            p = c / total
            ent -= p * math.log2(p)
    return ent


# Корреляция соседних пикселей (по горизонтали)
def corr_adjacent_horizontal(rgb_bytes: bytes, width: int, height: int) -> float:
    if width < 2 or height < 1:
        return float('nan')
    n_pairs = 0
    sum_x = sum_y = 0.0
    sum_x2 = sum_y2 = 0.0
    sum_xy = 0.0

    idx = 0
    for y in range(height):
        row = []
        for x in range(width):
            r = rgb_bytes[idx]; g = rgb_bytes[idx+1]; b = rgb_bytes[idx+2]
            idx += 3
            row.append(rgb_to_gray(r,g,b))
        for x in range(width-1):
            X = float(row[x]); Y = float(row[x+1])
            sum_x += X; sum_y += Y
            sum_x2 += X*X; sum_y2 += Y*Y
            sum_xy += X*Y
            n_pairs += 1

    if n_pairs == 0:
        return float('nan')
    mean_x = sum_x / n_pairs
    mean_y = sum_y / n_pairs
    cov = sum_xy / n_pairs - mean_x * mean_y
    var_x = sum_x2 / n_pairs - mean_x * mean_x
    var_y = sum_y2 / n_pairs - mean_y * mean_y
    if var_x <= 0 or var_y <= 0:
        return float('nan')
    return cov / math.sqrt(var_x * var_y)


# NPCR и UACI (между двумя изображениями одинакового размера)
def npcr_uaci(a: bytes, b: bytes):
    if len(a) != len(b):
        raise ValueError("NPCR/UACI: размеры не совпадают.")
    n = len(a)
    diff = 0
    acc_abs = 0
    for i in range(n):
        if a[i] != b[i]:
            diff += 1
        acc_abs += abs(a[i] - b[i])
    NPCR = diff / n * 100.0
    UACI = acc_abs / (255.0 * n) * 100.0
    return NPCR, UACI



# Чувствительность к ключу: NPCR/UACI между двумя шифртекстами
def key_sensitivity(cipher_a: bytes, cipher_b: bytes):
    return npcr_uaci(cipher_a, cipher_b)
