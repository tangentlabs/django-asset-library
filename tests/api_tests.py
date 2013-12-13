from urllib import urlencode
from urlparse import urljoin, urlparse
import json
import os
import shutil

from PIL import Image

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import File
from django.test import TestCase
from django.test.client import Client
from django.test.utils import override_settings

from asset_library import models
from asset_library.utils import media_uri_to_path
from tests.utils import create_user, get_fixture_path


def get_url(*args, **kwargs):
    """ Construct URL for API """
    base_url = settings.ASSET_API_ROOT
    base_url += '/' if not base_url.endswith('/') else ''
    url = base_url + "/".join(str(arg) for arg in args if arg)
    url += '/' if not url.endswith('/') else ''
    query_string = "?" + urlencode(kwargs)
    return urljoin(url, query_string)


class TestUserAutocompletion(TestCase):
    def setUp(self, *args, **kwargs):
        super(TestUserAutocompletion, self).setUp(*args, **kwargs)
        self.users = [
            create_user(first_name="Peter", last_name="Luke",
                        email='pluke@example.com'),
            create_user(first_name="John", last_name="Smith",
                        email='jsmith@example.com'),
            create_user(name="admin", password="password",
                        email='admin@example.com'),
            create_user(name="superuser", password="password",
                        email='superuser@example.com'),
        ]
        self.client = Client()
        self.client.login(username="superuser", password="password")

    def get_names(self, search):
        """ Return list of names for autocompletion """
        url = get_url('users', search=search)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        data = json.loads(response.content)
        return {obj['name'] for obj in data['objects']}

    def test_filters_by_first_name(self):
        names = self.get_names("Joh")
        self.assertEqual({"John Smith (jsmith@example.com)"}, names)

    def test_filters_by_last_name(self):
        names = self.get_names("uk")
        self.assertEqual({"Peter Luke (pluke@example.com)"}, names)

    def test_filters_by_user_name(self):
        names = self.get_names("adm")
        self.assertEqual({"admin@example.com"}, names)

    def test_filters_by_first_and_last_name(self):
        names = self.get_names("Peter Lu")
        self.assertEqual({"Peter Luke (pluke@example.com)"}, names)

    def test_is_case_insensitive(self):
        names = self.get_names("smith")
        self.assertEqual({"John Smith (jsmith@example.com)"}, names)

    def test_excludes_user_itself(self):
        names = self.get_names("superuser")
        self.assertEqual(0, len(names))


class AssetResourceTestCase(TestCase):
    """
    Base test class for testing resources through http requests.
    """

    PASSWORD = 'dummy-password'

    def setUp(self):
        super(AssetResourceTestCase, self).setUp()
        self.user = self.create_user()
        self.client = Client()

    def tearDown(self):
        """ Remove any uploaded media """
        if os.path.exists(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)

    def login(self):
        self.client.login(
            username=self.user.username,
            password=self.PASSWORD,
        )

    def create_user(self, name='dummy-user', email='dummy.user@example.com',
                    password=PASSWORD):
        """ Create a new user with the predefined credentials """
        return User.objects.create_user(name, email, password)

    def generate_assets(self, names, tags=None, creator=None, is_global=False):
        """ Create assets in database

        :param tags: list of tags to assign to those assets
        :param creator: creator/owner of assets
        :type creator: User object or None
        :param is_global: are assets global?
        """
        if tags is None:
            tags = []

        if creator is None:
            creator = self.user

        tag_objects = []
        for tag_name in tags:
            tag, created = models.Tag.objects.get_or_create(name=tag_name)
            if created:
                tag.save()
            tag_objects.append(tag)

        asset_ids = []
        for name in names:
            asset = self.create_asset()
            asset.creator = creator
            asset.name = name
            asset.is_global = is_global
            asset.save()

            asset_ids.append(asset.id)

            for tag in tag_objects:
                asset.tags.add(tag)

        return asset_ids

    def fetch_json(self, *args, **kwargs):
        """ Fetch JSON from API and make sure the request was
        successful (HTTP code 200) """
        url = get_url(self.resource, *args, **kwargs)
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        return json.loads(response.content)

    def fetch_names(self, **kwargs):
        """ Extract names from the response """
        response = self.fetch_json(**kwargs)
        return [str(asset['name']) for asset in response['objects']]

    def upload_file(self, filename, **kwargs):
        """ Upload a file and return response """
        url = get_url(self.resource)
        with open(filename) as fp:
            kwargs.update({'file': fp})
            response = self.client.post(url, kwargs)
        self.assertEqual(200, response.status_code)
        return json.loads(response.content)

    def post_data(self, data, *args, **kwargs):
        """ Post data to server """
        url = get_url(self.resource, *args, **kwargs)
        response = self.client.post(url, data)
        self.assertEqual(200, response.status_code)
        return json.loads(response.content)


