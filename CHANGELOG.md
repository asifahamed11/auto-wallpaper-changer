# Changelog

## 2.0.0

- Migrated to the current Wallwidgy REST API contract.
- Added raw-index fallback, offline cache, image validation, bounded history, and rotating logs.
- Added a tray-first PySide6 interface with English and বাংলা language options.
- Added filters, gallery previews, favorites, undo, blocked wallpapers, and dynamic accent colors.
- Added Windows Task Scheduler rotation, launch-at-login, pause/resume, multi-monitor targeting, and fit modes.
- Added diagnostics export, update checks, tests, CI, release metadata, checksums, and optional signing.
- Polished the native Qt UI with a navigation rail, responsive previews, subtle page/window transitions,
  debounced search, contextual action states, a non-blocking busy indicator, and a dedicated Automation save.
- Reduced the GUI dependency to PySide6 Essentials, lazily create the full window for tray-only startup,
  and capped UI worker concurrency to keep the app lightweight.
- Added button-level window and tray tests, including error-state recovery and the Change-now signal regression.
