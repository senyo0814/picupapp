import io
import os
import json
import logging
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe

from geopy.geocoders import Nominatim

from .models import PhotoUpload, PhotoGroup
from .exif_utils import extract_gps_and_datetime

from collections import Counter


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

# @login_required
def landing(request):
    try:
        from .models import PhotoGroup  # Ensure correct import
        user_groups = PhotoGroup.objects.filter(members=request.user)

        valid_photos = PhotoUpload.objects.filter(
            models.Q(uploaded_by=request.user) |
            models.Q(visibility='any') |
            models.Q(group__in=user_groups)
        ).distinct().select_related('uploaded_by').prefetch_related('shared_with').order_by('-uploaded_at')

        if request.method == 'POST':
            visibility = request.POST.get('visibility', 'private')
            shared_with = request.POST.getlist('shared_with')  # list of user IDs

            # Dynamically detect shared visibility
            if visibility == 'private' and shared_with:
                visibility = 'shared'

            selected_group_id = request.POST.get('photo_group') if visibility == 'group' else None

            if visibility == 'group' and not selected_group_id:
                return JsonResponse({"error": "Group ID is required for group visibility."}, status=400)

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

                original_file = f

                # ✅ Apply watermark
                from .utils import add_watermark
                watermarked = add_watermark(original_file, request.user.username)
                watermarked.seek(0)

                photo = PhotoUpload(
                    uploaded_by=request.user,
                    comment=comment,
                    latitude=lat,
                    longitude=lon,
                    photo_taken_date=taken_date,
                    visibility=visibility,
                )

                if selected_group_id:
                    photo.group_id = selected_group_id

                photo.image.save(f.name, watermarked, save=False)
                photo.save()

                if visibility == 'shared' and shared_with:
                    photo.shared_with.set(shared_with)

            return redirect('picupapp:landing')


        return render(request, 'picupapp/landing.html', {
            'photos': valid_photos,
            'username': request.user.username,
            'all_users': User.objects.exclude(id=request.user.id),
            'user_groups': user_groups
        })

    except Exception as e:
        logger.exception("Landing view error:")
        return HttpResponse("Something went wrong.", status=500)


# --- Delete Photo ---

# @login_required
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

# @login_required
def map_pics_view(request):
    user_photos = PhotoUpload.objects.filter(
        uploaded_by=request.user,
        latitude__isnull=False,
        longitude__isnull=False
    )

    # Only include public, shared-with-user, or shared-to-user's group photos
    user_groups = PhotoGroup.objects.filter(members=request.user)

    other_photos = PhotoUpload.objects.exclude(uploaded_by=request.user).filter(
        models.Q(visibility='any') |
        models.Q(shared_with=request.user) |
        models.Q(group__in=user_groups)
    ).filter(latitude__isnull=False, longitude__isnull=False).distinct()

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

# @login_required
def metadata_table_view(request):
    photos = PhotoUpload.objects.order_by('-uploaded_at')
    return render(request, 'picupapp/metadata_table.html', {
        'photos': photos
    })

@csrf_exempt
# @login_required
def update_comment(request):
    if request.method == 'POST':
        photo_id = request.POST.get('photo_id')
        comment = request.POST.get('comment', '')
        visibility = request.POST.get('visibility', 'private')
        group_id = request.POST.get('group_id') if visibility == 'group' else None
        shared_with_ids = request.POST.getlist('shared_with_modal') if visibility == 'shared' else []

        try:
            photo = PhotoUpload.objects.get(id=photo_id, uploaded_by=request.user)
            photo.comment = comment
            photo.visibility = visibility
            photo.group_id = group_id if group_id else None
            photo.save()

            if visibility == 'shared':
                photo.shared_with.set(shared_with_ids)
            else:
                photo.shared_with.clear()

            return redirect('picupapp:landing')
        except PhotoUpload.DoesNotExist:
            return HttpResponse("Unauthorized", status=403)

from django.contrib.auth import get_user_model
User = get_user_model()

from django.utils.safestring import mark_safe
from geopy.geocoders import Nominatim
import json

