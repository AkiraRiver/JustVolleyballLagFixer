"""Helpers shared by optim.py: find the game's PCK key, decompile with GDRE
Tools, apply text patches to scripts, rebuild the PCK."""

import hashlib
import os
import re
import struct
import subprocess
import sys

# set by optim.py
GDRE = ""
WORK = ""
KEY_CACHE = ""
EXE_NAME = ""
GAME_DIR = ""
BUILD_ID = "dev"
VERBOSE = False


def die(msg):
    print("\nERROR: " + msg)
    sys.exit(1)


def step(msg):
    if VERBOSE:
        print("== " + msg, flush=True)


# ---------------------------------------------------------------- patches
# Each patch finds one snippet of a decompiled script and replaces it.
# Snippets are written with 4-space indents and turned into the game's tabs.

def _tabs(s):
    s = s.strip("\n")
    return "\n".join(re.sub(r"^((?:    )+)", lambda m: "\t" * (len(m.group(1)) // 4), l)
                     for l in s.split("\n"))


def P(file, name, find, replace):
    return {"file": file, "name": name, "find": _tabs(find), "replace": _tabs(replace)}


def source_pck(steam_dir):
    """The game's data: <exe>.pck next to the exe (full game since Nov 2026), else embedded."""
    sep = os.path.join(steam_dir, os.path.splitext(EXE_NAME)[0] + ".pck")
    return sep if os.path.exists(sep) else None


def _pck_directory(data):
    if data[:4] == b"GDPC":
        pck = 0  # stand-alone .pck
    elif data[-4:] == b"GDPC":
        pck_size = struct.unpack_from("<Q", data, len(data) - 12)[0]
        pck = len(data) - 12 - pck_size
    else:
        die("no PCK found (did the game format change?)")
    dir_off = struct.unpack_from("<Q", data, pck + 32)[0]
    d = pck + dir_off + 4  # skip the plaintext file count
    md5 = data[d:d + 16]
    length = struct.unpack_from("<Q", data, d + 16)[0]
    iv = data[d + 24:d + 40]
    ct = data[d + 40:d + 40 + ((length + 15) & ~15)]
    return pck, md5, length, iv, ct


def find_key(exe, pck_file=None):
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except ImportError:
        die("python module 'cryptography' missing: pip install cryptography")
    data = open(exe, "rb").read()
    if pck_file:
        _, md5, length, iv, ct = _pck_directory(open(pck_file, "rb").read())
        pck = len(data)  # the whole exe is code/data then
    else:
        pck, md5, length, iv, ct = _pck_directory(data)

    def full(key):
        dec = Cipher(algorithms.AES(key), modes.CFB(iv)).decryptor()
        return hashlib.md5(dec.update(ct)[:length]).digest() == md5

    if os.path.exists(KEY_CACHE):
        key = bytes.fromhex(open(KEY_CACHE).read().strip())
        if full(key):
            return key.hex()
        print("the game's key changed, looking for the new one (1-3 min)...")

    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt = struct.unpack_from("<H", data, pe + 20)[0]
    secs = []
    for i in range(nsec):
        o = pe + 24 + opt + i * 40
        name = data[o:o + 8].rstrip(b"\0").decode(errors="replace")
        rsize, rptr = struct.unpack_from("<II", data, o + 16)
        secs.append((name, rptr, rsize))
    # the key has always been in .data; try it first
    secs.sort(key=lambda s: {".data": 0, ".rdata": 1}.get(s[0], 2))
    for name, start, size in secs:
        if start >= pck or name == "pck":
            continue
        step("scan " + name)
        for off in range(start, min(start + size, pck) - 32):
            key = data[off:off + 32]
            if key.count(0) > 4 or len(set(key)) < 20:
                continue
            ks = Cipher(algorithms.AES(key), modes.ECB()).encryptor().update(iv)
            b = bytes(x ^ y for x, y in zip(ks, ct[:16]))
            # first entry: u32 path length (small), then printable path chars
            if b[2] or b[3] or not all(32 <= c < 127 for c in b[4:16]):
                continue
            if full(key):
                step("key found at 0x%x" % off)
                open(KEY_CACHE, "w").write(key.hex())
                return key.hex()
    die("AES key not found in the exe")


def _loose(find):
    # blank-line runs and trailing spaces may differ between builds
    out = [re.escape(l.rstrip()) + r"[ \t]*" for l in find.split("\n") if l.strip()]
    return r"\n(?:[ \t]*\n)*".join(out)


def _read(path):
    return open(path, encoding="utf-8", newline="").read().replace("\r\n", "\n")


def patch_tree(src_root, patches, new_files, files_dir, fresh=True):
    """Apply patches to the .gd files under src_root in place."""
    texts = {}
    for p in patches:
        f = p["file"]
        if f not in texts:
            path = os.path.join(src_root, f)
            if not os.path.exists(path):
                die("script not found in the game: " + f)
            texts[f] = _read(path)
            if fresh and "[lag fixer]" in texts[f]:
                die(f + " is already patched")
        hits = list(re.finditer(_loose(p["find"]), texts[f]))
        if not hits and p.get("optional"):
            step("skip %-12s %s (not in this game version)" % (os.path.basename(f), p["name"]))
            continue
        if len(hits) != 1:
            die("patch '%s' (%s): %d matches instead of 1.\n"
                "The game changed there; tools/perf_patches.py needs an update."
                % (p["name"], f, len(hits)))
        m = hits[0]
        texts[f] = texts[f][:m.start()] + p["replace"] + texts[f][m.end():]
        step("ok  %-14s %s" % (os.path.basename(f), p["name"]))
    for f, text in texts.items():
        with open(os.path.join(src_root, f), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    for f in new_files:
        dst = os.path.join(src_root, f)
        if os.path.exists(dst):
            die("the game now ships a file " + f + " (conflicts with the mod)")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        text = _read(os.path.join(files_dir, f)).replace("__BUILD_ID__", BUILD_ID)
        with open(dst, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)


def gdre(args, log):
    with open(log, "w", encoding="utf-8", errors="replace") as out:
        subprocess.run([GDRE, "--headless"] + args, stdout=out, stderr=subprocess.STDOUT)
    return open(log, encoding="utf-8", errors="replace").read()


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def write_override(threaded=True):
    """override.cfg next to the exe (Godot reads it at startup). No render
    thread when the player runs OpenGL or left a no_render_thread.txt file."""
    path = os.path.join(GAME_DIR, "override.cfg")
    text = OVERRIDE_BASE
    if threaded and not os.path.exists(os.path.join(GAME_DIR, "no_render_thread.txt")):
        text += OVERRIDE_THREAD
    with open(path, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(text)


OVERRIDE_BASE = """; [lag fixer] engine settings for this copy (Godot reads override.cfg next to the exe)
; the game log is written line by line, so it is complete even after a crash
[application]

run/flush_stdout_on_print=true
"""

OVERRIDE_THREAD = """
; rendering on its own thread: ~+30% fps when hosting 4v4 (Godot still calls it experimental).
; Crashes or glitches? create an empty file no_render_thread.txt in this folder
; and run JV_Optim.exe again (or delete the 3 lines below).
[rendering]

driver/threads/thread_model=2
"""

