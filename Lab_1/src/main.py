# -*- coding: utf-8 -*-
import argparse, json
from pathlib import Path
from typing import Dict, Any

from encryptors import xor_stream_encrypt, aes_ctr_encrypt
from metrics import shannon_entropy, corr_adjacent_horizontal, npcr_uaci, key_sensitivity
from utils import load_image, save_image_rgb, write_meta, write_metrics_json, histogram_png

def ensure_dirs():
    Path("imgs").mkdir(exist_ok=True)
    Path("results").mkdir(exist_ok=True)

def run_xor(input_path: str, key: bytes) -> Dict[str, Any]:
    rgb, w, h = load_image(input_path)
    enc = xor_stream_encrypt(rgb, key)
    dec = xor_stream_encrypt(enc, key)  # обратимость

    stem = Path(input_path).stem
    out_img = f"imgs/{stem}_xor.png"
    dec_img = f"imgs/{stem}_xor_dec.png"
    save_image_rgb(enc, w, h, out_img)
    save_image_rgb(dec, w, h, dec_img)

    write_meta(f"results/{stem}_xor_meta.json", "xor", key, input_path, out_img, None)

    ent_src = shannon_entropy(rgb)
    ent_enc = shannon_entropy(enc)
    corr_src = corr_adjacent_horizontal(rgb, w, h)
    corr_enc = corr_adjacent_horizontal(enc, w, h)
    npcr, uaci = npcr_uaci(rgb, enc)

    bad_key = bytes([key[0]^1]) + key[1:]
    enc_bad = xor_stream_encrypt(rgb, bad_key)
    npcr_k, uaci_k = key_sensitivity(enc, enc_bad)

    histogram_png(rgb, w, h, f"results/{stem}_xor_hist_src.png", f"{stem} source")
    histogram_png(enc, w, h, f"results/{stem}_xor_hist_enc.png", f"{stem} XOR enc")

    assert rgb == dec, "XOR: дешифрование не восстановило исходник побитово"

    summary = {
        "algo": "xor",
        "input": input_path,
        "output": out_img,
        "entropy_src": ent_src,
        "entropy_enc": ent_enc,
        "corr_src": corr_src,
        "corr_enc": corr_enc,
        "NPCR_src_vs_enc": npcr,
        "UACI_src_vs_enc": uaci,
        "KeySensitivity_NPCR": npcr_k,
        "KeySensitivity_UACI": uaci_k
    }
    write_metrics_json(f"results/{stem}_xor_metrics.json", summary)
    print(f"[OK] XOR: {input_path} -> {out_img}")
    return summary

def run_aes_ctr(input_path: str, key: bytes, nonce_hex: str) -> Dict[str, Any]:
    if not nonce_hex or len(nonce_hex) != 16:
        raise SystemExit("Для AES-CTR укажите --nonce длиной ровно 16 hex-символов (8 байт)")
    nonce8 = bytes.fromhex(nonce_hex)

    rgb, w, h = load_image(input_path)
    enc = aes_ctr_encrypt(rgb, key, nonce8)
    dec = aes_ctr_encrypt(enc, key, nonce8)

    stem = Path(input_path).stem
    out_img = f"imgs/{stem}_aes-ctr.png"
    dec_img = f"imgs/{stem}_aes-ctr_dec.png"
    save_image_rgb(enc, w, h, out_img)
    save_image_rgb(dec, w, h, dec_img)

    write_meta(f"results/{stem}_aes-ctr_meta.json", "aes-ctr", key, input_path, out_img, nonce8)

    ent_src = shannon_entropy(rgb)
    ent_enc = shannon_entropy(enc)
    corr_src = corr_adjacent_horizontal(rgb, w, h)
    corr_enc = corr_adjacent_horizontal(enc, w, h)
    npcr, uaci = npcr_uaci(rgb, enc)

    bad_key = bytes([key[0]^1]) + key[1:]
    enc_bad = aes_ctr_encrypt(rgb, bad_key, nonce8)
    npcr_k, uaci_k = key_sensitivity(enc, enc_bad)

    histogram_png(rgb, w, h, f"results/{stem}_aes-ctr_hist_src.png", f"{stem} source")
    histogram_png(enc, w, h, f"results/{stem}_aes-ctr_hist_enc.png", f"{stem} AES-CTR enc")

    assert rgb == dec, "AES-CTR: дешифрование не восстановило исходник побитово"

    summary = {
        "algo": "aes-ctr",
        "input": input_path,
        "output": out_img,
        "entropy_src": ent_src,
        "entropy_enc": ent_enc,
        "corr_src": corr_src,
        "corr_enc": corr_enc,
        "NPCR_src_vs_enc": npcr,
        "UACI_src_vs_enc": uaci,
        "KeySensitivity_NPCR": npcr_k,
        "KeySensitivity_UACI": uaci_k
    }
    write_metrics_json(f"results/{stem}_aes-ctr_metrics.json", summary)
    print(f"[OK] AES-CTR: {input_path} -> {out_img}")
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--algo", choices=["xor","aes-ctr"])
    ap.add_argument("--key", default="mysecretkey12345", help="строковый ключ; для AES-128 будут взяты первые 16 байт")
    ap.add_argument("--nonce", help="hex (8 байт = 16 hex символов) для AES-CTR")
    ap.add_argument("--input", help="PNG в папке imgs/ (можно указать относительный путь)")
    ap.add_argument("--run-all", action="store_true", help="прогнать оба алгоритма по всем PNG в imgs/")
    args = ap.parse_args()

    ensure_dirs()
    key = args.key.encode("utf-8")
    key = key.ljust(16, b"\0")[:16]  # нормируем к 16 байтам

    if args.run_all:
        inputs = sorted(Path("imgs").glob("*.png"))
        if not inputs:
            raise SystemExit("В папке imgs нет входных PNG")
        rows = []
        nonce_hex = "0011223344556677"
        for p in inputs:
            rows.append(run_xor(str(p), key))
            rows.append(run_aes_ctr(str(p), key, nonce_hex))
        Path("results/summary_all.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        # csv — по желанию, но полезно
        import csv
        with open("results/summary_all.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader(); w.writerows(rows)
        print("[OK] summary: results/summary_all.(json|csv)")
        return

    if not args.algo or not args.input:
        raise SystemExit("Нужно указать --algo и --input, либо --run-all")
    input_path = args.input
    if not Path(input_path).exists():
        input_path = "imgs/" + input_path  # удобный шорткат
    if args.algo == "xor":
        run_xor(input_path, key)
    else:
        if not args.nonce:
            raise SystemExit("Для AES-CTR укажите --nonce (16 hex символов)")
        run_aes_ctr(input_path, key, args.nonce)

if __name__ == "__main__":
    main()