class LogInMixin(object):
    """ Make sure user is logged for every test """
    def setUp(self):
        super(LogInMixin, self).setUp()
        self.login()


class AssetTestsMixin(LogInMixin):
    """ Tests that are common for image, file and snippet assets """

    def test_sort_by_name_case_insensitively(self):
        self.generate_assets(['b', 'A', 'a', 'c', 'B'])
        assets = self.fetch_names(sort_by='name')
        self.assertEqual(['A', 'a', 'b', 'B', 'c'], assets)

    def test_meta_details(self):
        names = ['b', 'A', 'a', 'c', 'B']
        self.generate_assets(names)

        for limit in range(1, 10):
            num_pages = len(names) / limit
            num_pages += 1 if len(names) % limit != 0 else 0
            for page in range(1, num_pages):
                response = self.fetch_json(page=page, limit=limit,
                                           sort_by='name')
                meta = response['meta']
                self.assertEqual(
                    page, meta['page'],
                    "Wrong page for page %d with limit %d" % (page, limit))
                self.assertEqual(
                    limit, meta['limit'],
                    "Wrong limit for page %d with limit %d" % (page, limit))
                self.assertEqual(
                    num_pages, meta['num_pages'],
                    "Wrong num_pages for page %d with limit %d" % (
                        page, limit))

    def test_ordering_on_pagination(self):
        self.generate_assets(['b', 'A', 'a', 'c', 'B'])

        page1 = self.fetch_names(page=1, limit=2, sort_by='name')
        self.assertEqual(['A', 'a'], page1)
        page2 = self.fetch_names(page=2, limit=2, sort_by='name')
        self.assertEqual(['b', 'B'], page2)
        page3 = self.fetch_names(page=3, limit=2, sort_by='name')
        self.assertEqual(['c'], page3)

    def test_filter_without_tags(self):
        self.generate_assets(['0', '1', '2', '3'], tags=['tag'])
        self.generate_assets(['4', '5'])

        assets = self.fetch_names(sort_by='name', without_tags=True)
        self.assertEqual(['4', '5'], assets)

    def test_filter_any_tags(self):
        self.generate_assets(['0', '1'], tags=['tag A'])
        self.generate_assets(['2', '3'], tags=['tag B'])
        self.generate_assets(['4', '5'])

        assets = self.fetch_names(sort_by='name')
        self.assertEqual(['0', '1', '2', '3', '4', '5'], assets)

    def test_filter_by_tag(self):
        self.generate_assets(['0', '1'], tags=['tag A'])
        self.generate_assets(['2', '3'], tags=['tag B'])
        self.generate_assets(['4', '5'])

        tag_filter = models.Tag.objects.get(name='tag B').id
        assets = self.fetch_names(sort_by='name', tag=tag_filter)
        self.assertEqual(['2', '3'], assets)

    def test_filter_by_non_existing_tag(self):
        self.generate_assets(['0', '1'])
        url = get_url(self.resource, sort_by='name', tag=123)
        response = self.client.get(url)
        self.assertEqual(400, response.status_code)

    def test_filter_by_malicious_string(self):
        self.generate_assets(['0', '1'])
        url = get_url(self.resource, sort_by='name', tag="'shutdown")
        response = self.client.get(url)
        self.assertEqual(400, response.status_code)

    def test_get_global(self):
        admin = self.create_user('administrator')
        self.generate_assets(['0', '1'], creator=admin, is_global=True)
        self.generate_assets(['2', '3'])
        self.generate_assets(['4', '5'], is_global=True)

        assets = self.fetch_names(sort_by='name', source='global')
        self.assertEqual(['0', '1', '4', '5'], assets)

        assets = self.fetch_names(sort_by='name', source='personal')
        self.assertEqual(['2', '3'], assets)

    def test_get_my_assets(self):
        admin = self.create_user('administrator')
        self.generate_assets(['0', '1'], creator=admin, is_global=True)
        self.generate_assets(['2', '3'])
        self.generate_assets(['4', '5'], is_global=True)

        assets = self.fetch_names(sort_by='name', source='personal')
        self.assertEqual(['2', '3'], assets)

    def test_get_only_my_assets(self):
        foouser = self.create_user('foouser')
        self.generate_assets(['0', '1'])
        self.generate_assets(['2', '3'], creator=foouser)
        self.generate_assets(['4', '5'])

        assets = self.fetch_names(sort_by='name')
        self.assertEqual(['0', '1', '4', '5'], assets)

    def test_paging(self):
        COUNT, LIMIT = 17, 3
        names = ["%02d" % i for i in range(COUNT)]

        self.generate_assets(names)
        for page in range(1, COUNT + 1):
            assets = self.fetch_names(
                page=page, limit=LIMIT, sort_by='name')
            offset = (page - 1) * LIMIT
            self.assertEqual(names[offset:offset+LIMIT], assets)

    def test_search(self):
        self.generate_assets(['car', 'parrot', 'plane'])

        names1 = self.fetch_names(search='')
        self.assertEqual(['car', 'parrot', 'plane'], names1)

        names2 = self.fetch_names(search='a')
        self.assertEqual(['car', 'parrot', 'plane'], names2)

        names3 = self.fetch_names(search='ar')
        self.assertEqual(['car', 'parrot'], names3)

        names4 = self.fetch_names(search='arr')
        self.assertEqual(['parrot'], names4)

        names5 = self.fetch_names(search='arrogant')
        self.assertEqual([], names5)

    def test_sort_by(self):
        self.generate_assets(['frog', 'cow', 'sky', 'ant'])

        assets1 = self.fetch_names(sort_by='name')
        self.assertEqual(['ant', 'cow', 'frog', 'sky'], assets1)

        assets2 = self.fetch_names(sort_by='newest_first')
        self.assertEqual(['ant', 'sky', 'cow', 'frog'], assets2)

        assets3 = self.fetch_names(sort_by='oldest_first')
        self.assertEqual(['frog', 'cow', 'sky', 'ant'], assets3)


