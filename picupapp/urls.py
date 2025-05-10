from django.urls import path
from . import views

app_name = 'picupapp'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('landing/', views.landing, name='landing'),
    path('logout/', views.logout_view, name='logout'),    
    path('register/', views.register_view, name='register'),
    path('delete/<int:photo_id>/', views.delete_photo, name='delete_photo'),

    # Public/Shared User Map View (normal users)
    path('map/', views.photo_map_view, name='photo_map'),

    # Admin Map View (staff-only)
    path('map/admin/', views.map_pics_view, name='map_admin'),

    path('check-media/', views.check_media_access, name='check_media'),
    path('metadata/', views.metadata_table_view, name='metadata_table'),
    path('update-comment/', views.update_comment, name='update_comment'),
]
