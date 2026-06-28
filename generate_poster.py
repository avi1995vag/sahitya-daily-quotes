import os
import csv
import random
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# SAFEGUARD: Forces Pygame to run headlessly on headless Linux servers (no display monitor required)
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.font.init()

# Pre-filled directly from your Google Sheet
GOOGLE_SHEET_ID = "1rmyyD1lS3uAZ4c9WAkmTekDrrcx4X3jdvpJz8DWyhX0"

# Target ONLY the first tab ("New Quotes") using gid=0, bypassing any 404 blocks
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"

# TODO: Add your free Pexels API Key here to load premium dark bokeh stock photos
PEXELS_API_KEY = "We2njvb6rYtUvXMH2fuU6IjHgSjOlpsUVFRCSibahkalqXN3m7v7eriF"

# Google Font URLs for your requested styles
FONT_URLS = {
    "Anek Kannada": "https://github.com/google/fonts/raw/main/ofl/anekkannada/AnekKannada%5Bwdth,wght%5D.ttf",
    "Hubballi": "https://github.com/google/fonts/raw/main/ofl/hubballi/Hubballi-Regular.ttf"
}

# Dark, highly aesthetic background palettes
GRADIENTS = [
    ((20, 20, 35), (45, 45, 65)),  # Cosmic Dark Blue
    ((30, 20, 20), (60, 40, 40)),  # Dark Cherry Red
    ((15, 25, 20), (35, 55, 45)),  # Deep Forest Green
    ((24, 24, 24), (48, 48, 48))   # Modern Carbon Grey
]

def generate_dark_gradient(W, H):
    """Procedurally generates a smooth, modern dark gradient background."""
    color1, color2 = random.choice(GRADIENTS)
    base = Image.new('RGB', (W, H), color1)
    top_layer = Image.new('RGB', (W, H), color2)
    mask = Image.new('L', (W, H))
    mask_draw = ImageDraw.Draw(mask)
    for y in range(H):
        alpha = int((y / float(H)) * 255)
        mask_draw.line((0, y, W, y), fill=alpha)
    return Image.composite(top_layer, base, mask)

def fetch_pexels_background(prompt, W, H):
    """Fetches high-end dark, moody, or minimalist stock photos matching the prompt."""
    if not PEXELS_API_KEY or PEXELS_API_KEY == "YOUR_PEXELS_API_KEY_HERE":
        return None
    
    headers = {"Authorization": PEXELS_API_KEY}
    
    # Target elegant, high-contrast, minimalist templates
    search_query = "dark minimalist abstract"
    if "special" in prompt.lower() or "festive" in prompt.lower():
        search_query = "gold bokeh dark abstract"
        
    url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(search_query)}&per_page=15"
    
    try:
        # FIXED: Corrected 'apiUrl' variable to 'url' to resolve execution crashes
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            photos = data.get("photos", [])
            if photos:
                # Pick a random photo from the matching list for variety
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

