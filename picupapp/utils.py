from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.core.files.base import ContentFile
import os
from django.conf import settings

def add_watermark(image_file, username):
    with Image.open(image_file).convert("RGBA") as base:
        width, height = base.size
        watermark = Image.new("RGBA", base.size)

        # 🔧 Scaled font
        font_size = max(14, int(height * 0.025))
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        user_text = f"Posted by {username}"
        x = 10
        y = height - font_size - 10

        # ✅ Transparent text layer for watermark text
        text_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)
        text_draw.text((x + 1, y + 1), user_text, font=font, fill=(0, 0, 0, 160))   # shadow
        text_draw.text((x, y), user_text, font=font, fill=(255, 255, 255, 200))     # main

        # Merge text into watermark layer
        watermark = Image.alpha_composite(watermark, text_layer)

        # ✅ Add scaled logo
        logo_path = os.path.join(settings.BASE_DIR, 'picupapp/static/img/logoside.png')
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_target_height = max(20, int(height * 0.04))
            aspect_ratio = logo.width / logo.height
            logo = logo.resize((int(logo_target_height * aspect_ratio), logo_target_height))

            logo_pos = (width - logo.width - 10, height - logo.height - 10)
            watermark.paste(logo, logo_pos, logo)
        except Exception as e:
            print(f"[WARN] Could not load logo: {e}")

        # ✅ Merge watermark and base
        combined = Image.alpha_composite(base, watermark).convert("RGB")

        buffer = BytesIO()
        combined.save(buffer, format="JPEG")
        buffer.seek(0)

        print(f"[INFO] Watermark applied for {username} on image {getattr(image_file, 'name', 'unnamed')}")
        return ContentFile(buffer.getvalue(), name=getattr(image_file, 'name', 'watermarked.jpg'))
