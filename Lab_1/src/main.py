# -*- coding: utf-8 -*-
import os
import argparse
import json
from pathlib import Path
from typing import Dict, Any

from encryptors import *
from metrics import *
from utils import *


def ensure_dirs():
    Path("imgs").mkdir(exist_ok=True)
    Path("results").mkdir(exist_ok=True)


def run_xor(input_path: str, key: bytes) -> Dict[str, Any]:
    iv = os.urandom(16)
    rgb, w, h = load_image(input_path)

    # Шифрование / дешифрование (одна и та же функция)
    enc = xor_stream_encrypt(rgb, key, iv)
    dec = xor_stream_encrypt(enc, key, iv)

    stem = Path(input_path).stem
    out_img = f"imgs/{stem}_xor.png"
    dec_img = f"imgs/{stem}_xor_dec.png"

    save_image_rgb(enc, w, h, out_img)
    save_image_rgb(dec, w, h, dec_img)

    write_meta(f"results/{stem}_xor_meta.json", "xor", key, input_path, out_img, iv)

    # Метрики
    ent_src = shannon_entropy(rgb)
    ent_enc = shannon_entropy(enc)
    corr_src = corr_adjacent_horizontal(rgb, w, h)
    corr_enc = corr_adjacent_horizontal(enc, w, h)
    npcr, uaci = npcr_uaci(rgb, enc)

    # Чувствительность к ключу: меняем 1 бит ключа
    bad_key = bytes([key[0] ^ 1]) + key[1:]
    enc_bad = xor_stream_encrypt(rgb, bad_key, iv)
    npcr_k, uaci_k = key_sensitivity(enc, enc_bad)

    # Гистограммы
    histogram_png(rgb, w, h, f"results/{stem}_xor_hist_src.png", f"{stem} source")
    histogram_png(enc, w, h, f"results/{stem}_xor_hist_enc.png", f"{stem} XOR enc")

    # Проверка побитовой обратимости
    assert rgb == dec, "XOR: дешифрование не восстановило исходник побитово"

    summary = {
        "algo": "xor",
        "input": input_path,
        "output": out_img,
        "iv_hex": iv.hex(),
        "entropy_src": ent_src,
        "entropy_enc": ent_enc,
        "corr_src": corr_src,
        "corr_enc": corr_enc,
        "NPCR_src_vs_enc": npcr,
        "UACI_src_vs_enc": uaci,
        "KeySensitivity_NPCR": npcr_k,
        "KeySensitivity_UACI": uaci_k,
    }
    write_metrics_json(f"results/{stem}_xor_metrics.json", summary)
    print(f"[OK] XOR: {input_path} -> {out_img}")
    return summary


def run_aes_ecb(input_path: str, key: bytes) -> Dict[str, Any]:
    rgb, w, h = load_image(input_path)
    enc = aes_ecb_encrypt(rgb, key)
    dec = aes_ecb_decrypt(enc, key)

    stem = Path(input_path).stem
    out_img = f"imgs/{stem}_aes-ecb.png"
    dec_img = f"imgs/{stem}_aes-ecb_dec.png"

    save_image_rgb(enc, w, h, out_img)
    save_image_rgb(dec, w, h, dec_img)

    write_meta(
        f"results/{stem}_aes-ecb_meta.json",
        "aes-ecb",
        key,
        input_path,
        out_img,
        None,
    )

    ent_src = shannon_entropy(rgb)
    ent_enc = shannon_entropy(enc)
    corr_src = corr_adjacent_horizontal(rgb, w, h)
    corr_enc = corr_adjacent_horizontal(enc, w, h)

    # NPCR/UACI между исходником и шифром
    npcr, uaci = npcr_uaci(rgb, enc)

    # Чувствительность к ключу
    bad_key = bytes([key[0] ^ 1]) + key[1:]
    enc_bad = aes_ecb_encrypt(rgb, bad_key)
    npcr_k, uaci_k = key_sensitivity(enc, enc_bad)

    histogram_png(
        rgb, w, h,
        f"results/{stem}_aes-ecb_hist_src.png",
        f"{stem} source"
    )
    histogram_png(
        enc, w, h,
        f"results/{stem}_aes-ecb_hist_enc.png",
        f"{stem} AES-ECB enc"
    )

    assert rgb == dec, "AES-ECB: дешифрование не восстановило исходник"

    summary = {
        "algo": "aes-ecb",
        "input": input_path,
        "output": out_img,
        "entropy_src": ent_src,
        "entropy_enc": ent_enc,
        "corr_src": corr_src,
        "corr_enc": corr_enc,
        "NPCR_src_vs_enc": npcr,
        "UACI_src_vs_enc": uaci,
        "KeySensitivity_NPCR": npcr_k,
        "KeySensitivity_UACI": uaci_k,
    }
    write_metrics_json(f"results/{stem}_aes-ecb_metrics.json", summary)
    print(f"[OK] AES-ECB: {input_path} -> {out_img}")
    return summary