# @login_required
def photo_map_view(request):
    username = request.user.username

    user_groups = PhotoGroup.objects.filter(members=request.user)
    all_users = list(User.objects.values_list('username', flat=True))
    all_groups = list(PhotoGroup.objects.values_list('name', flat=True))

    user_photos_qs = PhotoUpload.objects.filter(uploaded_by=request.user)
    other_photos_qs = PhotoUpload.objects.exclude(uploaded_by=request.user).filter(
        models.Q(visibility='any') |
        models.Q(shared_with=request.user) |
        models.Q(group__in=user_groups)
    ).distinct()

    geolocator = Nominatim(user_agent="picupapp")

    def serialize_photos(qs):
        country_set = set()
        serialized = []
        for p in qs:
            country = ''
            if p.latitude and p.longitude:
                try:
                    location = geolocator.reverse(f"{p.latitude}, {p.longitude}", language='en', timeout=5)
                    country = location.raw.get('address', {}).get('country', '')
                except Exception:
                    country = ''
            if country:
                country_set.add(country)
            serialized.append({
                "id": p.id,
                "image_url": p.image.url,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "comment": p.comment or "",
                "user": p.uploaded_by.username,
                "taken": p.photo_taken_date.strftime("%Y-%m-%d %H:%M") if p.photo_taken_date else "",
                "group": p.group.name if p.group else "",
                "visibility": p.visibility or "private",
                "country": country
            })
        return serialized, country_set

    combined_qs = list(user_photos_qs) + list(other_photos_qs)
    all_data, country_set = serialize_photos(combined_qs)

    user_data = [p for p in all_data if p['user'] == username]
    other_data = [p for p in all_data if p['user'] != username]

    return render(request, 'picupapp/mappics.html', {
        'username': username,
        'user_photos_json': mark_safe(json.dumps(user_data)),
        'other_photos_json': mark_safe(json.dumps(other_data)),
        'countries': sorted(country_set),
        'user_groups': user_groups,
        'all_users': all_users,
        'all_groups': all_groups,
        'user_photo_count': user_photos_qs.count(),
        'shared_photo_count': other_photos_qs.count(),
    })


# @login_required
def create_group_view(request):
    selected_member_ids = []

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        selected_member_ids = request.POST.getlist('members')

        if PhotoGroup.objects.filter(name__iexact=name).exists():
            messages.error(request, "A group with this name already exists.")
        elif name:
            group = PhotoGroup.objects.create(name=name, created_by=request.user)
            members = User.objects.filter(id__in=selected_member_ids)
            group.members.set(members)
            group.members.add(request.user)
            return redirect(f"{reverse('picupapp:landing')}?new_group=1")
        else:
            messages.error(request, "Group name is required.")

    all_users = User.objects.exclude(id=request.user.id)
    return render(request, 'picupapp/create_group.html', {
        'all_users': all_users,
        'selected_member_ids': selected_member_ids
    })

# @login_required
def get_user_groups(request):
    groups = PhotoGroup.objects.filter(created_by=request.user).values('id', 'name')
    return JsonResponse(list(groups), safe=False)


def public_photo_map_view(request):
    shared_photos = PhotoUpload.objects.filter(visibility='any')
    geolocator = Nominatim(user_agent="picupapp-public")

    country_counter = Counter()

    def serialize_photos(qs):
        serialized = []
        for p in qs:
            country = ''
            if p.latitude and p.longitude:
                try:
                    location = geolocator.reverse(f"{p.latitude}, {p.longitude}", language='en', timeout=5)
                    country = location.raw.get('address', {}).get('country', '')
                except Exception:
                    country = ''
            if country:
                country_counter[country] += 1

            serialized.append({
                "id": p.id,
                "image_url": p.image.url,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "comment": p.comment or "",
                "user": p.uploaded_by.username,
                "taken": p.photo_taken_date.strftime("%Y-%m-%d %H:%M") if p.photo_taken_date else "",
                "visibility": p.visibility or "private",
                "country": country
            })
        return serialized

    serialized_photos = serialize_photos(shared_photos)

    sorted_countries = [country for country, _ in country_counter.most_common()] or sorted(country_counter.keys())

    return render(request, 'picupapp/public_map.html', {
        'shared_photos_json': mark_safe(json.dumps(serialized_photos)),
        'shared_photo_count': shared_photos.count(),
        'countries': sorted_countries,
    })

def about_view(request):
    next_page = request.GET.get('next', None)
    return render(request, 'picupapp/about.html', {
        'user': request.user,
        'next_page': next_page,
    })

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect
from django.contrib import messages

# @login_required
def change_profile_view(request):
    user = request.user
    password_form = PasswordChangeForm(user, request.POST or None)

    if request.method == 'POST':
        new_username = request.POST.get('username', '').strip()
        new_email = request.POST.get('email', '').strip()

        # Only update if values are provided and different
        if new_username and new_username != user.username:
            user.username = new_username
        if new_email and new_email != user.email:
            user.email = new_email

        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, user)
            user.save()
            messages.success(request, "Profile and password updated successfully.")
            return redirect('picupapp:change_profile')
        else:
            # Even if password is invalid, save other profile fields
            user.save()
            if password_form.has_changed():
                messages.warning(request, "Username/email updated, but password not changed.")
            else:
                messages.success(request, "Profile updated.")

    return render(request, 'registration/change_profile.html', {
        'form': password_form,
    })

