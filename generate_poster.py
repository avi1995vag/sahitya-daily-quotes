import os
import csv
import random
import requests
import re
import hashlib
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================

GOOGLE_SHEET_ID = "1rmyyD1lS3uAZ4c9WAkmTekDrrcx4X3jdvpJz8DWyhX0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"

FONT_URLS = {
    "Anek Kannada": "https://github.com/google/fonts/raw/main/ofl/anekkannada/AnekKannada%5Bwdth,wght%5D.ttf",
    "Hubballi": "https://github.com/google/fonts/raw/main/ofl/hubballi/Hubballi-Regular.ttf"
}

W, H = 1080, 1080

# Used by the "notes card" template's footer bar (like the reference screenshot).
# Fill these in with your own branding — leave CONTACT_NUMBER empty to hide it.
BRAND_NAME = "VIJAY KARNATAKA"
CONTACT_NUMBER = ""

# ============================================================
# CURATED PREMIUM PALETTES
# Each palette: (bg_dark, bg_light, accent, accent_soft)
# accent = used for quote marks / divider / author name
# accent_soft = used for alternating "kinetic" text lines
# ============================================================

PALETTES = [
    {
        "name": "Midnight Ocean",
        "bg1": (8, 15, 28), "bg2": (22, 45, 68),
        "accent": (94, 197, 255), "accent_soft": (180, 230, 255),
    },
    {
        "name": "Royal Plum",
        "bg1": (24, 10, 26), "bg2": (58, 22, 58),
        "accent": (255, 122, 200), "accent_soft": (232, 180, 255),
    },
    {
        "name": "Emerald Noir",
        "bg1": (7, 20, 16), "bg2": (18, 48, 36),
        "accent": (95, 230, 170), "accent_soft": (200, 245, 220),
    },
    {
        "name": "Sunset Ember",
        "bg1": (26, 12, 8), "bg2": (62, 28, 14),
        "accent": (255, 154, 60), "accent_soft": (255, 205, 140),
    },
    {
        "name": "Charcoal Gold",
        "bg1": (16, 16, 16), "bg2": (38, 36, 32),
        "accent": (255, 197, 92), "accent_soft": (240, 220, 180),
    },
    {
        "name": "Deep Indigo",
        "bg1": (12, 10, 30), "bg2": (34, 26, 70),
        "accent": (170, 150, 255), "accent_soft": (215, 200, 255),
    },
]


def generate_solid_background(palette, W, H):
    """Flat, clean solid-color background — no photo, no gradient, no texture."""
    return Image.new('RGB', (W, H), palette["bg2"])


def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines


def get_text_hash(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]


def clear_old_images():
    print("Cleaning up old image assets...")
    if os.path.exists("images"):
        for root, dirs, files in os.walk("images", topdown=False):
            for file in files:
                if file.endswith(".png"):
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception as e:
                        print(f"Failed to delete {file}: {e}")


def fetch_quotes_from_sheets():
    quotes = []
    try:
        response = requests.get(CSV_URL, timeout=15)
        if response.status_code == 200:
            lines = response.content.decode('utf-8').splitlines()
            reader = csv.reader(lines)
            for row in reader:
                if len(row) >= 4:
                    date_val = row[0].strip()
                    category_val = row[1].strip().lower()
                    text_val = row[2].strip()
                    prompt_val = row[3].strip()
                    if date_val.lower() == "date" or category_val == "category":
                        continue
                    if date_val and category_val and text_val and prompt_val:
                        quotes.append({
                            "date": date_val,
                            "category": category_val,
                            "text": text_val,
                            "prompt": prompt_val
                        })
    except Exception as e:
        print(f"Failed to fetch Google Sheets: {e}")
    return quotes


def parse_author(raw_text):
    author_name = ""
    quote_body = raw_text
    match = re.search(r'[\.\?\!\s]*[-\u2014\u2013\u2212]\s*([^-—–]+)$', raw_text)
    if match:
        author_name = match.group(1).strip()
        quote_body = raw_text[:match.start()].strip()
    return quote_body, author_name


def pick_font_size(text_length):
    if text_length < 35:
        return 118
    elif text_length < 75:
        return 92
    return 72


def apply_logo(img):
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            aspect_ratio = logo.width / float(logo.height)
            logo_h = 55
            logo_w = int(logo_h * aspect_ratio)
            logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
            logo_x = W - logo.width - 50
            logo_y = H - logo.height - 50
            img.paste(logo, (logo_x, logo_y), logo)
        except Exception as e:
            print(f"Failed to apply logo: {e}")


