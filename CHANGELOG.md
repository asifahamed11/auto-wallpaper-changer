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
- Replaced stylesheet-only rounded corners with antialiased painter paths across panels, buttons,
  preview clipping, gallery tiles, combo boxes, and spin controls.
- Added lightweight React Bits-inspired fade/slide page entrances, cursor spotlights, animated nav
  selection, hover/press feedback, and status reveals without a continuous animation loop.
- Fixed pressed primary-button contrast for dark wallpaper-derived accents, Discover filter text
  truncation, and spotlight visibility; added a confirmed reset-to-defaults action that preserves user data.
- Made wallpaper-derived accent colors update immediately after online, offline, and undo changes;
  replaced constrained action rows with responsive two-column layouts so English and Bangla button
  labels remain fully visible at the minimum supported window size.
- Added compact-height scrolling to Automation and Settings while keeping Save/Reset actions fixed,
  preventing dense forms, cards, and controls from overlapping when the window is resized smaller.
- Made the Home wallpaper preview vertically flexible so showing the Change Now progress bar cannot
  push the preview over its title, metadata, or action buttons at default or compact window sizes.
