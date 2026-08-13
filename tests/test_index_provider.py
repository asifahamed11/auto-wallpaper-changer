from __future__ import annotations

import json
from datetime import UTC, datetime

from wallpaper_changer.api.wallwidgy_index import WallwidgyIndexProvider


def test_cached_index_supports_search_filters(tmp_path):
    index = [
        {
            "file_name": "blue-forest",
            "file_cache_name": "blue-forest.webp",
            "file_main_name": "blue-forest.png",
            "width": 3840,
            "height": 2160,
            "orientation": "Desktop",
            "category": "#nature",
            "data": {"title": "Blue Forest", "primary_colors": ["blue"]},
        },
        {
            "file_name": "red-phone",
            "file_cache_name": "red-phone.webp",
            "file_main_name": "red-phone.png",
            "orientation": "Mobile",
            "category": "#abstract",
            "data": {"title": "Red Shape", "primary_colors": ["red"]},
        },
    ]
    cache = tmp_path / "index.json"
    metadata = tmp_path / "index.meta.json"
    cache.write_text(json.dumps(index), encoding="utf-8")
    metadata.write_text(json.dumps({"checked_at": datetime.now(UTC).isoformat()}), encoding="utf-8")
    provider = WallwidgyIndexProvider(
        "https://example.test/index.json", "https://example.test/", cache, metadata
    )
    results = provider.search(query="forest", category="nature", color="blue", orientation="desktop")
    assert [item.id for item in results] == ["blue-forest"]
