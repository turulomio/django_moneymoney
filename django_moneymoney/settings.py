from django.urls import reverse_lazy
from getpass import getuser
from moneymoney import __version__
from os import path, makedirs
from shutil import rmtree

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

## Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = path.dirname(path.dirname(__file__))

## SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'CHANGEME-CHANGEME-CHANGEME-CHANGEME-CHANGEME-CHANGEME'

## @note SECURITY WARNING: don't run with debug turned on in production!
## Defines is a Debug environment
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1' ]

REST_FRAMEWORK={ 
    'DEFAULT_AUTHENTICATION_CLASSES':[
        'rest_framework.authentication.BasicAuthentication',  ## Uncomment to use api in url 
        'rest_framework.authentication.TokenAuthentication', 
    ], 
    'COERCE_DECIMAL_TO_STRING': False, 
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


if 'rest_framework.authentication.BasicAuthentication' in REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]:
    print ("You should remove BasicAuthentication for production systems")

SPECTACULAR_SETTINGS = {
    'TITLE': 'Django Money Money API Documentation',
    'DESCRIPTION': 'Interactive documentation',
    'VERSION': __version__,
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX_INSERT': '',
}

## Application definitions
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken', 
    'drf_spectacular',
    'corsheaders', 
    'moneymoney',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware', #Must be here
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware', 
]

ROOT_URLCONF = 'django_moneymoney.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR+"/templates/"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

CORS_ORIGIN_WHITELIST =  "http://localhost:8005",

WSGI_APPLICATION = 'django_moneymoney.wsgi.application'

## Database connection definitions
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'xulpymoney',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': 5432,
    }
}

CONCURRENCY_DB_CONNECTIONS_BY_USER=8

## Locale paths in source distribution
LOCALE_PATHS = (
    BASE_DIR+ '/moneymoney/locale/',
)

## Password validation 
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

## Language code
LANGUAGE_CODE = 'en-us'
LANGUAGES=[
    ("en", "English"),  
    ("es",  "Español"), 
    ("fr", "Français") , 
    ("ro", "Romanian"), 
    ("ru", "Russian"), 
]
## Timezone definition
USE_TZ = True
TIME_ZONE = 'UTC'

## Internationalization
USE_I18N = True
USE_L10N = True

LOGIN_URL = reverse_lazy("login")
LOGOUT_REDIRECT_URL = reverse_lazy("login")

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR+ "/moneymoney/static/"

TMPDIR=f"/tmp/django_moneymoney-{getuser()}"
rmtree(TMPDIR, ignore_errors=True)
makedirs(TMPDIR, exist_ok=True)