# ============================================================
# LAYOUT TEMPLATES
# Each takes (img, quote_body, author_name, font_path, palette) and returns final RGB image
# ============================================================

def template_centered_card(img, quote_body, author_name, font_path, palette, quote_date=None):
    """Classic frosted glass card, centered, kinetic staggered lines."""
    accent = palette["accent"]
    accent_soft = palette["accent_soft"]

    font_size = pick_font_size(len(quote_body))
    font = ImageFont.truetype(font_path, size=font_size, layout_engine=ImageFont.Layout.RAQM)

    max_text_width = 860
    wrapped_lines = wrap_text(quote_body, font, max_text_width)

    line_spacing = 20
    total_text_height = 0
    line_heights = []
    for line in wrapped_lines:
        bbox = font.getbbox(line)
        line_h = bbox[3] - bbox[1]
        line_heights.append(line_h)
        total_text_height += int(line_h * 1.35)
    total_text_height += line_spacing * (len(wrapped_lines) - 1)

    padding_y = 75
    card_w = 940
    card_h = total_text_height + (padding_y * 2) + 120

    left = (W - card_w) / 2
    top = (H - card_h) / 2
    right = left + card_w
    bottom = top + card_h

    # Soft drop shadow behind the card for depth
    shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([left, top + 18, right, bottom + 18], radius=28, fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    img = Image.alpha_composite(img.convert('RGBA'), shadow)

    # Frosted glass card: blurred background sample + translucent tint + thin border
    card_region = img.crop((int(left), int(top), int(right), int(bottom))).filter(ImageFilter.GaussianBlur(14))
    tint = Image.new('RGBA', card_region.size, (10, 10, 15, 140))
    card_region = Image.alpha_composite(card_region.convert('RGBA'), tint)

    mask = Image.new('L', card_region.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, card_region.width, card_region.height], radius=28, fill=255)
    img.paste(card_region, (int(left), int(top)), mask)

    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([left, top, right, bottom], radius=28, outline=(255, 255, 255, 40), width=2)

    quote_font = ImageFont.truetype(font_path, size=140, layout_engine=ImageFont.Layout.RAQM)
    draw.text((W / 2, top + 5), "\u201c", font=quote_font, fill=(*accent, 200), anchor="ma")

    current_y = top + padding_y + 75
    for i, line in enumerate(wrapped_lines):
        stagger_offset = -22 if i % 2 == 1 else 22
        line_x = (W / 2) + stagger_offset
        text_color = (255, 255, 255) if i % 2 == 0 else accent_soft

        draw.text((line_x + 3, current_y + 3), line, font=font, fill=(0, 0, 0, 160), anchor="ma")
        draw.text((line_x, current_y), line, font=font, fill=text_color, anchor="ma")
        current_y += int(line_heights[i] * 1.35) + line_spacing

    if author_name:
        line_y = current_y + 12
        draw.line([W / 2 - 100, line_y, W / 2 + 100, line_y], fill=(*accent, 160), width=3)
        tagline_font = ImageFont.truetype(font_path, size=56, layout_engine=ImageFont.Layout.RAQM)
        draw.text((W / 2, line_y + 18), author_name.upper(), font=tagline_font, fill=(*accent, 235), anchor="ma")

    return img.convert('RGB')


