from django.contrib import admin
from django.urls import path, include, re_path
from django.views.i18n import set_language
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="BIMUZ API",
        default_version='v1',
        description="API documentation for BIMUZ project. Employees can register, login, and manage their profiles. Students are managed by employees through the admin panel.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="dilshod.normurodov1392@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/setlang/', set_language, name='set_language'),
    
    path('api/v1/auth/', include('user.api.urls')),
    path('api/v1/education/', include('education.api.urls')),
    
    # Swagger/ReDoc URLs
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
