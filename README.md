# Auto Wallpaper Changer v2

A tray-first Windows wallpaper companion powered by Wallwidgy. It can change wallpapers on demand or on a schedule, filter by category and color, work across multiple monitors, and recover gracefully when the network is unavailable.

> The old `wallwidgy.me/api/random-wallpapers` integration is retired. v2 follows the current [Wallwidgy API documentation](https://wallwidgy.app/api) and uses the metadata-rich [Wallwidgy storage index](https://raw.githubusercontent.com/not-ayan/storage/main/index.json) as a gallery and fallback source.

## Highlights

- Current Wallwidgy REST API support with schema and content-type validation
- Raw-index fallback and offline wallpaper cache
- System tray actions: Change now, Undo, Favorite, Block, Pause, Settings
- Scheduled rotation through Windows Task Scheduler; the UI does not need to stay open
- Random, category, color, and favorites rotation modes
- Searchable preview gallery with category, color, and orientation filters
- Lightweight native navigation, smooth page transitions, responsive previews, and debounced search
- Lazy settings-window creation keeps tray-only startup fast and avoids loading the full UI until needed
- Per-monitor, all-monitor, or different-wallpaper-per-monitor modes
- Fill, fit, stretch, center, tile, and span positioning
- English and বাংলা UI, light/dark/system themes, and wallpaper-derived accent color
- Bounded SQLite history, rotating logs, diagnostics export, and update checks
- HTTPS-only downloads with trusted-host, MIME, size, and image-decoding validation

## Install

### Recommended

Download `AutoWallpaperChanger.exe` or the installer from [GitHub Releases](https://github.com/asifahamed11/auto-wallpaper-changer/releases). Verify it with the accompanying `.sha256` file.

The first launch opens Settings. Automatic rotation and **Start with Windows** are opt-in; the app never enables them silently.

### Run from source

Requirements: Windows 10/11 and Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python tools\build_assets.py
python -m wallpaper_changer
```

Headless commands:

```powershell
python -m wallpaper_changer --change-now
python -m wallpaper_changer --diagnostics
python -m wallpaper_changer --version
```

## Using the app

The tray menu provides fast actions without opening a full window. The settings window contains:

- **Home:** current preview, Change now, Undo, Favorite, Block, and the next-change timer.
- **Discover:** search, filters, preview gallery, and direct apply/favorite actions.
- **Automation:** interval, rotation mode, display target, image position, pause, startup behavior, and its own Save action.
- **Settings:** theme, language, notifications, cache limits, connection test, updates, and diagnostics.

Downloaded data is stored under:

```text
%LOCALAPPDATA%\AutoWallpaperChanger\
  settings.json
  wallpapers.sqlite3
  cache\
  logs\
  diagnostics\
```

No administrator permission is required for normal operation.

## Development

```powershell
python -m ruff check src tests
python -m pytest -m "not live"
python -m pytest tests\test_live_api.py -m live
```

The UI action suite runs offscreen and verifies the window and tray controls, loading/failure recovery,
filter debounce, Automation persistence, connection checks, updates, diagnostics, and folder actions.

Build a portable executable and, when Inno Setup is installed, an installer:

```powershell
.\tools\Build-Release.ps1
```

The release pipeline adds product/version metadata and SHA-256 checksums. Authenticode signing is enabled in GitHub Actions when the repository's certificate secrets are configured.

See [architecture](docs/ARCHITECTURE.md), [privacy](PRIVACY.md), [security](SECURITY.md), [contributing](CONTRIBUTING.md), and the [changelog](CHANGELOG.md).
Third-party runtime licenses are listed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## API and attribution

Wallpaper discovery and images are supplied by Wallwidgy and its storage repository. This project is an independent Windows client. Confirm upstream terms before redistributing third-party wallpaper assets or copying upstream source code.

## License

This project is available under the [MIT License](LICENSE).

## Author

Asif Ahamed — [GitHub](https://github.com/asifahamed11) — [email](mailto:asifahamedstudent@gmail.com)