def template_side_accent(img, quote_body, author_name, font_path, palette, quote_date=None):
    """Bold left-aligned quote with a vertical accent bar. Editorial / punchy feel."""
    accent = palette["accent"]

    font_size = pick_font_size(len(quote_body)) - 5
    font = ImageFont.truetype(font_path, size=font_size, layout_engine=ImageFont.Layout.RAQM)
    max_text_width = 760
    wrapped_lines = wrap_text(quote_body, font, max_text_width)

    line_spacing = 22
    line_heights = []
    total_h = 0
    for line in wrapped_lines:
        bbox = font.getbbox(line)
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
        total_h += int(lh * 1.3)
    total_h += line_spacing * (len(wrapped_lines) - 1)

    left_margin = 110
    start_y = (H - total_h) / 2 - 40

    img = img.convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Vertical accent bar
    bar_top = start_y - 20
    bar_bottom = start_y + total_h + 20
    draw.rounded_rectangle([left_margin - 45, bar_top, left_margin - 32, bar_bottom], radius=6, fill=(*accent, 230))

    current_y = start_y
    for i, line in enumerate(wrapped_lines):
        draw.text((left_margin + 3, current_y + 3), line, font=font, fill=(0, 0, 0, 170), anchor="la")
        draw.text((left_margin, current_y), line, font=font, fill=(255, 255, 255), anchor="la")
        current_y += int(line_heights[i] * 1.3) + line_spacing

    if author_name:
        tagline_font = ImageFont.truetype(font_path, size=48, layout_engine=ImageFont.Layout.RAQM)
        draw.text((left_margin, current_y + 30), f"— {author_name}", font=tagline_font, fill=(*accent, 235), anchor="la")

    # Small corner monogram-style quote mark, top right, very subtle
    quote_font = ImageFont.truetype(font_path, size=180, layout_engine=ImageFont.Layout.RAQM)
    draw.text((W - 90, 60), "\u201d", font=quote_font, fill=(255, 255, 255, 30), anchor="ma")

    return img.convert('RGB')


def template_minimal_bold(img, quote_body, author_name, font_path, palette, quote_date=None):
    """Full-bleed, no card — huge centered type directly on the textured background."""
    accent = palette["accent"]

    text_length = len(quote_body)
    font_size = 104 if text_length < 40 else (84 if text_length < 80 else 66)
    font = ImageFont.truetype(font_path, size=font_size, layout_engine=ImageFont.Layout.RAQM)
    max_text_width = 900
    wrapped_lines = wrap_text(quote_body, font, max_text_width)

    line_spacing = 24
    line_heights = []
    total_h = 0
    for line in wrapped_lines:
        bbox = font.getbbox(line)
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
        total_h += int(lh * 1.3)
    total_h += line_spacing * (len(wrapped_lines) - 1)

    img = img.convert('RGBA')
    draw = ImageDraw.Draw(img)

    start_y = (H - total_h) / 2
    current_y = start_y
    for i, line in enumerate(wrapped_lines):
        draw.text((W / 2 + 3, current_y + 3), line, font=font, fill=(0, 0, 0, 150), anchor="ma")
        draw.text((W / 2, current_y), line, font=font, fill=(255, 255, 255), anchor="ma")
        current_y += int(line_heights[i] * 1.3) + line_spacing

    if author_name:
        line_y = current_y + 35
        draw.line([W / 2 - 60, line_y, W / 2 + 60, line_y], fill=(*accent, 200), width=4)
        tagline_font = ImageFont.truetype(font_path, size=44, layout_engine=ImageFont.Layout.RAQM)
        spaced_name = "  ".join(list(author_name.upper()))  # letter-spaced feel for a minimalist label
        # letter-spacing every character is too aggressive for Kannada script; fall back to plain for non-ASCII
        display_name = spaced_name if author_name.isascii() else author_name.upper()
        draw.text((W / 2, line_y + 20), display_name, font=tagline_font, fill=(*accent, 235), anchor="ma")

    return img.convert('RGB')


def template_split_band(img, quote_body, author_name, font_path, palette, quote_date=None):
    """Solid accent-colored band at top, quote text below on the textured background."""
    accent = palette["accent"]
    bg1 = palette["bg1"]

    img = img.convert('RGBA')
    band_h = 130
    band = Image.new('RGBA', (W, band_h), (*accent, 235))
    img.paste(band, (0, 0), band)

    draw = ImageDraw.Draw(img)
    label_font = ImageFont.truetype(font_path, size=40, layout_engine=ImageFont.Layout.RAQM)
    draw.text((W / 2, band_h / 2), "\u2726 QUOTE OF THE DAY \u2726", font=label_font, fill=bg1, anchor="mm")

    font_size = pick_font_size(len(quote_body))
    font = ImageFont.truetype(font_path, size=font_size, layout_engine=ImageFont.Layout.RAQM)
    max_text_width = 880
    wrapped_lines = wrap_text(quote_body, font, max_text_width)

    line_spacing = 22
    line_heights = []
    total_h = 0
    for line in wrapped_lines:
        bbox = font.getbbox(line)
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
        total_h += int(lh * 1.3)
    total_h += line_spacing * (len(wrapped_lines) - 1)

    available_h = H - band_h - 160
    start_y = band_h + (available_h - total_h) / 2 + 40

    current_y = start_y
    for i, line in enumerate(wrapped_lines):
        draw.text((W / 2 + 3, current_y + 3), line, font=font, fill=(0, 0, 0, 160), anchor="ma")
        draw.text((W / 2, current_y), line, font=font, fill=(255, 255, 255), anchor="ma")
        current_y += int(line_heights[i] * 1.3) + line_spacing

    if author_name:
        tagline_font = ImageFont.truetype(font_path, size=50, layout_engine=ImageFont.Layout.RAQM)
        draw.text((W / 2, current_y + 30), f"— {author_name}", font=tagline_font, fill=(*accent, 235), anchor="ma")

    return img.convert('RGB')


