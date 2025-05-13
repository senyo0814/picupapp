from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
import os

def add_watermark(image_file, username):
    with Image.open(image_file) as img:
        base = ImageOps.exif_transpose(img).convert("RGBA")  # ⬅️ fix orientation

        width, height = base.size
        watermark = Image.new("RGBA", base.size, (0, 0, 0, 0))

        # ⬇️ Draw text: "Posted by username"
        font_size = max(14, int(height * 0.025))
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        draw = ImageDraw.Draw(watermark)
        user_text = f"Posted by {username}"
        x = 10
        y = height - font_size - 10
        draw.text((x + 1, y + 1), user_text, font=font, fill=(0, 0, 0, 160))  # shadow
        draw.text((x, y), user_text, font=font, fill=(255, 255, 255, 200))   # main

        # ⬇️ Add logo on right
        logo_path = os.path.join(settings.BASE_DIR, 'picupapp/static/img/logoside.png')
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_height = max(20, int(height * 0.04))
            aspect_ratio = logo.width / logo.height
            logo = logo.resize((int(logo_height * aspect_ratio), logo_height))

            logo_pos = (width - logo.width - 10, height - logo.height - 10)
            watermark.paste(logo, logo_pos, logo)
        except Exception as e:
            print(f"[WARN] Could not load logo: {e}")

        # ⬇️ Combine layers
        combined = Image.alpha_composite(base, watermark).convert("RGB")
        buffer = BytesIO()
        combined.save(buffer, format="JPEG")
        buffer.seek(0)

        print(f"[INFO] ✅ Watermark added for {username}")
        return ContentFile(buffer.getvalue(), name=getattr(image_file, 'name', 'watermarked.jpg'))
