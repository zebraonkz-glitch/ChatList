"""Создание app.ico для ChatList. Требуется: pip install Pillow"""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError as exc:
    raise SystemExit(
        "Не установлен Pillow. Выполните: pip install Pillow",
    ) from exc

ICON_PATH = Path(__file__).parent / "app.ico"
ICON_SIZES = [16, 32, 48, 64, 128, 256]


def draw_icon(size: int) -> Image.Image:
    """Синий круг на красном фоне."""
    img = Image.new("RGB", (size, size), (220, 20, 60))
    draw = ImageDraw.Draw(img)

    padding = max(int(size * 0.1), 1)
    radius = (size - padding * 2) // 2
    center = size // 2
    circle_coords = (
        center - radius,
        center - radius,
        center + radius,
        center + radius,
    )
    draw.ellipse(circle_coords, fill=(30, 144, 255))
    return img


def main() -> None:
    icons = [draw_icon(size) for size in ICON_SIZES]
    icons[0].save(
        ICON_PATH,
        format="ICO",
        sizes=[(size, size) for size in ICON_SIZES],
        append_images=icons[1:],
    )
    print(f"Иконка создана: {ICON_PATH}")
    print("Дизайн: синий круг на красном фоне")


if __name__ == "__main__":
    main()