def template_notes_card(img, quote_body, author_name, font_path, palette, quote_date=None):
    """Light 'notes app' style card — big bold dark text, header bar, date, footer brand strip.
    Inspired by the iOS-notes-style reference screenshot."""
    accent = palette["accent"]

    font_size = pick_font_size(len(quote_body)) - 6  # dark-on-light reads bigger, so trim slightly
    font = ImageFont.truetype(font_path, size=font_size, layout_engine=ImageFont.Layout.RAQM)
    max_text_width = 800
    wrapped_lines = wrap_text(quote_body, font, max_text_width)

    line_spacing = 16
    line_heights = []
    total_h = 0
    for line in wrapped_lines:
        bbox = font.getbbox(line)
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
        total_h += int(lh * 1.28)
    total_h += line_spacing * (len(wrapped_lines) - 1)

    header_h = 130
    date_h = 65
    footer_h = 95
    author_h = 70 if author_name else 20
    padding_y = 40
    card_w = 940
    card_h = header_h + date_h + total_h + author_h + footer_h + padding_y

    left = (W - card_w) / 2
    top = (H - card_h) / 2
    right = left + card_w
    bottom = top + card_h

    img = img.convert('RGBA')

    # Drop shadow
    shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rounded_rectangle([left, top + 16, right, bottom + 16], radius=32, fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    img = Image.alpha_composite(img, shadow)

    # Off-white card body
    card = Image.new('RGBA', (int(card_w), int(card_h)), (250, 248, 244, 255))
    mask = Image.new('L', card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, card.width, card.height], radius=32, fill=255)
    img.paste(card, (int(left), int(top)), mask)

    draw = ImageDraw.Draw(img)

    # Header: back arrow, "QUOTE OF THE DAY", "•••" menu dots
    header_font = ImageFont.truetype(font_path, size=32, layout_engine=ImageFont.Layout.RAQM)
    arrow_font = ImageFont.truetype(font_path, size=42, layout_engine=ImageFont.Layout.RAQM)
    draw.text((left + 40, top + 60), "\u2039", font=arrow_font, fill=accent, anchor="lm")
    draw.text((left + 80, top + 60), "QUOTE OF THE DAY", font=header_font, fill=accent, anchor="lm")
    draw.text((right - 40, top + 60), "\u2022\u2022\u2022", font=header_font, fill=(150, 145, 138), anchor="rm")
    draw.line([left + 30, top + header_h, right - 30, top + header_h], fill=(222, 217, 207), width=2)

    # Date
    if quote_date:
        date_font = ImageFont.truetype(font_path, size=28, layout_engine=ImageFont.Layout.RAQM)
        draw.text((W / 2, top + header_h + date_h / 2), quote_date, font=date_font, fill=(160, 155, 145), anchor="mm")

    # Big bold dark quote text, left-aligned like a real note
    current_y = top + header_h + date_h + 15
    for i, line in enumerate(wrapped_lines):
        draw.text((left + 50, current_y), line, font=font, fill=(28, 26, 24), anchor="la")
        current_y += int(line_heights[i] * 1.28) + line_spacing

    if author_name:
        author_font = ImageFont.truetype(font_path, size=34, layout_engine=ImageFont.Layout.RAQM)
        draw.text((left + 50, current_y + 18), f"[{author_name}]", font=author_font, fill=(120, 114, 106), anchor="la")

    # Footer brand strip
    footer_top = bottom - footer_h
    draw.line([left + 30, footer_top, right - 30, footer_top], fill=(222, 217, 207), width=2)
    brand_font = ImageFont.truetype(font_path, size=32, layout_engine=ImageFont.Layout.RAQM)
    draw.text((left + 50, bottom - footer_h / 2), BRAND_NAME, font=brand_font, fill=accent, anchor="lm")
    if CONTACT_NUMBER:
        draw.text((right - 50, bottom - footer_h / 2), CONTACT_NUMBER, font=brand_font, fill=(120, 114, 106), anchor="rm")

    return img.convert('RGB')


