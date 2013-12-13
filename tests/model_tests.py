import os
import shutil

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.test import TestCase

from asset_library import models
from .utils import create_asset, create_image_asset, create_file_asset, \
    create_snippet_asset, clean_media, create_user, get_fixture_path


class TestAssetSharing(TestCase):
    def create_asset(self, *args, **kwargs):
        return create_asset(*args, **kwargs)

    def setUp(self):
        self.shared_by = create_user()
        self.shared_with = create_user()
        self.asset = self.create_asset(creator=self.shared_by)

    def test_creates_a_new_asset(self):
        # There is one asset
        self.assertEqual(1, models.Asset.objects.all().count())

        self.asset.share(self.shared_by, self.shared_with)

        # There are two assets now
        self.assertEqual(2, models.Asset.objects.all().count())

    def test_makes_new_asset_tags_independent(self):
        tag_names = [str(i) for i in range(10)]
        tags = [models.Tag.objects.create(name=name) for name in tag_names]
        self.asset.tags = tags
        new_asset = self.asset.share(self.shared_by, self.shared_with)
        self.asset.tags = []
        new_tag_names = [tag.name for tag in new_asset.tags.all()]
        self.assertEqual(tag_names, new_tag_names)

    def test_makes_old_asset_tags_independent(self):
        tag_names = [str(i) for i in range(10)]
        tags = [models.Tag.objects.create(name=name) for name in tag_names]
        self.asset.tags = tags
        new_asset = self.asset.share(self.shared_by, self.shared_with)
        new_asset.tags = []
        asset_tag_names = [tag.name for tag in self.asset.tags.all()]
        self.assertEqual(tag_names, asset_tag_names)

    def test_makes_normal_fields_independent(self):
        new_asset = self.asset.share(self.shared_by, self.shared_with)
        # Change original asset
        self.asset.name = 'New name'
        self.asset.description = 'Changed description'
        self.asset.save()
        # Reload new asset from database
        new_asset = models.Asset.objects.get(pk=new_asset.pk)
        self.assertNotEqual('New name', new_asset.name)
        self.assertNotEqual('Changed description', new_asset.description)

    def test_can_accepting_inbox_asset(self):
        shared_asset = self.asset.share(self.shared_by, self.shared_with)
        shared_asset.accept_shared()
        self.assertEqual(None, shared_asset.shared_by)

    def test_can_reject_asset(self):
        shared_asset = self.asset.share(self.shared_by, self.shared_with)
        shared_asset.reject_shared()
        # PK does not exist anymore because the asset was deleted
        self.assertEqual(None, shared_asset.pk)


class TestImageAssetSharing(TestAssetSharing):
    def create_asset(self, *args, **kwargs):
        return create_image_asset(*args, **kwargs)

    def tearDown(self):
        clean_media()


class TestFileAssetSharing(TestAssetSharing):
    def create_asset(self, *args, **kwargs):
        return create_file_asset(*args, **kwargs)

    def tearDown(self):
        clean_media()


class TestSnippetAssetSharing(TestAssetSharing):
    def create_asset(self, *args, **kwargs):
        return create_snippet_asset(*args, **kwargs)


