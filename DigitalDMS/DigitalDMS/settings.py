"""
    Django settings for Auto post tool project.

    For more information on this file, see
    https://docs.djangoproject.com/en/3.2/topics/settings/

    For the full list of settings and their values, see
    https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import json
import os
import warnings
from datetime import timedelta
from os.path import dirname, join
from pathlib import Path

from dotenv import load_dotenv


# Ignore warnings
warnings.filterwarnings("ignore")


ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

env_file_name = f"env/{ENVIRONMENT}.env"

dotenv_path = join(dirname(__file__), f"../{env_file_name}")
load_dotenv(dotenv_path)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

PRODUCT_NAME = os.environ.get("PROJECT_NAME", "EB3 Admin")
VERSION = os.environ.get("VERSION", "1.0")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = "True"

ALLOWED_HOSTS = ["*"]
ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # # Third-party apps
    "corsheaders",
    "ninja_extra",
    "storages",
    "django_celery_results",
    # local apps
    "user_account",
    "token_management",
    "document_management",
    "search_services",
    "entry_log_management",
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom middleware
    "utils.middleware.ResponseHandleWiddleware",
]

ROOT_URLCONF = "DigitalDMS.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "DigitalDMS.wsgi.application"

# Change user model
AUTH_USER_MODEL = "user_account.User"


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DATABASE_ENGINE"),
        "NAME": os.environ.get("DATABASE_NAME"),
        "USER": os.environ.get("DATABASE_USER"),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD"),
        "HOST": os.environ.get("DATABASE_HOST"),
        "PORT": os.environ.get("DATABASE_PORT"),
    }
}

# JWT Settings
ACCESS_TOKEN_LIFETIME = int(str(os.environ.get("ACCESS_TOKEN_LIFETIME")))
REFRESH_TOKEN_LIFETIME = int(str(os.environ.get("REFRESH_TOKEN_LIFETIME")))


NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=ACCESS_TOKEN_LIFETIME),
    "REFRESH_TOKEN_LIFETIME": timedelta(minutes=REFRESH_TOKEN_LIFETIME),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "USER_ID_FIELD": "email",
    "USER_ID_CLAIM": "email",
    "USER_AUTHENTICATION_RULE": "ninja_jwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("ninja_jwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "ninja_jwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# EMAIL CONFIGURATION
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS")
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND")
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
EMAIL_TIMEOUT = int(str(os.environ.get("EMAIL_TIMEOUT")))

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE")

TIME_ZONE = os.environ.get("TIME_ZONE")

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ORIGIN_ALLOW_ALL = os.environ.get("CORS_ALLOW_ALL_ORIGINS") == "True"

# Pagination
DEFAULT_PAGE_SIZE = int(str(os.environ.get("DEFAULT_PAGE_SIZE")))
PAGE_SIZE_MAX = int(str(os.environ.get("PAGE_SIZE_MAX")))

# ADMIN USER
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# UID
BASE_UI_URL = os.environ.get("BASE_UI_URL")
BASE_MEDIA_HOST = os.environ.get("BASE_MEDIA_HOST")
CALL_BACK_URL = os.environ.get("CALL_BACK_URL")
BASE_HOST = os.environ.get("BASE_HOST")


# NINJA_DOCS_VIEW = "redoc"

# Logging Settings
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] [%(levelname)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
        "color_formatter": {
            "()": "utils.logging.formatter.Formatter"
        },  # colored output
    },
    "handlers": {
        "console_handler": {
            "class": "logging.StreamHandler",
            "formatter": "color_formatter",
        }
    },
    "loggers": {
        "": {
            "level": "DEBUG",
            "handlers": ["console_handler"],
            "propagate": False,
            "formatter": "color_formatter",
        },
        "API": {
            "level": "DEBUG",
            "handlers": ["console_handler"],
            "propagate": False,
            "formatter": "color_formatter",
        },
    },
}

# media directory in the root directory
# MEDIA_ROOT = os.path.join(BASE_DIR, str(os.environ.get("MEDIA_ROOT")))
# MEDIA_URL = str(os.environ.get("MEDIA_URL"))

# STATICFILES_DIRS = [BASE_DIR / "media/images"]
# STATIC_ROOT = os.path.join(BASE_DIR, "static")
# STATIC_URL = os.environ.get("STATIC_URL")

STATIC_URL = "/static/static/"
STATIC_ROOT = "/vol/web/static"
MEDIA_URLS = "/static/media/"
MEDIA_ROOT = "/vol/web/media"

# JWT
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM")
JWT_EXPIRED_TIME = int(str(os.environ.get("JWT_EXPIRED_TIME")))

LOGIN_TOKEN_LENGTH = int(str(os.environ.get("LOGIN_TOKEN_LENGTH")))

RESET_TOKEN_LENGTH = int(str(os.environ.get("RESET_PASSWORD_TOKEN_LENGTH")))
RESET_PASSWORD_TOKEN_LIFETIME = int(
    str(os.environ.get("RESET_PASSWORD_TOKEN_LIFETIME"))
)


API_REQUEST_CONTENT_TYPE = os.environ.get("API_REQUEST_CONTENT_TYPE")
REQUEST_TIMEOUT = int(str(os.environ.get("REQUEST_TIMEOUT")))

MINIMUM_LENGTH = os.environ.get("MINIMUM_LENGTH")
CONTAIN_NO_NUMBER = os.environ.get("CONTAIN_NO_NUMBER")
CONTAIN_NUMBER_AND_LETTER = os.environ.get("CONTAIN_NUMBER_AND_LETTER")
EMAIL = os.environ.get("EMAIL")

NAME = os.environ.get("NAME")
PASSWORD = os.environ.get("PASSWORD")
EMAIL = os.environ.get("EMAIL")

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_WHILELIST = ("localhost:9999",)
CORS_ALLOW_HEADERS = [
    "ngrok-skip-browser-warning",
    "Authorization",
    "Content-Type",
    # Add other headers if needed
]
# password rules
PASSWORD_MUST_CONTAIN_NUMBER = os.environ.get("PASSWORD_MUST_CONTAIN_NUMBER") == "False"
PASSWORD_MINIMUM_LENGTH = int(os.environ.get("PASSWORD_MINIMUM_LENGTH"))
PASSWORD_NOT_CONTAIN_SPACE = os.environ.get("PASSWORD_NOT_CONTAIN_SPACE") == "True"

# name rules
NAME_CANT_CONTAIN_NUMBER = os.environ.get("NAME_CANT_CONTAIN_NUMBER")

SUCCESS_CODE = os.environ.get("SUCCESS_CODE")

# post type
NAME_NOT_CONTAIN_SPACE = os.environ.get("NAME_NOT_CONTAIN_SPACE") == "True"
# post type
DEFAULT_POST_TYPE = os.environ.get("DEFAULT_POST_TYPE")


AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
AWS_S3_SIGNATURE_NAME = os.environ.get("AWS_S3_SIGNATURE_NAME")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_S3_VERIFY = True
DEFAULT_FILE_STORAGE = os.environ.get("DEFAULT_FILE_STORAGE")
AWS_S3_ENDPOINT = os.environ.get("AWS_S3_ENDPOINT")


# Elasticsearch config
ELASTICSEARCH_HOST = os.environ.get("ELASTICSEARCH_HOST")
ELASTICSEARCH_PASSWORD = os.environ.get("ELASTICSEARCH_PASSWORD")
METADATA_THRESHOLD = float(os.environ.get("METADATA_THRESHOLD", 0.7))
# CELERY CONFIG
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_BROKER_URL = os.environ.get("CELERY_WORKER", "redis://localhost:6379/0")
# CELERY_RESULT_BACKEND = os.environ.get("CELERY_BACKEND", "redis://127.0.0.1:6379/0")
# CELERY_TASK_SERIALIZER= 'pickle'
# CELERY_RESULT_SERIALIZER= 'pickle'
CELERY_ACCEPT_CONTENT = ["pickle", "application/json", "application/x-python-serialize"]
SEARCH_INDEX = os.environ.get("SEARCH_INDEX", "test")
METADATA_INDEX = os.environ.get("METADATA_INDEX", "metadata")
ALLOW_UPLOAD = os.environ.get("ALLOW_UPLOAD", "False")
DEFAULT_ELASTIC_PAGINATION_SIZE = int(os.environ.get("DEFAULT_ELASTIC_PAGINATION_SIZE", 200))