def template_bold_impact(img, quote_body, author_name, font_path, palette, quote_date=None):
    """Huge stacked outlined type with heavy drop shadow — poster/banner energy,
    inspired by the festive banner reference image."""
    accent = palette["accent"]
    accent_soft = palette["accent_soft"]

    text_length = len(quote_body)
    font_size = 128 if text_length < 40 else (98 if text_length < 80 else 74)
    font = ImageFont.truetype(font_path, size=font_size, layout_engine=ImageFont.Layout.RAQM)
    max_text_width = 960
    wrapped_lines = wrap_text(quote_body, font, max_text_width)

    line_spacing = 12
    line_heights = []
    total_h = 0
    for line in wrapped_lines:
        bbox = font.getbbox(line)
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
        total_h += int(lh * 1.22)
    total_h += line_spacing * (len(wrapped_lines) - 1)

    img = img.convert('RGBA')
    draw = ImageDraw.Draw(img)

    current_y = (H - total_h) / 2 - 30
    outline_w = 4
    for i, line in enumerate(wrapped_lines):
        color = (255, 255, 255) if i % 2 == 0 else accent_soft

        # Hard outline by stamping the text offset in a ring around the target position
        for ox in (-outline_w, 0, outline_w):
            for oy in (-outline_w, 0, outline_w):
                if ox == 0 and oy == 0:
                    continue
                draw.text((W / 2 + ox, current_y + oy), line, font=font, fill=(0, 0, 0, 210), anchor="ma")

        # Heavy drop shadow for a punchy, poster-like feel
        draw.text((W / 2 + 7, current_y + 7), line, font=font, fill=(0, 0, 0, 140), anchor="ma")
        draw.text((W / 2, current_y), line, font=font, fill=color, anchor="ma")
        current_y += int(line_heights[i] * 1.22) + line_spacing

    if author_name:
        line_y = current_y + 35
        draw.line([W / 2 - 95, line_y, W / 2 + 95, line_y], fill=(*accent, 230), width=5)
        tag_font = ImageFont.truetype(font_path, size=48, layout_engine=ImageFont.Layout.RAQM)
        draw.text((W / 2, line_y + 22), author_name.upper(), font=tag_font, fill=(*accent, 245), anchor="ma")

    return img.convert('RGB')


TEMPLATES = [
    template_centered_card,
    template_side_accent,
    template_minimal_bold,
    template_split_band,
    template_notes_card,
    template_bold_impact,
]


def main():
    clear_old_images()

    quotes = fetch_quotes_from_sheets()
    if not quotes:
        print("Error: No valid quotes loaded from your Google Sheet.")
        return

    print(f"\nLoaded {len(quotes)} quotes. Generating posters...\n")

    font_files = {}
    for name, url in FONT_URLS.items():
        filename = f"{name.replace(' ', '_').lower()}.ttf"
        if not os.path.exists(filename):
            response = requests.get(url, timeout=15)
            with open(filename, "wb") as f:
                f.write(response.content)
        font_files[name] = filename

    for idx, q in enumerate(quotes):
        category = q["category"]
        raw_text = q["text"]
        bg_prompt = q["prompt"]
        date_str = q["date"].replace("-", "")

        quote_body, author_name = parse_author(raw_text)
        print(f"[{idx + 1}/{len(quotes)}] Generating: '{quote_body[:25]}...'")

        palette = random.choice(PALETTES)
        img = generate_solid_background(palette, W, H)

        font_name = random.choice(list(FONT_URLS.keys()))
        font_path = font_files[font_name]

        template_fn = random.choice(TEMPLATES)
        today_display_date = datetime.now().strftime("%B %d, %Y")  # e.g. "July 10, 2026"
        img = template_fn(img, quote_body, author_name, font_path, palette, quote_date=today_display_date)

        apply_logo(img)

        output_dir = f"images/{category}"
        os.makedirs(output_dir, exist_ok=True)
        unique_hash = get_text_hash(quote_body)
        output_path = f"{output_dir}/quote_{date_str}_{unique_hash}.png"
        img.save(output_path, "PNG")

    print(f"\nSUCCESS: Generated {len(quotes)} quote posters!")


if __name__ == "__main__":
    main()
