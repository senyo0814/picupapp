import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from picupapp.utils import add_watermark

# Use a test image in the same directory
input_file = "your_test_image.jpg"
output_file = "test_output.jpg"

with open(input_file, "rb") as f:
    result = add_watermark(f, "testuser")

    with open(output_file, "wb") as out:
        out.write(result.read())

print(f"✅ Watermarked image saved as {output_file}")
