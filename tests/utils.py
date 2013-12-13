import os
import shutil
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import File

from asset_library.models import Asset, ImageAsset, FileAsset, SnippetAsset


""" Various factory methods to make setting up environments
as easy as possible """


def get_fixture_path(fixture_name):
    """ Return path to fixture """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'fixtures', fixture_name)


def create_user(name=None, email='dummy.user@example.com',
                password='dummy-passsword', first_name=None,
                last_name=None):
    """ Create a new user with the predefined credentials """
    if first_name and last_name:
        name = "%s.%s" % (first_name.lower(), last_name.lower())
    if name is None:
        # Generate random name
        name = str(uuid4())
    user = User.objects.create_user(name, email, password)
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    user.save()
    return user


def create_asset(creator=None, name="Dummy asset name",
                 description="My dummy asset description"):
    """ Factory method to create a general asset """
    if creator is None:
        creator = create_user()
    return Asset.objects.create(
        name=name, description=description, creator=creator)


def create_image_asset(creator=None, name="Dummy image name",
                       description="My dummy image description"):
    """ Factory method to create a new image asset """
    if creator is None:
        creator = create_user()
    image = File(open(get_fixture_path('TEST_IMAGE.jpeg')))
    return ImageAsset.objects.create(
        name=name, description=description, image=image, creator=creator)


def create_file_asset(creator=None, name="Dummy file name",
                      description="My dummy file description"):
    """ Factory method to create a new file asset """
    if creator is None:
        creator = create_user()
    file_obj = File(open(get_fixture_path('TEST_IMAGE.jpeg')))
    return FileAsset.objects.create(
        name=name, description=description, file=file_obj, creator=creator)


def create_snippet_asset(creator=None, name="Dummy snippet name",
                         description="My dummy snippet descriptions",
                         contents="Snippet contents"):
    if creator is None:
        creator = create_user()
    return SnippetAsset.objects.create(
        name=name, description=description, contents=contents, creator=creator)


def clean_media():
    """ Remove any uploaded media """
    if os.path.exists(settings.MEDIA_ROOT):
        shutil.rmtree(settings.MEDIA_ROOT)
