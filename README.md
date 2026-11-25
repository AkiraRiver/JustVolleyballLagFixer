# Just Volleyball Lag Fixer (unofficial mod)

Makes **just volleyball** run smoother (more FPS, faster loading).
It does **not** change the gameplay or online play.

## [Download here](../../releases/latest)

Download **`JustVolleyball_Optim.zip`** under *Assets*.

## How to install

1. **Unzip** the file anywhere (right-click → *Extract All*).
2. Open the folder and **double-click `JV_Optim.exe`**.
   - If Windows shows a blue box: click *More info* → *Run anyway*.
   - Wait for **"ready"**, then press Enter. It finds the game by itself.
3. **Double-click `LAUNCH_GAME.bat`** to play (Steam must be open).

**Game updated?** Just double-click `JV_Optim.exe` again. (and ping me on discord akira2549 if needed)

**Back to normal?** Launch the game from Steam as usual. Your Steam game is never changed.

## Options

Double-click `LIGHT_STAGES.bat`, change `true` to `false` for what you want to keep, save, and close.

| Option | When `true` |
|---|---|
| `crowd` | no people in the background |
| `trails` | no footprints in the sand |
| `anim` | no moving sea, clouds or cubes |
| `backdrop` | no far scenery (town, hills, big screens) |

## Problems?

- **Crashes or weird graphics:** delete `override.cfg` in the `game_full` folder.
- Don't run the Steam game and this one **at the same time**.

---

<sub>Unofficial, not made by the game's developer.
Source: `src/` (patches in `src/tools/perf_patches.py`). Build: `pip install pyinstaller cryptography`, then `python build_release.py --gdre <GDRE Tools folder>` ([GDRE Tools](https://github.com/GDRETools/gdsdecomp), MIT).</sub>
