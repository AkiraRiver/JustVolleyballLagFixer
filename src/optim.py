"""Just Volleyball Lag Fixer: performance only, no gameplay changes.

Builds a faster copy of YOUR installed game next to this program
(finds it through the Steam registry key and libraryfolders.vdf):
  game_full\volleyball_optim.exe       (full game, if installed)
  game_demo\volleyballdemo_optim.exe   (demo, if installed)
The Steam install is never modified. Run it again after each game update.
"""

import datetime
import hashlib
import os
import platform
import re
import shutil
import sys
import traceback

FROZEN = getattr(sys, "frozen", False)
PKG = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))
TOOLS = os.path.join(PKG, "tools")
sys.path.insert(0, TOOLS)

import jvpatch as m  # noqa: E402  (key, patching, gdre)
from perf_patches import PERF_PATCHES, PERF_FILES  # noqa: E402

VERSION = "optim-2"
LOG_PATH = os.path.join(PKG, "JV_Optim_log.txt")
_log = None


class _Tee:
    """Everything printed also goes to JV_Optim_log.txt."""

    def __init__(self, out):
        self.out = out

    def write(self, text):
        if self.out is not None:
            self.out.write(text)
        log_only(text, raw=True)

    def flush(self):
        if self.out is not None:
            self.out.flush()


def log_only(text, raw=False):
    if _log is not None:
        _log.write(text if raw else text + "\n")
        _log.flush()


def open_log():
    global _log
    try:
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 2_000_000:
            os.remove(LOG_PATH)
        _log = open(LOG_PATH, "a", encoding="utf-8")
    except OSError:
        _log = None
    log_only("\n" + "=" * 70)
    log_only("JV_Optim %s  %s" % (VERSION, datetime.datetime.now().isoformat(timespec="seconds")))
    log_only("windows: %s | python %s | frozen %s" % (platform.platform(), platform.python_version(), FROZEN))
    log_only("folder: " + PKG)
    sys.stdout = _Tee(sys.stdout)
    sys.stderr = _Tee(sys.stderr)
    m.step = lambda msg: log_only("  . " + msg)  # every patch step, file only


