# -*- coding: utf-8 -*-
"""Shift-free brand patch for the NovaFlow (rebranded DSH mobile) Hermes bundle.

Strategy: Hermes string storage shares bytes between entries (substring dedupe +
boundary sharing), so every write must keep every referenced byte exactly where
it is. We therefore only rewrite whole greeting lines inside the big about
bodies (same total length), shorten the Spanish WeChat a11y string via its
overflow length field, and repoint the DEFAULT_BRAND_NAME entry to an existing
"NovaFlow" string.
"""
import hashlib
import io
import os
import struct
import sys

import hermes_dec.parsers.hbc_file_parser as hfp

BUNDLE = r"C:\Users\mo\cluade\apk-rebrand\assets\index.android.bundle"
HBCReader = hfp.HBCReader

rec = {}


def _wrap(name):
    orig = getattr(HBCReader, name)

    def f(self, *a, **k):
        r = orig(self, *a, **k)
        rec[name] = self.file_buffer.tell()
        return r

    setattr(HBCReader, name, f)


for _n in ("read_small_string_table", "read_overflow_string_table", "read_string_storage"):
    _wrap(_n)

data = open(BUNDLE, "rb").read()
r = HBCReader()
r.read_whole_file(io.BytesIO(data))

n_strings = r.header.stringCount
n_over = r.header.overflowStringCount
storage_size = r.header.stringStorageSize
small_off = rec["read_small_string_table"] - n_strings * 4
over_off = rec["read_overflow_string_table"] - n_over * 8
storage_off = rec["read_string_storage"] - storage_size
print("small@%d over@%d storage@%d" % (small_off, over_off, storage_off))


def entry(i):
    v = struct.unpack_from("<I", data, small_off + 4 * i)[0]
    is_u16 = v & 1
    off = (v >> 1) & 0x7FFFFF
    ln = (v >> 24) & 0xFF
    if ln == 0xFF:
        ovidx = off
        ov_off, ov_len = struct.unpack_from("<II", data, over_off + 8 * ovidx)
        return is_u16, ov_off, ov_len, ovidx
    return is_u16, off, ln, None


ABOUT = [16337, 16398, 16399, 16400, 16402, 16404, 16405, 16411, 16416, 16419, 16427]
GREETINGS = {
    16337: "Willkommen, NovaFlow!",
    16398: "Bienvenue, NovaFlow",
    16399: "Hi from NovaFlow",
    16400: "Te damos la bienvenida,NovaFlow",
    16402: "NovaFlow'ı kullanın, teşekkürler",
    16404: "Bem-vindo, NovaFlow",
    16405: "Добро пожаловать NovaFlow",
    16411: "NovaFlowようこそ",
    16416: "欢迎使用NovaFlow",
    16419: "歡迎使用NovaFlow",
    16427: "NovaFlow 사용해 주셔서 감사합니다",
}


def new_about(i, s):
    lines = s.split("\n")
    assert len(lines) >= 3, i
    old = lines[2]
    new = GREETINGS[i]
    if len(new) > len(old):
        raise SystemExit("#%d greeting too long: %r (%d>%d)" % (i, new, len(new), len(old)))
    new += " " * (len(old) - len(new))
    lines[2] = new
    out = "\n".join(lines)
    assert len(out) == len(s)
    return out


ES_WECHAT = "Código QR del grupo WeChat: escanea con WeChat y únete al grupo NovaFlow"
COPYRIGHT = "NovaFlow 2026"
BRAND_IDX = 4138
TARGET_BRAND_IDX = 4152


def encode(s, is_u16):
    if is_u16:
        return s.encode("utf-16-le")
    return bytes(ord(c) for c in s)


out = bytearray(data)
intended = set()

for i in ABOUT:
    is_u16, off, ln, _ = entry(i)
    s = r.strings[i]
    ns = new_about(i, s)
    b = encode(ns, is_u16)
    assert len(b) == ln * (2 if is_u16 else 1)
    out[storage_off + off:storage_off + off + len(b)] = b
    intended.add(i)

is_u16, off, ln, ovidx = entry(16716)
assert is_u16 and ovidx is not None, "16716 layout changed"
new_es = ES_WECHAT + " " * (74 - len(ES_WECHAT))
assert len(new_es) <= 74
b = new_es.encode("utf-16-le")
out[storage_off + off:storage_off + off + len(b)] = b
if len(new_es) != ln:
    struct.pack_into("<I", out, over_off + 8 * ovidx + 4, len(new_es))
intended.add(16716)

is_u16, off, ln, ovidx = entry(16717)
assert is_u16 and ln == 13
b = COPYRIGHT.encode("utf-16-le")
out[storage_off + off:storage_off + off + len(b)] = b
intended.add(16717)

_, tgt_off, tgt_len, tgt_ov = entry(TARGET_BRAND_IDX)
assert r.strings[TARGET_BRAND_IDX] == "NovaFlow" and tgt_ov is None and tgt_len == 8
v = (tgt_off << 1) | (8 << 24)
struct.pack_into("<I", out, small_off + 4 * BRAND_IDX, v)
intended.add(BRAND_IDX)

# 5) remaining ASCII WeChat a11y strings: shrink length so the last (shared)
#    boundary byte stays untouched, then write the new text into the freed span.
A11Y_ASCII = {
    4137: (76, "Code QR du groupe WeChat : scanne avec WeChat, groupe NovaFlow"),
    5776: (76, "QR code do grupo WeChat: use o WeChat, grupo NovaFlow"),
    13419: (58, "WeChat group QR code: scan with WeChat, join NovaFlow"),
    14994: (74, "WeChat-Gruppen-QR-Code: mit WeChat scannen, Gruppe NovaFlow"),
}
for i, (newlen, text) in A11Y_ASCII.items():
    is_u16, off, ln, ovidx = entry(i)
    assert not is_u16 and ovidx is None, (i, is_u16, ovidx)
    assert newlen <= ln, (i, newlen, ln)
    t = text + " " * (newlen - len(text))
    assert len(t) == newlen
    out[storage_off + off:storage_off + off + newlen] = t.encode("latin-1")
    if newlen != ln:
        v = struct.unpack_from("<I", data, small_off + 4 * i)[0]
        struct.pack_into("<I", out, small_off + 4 * i, (v & ~(0xFF << 24)) | (newlen << 24))
    intended.add(i)

out[-20:] = hashlib.sha1(bytes(out[:-20])).digest()
r2 = HBCReader()
r2.read_whole_file(io.BytesIO(bytes(out)))
changed = {i for i in range(n_strings) if r.strings[i] != r2.strings[i]}
print("intended:", sorted(intended))
print("changed :", sorted(changed))
unexpected = changed - intended
print("unexpected:", sorted(unexpected))
for i in sorted(unexpected):
    print("  #%d %r -> %r" % (i, r.strings[i][:70], r2.strings[i][:70]))
print("brand now:", repr(r2.strings[BRAND_IDX]))
print("about now:", repr(r2.strings[16399][:90]))
print("es wechat now: len=%d %r" % (len(r2.strings[16716]), r2.strings[16716][:80]))
print("copyright now:", repr(r2.strings[16717]))
print("16718 now:", repr(r2.strings[16718]))
print("AI-HUB left in data:", bytes(out).count(b"AI-HUB"))

if os.environ.get("SIMULATE") == "1":
    print("SIMULATE=1 -> not writing")
    raise SystemExit(0 if not unexpected else 2)

final = bytes(out)
open(BUNDLE, "wb").write(final)
print("written size", len(final), "sha256", hashlib.sha256(final).hexdigest())
print("trailer sha1", hashlib.sha1(final[:-20]).hexdigest())
