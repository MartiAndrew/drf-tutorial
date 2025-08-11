"""
URL configuration for drf_example project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from debug_toolbar.toolbar import debug_toolbar_urls
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from drf_example.apps.example.api.router import router as example_router
from drf_example.custom_router import EnhancedAPIRouter


custom_router = EnhancedAPIRouter()
#
custom_router.register('examples', example_router, basename='examples')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/', include(custom_router.urls)),
]


# rest framework
urlpatterns = (
    [
        # URLs specific only to Django REST Framework:
        path('api-auth/', include('rest_framework.urls')),
    ]
    + urlpatterns
)

# debug toolbar

if settings.DEBUG:  # pragma: no cover
    import debug_toolbar  # noqa: WPS433

    urlpatterns += debug_toolbar_urls()
