from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(('picupapp.urls', 'picupapp'), namespace='picupapp')),
    path('change-password/', auth_views.PasswordChangeView.as_view(
        template_name='registration/change_password.html',
        success_url=reverse_lazy('password_change_done')
    ), name='change_password'),

    path('change-password-done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/change_password_done.html'
    ), name='password_change_done'),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Ensure media files are served in production (e.g., Render)
# urlpatterns += [
#     re_path(r'^media/(?P<path>.*)$', serve, {
#         'document_root': settings.MEDIA_ROOT,
#     }),
# ]
