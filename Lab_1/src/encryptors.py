# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
from Crypto.Cipher import AES
from Crypto.Util import Counter


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


# ========== ПОТОКОВЫЙ XOR ==========
class XorShift32:

    __slots__ = ("state",)

    def __init__(self, state: int) -> None:
        if state == 0:
            state = 0x12345678
        self.state = state & 0xFFFFFFFF

    def next_u32(self) -> int:
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state

    def next_byte(self) -> int:
        return self.next_u32() & 0xFF


def _derive_stream_seed(key: bytes, iv: bytes) -> int:
    h = _sha256(key + iv)
    seed = int.from_bytes(h[:4], "big")
    if seed == 0:
        seed = 0x87654321
    return seed


def _keystream_xorshift(key: bytes, iv: bytes, n_bytes: int) -> bytes:
    seed = _derive_stream_seed(key, iv)
    prng = XorShift32(seed)
    return bytes(prng.next_byte() for _ in range(n_bytes))


def xor_stream(data: bytes, key: bytes, iv: bytes) -> bytes:
    ks = _keystream_xorshift(key, iv, len(data))
    return bytes(a ^ b for a, b in zip(data, ks))


def xor_stream_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    return xor_stream(data, key, iv)


def xor_stream_decrypt(enc_data: bytes, key: bytes, iv: bytes) -> bytes:
    return xor_stream(enc_data, key, iv)


# ========== AES (ECB ; CBC ; CTR) ==========
def aes_ecb_encrypt(data: bytes, key: bytes) -> bytes:
    if len(data) % AES.block_size != 0:
        raise ValueError(
            f"AES-ECB requires data length multiple of {AES.block_size}, got {len(data)}"
        )
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(data)


def aes_ecb_decrypt(enc_data: bytes, key: bytes) -> bytes:
    if len(enc_data) % AES.block_size != 0:
        raise ValueError(
            f"AES-ECB requires data length multiple of {AES.block_size}, got {len(enc_data)}"
        )
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.decrypt(enc_data)


def aes_cbc_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    if len(iv) != 16:
        raise ValueError("AES-CBC requires 16-byte IV (got %d)" % len(iv))
    if len(data) % AES.block_size != 0:
        raise ValueError(
            f"AES-CBC requires data length multiple of {AES.block_size}, got {len(data)}"
        )
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(data)


def aes_cbc_decrypt(enc_data: bytes, key: bytes, iv: bytes) -> bytes:
    if len(iv) != 16:
        raise ValueError("AES-CBC requires 16-byte IV (got %d)" % len(iv))
    if len(enc_data) % AES.block_size != 0:
        raise ValueError(
            f"AES-CBC requires data length multiple of {AES.block_size}, got {len(enc_data)}"
        )
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.decrypt(enc_data)


def aes_ctr_encrypt(data: bytes, key: bytes, nonce8: bytes) -> bytes:
    if len(nonce8) != 8:
        raise ValueError("AES-CTR requires 8-byte nonce (got %d)" % len(nonce8))
    ctr = Counter.new(64, prefix=nonce8, initial_value=0)
    cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
    return cipher.encrypt(data)


def aes_ctr_decrypt(enc_data: bytes, key: bytes, nonce8: bytes) -> bytes:
    if len(nonce8) != 8:
        raise ValueError("AES-CTR requires 8-byte nonce (got %d)" % len(nonce8))
    ctr = Counter.new(64, prefix=nonce8, initial_value=0)
    cipher = AES.new(key, AES.MODE_CTR, counter=ctr)
    return cipher.encrypt(enc_data)
