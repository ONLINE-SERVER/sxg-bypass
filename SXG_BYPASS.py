#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UltimateEngine LITE
PAK Tool - Extract, Inject, Rebuild, Shield

UI: SXG-style termux look
Workspace: /storage/emulated/0/SXGBYPASS
With Key System - 1 Day Validity + Device Lock
"""

import struct
import shutil
import os
import sys
import hashlib
import subprocess
import zlib
import ctypes
import math
import itertools as it
import json
import uuid
import platform
import base64
from dataclasses import dataclass
from functools import lru_cache
from pathlib import PurePath, Path
from typing import List, Dict, Tuple
import time
from datetime import datetime


# ============================================================
# DEPENDENCY MANAGEMENT
# ============================================================
try:
    import pytz
except ImportError:
    os.system("pip install pytz -q")
    import pytz

try:
    import gmalg
except ImportError:
    os.system("pip install gmalg -q")
    import gmalg

try:
    from Crypto.Cipher import AES
    from Crypto.Cipher.AES import MODE_CBC
    from Crypto.Hash import SHA1
    from Crypto.Util.Padding import unpad
except ImportError:
    os.system("pip install pycryptodome -q")
    from Crypto.Cipher import AES
    from Crypto.Cipher.AES import MODE_CBC
    from Crypto.Hash import SHA1
    from Crypto.Util.Padding import unpad

try:
    from zstandard import ZstdDecompressor, ZstdCompressionDict, DICT_TYPE_AUTO, ZstdCompressor
except ImportError:
    os.system("pip install zstandard -q")
    from zstandard import ZstdDecompressor, ZstdCompressionDict, DICT_TYPE_AUTO, ZstdCompressor


# ============================================================
# ANSI COLORS (UI only)
# ============================================================
class C:
    RED     = '\033[91m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN    = '\033[96m'
    WHITE   = '\033[97m'
    BOLD    = '\033[1m'
    DIM     = '\033[2m'
    RESET   = '\033[0m'


def clr():
    os.system('cls' if os.name == 'nt' else 'clear')


# ============================================================
# FIXED WORKSPACE
# ============================================================
def _get_workspace():
    candidates = [
        Path("/storage/emulated/0/SXGBYPASS"),
        Path("/sdcard/SXGBYPASS"),
        Path.home() / "SXGBYPASS",
    ]
    for p in candidates:
        try:
            p.mkdir(parents=True, exist_ok=True)
            test = p / ".write_test"
            test.write_text("ok")
            test.unlink()
            return p
        except Exception:
            continue
    return Path.home() / "SXGBYPASS"

WORKSPACE = _get_workspace()


# ============================================================
# KEY SYSTEM - 1 DAY VALIDITY + DEVICE LOCK
# ============================================================
class KeySystem:
    SECRET = "ALLSRCFREE_BYPASS_SECRET_2024_X99"
    KEY_NAME = "@ALLSRCFREE_BYPASS"
    VALIDITY_HOURS = 24

    # Admin: True = multi-device allowed
    MULTI_DEVICE_ENABLED = False

    def __init__(self):
        self.data_dir = WORKSPACE / ".sxg_data"
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        self.key_file = self.data_dir / "key.dat"
        self.license_file = self.data_dir / "license.dat"
        self.device_file = self.data_dir / "device.dat"

        self.device_id = self._get_device_id()

    def _get_device_id(self) -> str:
        try:
            if self.device_file.exists():
                data = self._read_encrypted(self.device_file)
                if data and 'device_id' in data:
                    return data['device_id']
        except Exception:
            pass

        raw = ""
        try:
            raw += platform.node()
            raw += platform.machine()
            raw += platform.processor()
            raw += str(uuid.getnode())
        except Exception:
            raw += str(uuid.uuid4())

        h = hashlib.sha256((raw + self.SECRET).encode()).hexdigest()
        dev_id = h[:32].upper()
        self._write_encrypted(self.device_file, {'device_id': dev_id})
        return dev_id

    def _xor_crypt(self, data: bytes, key: bytes) -> bytes:
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def _write_encrypted(self, path: Path, obj: dict):
        try:
            raw = json.dumps(obj).encode()
            key = hashlib.sha256(self.SECRET.encode()).digest()
            enc = self._xor_crypt(raw, key)
            b64 = base64.b64encode(enc)
            path.write_bytes(b64)
        except Exception:
            pass

    def _read_encrypted(self, path: Path):
        try:
            if not path.exists():
                return None
            b64 = path.read_bytes()
            enc = base64.b64decode(b64)
            key = hashlib.sha256(self.SECRET.encode()).digest()
            raw = self._xor_crypt(enc, key)
            return json.loads(raw.decode())
        except Exception:
            return None

    def is_activated(self) -> tuple:
        lic = self._read_encrypted(self.license_file)
        if not lic:
            return False, "No license found. Please activate."

        if lic.get('key') != self.KEY_NAME:
            return False, "Invalid key. Please re-activate."

        if not self.MULTI_DEVICE_ENABLED:
            if lic.get('device_id') != self.device_id:
                return False, "License locked to another device!"

        start = lic.get('start_time', 0)
        expiry = start + (self.VALIDITY_HOURS * 3600)
        now = time.time()

        if now > expiry:
            remaining_sec = now - expiry
            return False, f"License EXPIRED ({int(remaining_sec/3600)}h ago). Please renew."

        remaining = expiry - now
        h = int(remaining // 3600)
        m = int((remaining % 3600) // 60)
        return True, f"Active | Expires in {h}h {m}m"

    def activate(self, user_key: str) -> tuple:
        user_key = user_key.strip()

        if not user_key:
            return False, "Key cannot be empty!"

        if user_key != self.KEY_NAME:
            return False, f"Invalid Key!\nRequired: {self.KEY_NAME}"

        existing = self._read_encrypted(self.license_file)
        if existing and not self.MULTI_DEVICE_ENABLED:
            if existing.get('device_id') != self.device_id:
                return False, "This key is already activated on another device!"

        lic = {
            'key': self.KEY_NAME,
            'device_id': self.device_id,
            'start_time': time.time(),
            'activated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._write_encrypted(self.license_file, lic)
        return True, "License Activated Successfully!"

    def reset(self):
        if self.license_file.exists():
            self.license_file.unlink()

    def get_info(self) -> dict:
        lic = self._read_encrypted(self.license_file)
        if not lic:
            return {}
        start = lic.get('start_time', 0)
        expiry = start + (self.VALIDITY_HOURS * 3600)
        return {
            'key': lic.get('key'),
            'device': lic.get('device_id'),
            'current_device': self.device_id,
            'activated_at': lic.get('activated_at'),
            'expiry': datetime.fromtimestamp(expiry).strftime("%Y-%m-%d %H:%M:%S"),
            'multi_device': self.MULTI_DEVICE_ENABLED,
        }


# ============================================================
# CONSTANTS (UNCHANGED)
# ============================================================
ZUC_KEY = bytes.fromhex('01010101010101010101010101010101')
ZUC_IV = bytes.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF')

RSA_MOD_1 = bytes.fromhex('CBE8B9F2504050EF9831B719E9A6249A6D238505ADE909BDE78C180DED6072A0C3347B8AF4780E1F212D952D82D4BF7F233C1ECA499E1F9D9A85B4FAD759F54BABC1666C5DE411EA9E4B2374425DD6C6F54333BBC8F2610FE6063E4D0D6C21A671A8F7C3740555E5DC06D4E1691C456DB4116C0C012BF7B206E8311AAAEC689952BF804EF638F09D5822B4117B114208F14DEB459E80CB770E5B0D7978E21F5E6CED4999D3583108221A7AB28B960277ADB5690A332784019D9C195BE4EA9EA0A09459010F236465DE0D59C3EF7324E954E1118D93EE19F299760C2CDB963CE87973EA5ECC9BBE81C27D4C7C8572AC07E9BCEAC9BD72AB7A56A3C0AD736ABCE4')
RSA_MOD_2 = bytes.fromhex('7F58E8A39A4DA4E87357DDD650EAA16D3B5CE95B213D1030A662566444796A78A84AE9AC3DBFFDE7F41094896696835DAF13B89E6EC2B84963B1B1BAF7151DA245C3FBFAE2A6AE18B2684D03F9229DE2C91440F2A3A3BCDE1E5680C16722A88039C73560D5D43F4B6562C2EEA5B1D926D86B51108A2643C70FB74D6442CE3A08339B8FD8F660AE88129B7AB8C46F2FA58124485CCCB1E987B05A6DA65A01858ED3F89905449AE42BB07290FCB9994BF22E26610BCABB9804783A3B9587917F3D97316EDDA15C5E13F79066407B55A93B291B68A4AC42A98D6E35FED84B14A792D154E62028DDAD20FC301951E5924BE9AD62FB719DD94CC30CAB871BEC4377A8')

SIMPLE1_DECRYPT_KEY = 121
SIMPLE2_DECRYPT_KEY = bytes.fromhex('E55B4ED1')
SIMPLE2_BLOCK_SIZE = 16

SM4_SECRET_4 = 'eb691efea914241317a8'
SM4_SECRET_2 = 'Q0hVTKey$as*1ZFlQCiA'
SM4_SECRET_NEW = [
    'xG2qW5lP7lV2iN5fN5pG', 'xT1cJ6dL5wC0kK1rB4dK', 'qC4jS5bZ6fL5xE6nD4zA',
    'gD4jQ2aL3bS3lC3xT0iW', 'xU1yQ8wE9zY3gZ3bT5aE', 'uQ3cO2dX7xY4xU7gH7iS',
    'gW1fR0jK6wQ4oN0oK1kZ', 'aJ4pV7iZ7pU4wP2aC2cZ', 'cX6jT3cM2oT3vK0kJ1qN',
    'iT2vS0cS6yT6cZ1sE1lO', 'hM1pH9iY8wM9hT4lN5uJ', 'kG6bC8jK0fL0dE4sH4mL',
    'dB6lB3vE0eZ8wM8rI0aC', 'tP7sP7nI9rA2vQ4cV5yQ', 'aT0cL1yN4pT3sZ7eM2vY',
    'uV6fU8fC9zN3mP5dH8mN', 'rT6aQ6oZ1yM0gO5tO1aN', 'jU5bH7lQ0fM9hK2kI0oF',
    'iQ0eM0mJ7uT0kV6kL5zY',
]

EM_SIMPLE1 = 1
EM_SIMPLE2 = 16
EM_SM4_2 = 2
EM_SM4_4 = 4
EM_SM4_NEW_BASE = 31
EM_SM4_NEW_MASK = ~EM_SM4_NEW_BASE

CM_NONE = 0
CM_ZLIB = 1
CM_ZSTD = 6
CM_ZSTD_DICT = 8
CM_MASK = 15


# ============================================================
# UTILS
# ============================================================
def to_long_path(path) -> str:
    p = str(path)
    if os.name != "nt":
        return p
    if p.startswith("\\\\?\\"):
        return p
    p = os.path.abspath(p)
    if p.startswith("\\\\"):
        return "\\\\?\\UNC\\" + p[2:]
    return "\\\\?\\" + p


def open_long(path, mode='rb'):
    return open(to_long_path(path), mode)


def get_indian_time():
    try:
        tz = pytz.timezone("Asia/Kolkata")
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def human_size(size):
    if size is None:
        return "N/A"
    size = int(size)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            if unit == 'B':
                return f'{size} B'
            return f'{size:.2f} {unit}'
        size /= 1024.0
    return f'{size:.2f} PB'


def check_key_press():
    try:
        if sys.platform == 'win32':
            import msvcrt
            if msvcrt.kbhit():
                return msvcrt.getch().decode('utf-8', errors='ignore').lower()
        else:
            import select
            if select.select([sys.stdin], [], [], 0)[0]:
                return sys.stdin.read(1).lower()
    except Exception:
        pass
    return None


def safe_input(prompt=''):
    import re
    clean = re.sub(r'\[/?[^\[\]]*\]', '', prompt)
    try:
        return input(clean)
    except (EOFError, KeyboardInterrupt):
        return ""


# ============================================================
# WORKSPACE INIT
# ============================================================
CREDIT_FILE_CONTENT = """TG ~ @BAAPU_OWNER1
TG ~ @ios_SHANi

