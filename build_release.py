"""Build the release zip: python build_release.py --gdre <folder with gdre_tools.exe>

Needs: pip install pyinstaller cryptography
GDRE Tools (MIT): https://github.com/GDRETools/gdsdecomp/releases (tested with 2.7.4)
"""

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "JustVolleyball_Optim"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gdre", required=True, help="folder holding gdre_tools.exe")
    a = ap.parse_args()
    if not os.path.exists(os.path.join(a.gdre, "gdre_tools.exe")):
        sys.exit("gdre_tools.exe not found in " + a.gdre)

    build = os.path.join(HERE, "build")
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "--onefile", "--console",
                           "--name", "JV_Optim", "--paths", os.path.join(HERE, "src", "tools"),
                           "--hidden-import", "jvpatch", "--hidden-import", "perf_patches",
                           "--distpath", os.path.join(build, "dist"), "--workpath", build,
                           "--specpath", build, os.path.join(HERE, "src", "optim.py")])

    out = os.path.join(HERE, "release", NAME)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(os.path.join(out, "tools"))
    shutil.copy2(os.path.join(build, "dist", "JV_Optim.exe"), out)
    for f in os.listdir(os.path.join(HERE, "package")):
        shutil.copy2(os.path.join(HERE, "package", f), out)
    shutil.copytree(os.path.join(HERE, "src", "tools", "mod_files"), os.path.join(out, "tools", "mod_files"))
    shutil.copytree(a.gdre, os.path.join(out, "tools", "gdre"))
    zip_path = shutil.make_archive(os.path.join(HERE, "release", NAME), "zip",
                                   os.path.join(HERE, "release"), NAME)
    print("release: " + zip_path)


if __name__ == "__main__":
    main()
