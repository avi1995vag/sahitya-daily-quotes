import os
import csv
import random
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# Pre-filled directly from your Google Sheet ID
GOOGLE_SHEET_ID = "1rmyyD1lS3uAZ4c9WAkmTekDrrcx4X3jdvpJz8DWyhX0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"

# TODO: Add your free Pexels API Key here to load premium dark bokeh stock photos
PEXELS_API_KEY = "We2njvb6rYtUvXMH2fuU6IjHgSjOlpsUVFRCSibahkalqXN3m7v7eriF"

# Google Font URLs for your requested styles
FONT_URLS = {
    "Anek Kannada": "https://github.com/google/fonts/raw/main/ofl/anekkannada/AnekKannada%5Bwdth,wght%5D.ttf",
    "Hubballi": "https://github.com/google/fonts/raw/main/ofl/hubballi/Hubballi-Regular.ttf"
}

def generate_dark_radial_gradient(W, H):
    """Fallback elegant dark radial gradient if Pexels API is not configured."""
    base = Image.new('RGB', (W, H), (18, 18, 18))
    draw = ImageDraw.Draw(base)
    for r in range(W, 0, -8):
        alpha = int((1 - (r / float(W))) * 45)
        color = (25, 25, 25)
        draw.ellipse([W/2 - r, H/2 - r, W/2 + r, H/2 + r], fill=color + (alpha,))
    return base

def fetch_pexels_background(prompt, W, H):
    """Fetches high-end dark, moody, or minimalist stock photos matching the prompt."""
    if not PEXELS_API_KEY or PEXELS_API_KEY == "YOUR_PEXELS_API_KEY_HERE":
        return None
    
    headers = {"Authorization": PEXELS_API_KEY}
    # Force search query to target elegant, high-contrast, minimalist templates
    search_query = f"dark minimalist abstract"
    if "special" in prompt.lower() or "festive" in prompt.lower():
        search_query = "gold bokeh dark abstract"
        
    url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(search_query)}&per_page=15"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            photos = data.get("photos", [])
            if photos:
                # Pick a random high-quality photo from the matching list for variety
                photo = random.choice(photos)
                img_url = photo["src"].get("large2x") or photo["src"].get("original")
                if img_url:
                    print(f"Downloading Pexels Stock Background: {img_url}")
                    img_response = requests.get(img_url, timeout=30)
                    with open("temp_bg.jpg", "wb") as f:
                        f.write(img_response.content)
                    return Image.open("temp_bg.jpg").resize((W, H))
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

def fetch_quotes_from_sheets():
    quotes = []
    try:
        print("Connecting to your Google Sheet database...")
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

