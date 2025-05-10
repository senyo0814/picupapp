from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from .models import PhotoUpload
from django.conf import settings
import logging
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime
import os
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# --- Auth Views ---

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('picupapp:landing')
        return render(request, 'picupapp/login.html', {'error': 'Invalid credentials'})
    return render(request, 'picupapp/login.html')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        if User.objects.filter(username=username).exists():
            return render(request, 'picupapp/register.html', {'error': 'Username already taken'})
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        return redirect('picupapp:landing')
    return render(request, 'picupapp/register.html')

def extract_gps_and_datetime(file):
    try:
        file.seek(0)  # Ensure file pointer is at start
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

        print(">>> Image filename:", getattr(file, 'name', 'Unknown'))
        print(">>> GPSLatitude Raw:", gps_info.get('GPSLatitude'))
        print(">>> GPSLatitudeRef:", gps_info.get('GPSLatitudeRef'))
        print(">>> GPSLongitude Raw:", gps_info.get('GPSLongitude'))
        print(">>> GPSLongitudeRef:", gps_info.get('GPSLongitudeRef'))

        def get_gps_decimal(coord, ref):
            try:
                def frac(val):
                    return float(val[0]) / float(val[1]) if isinstance(val, tuple) else float(val)

                d = frac(coord[0])
                m = frac(coord[1])
                s = frac(coord[2])

                decimal = d + (m / 60.0) + (s / 3600.0)
                if ref and str(ref).upper() in ['S', 'W']:
                    decimal *= -1
                return round(decimal, 6)
            except Exception as e:
                logger.warning(f"Error converting GPS: {e}")
                return None

        lat = lon = None
        if 'GPSLatitude' in gps_info and 'GPSLatitudeRef' in gps_info:
            lat = get_gps_decimal(gps_info['GPSLatitude'], gps_info['GPSLatitudeRef'])

        if 'GPSLongitude' in gps_info and 'GPSLongitudeRef' in gps_info:
            lon = get_gps_decimal(gps_info['GPSLongitude'], gps_info['GPSLongitudeRef'])

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

# --- Landing View ---

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import PhotoUpload
from .exif_utils import extract_gps_and_datetime
from datetime import datetime
import io
import logging

logger = logging.getLogger(__name__)

@login_required
def landing(request):
    try:
        all_photos = PhotoUpload.objects.order_by('-uploaded_at')
        valid_photos = [photo for photo in all_photos if photo.image]

        if request.method == 'POST':
            for idx, f in enumerate(request.FILES.getlist('images')):
                copy = io.BytesIO(f.read())
                f.seek(0)

                lat = request.POST.get(f'latitude_{idx}')
                lon = request.POST.get(f'longitude_{idx}')
                taken_str = request.POST.get(f'photo_taken_{idx}')

                try:
                    taken_date = datetime.strptime(taken_str, "%Y:%m:%d %H:%M:%S") if taken_str else None
                except ValueError:
                    taken_date = None

                if not lat or not lon:
                    lat_exif, lon_exif, taken_exif = extract_gps_and_datetime(copy)
                    lat = lat or lat_exif
                    lon = lon or lon_exif
                    taken_date = taken_date or taken_exif

                try:
                    lat = round(float(lat), 6) if lat else None
                    lon = round(float(lon), 6) if lon else None
                except Exception as conv_e:
                    logger.warning(f"Latitude/Longitude conversion error: {conv_e}")
                    lat = lon = None

                comment = request.POST.get(f'comment_{idx}', '')

                from django.core.files.base import ContentFile

                # Instead of assigning `image=f` directly
                photo = PhotoUpload(
                    uploaded_by=request.user,
                    comment=comment,
                    latitude=lat,
                    longitude=lon,
                    photo_taken_date=taken_date
                )

                # Explicitly save the file to trigger `upload_to=user_directory_path`
                photo.image.save(f.name, ContentFile(f.read()), save=False)

                photo.save()

            return redirect('picupapp:landing')

        return render(request, 'picupapp/landing.html', {
            'photos': valid_photos,
            'username': request.user.username
        })

    except Exception as e:
        logger.exception("Landing view error:")
        return HttpResponse("Something went wrong.", status=500)

# --- Delete Photo ---

@login_required
def delete_photo(request, photo_id):
    photo = get_object_or_404(PhotoUpload, id=photo_id, uploaded_by=request.user)
    photo.image.delete()
    photo.delete()
    return redirect('picupapp:landing')

# --- Logout ---

def logout_view(request):
    logout(request)
    return redirect('picupapp:login')

# --- Map View ---

@login_required
def map_pics_view(request):
    user_photos = PhotoUpload.objects.filter(uploaded_by=request.user).exclude(latitude=None).exclude(longitude=None)
    other_photos = PhotoUpload.objects.exclude(uploaded_by=request.user).exclude(latitude=None).exclude(longitude=None)

    def serialize(photos):
        return [
            {
                "latitude": p.latitude,
                "longitude": p.longitude,
                "image_url": settings.MEDIA_URL + str(p.image),
                "comment": p.comment or "",
                "taken": p.photo_taken_date.strftime("%Y-%m-%d %H:%M") if p.photo_taken_date else "Unknown",
                "user": p.uploaded_by.username
            }
            for p in photos
        ]

    return render(request, 'picupapp/mappics.html', {
        'user_photos': serialize(user_photos),
        'other_photos': serialize(other_photos),
        'username': request.user.username
    })

def check_media_access(request):
    path = os.path.join(settings.MEDIA_ROOT, 'uploads')
    test_file = os.path.join(path, 'test.txt')
    result = {
        "media_root": settings.MEDIA_ROOT,
        "uploads_dir": path,
        "exists": os.path.exists(path),
        "writable": os.access(path, os.W_OK),
        "write_success": False,
        "error": None,
    }
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        result["write_success"] = True
        os.remove(test_file)
    except Exception as e:
        result["error"] = str(e)

    return JsonResponse(result)

# --- Metadata List View ---

@login_required
def metadata_table_view(request):
    photos = PhotoUpload.objects.order_by('-uploaded_at')
    return render(request, 'picupapp/metadata_table.html', {
        'photos': photos
    })

@csrf_exempt
@login_required
def update_comment(request):
    if request.method == 'POST':
        photo_id = request.POST.get('photo_id')
        new_comment = request.POST.get('comment')
        try:
            photo = PhotoUpload.objects.get(id=photo_id, uploaded_by=request.user)
            photo.comment = new_comment
            photo.save()
            return redirect('picupapp:landing')  # or return JsonResponse if using AJAX
        except PhotoUpload.DoesNotExist:
            return HttpResponse("Unauthorized", status=403)

@login_required
def photo_map_view(request):
    # Filter users who have uploaded or shared public photos
    shared_users = User.objects.filter(
        photoupload__isnull=False
    ).distinct()

    # Include request.user in case of personal view
    username = request.user.username if request.user.is_authenticated else 'Anonymous'

    user_photos = PhotoUpload.objects.filter(uploaded_by=request.user)
    other_photos = PhotoUpload.objects.exclude(uploaded_by=request.user).filter(is_public=True)

    return render(request, 'picupapp/mappics.html', {
        'username': username,
        'shared_users': shared_users,
        'user_photos': serialize_photos(user_photos),
        'other_photos': serialize_photos(other_photos),
    })

def serialize_photos(qs):
    return [
        {
            "id": p.id,
            "image_url": p.image.url,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "comment": p.comment,
            "user": p.uploaded_by.username,
            "taken": p.photo_taken_date.strftime("%Y-%m-%d %H:%M") if p.photo_taken_date else '',
        } for p in qs
    ]
