# Architecture

The application keeps the graphical interface independent from wallpaper-changing logic:

```text
PySide6 tray/settings ─┐
Task Scheduler CLI ────┼─> WallpaperService
                       │      ├─ REST provider
                       │      ├─ cached index provider
                       │      ├─ secure image downloader
                       │      ├─ Windows IDesktopWallpaper integration
                       │      └─ SQLite history/favorites
                       └─> SettingsStore / diagnostics / updates
```

The REST provider is preferred for lightweight random changes. The cached `index.json` provider supplies metadata for gallery search, aspect-ratio selection, and fallback. If neither network source is available, the service applies a validated local cached image.

Scheduled tasks execute `AutoWallpaperChanger.exe --change-now --scheduled`. The GUI is not required to remain running. Launch-at-login is a separate opt-in setting stored in the current user's Windows Run key.

No module outside `platform/windows_wallpaper.py` calls Windows wallpaper APIs directly. This allows core behavior to be tested with fake platform services.