class UploadTestsMixin(object):
    def test_upload_without_file(self):
        response = self.client.post(get_url(self.resource))
        self.assertEqual(400, response.status_code)

    def test_dangerous_destination_is_prohibited(self):
        with open(self.test_file) as fp:
            url = get_url(self.resource)
            response = self.client.post(url, {
                'destination': '../../etc',
                'file': fp,
            })
        self.assertEqual(400, response.status_code)

    def test_upload(self):
        self.assertEqual(0, len(self.fetch_names()))

        filename = os.path.basename(self.test_file)
        destination = os.path.join(settings.MEDIA_URL, 'email/1/1')
        response = self.upload_file(self.test_file, destination=destination)

        self.assertEqual(filename, response['object']['name'])
        self.assertIn('campaign_copy', response)

        # Validate campaign_copy
        parsed_path = urlparse(response['campaign_copy'])
        self.assertNotEqual('', parsed_path.scheme)
        self.assertTrue(parsed_path.path.startswith(settings.MEDIA_URL))

        self.assertEqual(1, len(self.fetch_names()))
        self.assertEqual([filename], self.fetch_names())

    def test_filter_extensions_are_case_insensitive(self):
        count = len(self.generate_assets(['test']))

        my_count = len(self.fetch_names(extension=self.extension))
        self.assertEqual(count, my_count)

        my_count = len(self.fetch_names(extension=self.extension.lower()))
        self.assertEqual(count, my_count)

        my_count = len(self.fetch_names(extension=self.extension.upper()))
        self.assertEqual(count, my_count)

    def test_filter_extensions_with_additional_extension(self):
        count = len(self.generate_assets(['test']))
        ext = "XXX,%s" % self.extension
        self.assertEqual(count, len(self.fetch_names(extension=ext)))

        ext = "%s,XxX" % self.extension.lower()
        self.assertEqual(count, len(self.fetch_names(extension=ext)))

        ext = "XXX,%s" % self.extension.upper()
        self.assertEqual(count, len(self.fetch_names(extension=ext)))

        ext = "jpg,jpeg,png,txt,%s,bmp,gif,tiff,my ext" % self.extension
        self.assertEqual(count, len(self.fetch_names(extension=ext)))

    def test_filter_extensions_ignore_empty_ext(self):
        count = len(self.generate_assets(['test']))
        ext = ",,, ,,,,,,,XXX,,,%s,,,, ,  ,, ,,," % self.extension
        self.assertEqual(count, len(self.fetch_names(extension=ext)))

    def test_filter_extensions_no_match(self):
        self.generate_assets(['test'])
        self.assertEqual(0, len(self.fetch_names(extension="XXX")))

    def test_filter_extensions_match_used_extensions(self):
        self.generate_assets(['test'])
        self.assertEqual(
            [], self.fetch_json(extension="XXX")['meta']['extensions'])
        extensions = "%s,XXX" % self.extension
        response = self.fetch_json(extension=extensions)
        returned_extensions = [
            ext.lower() for ext in response['meta']['extensions']
        ]
        self.assertEqual([self.extension.lower()], returned_extensions)


