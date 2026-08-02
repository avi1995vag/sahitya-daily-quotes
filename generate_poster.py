import os
import csv
import io
import re
import requests
import hashlib
from PIL import Image, ImageDraw, ImageFont

# Optional CairoSVG import (falls back smoothly to direct PNG icons if absent)
CAIROSVG_AVAILABLE = False
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    pass

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================

GOOGLE_SHEET_ID = "1rmyyD1lS3uAZ4c9WAkmTekDrrcx4X3jdvpJz8DWyhX0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"

# Canvas Dimensions
W, H = 1080, 1080

# 6 THEME BACKGROUND COLORS (Mapped to categories)
THEME_COLORS = {
    "daily_special": (0, 151, 156),   # 1. Teal
    "daily": (0, 151, 156),
    "inspirational": (74, 21, 75),   # 2. Deep Royal Purple
    "motivational": (74, 21, 75),
    "wisdom": (27, 59, 111),         # 3. Midnight Royal Blue
    "author_quote": (27, 59, 111),
    "success": (175, 100, 20),       # 4. Warm Golden Amber
    "love": (165, 32, 64),           # 5. Crimson Rose
    "life": (38, 85, 70),            # 6. Deep Emerald Green
}

DEFAULT_BG_COLOR = (0, 151, 156)

# Text & Accent Colors
COLOR_TEXT = (255, 255, 255)        # White main quote text
COLOR_QUOTE_MARK = (245, 226, 0)    # Yellow quote marks
COLOR_AUTHOR = (240, 232, 210)      # Soft Gold / Cream for Author
COLOR_BRAND = (255, 255, 255)       # White branding at bottom

# Branding Text
BRAND_NAME = "Sahitya Keyboard"

# Fonts
FONT_URLS = {
    "Anek_Kannada": "https://github.com/google/fonts/raw/main/ofl/anekkannada/AnekKannada%5Bwdth,wght%5D.ttf",
    "Hubballi": "https://github.com/google/fonts/raw/main/ofl/hubballi/Hubballi-Regular.ttf"
}

