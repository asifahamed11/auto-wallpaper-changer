# Auto Wallpaper Changer

A lightweight Windows app for discovering, applying, and automatically rotating wallpapers from Wallwidgy.

[![CI](https://github.com/asifahamed11/auto-wallpaper-changer/actions/workflows/ci.yml/badge.svg)](https://github.com/asifahamed11/auto-wallpaper-changer/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/asifahamed11/auto-wallpaper-changer?display_name=tag)](https://github.com/asifahamed11/auto-wallpaper-changer/releases)
[![License](https://img.shields.io/github/license/asifahamed11/auto-wallpaper-changer)](LICENSE)

## Features

- Change wallpapers instantly or on a schedule
- Browse by search, category, color, and orientation
- Use one wallpaper across displays or a different one per monitor
- Undo, favorite, block, pause, and resume from the system tray
- Continue with cached wallpapers when the network is unavailable
- Choose light, dark, or system theme with wallpaper-derived accents
- Use the interface in English or বাংলা
- Keep local history, diagnostics, and cache within sensible limits

## Download

Download the latest installer or portable build from [GitHub Releases](https://github.com/asifahamed11/auto-wallpaper-changer/releases).

Windows 10/11 is supported. Normal use does not require administrator permission. Automatic rotation and **Start with Windows** remain disabled until you enable them.

## Run from source

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python tools\build_assets.py
python -m wallpaper_changer
```

Useful commands:

```powershell
python -m wallpaper_changer --change-now
python -m wallpaper_changer --diagnostics
python -m wallpaper_changer --version
```

## Development

```powershell
python -m ruff check src tests tools
python -m pytest -m "not live"
.\tools\Build-Release.ps1
```

Application data is stored in `%LOCALAPPDATA%\AutoWallpaperChanger`. Resetting settings does not delete downloaded wallpapers, favorites, or history.

## Project notes

Wallpapers are provided by the [Wallwidgy API](https://wallwidgy.app/api) and its [storage index](https://github.com/not-ayan/storage). This repository is an independent Windows client.

See the [changelog](CHANGELOG.md), [privacy policy](PRIVACY.md), [security policy](SECURITY.md), and [architecture](docs/ARCHITECTURE.md) for more information.

Licensed under the [MIT License](LICENSE). Created by [Asif Ahamed](https://github.com/asifahamed11).
