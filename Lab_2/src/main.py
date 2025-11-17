# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List

from lsb import *
from utils import *
from metrics import *


def ensure_dirs() -> None:
    Path("imgs").mkdir(exist_ok=True)
    Path("results").mkdir(exist_ok=True)


def run_encode(args: argparse.Namespace) -> None:
    cover_path = Path(args.cover)
    if not cover_path.exists():
        cover_in_imgs = Path("imgs") / cover_path.name
        if cover_in_imgs.exists():
            cover_path = cover_in_imgs
        else:
            raise SystemExit(f"Cover image not found: {args.cover}")

    stego_path = Path(args.out)

    if args.text is not None:
        text = args.text
    elif args.text_file is not None:
        text = Path(args.text_file).read_text(encoding="utf-8")
    else:
        raise SystemExit("Need --text or --text-file for encode mode")

    payload_frac = None
    if args.payload_percent is not None:
        payload_frac = args.payload_percent / 100.0

    bits_per_channel = args.bits

    lsb_encode_text(
        cover_path=cover_path,
        stego_path=stego_path,
        text=text,
        bits_per_channel=bits_per_channel,
        payload_frac=payload_frac,
    )

    cover_rgb, w, h = load_image(cover_path)
    stego_rgb, w2, h2 = load_image(stego_path)
    assert w == w2 and h == h2

    psnr_val = psnr_rgb(cover_rgb, stego_rgb)
    ssim_val = ssim_rgb(cover_rgb, stego_rgb, w, h)
    chi2_info_cover = hi2_lsb_all_channels(cover_rgb)
    chi2_info_stego = hi2_lsb_all_channels(stego_rgb)

    stem = cover_path.stem
    hist_cover_path = Path("results") / f"{stem}_hist_cover.png"
    hist_stego_path = Path("results") / f"{stem}_hist_stego.png"
    diff_map_path = Path("results") / f"{stem}_diff_map.png"

    histogram_png(cover_rgb, w, h, hist_cover_path, f"{stem} cover")
    histogram_png(stego_rgb, w, h, hist_stego_path, f"{stem} stego")
    diff_map_png(cover_rgb, stego_rgb, w, h, diff_map_path)

    summary = {
        "mode": "encode",
        "cover": str(cover_path),
        "stego": str(stego_path),
        "bits_per_channel": bits_per_channel,
        "payload_percent": args.payload_percent,
        "psnr": psnr_val,
        "ssim": ssim_val,
        "chi2_cover": chi2_info_cover,
        "chi2_stego": chi2_info_stego,
        "hist_cover": str(hist_cover_path),
        "hist_stego": str(hist_stego_path),
        "diff_map": str(diff_map_path),
    }
    out_json = Path("results") / f"{stem}_lsb_metrics.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"[OK] LSB encode: {cover_path} -> {stego_path}")

def run_decode(args: argparse.Namespace) -> None:
    stego_path = Path(args.stego)
    if not stego_path.exists():
        stego_in_imgs = Path("imgs") / stego_path.name
        if stego_in_imgs.exists():
            stego_path = stego_in_imgs
        else:
            raise SystemExit(f"Stego image not found: {args.stego}")

    bits_per_channel = args.bits
    text = lsb_decode_text(stego_path, bits_per_channel=bits_per_channel)

    if args.out_text_file:
        Path(args.out_text_file).write_text(text, encoding="utf-8")
        print(f"[OK] Decoded text saved to {args.out_text_file}")
    else:
        print("[OK] Decoded text:")
        print(text)


