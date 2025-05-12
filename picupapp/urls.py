from django.urls import path
from . import views

app_name = 'picupapp'  # This enables namespacing like 'picupapp:landing'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('landing/', views.landing, name='landing'),
    path('logout/', views.logout_view, name='logout'),    
    path('register/', views.register_view, name='register'),
    path('delete/<int:photo_id>/', views.delete_photo, name='delete_photo'),
    # path('mappics/', views.map_pics_view, name='mappics'),
    path('mappics/', views.photo_map_view, name='mappics'),  # should point to the one with counts
    path('check-media/', views.check_media_access, name='check_media'),
    path('metadata/', views.metadata_table_view, name='metadata_table'),
    path('update-comment/', views.update_comment, name='update_comment'),
    path('create-group/', views.create_group_view, name='create_group'),
    path('api/my-groups/', views.get_user_groups, name='get_user_groups'),
    path('shared-map/', views.public_photo_map_view, name='shared_photo_map'),

]
