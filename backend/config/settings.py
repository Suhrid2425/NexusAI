
"""
Django settings for config project.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv


# --------------------------------------------------
# BASE CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# Load project-root .env during local development.
load_dotenv(BASE_DIR.parent / ".env")


# --------------------------------------------------
# SECRET KEY
# --------------------------------------------------

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

# Allow a development-only fallback on your local machine.
# Vercel must always have DJANGO_SECRET_KEY configured.
if not SECRET_KEY:
    if os.getenv("VERCEL"):
        raise RuntimeError(
            "DJANGO_SECRET_KEY must be configured in Vercel."
        )

    SECRET_KEY = "django-insecure-local-development-key"


# --------------------------------------------------
# DEBUG
# --------------------------------------------------

DEBUG = False


# --------------------------------------------------
# SECURITY SETTINGS
# --------------------------------------------------

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "nexus-ai-ashy-iota.vercel.app",
    "nexus-ai-git-main-fresher-go.vercel.app",
    "nexus-p3ukw6kze-fresher-go.vercel.app",
]

# Add Vercel's automatically supplied deployment hostname.
VERCEL_URL = os.getenv("VERCEL_URL")

if VERCEL_URL:
    ALLOWED_HOSTS.append(VERCEL_URL)

# Additional hosts from environment variables.
EXTRA_ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

ALLOWED_HOSTS.extend(
    host for host in EXTRA_ALLOWED_HOSTS
    if host not in ALLOWED_HOSTS
)


# CSRF trusted origins.
CSRF_TRUSTED_ORIGINS = [
    "https://nexus-ai-ashy-iota.vercel.app",
    "https://nexus-ai-git-main-fresher-go.vercel.app",
    "https://nexus-p3ukw6kze-fresher-go.vercel.app",
]

if VERCEL_URL:
    CSRF_TRUSTED_ORIGINS.append(
        f"https://{VERCEL_URL}"
    )

EXTRA_CSRF_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

CSRF_TRUSTED_ORIGINS.extend(
    origin for origin in EXTRA_CSRF_ORIGINS
    if origin not in CSRF_TRUSTED_ORIGINS
)

# Vercel terminates HTTPS and forwards the original protocol.
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)


# --------------------------------------------------
# APPLICATION DEFINITION
# --------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",

    "accounts",
    "organizations",
    "core",
]


# --------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"


# --------------------------------------------------
# TEMPLATES
# --------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"


# --------------------------------------------------
# DATABASE CONFIGURATION
# --------------------------------------------------

DATABASE_URL = os.getenv("NEXUS_DB_DATABASE_URL")

if DATABASE_URL:
    # Neon PostgreSQL on Vercel.
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,
            ssl_require=True,
        )
    }

elif os.getenv("VERCEL"):
    # Never silently fall back to localhost in production.
    raise RuntimeError(
        "NEXUS_DB_DATABASE_URL is missing in Vercel."
    )

else:
    # Local development PostgreSQL.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5433"),
        }
    }


# --------------------------------------------------
# PASSWORD VALIDATION
# --------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# --------------------------------------------------
# INTERNATIONALIZATION
# --------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# --------------------------------------------------
# STATIC FILES
# --------------------------------------------------

STATIC_URL = "/static/"


# --------------------------------------------------
# EMAIL
# --------------------------------------------------

EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
)


# --------------------------------------------------
# CUSTOM USER MODEL
# --------------------------------------------------

AUTH_USER_MODEL = "accounts.User"


# --------------------------------------------------
# DJANGO REST FRAMEWORK
# --------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}


# --------------------------------------------------
# UPLOADED MEDIA
# --------------------------------------------------

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# --------------------------------------------------
# DEFAULT PRIMARY KEY
# --------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
