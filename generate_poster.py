import os
import csv
import random
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# Pre-filled directly from your Google Sheet ID
GOOGLE_SHEET_ID = "1rmyyD1lS3uAZ4c9WAkmTekDrrcx4X3jdvpJz8DWyhX0"

# Target ONLY the first tab ("New Quotes") using gid=0
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"

# Google Font URLs for your requested styles
FONT_URLS = {
    "Anek Kannada": "https://github.com/google/fonts/raw/main/ofl/anekkannada/AnekKannada%5Bwdth,wght%5D.ttf",
    "Hubballi": "https://github.com/google/fonts/raw/main/ofl/hubballi/Hubballi-Regular.ttf"
}

def wrap_text(text, font, max_width):
    """
    Splits a single long string into multiple lines based on font size 
    and maximum pixel width limits.
    """
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
        print("Connecting exclusively to the 'New Quotes' sheet...")
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
        else:
            print(f"Error: Google Sheets responded with status code {response.status_code}")
    except Exception as e:
        print(f"Failed to fetch Google Sheets: {e}")
    return quotes

def main():
    quotes = fetch_quotes_from_sheets()
    if not quotes:
        print("Error: No valid quotes loaded from your Google Sheet.")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    today_quotes = [q for q in quotes if q["date"] == today_str]

    if today_quotes:
        today_quote = random.choice(today_quotes)
        print(f"Found quote matching today's date ({today_str}).")
    else:
        print(f"No quotes scheduled specifically for today ({today_str}). Selecting a random fallback quote.")
        today_quote = random.choice(quotes)

    category = today_quote["category"]
    text = today_quote["text"]
    bg_prompt = today_quote["prompt"]

    # 1. Fetch free AI background from Pollinations.ai
    encoded_prompt = requests.utils.quote(bg_prompt)
    bg_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true"
    
    print(f"Requesting AI Image background for prompt: {bg_prompt}")
    bg_response = requests.get(bg_url, timeout=30)
    with open("temp_bg.jpg", "wb") as f:
        f.write(bg_response.content)

    # 2. Open image in Pillow
    img = Image.open("temp_bg.jpg")
    W, H = img.size

    # 3. Download and apply font style (Anek Kannada or Hubballi)
    font_name, font_download_url = random.choice(list(FONT_URLS.items()))
    print(f"Downloading and applying typography style: {font_name}")
    
    font_response = requests.get(font_download_url, timeout=15)
    with open("selected_font.ttf", "wb") as f:
        f.write(font_response.content)
    
    font = ImageFont.truetype("selected_font.ttf", size=42)

    # 4. Perform Word Wrapping
    max_text_width = 750  
    wrapped_lines = wrap_text(text, font, max_text_width)

    # 5. Calculate Dynamic Card Height
    line_spacing = 15
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

    # Define card boundary rectangles
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

    # 6. Draw the Wrapped Text Lines (Centered precisely)
    current_y = top + padding_y
    for i, line in enumerate(wrapped_lines):
        # Draw horizontally centered (Pillow automatically uses HarfBuzz if libraqm is installed on the system)
        draw.text((W / 2, current_y), line, font=font, fill="white", anchor="ma")
        current_y += line_heights[i] + line_spacing

    # 7. Draw the Kannada Watermark "ಸಾಹಿತ್ಯ ಕೀಬೋರ್ಡ್‌" in the bottom-right corner
    watermark_text = "ಸಾಹಿತ್ಯ ಕೀಬೋರ್ಡ್‌"
    watermark_font = ImageFont.truetype("selected_font.ttf", size=24)
    draw.text((W - 40, H - 40), watermark_text, font=watermark_font, fill=(255, 255, 255, 180), anchor="rd")

    # 8. Save the final high-definition PNG to the correct category folder
    output_dir = f"images/{category}"
    os.makedirs(output_dir, exist_ok=True)
    
    file_date_str = today_str.replace("-", "")
    output_path = f"{output_dir}/quote_{file_date_str}.png"
    img.convert('RGB').save(output_path, "PNG")
    
    print("-" * 50)
    print(f"SUCCESS: Generated HD Poster with '{font_name}' font.")
    print(f"Category: {category}")
    print(f"Output File: {output_path}")
    print("-" * 50)

if __name__ == "__main__":
    main()
