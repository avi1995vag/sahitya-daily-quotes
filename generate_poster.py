import os
import csv
import random
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# TODO: Replace with your actual Google Sheet ID
GOOGLE_SHEET_ID = "1rmyyD1lS3uAZ4c9WAkmTekDrrcx4X3jdvpJz8DWyhX0"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"

# TODO: Add your free Pexels API Key here (or leave empty to use premium gradients)
PEXELS_API_KEY = "We2njvb6rYtUvXMH2fuU6IjHgSjOlpsUVFRCSibahkalqXN3m7v7eriF"

# Google Font URLs for your requested styles
FONT_URLS = {
    "Anek Kannada": "https://github.com/google/fonts/raw/main/ofl/anekkannada/AnekKannada%5Bwdth,wght%5D.ttf",
    "Hubballi": "https://github.com/google/fonts/raw/main/ofl/hubballi/Hubballi-Regular.ttf"
}

# A curated selection of modern, soft gradients
GRADIENTS = [
    ((255, 120, 150), (120, 80, 220)), 
    ((255, 160, 140), (255, 210, 140)), 
    ((18, 120, 150), (100, 200, 220)),  
    ((33, 147, 176), (109, 213, 237)),  
    ((241, 39, 17), (245, 175, 25)),    
    ((11, 72, 107), (245, 194, 66)),    
    ((118, 184, 111), (118, 174, 93))   
]

def generate_gradient_background(W, H):
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
    """
    Queries Pexels Stock Photo API using your custom prompt and downloads the best matching background.
    """
    if not PEXELS_API_KEY or PEXELS_API_KEY == "YOUR_PEXELS_API_KEY_HERE":
        return None
        
    headers = {"Authorization": PEXELS_API_KEY}
    url = f"https://api.pexels.com/v1/search?query={requests.utils.quote(prompt)}&per_page=1&orientation=square"
    
    try:
        response = requests.get(apiUrl, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            photos = data.get("photos", [])
            if photos:
                # Use large or original image URL
                img_url = photos[0]["src"].get("large2x") or photos[0]["src"].get("original")
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

    print(f"\nSUCCESS: Loaded {len(quotes)} quotes from Google Sheets.")
    print("Generating high-definition posters...\n")

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

    W, H = 1080, 1080

    for idx, q in enumerate(quotes):
        category = q["category"]
        text = q["text"]
        bg_prompt = q["prompt"]
        date_str = q["date"].replace("-", "")

        print(f"[{idx + 1}/{len(quotes)}] Generating poster for: '{text[:25]}...'")

        # 1. Fetch Background (Tries Pexels / Pollinations, falls back to Gradient if not configured)
        img = None
        if GOOGLE_SHEET_ID != "1A2B3C_YOUR_SHEET_ID_HERE":
            img = generate_gradient_background(W, H) # Default clean gradient
        else:
            # Fallback to gradient if image fails
            img = generate_gradient_background(W, H)

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
        max_text_width = 900 
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
        padding_y = 45
        card_w = 850
        card_h = total_text_height + (padding_y * 2)

        left = (W - card_w) / 2
        top = (H - card_h) / 2
        right = left + card_w
        bottom = top + card_h

        # Draw rounded transparent card
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle([left, top, right, bottom], radius=20, fill=(0, 0, 0, 140))
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        draw = ImageDraw.Draw(img)

        # 6. Draw the Wrapped Text Lines with subtle 3D Drop Shadows
        current_y = top + padding_y
        for i, line in enumerate(wrapped_lines):
            shadow_offset = 4
            # Draw shadow
            draw.text((W / 2 + shadow_offset, current_y + shadow_offset), line, font=font, fill=(0, 0, 0, 160), anchor="ma")
            # Draw crisp white text
            draw.text((W / 2, current_y), line, font=font, fill="white", anchor="ma")
            current_y += line_heights[i] + line_spacing

        # 7. DRAW CUSTOM LOGO WATERMARK (If logo.png is uploaded to repository root)
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            try:
                logo = Image.open(logo_path).convert("RGBA")
                # Scale logo to a professional height of 50px maintaining aspect ratio
                aspect_ratio = logo.width / float(logo.height)
                logo_h = 50
                logo_w = int(logo_h * aspect_ratio)
                logo = logo.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
                
                # Position logo in bottom-right corner with 50px margins
                logo_x = W - logo.width - 50
                logo_y = H - logo.height - 50
                img.paste(logo, (logo_x, logo_y), logo)
                print("Applied your custom logo watermark.")
            except Exception as e:
                print(f"Failed to apply logo watermark: {e}")
        else:
            # Fallback to beautifully rendered text watermark
            watermark_text = "ಸಾಹಿತ್ಯ ಕೀಬೋರ್ಡ್‌"
            watermark_font = ImageFont.truetype(font_path, size=24, layout_engine=ImageFont.Layout.RAQM)
            draw.text((W - 50, H - 50), watermark_text, font=watermark_font, fill=(255, 255, 255, 180), anchor="rd")

        # 8. Save the final high-definition poster
        output_dir = f"images/{category}"
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = f"{output_dir}/quote_{date_str}_{idx + 1}.png"
        img.convert('RGB').save(output_path, "PNG")

    print(f"\nSUCCESS: Generated {len(quotes)} high-definition quote posters!")

if __name__ == "__main__":
    main()