def run_aes_cbc(input_path: str, key: bytes) -> Dict[str, Any]:
    iv = os.urandom(16)

    rgb, w, h = load_image(input_path)
    enc = aes_cbc_encrypt(rgb, key, iv)
    dec = aes_cbc_decrypt(enc, key, iv)

    stem = Path(input_path).stem
    out_img = f"imgs/{stem}_aes-cbc.png"
    dec_img = f"imgs/{stem}_aes-cbc_dec.png"

    save_image_rgb(enc, w, h, out_img)
    save_image_rgb(dec, w, h, dec_img)

    write_meta(
        f"results/{stem}_aes-cbc_meta.json",
        "aes-cbc",
        key,
        input_path,
        out_img,
        iv,
    )

    ent_src = shannon_entropy(rgb)
    ent_enc = shannon_entropy(enc)
    corr_src = corr_adjacent_horizontal(rgb, w, h)
    corr_enc = corr_adjacent_horizontal(enc, w, h)

    # NPCR/UACI между исходником и шифром
    npcr, uaci = npcr_uaci(rgb, enc)

    bad_key = bytes([key[0] ^ 1]) + key[1:]
    enc_bad = aes_cbc_encrypt(rgb, bad_key, iv)
    npcr_k, uaci_k = key_sensitivity(enc, enc_bad)

    histogram_png(
        rgb, w, h,
        f"results/{stem}_aes-cbc_hist_src.png",
        f"{stem} source"
    )
    histogram_png(
        enc, w, h,
        f"results/{stem}_aes-cbc_hist_enc.png",
        f"{stem} AES-CBC enc"
    )

    assert rgb == dec, "AES-CBC: дешифрование не восстановило исходник"

    summary = {
        "algo": "aes-cbc",
        "input": input_path,
        "output": out_img,
        "iv_hex": iv.hex(),
        "entropy_src": ent_src,
        "entropy_enc": ent_enc,
        "corr_src": corr_src,
        "corr_enc": corr_enc,
        "NPCR_src_vs_enc": npcr,
        "UACI_src_vs_enc": uaci,
        "KeySensitivity_NPCR": npcr_k,
        "KeySensitivity_UACI": uaci_k,
    }
    write_metrics_json(f"results/{stem}_aes-cbc_metrics.json", summary)
    print(f"[OK] AES-CBC: {input_path} -> {out_img} (IV: {iv.hex()[:16]}...)")
    return summary


