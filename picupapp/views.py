from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from .models import PhotoUpload
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Login view
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('picupapp:landing')
        else:
            return render(request, 'picupapp/login.html', {'error': 'Invalid credentials'})
    return render(request, 'picupapp/login.html')

# Register view
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

# Landing page
@login_required
def landing(request):
    try:
        photos = PhotoUpload.objects.order_by('-uploaded_at')

        if request.method == 'POST':
            for f in request.FILES.getlist('images'):
                PhotoUpload.objects.create(image=f, uploaded_by=request.user)
            return redirect('picupapp:landing')

        return render(request, 'picupapp/landing.html', {
            'photos': photos,
            'username': request.user.username
        })

    except Exception as e:
        logger.exception("Landing view error:")
        return HttpResponse("Something went wrong.", status=500)

# Delete photo
@login_required
def delete_photo(request, photo_id):
    photo = get_object_or_404(PhotoUpload, id=photo_id, uploaded_by=request.user)
    photo.image.delete()
    photo.delete()
    return redirect('picupapp:landing')

# Logout
def logout_view(request):
    logout(request)
    return redirect('picupapp:login')

# ✅ New: Map view
@login_required
def map_pics_view(request):
    user_photos = PhotoUpload.objects.filter(
        uploaded_by=request.user
    ).exclude(latitude=None).exclude(longitude=None)

    other_photos = PhotoUpload.objects.exclude(
        uploaded_by=request.user
    ).exclude(latitude=None).exclude(longitude=None)

    def serialize(photos):
        return [
            {
                "latitude": p.latitude,
                "longitude": p.longitude,
                "image_url": settings.MEDIA_URL + str(p.image),
                "comment": p.comment or "",
                "user": p.uploaded_by.username
            }
            for p in photos
        ]

    return render(request, 'picupapp/mappics.html', {
        'user_photos': serialize(user_photos),
        'other_photos': serialize(other_photos),
        'username': request.user.username
    })

