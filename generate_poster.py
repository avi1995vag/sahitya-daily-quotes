import os
import csv
import random
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# SAFEGUARD: Forces Pygame to run headlessly (no physical monitor or screen needed on the server)
os.environ["SDL_VIDEODRIVER"] = "dummy"

# Initialize Pygame's hardware-accelerated Font System
import pygame
pygame.font.init()

# Pre-filled directly from your Google Sheet ID
GOOGLE_SHEET_ID = "1rmyyD1lS3uAZ4c9WAkmTekDrrcx4X3jdvpJz8DWyhX0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"
# (The rest of your generate_poster.py code remains exactly the same...)

FONT_URLS = {
    "Anek Kannada": "https://github.com/google/fonts/raw/main/ofl/anekkannada/AnekKannada%5Bwdth,wght%5D.ttf",
    "Hubballi": "https://github.com/google/fonts/raw/main/ofl/hubballi/Hubballi-Regular.ttf"
}

# A curated selection of professional, high-end gradients
GRADIENTS = [
    ((255, 120, 150), (120, 80, 220)), # Pink to Deep Cosmic Purple
    ((255, 160, 140), (255, 210, 140)), # Soft Peach Sunset
    ((18, 120, 150), (100, 200, 220)),  # Soft Turquoise Sea
    ((33, 147, 176), (109, 213, 237)),  # Ocean Breeze Blue
    ((241, 39, 17), (245, 175, 25)),    # Warm Sunrise Glow
    ((11, 72, 107), (245, 194, 66)),    # Deep Midnight Blue to Warm Gold
    ((118, 184, 111), (118, 174, 93))   # Fresh Pastel Meadow Green
]

def generate_gradient_background(W, H):
    """
    Procedurally generates a smooth, modern linear gradient inside Python.
    Eliminates busy backgrounds and loads instantly.
    """
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

    print(f"\nSUCCESS: Loaded {len(quotes)} quotes from Google Sheets.")
    print(f"Generating high-definition posters for ALL rows...\n")

    # Download active font files locally
    font_files = {}
    for name, url in FONT_URLS.items():
        filename = f"{name.replace(' ', '_').lower()}.ttf"
        if not os.path.exists(filename):
            print(f"Downloading font: {name}")
            response = requests.get(url, timeout=15)
            with open(filename, "wb") as f:
                f.write(response.content)
        font_files[name] = filename

    # LOOP THROUGH EVERY ROW IN THE SHEET
    for idx, q in enumerate(quotes):
        category = q["category"]
        text = q["text"]
        date_str = q["date"].replace("-", "")

        print(f"[{idx + 1}/{len(quotes)}] Generating poster for: '{text[:25]}...'")

        # 1. Generate full-screen gradient background
        W, H = 1080, 1080
        img = generate_gradient_background(W, H)

        # 2. Select a font style
        font_name = random.choice(list(FONT_URLS.keys()))
        font_path = font_files[font_name]

        # 3. DYNAMICALLY SCALE FONT SIZE (Very big text for shorter quotes)
        text_length = len(text)
        if text_length < 35:
            font_size = 72
        elif text_length < 65:
            font_size = 56
        else:
            font_size = 46

        pg_font = pygame.font.Font(font_path, font_size)

        # 4. Perform Word Wrapping
        max_text_width = 900 # Wide margins for full-screen text focus
        wrapped_lines = wrap_text_pygame(text, pg_font, max_text_width)

        # 5. Render lines into transparent image layers with 3D shadows
        line_spacing = 18
        total_text_height = 0
        line_layers = []

        for line in wrapped_lines:
            # Render perfectly shaped text (White foreground)
            text_surface = pg_font.render(line, True, (255, 255, 255))
            surface_bytes = pygame.image.tobytes(text_surface, "RGBA")
            fg_img = Image.frombytes("RGBA", text_surface.get_size(), surface_bytes)

            # Render matching shadow text (Semi-transparent black)
            shadow_surface = pg_font.render(line, True, (0, 0, 0))
            shadow_bytes = pygame.image.tobytes(shadow_surface, "RGBA")
            bg_img = Image.frombytes("RGBA", shadow_surface.get_size(), shadow_bytes)

            line_layers.append((fg_img, bg_img))
            total_text_height += fg_img.height

        total_text_height += line_spacing * (len(wrapped_lines) - 1)

        # 6. Paste text layers centered vertically onto the gradient canvas
        current_y = (H - total_text_height) // 2
        for fg_img, bg_img in line_layers:
            line_x = (W - fg_img.width) // 2
            
            # Draw the 3D drop shadow layer first (shifted by 5 pixels)
            shadow_offset = 5
            shadow_alpha = Image.new("L", bg_img.size, 160) # 60% opacity shadow
            img.paste(bg_img, (line_x + shadow_offset, int(current_y) + shadow_offset), shadow_alpha)
            
            # Draw the clean white foreground text layer directly on top
            img.paste(fg_img, (line_x, int(current_y)), fg_img)
            current_y += fg_img.height + line_spacing

        # 7. Render and draw the watermark "ಸಾಹಿತ್ಯ ಕೀಬೋರ್ಡ್‌"
        watermark_font = pygame.font.Font(font_path, 26)
        
        # Render white watermark and shadow layer
        wm_fg_surface = watermark_font.render("ಸಾಹಿತ್ಯ ಕೀಬೋರ್ಡ್‌", True, (255, 255, 255))
        wm_bg_surface = watermark_font.render("ಸಾಹಿತ್ಯ ಕೀಬೋರ್ಡ್‌", True, (0, 0, 0))
        
        wm_fg_bytes = pygame.image.tobytes(wm_fg_surface, "RGBA")
        wm_bg_bytes = pygame.image.tobytes(wm_bg_surface, "RGBA")
        
        wm_fg_img = Image.frombytes("RGBA", wm_fg_surface.get_size(), wm_fg_bytes)
        wm_bg_img = Image.frombytes("RGBA", wm_bg_surface.get_size(), wm_bg_bytes)

        wm_x = W - wm_fg_img.width - 50
        wm_y = H - wm_fg_img.height - 50

        # Draw watermark shadow
        wm_shadow_alpha = Image.new("L", wm_bg_img.size, 140)
        img.paste(wm_bg_img, (wm_x + 3, wm_y + 3), wm_shadow_alpha)
        # Draw watermark foreground
        img.paste(wm_fg_img, (wm_x, wm_y), wm_fg_img)

        # 8. Save the high-definition poster file
        output_dir = f"images/{category}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save filename as quote_date_index.png to support multiple files per day
        output_path = f"{output_dir}/quote_{date_str}_{idx + 1}.png"
        img.convert('RGB').save(output_path, "PNG")

    print(f"\nSUCCESS: Generated {len(quotes)} high-definition quote posters on gradient backgrounds!")

if __name__ == "__main__":
    main()