class ResourceDetailMixin(LogInMixin):
    def test_non_existing_asset(self):
        # GET
        response = self.client.get(get_url(self.resource, "none"))
        self.assertEqual(404, response.status_code)
        response = self.client.get(get_url(self.resource, 12345))
        self.assertEqual(404, response.status_code)

        # POST
        response = self.client.post(get_url(self.resource, "none"))
        self.assertEqual(404, response.status_code)
        response = self.client.post(get_url(self.resource, 12345))
        self.assertEqual(404, response.status_code)

    def test_access_details(self):
        names = ['A', 'B', 'C']
        asset_ids = self.generate_assets(names)
        for asset_id, name in zip(asset_ids, names):
            response = self.fetch_json(asset_id)
            self.assertIn('object', response)
            self.assertEqual(name, response['object']['name'])

    def test_destination_required_for_selection(self):
        asset_id = self.generate_assets(['asset'])[0]
        response = self.client.post(get_url(self.resource, asset_id))
        self.assertEqual(400, response.status_code)

    def test_select_asset(self):
        asset_id = self.generate_assets(['asset'])[0]
        destination = os.path.join(settings.MEDIA_URL, 'email/1/1/')
        response = self.post_data({'destination': destination}, asset_id)
        self.assertIn('campaign_copy', response)
        copy_path = response['campaign_copy']
        # Validate copy_path
        parsed_path = urlparse(copy_path)
        self.assertNotEqual('', parsed_path.scheme)
        self.assertTrue(parsed_path.path.startswith(settings.MEDIA_URL))


class TestAPIAccessibility(AssetResourceTestCase):
    """ API should expose only necessary methods and require login """

    def assert_login_required(self, url, msg):
        for method in "get", "post", "put", "delete":
            rest_method = getattr(self.client, method)
            response = rest_method(url)
            # 401 -- require authorization
            # 405 -- method not forbidden/impelemented
            self.assertIn(response.status_code, [401, 405],
                          "%s (%s method)" % (msg, method.upper()))

    def assert_forbidden_methods(self, url, methods, msg):
        self.login()
        for method in methods:
            rest_method = getattr(self.client, method.lower())
            response = rest_method(url)

            response = getattr(self.client, method)(url)
            self.assertEqual(
                405, response.status_code,
                "%s: Method %s is not forbidden" % (msg, method.upper()))

    def test_login_is_required(self):
        for resource in 'tags', 'images', 'files', 'snippets':
            url = get_url(resource)
            self.assert_login_required(
                url,
                "Resource '%s' is accesible without login" % resource)

        # Image details
        self.assert_login_required(
            get_url('images', 42), "Image details are accesible without login")

        # File details
        self.assert_login_required(
            get_url('files', 42), "File details are accesible without login")

        # Image editor
        self.assert_login_required(
            get_url('images', 'transformations'),
            "Image editor is accessible without login")

    def test_tags_methods_not_accessibe(self):
        self.assert_forbidden_methods(
            get_url('tags'), ['post', 'put', 'delete'], 'Tags resource')

    def test_images_methods_not_accessibe(self):
        self.assert_forbidden_methods(
            get_url('tags'), ['put', 'delete'], 'Images resource')

    def test_files_methods_not_accessibe(self):
        self.assert_forbidden_methods(
            get_url('files'), ['put', 'delete'], 'Files resource')

    def test_snippets_methods_not_accessibe(self):
        self.assert_forbidden_methods(
            get_url('snippets'), ['post', 'put', 'delete'],
            'Snippets resource')

    def test_image_details_methods_not_accessibe(self):
        self.assert_forbidden_methods(
            get_url('images', 1), ['put', 'delete'], 'Image details')

    def test_file_details_methods_not_accessible(self):
        self.assert_forbidden_methods(
            get_url('files', 1), ['put', 'delete'], 'File details')

    def test_image_editor_methods_not_accessibe(self):
        self.assert_forbidden_methods(
            get_url('images', 'transformations'),
            ['get', 'put', 'delete'], 'Image editor')


