@echo off
rem lighter-stage options: true = on, false = off (used from the next stage load)
set CFG=%APPDATA%\Godot\app_userdata\volleyball\jv_mod_lite.cfg
if not exist "%CFG%" (
  if not exist "%APPDATA%\Godot\app_userdata\volleyball" mkdir "%APPDATA%\Godot\app_userdata\volleyball"
  (
    echo [lite]
    echo.
    echo crowd=true
    echo trails=true
    echo anim=true
    echo backdrop=true
  ) > "%CFG%"
)
start "" notepad "%CFG%"
