import os
from datetime import timedelta
from pathlib import Path

# import ssl
import certifi

# ssl._create_default_https_context = ssl.create_default_context(
#     cafile=certifi.where()
# )
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-h5s(&dh2&3zqwv)+p2p$j4lm+cc9si#l1^!pbry%l-o%j5)f^h'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'drf_yasg',

    'users',
    'clients',
    'applications',
    'loans',
    'payments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
CORS_ALLOW_ALL_ORIGINS = True
ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'umuzylvc_KML',
        'USER': 'umuzylvc_admin',
        'PASSWORD': 'Ngoga@1patrick',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
AUTH_USER_MODEL = 'users.User'
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# EMAIL_HOST = "mynextmarket.com"          # Namecheap SMTP server
# EMAIL_PORT = 465                          # SSL port
# EMAIL_USE_TLS = False                     # disable TLS
# EMAIL_USE_SSL = True                      # enable SSL for port 465
# # EMAIL_USE_SSL = False 

# EMAIL_HOST_USER = "no-reply@mynextmarket.com"
# EMAIL_HOST_PASSWORD = "Ngoga@1patrick"

# DEFAULT_FROM_EMAIL = "My Next Market <no-reply@mynextmarket.com>"

# DEFAULT_FROM_EMAIL = "Volcanorom <no-reply@mynextmarket.com>"
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
# EMAIL_USE_TLS = True
# EMAIL_SSL_CERTFILE = certifi.where()
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'housemajorrwanda@gmail.com'
EMAIL_HOST_PASSWORD = 'kpxr khxv wjoy hprg'  # NOT your Gmail password!
DEFAULT_FROM_EMAIL = 'House Major <housemajorrwanda@gmail.com>'
