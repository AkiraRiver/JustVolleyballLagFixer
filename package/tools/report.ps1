param([string]$Here = ".")
# Bug report for Just Volleyball Lag Fixer: logs, settings and PC info in one zip.
$ErrorActionPreference = "SilentlyContinue"
$out = Join-Path $env:TEMP "JV_report"
Remove-Item $out -Recurse -Force
New-Item -ItemType Directory -Force $out | Out-Null

# this tool's own logs and the files it wrote
foreach ($f in "JV_Optim_log.txt", "launch_log.txt", "compat_mode.txt") {
    Copy-Item (Join-Path $Here $f) $out
}
foreach ($g in "game_full", "game_demo") {
    $d = Join-Path $Here $g
    if (Test-Path $d) {
        New-Item -ItemType Directory -Force (Join-Path $out $g) | Out-Null
        Get-ChildItem $d -File | Where-Object { $_.Extension -in ".cfg", ".txt" } |
            Copy-Item -Destination (Join-Path $out $g)
        Get-ChildItem $d -File | Select-Object Name, Length, LastWriteTime |
            Out-File (Join-Path $out "$g\files.txt")
    }
}

# the game's own logs (last 5) and settings
$ud = Join-Path $env:APPDATA "Godot\app_userdata\volleyball"
New-Item -ItemType Directory -Force (Join-Path $out "game_logs") | Out-Null
Get-ChildItem (Join-Path $ud "logs") -Filter *.log | Sort-Object LastWriteTime -Descending |
    Select-Object -First 5 | Copy-Item -Destination (Join-Path $out "game_logs")
Copy-Item (Join-Path $ud "data\settings.json") $out
Copy-Item (Join-Path $ud "jv_mod_lite.cfg") $out

# PC info
$info = @()
$info += "date: " + (Get-Date -Format s)
$os = Get-CimInstance Win32_OperatingSystem
$info += "windows: " + $os.Caption + " " + $os.Version + " (" + $os.OSArchitecture + ")"
$info += "cpu: " + (Get-CimInstance Win32_Processor | Select-Object -First 1).Name
$info += "ram: " + [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1) + " GB"
foreach ($v in Get-CimInstance Win32_VideoController) {
    $info += "gpu: " + $v.Name + " | driver " + $v.DriverVersion + " (" + $v.DriverDate + ") | " + $v.CurrentHorizontalResolution + "x" + $v.CurrentVerticalResolution
}
$info += "boot crash marker (.boot_pending): " + (Test-Path (Join-Path $ud ".boot_pending"))
$info += ""
$info += "compatibility mode settings for volleyball exes:"
foreach ($hive in "HKCU:", "HKLM:") {
    $k = Get-Item "$hive\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
    if ($k) {
        foreach ($n in $k.GetValueNames()) {
            if ($n -like "*volleyball*") { $info += "  $hive $n = " + $k.GetValue($n) }
        }
    }
}
$info += ""
$info += "running volleyball processes:"
Get-Process volleyball* | ForEach-Object { $info += "  " + $_.Id + " " + $_.Path }
$info | Out-File (Join-Path $out "pc_info.txt") -Encoding utf8

$zip = Join-Path ([Environment]::GetFolderPath("Desktop")) "JV_report.zip"
Remove-Item $zip -Force
Compress-Archive -Path (Join-Path $out "*") -DestinationPath $zip
Remove-Item $out -Recurse -Force
if (Test-Path $zip) {
    Write-Host "Report ready on your Desktop: JV_report.zip"
    Write-Host "(it has your game logs, which include the names of players you met online)"
} else {
    Write-Host "Could not create the report."
}
