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
import io
from django.core.files.base import ContentFile
from django.db.models import Q

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
        file.seek(0)
        img = Image.open(file)
        exif_data = img._getexif()
        gps_info = {}
        datetime_taken = None

        if not exif_data:
            logger.info("No EXIF data found.")
            return None, None, None

        for tag, value in exif_data.items():
            decoded = TAGS.get(tag)
            if decoded == "DateTimeOriginal":
                datetime_taken = value
            elif decoded == "GPSInfo":
                for t in value:
                    sub_decoded = GPSTAGS.get(t)
                    gps_info[sub_decoded] = value[t]

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

        if datetime_taken:
            try:
                datetime_taken = datetime.strptime(datetime_taken, "%Y:%m:%d %H:%M:%S")
            except ValueError as ve:
                logger.warning(f"Invalid datetime format in EXIF: {ve}")
                datetime_taken = None

        return lat, lon, datetime_taken

    except Exception as e:
        logger.warning(f"EXIF parse failed: {e}")
        return None, None, None

# --- Landing View ---

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
                visibility = request.POST.get('visibility')

                photo = PhotoUpload(
                    uploaded_by=request.user,
                    comment=comment,
                    latitude=lat,
                    longitude=lon,
                    photo_taken_date=taken_date,
                    is_public=(visibility == 'public')
                )
                photo.image.save(f.name, ContentFile(f.read()), save=False)
                photo.save()

                if visibility == 'public':
                    shared_ids = request.POST.getlist('shared_with')
                    if shared_ids:
                        users_to_share = User.objects.filter(id__in=shared_ids)
                        photo.shared_with.set(users_to_share)

            return redirect('picupapp:landing')

        return render(request, 'picupapp/landing.html', {
            'photos': valid_photos,
            'username': request.user.username,
            'all_users': User.objects.exclude(id=request.user.id)
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

# --- Map Views ---

@login_required
def photo_map_view(request):
    shared_users = User.objects.filter(
        photoupload__in=PhotoUpload.objects.filter(
            Q(is_public=True) | Q(shared_with=request.user)
        )
    ).distinct().order_by('username')

    username = request.user.username

    user_photos = PhotoUpload.objects.filter(uploaded_by=request.user).exclude(latitude=None).exclude(longitude=None)
    other_photos = PhotoUpload.objects.exclude(uploaded_by=request.user).filter(
        Q(is_public=True) | Q(shared_with=request.user)
    ).exclude(latitude=None).exclude(longitude=None)

    return render(request, 'picupapp/mappics.html', {
        'username': username,
        'shared_users': shared_users,
        'user_photos': serialize_photos(user_photos),
        'other_photos': serialize_photos(other_photos),
    })

@user_passes_test(lambda u: u.is_staff)
@login_required
def map_pics_view(request):
    user_photos = PhotoUpload.objects.filter(uploaded_by=request.user).exclude(latitude=None).exclude(longitude=None)
    other_photos = PhotoUpload.objects.exclude(uploaded_by=request.user).exclude(latitude=None).exclude(longitude=None)

    return render(request, 'picupapp/mappics.html', {
        'user_photos': serialize_photos(user_photos),
        'other_photos': serialize_photos(other_photos),
        'username': request.user.username
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

