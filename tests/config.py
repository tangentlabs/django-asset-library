import os
from django.conf import settings

from asset_library.defaults import *
asset_library_settings = {
    k: v for k, v in locals().items() if k.startswith('ASSET_')}


def configure():
    if not settings.configured:

        # Helper function to extract absolute path
        location = lambda x: os.path.join(
            os.path.dirname(os.path.realpath(__file__)), x)

        settings.configure(
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.admin',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.sites',
                'django.contrib.flatpages',
                'django.contrib.staticfiles',
                'sorl.thumbnail',
                'asset_library',
            ],
            PASSWORD_HASHERS=(
                'django.contrib.auth.hashers.MD5PasswordHasher',
            ),
            STATIC_URL='/static/',
            STATIC_ROOT=location('static'),
            MEDIA_URL='/media/',
            MEDIA_ROOT=location('media'),
            ROOT_URLCONF='tests.urls',
            FIXTURE_DIRS=(location('fixtures'), ),
            **asset_library_settings
        )

        settings.ASSET_FILE_EXTENSIONS += ['TXT']