# Эксперимент: для payload 0.1%, 0.5%, 1%, 5%
def run_experiment(args: argparse.Namespace) -> None:
    imgs_dir = Path(args.imgs_dir)
    if not imgs_dir.exists():
        raise SystemExit(f"Images dir not found: {imgs_dir}")

    covers: List[Path] = sorted(imgs_dir.glob("*.png"))
    if not covers:
        raise SystemExit(f"No PNG images found in {imgs_dir}")

    bits_per_channel = args.bits
    payload_percents = [0.1, 0.5, 1.0, 5.0]

    rows: list[dict] = []

    for cover_path in covers:
        cover_rgb, w, h = load_image(cover_path)
        capacity_bits = w * h * 3 * bits_per_channel

        for p in payload_percents:
            payload_frac = p / 100.0

            max_bits = int(capacity_bits * payload_frac)
            max_bits = (max_bits // 8) * 8
            if max_bits < 32 + 8:
                continue

            msg_bytes_avail = (max_bits - 32) // 8
            if msg_bytes_avail <= 0:
                continue
            message = os.urandom(msg_bytes_avail)

            stem = cover_path.stem
            p_tag = str(p).replace(".", "p")
            stego_path = Path("results") / f"{stem}_lsb_{p_tag}.png"

            from lsb import lsb_encode_image
            lsb_encode_image(
                cover_path=cover_path,
                stego_path=stego_path,
                message=message,
                bits_per_channel=bits_per_channel,
                payload_frac=payload_frac,
            )

            stego_rgb, w2, h2 = load_image(stego_path)
            assert w == w2 and h == h2

            psnr_val = psnr_rgb(cover_rgb, stego_rgb)
            ssim_val = ssim_rgb(cover_rgb, stego_rgb, w, h)
            chi2_cover = hi2_lsb_all_channels(cover_rgb)
            chi2_stego = hi2_lsb_all_channels(stego_rgb)

            row = {
                "cover": str(cover_path),
                "stego": str(stego_path),
                "bits_per_channel": bits_per_channel,
                "payload_percent": p,
                "psnr": psnr_val,
                "ssim": ssim_val,
                "chi2_cover": chi2_cover,
                "chi2_stego": chi2_stego,
            }
            rows.append(row)
            print(f"[OK] payload {p:.3f}% on {cover_path.name}: PSNR={psnr_val:.3f}, SSIM={ssim_val:.5f}")

    out_json = Path("results") / "lsb_experiment_payload.json"
    out_json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"[OK] Experiment summary saved to {out_json}")


# CLI
def main() -> None:
    ap = argparse.ArgumentParser(description="LSB стеганография для изображений PNG")
    sub = ap.add_subparsers(dest="mode", required=True)

    # encode
    ap_enc = sub.add_parser("encode", help="встроить текст в изображение")
    ap_enc.add_argument("--cover", required=True, help="входное cover-изображение (PNG)")
    ap_enc.add_argument("--out", required=True, help="выходное stego-изображение (PNG)")
    ap_enc.add_argument("--text", help="текст для встраивания (строка)")
    ap_enc.add_argument("--text-file", help="файл с текстом для встраивания (UTF-8)")
    ap_enc.add_argument("--bits", type=int, default=1, help="число LSB на канал (здесь 1)")
    ap_enc.add_argument(
        "--payload-percent",
        type=float,
        help="доля емкости под сообщение в процентах (например 0.1, 0.5, 1, 5)",
    )

    # decode
    ap_dec = sub.add_parser("decode", help="извлечь текст из stego-изображения")
    ap_dec.add_argument("--stego", required=True, help="stego-изображение (PNG)")
    ap_dec.add_argument("--bits", type=int, default=1, help="число LSB на канал (1)")
    ap_dec.add_argument("--out-text-file", help="файл для сохранения извлеченного текста")

    # experiment
    ap_exp = sub.add_parser("experiment", help="эксперимент по payload 0.1/0.5/1/5%%")
    ap_exp.add_argument(
        "--imgs-dir",
        default="imgs",
        help="каталог с входными изображениями (по умолчанию imgs/)",
    )
    ap_exp.add_argument("--bits", type=int, default=1, help="число LSB на канал (1)")

    args = ap.parse_args()
    ensure_dirs()

    if args.mode == "encode":
        run_encode(args)
    elif args.mode == "decode":
        run_decode(args)
    elif args.mode == "experiment":
        run_experiment(args)
    else:
        raise SystemExit(f"Unknown mode: {args.mode}")


if __name__ == "__main__":
    main()
