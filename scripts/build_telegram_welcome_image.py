from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "web" / "public" / "telegram-welcome.jpg"
LOGO = ROOT / "assets" / "brand" / "nodo-bot-profile-1024.png"

FONT_REGULAR = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")
FONT_SEMIBOLD = Path("C:/Windows/Fonts/segoeuisb.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    if not path.exists() and bold:
        path = FONT_SEMIBOLD if FONT_SEMIBOLD.exists() else FONT_REGULAR
    return ImageFont.truetype(str(path), size=size)


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def add_text_center(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
) -> None:
    draw.text(xy, text, font=text_font, fill=fill, anchor="mm")


def add_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    line_spacing: int = 10,
    align: str = "center",
) -> int:
    left, top, right, _bottom = box
    max_width = right - left
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=text_font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    y = top
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=text_font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        x = left + (max_width - width) // 2 if align == "center" else left
        draw.text((x, y), line, font=text_font, fill=fill)
        y += height + line_spacing
    return y


def gradient_bg(width: int, height: int) -> Image.Image:
    img = Image.new("RGB", (width, height), "#020916")
    px = img.load()
    for y in range(height):
        for x in range(width):
            radial = ((x - width * 0.70) ** 2 + (y - height * 0.12) ** 2) ** 0.5 / width
            vertical = y / height
            r = int(3 + 5 * (1 - vertical) + max(0, 22 * (0.8 - radial)))
            g = int(11 + 24 * (1 - vertical) + max(0, 40 * (0.75 - radial)))
            b = int(27 + 34 * (1 - vertical) + max(0, 34 * (0.75 - radial)))
            px[x, y] = (min(r, 18), min(g, 62), min(b, 88))
    return img


def draw_glow(draw: ImageDraw.ImageDraw, center: tuple[int, int], radius: int, color: tuple[int, int, int, int]) -> None:
    x, y = center
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def alpha_composite_blur(base: Image.Image, overlay: Image.Image, blur: int) -> None:
    blurred = overlay.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(blurred)


def make_coin(text: str, color: tuple[int, int, int], pos: tuple[int, int], size: int, angle: int = 0) -> Image.Image:
    coin = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(coin)
    d.ellipse((8, 8, size - 8, size - 8), fill=color + (255,), outline=(130, 255, 190, 190), width=5)
    d.ellipse((18, 18, size - 18, size - 18), outline=(255, 255, 255, 54), width=4)
    add_text_center(d, (size // 2, size // 2 - 2), text, font(size // 3, bold=True), (255, 255, 255))
    if angle:
        coin = coin.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    canvas = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0))
    canvas.alpha_composite(coin, pos)
    return canvas


def main() -> None:
    width, height = 1080, 1350
    base = gradient_bg(width, height).convert("RGBA")

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    draw_glow(gd, (140, 250), 175, (0, 230, 118, 34))
    draw_glow(gd, (1000, 110), 190, (0, 142, 255, 26))
    draw_glow(gd, (985, 760), 210, (0, 230, 118, 22))
    alpha_composite_blur(base, glow, 38)

    base.alpha_composite(make_coin("$", (0, 150, 88), (74, 130), 142, -9))
    base.alpha_composite(make_coin("Bs", (24, 95, 219), (850, 170), 132, 10))

    draw = ImageDraw.Draw(base)

    logo = Image.open(LOGO).convert("RGBA")
    logo = logo.resize((218, 218), Image.Resampling.LANCZOS)
    logo_card = Image.new("RGBA", (250, 250), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (250, 250), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((16, 16, 234, 234), radius=54, fill=(0, 0, 0, 120))
    logo_card.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    logo_card.alpha_composite(logo, (16, 16))
    base.alpha_composite(logo_card, ((width - 250) // 2, 55))

    add_text_center(draw, (width // 2, 360), "NODO", font(104, bold=True), (255, 255, 255))
    add_text_center(draw, (width // 2, 455), "Bienvenido a NODO", font(68, bold=True), (255, 255, 255))

    add_wrapped_text(
        draw,
        "Compara ofertas publicadas, revisa sus condiciones y crea tu orden en pocos pasos.",
        (175, 520, 905, 620),
        font(34),
        (218, 228, 242),
        line_spacing=12,
    )

    # Main card
    card = (115, 640, 965, 1086)
    draw.rounded_rectangle(card, radius=34, fill=(6, 20, 42, 218), outline=(34, 92, 124, 170), width=2)
    add_text_center(draw, (width // 2, 684), "Cómo funciona", font(42, bold=True), (255, 255, 255))

    steps = [
        ("1", "Indica el monto que vas a enviar."),
        ("2", "Elige una oferta disponible."),
        ("3", "Revisa los datos publicados por el negocio."),
        ("4", "Guarda la evidencia de tu orden."),
    ]
    y = 730
    for number, text in steps:
        draw.ellipse((158, y + 5, 225, y + 72), fill=(0, 113, 77), outline=(55, 244, 151, 80), width=2)
        add_text_center(draw, (191, y + 39), number, font(34, bold=True), (255, 255, 255))
        draw.rounded_rectangle((274, y, 892, y + 78), radius=20, fill=(7, 18, 38, 235), outline=(28, 70, 100, 170), width=1)
        draw.text((318, y + 22), text, font=font(30), fill=(245, 248, 255))
        y += 84

    trust = (115, 1115, 965, 1248)
    draw.rounded_rectangle(trust, radius=34, fill=(6, 20, 42, 226), outline=(34, 92, 124, 170), width=2)
    draw.rounded_rectangle((154, 1148, 230, 1216), radius=20, fill=(0, 230, 118, 32), outline=(0, 230, 118, 200), width=4)
    draw.line((176, 1183, 194, 1202, 214, 1168), fill=(255, 255, 255), width=8, joint="curve")
    draw.text((270, 1146), "NODO registra tu orden", font=font(36, bold=True), fill=(255, 255, 255))
    draw.text((270, 1192), "y conserva evidencia.", font=font(36, bold=True), fill=(0, 230, 118))

    feature_y = 1290
    add_text_center(draw, (310, feature_y), "Registro", font(27, bold=True), (224, 235, 246))
    add_text_center(draw, (540, feature_y), "Orden", font(27, bold=True), (224, 235, 246))
    add_text_center(draw, (770, feature_y), "Soporte", font(27, bold=True), (224, 235, 246))
    for x in (420, 660):
        draw.line((x, 1266, x, 1312), fill=(52, 86, 112), width=2)

    rgb = base.convert("RGB")
    rgb.save(OUT, quality=94, optimize=True, progressive=True)
    print(f"created={OUT} bytes={OUT.stat().st_size}")


if __name__ == "__main__":
    main()
