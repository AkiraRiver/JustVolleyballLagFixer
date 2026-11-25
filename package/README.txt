just volleyball - optimisation (unofficial mod)
===============================================

Performance only: no gameplay or matchmaking changes.

1. Double-click JV_Optim.exe
   It finds the game through Steam by itself (full game and/or demo, any
   Steam library drive) and builds an optimised copy in this folder
   (game_full / game_demo). Your Steam install is never modified.
2. Play with LAUNCH_GAME.bat (Steam must be running).
3. After each game update, run JV_Optim.exe again. Each run deletes the old
   copy and rebuilds it from the real Steam game.
   Launch options set in Steam (e.g. --rendering-driver vulkan) are copied
   to the optimised copy.

LIGHT_STAGES.bat - lighter-stage options (true = on, false = off):
  crowd     no background people
  trails    no footprints in the sand
  anim      no moving scenery (sea, clouds, cubes)
  backdrop  no extra scenery (town, hills, sun patches, nationals screens)
Used from the next stage load.

Back to the normal game: launch it from Steam, or delete this folder.
Crashes or glitches: double-click SAFE_MODE.bat (turns off multithreaded
rendering and rebuilds), then play again with LAUNCH_GAME.bat.
Still broken? Run MAKE_REPORT.bat and send the JV_report.zip it puts on
your Desktop (it contains your game logs).
Do not run the Steam game and this copy at the same time (online breaks).
Unofficial, use at your own risk.

---------------------------------------------
FR : lance JV_Optim.exe, puis joue avec LAUNCH_GAME.bat. Relance JV_Optim.exe
apres chaque mise a jour du jeu. LIGHT_STAGES.bat = options des terrains alleges.
Uniquement des optimisations. Mod non officiel, a tes risques.
