from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from core.views import home


urlpatterns = [
    # Homepage
    path("", home, name="home"),

    # Admin
    path("admin/", admin.site.urls),

    # Organization APIs
    path("api/", include("organizations.urls")),

    # Authentication
    path("api/auth/", include("accounts.urls")),

    # JWT authentication
    path(
        "api/auth/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/auth/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    # Core APIs
    path("api/", include("core.urls")),
]