def _describe(path):
    if not path or not os.path.exists(path):
        return "%s (missing)" % path
    st = os.stat(path)
    return "%s  %d bytes  %s" % (path, st.st_size,
                                datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"))


def _block(text, start):
    """The {...} block that follows text[start:], braces balanced."""
    i = text.find("{", start)
    if i < 0:
        return ""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    return text[i:]


def steam_launch_options(app_id):
    """Launch options set in Steam (Properties > Launch options), per Steam user."""
    found = []
    for lib in steam_libraries():
        ud = os.path.join(lib, "userdata")
        if not os.path.isdir(ud):
            continue
        for user in os.listdir(ud):
            cfg = os.path.join(ud, user, "config", "localconfig.vdf")
            if not os.path.exists(cfg):
                continue
            text = open(cfg, encoding="utf-8", errors="replace").read()
            for mt in re.finditer(r'"%s"\s*\{' % app_id, text):
                lo = re.search(r'"LaunchOptions"\s*"((?:[^"\\]|\\.)*)"', _block(text, mt.start()))
                if lo and lo.group(1).strip():
                    found.append(lo.group(1).replace('\\"', '"').strip())
    return found


def game_args(options):
    """Engine arguments to pass on to our copy: what follows %command% (or the
    whole line without it), flags starting with '-' and the value after one."""
    args = []
    for line in options:
        tail = line.split("%command%", 1)[1] if "%command%" in line else line
        prev_flag = False
        for t in tail.split():
            if t.startswith("-"):
                args.append(t)
                prev_flag = True
            elif prev_flag:
                args.append(t)  # --rendering-driver opengl3
                prev_flag = False
    return args


def compat_layers():
    """Windows compatibility-mode settings recorded for any volleyball exe."""
    out = []
    try:
        import winreg
        for hive, name in ((winreg.HKEY_CURRENT_USER, "HKCU"), (winreg.HKEY_LOCAL_MACHINE, "HKLM")):
            try:
                with winreg.OpenKey(hive, r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers") as k:
                    i = 0
                    while True:
                        try:
                            exe, val, _ = winreg.EnumValue(k, i)
                        except OSError:
                            break
                        if "volleyball" in exe.lower():
                            out.append("%s %s = %s" % (name, exe, val))
                        i += 1
            except OSError:
                pass
    except ImportError:
        pass
    return out


def dump_work_logs():
    for name in ("recover.log", "compile.log", "patch.log"):
        p = os.path.join(m.WORK, name)
        if os.path.exists(p):
            text = open(p, encoding="utf-8", errors="replace").read().replace("\r", "\n")
            lines = [l for l in text.split("\n") if l.strip() and "%]" not in l]
            log_only("--- last lines of _work/%s ---" % name)
            log_only("\n".join(lines[-40:]))
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
    log_only("source exe: " + _describe(src_exe))
    log_only("source pck: " + (_describe(src_pck) if src_pck else "(embedded in the exe)"))

    # launch options the player set in Steam: our copy is not started by Steam
    opts = steam_launch_options(app_id)
    play_args = game_args(opts)
    log_only("steam launch options: %s -> passed to our copy: %s" % (opts or "(none)", play_args or "(none)"))
    for c in compat_layers():
        log_only("WARNING compatibility mode: " + c)
    sha = m.file_sha(src_exe) + (m.file_sha(src_pck)[:16] if src_pck else "")
    stamp = "%s %s" % (sha, files_version())
    m.BUILD_ID = hashlib.sha256(stamp.encode()).hexdigest()[:16]
    # every run starts over from the real Steam game: the old copy is deleted
    if os.path.exists(out_exe):
        try:
            open(out_exe, "r+b").close()
        except OSError:
            m.die("the optimised game is open: close it and run this again.")
    keep_plain = os.path.exists(os.path.join(game_dir, "no_render_thread.txt"))
    if os.path.isdir(game_dir):
        log_only("deleting the previous copy: " + game_dir)
        shutil.rmtree(game_dir, ignore_errors=True)
        if os.path.isdir(game_dir):
            m.die("could not delete %s (a file in it is open?)" % game_dir)
    os.makedirs(game_dir)
    if keep_plain:
        open(os.path.join(game_dir, "no_render_thread.txt"), "w").close()  # the player's choice stays
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
        gdre_args = ["--pck-patch=" + src_pck, "--key=" + key, "--output=" + tmp_pck]
    else:
        base = os.path.join(m.WORK, "base.exe")
        shutil.copyfile(src_exe, base)
        gdre_args = ["--pck-patch=" + src_exe, "--key=" + key, "--embed=" + base, "--output=" + tmp_exe]
    for f in targets:
        gdre_args.append("--patch-file=%s=res://%s" % (os.path.normpath(os.path.join(fresh, f)), f))
    for f in files:
        gdre_args.append("--exclude=res://%s.remap" % f)
    log = m.gdre(gdre_args, os.path.join(m.WORK, "patch.log"))
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
    write_launch_args(game_dir, play_args)
    with open(stamp_file, "w") as fh:
        fh.write(stamp)
    shutil.rmtree(m.WORK, ignore_errors=True)
    print("  ready: " + out_exe)
    return True


def write_launch_args(game_dir, args):
    with open(os.path.join(game_dir, "launch_args.txt"), "w") as fh:
        fh.write(" ".join(args))
    # the separate render thread is only known good on d3d12/vulkan
    gl = "opengl3" in args
    m.write_override(threaded=not gl)
    if gl:
        print("  OpenGL is set in Steam: multithreaded rendering left off.")
    log_only("override.cfg:\n" + open(os.path.join(game_dir, "override.cfg")).read())


def main():
    open_log()
    print("just volleyball - optimisation\n")
    log_only("steam libraries: %s" % steam_libraries())
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
        dump_work_logs()
        print("\nSomething went wrong. Send JV_Optim_log.txt (or run MAKE_REPORT.bat).")
    except Exception:
        traceback.print_exc()
        dump_work_logs()
    if FROZEN:
        input("\nPress Enter to close...")
