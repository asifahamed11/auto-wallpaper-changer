from wallpaper_changer.models import Wallpaper, stable_wallpaper_id


def test_wallpaper_from_index_preserves_metadata():
    wallpaper = Wallpaper.from_index(
        {
            "file_name": "misty-mountain",
            "file_cache_name": "misty-mountain.webp",
            "file_main_name": "misty-mountain.png",
            "width": 3840,
            "height": 2160,
            "resolution": "4K",
            "orientation": "Desktop",
            "category": "#nature",
            "data": {"title": "Misty Mountain", "primary_colors": ["Blue", "white"]},
        },
        "https://raw.githubusercontent.com/not-ayan/storage/main/",
    )
    assert wallpaper.id == "misty-mountain"
    assert wallpaper.url.endswith("/main/misty-mountain.png")
    assert wallpaper.thumbnail_url.endswith("/cache/misty-mountain.webp")
    assert wallpaper.colors == ("blue", "white")
    assert wallpaper.orientation == "desktop"


def test_stable_id_is_repeatable():
    assert stable_wallpaper_id("same") == stable_wallpaper_id("same")
    assert stable_wallpaper_id("same") != stable_wallpaper_id("different")
