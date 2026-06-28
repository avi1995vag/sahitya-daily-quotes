import os
import csv
import random
import requests
import re
import hashlib
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# Forces Pygame to run headlessly on Linux servers
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.font.init()

GOOGLE_SHEET_ID = "1rmyyD1lS3uAZ4c9WAkmTekDrrcx4X3jdvpJz8DWyhX0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"

FONT_URLS = {
    "Anek Kannada": "https://github.com/google/fonts/raw/main/ofl/anekkannada/AnekKannada%5Bwdth,wght%5D.ttf",
    "Hubballi": "https://github.com/google/fonts/raw/main/ofl/hubballi/Hubballi-Regular.ttf"
}

# Dark, highly aesthetic background gradients
GRADIENTS = [
    ((20, 20, 35), (45, 45, 65)),  # Cosmic Dark Blue
    ((30, 20, 20), (60, 40, 40)),  # Dark Cherry Red
    ((15, 25, 20), (35, 55, 45)),  # Deep Forest Green
    ((24, 24, 24), (48, 48, 48))   # Modern Carbon Grey
]

def generate_dark_gradient(W, H):
    color1, color2 = random.choice(GRADIENTS)
    base = Image.new('RGB', (W, H), color1)
    top_layer = Image.new('RGB', (W, H), color2)
    mask = Image.new('L', (W, H))
    mask_draw = ImageDraw.Draw(mask)
    for y in range(H):
        alpha = int((y / float(H)) * 255)
        mask_draw.line((0, y, W, y), fill=alpha)
    return Image.composite(top_layer, base, mask)

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

def get_text_hash(text):
    """Generates a short, unique 8-character hash of the text to prevent naming conflicts."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

def clear_old_images():
    """Wipes out any old PNG files from previous runs so deleted quotes disappear from quotes.json."""
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

def main():
    # 1. Clear obsolete image assets first
    clear_old_images()

    quotes = fetch_quotes_from_sheets()
    if not quotes:
        print("Error: No valid quotes loaded from your Google Sheet.")
        return

    print(f"\nLoaded {len(quotes)} quotes. Generating posters...\n")

    # Download font files
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
        date_str = q["date"].replace("-", "")

        # A. ROBUST REGEX AUTHOR PARSING (Successfully parses '?.- ಕುವೆಂಪು', ', - author', etc.)
        author_name = ""
        quote_body = raw_text
        
        # Matches any typical hyphen/dash with optional preceding punctuation, followed by the author name
        match = re.search(r'[\.\?\!\s]*[-\u2014\u2013\u2212]\s*([^-—–]+)$', raw_text)
        if match:
            author_name = match.group(1).strip()
            quote_body = raw_text[:match.start()].strip()

        print(f"[{idx + 1}/{len(quotes)}] Generating creative layout for: '{quote_body[:25]}...'")

        # 2. Generate dark background
        img = generate_dark_gradient(W, H)

        # 3. Select a font style
        font_name = random.choice(list(FONT_URLS.keys()))
        font_path = font_files[font_name]

        # 4. SUPER-SIZED TYPOGRAPHY (Large fonts to fill space)
        text_length = len(quote_body)
        if text_length < 35:
            font_size = 85
        elif text_length < 75:
            font_size = 65
        else:
            font_size = 52

        pg_font = pygame.font.Font(font_path, font_size)

        # 5. Perform Word Wrapping
        max_text_width = 860 
        wrapped_lines = wrap_text_pygame(quote_body, pg_font, max_text_width)

        # 6. Calculate Dynamic Card Height with 1.35x Safety Multiplier
        line_spacing = 20
        total_text_height = 0
        line_layers = []

        for line in wrapped_lines:
            # Alternating Kinetic Colors: Even lines White, Odd lines Soft Yellow/Gold (#FFE17D)
            is_even = len(line_layers) % 2 == 0
            text_color = (255, 255, 255) if is_even else (255, 225, 125)

            text_surface = pg_font.render(line, True, text_color)
            surface_bytes = pygame.image.tobytes(text_surface, "RGBA")
            fg_img = Image.frombytes("RGBA", text_surface.get_size(), surface_bytes)

            shadow_surface = pg_font.render(line, True, (0, 0, 0))
            shadow_bytes = pygame.image.tobytes(shadow_surface, "RGBA")
            bg_img = Image.frombytes("RGBA", shadow_surface.get_size(), shadow_bytes)

            line_layers.append((fg_img, bg_img))
            total_text_height += int(fg_img.height * 1.35)

        total_text_height += line_spacing * (len(wrapped_lines) - 1)

        # Calculate card dimensions
        padding_y = 75
        card_w = 940
        card_h = total_text_height + (padding_y * 2) + 120  

        left = (W - card_w) / 2
        top = (H - card_h) / 2
        right = left + card_w
        bottom = top + card_h

        # Draw rounded semi-transparent container
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle([left, top, right, bottom], radius=24, fill=(0, 0, 0, 150))
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        draw = ImageDraw.Draw(img)

        # 7. Draw quotation marks
        quote_icon = "“"
        quote_font = ImageFont.truetype(font_path, size=120)
        draw.text((W / 2, top + 15), quote_icon, font=quote_font, fill=(255, 255, 255, 180), anchor="ma")

        # 8. Draw Kinetic Wrapped Lines (Alternating staggered alignments)
        current_y = top + padding_y + 80
        for i, (fg_img, bg_img) in enumerate(line_layers):
            base_x = (W - fg_img.width) // 2
            
            # Kinetic Stagger: Shifts odd lines slightly left, even lines slightly right (-25px / +25px)
            stagger_offset = -25 if i % 2 == 1 else 25
            line_x = base_x + stagger_offset
            
            # Ensure text doesn't clipping-leak past the card edges
            if line_x < left + 30: line_x = int(left + 30)
            if line_x + fg_img.width > right - 30: line_x = int(right - 30 - fg_img.width)

            shadow_offset = 4
            # Draw shadow
            shadow_alpha = Image.new("L", bg_img.size, 160)
            img.paste(bg_img, (line_x + shadow_offset, int(current_y) + shadow_offset), shadow_alpha)
            # Draw text
            img.paste(fg_img, (line_x, int(current_y)), fg_img)
            
            current_y += int(fg_img.height * 1.35) + line_spacing

        # 9. Draw Author Line Divider (Only if a real author is parsed)
        if author_name:
            line_y = current_y + 10
            draw.line([W/2 - 120, line_y, W/2 + 120, line_y], fill=(255, 255, 255, 100), width=3)
            
            tagline_font = ImageFont.truetype(font_path, size=28, layout_engine=ImageFont.Layout.RAQM)
            # Render Author name in rich gold accent (#FFAA33)
            draw.text((W / 2, line_y + 20), author_name, font=tagline_font, fill=(255, 170, 51, 220), anchor="ma")

        # 10. Apply Custom Logo Watermark in Corner
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

        # 11. Save the final high-definition poster
        output_dir = f"images/{category}"
        os.makedirs(output_dir, exist_ok=True)
        
        # FIXED: Naming is now hashed based on content. No cached files will collide!
        unique_hash = get_text_hash(quote_body)
        output_path = f"{output_dir}/quote_{date_str}_{unique_hash}.png"
        img.convert('RGB').save(output_path, "PNG")

    print(f"\nSUCCESS: Generated {len(quotes)} quote posters!")

if __name__ == "__main__":
    main()
