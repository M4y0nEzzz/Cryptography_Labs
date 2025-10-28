# -*- coding: utf-8 -*-
from __future__ import annotations
import hashlib
from Crypto.Cipher import AES
from Crypto.Util import Counter


# возвращаем 32 байта хэша SHA-256
def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


# генерируем псевдослучайный ключевой поток
def _keystream_sha256(key: bytes, n_bytes: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n_bytes:
        out.extend(_sha256(key + ctr.to_bytes(8, 'big')))
        ctr += 1
    return bytes(out[:n_bytes])


# шифрование XOR (поток)
def xor_stream_encrypt(data: bytes, key: bytes) -> bytes:
    ks = _keystream_sha256(key, len(data))
    return bytes(a ^ b for a, b in zip(data, ks))


# AES в режиме счетчика (блочный)
def aes_ctr_encrypt(data: bytes, key: bytes, nonce8: bytes) -> bytes:
    if len(nonce8) != 8:
        raise ValueError("AES-CTR requires 8-byte nonce")
    ctr = Counter.new(64, prefix=nonce8, initial_value=0)
    cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
    return cipher.encrypt(data)
