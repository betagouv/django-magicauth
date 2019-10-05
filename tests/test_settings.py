SECRET_KEY = "can you keep a secret?"

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3"}}

ROOT_URLCONF = "tests.test_url"

INSTALLED_APPS = [
    "tests",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "magicauth",
]

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

MAGICAUTH_FROM_EMAIL = "user@domain.user"
MAGICAUTH_LOGGED_IN_REDIRECT_URL_NAME = "test_home"


TEMPLATES = [
    {"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
]