# Icon mapping for instant CDN matching
KEYWORD_ICON_MAP = {
    "bicycle": "bicycle",
    "bike": "bicycle",
    "heart": "heart",
    "love": "heart",
    "book": "book",
    "knowledge": "book",
    "light": "light-bulb",
    "idea": "light-bulb",
    "star": "star",
    "magic": "sparkles",
    "sparkle": "sparkles",
    "target": "goal",
    "trophy": "trophy",
    "success": "trophy",
    "smile": "happy",
    "time": "time",
    "clock": "time",
    "inspirational": "sparkles",
    "motivational": "flex-biceps",
    "wisdom": "brain",
    "life": "compass",
    "daily_special": "calendar",
    "daily": "calendar",
    "author_quote": "quote-left"
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def download_file(url, save_path):
    if not os.path.exists(save_path):
        try:
            res = requests.get(url, timeout=15)
            if res.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(res.content)
        except Exception as e:
            print(f"Failed downloading {url}: {e}")

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
                    if date_val and category_val and text_val:
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

# ============================================================
# GUARANTEED FLATICON ENGINE
# ============================================================

def extract_keyword_from_quote(quote_body, category):
    """Extracts topic keyword from quote text or category."""
    text_lower = quote_body.lower()
    
    for kw in KEYWORD_ICON_MAP.keys():
        if kw in text_lower:
            return kw
            
    if category and category.strip():
        return category.strip().lower()
        
    return "quote"

def fetch_quote_relevant_icon(keyword):
    """Fetches white flat PNG icon with multi-cdn fallbacks."""
    icon_name = KEYWORD_ICON_MAP.get(keyword.lower(), "quote-left")
    
    # 1. Primary: Direct CDN PNG (Fast, 0 C-library dependencies)
    cdn_url = f"https://img.icons8.com/ios-filled/120/FFFFFF/{icon_name}.png"
    try:
        res = requests.get(cdn_url, timeout=6)
        if res.status_code == 200 and len(res.content) > 200:
            return Image.open(io.BytesIO(res.content)).convert("RGBA")
    except Exception as e:
        print(f"CDN icon fetch failed for '{keyword}': {e}")

    # 2. Secondary: Iconify API Vector rendering
    try:
        search_url = f"https://api.iconify.design/search?query={keyword}&limit=3"
        res = requests.get(search_url, timeout=6)
        if res.status_code == 200 and res.json().get("icons"):
            iconify_name = res.json()["icons"][0]
            svg_url = f"https://api.iconify.design/{iconify_name}.svg?color=%23FFFFFF&width=120&height=120"
            svg_res = requests.get(svg_url, timeout=6)
            if svg_res.status_code == 200 and CAIROSVG_AVAILABLE:
                png_bytes = cairosvg.svg2png(bytestring=svg_res.content, output_width=120, output_height=120)
                return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    except Exception as e:
        print(f"Iconify fetch failed for '{keyword}': {e}")

    # 3. Fallback: Default White Quote Icon
    try:
        fallback_url = "https://img.icons8.com/ios-filled/120/FFFFFF/quote-left.png"
        res = requests.get(fallback_url, timeout=6)
        if res.status_code == 200:
            return Image.open(io.BytesIO(res.content)).convert("RGBA")
    except Exception as e:
        print(f"Fallback icon failed: {e}")

    return None

# ============================================================
# UNIFIED POSTER RENDERER
# ============================================================

def render_poster(quote_body, author_name, category, main_font_path, brand_font_path):
    # 1. Select Background Theme
    bg_color = THEME_COLORS.get(category.lower(), DEFAULT_BG_COLOR)
    img = Image.new('RGBA', (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # 2. Extract Keyword & Load Top Flat Icon
    keyword = extract_keyword_from_quote(quote_body, category)
    icon = fetch_quote_relevant_icon(keyword)
    
    if icon:
        icon_x = int((W - icon.width) / 2)
        icon_y = 150
        img.paste(icon, (icon_x, icon_y), icon)

    # 3. Typography & Text Wrapping
    font_size = 62 if len(quote_body) < 60 else (52 if len(quote_body) < 110 else 44)
    font = ImageFont.truetype(main_font_path, size=font_size, layout_engine=ImageFont.Layout.RAQM)
    quote_mark_font = ImageFont.truetype(main_font_path, size=font_size + 14, layout_engine=ImageFont.Layout.RAQM)

    max_width = 820
    wrapped_lines = wrap_text(quote_body, font, max_width)

    line_heights = []
    total_text_h = 0
    line_spacing = 18
    for line in wrapped_lines:
        bbox = font.getbbox(line)
        lh = bbox[3] - bbox[1]
        line_heights.append(lh)
        total_text_h += int(lh * 1.3)
    total_text_h += line_spacing * (len(wrapped_lines) - 1)

    # 4. Draw Quote Body with Yellow Quote Marks “...”
    start_y = 360 + (300 - total_text_h) / 2
    current_y = start_y

    for i, line in enumerate(wrapped_lines):
        line_bbox = font.getbbox(line)
        line_w = line_bbox[2] - line_bbox[0]
        line_x = (W - line_w) / 2

        # Yellow opening quote mark “
        if i == 0:
            open_quote = "“"
            q_bbox = quote_mark_font.getbbox(open_quote)
            q_w = q_bbox[2] - q_bbox[0]
            draw.text((line_x - q_w - 4, current_y - 8), open_quote, font=quote_mark_font, fill=COLOR_QUOTE_MARK, anchor="la")

        # Main text in White
        draw.text((line_x, current_y), line, font=font, fill=COLOR_TEXT, anchor="la")

        # Yellow closing quote mark ”
        if i == len(wrapped_lines) - 1:
            close_quote = "”"
            draw.text((line_x + line_w + 2, current_y - 8), close_quote, font=quote_mark_font, fill=COLOR_QUOTE_MARK, anchor="la")

        current_y += int(line_heights[i] * 1.3) + line_spacing

    # 5. Author Name
    if author_name:
        author_font = ImageFont.truetype(main_font_path, size=38, layout_engine=ImageFont.Layout.RAQM)
        draw.text((W / 2, current_y + 35), author_name.upper(), font=author_font, fill=COLOR_AUTHOR, anchor="ma")

    # 6. Footer Branding
    brand_font = ImageFont.truetype(brand_font_path, size=52, layout_engine=ImageFont.Layout.RAQM)
    draw.text((W / 2, H - 90), BRAND_NAME, font=brand_font, fill=COLOR_BRAND, anchor="mm")

    return img.convert('RGB')

# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    clear_old_images()

    quotes = fetch_quotes_from_sheets()
    if not quotes:
        print("Error: No valid quotes loaded from your Google Sheet.")
        return

    print(f"\nLoaded {len(quotes)} quotes. Generating posters...\n")

    # Download required fonts
    font_files = {}
    for name, url in FONT_URLS.items():
        filename = f"{name}.ttf"
        download_file(url, filename)
        font_files[name] = filename

    main_font = font_files["Anek_Kannada"]
    brand_font = font_files["Hubballi"]

    for idx, q in enumerate(quotes):
        category = q["category"]
        raw_text = q["text"]
        date_str = q["date"].replace("-", "")

        quote_body, author_name = parse_author(raw_text)
        print(f"[{idx + 1}/{len(quotes)}] Generating poster ({category}): '{quote_body[:30]}...'")

        # Render poster
        img = render_poster(quote_body, author_name, category, main_font, brand_font)

        # Save Image
        output_dir = f"images/{category}"
        os.makedirs(output_dir, exist_ok=True)
        unique_hash = get_text_hash(quote_body)
        output_path = f"{output_dir}/quote_{date_str}_{unique_hash}.png"
        img.save(output_path, "PNG")

    print(f"\nSUCCESS: Generated {len(quotes)} quote posters!")

if __name__ == "__main__":
    main()