def wrap_text_pygame(text, pygame_font, max_width):
    words = text.split(' ')
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        width, _ = pygame_font.size(test_line)
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

    # Download font files locally
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
        raw_text = q["text"]
        bg_prompt = q["prompt"]
        date_str = q["date"].replace("-", "")

        # A. PARSE AUTHOR NAMES: Split text if it contains standard hyphens or dashes
        author_name = ""
        quote_body = raw_text
        for separator in [" - ", " — ", " -", " – "]:
            if separator in raw_text:
                parts = raw_text.split(separator, 1)
                quote_body = parts[0].strip()
                author_name = parts[1].strip()
                break

        print(f"[{idx + 1}/{len(quotes)}] Generating creative layout for: '{quote_body[:25]}...'")

        # 1. Fetch Background (Tries Pexels first, falls back to dark gradient if unconfigured)
        img = fetch_pexels_background(bg_prompt, W, H)
        if img is None:
            img = generate_dark_gradient(W, H)

        # 2. Select a font style
        font_name = random.choice(list(FONT_URLS.keys()))
        font_path = font_files[font_name]

        # 3. SUPER-SIZED TYPOGRAPHY (Large fonts to cover empty space)
        text_length = len(quote_body)
        if text_length < 35:
            font_size = 85
        elif text_length < 75:
            font_size = 65
        else:
            font_size = 52

        pg_font = pygame.font.Font(font_path, font_size)

        # 4. Perform Word Wrapping
        max_text_width = 860 
        wrapped_lines = wrap_text_pygame(quote_body, pg_font, max_text_width)

        # 5. Calculate Dynamic Card Height with 1.35x Safety Multiplier (Prevents vertical overflow)
        line_spacing = 20
        total_text_height = 0
        line_layers = []

        for line in wrapped_lines:
            text_surface = pg_font.render(line, True, (255, 255, 255))
            surface_bytes = pygame.image.tobytes(text_surface, "RGBA")
            fg_img = Image.frombytes("RGBA", text_surface.get_size(), surface_bytes)

            shadow_surface = pg_font.render(line, True, (0, 0, 0))
            shadow_bytes = pygame.image.tobytes(shadow_surface, "RGBA")
            bg_img = Image.frombytes("RGBA", shadow_surface.get_size(), shadow_bytes)

            line_layers.append((fg_img, bg_img))
            
            # Apply 1.35x scale factor to account for vertical consonant conjunct spacing
            total_text_height += int(fg_img.height * 1.35)

        total_text_height += line_spacing * (len(wrapped_lines) - 1)

        # Calculate card dimensions with spacing and vertical buffers
        padding_y = 75
        card_w = 940
        card_h = total_text_height + (padding_y * 2) + 120  # Added safety space for quote icon

        left = (W - card_w) / 2
        top = (H - card_h) / 2
        right = left + card_w
        bottom = top + card_h

        # Draw rounded semi-transparent dark container
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle([left, top, right, bottom], radius=24, fill=(0, 0, 0, 150))
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        draw = ImageDraw.Draw(img)

        # 6. Draw elegant quotation marks
        quote_icon = "“"
        quote_font = ImageFont.truetype(font_path, size=120)
        draw.text((W / 2, top + 15), quote_icon, font=quote_font, fill=(255, 255, 255, 180), anchor="ma")

        # 7. Draw Wrapped Text Lines with 3D shadows
        current_y = top + padding_y + 80
        for fg_img, bg_img in line_layers:
            line_x = (W - fg_img.width) // 2
            shadow_offset = 4
            
            # Shadow
            shadow_alpha = Image.new("L", bg_img.size, 160)
            img.paste(bg_img, (line_x + shadow_offset, int(current_y) + shadow_offset), shadow_alpha)
            # Foreground text
            img.paste(fg_img, (line_x, int(current_y)), fg_img)
            
            current_y += int(fg_img.height * 1.35) + line_spacing

        # 8. DRAW AUTHOR NAME OR MINIMAL LINE (Only if a real author is parsed)
        if author_name:
            line_y = current_y + 10
            draw.line([W/2 - 120, line_y, W/2 + 120, line_y], fill=(255, 255, 255, 100), width=3)
            
            tagline_font = ImageFont.truetype(font_path, size=28, layout_engine=ImageFont.Layout.RAQM)
            # Render Author name in rich gold accent (#FFAA33)
            draw.text((W / 2, line_y + 20), author_name, font=tagline_font, fill=(255, 170, 51, 220), anchor="ma")

        # 9. Apply Custom Logo Watermark in Corner
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

        # 10. Save the final high-definition poster
        output_dir = f"images/{category}"
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = f"{output_dir}/quote_{date_str}_{idx + 1}.png"
        img.convert('RGB').save(output_path, "PNG")

    print(f"\nSUCCESS: Generated {len(quotes)} quote posters!")

if __name__ == "__main__":
    main()
