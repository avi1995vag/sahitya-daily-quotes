import os
import csv
import random
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

# Pre-filled directly from your Google Sheet screenshot
GOOGLE_SHEET_ID = "1rmyyD1lS3uAZ4c9WAkmTekDrrcx4X3jdvpJz8DWyhX0"

# Target ONLY the "New Quotes" sheet tab by name, ignoring "Old Quotes"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/gviz/tq?tqx=out:csv&sheet=New%20Quotes"

# Google Font URLs for your requested styles
FONT_URLS = {
    "Anek Kannada": "https://github.com/google/fonts/raw/main/ofl/anekkannada/AnekKannada%5Bwdth,wght%5D.ttf",
    "Hubballi": "https://github.com/google/fonts/raw/main/ofl/hubballi/Hubballi-Regular.ttf"
}

def fetch_quotes_from_sheets():
    quotes = []
    try:
        print("Connecting exclusively to the 'New Quotes' sheet...")
        response = requests.get(CSV_URL, timeout=15)
        if response.status_code == 200:
            lines = response.content.decode('utf-8').splitlines()
            reader = csv.DictReader(lines)
            for row in reader:
                # Read and validate populated columns
                if row.get("date") and row.get("category") and row.get("text") and row.get("prompt"):
                    quotes.append({
                        "date": row["date"].strip().replace('"', ''),
                        "category": row["category"].strip().lower().replace('"', ''),
                        "text": row["text"].strip().replace('"', ''),
                        "prompt": row["prompt"].strip().replace('"', '')
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

    # Check for quotes scheduled for today (YYYY-MM-DD)
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_quotes = [q for q in quotes if q["date"] == today_str]

    if today_quotes:
        # Select one random quote from today's batch to generate
        today_quote = random.choice(today_quotes)
        print(f"Found quote matching today's date ({today_str}).")
    else:
        # Fallback: If no quote is scheduled for today, select a random row so the test run succeeds
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

    # 3. Download and apply font style (Randomly chooses between Anek Kannada and Hubballi)
    font_name, font_download_url = random.choice(list(FONT_URLS.items()))
    print(f"Downloading and applying typography style: {font_name}")
    
    font_response = requests.get(font_download_url, timeout=15)
    with open("selected_font.ttf", "wb") as f:
        f.write(font_response.content)
    
    font = ImageFont.truetype("selected_font.ttf", size=44)

    # 4. Draw rounded dark background card for perfect text readability
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    card_w, card_h = 800, 200
    left = (W - card_w) / 2
    top = (H - card_h) / 2
    right = left + card_w
    bottom = top + card_h
    overlay_draw.rounded_rectangle([left, top, right, bottom], radius=20, fill=(0, 0, 0, 140))
    
    img = Image.alpha_composite(img.convert('RGBA'), overlay)
    draw = ImageDraw.Draw(img)

    # 5. Draw the Kannada Text centered precisely inside the card
    draw.text((W / 2, H / 2), text, font=font, fill="white", anchor="mm")

    # 6. Draw the Kannada Watermark "ಸಾಹಿತ್ಯ ಕೀಬೋರ್ಡ್‌" in the bottom-right corner
    watermark_text = "ಸಾಹಿತ್ಯ ಕೀಬೋರ್ಡ್‌"
    watermark_font = ImageFont.truetype("selected_font.ttf", size=24)
    draw.text((W - 40, H - 40), watermark_text, font=watermark_font, fill=(255, 255, 255, 180), anchor="rd")

    # 7. Save the final high-definition PNG to the correct category folder
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
