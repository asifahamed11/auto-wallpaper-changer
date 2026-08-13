# Contributing

1. Install Python 3.11 or newer.
2. Create a virtual environment.
3. Run `python -m pip install -e ".[dev]"`.
4. Run `python -m ruff check src tests` and `python -m pytest -m "not live"` before opening a pull request.

Keep network, storage, Windows integration, and UI changes separated. New API behavior must include fixtures or mocked tests for malformed JSON, HTML responses, timeouts, and empty results.

Do not add wallpaper images or copy upstream application code unless redistribution permission is clear.

