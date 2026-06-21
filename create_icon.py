"""Создание app.ico для ChatList. Требуется: pip install Pillow"""

from __future__ import annotations

import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError as exc:
    raise SystemExit(
        "Не установлен Pillow. Выполните: pip install Pillow",
    ) from exc

ICON_PATH = Path(__file__).parent / "app.ico"
ICON_SIZES = [16, 32, 48, 64, 128, 256]

# Палитра «всевидящее око»
BG = (14, 18, 36)
GOLD = (201, 162, 39)
GOLD_DARK = (139, 108, 22)
SCLERA = (245, 242, 230)
IRIS = (46, 92, 138)
PUPIL = (8, 8, 12)
HIGHLIGHT = (255, 255, 255)
RAY = (201, 162, 39, 90)


def _scale(size: int, value: float) -> int:
    return max(1, round(size * value))


def _triangle_points(size: int, inset: float) -> list[tuple[int, int]]:
    pad = size * inset
    cx = size / 2
    return [
        (cx, pad),
        (pad, size - pad),
        (size - pad, size - pad),
    ]


def draw_icon(size: int) -> Image.Image:
    """Всевидящее око: треугольник, лучи и глаз на тёмном фоне."""
    img = Image.new("RGBA", (size, size), BG + (255,))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    inset = 0.08 if size >= 32 else 0.06
    triangle = _triangle_points(size, inset)

    # Лучи света (только на достаточно крупных размерах)
    if size >= 48:
        rays = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ray_draw = ImageDraw.Draw(rays)
        ray_count = 12
        inner = _scale(size, 0.34)
        outer = _scale(size, 0.46)
        for index in range(ray_count):
            angle = (index / ray_count) * 6.28318 - 1.5708
            x1 = cx + inner * math.cos(angle)
            y1 = cy + inner * math.sin(angle) * 0.55
            x2 = cx + outer * math.cos(angle)
            y2 = cy + outer * math.sin(angle) * 0.55
            ray_draw.line(
                (x1, y1, x2, y2),
                fill=RAY,
                width=max(1, _scale(size, 0.018)),
            )
        img = Image.alpha_composite(img, rays)
        draw = ImageDraw.Draw(img)

    # Треугольник: заливка и контур
    if size >= 24:
        draw.polygon(triangle, fill=GOLD_DARK)
    outline_width = max(1, _scale(size, 0.035))
    draw.polygon(triangle, outline=GOLD, width=outline_width)

    # Глаз — горизонтальный овал
    eye_w = _scale(size, 0.42)
    eye_h = _scale(size, 0.22)
    eye_box = (cx - eye_w // 2, cy - eye_h // 2, cx + eye_w // 2, cy + eye_h // 2)
    draw.ellipse(eye_box, fill=SCLERA, outline=GOLD, width=max(1, _scale(size, 0.02)))

    # Радужка
    iris_r = _scale(size, 0.09)
    iris_box = (cx - iris_r, cy - iris_r, cx + iris_r, cy + iris_r)
    draw.ellipse(iris_box, fill=IRIS)

    # Зрачок
    pupil_r = max(1, _scale(size, 0.045))
    pupil_box = (cx - pupil_r, cy - pupil_r, cx + pupil_r, cy + pupil_r)
    draw.ellipse(pupil_box, fill=PUPIL)

    # Блик
    if size >= 32:
        hl_r = max(1, _scale(size, 0.022))
        hl_x = cx - _scale(size, 0.03)
        hl_y = cy - _scale(size, 0.03)
        draw.ellipse(
            (hl_x - hl_r, hl_y - hl_r, hl_x + hl_r, hl_y + hl_r),
            fill=HIGHLIGHT,
        )

    return img.convert("RGB")


def main() -> None:
    icons = [draw_icon(size) for size in ICON_SIZES]
    icons[0].save(
        ICON_PATH,
        format="ICO",
        sizes=[(size, size) for size in ICON_SIZES],
        append_images=icons[1:],
    )
    print(f"Иконка создана: {ICON_PATH}")
    print("Дизайн: всевидящее око в золотом треугольнике")


if __name__ == "__main__":
    main()
