from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.core.files.base import ContentFile
import os
from django.conf import settings

def add_watermark(image_file, username):
    with Image.open(image_file).convert("RGBA") as base:
        width, height = base.size
        watermark = Image.new("RGBA", base.size)
        
        # 🧠 Scale font size based on image height
        font_size = max(14, int(height * 0.025))  # ~2.5% of image height
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()
        
        user_text = f"Posted by {username}"
        x = 10
        y = height - font_size - 10  # pad 10px from bottom

        # 🧊 Transparent text layer
        text_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
        text_draw = ImageDraw.Draw(text_layer)
        text_draw.text((x + 1, y + 1), user_text, font=font, fill=(0, 0, 0, 160))   # shadow
        text_draw.text((x, y), user_text, font=font, fill=(255, 255, 255, 200))     # main text
        watermark = Image.alpha_composite(watermark, text_layer)

        # ✅ Add scaled logo
        logo_path = os.path.join(settings.BASE_DIR, 'picupapp/static/img/logoside.png')
        print(f"[DEBUG] Looking for logo at: {logo_path}")

        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_target_height = max(20, int(height * 0.04))  # ~4% of image height
            aspect_ratio = logo.width / logo.height
            logo = logo.resize((int(logo_target_height * aspect_ratio), logo_target_height))

            logo_pos = (width - logo.width - 10, height - logo.height - 10)
            watermark.paste(logo, logo_pos, logo)  # respect alpha channel
            print(f"[INFO] Logo pasted at {logo_pos}, resized to {logo.size}")
        except Exception as e:
            print(f"[WARN] Could not load logo: {e}")

        # Final composite
        combined = Image.alpha_composite(base, watermark).convert("RGB")

        buffer = BytesIO()
        combined.save(buffer, format="JPEG")
        buffer.seek(0)

        print(f"[INFO] Watermark applied for {username} on image {image_file.name}")
        return ContentFile(buffer.getvalue(), name=image_file.name)
