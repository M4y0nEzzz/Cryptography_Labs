# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image



# Преобразования текст->байты и наоборот
def text_to_bytes(text: str, encoding: str = "utf-8") -> bytes:
    return text.encode(encoding)
def bytes_to_text(data: bytes, encoding: str = "utf-8") -> str:
    return data.decode(encoding, errors="replace")


# Преобразования байты->список_битов и наоборот
def bytes_to_bits(data: bytes) -> list[int]:
    bits: list[int] = []
    for b in data:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return bits
def bits_to_bytes(bits: list[int]) -> bytes:
    if len(bits) % 8 != 0:
        raise ValueError("bits length is not multiple of 8")
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i:i+8]:
            byte = (byte << 1) | (bit & 1)
        out.append(byte)
    return bytes(out)



# Емкость изображения в битах
def _capacity_bits_rgb(width: int, height: int, bits_per_channel: int = 1) -> int:
    if bits_per_channel != 1:
        raise ValueError("1 LSB per channel")
    return width * height * 3 * bits_per_channel


# Вставка сообщения в младшие биты
def _embed_bits_lsb_rgb(
    rgb_bytes: bytes,
    width: int,
    height: int,
    message_bits: list[int],
    bits_per_channel: int = 1,
) -> bytes:
    capacity = _capacity_bits_rgb(width, height, bits_per_channel)
    total_bits = len(message_bits)
    if total_bits > capacity:
        raise ValueError(
            f"Message too large: need {total_bits} bits, capacity {capacity} bits"
        )
    data = bytearray(rgb_bytes)
    bit_idx = 0
    n = len(data)
    for i in range(n):
        if bit_idx >= total_bits:
            break
        b = data[i]
        b = (b & 0xFE) | (message_bits[bit_idx] & 1)
        data[i] = b
        bit_idx += 1
    return bytes(data)


# Извлечение сообщения из младших битов
def _extract_bits_lsb_rgb(
    rgb_bytes: bytes,
    width: int,
    height: int,
    n_bits: int,
    bits_per_channel: int = 1,
) -> list[int]:
    capacity = _capacity_bits_rgb(width, height, bits_per_channel)
    if n_bits > capacity:
        raise ValueError(
            f"Requested {n_bits} bits, but capacity is {capacity} bits"
        )
    bits: list[int] = []
    for b in rgb_bytes:
        bits.append(b & 1)
        if len(bits) >= n_bits:
            break
    return bits



# Payload. [32-битная длина сообщения в байтах][байты сообщения]
def _build_payload_bits(message: bytes) -> list[int]:
    msg_len = len(message)
    if msg_len > 0xFFFFFFFF:
        raise ValueError("Message too long for 32-bit length header")
    header = msg_len.to_bytes(4, "big")
    full = header + message
    return bytes_to_bits(full)


# Извлечение 32-битной длины и самих данных
def _parse_payload_bits(bits: list[int]) -> bytes:
    if len(bits) < 32:
        raise ValueError("Not enough bits for length header")

    len_bits = bits[:32]
    length_bytes = bits_to_bytes(len_bits)
    msg_len = int.from_bytes(length_bytes, "big")

    total_bits_needed = 32 + msg_len * 8
    if len(bits) < total_bits_needed:
        raise ValueError(
            f"Not enough bits for message: need {total_bits_needed}, got {len(bits)}"
        )

    msg_bits = bits[32:32 + msg_len * 8]
    return bits_to_bytes(msg_bits)




# Вставка/извлечение в png
def lsb_encode_image(
    cover_path: str | Path,
    stego_path: str | Path,
    message: bytes,
    bits_per_channel: int = 1,
    payload_frac: float | None = None,
) -> None:
    cover_path = Path(cover_path)
    stego_path = Path(stego_path)

    img = Image.open(cover_path).convert("RGB")
    w, h = img.size
    rgb = img.tobytes()
    capacity_bits = _capacity_bits_rgb(w, h, bits_per_channel)
    all_payload_bits = _build_payload_bits(message)

    # Ограничение по payload_frac
    if payload_frac is not None:
        if not (0.0 < payload_frac <= 1.0):
            raise ValueError("payload_frac must be in (0, 1]")
        max_bits = int(capacity_bits * payload_frac)
        max_bits = (max_bits // 8) * 8
        if max_bits < 32 + 8:
            raise ValueError(
                f"payload_frac={payload_frac} too small: "
                f"only {max_bits} bits < 40 bits (header+1byte)"
            )
        if len(all_payload_bits) > max_bits:
            msg_bits_available = max_bits - 32
            msg_bytes_available = msg_bits_available // 8
            if msg_bytes_available <= 0:
                raise ValueError("Not enough space for any message bytes")
            trimmed_message = message[:msg_bytes_available]
            all_payload_bits = _build_payload_bits(trimmed_message)
    else:
        if len(all_payload_bits) > capacity_bits:
            max_bytes = (capacity_bits - 32) // 8
            raise ValueError(
                f"Message too long: need {len(all_payload_bits)} bits, "
                f"capacity {capacity_bits} bits (~{max_bytes} bytes payload)"
            )
    stego_rgb = _embed_bits_lsb_rgb(
        rgb_bytes=rgb,
        width=w,
        height=h,
        message_bits=all_payload_bits,
        bits_per_channel=bits_per_channel,
    )
    stego_img = Image.frombytes("RGB", (w, h), stego_rgb)
    stego_img.save(stego_path)


# Извлечение сообщения из stego-изображения
def lsb_decode_image(
    stego_path: str | Path,
    bits_per_channel: int = 1,
) -> bytes:
    stego_path = Path(stego_path)
    img = Image.open(stego_path).convert("RGB")
    w, h = img.size
    rgb = img.tobytes()

    header_bits = _extract_bits_lsb_rgb(
        rgb_bytes=rgb,
        width=w,
        height=h,
        n_bits=32,
        bits_per_channel=bits_per_channel,
    )
    header_bytes = bits_to_bytes(header_bits)
    msg_len = int.from_bytes(header_bytes, "big")

    total_bits = 32 + msg_len * 8
    all_bits = _extract_bits_lsb_rgb(
        rgb_bytes=rgb,
        width=w,
        height=h,
        n_bits=total_bits,
        bits_per_channel=bits_per_channel,
    )

    message = _parse_payload_bits(all_bits)
    return message


def lsb_encode_text(
    cover_path: str | Path,
    stego_path: str | Path,
    text: str,
    bits_per_channel: int = 1,
    payload_frac: float | None = None,
    encoding: str = "utf-8",
) -> None:
    data = text_to_bytes(text, encoding=encoding)
    lsb_encode_image(
        cover_path=cover_path,
        stego_path=stego_path,
        message=data,
        bits_per_channel=bits_per_channel,
        payload_frac=payload_frac,
    )
def lsb_decode_text(
    stego_path: str | Path,
    bits_per_channel: int = 1,
    encoding: str = "utf-8",
) -> str:
    data = lsb_decode_image(stego_path, bits_per_channel=bits_per_channel)
    return bytes_to_text(data, encoding=encoding)
