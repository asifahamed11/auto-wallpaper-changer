from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "src" / "wallpaper_changer" / "assets"


def lerp(start: int, end: int, amount: float) -> int:
    return round(start + (end - start) * amount)


def build_icon(size: int = 256) -> Image.Image:
    scale = size / 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = round(58 * scale)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill="#0A0A0A")

    sun_box = tuple(round(value * scale) for value in (155, 43, 211, 99))
    for offset in range(max(1, round(28 * scale)), 0, -1):
        amount = 1 - offset / max(1, round(28 * scale))
        color = (
            lerp(247, 139, amount),
            lerp(240, 233, amount),
            lerp(109, 200, amount),
            255,
        )
        center_x = (sun_box[0] + sun_box[2]) // 2
        center_y = (sun_box[1] + sun_box[3]) // 2
        draw.ellipse((center_x - offset, center_y - offset, center_x + offset, center_y + offset), fill=color)

    def points(values: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return [(round(x * scale), round(y * scale)) for x, y in values]

    draw.polygon(
        points([(25, 194), (92, 92), (134, 150), (159, 119), (231, 194), (231, 224), (25, 224)]),
        fill="#17332F",
    )
    draw.polygon(
        points([(25, 194), (92, 92), (134, 150), (116, 173), (94, 144), (42, 224), (25, 224)]), fill="#3D776D"
    )
    draw.polygon(
        points([(25, 203), (64, 190), (107, 186), (160, 201), (193, 205), (231, 198), (231, 224), (25, 224)]),
        fill="#F7F06D",
    )
    return image


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    icon = build_icon()
    icon.save(ASSET_DIR / "icon.png", optimize=True)
    icon.save(
        ASSET_DIR / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Generated assets in {ASSET_DIR}")


if __name__ == "__main__":
    main()