JOIN TELEGRAM CHANNEL
https://t.me/ALLSRCFREE_BYPASS
https://t.me/ALLSRCFREE_BYPASS
https://t.me/ALLSRCFREE_BYPASS
"""

CREDIT_FILE_NAME = "TOOL_BUY.cpp"


def init_workspace():
    """Create workspace + subfolders + credit file automatically."""
    try:
        WORKSPACE.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    for sub in ("PAK", "EDIT", "UNPACK", "RESULT"):
        try:
            (WORKSPACE / sub).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    credit_path = WORKSPACE / CREDIT_FILE_NAME
    try:
        if not credit_path.exists():
            credit_path.write_text(CREDIT_FILE_CONTENT, encoding='utf-8')
    except Exception:
        pass


# ============================================================
# SIMPLE UI HELPERS
# ============================================================
def print_status(message: str, status: str = "info"):
    styles = {
        "info":       (C.CYAN,   "[i]"),
        "success":    (C.GREEN,  "[+]"),
        "error":      (C.RED,    "[X]"),
        "warning":    (C.YELLOW, "[!]"),
        "processing": (C.CYAN,   "[*]"),
    }
    color, icon = styles.get(status, styles["info"])
    print(f"{color}{icon}{C.RESET} {message}")


def print_header(title: str, subtitle: str = ""):
    print()
    print(f"{C.CYAN}{C.BOLD}{title}{C.RESET}")
    if subtitle:
        print(f"{C.DIM}{subtitle}{C.RESET}")


def print_success_panel(title: str, message: str):
    print()
    print(f"{C.GREEN}{C.BOLD}[+] {title}{C.RESET}")
    for line in message.split('\n'):
        print(f"    {line}")
    print()


def print_error_panel(title: str, message: str):
    print()
    print(f"{C.RED}{C.BOLD}[X] {title}{C.RESET}")
    for line in str(message).split('\n'):
        print(f"    {line}")
    print()


def print_warning_panel(title: str, message: str):
    print()
    print(f"{C.YELLOW}{C.BOLD}[!] {title}{C.RESET}")
    for line in str(message).split('\n'):
        print(f"    {line}")
    print()


def get_choice(prompt: str, valid: list, default: str = None) -> str:
    while True:
        try:
            val = input(f"{C.CYAN}{prompt}{C.RESET} ").strip()
            if not val and default is not None:
                return default
            if val in valid:
                return val
            print(f"{C.RED}[X] Invalid. Choose from: {', '.join(valid)}{C.RESET}")
        except (KeyboardInterrupt, EOFError):
            return "0"


def confirm(prompt: str, default: bool = True) -> bool:
    try:
        suffix = " [Y/n]: " if default else " [y/N]: "
        val = input(f"{C.YELLOW}{prompt}{suffix}{C.RESET}").strip().lower()
        if not val:
            return default
        return val in ('y', 'yes')
    except (KeyboardInterrupt, EOFError):
        return False


# ============================================================
# MISC
# ============================================================
class Misc:
    @staticmethod
    def pad_to_n(data: bytes, n: int) -> bytes:
        assert n > 0
        padding = n - len(data) % n
        return data if padding == n else data + b'\x00' * padding

    @staticmethod
    def align_up(x: int, n: int) -> int:
        return (x + n - 1) // n * n


# ============================================================
# SM4
# ============================================================
class SM4:
    _S_BOX = bytes([
        52, 102, 37, 116, 137, 120, 228, 169, 90, 65, 188, 122, 214, 22, 33, 35,
        77, 97, 218, 148, 155, 223, 19, 60, 105, 58, 49, 10, 95, 215, 153, 149,
        241, 174, 114, 61, 7, 96, 36, 182, 152, 238, 196, 162, 45, 136, 221, 141,
        4, 234, 187, 17, 202, 62, 93, 161, 246, 63, 176, 151, 128, 71, 43, 166,
        230, 247, 217, 177, 89, 192, 124, 190, 84, 40, 183, 126, 79, 248, 67, 110,
        160, 80, 14, 245, 144, 184, 251, 163, 123, 98, 25, 70, 3, 42, 185, 143,
        159, 119, 180, 91, 131, 135, 8, 235, 226, 30, 66, 240, 15, 232, 113, 106,
        117, 173, 85, 31, 181, 171, 51, 250, 127, 21, 189, 133, 216, 6, 104, 179,
        82, 48, 72, 11, 0, 237, 239, 178, 87, 142, 231, 108, 213, 229, 46, 83,
        130, 5, 249, 129, 244, 86, 191, 140, 75, 227, 219, 74, 145, 76, 44, 211,
        64, 41, 78, 32, 20, 54, 121, 9, 111, 209, 55, 224, 57, 12, 138, 146,
        56, 18, 53, 109, 225, 253, 147, 154, 23, 212, 201, 156, 107, 132, 38, 157,
        175, 118, 193, 158, 208, 150, 197, 203, 233, 115, 73, 210, 205, 100, 195, 199,
        1, 125, 243, 172, 252, 222, 164, 68, 50, 27, 194, 186, 28, 2, 198, 39,
        69, 139, 242, 24, 167, 16, 81, 29, 200, 207, 99, 255, 47, 13, 88, 206,
        101, 165, 220, 26, 59, 134, 254, 34, 92, 168, 94, 103, 170, 236, 112, 204
    ])
    _FK = [1184304796, 1270900830, 1493524870, 3164752158]
    _CK = [964907, 973793155, 2654690407, 2916866751, 2071233739, 1226140771, 3348805095, 2045549823, 388349611, 800627875, 612403927, 3721562911, 1195432523, 3150178931, 612053223, 2445162591, 67183755, 1174197155, 1393249511, 3331183455, 3822152747, 1332317203, 1804781383, 1990130463, 1282653851, 3376591251, 2910902311, 925872959, 332098219, 735840931, 396665415, 3588844719]

    @staticmethod
    def ROL32(x, n):
        return (x << n) & 0xFFFFFFFF | (x >> (32 - n))

    @staticmethod
    def _BS(X):
        return (SM4._S_BOX[X >> 24 & 255] << 24 |
                SM4._S_BOX[X >> 16 & 255] << 16 |
                SM4._S_BOX[X >> 8 & 255] << 8 |
                SM4._S_BOX[X & 255])

    @staticmethod
    def _T0(X):
        X = SM4._BS(X)
        return X ^ SM4.ROL32(X, 2) ^ SM4.ROL32(X, 10) ^ SM4.ROL32(X, 18) ^ SM4.ROL32(X, 24)

    @staticmethod
    def _T1(X):
        X = SM4._BS(X)
        return X ^ SM4.ROL32(X, 13) ^ SM4.ROL32(X, 23)

    @staticmethod
    def _key_expand(key: bytes, rkey: list):
        K0 = int.from_bytes(key[0:4], 'big') ^ SM4._FK[0]
        K1 = int.from_bytes(key[4:8], 'big') ^ SM4._FK[1]
        K2 = int.from_bytes(key[8:12], 'big') ^ SM4._FK[2]
        K3 = int.from_bytes(key[12:16], 'big') ^ SM4._FK[3]
        for i in range(0, 32, 4):
            K0 = K0 ^ SM4._T1(K1 ^ K2 ^ K3 ^ SM4._CK[i])
            rkey[i] = K0
            K1 = K1 ^ SM4._T1(K2 ^ K3 ^ K0 ^ SM4._CK[i + 1])
            rkey[i + 1] = K1
            K2 = K2 ^ SM4._T1(K3 ^ K0 ^ K1 ^ SM4._CK[i + 2])
            rkey[i + 2] = K2
            K3 = K3 ^ SM4._T1(K0 ^ K1 ^ K2 ^ SM4._CK[i + 3])
            rkey[i + 3] = K3

    @classmethod
    def key_length(cls): return 16
    @classmethod
    def block_length(cls): return 16

    def __init__(self, key: bytes):
        if len(key) != self.key_length():
            raise ValueError(f'Key must be {self.key_length()} bytes')
        self._key = key
        self._rkey = [0] * 32
        SM4._key_expand(self._key, self._rkey)
        self._block_buffer = bytearray()
        if not hasattr(SM4, '_T_TABLES'):
            SM4._T_TABLES = SM4._make_t_tables()

    @classmethod
    def _make_t_tables(cls):
        S = cls._S_BOX
        def rol(x, n): return (x << n) & 0xFFFFFFFF | (x >> (32 - n))
        def L(y): return y ^ rol(y, 2) ^ rol(y, 10) ^ rol(y, 18) ^ rol(y, 24)
        T0 = [0] * 256; T1 = [0] * 256; T2 = [0] * 256; T3 = [0] * 256
        for i in range(256):
            s = S[i]
            T0[i] = L(s << 24); T1[i] = L(s << 16); T2[i] = L(s << 8); T3[i] = L(s)
        return (T0, T1, T2, T3)

    def _bulk(self, data: bytes, rk) -> bytes:
        n = len(data)
        out = bytearray(n)
        T0, T1, T2, T3 = self._T_TABLES
        unpack_from = struct.unpack_from
        pack_into = struct.pack_into
        idx = 0
        while idx < n:
            X0, X1, X2, X3 = unpack_from('>IIII', data, idx)
            for i in range(0, 32, 4):
                t = X1 ^ X2 ^ X3 ^ rk[i]
                X0 ^= T0[t >> 24] ^ T1[t >> 16 & 255] ^ T2[t >> 8 & 255] ^ T3[t & 255]
                t = X2 ^ X3 ^ X0 ^ rk[i + 1]
                X1 ^= T0[t >> 24] ^ T1[t >> 16 & 255] ^ T2[t >> 8 & 255] ^ T3[t & 255]
                t = X3 ^ X0 ^ X1 ^ rk[i + 2]
                X2 ^= T0[t >> 24] ^ T1[t >> 16 & 255] ^ T2[t >> 8 & 255] ^ T3[t & 255]
                t = X0 ^ X1 ^ X2 ^ rk[i + 3]
                X3 ^= T0[t >> 24] ^ T1[t >> 16 & 255] ^ T2[t >> 8 & 255] ^ T3[t & 255]
            pack_into('>IIII', out, idx, X3, X2, X1, X0)
            idx += 16
        return bytes(out)

    def encrypt_bulk(self, data: bytes) -> bytes:
        lib = _load_fast_sm4()
        if lib is not None:
            data = bytes(data)
            n = len(data)
            inbuf = ctypes.create_string_buffer(data)
            outbuf = ctypes.create_string_buffer(n)
            lib.sm4_ecb(ctypes.create_string_buffer(self._key), inbuf, outbuf, n, 1)
            return outbuf.raw
        return self._bulk(data, self._rkey)

    def decrypt_bulk(self, data: bytes) -> bytes:
        lib = _load_fast_sm4()
        if lib is not None:
            data = bytes(data)
            n = len(data)
            inbuf = ctypes.create_string_buffer(data)
            outbuf = ctypes.create_string_buffer(n)
            lib.sm4_ecb(ctypes.create_string_buffer(self._key), inbuf, outbuf, n, 0)
            return outbuf.raw
        return self._bulk(data, self._rkey[::-1])


_FAST_SM4_LIB = None
_FAST_SM4_TRIED = False


def _sm4_c_source() -> str:
    sbox = SM4._S_BOX; fk = SM4._FK; ck = SM4._CK
    L = []
    L.append('#include <stdint.h>')
    L.append('#include <stddef.h>')
    L.append('static const uint8_t SBOX[256] = { ' + ', '.join(str(x) for x in sbox) + ' };')
    L.append('static const uint32_t FK[4] = { ' + ', '.join(hex(x) for x in fk) + ' };')
    L.append('static const uint32_t CK[32] = { ' + ', '.join(hex(x) for x in ck) + ' };')
    L.append('static inline uint32_t rotl(uint32_t x, int n){ return (x << n) | (x >> (32 - n)); }')
    L.append('static inline uint32_t load_be(const uint8_t* p){ return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|(uint32_t)p[3]; }')
    L.append('static inline void store_be(uint8_t* p, uint32_t v){ p[0]=(uint8_t)(v>>24); p[1]=(uint8_t)(v>>16); p[2]=(uint8_t)(v>>8); p[3]=(uint8_t)v; }')
    L.append('static inline uint32_t sb(uint32_t x){ return ((uint32_t)SBOX[(x>>24)&0xff]<<24)|((uint32_t)SBOX[(x>>16)&0xff]<<16)|((uint32_t)SBOX[(x>>8)&0xff]<<8)|(uint32_t)SBOX[x&0xff]; }')
    L.append('static inline uint32_t t0(uint32_t x){ x = sb(x); return x ^ rotl(x,2) ^ rotl(x,10) ^ rotl(x,18) ^ rotl(x,24); }')
    L.append('static inline uint32_t t1(uint32_t x){ x = sb(x); return x ^ rotl(x,13) ^ rotl(x,23); }')
    L.append('static void expand(const uint8_t* key, uint32_t rk[32]){')
    L.append('    uint32_t k0 = load_be(key) ^ FK[0];')
    L.append('    uint32_t k1 = load_be(key+4) ^ FK[1];')
    L.append('    uint32_t k2 = load_be(key+8) ^ FK[2];')
    L.append('    uint32_t k3 = load_be(key+12) ^ FK[3];')
    L.append('    for (int i = 0; i < 32; i++){')
    L.append('        k0 ^= t1(k1 ^ k2 ^ k3 ^ CK[i]); rk[i] = k0;')
    L.append('        k1 ^= t1(k2 ^ k3 ^ k0 ^ CK[++i]); rk[i] = k1;')
    L.append('        k2 ^= t1(k3 ^ k0 ^ k1 ^ CK[++i]); rk[i] = k2;')
    L.append('        k3 ^= t1(k0 ^ k1 ^ k2 ^ CK[++i]); rk[i] = k3;')
    L.append('    }')
    L.append('}')
    L.append('static void crypt_block(const uint8_t* in, uint8_t* out, const uint32_t* rk){')
    L.append('    uint32_t x0 = load_be(in);')
    L.append('    uint32_t x1 = load_be(in+4);')
    L.append('    uint32_t x2 = load_be(in+8);')
    L.append('    uint32_t x3 = load_be(in+12);')
    L.append('    for (int i = 0; i < 32; i += 4){')
    L.append('        x0 ^= t0(x1 ^ x2 ^ x3 ^ rk[i]);')
    L.append('        x1 ^= t0(x2 ^ x3 ^ x0 ^ rk[i+1]);')
    L.append('        x2 ^= t0(x3 ^ x0 ^ x1 ^ rk[i+2]);')
    L.append('        x3 ^= t0(x0 ^ x1 ^ x2 ^ rk[i+3]);')
    L.append('    }')
    L.append('    store_be(out, x3); store_be(out+4, x2); store_be(out+8, x1); store_be(out+12, x0);')
    L.append('}')
    L.append('void sm4_ecb(const uint8_t* key, const uint8_t* in, uint8_t* out, size_t len, int encrypt){')
    L.append('    uint32_t rk[32];')
    L.append('    expand(key, rk);')
    L.append('    if (!encrypt){')
    L.append('        for (int i = 0; i < 16; i++){ uint32_t tmp = rk[i]; rk[i] = rk[31-i]; rk[31-i] = tmp; }')
    L.append('    }')
    L.append('    for (size_t off = 0; off < len; off += 16){ crypt_block(in + off, out + off, rk); }')
    L.append('}')
    return '\n'.join(L)


def _load_fast_sm4():
    global _FAST_SM4_LIB, _FAST_SM4_TRIED
    if _FAST_SM4_TRIED:
        return _FAST_SM4_LIB
    _FAST_SM4_TRIED = True
    try:
        cache_dir = WORKSPACE / ".sxg_cache"
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            cache_dir = Path(__file__).resolve().parent

        src_path = cache_dir / ".sm4_fast.c"
        so_path  = cache_dir / ".sm4_fast.so"
        c_src = _sm4_c_source()
        if not src_path.exists() or src_path.read_text() != c_src:
            src_path.write_text(c_src)
        recompile = (not so_path.exists()) or (so_path.stat().st_mtime < src_path.stat().st_mtime)
        if recompile:
            for cc in ('gcc', 'cc', 'clang'):
                try:
                    r = subprocess.run([cc, '-O2', '-shared', '-fPIC', str(src_path), '-o', str(so_path)],
                                       capture_output=True, timeout=120)
                    if r.returncode == 0 and so_path.exists():
                        break
                except Exception:
                    continue
        if not so_path.exists():
            return None
        lib = ctypes.CDLL(str(so_path))
        lib.sm4_ecb.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int]
        lib.sm4_ecb.restype = None
        _FAST_SM4_LIB = lib
        return lib
    except Exception:
        return None


# ============================================================
# READER
# ============================================================
class Reader:
    def __init__(self, buffer, cursor=0):
        self._buffer = buffer
        self._cursor = cursor

    def u1(self, move_cursor=True): return self.unpack('B', move_cursor=move_cursor)[0]
    def u4(self, move_cursor=True): return self.unpack('<I', move_cursor=move_cursor)[0]
    def u8(self, move_cursor=True): return self.unpack('<Q', move_cursor=move_cursor)[0]
    def i4(self, move_cursor=True): return self.unpack('<i', move_cursor=move_cursor)[0]
    def s(self, n: int, move_cursor=True): return self.unpack(f'{n}s', move_cursor=move_cursor)[0]

    def unpack(self, f: str, offset=0, move_cursor=True):
        x = struct.unpack_from(f, self._buffer, self._cursor + offset)
        if move_cursor:
            self._cursor += struct.calcsize(f)
        return x

    def string(self, move_cursor=True) -> str:
        length = self.i4(move_cursor=move_cursor)
        if length == 0:
            return str()
        assert length > 0
        offset = 0 if move_cursor else 4
        return self.unpack(f'{length}s', offset=offset, move_cursor=move_cursor)[0].rstrip(b'\x00').decode(errors='ignore')


# ============================================================
# PAK INFO
# ============================================================
class PakInfo:
    def __init__(self, buffer, keystream: List[int]):
        def decrypt_index_encrypted(x):
            return (x ^ keystream[3]) & 255
        def decrypt_magic(x):
            return x ^ keystream[2]
        def decrypt_index_hash(x):
            key = struct.pack('<5I', *keystream[4:][:5])
            assert len(x) == len(key)
            return bytes((a ^ b for a, b in zip(x, key)))
        def decrypt_index_size(x):
            return x ^ (keystream[10] << 32 | keystream[11])
        def decrypt_index_offset(x):
            return x ^ (keystream[0] << 32 | keystream[1])

        reader = Reader(buffer[-PakInfo._mem_size((-1)):])
        self.index_encrypted = decrypt_index_encrypted(reader.u1()) == 1
        self.magic = decrypt_magic(reader.u4())
        self.version = reader.u4()
        self.index_hash = decrypt_index_hash(reader.s(20)) if self.version >= 6 else bytes()
        self.index_size = decrypt_index_size(reader.u8())
        self.index_offset = decrypt_index_offset(reader.u8())
        if self.version <= 3:
            self.index_encrypted = False

    @staticmethod
    def _mem_size(_): return 45


class TencentPakInfo(PakInfo):
    def __init__(self, buffer, keystream: List[int]):
        def decrypt_unk(x):
            key = struct.pack('<8I', *keystream[7:][:8])
            assert len(x) == len(key)
            return bytes((a ^ b for a, b in zip(x, key)))
        def decrypt_stem_hash(x):
            return x ^ keystream[8]
        def decrypt_unk_hash(x):
            return x ^ keystream[9]

        super().__init__(buffer, keystream)
        reader = Reader(buffer[-TencentPakInfo._mem_size(self.version):])
        self.unk1 = decrypt_unk(reader.s(32)) if self.version >= 7 else bytes()
        self.packed_key = reader.s(256) if self.version >= 8 else bytes()
        self.packed_iv = reader.s(256) if self.version >= 8 else bytes()
        self.packed_index_hash = reader.s(256) if self.version >= 8 else bytes()
        self.stem_hash = decrypt_stem_hash(reader.u4()) if self.version >= 9 else 0
        self.unk2 = decrypt_unk_hash(reader.u4()) if self.version >= 9 else 0
        self.content_org_hash = reader.s(20) if self.version >= 12 else bytes()

    @staticmethod
    def _mem_size(version: int) -> int:
        s7 = 32 if version >= 7 else 0
        s8 = 768 if version >= 8 else 0
        s9 = 8 if version >= 9 else 0
        s12 = 20 if version >= 12 else 0
        return PakInfo._mem_size(version) + s7 + s8 + s9 + s12


class PakCompressedBlock:
    def __init__(self, reader: Reader):
        self.start = reader.u8()
        self.end = reader.u8()


@dataclass
class TencentPakEntry:
    def __init__(self, reader: Reader, version: int):
        self.content_hash = reader.s(20)
        if version <= 1:
            _ = reader.u8()
        self.offset = reader.u8()
        self.uncompressed_size = reader.u8()
        self.compression_method = reader.u4() & CM_MASK
        self.size = reader.u8()
        self.unk1 = reader.u1() if version >= 5 else 0
        self.unk2 = reader.s(20) if version >= 5 else bytes()
        if self.compression_method != 0 and version >= 3:
            self.compressed_blocks = [PakCompressedBlock(reader) for _ in range(reader.u4())]
        else:
            self.compressed_blocks = []
        self.compression_block_size = reader.u4() if version >= 4 else 0
        self.encrypted = reader.u1() == 1 if version >= 4 else False
        self.encryption_method = reader.u4() if version >= 12 else 0
        self.index_new_sep = reader.u4() if version >= 12 else 0


# ============================================================
# PAK CRYPTO
# ============================================================
class PakCrypto:
    class _LCG:
        def __init__(self, seed: int):
            self.state = seed

        def next(self) -> int:
            MASK_32 = 4294967295
            MSB_1 = 2147483648
            def wrap(x):
                x &= MASK_32
                return x if not x & MSB_1 else (x + MSB_1 & MASK_32) - MSB_1
            x1 = wrap(1103515245 * self.state)
            self.state = wrap(x1 + 12345)
            x2 = wrap(x1 + 77880) if self.state < 0 else self.state
            return (x2 >> 16 & MASK_32) % 32767

    @staticmethod
    def zuc_keystream() -> List[int]:
        zuc = gmalg.ZUC(ZUC_KEY, ZUC_IV)
        return [struct.unpack('>I', zuc.generate())[0] for _ in range(16)]

    @staticmethod
    def _xorxor(buffer, x):
        return bytes((buffer[i] ^ x[i % len(x)] for i in range(len(buffer))))

    @staticmethod
    def _hashhash(buffer, n: int) -> bytes:
        result = bytes()
        for i in range(math.ceil(n / SHA1.digest_size)):
            result += SHA1.new(buffer).digest()
        if len(result) >= n:
            return result[:n]
        return result + b'\x00' * (n - len(result))

    @staticmethod
    def _meowmeow(buffer) -> bytes:
        def unpad(x):
            skip = 1 + next((i for i in range(len(x)) if x[i] != 0))
            return x[skip:]
        if len(buffer) < 43:
            return bytes()
        x1 = buffer[1:][:SHA1.digest_size]
        x2 = buffer[SHA1.digest_size + 1:]
        x1 = PakCrypto._xorxor(x1, PakCrypto._hashhash(x2, len(x1)))
        x2 = PakCrypto._xorxor(x2, PakCrypto._hashhash(x1, len(x2)))
        part1, m = (x2[:SHA1.digest_size], x2[SHA1.digest_size:])
        if part1 != SHA1.new(b'\x00' * SHA1.digest_size).digest():
            return bytes()
        return unpad(m)

    @staticmethod
    def rsa_extract(signature: bytes, modulus: bytes) -> bytes:
        c = int.from_bytes(signature, 'little')
        n = int.from_bytes(modulus, 'little')
        e = 65537
        m = pow(c, e, n).to_bytes(256, 'little').rstrip(b'\x00')
        return PakCrypto._meowmeow(Misc.pad_to_n(m, 4))

    @staticmethod
    def _decrypt_simple1(ciphertext) -> bytes:
        return bytes((x ^ SIMPLE1_DECRYPT_KEY for x in ciphertext))

    @staticmethod
    def _decrypt_simple2(ciphertext) -> bytes:
        class RollingKey:
            def __init__(self, v):
                self._value = v
            def update(self, x):
                self._value ^= x
                return self._value
        assert len(ciphertext) % SIMPLE2_BLOCK_SIZE == 0
        initial_key, = struct.unpack('<I', SIMPLE2_DECRYPT_KEY)
        rk = RollingKey(initial_key)
        plaintext = (struct.pack('<I', rk.update(x)) for x in struct.unpack(f'<{len(ciphertext)//4}I', ciphertext))
        return bytes(it.chain.from_iterable(plaintext))

    @staticmethod
    @lru_cache(maxsize=128)
    def _derive_sm4_key(file_path: PurePath, encryption_method: int) -> bytes:
        part1 = file_path.stem.lower()
        if encryption_method == EM_SM4_2:
            secret = SM4_SECRET_2
        else:
            if encryption_method == EM_SM4_4:
                secret = SM4_SECRET_4
            else:
                index = (encryption_method - EM_SM4_NEW_BASE) % len(SM4_SECRET_NEW)
                secret = f'{SM4_SECRET_NEW[index]}{encryption_method}'
        return SHA1.new(str(part1 + secret).encode()).digest()[:SM4.key_length()]

    @staticmethod
    @lru_cache(maxsize=128)
    def _sm4_context_for_key(key: bytes) -> SM4:
        return SM4(key)

    @staticmethod
    def _decrypt_sm4(ciphertext, file_path, encryption_method) -> bytes:
        assert len(ciphertext) % SM4.block_length() == 0
        key = PakCrypto._derive_sm4_key(file_path, encryption_method)
        return PakCrypto._sm4_context_for_key(key).decrypt_bulk(ciphertext)

    @staticmethod
    def decrypt_index(ciphertext, pak_info):
        if pak_info.version > 7:
            key = PakCrypto.rsa_extract(pak_info.packed_key, RSA_MOD_1)
            iv = PakCrypto.rsa_extract(pak_info.packed_iv, RSA_MOD_1)
            assert len(key) == 32 and len(iv) == 32
            aes = AES.new(key, MODE_CBC, iv[:16])
            return unpad(aes.decrypt(ciphertext), AES.block_size)
        return bytes(PakCrypto._decrypt_simple1(ciphertext))

    @staticmethod
    def _is_simple1_method(m): return m == EM_SIMPLE1

    @staticmethod
    def _is_simple2_method(m): return m == EM_SIMPLE2 or m == 17

    @staticmethod
    def _is_sm4_method(m):
        return m == EM_SM4_2 or m == EM_SM4_4 or m & EM_SM4_NEW_MASK != 0

    @staticmethod
    def align_encrypted_content_size(n, m):
        if PakCrypto._is_simple2_method(m):
            return Misc.align_up(n, SIMPLE2_BLOCK_SIZE)
        if PakCrypto._is_sm4_method(m):
            return Misc.align_up(n, SM4.block_length())
        return n

    @staticmethod
    def decrypt_block(ciphertext, file, encryption_method):
        if PakCrypto._is_simple1_method(encryption_method):
            return PakCrypto._decrypt_simple1(ciphertext)
        if PakCrypto._is_simple2_method(encryption_method):
            return PakCrypto._decrypt_simple2(ciphertext)
        if PakCrypto._is_sm4_method(encryption_method):
            return PakCrypto._decrypt_sm4(ciphertext, file, encryption_method)
        raise ValueError(f'Unknown encryption method: {encryption_method}')

    @staticmethod
    @lru_cache(maxsize=33)
    def generate_block_indices(n, encryption_method):
        if not PakCrypto._is_sm4_method(encryption_method):
            return list(range(n))
        perm = []
        lcg = PakCrypto._LCG(n)
        while len(perm) != n:
            x = lcg.next() % n
            if x not in perm:
                perm.append(x)
        inv = [0] * len(perm)
        for i, x in enumerate(perm):
            inv[x] = i
        return inv


# ============================================================
# PAK COMPRESSION
# ============================================================
class PakCompression:
    @staticmethod
    @lru_cache(maxsize=33)
    def _zstd_decompressor(d):
        return ZstdDecompressor(d)

    @staticmethod
    def decompress_block(block, dict, compression_method):
        if compression_method == CM_ZLIB:
            try:
                return zlib.decompress(block)
            except zlib.error:
                return block
        if compression_method in (CM_ZSTD, CM_ZSTD_DICT):
            if compression_method != CM_ZSTD_DICT:
                dict = None
            return PakCompression._zstd_decompressor(dict).decompress(block)
        raise ValueError(f'Unknown compression method: {compression_method}')


# ============================================================
# PAK FILE
# ============================================================
class TencentPakFile:
    def __init__(self, file_path, is_od=False, silent=True):
        self._silent = silent
        self._file_path = file_path
        with open_long(file_path, 'rb') as f:
            self._file_content = memoryview(f.read())
        self._is_od = is_od
        self._mount_point = PurePath()
        self._is_zstd_with_dict = 'zsdic' in str(self._file_path)
        self._zstd_dict = None
        self._zstd_dict_entry = None
        self._files = []
        self._index = {}
        try:
            ks = PakCrypto.zuc_keystream()
        except Exception:
            ks = [0] * 16
        self._pak_info = TencentPakInfo(self._file_content, ks)
        self._verify_stem_hash()
        self._tencent_load_index()

    def _verify_stem_hash(self):
        if not self._is_od and self._pak_info.version >= 9:
            try:
                assert self._pak_info.stem_hash == zlib.crc32(self._file_path.stem.encode('utf-32le'))
            except AssertionError:
                if not self._silent:
                    print_status("PAK filename differs from original stem", "warning")

    def _tencent_load_index(self):
        raw_index = bytes(self._file_content[self._pak_info.index_offset:][:self._pak_info.index_size])

        def _try_aes_decrypt(data, mod):
            try:
                key = PakCrypto.rsa_extract(self._pak_info.packed_key, mod)
                iv = PakCrypto.rsa_extract(self._pak_info.packed_iv, mod)
                if not key or not iv or len(key) < 16 or len(iv) < 16:
                    return None
                aes = AES.new(key, MODE_CBC, iv[:16])
                decrypted = aes.decrypt(data)
                try:
                    result = unpad(decrypted, AES.block_size)
                except Exception:
                    result = decrypted.rstrip(b'\x00')
                    if not result:
                        return None
                r = Reader(result)
                r.string()
                n = r.u4()
                if 0 <= n <= 200000:
                    return result
                return None
            except Exception:
                return None

        candidates = []
        if self._pak_info.index_encrypted:
            d = _try_aes_decrypt(raw_index, RSA_MOD_1)
            if d: candidates.append(d)
            d = _try_aes_decrypt(raw_index, RSA_MOD_2)
            if d: candidates.append(d)
            try:
                candidates.append(PakCrypto._decrypt_simple1(raw_index))
            except Exception:
                pass
        candidates.append(raw_index)

        for data in candidates:
            try:
                self._files = []
                self._index = {}
                self._load_index(data)
                if self._index:
                    return
            except Exception:
                continue

        self._files = []
        self._index = {}

    @staticmethod
    def _construct_mount_point(mp):
        result = PurePath()
        for part in PurePath(mp).parts:
            if part != '..':
                result /= part
        return result

    def _peek_content(self, offset, size, encryption_method):
        size = PakCrypto.align_encrypted_content_size(size, encryption_method)
        return self._file_content[offset:][:size]

    def _peek_block_content(self, block, encryption_method):
        size = PakCrypto.align_encrypted_content_size(block.end - block.start, encryption_method)
        return self._file_content[block.start:][:size]

    def _construct_zstd_dict(self, dict_entry):
        try:
            data = self._peek_content(dict_entry.offset, dict_entry.size, dict_entry.encryption_method)
            if dict_entry.encrypted:
                data = PakCrypto.decrypt_block(data, PurePath("zstddic"), dict_entry.encryption_method)
            reader = Reader(data)
            dict_size = reader.u8()
            _ = reader.u4()
            _ = reader.u4()
            dict_data = reader.s(dict_size)
            if ZstdCompressionDict:
                self._zstd_dict = ZstdCompressionDict(dict_data, DICT_TYPE_AUTO)
        except Exception as e:
            if not self._silent:
                print_status(f"Dictionary Load Error: {e}", "error")

    def _load_index(self, index_data):
        if self._pak_info.version <= 10:
            raise ValueError(f'Unsupported version: {self._pak_info.version}')
        reader = Reader(index_data)
        self._mount_point = self._construct_mount_point(reader.string())
        n_files = min(reader.u4(), 200000)
        self._files = [TencentPakEntry(reader, self._pak_info.version) for _ in range(n_files)]
        dirs_count = min(reader.u8(), 200000)
        for _ in range(dirs_count):
            dir_path = PurePath(reader.string())
            file_count = min(reader.u8(), 200000)
            e = {}
            for _ in range(file_count):
                name = reader.string()
                idx = reader.i4()
                mapped = ~idx
                if 0 <= mapped < len(self._files):
                    e[name] = self._files[mapped]
                else:
                    e[name] = None
            if self._is_zstd_with_dict and dir_path.name == 'zstddic':
                if e:
                    self._zstd_dict_entry = e[[*e.keys()][0]]
                    self._construct_zstd_dict(self._zstd_dict_entry)
                continue
            self._index.update({PurePath(dir_path): e})

    def _write_to_disk(self, file_path, entry):
        encryption_method = entry.encryption_method
        compression_method = entry.compression_method

        file_path = Path(*[str(p).replace('\x00', '') for p in Path(file_path).parts])
        parent_dir = file_path.parent
        os.makedirs(to_long_path(parent_dir), exist_ok=True)

        with open_long(file_path, 'wb') as file:
            if compression_method == CM_NONE:
                data = self._peek_content(entry.offset, entry.size, encryption_method)
                if entry.encrypted:
                    data = PakCrypto.decrypt_block(data, file_path, encryption_method)
                file.write(data[:entry.uncompressed_size])
                return

            if not entry.compressed_blocks:
                if entry.size:
                    data = self._peek_content(entry.offset, entry.size, encryption_method)
                    if entry.encrypted:
                        data = PakCrypto.decrypt_block(data, file_path, encryption_method)
                    data = PakCompression.decompress_block(data, self._zstd_dict, compression_method)
                    file.write(data)
                return

            try:
                for x in PakCrypto.generate_block_indices(len(entry.compressed_blocks), encryption_method):
                    data = self._peek_block_content(entry.compressed_blocks[x], encryption_method)
                    if entry.encrypted:
                        data = PakCrypto.decrypt_block(data, file_path, encryption_method)
                    data = PakCompression.decompress_block(data, self._zstd_dict, compression_method)
                    file.write(data)
            except Exception:
                file.seek(0)
                file.truncate()
                raw = bytearray()
                for blk in entry.compressed_blocks:
                    raw += self._peek_block_content(blk, encryption_method)
                file.write(raw)

    def dump(self, out_path):
        out_path = out_path / self._mount_point
        out_path.mkdir(parents=True, exist_ok=True)
        total_files = sum(len(d) for d in self._index.values())

        if total_files == 0:
            print_warning_panel("NO FILES", "PAK index is empty")
            return False

        print(f"{C.CYAN}[i] PAUSE / RESUME [S]    |    STOP / CANCEL [B]{C.RESET}")
        print()

        is_paused = False
        is_cancelled = False
        done = 0

        for dir_path, dir_content in self._index.items():
            if is_cancelled: break
            current_out_path = out_path / dir_path
            current_out_path.mkdir(parents=True, exist_ok=True)

            for file_name, entry in dir_content.items():
                if is_cancelled: break

                while True:
                    key = check_key_press()
                    if key == 's':
                        is_paused = not is_paused
                        if is_paused:
                            print(f"{C.YELLOW}[!] PAUSED - press S to resume{C.RESET}")
                        else:
                            print(f"{C.GREEN}[+] RESUMED{C.RESET}")
                    elif key == 'b':
                        is_cancelled = True
                        print(f"{C.RED}[X] STOP requested...{C.RESET}")
                        break
                    if not is_paused: break
                    time.sleep(0.1)

                if is_cancelled: break
                if entry is None:
                    done += 1
                    continue

                short_name = file_name if len(file_name) < 55 else file_name[:25] + "..." + file_name[-25:]
                try:
                    self._write_to_disk(current_out_path / file_name, entry)
                    print(f"{C.GREEN}->{C.RESET} {short_name}")
                except Exception as e:
                    print(f"{C.RED}FAIL:{C.RESET} {short_name} ({e})")

                done += 1
                pct = (done * 100) // total_files
                bar_len = 30
                filled = (done * bar_len) // total_files
                bar = '=' * filled + '-' * (bar_len - filled)
                sys.stdout.write(f"\r{C.CYAN}[{bar}] {pct}% ({done}/{total_files}){C.RESET}")
                sys.stdout.flush()

        print()
        if is_cancelled:
            print_warning_panel("EXTRACTION CANCELLED", "Partial files already written.")
            return False
        else:
            print_success_panel("EXTRACTION COMPLETE", f"Successfully unpacked {total_files} files!")
            return True


# ============================================================
# ENCRYPTION HELPERS
# ============================================================
def _encrypt_plaintext(plaintext: bytes, pak_relative_path: PurePath, encryption_method: int) -> bytes:
    if PakCrypto._is_simple1_method(encryption_method):
        return bytes((b ^ SIMPLE1_DECRYPT_KEY for b in plaintext))
    if PakCrypto._is_simple2_method(encryption_method):
        pad_len = -len(plaintext) % SIMPLE2_BLOCK_SIZE
        plaintext += b'\x00' * pad_len
        key, = struct.unpack('<I', SIMPLE2_DECRYPT_KEY)
        rolling = key
        out = []
        for x, in struct.iter_unpack('<I', plaintext):
            c = rolling ^ x
            out.append(c)
            rolling ^= c
        return struct.pack(f'<{len(out)}I', *out)
    if PakCrypto._is_sm4_method(encryption_method):
        key = PakCrypto._derive_sm4_key(pak_relative_path, encryption_method)
        sm4 = PakCrypto._sm4_context_for_key(key)
        pad_len = -len(plaintext) % 16
        if pad_len > 0:
            plaintext = plaintext + b'\x00' * pad_len
        return sm4.encrypt_bulk(plaintext)
    return plaintext


def _best_compress(chunk, cm, zstd_dict=None, fast=False):
    if cm == CM_ZLIB:
        return zlib.compress(chunk, 1 if fast else 9)
    if cm in (CM_ZSTD, CM_ZSTD_DICT):
        zd = zstd_dict if cm == CM_ZSTD_DICT else None
        levels = [6, 3, 1] if fast else [22, 19, 16, 13, 10, 7, 4, 1]
        for lvl in levels:
            try:
                return ZstdCompressor(level=lvl, dict_data=zd, threads=1).compress(chunk)
            except Exception:
                continue
    return chunk


def _pw_string(s):
    if not s:
        return struct.pack('<i', 0)
    b = s.encode('utf-8') + b'\x00'
    return struct.pack('<i', len(b)) + b


def _pw_entry(e, v):
    w = bytearray(e.content_hash)
    w += struct.pack('<Q', e.offset)
    w += struct.pack('<Q', e.uncompressed_size)
    w += struct.pack('<I', e.compression_method)
    w += struct.pack('<Q', e.size)
    if v >= 5:
        w += bytes([e.unk1])
        w += e.unk2
    if e.compression_method != CM_NONE and v >= 3:
        w += struct.pack('<I', len(e.compressed_blocks))
        for b in e.compressed_blocks:
            w += struct.pack('<QQ', b.start, b.end)
    if v >= 4:
        w += struct.pack('<I', e.compression_block_size)
        w += bytes([1 if e.encrypted else 0])
    if v >= 12:
        w += struct.pack('<II', e.encryption_method, e.index_new_sep)
    return bytes(w)


def _get_all_dirs_and_mp(pak_file):
    raw = bytes(pak_file._file_content[pak_file._pak_info.index_offset:][:pak_file._pak_info.index_size])
    if pak_file._pak_info.index_encrypted:
        raw = PakCrypto.decrypt_index(raw, pak_file._pak_info)
    r = Reader(raw)
    mp = r.string()
    num_files = r.u4()
    for _ in range(num_files):
        TencentPakEntry(r, pak_file._pak_info.version)
    dirs = {}
    for _ in range(r.u8()):
        dp = r.string()
        cnt = r.u8()
        dirs[dp] = {r.string(): pak_file._files[~r.i4()] for _ in range(cnt)}
    return mp, dirs


def _write_entry_into_buf(out_buf, ne, new_raw, pak_rel, template_entry, zstd_dict):
    ne.compression_method = template_entry.compression_method
    ne.encryption_method = template_entry.encryption_method
    ne.encrypted = template_entry.encrypted
    ne.unk1 = template_entry.unk1
    ne.index_new_sep = template_entry.index_new_sep
    ne.uncompressed_size = len(new_raw)

    if ne.compression_method == CM_NONE:
        if ne.encrypted:
            padded = new_raw
            if PakCrypto._is_sm4_method(ne.encryption_method):
                pad_len = -len(padded) % 16
                if pad_len > 0:
                    padded = padded + b'\x00' * pad_len
            cipher = _encrypt_plaintext(padded, pak_rel, ne.encryption_method)
        else:
            cipher = new_raw
        ne.offset = len(out_buf)
        ne.size = len(cipher)
        ne.compression_block_size = 0
        ne.compressed_blocks = []
        out_buf += cipher
    else:
        cs = template_entry.compression_block_size if template_entry.compression_block_size > 0 else 65536
        ne.compression_block_size = cs
        chunks = [new_raw[i:i + cs] for i in range(0, len(new_raw), cs)]

        if not chunks:
            ne.compressed_blocks = []
            ne.offset = len(out_buf)
            ne.size = 0
            return

        n = len(chunks)
        cipher_logical = []
        for chunk in chunks:
            compressed = _best_compress(chunk, ne.compression_method, zstd_dict)
            if ne.encrypted:
                if PakCrypto._is_sm4_method(ne.encryption_method):
                    pad_len = -len(compressed) % 16
                    if pad_len > 0:
                        compressed = compressed + b'\x00' * pad_len
                cipher = _encrypt_plaintext(compressed, pak_rel, ne.encryption_method)
            else:
                cipher = compressed
            cipher_logical.append(cipher)

        if ne.encrypted and PakCrypto._is_sm4_method(ne.encryption_method):
            order = PakCrypto.generate_block_indices(n, ne.encryption_method)
        else:
            order = list(range(n))

        phys_cipher = [b''] * n
        for logical_i in range(n):
            phys_cipher[order[logical_i]] = cipher_logical[logical_i]

        phys_blks = []
        for phys_i in range(n):
            bd = phys_cipher[phys_i]
            blk = PakCompressedBlock.__new__(PakCompressedBlock)
            blk.start = len(out_buf)
            blk.end = blk.start + len(bd)
            out_buf += bd
            phys_blks.append(blk)

        logical_blks = [None] * n
        for logical_i in range(n):
            phys_i = order[logical_i]
            logical_blks[logical_i] = phys_blks[phys_i]

        ne.compressed_blocks = logical_blks
        ne.offset = phys_blks[0].start if phys_blks else len(out_buf)
        ne.size = sum(b.end - b.start for b in phys_blks)

    stored_bytes = bytes(out_buf[ne.offset:ne.offset + ne.size])
    ne.content_hash = SHA1.new(stored_bytes).digest()
    ne.unk2 = b'\x00' * 20


def _extract_entry_plaintext(pak_file, entry, full_path):
    em = entry.encryption_method
    cm = entry.compression_method
    path = PurePath(full_path)
    if cm == CM_NONE:
        data = pak_file._peek_content(entry.offset, entry.size, em)
        if entry.encrypted:
            data = PakCrypto.decrypt_block(data, path, em)
        return bytes(data[:entry.uncompressed_size])
    out = bytearray()
    for x in PakCrypto.generate_block_indices(len(entry.compressed_blocks), em):
        data = pak_file._peek_block_content(entry.compressed_blocks[x], em)
        if entry.encrypted:
            data = PakCrypto.decrypt_block(data, path, em)
        out += PakCompression.decompress_block(data, pak_file._zstd_dict, cm)
    return bytes(out)


def _copy_original_content(out_buf, pak_file, ne, old_entry):
    em = old_entry.encryption_method
    if old_entry.compression_method == CM_NONE:
        read_sz = (PakCrypto.align_encrypted_content_size(old_entry.size, em)
                   if old_entry.encrypted else old_entry.size)
        ne.offset = len(out_buf)
        out_buf += bytes(pak_file._file_content[old_entry.offset: old_entry.offset + read_sz])
    elif old_entry.compressed_blocks:
        new_blks = []
        for ob in old_entry.compressed_blocks:
            unc = ob.end - ob.start
            enc = (PakCrypto.align_encrypted_content_size(unc, em)
                   if old_entry.encrypted else unc)
            nb = PakCompressedBlock.__new__(PakCompressedBlock)
            nb.start = len(out_buf)
            nb.end = nb.start + unc
            out_buf += bytes(pak_file._file_content[ob.start: ob.start + enc])
            new_blks.append(nb)
        ne.compressed_blocks = new_blks
        ne.offset = new_blks[0].start
    ne.encryption_method = old_entry.encryption_method
    ne.encrypted = old_entry.encrypted


def _write_pak_index_footer(pak_file, mp_str, all_dirs, new_files, old_to_new, out_buf, output_path):
    version = pak_file._pak_info.version
    keystream = PakCrypto.zuc_keystream()
    eidx = {id(new_files[i]): i for i in range(len(new_files))}
    old_id_to_new_idx = {id(pak_file._files[i]): i for i in range(len(pak_file._files))}

    idx = bytearray(_pw_string(mp_str))
    idx += struct.pack('<I', len(new_files))
    for ne in new_files:
        idx += _pw_entry(ne, version)
    idx += struct.pack('<Q', len(all_dirs))

    for dp_str, dir_files in all_dirs.items():
        idx += _pw_string(dp_str)
        idx += struct.pack('<Q', len(dir_files))
        for name, old_e in dir_files.items():
            idx += _pw_string(name)
            found_idx = eidx.get(id(old_e))
            if found_idx is None:
                found_idx = old_id_to_new_idx.get(id(old_e))
            if found_idx is None:
                copy_of = next((k for k, v in old_to_new.items() if v is old_e), None)
                if copy_of is not None:
                    found_idx = eidx.get(id(old_to_new[copy_of]))
            if found_idx is None:
                for i, e in enumerate(new_files):
                    if e.offset == old_e.offset and e.size == old_e.size:
                        found_idx = i
                        break
            idx += struct.pack('<i', ~found_idx if found_idx is not None else -1)

    index_plain = bytes(idx)
    new_sha1 = SHA1.new(index_plain).digest()

    if pak_file._pak_info.index_encrypted:
        key = PakCrypto.rsa_extract(pak_file._pak_info.packed_key, RSA_MOD_1)
        iv = PakCrypto.rsa_extract(pak_file._pak_info.packed_iv, RSA_MOD_1)
        aes = AES.new(key, MODE_CBC, iv[:16])
        pad_len = (-len(index_plain)) % AES.block_size or AES.block_size
        index_bytes = aes.encrypt(index_plain + bytes([pad_len] * pad_len))
    else:
        index_bytes = index_plain

    new_idx_offset = len(out_buf)
    new_idx_size = len(index_bytes)
    out_buf += index_bytes

    footer_sz = TencentPakInfo._mem_size(version)
    new_footer = bytearray(pak_file._file_content[-footer_sz:])
    h_key = struct.pack('<5I', *keystream[4:9])
    new_footer[-36:-16] = bytes(a ^ b for a, b in zip(new_sha1, h_key))
    new_footer[-16:-8] = ((new_idx_size ^ (keystream[10] << 32 | keystream[11])).to_bytes(8, 'little'))
    new_footer[-8:] = ((new_idx_offset ^ (keystream[0] << 32 | keystream[1])).to_bytes(8, 'little'))
    out_buf += new_footer

    with open(output_path, 'wb') as f:
        f.write(out_buf)


# ============================================================
# HIGH LEVEL OPERATIONS
# ============================================================
def extract_pak(pak_path, unpack_dir):
    pak = TencentPakFile(pak_path)
    out_path = unpack_dir / pak_path.stem
    success = pak.dump(out_path)
    return success, out_path


def inject_files_into_pak(pak_path, edit_dir, result_dir, encrypt_new=True):
    pak = TencentPakFile(pak_path)
    output_pak = result_dir / pak_path.name
    edited, added = inject_edit_files(pak, edit_dir, output_pak, protect_new=encrypt_new, sm4_type=47)
    return output_pak, edited, added


def rebuild_pak(pak_path, edit_dir, result_dir):
    pak = TencentPakFile(pak_path)
    output_pak = result_dir / pak_path.name
    count = repack_pak_file_full(pak, edit_dir, output_pak)
    return output_pak, count


def shield_pak(pak_path, result_dir, sm4_type=47):
    pak = TencentPakFile(pak_path)
    output_pak = result_dir / pak_path.name
    protected, skipped = protect_pak_file(pak, output_pak, sm4_type=sm4_type)
    return output_pak, protected, skipped


def repack_pak_file_full(pak_file, edited_root, output_path, target_path=None, force_add=False):
    import copy as _cp

    print_status("Full Reconstruction Mode", "info")
    if target_path:
        print_status(f"Target path: {target_path}", "info")

    edit_files = [p for p in Path(edited_root).rglob('*') if p.is_file()]
    if not edit_files:
        print_status("No files found in EDIT folder!", "error")
        return 0
    print_status(f"Found {len(edit_files)} files in EDIT folder", "info")

    version = pak_file._pak_info.version
    keystream = PakCrypto.zuc_keystream()
    orig_fc = pak_file._file_content
    mp_str, all_dirs = _get_all_dirs_and_mp(pak_file)

    if target_path and force_add:
        target_path = target_path.replace('\\', '/')
        matched_dir = None
        for existing_dir in all_dirs.keys():
            if existing_dir.strip('/').lower() == target_path.strip('/').lower():
                matched_dir = existing_dir
                break
        if matched_dir:
            target_path = matched_dir
        else:
            target_path = target_path.strip('/') + '/'

    pak_name_map = {}
    for dir_path, files in pak_file._index.items():
        for name, entry in files.items():
            full_path = str(PurePath(dir_path) / name).replace('\\', '/')
            pak_name_map.setdefault(name.lower(), []).append((full_path, entry))

    edited = {}
    for p in edit_files:
        fl = p.name.lower()
        found_match = False

        if fl in pak_name_map:
            cands = pak_name_map[fl]
            if target_path:
                target_candidates = [(fp, e) for fp, e in cands if target_path.strip('/') in fp]
                if target_candidates:
                    sz = p.stat().st_size
                    sm = [(fp, e) for fp, e in target_candidates if e.uncompressed_size == sz]
                    fp, ent = sm[0] if sm else target_candidates[0]
                    edited[fp] = (p, ent)
                    found_match = True

            if not found_match:
                sz = p.stat().st_size
                sm = [(fp, e) for fp, e in cands if e.uncompressed_size == sz]
                fp, ent = sm[0] if sm else cands[0]
                if target_path:
                    edited[f"{target_path.rstrip('/')}/{p.name}"] = (p, ent)
                else:
                    edited[fp] = (p, ent)
                found_match = True

        if not found_match:
            stem = p.stem.lower()
            ext = p.suffix.lower()
            for dir_path, files in pak_file._index.items():
                for name, entry in files.items():
                    if Path(name).stem.lower() == stem and Path(name).suffix.lower() == ext:
                        full_path = str(PurePath(dir_path) / name).replace('\\', '/')
                        if target_path:
                            edited[f"{target_path.rstrip('/')}/{p.name}"] = (p, entry)
                        else:
                            edited[full_path] = (p, entry)
                        found_match = True
                        break
                if found_match:
                    break

        if not found_match and force_add and target_path:
            template_entry = None
            for dir_path, files in pak_file._index.items():
                for name, entry in files.items():
                    if Path(name).suffix.lower() == p.suffix.lower():
                        template_entry = entry
                        break
                if template_entry:
                    break
            if not template_entry:
                for dir_path, files in pak_file._index.items():
                    for name, entry in files.items():
                        template_entry = entry
                        break
                    if template_entry:
                        break
            if template_entry:
                new_fp = f"{target_path.rstrip('/')}/{p.name}"
                edited[new_fp] = (p, template_entry)

    if not edited:
        print_status("No files to repack!", "error")
        return 0
    print_status(f"Files to repack: {len(edited)}", "info")

    new_files = []
    for e in pak_file._files:
        ne = _cp.copy(e)
        ne.compressed_blocks = [_cp.copy(b) for b in e.compressed_blocks]
        new_files.append(ne)
    old_to_new = {id(pak_file._files[i]): new_files[i] for i in range(len(pak_file._files))}

    edited_paths = {fp: p for fp, (p, _) in edited.items()}
    out_buf = bytearray()

    for dp_str, dir_files in list(all_dirs.items()):
        for name, old_entry in list(dir_files.items()):
            full_path = str(PurePath(dp_str) / name).replace('\\', '/')
            ne = old_to_new.get(id(old_entry), None)
            if ne is None:
                ne = _cp.copy(old_entry)
                ne.compressed_blocks = [_cp.copy(b) for b in old_entry.compressed_blocks]
                new_files.append(ne)
                old_to_new[id(old_entry)] = ne

            if full_path in edited_paths:
                p, template = edited[full_path]
                new_raw = p.read_bytes()
                pak_rel = PurePath(full_path)

                fresh = _cp.copy(old_entry)
                fresh.compressed_blocks = []
                _write_entry_into_buf(out_buf, fresh, new_raw, pak_rel, old_entry, pak_file._zstd_dict)
                fresh.unk2 = SHA1.new((mp_str + full_path).lower().encode('utf-8')).digest()

                for i, e in enumerate(new_files):
                    if id(e) == id(old_to_new[id(old_entry)]):
                        new_files[i] = fresh
                        old_to_new[id(old_entry)] = fresh
                        break
                print(f"{C.CYAN}[+] Processed:{C.RESET} {full_path}")
            else:
                _copy_original_content(out_buf, pak_file, ne, old_entry)

    if target_path and force_add:
        for fp, (p, template) in edited.items():
            already_processed = False
            for dp_str, dir_files in all_dirs.items():
                for name in dir_files.keys():
                    if str(PurePath(dp_str) / name).replace('\\', '/') == fp:
                        already_processed = True
                        break
                if already_processed:
                    break
            if not already_processed:
                ne = _cp.copy(template)
                ne.compressed_blocks = []
                new_raw = p.read_bytes()
                pak_rel = PurePath(fp)
                _write_entry_into_buf(out_buf, ne, new_raw, pak_rel, template, pak_file._zstd_dict)
                ne.unk2 = SHA1.new((mp_str + fp).lower().encode('utf-8')).digest()
                new_files.append(ne)
                if target_path not in all_dirs:
                    all_dirs[target_path] = {}
                all_dirs[target_path][p.name] = ne

    _write_pak_index_footer(pak_file, mp_str, all_dirs, new_files, old_to_new, out_buf, output_path)
    return len(edited)


def inject_edit_files(pak_file, edit_root, output_path, protect_new=False, sm4_type=47):
    import copy as _cp
    version = pak_file._pak_info.version

    edit_files = [p for p in Path(edit_root).rglob('*') if p.is_file()]
    if not edit_files:
        raise ValueError(f'No files found in EDIT folder: {edit_root}')

    mp_str, all_dirs = _get_all_dirs_and_mp(pak_file)

    injections = {}
    for p in edit_files:
        rel = p.relative_to(edit_root)
        parts = rel.parts
        file_name = parts[-1]
        rel_dir = '/'.join(parts[:-1]).replace('\\', '/')

        target_dir = _find_existing_dir(all_dirs, rel_dir) if rel_dir.strip('/') else ''
        if target_dir is None:
            target_dir = _normalize_dir_key(rel_dir)

        existing = None
        if target_dir in all_dirs:
            for name, e in list(all_dirs[target_dir].items()):
                if name.lower() == file_name.lower():
                    existing = (name, e)
                    break

        if existing:
            full_path = target_dir + existing[0]
            injections[full_path] = (p, existing[1], False)
        else:
            full_path = target_dir + file_name
            template = _pick_template(pak_file, all_dirs, target_dir, file_name)
            injections[full_path] = (p, template, True)

        print(f"{C.CYAN}[>]{C.RESET} {full_path}")

    new_files = []
    for e in pak_file._files:
        ne = _cp.copy(e)
        ne.compressed_blocks = [_cp.copy(b) for b in e.compressed_blocks]
        new_files.append(ne)
    old_to_new = {id(pak_file._files[i]): new_files[i] for i in range(len(pak_file._files))}

    out_buf = bytearray()
    edited_count = 0
    new_count = 0

    for dp_str, dir_files in list(all_dirs.items()):
        for name, old_entry in list(dir_files.items()):
            full_path = str(PurePath(dp_str) / name).replace('\\', '/')
            ne = old_to_new.get(id(old_entry), None)
            if ne is None:
                ne = _cp.copy(old_entry)
                ne.compressed_blocks = [_cp.copy(b) for b in old_entry.compressed_blocks]
                new_files.append(ne)
                old_to_new[id(old_entry)] = ne

            if full_path in injections:
                p, template, is_new = injections[full_path]
                new_raw = p.read_bytes()
                pak_rel = PurePath(full_path)

                fresh = _cp.copy(old_entry) if not is_new else (_cp.copy(template) if template else None)

                if fresh is None:
                    fresh = TencentPakEntry.__new__(TencentPakEntry)
                    fresh.content_hash = b'\x00' * 20
                    fresh.offset = 0
                    fresh.uncompressed_size = 0
                    fresh.compression_method = CM_NONE
                    fresh.size = 0
                    fresh.unk1 = 0
                    fresh.unk2 = b'\x00' * 20
                    fresh.compressed_blocks = []
                    fresh.compression_block_size = 0
                    fresh.encrypted = False
                    fresh.encryption_method = 0
                    fresh.index_new_sep = 0

                fresh.compressed_blocks = []
                if protect_new and is_new:
                    fresh.encryption_method = sm4_type
                    fresh.encrypted = True

                _write_entry_into_buf(out_buf, fresh, new_raw, pak_rel, fresh, pak_file._zstd_dict)
                fresh.unk2 = SHA1.new((mp_str + full_path).lower().encode('utf-8')).digest()

                if is_new:
                    new_files.append(fresh)
                    dp_key = full_path.rsplit('/', 1)[0] + '/' if '/' in full_path else ''
                    all_dirs.setdefault(dp_key, {})[full_path.rsplit('/', 1)[-1]] = fresh
                    new_count += 1
                else:
                    for i, e in enumerate(new_files):
                        if id(e) == id(old_to_new[id(old_entry)]):
                            new_files[i] = fresh
                            old_to_new[id(old_entry)] = fresh
                            break
                    edited_count += 1

                print(f"{C.GREEN}[+] OK:{C.RESET} {full_path}")
            else:
                _copy_original_content(out_buf, pak_file, ne, old_entry)

    _write_pak_index_footer(pak_file, mp_str, all_dirs, new_files, old_to_new, out_buf, output_path)
    return edited_count, new_count


def protect_pak_file(pak_file, output_path, sm4_type=47):
    import copy as _cp
    version = pak_file._pak_info.version
    mp_str, all_dirs = _get_all_dirs_and_mp(pak_file)

    new_files = []
    for e in pak_file._files:
        ne = _cp.copy(e)
        ne.compressed_blocks = [_cp.copy(b) for b in e.compressed_blocks]
        new_files.append(ne)
    old_to_new = {id(pak_file._files[i]): new_files[i] for i in range(len(pak_file._files))}

    out_buf = bytearray()
    protected = 0
    skipped = 0

    for dp_str, dir_files in list(all_dirs.items()):
        for name, old_entry in list(dir_files.items()):
            full_path = str(PurePath(dp_str) / name).replace('\\', '/')
            ne = old_to_new.get(id(old_entry), None)
            if ne is None:
                ne = _cp.copy(old_entry)
                ne.compressed_blocks = [_cp.copy(b) for b in old_entry.compressed_blocks]
                new_files.append(ne)
                old_to_new[id(old_entry)] = ne

            is_marker = (old_entry.compression_method == CM_NONE and old_entry.size == 0)
            is_zdict = (pak_file._zstd_dict_entry is not None and old_entry is pak_file._zstd_dict_entry)

            if is_marker or is_zdict:
                _copy_original_content(out_buf, pak_file, ne, old_entry)
                skipped += 1
                continue

            try:
                plaintext = _extract_entry_plaintext(pak_file, old_entry, full_path)
            except Exception:
                _copy_original_content(out_buf, pak_file, ne, old_entry)
                skipped += 1
                print(f"{C.RED}[!]{C.RESET} Skipped: {full_path}")
                continue

            fresh = _cp.copy(old_entry)
            fresh.compressed_blocks = []
            fresh.encryption_method = sm4_type
            fresh.encrypted = True
            if fresh.compression_method == CM_NONE:
                fresh.compression_method = CM_ZLIB

            _write_entry_into_buf(out_buf, fresh, plaintext, PurePath(full_path), fresh, pak_file._zstd_dict)

            for i, e in enumerate(new_files):
                if id(e) == id(old_to_new[id(old_entry)]):
                    new_files[i] = fresh
                    old_to_new[id(old_entry)] = fresh
                    break

            protected += 1
            if protected <= 12 or protected % 250 == 0:
                print(f"{C.MAGENTA}[*]{C.RESET} LOCKED: {full_path}")

    _write_pak_index_footer(pak_file, mp_str, all_dirs, new_files, old_to_new, out_buf, output_path)
    return protected, skipped


def _normalize_dir_key(path_str):
    s = str(path_str).replace('\\', '/').strip('/')
    return (s + '/') if s else ''


def _find_existing_dir(all_dirs, want_dir):
    want = _normalize_dir_key(want_dir).strip('/').lower()
    if not want:
        return ''
    for k in all_dirs:
        if k.strip('/').lower() == want:
            return k
    best = None
    for k in all_dirs:
        key = k.strip('/').lower()
        if key and want.endswith('/' + key):
            if best is None or len(key) > len(best):
                best = k
    return best


def _pick_template(pak_file, all_dirs, target_dir, file_name):
    ext = Path(file_name).suffix.lower()
    if target_dir in all_dirs:
        for name, e in all_dirs[target_dir].items():
            if Path(name).suffix.lower() == ext:
                return e
    for dp, files in all_dirs.items():
        for name, e in files.items():
            if Path(name).suffix.lower() == ext:
                return e
    for dp, files in all_dirs.items():
        for name, e in files.items():
            return e
    return pak_file._files[0] if pak_file._files else None


# ============================================================
# FILE SELECTOR (SXG style)
# ============================================================
def display_file_selector(title, folder_path, file_pattern="*.pak"):
    files = list(folder_path.glob(file_pattern))
    if not files:
        files = list(folder_path.glob("*.obb"))
    if not files:
        print(f"{C.RED}[X] No PAK files found in {folder_path}{C.RESET}")
        return None

    print(f"\n{C.CYAN}{C.BOLD}{title}{C.RESET}")
    print(f"{C.DIM}{'-' * 60}{C.RESET}")
    for i, f in enumerate(files, 1):
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {C.GREEN}[{i}]{C.RESET} {f.name}  {C.DIM}({size_mb:.2f} MB){C.RESET}")
    print(f"{C.DIM}{'-' * 60}{C.RESET}")

    try:
        idx = int(input(f"{C.CYAN}Select file number (1-{len(files)}): {C.RESET}")) - 1
        if idx < 0 or idx >= len(files):
            print(f"{C.RED}[X] Invalid selection{C.RESET}")
            return None
        return files[idx]
    except (ValueError, EOFError, KeyboardInterrupt):
        print(f"{C.RED}[X] Please enter a valid number{C.RESET}")
        return None


# ============================================================
# BANNER (SXG style)
# ============================================================
SXG_LOGO = r"""
███████╗██╗  ██╗ ██████╗ 
██╔════╝╚██╗██╔╝██╔════╝ 
███████╗ ╚███╔╝ ██║  ███╗
╚════██║ ██╔██╗ ██║   ██║
███████║██╔╝ ██╗╚██████╔╝
╚══════╝╚═╝  ╚═╝ ╚═════╝ 
"""


def print_banner():
    clr()
    print(f"{C.RED}{C.BOLD}{SXG_LOGO}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}        SXG BYPASS TOOL v1.0{C.RESET}")
    print(f"{C.YELLOW}   CREDIT: TG BY ~ @BAAPU_OWNER1{C.RESET}")
    print(f"{C.GREEN}{'=' * 50}{C.RESET}")
    print(f"{C.YELLOW}Fixed Workspace: {C.RESET}{WORKSPACE}")
    print(f"{C.GREEN}Storage Access Granted{C.RESET}")
    print()


# ============================================================
# KEY SCREEN
# ============================================================
def show_key_screen(key_sys: KeySystem) -> bool:
    clr()
    active, msg = key_sys.is_activated()
    if active:
        return True

    print(f"{C.RED}{C.BOLD}{SXG_LOGO}{C.RESET}")
    print(f"{C.CYAN}{C.BOLD}        SXG BYPASS TOOL v1.0{C.RESET}")
    print(f"{C.YELLOW}   CREDIT: TG BY ~ @BAAPU_OWNER1{C.RESET}")
    print(f"{C.GREEN}{'=' * 50}{C.RESET}")
    print()
    print(f"{C.RED}{C.BOLD}[!] LICENSE REQUIRED{C.RESET}")
    print(f"{C.YELLOW}{'-' * 50}{C.RESET}")
    print(f"  Key Name  : {C.GREEN}{KeySystem.KEY_NAME}{C.RESET}")
    print(f"  Validity  : {C.GREEN}1 Day (24 Hours){C.RESET}")
    mode_str = 'MULTI-DEVICE' if KeySystem.MULTI_DEVICE_ENABLED else '1 DEVICE LOCK'
    print(f"  Mode      : {C.GREEN}{mode_str}{C.RESET}")
    print(f"  Device ID : {C.CYAN}{key_sys.device_id[:20]}...{C.RESET}")
    print(f"{C.YELLOW}{'-' * 50}{C.RESET}")
    print()

    if msg and "No license found" not in msg:
        print(f"{C.RED}[X] {msg}{C.RESET}")
        print()

    try:
        user_key = input(f"{C.CYAN}Enter Key: {C.RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        return False

    if not user_key:
        print(f"{C.RED}[X] No key entered!{C.RESET}")
        time.sleep(1.5)
        return False

    ok, msg = key_sys.activate(user_key)

    if ok:
        print()
        print(f"{C.GREEN}{C.BOLD}[+] {msg}{C.RESET}")
        print(f"{C.GREEN}[+] Valid for: 1 Day (24 Hours){C.RESET}")
        print(f"{C.GREEN}[+] Device: {key_sys.device_id[:16]}...{C.RESET}")
        time.sleep(1.8)
        return True
    else:
        print()
        print(f"{C.RED}{C.BOLD}[X] Activation Failed!{C.RESET}")
        for line in msg.split('\n'):
            print(f"{C.RED}    {line}{C.RESET}")
        time.sleep(2.5)
        return False


# ============================================================
# MAIN MENU
# ============================================================
def main_menu(key_sys=None):
    # Initialize workspace & folders & credit file
    init_workspace()

    pak_dir    = WORKSPACE / "PAK"
    edit_dir   = WORKSPACE / "EDIT"
    unpack_dir = WORKSPACE / "UNPACK"
    result_dir = WORKSPACE / "RESULT"

    while True:
        print_banner()

        print(f"{C.CYAN}{C.BOLD}TOOLS{C.RESET}")
        print(f"  {C.GREEN}[1]{C.RESET} PAK UNPACK         {C.DIM}(PAK -> UNPACK folder){C.RESET}")
        print(f"  {C.GREEN}[2]{C.RESET} ENCRYPT LUA        {C.DIM}(EDIT -> PAK, modify existing){C.RESET}")
        print(f"  {C.GREEN}[3]{C.RESET} PAK REPACK        {C.DIM}(EDIT -> PAK, full reconstruction){C.RESET}")
        print(f"  {C.GREEN}[4]{C.RESET} TARGETED DEPLOY     {C.DIM}(EDIT -> PAK at specific path){C.RESET}")
        print(f"  {C.GREEN}[5]{C.RESET} CIPHER SHIELD       {C.DIM}(Encrypt all files with SM4){C.RESET}")
        print(f"  {C.GREEN}[9]{C.RESET} SHOW FOLDERS        {C.DIM}(Open folder locations){C.RESET}")
        print(f"  {C.GREEN}[0]{C.RESET} TERMINATE           {C.DIM}(Close the tool){C.RESET}")
        print()

        try:
            choice = input(f"{C.CYAN}Select option: {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        # ---- 1. EXTRACT ----
        if choice == '1':
            print_header("PAK UNPACK", "Extract all files from PAK to UNPACK folder")

            pak_file = display_file_selector("Select PAK to EXTRACT:", pak_dir, "*.pak")
            if not pak_file:
                pak_file = display_file_selector("Select PAK to EXTRACT:", pak_dir, "*.obb")
            if not pak_file:
                safe_input('\nPress Enter to continue...')
                continue

            try:
                print_status(f'Extracting {pak_file.name}...', "processing")
                success, out_path = extract_pak(pak_file, unpack_dir)
                if success:
                    print_success_panel("SUCCESS", f"Extracted to:\n{out_path}")
                else:
                    print_warning_panel("PARTIAL", "Extraction stopped by user.")
            except Exception as e:
                print_error_panel("ERROR", str(e))
                import traceback
                traceback.print_exc()
            safe_input('\nPress Enter to continue...')

        # ---- 2. INJECT ----
        elif choice == '2':
            print_header("ENCRYPT LUA", "Modify existing files in PAK with EDIT folder contents")

            pak_file = display_file_selector("Select PAK to INJECT INTO:", pak_dir, "*.pak")
            if not pak_file:
                pak_file = display_file_selector("Select PAK to INJECT INTO:", pak_dir, "*.obb")
            if not pak_file:
                safe_input('\nPress Enter...')
                continue

            if not edit_dir.exists() or not any(edit_dir.iterdir()):
                print_error_panel("NO FILES", f"EDIT folder is empty!\nPlace modified files in:\n{edit_dir}")
                safe_input('\nPress Enter...')
                continue

            encrypt_new = confirm("Encrypt new files with SM4?", default=True)

            try:
                print_status(f'Injecting into {pak_file.name}...', "processing")
                output_pak, edited, added = inject_files_into_pak(pak_file, edit_dir, result_dir, encrypt_new)
                print()
                print_success_panel(
                    "INJECTION COMPLETE",
                    f"Edited: {edited} files\nAdded: {added} files\n\nOutput:\n{output_pak}"
                )
            except Exception as e:
                print_error_panel("INJECT FAILED", str(e))
                import traceback
                traceback.print_exc()
            safe_input('\nPress Enter...')

        # ---- 3. PAK REPACK ----
        elif choice == '3':
            print_header("PAK REPACK", "Rebuild PAK completely from EDIT folder")

            pak_file = display_file_selector("Select PAK to REBUILD:", pak_dir, "*.pak")
            if not pak_file:
                pak_file = display_file_selector("Select PAK to REBUILD:", pak_dir, "*.obb")
            if not pak_file:
                safe_input('\nPress Enter...')
                continue

            if not edit_dir.exists() or not any(edit_dir.iterdir()):
                print_error_panel("NO FILES", f"EDIT folder is empty!\nPlace modified files in:\n{edit_dir}")
                safe_input('\nPress Enter...')
                continue

            try:
                print_status(f'Rebuilding {pak_file.name}...', "processing")
                output_pak, count = rebuild_pak(pak_file, edit_dir, result_dir)
                if count > 0:
                    print_success_panel("REBUILD COMPLETE", f"Rebuilt {count} files!\n\nOutput:\n{output_pak}")
                else:
                    print_error_panel("FAILED", "No files rebuilt!")
            except Exception as e:
                print_error_panel("REBUILD FAILED", str(e))
                import traceback
                traceback.print_exc()
            safe_input('\nPress Enter...')

        # ---- 4. TARGETED DEPLOY ----
        elif choice == '4':
            print_header("TARGETED DEPLOY", "Add files to a specific path inside PAK")

            pak_file = display_file_selector("Select PAK:", pak_dir, "*.pak")
            if not pak_file:
                pak_file = display_file_selector("Select PAK:", pak_dir, "*.obb")
            if not pak_file:
                safe_input('\nPress Enter...')
                continue

            if not edit_dir.exists() or not any(edit_dir.iterdir()):
                print_error_panel("NO FILES", f"EDIT folder is empty!\nPlace files in:\n{edit_dir}")
                safe_input('\nPress Enter...')
                continue

            print()
            print(f"{C.CYAN}{C.BOLD}Enter the target path inside the PAK:{C.RESET}")
            print(f"{C.DIM}Example: Content/Lua/GameLua/Mod/BRMod/Gameplay/Core{C.RESET}")
            print(f"{C.DIM}Files from EDIT will be placed here{C.RESET}")
            target_path = safe_input(f"{C.CYAN}Path: {C.RESET}").strip()

            if not target_path:
                print_error_panel("NO PATH", "No path provided!")
                safe_input('\nPress Enter...')
                continue

            target_path = target_path.replace('\\', '/').strip('/')

            try:
                print_status(f'Deploying to {target_path}...', "processing")
                pak = TencentPakFile(pak_file)
                output_pak = result_dir / pak_file.name
                count = repack_pak_file_full(pak, edit_dir, output_pak, target_path, force_add=True)
                if count > 0:
                    print_success_panel(
                        "DEPLOY COMPLETE",
                        f"Processed {count} files to:\n{target_path}\n\nOutput:\n{output_pak}"
                    )
            except Exception as e:
                print_error_panel("FAILED", str(e))
                import traceback
                traceback.print_exc()
            safe_input('\nPress Enter...')

        # ---- 5. CIPHER SHIELD ----
        elif choice == '5':
            print_header("CIPHER SHIELD", "Re-encrypt EVERY file with SM4 encryption")

            pak_file = display_file_selector("Select PAK to SHIELD:", pak_dir, "*.pak")
            if not pak_file:
                pak_file = display_file_selector("Select PAK to SHIELD:", pak_dir, "*.obb")
            if not pak_file:
                safe_input('\nPress Enter...')
                continue

            print()
            print_status("This will re-encrypt ALL files with SM4", "warning")
            print_status("Make sure you have a backup!", "warning")
            print()

            if not confirm("Start CIPHER SHIELD?", default=False):
                print_status("Cancelled.", "warning")
                safe_input('\nPress Enter...')
                continue

            try:
                print_status(f'Shielding {pak_file.name}...', "processing")
                output_pak, protected, skipped = shield_pak(pak_file, result_dir, sm4_type=47)
                print()
                print_success_panel(
                    "SHIELD COMPLETE",
                    f"Protected: {protected} files (SM4)\nSkipped: {skipped} files\n\nOutput:\n{output_pak}"
                )
            except Exception as e:
                print_error_panel("SHIELD FAILED", str(e))
                import traceback
                traceback.print_exc()
            safe_input('\nPress Enter...')

        # ---- 9. SHOW FOLDERS ----
        elif choice == '9':
            print_header("FOLDER LOCATIONS", "Working directories")
            print()
            print(f"  {C.GREEN}PAK{C.RESET}     -> Place your .pak/.obb files here   {C.DIM}{pak_dir}{C.RESET}")
            print(f"  {C.GREEN}EDIT{C.RESET}    -> Place modified files here       {C.DIM}{edit_dir}{C.RESET}")
            print(f"  {C.GREEN}UNPACK{C.RESET}  -> Extracted files appear here     {C.DIM}{unpack_dir}{C.RESET}")
            print(f"  {C.GREEN}RESULT{C.RESET}  -> Final output PAK files          {C.DIM}{result_dir}{C.RESET}")
            print(f"  {C.GREEN}CREDIT{C.RESET}  -> Auto-created credit file      {C.DIM}{WORKSPACE / CREDIT_FILE_NAME}{C.RESET}")
            print()
            safe_input('Press Enter...')

        # ---- 0. EXIT ----
        elif choice == '0':
            print()
            print_success_panel("GOODBYE", "Thank you for using UltimateEngine LITE!")
            time.sleep(1.2)
            break
        else:
            print(f"{C.RED}[X] Invalid option!{C.RESET}")
            time.sleep(0.8)


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == '__main__':
    try:
        # 🔐 KEY SYSTEM - FIRST CHECK
        key_sys = KeySystem()
        active, msg = key_sys.is_activated()

        if not active:
            attempts = 0
            while not active:
                ok = show_key_screen(key_sys)
                if ok:
                    break
                attempts += 1
                if attempts >= 3:
                    print(f"\n{C.RED}[X] Too many failed attempts. Exiting...{C.RESET}")
                    time.sleep(2)
                    sys.exit(1)
                time.sleep(0.5)
                active, _ = key_sys.is_activated()

        # Show license status
        active, msg = key_sys.is_activated()
        if active:
            clr()
            print(f"{C.GREEN}{C.BOLD}[+] LICENSE ACTIVE{C.RESET}")
            print(f"{C.CYAN}    {msg}{C.RESET}")
            time.sleep(1.2)

        # ✅ Ab original tool chalao
        main_menu(key_sys)

    except KeyboardInterrupt:
        print(f'\n{C.CYAN}Interrupted. Exiting...{C.RESET}')
        sys.exit(0)
    except Exception as e:
        print_error_panel("FATAL ERROR", str(e))
        import traceback
        traceback.print_exc()
        safe_input('\nPress Enter to exit...')
        sys.exit(1)
