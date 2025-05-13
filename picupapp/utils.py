from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from django.core.files.base import ContentFile
import os
from django.conf import settings

def add_watermark(image_file, username):
    with Image.open(image_file).convert("RGBA") as base:
        watermark = Image.new("RGBA", base.size)
        draw = ImageDraw.Draw(watermark)

        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except IOError:
            font = ImageFont.load_default()

        width, height = base.size

        # ✅ Draw "Posted by username" at lower-left
        user_text = f"Posted by {username}"
        user_size = draw.textsize(user_text, font=font)
        user_pos = (10, height - user_size[1] - 10)
        draw.text((user_pos[0] + 1, user_pos[1] + 1), user_text, font=font, fill="black")
        draw.text(user_pos, user_text, font=font, fill="white")

        # ✅ Paste PicUp logo at lower-right
        logo_path = os.path.join(settings.BASE_DIR, 'picupapp/static/img/logoside.png')
        print(f"[DEBUG] Looking for logo at: {logo_path}")

        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_height = 25
            aspect_ratio = logo.width / logo.height
            logo = logo.resize((int(logo_height * aspect_ratio), logo_height))

            logo_pos = (width - logo.width - 10, height - logo.height - 10)
            watermark.paste(logo, logo_pos, logo)  # Respect transparency
            print("[DEBUG] Logo successfully pasted at:", logo_pos)
        except Exception as e:
            print(f"[WARN] Could not load logo: {e}")

        # ✅ Merge watermark and return file
        combined = Image.alpha_composite(base, watermark).convert("RGB")

        buffer = BytesIO()
        combined.save(buffer, format="JPEG")
        buffer.seek(0)  # ✅ This is required

        print(f"[DEBUG] Watermark added and image ready for saving: {image_file.name}")
        return ContentFile(buffer.getvalue(), name=image_file.name)
