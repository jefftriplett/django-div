import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        ALLOWED_HOSTS=["*"],
        DEBUG=True,
        INSTALLED_APPS=["django.contrib.auth", "django.contrib.contenttypes"],
        DATABASES={},
        SECRET_KEY="django-div-tests",
        TEMPLATES=[
            {
                "BACKEND": "django_div.django.DjangoDivTemplates",
                "NAME": "django_div",
                "DIRS": [],
                "APP_DIRS": False,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.request",
                    ],
                },
            },
        ],
        USE_I18N=True,
    )
    django.setup()
