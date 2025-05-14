from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
from django.core.files.base import ContentFile
from django.contrib.staticfiles import finders

def add_watermark(image_file, username):
    try:
        with Image.open(image_file) as raw:
            base = ImageOps.exif_transpose(raw).convert("RGBA")

        # ✅ Resize image for mobile viewing (max 1280px)
        max_size = (1280, 1280)
        base.thumbnail(max_size, Image.LANCZOS)

        width, height = base.size
        watermark = Image.new("RGBA", base.size)

        # ✅ Font scaling
        font_size = max(18, int(height * 0.07))

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()

        user_text = f"Posted by {username}"
        x = 20
        logo_height = max(20, int(height * 0.04))
        y = height - logo_height - 5

        # ✅ Draw watermark text without shadow (with white background)
        text_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_layer)

        text_width = text_draw.textlength(user_text, font)
        text_draw.rectangle(
            [x - 5, y - 5, x + text_width + 5, y + font_size + 5],
            fill=(255, 255, 255, 200)
        )
        text_draw.text((x, y), user_text, font=font, fill=(0, 0, 0, 255))

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

        # ✅ Combine and compress to JPEG
        combined = Image.alpha_composite(base, watermark).convert("RGB")
        buffer = BytesIO()
        combined.save(buffer, format="JPEG", quality=70, optimize=True)  # Reduced quality for smaller size
        buffer.seek(0)

        print(f"[INFO] Watermark and compression applied for {username} on {getattr(image_file, 'name', 'unnamed')}")
        return ContentFile(buffer.getvalue(), name=getattr(image_file, 'name', 'watermarked.jpg'))

    except Exception as e:
        print(f"[ERROR] Watermarking failed: {e}")
        return image_file  # fallback