class TestTagAPI(LogInMixin, AssetResourceTestCase):
    resource = 'tags'

    def create_asset(self):
        """ Generate general asset """
        return models.Asset(name="Generated Asset")

    def test_empty_tags(self):
        # No assets, no tags
        self.assertEqual([], self.fetch_names())

        # Only private tag of others
        admin = self.create_user('administrator')
        self.generate_assets(['asset'], creator=admin, tags=['tag'])
        self.assertEqual([], self.fetch_names())

        # Asset without tags
        self.generate_assets(['asset'])
        self.assertEqual([], self.fetch_names())

    def test_global_and_personal_tags_are_accessible(self):
        # Global tags
        admin = self.create_user('administrator')
        self.generate_assets(['0'], creator=admin, is_global=True,
                             tags=['global', 'by_admin'])
        self.generate_assets(['1'], creator=admin, is_global=True,
                             tags=['blue', 'by_admin'])

        # Personal tags
        self.generate_assets(['2', '3'], tags=['blue', 'personal'])
        self.generate_assets(['4'])
        self.generate_assets(['5'], tags=['red'])

        tags = set(self.fetch_names())
        expected = set(['global', 'by_admin', 'blue', 'personal', 'red'])
        self.assertEqual(expected, tags)

    def test_cant_see_others_tags(self):
        self.generate_assets(['0', '1'], tags=['tag', 'A'])

        foouser_a = self.create_user('foouser_a')
        self.generate_assets(['2', '3'], creator=foouser_a, tags=['foo', 'A'])

        foouser_b = self.create_user('foouser_b')
        self.generate_assets(['4', '5'], creator=foouser_b, tags=['foo', 'B'])

        tags = self.fetch_names()

        self.assertIn('tag', tags)
        # Shared 'A' tag is returned
        self.assertIn('A', tags)
        # Private tags
        self.assertNotIn('foo', tags)
        self.assertNotIn('B', tags)


class ImagesApiTestCase(AssetTestsMixin, UploadTestsMixin,
                        AssetResourceTestCase):
    resource = 'images'
    extension = 'JpEg'

    def setUp(self):
        super(ImagesApiTestCase, self).setUp()
        self.test_file = get_fixture_path('TEST_IMAGE.jpeg')

    def create_asset(self):
        test_image = File(open(self.test_file))
        return models.ImageAsset(name='New Image', image=test_image)

    def test_has_required_fields(self):
        self.generate_assets(['image'])
        image = self.fetch_json()['objects'][0]
        fields = set(image.keys())
        expected = set([
            'id', 'name', 'description', 'size', 'width', 'height',
            'thumbnail', 'date_created', 'date_modified', 'select_url'])
        self.assertEqual(expected, fields)

    def test_provide_extensions(self):
        self.generate_assets(['image'])
        meta = self.fetch_json()['meta']
        self.assertEqual(set(['JPEG']), set(meta['extensions']))

    def test_filter_by_extension(self):
        self.generate_assets(['image'])
        self.assertEqual(['image'], self.fetch_names(extension='JPEG'))
        self.assertEqual([], self.fetch_names(extension='PNG'))

    def test_extension_filter_is_case_insensitive(self):
        self.generate_assets(['image'])
        self.assertEqual(['image'], self.fetch_names(extension='JPEG'))
        self.assertEqual(['image'], self.fetch_names(extension='JpEg'))
        self.assertEqual(['image'], self.fetch_names(extension='jpeg'))

    def test_uploading_fake_image(self):
        filename = get_fixture_path('fake_image.jpg')
        url = get_url(self.resource)
        with open(filename) as fp:
            data = {
                'destination': 'email/1/1',
                'file': fp,
            }
            response = self.client.post(url, data)
        self.assertEqual(400, response.status_code)
        self.assertEqual(0, len(self.fetch_names()))

    @override_settings(ASSET_IMAGE_EXTENSIONS=['XXX'])
    def test_accept_only_allowed_exceptions(self):
        url = get_url(self.resource)

        # Reject extension
        with open(self.test_file) as fp:
            response = self.client.post(url, {
                'file': fp,
                'destination': 'email/1/1',
            })
        self.assertEqual(400, response.status_code)

        # Allow extension
        settings.ASSET_IMAGE_EXTENSIONS.append(self.extension)
        with open(self.test_file) as fp:
            response = self.client.post(url, {
                'file': fp,
                'destination': 'email/1/1',
            })
        self.assertEqual(200, response.status_code)


