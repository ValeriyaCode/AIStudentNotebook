from django.contrib import admin
from django.urls import include, path
from accounts.views import avatar_media

urlpatterns = [
    path('media/avatars/<str:filename>', avatar_media, name='avatar_media'),
    path('django-admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('workbooks.urls')),
]