class ImageAssetModel(TestCase):
    def setUp(self):
        super(ImageAssetModel, self).setUp()
        self.user = User.objects.create_user('dummy', 'mail@example.com',
                                             'password')

        path = get_fixture_path('TEST_IMAGE.jpeg')
        self.image = File(open(path))

    def tearDown(self):
        """ Remove any uploaded media """
        if os.path.exists(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)

    def test_create_asset(self):
        # Create asset
        NAME = 'My image'
        DESCRIPTION = 'A nice image'
        WIDTH, HEIGHT = 230, 219
        SIZE = 8820
        EXTENSION = 'JPEG'
        asset = models.ImageAsset(name=NAME, description=DESCRIPTION,
                                  image=self.image, creator=self.user)
        asset.save()

        # Look up asset
        image = models.ImageAsset.objects.all()[0]
        self.assertEqual(NAME, image.name)
        self.assertEqual(DESCRIPTION, image.description)
        self.assertEqual(WIDTH, image.width)
        self.assertEqual(HEIGHT, image.height)
        self.assertEqual(SIZE, image.size)
        self.assertEqual(EXTENSION, image.extension)

        # Cached parameters are same as image properties
        self.assertEqual(WIDTH, image.image.width)
        self.assertEqual(HEIGHT, image.image.height)
        self.assertEqual(SIZE, image.image.size)

    def test_accept_only_allowed_exceptions(self):
        old_settting = settings.ASSET_IMAGE_EXTENSIONS

        __, file_ext = os.path.splitext(self.image.name)
        file_ext = file_ext.lstrip('.').upper()
        settings.ASSET_IMAGE_EXTENSIONS = ['XXX']
        asset = models.ImageAsset(
            name='test', image=self.image, creator=self.user)
        asset.populate_fields()
        with self.assertRaises(ValidationError):
            asset.full_clean()

        # It works now
        settings.ASSET_IMAGE_EXTENSIONS.append(file_ext)
        asset.full_clean()

        settings.ASSET_IMAGE_EXTENSIONS = old_settting

    def test_refuse_fake_extensions(self):
        # See https://tracker.tangentlabs.co.uk/view.php?id=82497
        old_settting = settings.ASSET_IMAGE_EXTENSIONS

        # Fake PNG image prettending be JPG
        path = get_fixture_path('koala_png.jpg')
        image = File(open(path))

        settings.ASSET_IMAGE_EXTENSIONS = ['JPG']

        asset = models.ImageAsset(
            name='test', image=image, creator=self.user)
        asset.populate_fields()
        with self.assertRaises(ValidationError):
            asset.full_clean()

        # It work for PNG
        asset.image.seek(0)
        settings.ASSET_IMAGE_EXTENSIONS = ['PNG']
        asset.full_clean()

        settings.ASSET_IMAGE_EXTENSIONS = old_settting


class FileAssetModel(TestCase):
    def setUp(self):
        super(FileAssetModel, self).setUp()
        self.user = User.objects.create_user('dummy', 'mail@example.com',
                                             'password')

        path = get_fixture_path('TEST_FILE.txt')
        self.test_file = File(open(path))

    def tearDown(self):
        """ Remove any uploaded media """
        if os.path.exists(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)

    def test_create_asset(self):
        # Create asset
        NAME = 'My file'
        DESCRIPTION = 'All work and no play make Jack a dull boy'
        SIZE = 4200
        EXTENSION = 'TXT'
        asset = models.FileAsset(name=NAME, description=DESCRIPTION,
                                 file=self.test_file, creator=self.user)
        asset.save()

        # Look up asset
        file_asset = models.FileAsset.objects.all()[0]
        self.assertEqual(NAME, file_asset.name)
        self.assertEqual(DESCRIPTION, file_asset.description)
        self.assertEqual(SIZE, file_asset.size)
        self.assertEqual(EXTENSION, file_asset.extension)

        # Cached size must be the same as file size
        self.assertEqual(SIZE, file_asset.file.size)

    def test_accept_only_allowed_exceptions(self):
        old_settting = settings.ASSET_FILE_EXTENSIONS

        __, file_ext = os.path.splitext(self.test_file.name)
        file_ext = file_ext.lstrip('.').upper()
        settings.ASSET_FILE_EXTENSIONS = ['XXX']
        asset = models.FileAsset(
            name='test', file=self.test_file, creator=self.user)
        asset.populate_fields()
        with self.assertRaises(ValidationError):
            asset.full_clean()

        # It works now
        settings.ASSET_FILE_EXTENSIONS.append(file_ext)
        asset.full_clean()

        settings.ASSET_FILE_EXTENSIONS = old_settting