class FilesApiTestCase(AssetTestsMixin, UploadTestsMixin,
                       AssetResourceTestCase):
    resource = 'files'
    extension = 'TxT'

    def setUp(self):
        super(FilesApiTestCase, self).setUp()
        self.test_file = get_fixture_path('TEST_FILE.txt')

    def create_asset(self):
        file_obj = File(open(self.test_file))
        return models.FileAsset(name='New File', file=file_obj)

    def test_has_required_fields(self):
        self.generate_assets(['file'])
        file_asset = self.fetch_json()['objects'][0]
        fields = set(file_asset.keys())
        expected = set([
            'id', 'name', 'description', 'filename', 'thumbnail_url', 'size',
            'extension', 'date_created', 'date_modified', 'select_url'])
        self.assertEqual(expected, fields)

    def test_filename(self):
        self.generate_assets(['file'])
        file_asset = self.fetch_json()['objects'][0]
        self.assertEqual('TEST_FILE.txt', file_asset['filename'])

    def test_provide_extensions(self):
        self.generate_assets(['file'])
        meta = self.fetch_json()['meta']
        self.assertEqual(set(['TXT']), set(meta['extensions']))

    def test_filter_by_extension(self):
        self.generate_assets(['file'])
        self.assertEqual(['file'], self.fetch_names(extension='TXT'))
        self.assertEqual([], self.fetch_names(extension='PDF'))

    def test_extension_filter_is_case_insensitive(self):
        self.generate_assets(['file'])
        self.assertEqual(['file'], self.fetch_names(extension='TXT'))
        self.assertEqual(['file'], self.fetch_names(extension='tXt'))
        self.assertEqual(['file'], self.fetch_names(extension='txt'))

    def test_accept_only_allowed_exceptions(self):
        old_setting = settings.ASSET_FILE_EXTENSIONS
        url = get_url(self.resource)

        # Reject extension
        settings.ASSET_FILE_EXTENSIONS = ['XXX']
        with open(self.test_file) as fp:
            response = self.client.post(url, {
                'file': fp,
                'destination': 'email/1/1',
            })
        self.assertEqual(400, response.status_code)

        # Allow extension
        settings.ASSET_FILE_EXTENSIONS.append(self.extension)
        with open(self.test_file) as fp:
            response = self.client.post(url, {
                'file': fp,
                'destination': 'email/1/1',
            })
        self.assertEqual(200, response.status_code)

        settings.ASSET_FILE_EXTENSIONS = old_setting


class SnippetsApiTestCase(AssetTestsMixin, AssetResourceTestCase):
    resource = 'snippets'

    def create_asset(self):
        return models.SnippetAsset(name="Generated Snippet")

    def test_has_required_fields(self):
        self.generate_assets(['snippet'])
        snippet = self.fetch_json()['objects'][0]
        fields = set(snippet.keys())
        expected = set([
            'id', 'name', 'description', 'length', 'contents', 'date_created',
            'date_modified'])
        self.assertEqual(expected, fields)

    def test_has_correct_length(self):
        test_strings = ['A', 'Sample string', 'A rather longer sample string']
        for string in test_strings:
            models.SnippetAsset.objects.create(
                name=string, contents=string, creator=self.user)

        for snippet in self.fetch_json()['objects']:
            self.assertIn(snippet['contents'], test_strings)
            self.assertEqual(len(snippet['contents']), snippet['length'])


class ImageDetailApiTestCase(ResourceDetailMixin, AssetResourceTestCase):
    resource = 'images'

    def create_asset(self):
        test_image = File(open(get_fixture_path('TEST_IMAGE.jpeg')))
        return models.ImageAsset(name='New Image', image=test_image)


