from django.urls import path
from . import views

app_name = 'picupapp'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('landing/', views.landing, name='landing'),
    path('delete/<int:photo_id>/', views.delete_photo, name='delete_photo'),

    # Photo maps
    path('map/', views.photo_map_view, name='photo_map'),         # Public/shared view
    path('map/admin/', views.map_pics_view, name='map_admin'),    # Admin (staff/all photos)

    # Utilities
    path('check-media/', views.check_media_access, name='check_media'),
    path('metadata/', views.metadata_table_view, name='metadata_table'),
    path('update-comment/', views.update_comment, name='update_comment'),
]