def run_aes_ctr(input_path: str, key: bytes) -> Dict[str, Any]:
    nonce8 = os.urandom(8)

    rgb, w, h = load_image(input_path)
    enc = aes_ctr_encrypt(rgb, key, nonce8)
    dec = aes_ctr_decrypt(enc, key, nonce8)

    stem = Path(input_path).stem
    out_img = f"imgs/{stem}_aes-ctr.png"
    dec_img = f"imgs/{stem}_aes-ctr_dec.png"

    save_image_rgb(enc, w, h, out_img)
    save_image_rgb(dec, w, h, dec_img)

    write_meta(
        f"results/{stem}_aes-ctr_meta.json",
        "aes-ctr",
        key,
        input_path,
        out_img,
        nonce8,
    )

    ent_src = shannon_entropy(rgb)
    ent_enc = shannon_entropy(enc)
    corr_src = corr_adjacent_horizontal(rgb, w, h)
    corr_enc = corr_adjacent_horizontal(enc, w, h)

    # NPCR/UACI между исходником и шифром
    npcr, uaci = npcr_uaci(rgb, enc)

    bad_key = bytes([key[0] ^ 1]) + key[1:]
    enc_bad = aes_ctr_encrypt(rgb, bad_key, nonce8)
    npcr_k, uaci_k = key_sensitivity(enc, enc_bad)

    histogram_png(
        rgb, w, h,
        f"results/{stem}_aes-ctr_hist_src.png",
        f"{stem} source"
    )
    histogram_png(
        enc, w, h,
        f"results/{stem}_aes-ctr_hist_enc.png",
        f"{stem} AES-CTR enc"
    )

    assert rgb == dec, "AES-CTR: дешифрование не восстановило исходник"

    summary = {
        "algo": "aes-ctr",
        "input": input_path,
        "output": out_img,
        "nonce_hex": nonce8.hex(),
        "entropy_src": ent_src,
        "entropy_enc": ent_enc,
        "corr_src": corr_src,
        "corr_enc": corr_enc,
        "NPCR_src_vs_enc": npcr,
        "UACI_src_vs_enc": uaci,
        "KeySensitivity_NPCR": npcr_k,
        "KeySensitivity_UACI": uaci_k,
    }
    write_metrics_json(f"results/{stem}_aes-ctr_metrics.json", summary)
    print(f"[OK] AES-CTR: {input_path} -> {out_img} (Nonce: {nonce8.hex()})")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--algo",
        choices=["xor", "aes-ecb", "aes-cbc", "aes-ctr"],
        help="Алгоритм шифрования"
    )
    ap.add_argument(
        "--key",
        default="MikhailKonichev4",
        help="строковый ключ; для AES-128 будут взяты первые 16 байт",
    )
    ap.add_argument(
        "--input",
        help="PNG в папке imgs/ (можно указать относительный путь)",
    )
    ap.add_argument(
        "--run-all",
        action="store_true",
        help="прогнать все алгоритмы по всем PNG в imgs/",
    )
    args = ap.parse_args()

    ensure_dirs()
    key = args.key.encode("utf-8")
    key = key.ljust(16, b"\0")[:16]  # нормируем к 16 байтам (AES-128)

    if args.run_all:
        inputs = sorted(Path("imgs").glob("*.png"))
        if not inputs:
            raise SystemExit("В папке imgs нет входных PNG")
        rows = []
        for p in inputs:
            rows.append(run_xor(str(p), key))
            rows.append(run_aes_ecb(str(p), key))
            rows.append(run_aes_cbc(str(p), key))
            rows.append(run_aes_ctr(str(p), key))
        Path("results/summary_all.json").write_text(
            json.dumps(rows, indent=2),
            encoding="utf-8"
        )
        print("[OK] summary: results/summary_all.json")
        return

    if not args.algo or not args.input:
        raise SystemExit("Нужно указать --algo и --input, либо --run-all")

    input_path = args.input
    if not Path(input_path).exists():
        input_path = "imgs/" + input_path

    if args.algo == "xor":
        run_xor(input_path, key)
    elif args.algo == "aes-ecb":
        run_aes_ecb(input_path, key)
    elif args.algo == "aes-cbc":
        run_aes_cbc(input_path, key)
    elif args.algo == "aes-ctr":
        run_aes_ctr(input_path, key)


if __name__ == "__main__":
    main()
