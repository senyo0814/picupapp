from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
from django.core.files.base import ContentFile
from django.contrib.staticfiles import finders

def add_watermark(image_file, username):
    try:
        with Image.open(image_file) as raw:
            base = ImageOps.exif_transpose(raw).convert("RGBA")

        width, height = base.size
        watermark = Image.new("RGBA", base.size)

        # ✅ Font scaling
        font_size = max(18, int(height * 0.105))  # ~10.5% of image height
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        user_text = f"Posted by {username}"
        x = 20
        y = height - font_size - 20

        # ✅ Draw text with shadow (outline effect)
        text_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)

        shadow_offsets = [(1, 1), (-1, -1), (1, -1), (-1, 1)]
        for dx, dy in shadow_offsets:
            text_draw.text((x + dx, y + dy), user_text, font=font, fill=(0, 0, 0, 160))

        text_draw.text((x, y), user_text, font=font, fill=(255, 255, 255, 230))
        watermark = Image.alpha_composite(watermark, text_layer)

        # ✅ Add logo
        logo_path = finders.find("img/logoside.png")
        if logo_path:
            try:
                logo = Image.open(logo_path).convert("RGBA")
                logo_height = max(20, int(height * 0.04))
                aspect_ratio = logo.width / logo.height
                logo = logo.resize((int(logo_height * aspect_ratio), logo_height))
                logo_pos = (width - logo.width - 20, height - logo.height - 20)
                watermark.paste(logo, logo_pos, logo)
            except Exception as e:
                print(f"[WARN] Failed to paste logo: {e}")
        else:
            print("[WARN] Logo not found in static files.")

        # ✅ Final image
        combined = Image.alpha_composite(base, watermark).convert("RGB")
        buffer = BytesIO()
        combined.save(buffer, format="JPEG")
        buffer.seek(0)

        print(f"[INFO] Watermark applied for {username} on {getattr(image_file, 'name', 'unnamed')}")
        return ContentFile(buffer.getvalue(), name=getattr(image_file, 'name', 'watermarked.jpg'))

    except Exception as e:
        print(f"[ERROR] Watermarking failed: {e}")
        return image_file  # fallback to original