def main():
    quotes = fetch_quotes_from_sheets()
    if not quotes:
        print("Error: No valid quotes loaded from your Google Sheet.")
        return

    print(f"\nSUCCESS: Loaded {len(quotes)} quotes. Generating posters...\n")

    font_files = {}
    for name, url in FONT_URLS.items():
        filename = f"{name.replace(' ', '_').lower()}.ttf"
        if not os.path.exists(filename):
            response = requests.get(url, timeout=15)
            with open(filename, "wb") as f:
                f.write(response.content)
        font_files[name] = filename

    W, H = 1080, 1080

    for idx, q in enumerate(quotes):
        category = q["category"]
        text = q["text"]
        bg_prompt = q["prompt"]
        date_str = q["date"].replace("-", "")

        print(f"[{idx + 1}/{len(quotes)}] Generating creative layout for: '{text[:25]}...'")

        # 1. Fetch Background (Tries Pexels first, falls back to dark gradient if unconfigured)
        img = fetch_pexels_background(bg_prompt, W, H)
        if img is None:
            img = generate_dark_radial_gradient(W, H)

        # 2. Select a font style
        font_name = random.choice(list(FONT_URLS.keys()))
        font_path = font_files[font_name]

        # 3. Dynamic Font Scaling
        text_length = len(text)
        if text_length < 35:
            font_size = 72
        elif text_length < 65:
            font_size = 56
        else:
            font_size = 46

        # Engage Raqm layout engine for perfect, unbreakable complex Kannada shaping
        font = ImageFont.truetype(font_path, size=font_size, layout_engine=ImageFont.Layout.RAQM)

        # 4. Perform Word Wrapping
        max_text_width = 850 
        wrapped_lines = wrap_text(text, font, max_text_width)

        # 5. Calculate Dynamic Card Height
        line_spacing = 18
        total_text_height = 0
        line_heights = []

        for line in wrapped_lines:
            bbox = font.getbbox(line)
            line_h = bbox[3] - bbox[1]
            line_heights.append(line_h)
            total_text_height += line_h

        total_text_height += line_spacing * (len(wrapped_lines) - 1)

        # Calculate card dimensions with vertical padding
        padding_y = 65
        card_w = 920
        card_h = total_text_height + (padding_y * 2) + 80  # Extra space for quote icon

        left = (W - card_w) / 2
        top = (H - card_h) / 2
        right = left + card_w
        bottom = top + card_h

        # Draw rounded semi-transparent dark container (high contrast card)
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle([left, top, right, bottom], radius=24, fill=(0, 0, 0, 150))
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        draw = ImageDraw.Draw(img)

        # 6. DRAW CREATIVE SERIF QUOTE ICON (“”) AT THE TOP OF THE CARD
        quote_icon = "“"
        quote_font = ImageFont.truetype(font_path, size=110, layout_engine=ImageFont.Layout.RAQM)
        draw.text((W / 2, top + 15), quote_icon, font=quote_font, fill=(255, 255, 255, 180), anchor="ma")

        # 7. Draw the Wrapped Text Lines with subtle 3D Drop Shadows
        current_y = top + padding_y + 70
        for i, line in enumerate(wrapped_lines):
            shadow_offset = 4
            draw.text((W / 2 + shadow_offset, current_y + shadow_offset), line, font=font, fill=(0, 0, 0, 180), anchor="ma")
            draw.text((W / 2, current_y), line, font=font, fill="white", anchor="ma")
            current_y += line_heights[i] + line_spacing

        # 8. DRAW AN ELEGANT HORIZONTAL SEPARATOR LINE BELOW TEXT
        line_y = current_y + 10
        draw.line([W/2 - 120, line_y, W/2 + 120, line_y], fill=(255, 255, 255, 100), width=3)

        # 9. DRAW THE DESIGN TAGLINE (Gold/Orange Contrasting Color)
        tagline = "ಸಾಹಿತ್ಯ ವಿಚಾರ ಲಹರಿ" # "Sahitya Thought Stream"
        tagline_font = ImageFont.truetype(font_path, size=26, layout_engine=ImageFont.Layout.RAQM)
        # Gold/Orange Accent Color (#FFAA33)
        draw.text((W / 2, line_y + 20), tagline, font=tagline_font, fill=(255, 170, 51, 220), anchor="ma")

        # 10. DRAW CUSTOM LOGO WATERMARK (If logo.png is uploaded to repository root)
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                aspect_ratio = logo.width / float(logo.height)
                logo_h = 50
                logo_w = int(logo_h * aspect_ratio)
                logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
                
                logo_x = W - logo.width - 50
                logo_y = H - logo.height - 50
                img.paste(logo, (logo_x, logo_y), logo)
            except Exception as e:
                print(f"Failed to apply logo watermark: {e}")
        else:
            watermark_text = "ಸಾಹಿತ್ಯ ಕೀಬೋರ್ಡ್‌"
            watermark_font = ImageFont.truetype(font_path, size=24, layout_engine=ImageFont.Layout.RAQM)
            draw.text((W - 50, H - 50), watermark_text, font=watermark_font, fill=(255, 255, 255, 180), anchor="rd")

        # 11. Save the final high-definition poster
        output_dir = f"images/{category}"
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = f"{output_dir}/quote_{date_str}_{idx + 1}.png"
        img.convert('RGB').save(output_path, "PNG")

    print(f"\nSUCCESS: Generated {len(quotes)} high-definition quote posters!")

if __name__ == "__main__":
    main()
