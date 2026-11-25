"""just volleyball - optimisation only (no F7/F8, no matchmaking changes).

Builds a faster copy of YOUR installed game next to this program
(finds it through the Steam registry key and libraryfolders.vdf):
  game_full\volleyball_optim.exe       (full game, if installed)
  game_demo\volleyballdemo_optim.exe   (demo, if installed)
The Steam install is never modified. Run it again after each game update.
"""

import hashlib
import os
import shutil
import sys
import traceback

FROZEN = getattr(sys, "frozen", False)
PKG = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
TOOLS = os.path.join(PKG, "tools")
sys.path.insert(0, TOOLS)

import jvpatch as m  # noqa: E402  (key, patching, gdre)
from perf_patches import PERF_PATCHES, PERF_FILES  # noqa: E402

VERSION = "optim-1"
EDITIONS = {
    "full": ("just volleyball", "volleyball.exe", "volleyball_optim.exe", "5037200", "game_full"),
    "demo": ("just volleyball Demo", "volleyballdemo.exe", "volleyballdemo_optim.exe", "5401090", "game_demo"),
}

m.WORK = os.path.join(PKG, "_work")
m.GDRE = os.path.join(TOOLS, "gdre", "gdre_tools.exe")
MOD_FILES = os.path.join(TOOLS, "mod_files")
m.KEY_CACHE = os.path.join(TOOLS, "key.txt")


def steam_libraries():
    roots = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for name in ("SteamPath", "InstallPath"):
                        try:
                            roots.append(os.path.normpath(winreg.QueryValueEx(k, name)[0]))
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    roots += [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]
    libs = []
    for r in roots:
        vdf = os.path.join(r, "steamapps", "libraryfolders.vdf")
        libs.append(r)
        if os.path.exists(vdf):
            for line in open(vdf, encoding="utf-8", errors="replace"):
                line = line.strip()
                if line.startswith('"path"'):
                    libs.append(os.path.normpath(line.split('"')[3].replace("\\\\", "\\")))
    out = []
    for l in libs:
        if l.lower() not in [x.lower() for x in out] and os.path.isdir(l):
            out.append(l)
    return out


def find_game(folder):
    for lib in steam_libraries():
        p = os.path.join(lib, "steamapps", "common", folder)
        if os.path.isdir(p):
            return p
    return None


def files_version():
    h = hashlib.sha256(VERSION.encode())
    for f in PERF_FILES:
        h.update(open(os.path.join(MOD_FILES, f), "rb").read())
    for p in PERF_PATCHES:
        h.update((p["find"] + p["replace"]).encode())
    return h.hexdigest()[:16]


def build(edition, steam_dir):
    folder, exe_name, out_name, app_id, game_sub = EDITIONS[edition]
    m.EXE_NAME = exe_name
    game_dir = os.path.join(PKG, game_sub)
    stamp_file = os.path.join(game_dir, ".optim_stamp.txt")
    out_exe = os.path.join(game_dir, out_name)
    src_exe = os.path.join(steam_dir, exe_name)
    if not os.path.exists(src_exe):
        print("  %s not found in %s" % (exe_name, steam_dir))
        return False
    src_pck = m.source_pck(steam_dir)
    sha = m.file_sha(src_exe) + (m.file_sha(src_pck)[:16] if src_pck else "")
    stamp = "%s %s" % (sha, files_version())
    m.BUILD_ID = hashlib.sha256(stamp.encode()).hexdigest()[:16]
    if os.path.exists(out_exe) and os.path.exists(stamp_file) and open(stamp_file).read().strip() == stamp:
        print("  already up to date.")
        return True
    os.makedirs(game_dir, exist_ok=True)
    if os.path.exists(out_exe):
        try:
            open(out_exe, "r+b").close()
        except OSError:
            m.die("the optimised game is open: close it and run this again.")
    print("  building (1-3 min, longer the first time)...", flush=True)

    key = m.find_key(src_exe, src_pck)
    shutil.rmtree(m.WORK, ignore_errors=True)
    os.makedirs(m.WORK)
    fresh = os.path.join(m.WORK, "extracted")
    log = m.gdre(["--recover=" + (src_pck or src_exe), "--key=" + key, "--scripts-only",
                  "--output=" + fresh], os.path.join(m.WORK, "recover.log"))
    files = sorted({p["file"] for p in PERF_PATCHES})
    missing = [f for f in files if not os.path.exists(os.path.join(fresh, f))]
    if "Recovery finished" not in log or missing:
        m.die("decompiling failed (see _work\\recover.log)")

    m.patch_tree(fresh, PERF_PATCHES, PERF_FILES, MOD_FILES)
    targets = files + PERF_FILES
    log = m.gdre(["--bytecode=4.5.0", "--output=" + os.path.join(m.WORK, "gdc")]
                 + ["--compile=" + os.path.normpath(os.path.join(fresh, f)) for f in targets],
                 os.path.join(m.WORK, "compile.log"))
    if log.count("Compiled ") < len(targets) or "ERROR" in log:
        m.die("script error after patching (see _work\\compile.log)")

    tmp_exe = os.path.join(m.WORK, out_name)
    tmp_pck = os.path.splitext(tmp_exe)[0] + ".pck"
    if src_pck:
        args = ["--pck-patch=" + src_pck, "--key=" + key, "--output=" + tmp_pck]
    else:
        base = os.path.join(m.WORK, "base.exe")
        shutil.copyfile(src_exe, base)
        args = ["--pck-patch=" + src_exe, "--key=" + key, "--embed=" + base, "--output=" + tmp_exe]
    for f in targets:
        args.append("--patch-file=%s=res://%s" % (os.path.normpath(os.path.join(fresh, f)), f))
    for f in files:
        args.append("--exclude=res://%s.remap" % f)
    log = m.gdre(args, os.path.join(m.WORK, "patch.log"))
    if src_pck and os.path.exists(tmp_pck):
        shutil.copyfile(src_exe, tmp_exe)
    if "Patched PCK file" not in log or not os.path.exists(tmp_exe):
        m.die("build failed (see _work\\patch.log)")

    out_pck = os.path.splitext(out_exe)[0] + ".pck"
    if src_pck:
        shutil.move(tmp_pck, out_pck)
    elif os.path.exists(out_pck):
        os.remove(out_pck)
    shutil.move(tmp_exe, out_exe)
    for f in os.listdir(steam_dir):
        p = os.path.join(steam_dir, f)
        if os.path.isfile(p) and f.lower().endswith(".dll"):
            shutil.copy2(p, os.path.join(game_dir, f))
    with open(os.path.join(game_dir, "steam_appid.txt"), "w") as fh:
        fh.write(app_id)
    m.GAME_DIR = game_dir
    m.write_override()
    with open(stamp_file, "w") as fh:
        fh.write(stamp)
    shutil.rmtree(m.WORK, ignore_errors=True)
    print("  ready: " + out_exe)
    return True


def main():
    print("just volleyball - optimisation\n")
    if not os.path.exists(m.GDRE):
        m.die("tools/gdre is missing: keep the whole folder together.")
    done = 0
    for ed in ("full", "demo"):
        folder = EDITIONS[ed][0]
        d = find_game(folder)
        if d is None:
            continue
        print("%s : %s" % ("full game" if ed == "full" else "demo", d))
        if build(ed, d):
            done += 1
    if done == 0:
        print("No Steam install of just volleyball found.")
    else:
        print("\nPlay with LAUNCH_GAME.bat (Steam must be running).")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except Exception:
        traceback.print_exc()
    if FROZEN:
        input("\nPress Enter to close...")