class FileDetailApiTestCase(ResourceDetailMixin, AssetResourceTestCase):
    resource = 'files'

    def create_asset(self):
        test_file = get_fixture_path('TEST_FILE.txt')
        file_obj = File(open(test_file))
        return models.FileAsset(name='New File', file=file_obj)


class TestImageEditor(LogInMixin, AssetResourceTestCase):
    ORIG_WIDTH, ORIG_HEIGHT = 230, 219

    def setUp(self):
        super(TestImageEditor, self).setUp()
        test_file = get_fixture_path('TEST_IMAGE.jpeg')
        test_image = File(open(test_file))
        image = models.ImageAsset(name='New Image', image=test_image,
                                  creator=self.user)
        image.save()
        self.image_url = image.image.url

    def post_data(self, data, absolute_src=True, *args, **kwargs):
        """ Post data to server

        :param absolute_src: Convert src into absolute path on disk
            instead of uri
        """
        url = get_url('images', 'transformations')
        raw_response = self.client.post(url, data)
        self.assertEqual(200, raw_response.status_code)
        response = json.loads(raw_response.content)
        self.assertIn('src', response)
        self.assertIn('width', response)
        self.assertIn('height', response)
        self.assertNotEqual(self.image_url, response['src'])
        if absolute_src:
            response['src'] = media_uri_to_path(response['src'], absolute=True)
        return response

    def test_fail_with_none_path(self):
        url = get_url('images', 'transformations')
        raw_response = self.client.post(url, {
            'transformation': 'grayscale'})
        self.assertEqual(400, raw_response.status_code)

    def test_non_existing_path(self):
        url = get_url('images', 'transformations')
        raw_response = self.client.post(url, {
            'src': 'non-existing.jpeg',
            'transformation': 'grayscale'})
        self.assertEqual(400, raw_response.status_code)

    def test_unknown_transformation(self):
        url = get_url('images', 'transformations')
        raw_response = self.client.post(url, {
            'src': self.image_url,
            'transformation': 'more-unicorns!'})
        self.assertEqual(400, raw_response.status_code)

    def test_crop(self):
        response = self.post_data({
            'src': self.image_url,
            'transformation': 'crop',
            'x1': 10,
            'y1': 20,
            'x2': 100,
            'y2': 120,
        })
        width, height = Image.open(response['src']).size
        self.assertEqual(90, width)
        self.assertEqual(100, height)
        self.assertEqual(width, response['width'])
        self.assertEqual(height, response['height'])

    def test_crop_with_zero_coords(self):
        response = self.post_data({
            'src': self.image_url,
            'transformation': 'crop',
            'x1': 0,
            'y1': 0,
            'x2': 100,
            'y2': 100,
        })
        width, height = Image.open(response['src']).size
        self.assertEqual(100, width)
        self.assertEqual(100, height)
        self.assertEqual(width, response['width'])
        self.assertEqual(height, response['height'])

    def test_grayscale(self):
        response = self.post_data({
            'src': self.image_url,
            'transformation': 'grayscale',
        })
        width, height = Image.open(response['src']).size
        self.assertEqual(self.ORIG_WIDTH, width)
        self.assertEqual(self.ORIG_HEIGHT, height)
        self.assertEqual(width, response['width'])
        self.assertEqual(height, response['height'])

    def test_return_absolute_uri(self):
        response = self.post_data({
            'src': self.image_url,
            'transformation': 'grayscale',
        }, absolute_src=False)
        src = response['src']
        self.assertTrue(
            src.startswith('http://') or src.startswith('https://'))

    def test_rotate_90degrees(self):
        response = self.post_data({
            'src': self.image_url,
            'transformation': 'rotate',
            'angle': 90,
        })
        width, height = Image.open(response['src']).size
        # Because rotation, dimensions are swaped
        self.assertEqual(self.ORIG_HEIGHT, width)
        self.assertEqual(self.ORIG_WIDTH, height)
        self.assertEqual(width, response['width'])
        self.assertEqual(height, response['height'])

    def test_rotate_180degrees(self):
        response = self.post_data({
            'src': self.image_url,
            'transformation': 'rotate',
            'angle': 180,
        })
        width, height = Image.open(response['src']).size
        # Dimensions are same (but image is swapped)
        self.assertEqual(self.ORIG_WIDTH, width)
        self.assertEqual(self.ORIG_HEIGHT, height)
        self.assertEqual(width, response['width'])
        self.assertEqual(height, response['height'])
