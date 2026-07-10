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

# NOTE: Prefer setting this as an environment variable (PEXELS_API_KEY)
# instead of hardcoding it, especially if this file goes into a git repo.
PEXELS_API_KEY = os.environ.get(
    "PEXELS_API_KEY",
    "We2njvb6rYtUvXMH2fuU6IjHgSjOlpsUVFRCSibahkalqXN3m7v7eriF"
)

FONT_URLS = {
    "Anek Kannada": "https://github.com/google/fonts/raw/main/ofl/anekkannada/AnekKannada%5Bwdth,wght%5D.ttf",
    "Hubballi": "https://github.com/google/fonts/raw/main/ofl/hubballi/Hubballi-Regular.ttf"
}

W, H = 1080, 1080

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


def generate_textured_gradient(palette, W, H):
    """Diagonal gradient + soft vignette + fine grain for a premium, non-flat background."""
    bg1, bg2 = palette["bg1"], palette["bg2"]
    base = Image.new('RGB', (W, H), bg1)
    top_layer = Image.new('RGB', (W, H), bg2)
    mask = Image.new('L', (W, H))
    mpix = mask.load()

    # Diagonal gradient (more dynamic than a flat top-to-bottom fade)
    for y in range(H):
        for x in range(0, W, 4):  # step 4 for speed, upscale-safe since it's a smooth gradient
            t = ((x / W) * 0.5 + (y / H) * 0.5)
            val = int(max(0, min(255, t * 255)))
            for dx in range(4):
                if x + dx < W:
                    mpix[x + dx, y] = val

    img = Image.composite(top_layer, base, mask).convert('RGB')

    # Soft vignette (darken corners slightly for focus)
    vignette = Image.new('L', (W, H), 0)
    vdraw = ImageDraw.Draw(vignette)
    vdraw.ellipse([-W * 0.3, -H * 0.3, W * 1.3, H * 1.3], fill=80)
    vignette = vignette.filter(ImageFilter.GaussianBlur(180))
    dark = Image.new('RGB', (W, H), (0, 0, 0))
    img = Image.composite(img, dark, vignette)

    # Fine grain for a textured, non-plastic look
    noise = Image.effect_noise((W, H), 18).convert('L')
    noise_rgb = Image.merge('RGB', (noise, noise, noise))
    img = Image.blend(img, noise_rgb, 0.03)

    return img


def fetch_pexels_background(prompt, palette_name, W, H):
    """Fetches a moody stock photo matching the prompt + chosen palette mood."""
    if not PEXELS_API_KEY or PEXELS_API_KEY == "YOUR_PEXELS_API_KEY_HERE":
        return None

    headers = {"Authorization": PEXELS_API_KEY}
    mood_map = {
        "Midnight Ocean": "dark blue ocean abstract",
        "Royal Plum": "purple abstract dark texture",
        "Emerald Noir": "dark green forest abstract",
        "Sunset Ember": "orange abstract dark texture",
        "Charcoal Gold": "gold bokeh dark abstract",
        "Deep Indigo": "indigo abstract dark texture",
    }
    search_query = mood_map.get(palette_name, "dark minimalist abstract")
    if "special" in prompt.lower() or "festive" in prompt.lower():
        search_query = "gold bokeh dark abstract"

    url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(search_query)}&per_page=15"

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            photos = data.get("photos", [])
            if photos:
                photo = random.choice(photos)
                img_url = photo["src"].get("large2x") or photo["src"].get("original")
                if img_url:
                    print(f"Downloading Pexels Stock Background: {img_url}")
                    img_response = requests.get(img_url, timeout=30)
                    with open("temp_bg.jpg", "wb") as f:
                        f.write(img_response.content)
                    photo_img = Image.open("temp_bg.jpg").resize((W, H)).convert('RGB')
                    # Darken so text stays readable regardless of the photo
                    darken = Image.new('RGB', (W, H), (0, 0, 0))
                    return Image.blend(photo_img, darken, 0.45)
    except Exception as e:
        print(f"Failed to fetch Pexels background: {e}")
    return None


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
        return 85
    elif text_length < 75:
        return 65
    return 52


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

def template_centered_card(img, quote_body, author_name, font_path, palette):
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


def template_side_accent(img, quote_body, author_name, font_path, palette):
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


def template_minimal_bold(img, quote_body, author_name, font_path, palette):
    """Full-bleed, no card — huge centered type directly on the textured background."""
    accent = palette["accent"]

    text_length = len(quote_body)
    font_size = 92 if text_length < 40 else (72 if text_length < 80 else 58)
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


def template_split_band(img, quote_body, author_name, font_path, palette):
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


TEMPLATES = [template_centered_card, template_side_accent, template_minimal_bold, template_split_band]


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

        img = fetch_pexels_background(bg_prompt, palette["name"], W, H)
        if img is None:
            img = generate_textured_gradient(palette, W, H)

        font_name = random.choice(list(FONT_URLS.keys()))
        font_path = font_files[font_name]

        template_fn = random.choice(TEMPLATES)
        img = template_fn(img, quote_body, author_name, font_path, palette)

        apply_logo(img)

        output_dir = f"images/{category}"
        os.makedirs(output_dir, exist_ok=True)
        unique_hash = get_text_hash(quote_body)
        output_path = f"{output_dir}/quote_{date_str}_{unique_hash}.png"
        img.save(output_path, "PNG")

    print(f"\nSUCCESS: Generated {len(quotes)} quote posters!")


if __name__ == "__main__":
    main()
