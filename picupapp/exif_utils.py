from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def extract_gps_and_datetime(file):
    try:
            img = Image.open(file)
            exif_data = img._getexif()
            gps_info = {}
            datetime_taken = None

            if not exif_data:
                print(">>> No EXIF data found.")
                return None, None, None

            for tag, value in exif_data.items():
                decoded = TAGS.get(tag)
                if decoded == "DateTimeOriginal":
                    datetime_taken = value
                elif decoded == "GPSInfo":
                    for t in value:
                        sub_decoded = GPSTAGS.get(t)
                        gps_info[sub_decoded] = value[t]

            print(">>> Raw GPS Info:", gps_info)
            print(">>> Raw DateTimeOriginal:", datetime_taken)

            def convert_to_degrees(value):
                try:
                    d = float(value[0][0]) / float(value[0][1])
                    m = float(value[1][0]) / float(value[1][1])
                    s = float(value[2][0]) / float(value[2][1])
                    return d + (m / 60.0) + (s / 3600.0)
                except Exception as e:
                    logger.warning(f"Error converting to degrees: {e}")
                    return None

            lat = lon = None
            if 'GPSLatitude' in gps_info and 'GPSLatitudeRef' in gps_info:
                lat = convert_to_degrees(gps_info['GPSLatitude'])
                if lat is not None and gps_info['GPSLatitudeRef'] in ['S', 's']:
                    lat = -lat

            if 'GPSLongitude' in gps_info and 'GPSLongitudeRef' in gps_info:
                lon = convert_to_degrees(gps_info['GPSLongitude'])
                if lon is not None and gps_info['GPSLongitudeRef'] in ['W', 'w']:
                    lon = -lon

            print(">>> Parsed Latitude:", lat)
            print(">>> Parsed Longitude:", lon)

            if datetime_taken:
                try:
                    datetime_taken = datetime.strptime(datetime_taken, "%Y:%m:%d %H:%M:%S")
                    print(">>> Parsed Date Taken:", datetime_taken)
                except ValueError as ve:
                    logger.warning(f"Invalid datetime format in EXIF: {ve}")
                    datetime_taken = None

            return lat, lon, datetime_taken

        except Exception as e:
            print(">>> EXIF parse failed:", e)
            logger.warning(f"EXIF parse failed: {e}")
            return None, None, None
