from .models import PhotoUpload
from .utils import add_watermark
from django.utils.timezone import now
from django.shortcuts import redirect

def upload_photos(request):
    if request.method == 'POST':
        images = request.FILES.getlist('images')
        visibility = request.POST.get('visibility', 'private')
        photo_group = request.POST.get('photo_group')
        shared_with = request.POST.getlist('shared_with')

        for i, image_file in enumerate(images):
            # ✅ Apply watermark before saving
            watermarked = add_watermark(image_file, request.user.username)
            watermarked.seek(0)  # Ensure pointer is at start

            photo = PhotoUpload(
                uploaded_by=request.user,
                visibility=visibility,
                upload_date=now()
            )

            if visibility == 'group' and photo_group:
                photo.photo_group_id = photo_group

            filename = f"{request.user.username}_{now().strftime('%Y%m%d%H%M%S')}_{i}.jpg"
            photo.image.save(filename, watermarked)

            photo.save()

            if visibility == 'shared' and shared_with:
                photo.shared_with.set(shared_with)

        return redirect('picupapp:landing')
