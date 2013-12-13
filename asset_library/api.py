from PIL import Image
from PIL import ImageOps
import json
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import reverse
from django.db.models import get_model
from django.db.models.query_utils import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.generic.base import View

from . import forms
from .utils import thumbnail, copy_to_campaign, \
    path_to_media_uri, create_copy_name

Tag = get_model('asset_library', 'Tag')
ImageAsset = get_model('asset_library', 'ImageAsset')
FileAsset = get_model('asset_library', 'FileAsset')
SnippetAsset = get_model('asset_library', 'SnippetAsset')
User = get_model('auth', 'User')


def api_login_required(view_func):
    """ Make sure the user is authenticated to access API.

    Instead of Django's standard login_required which 302 redirect to login
    page, return 401 - authentication required code """
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponse('Not authorized', status=401)
    return _wrapped_view


def JsonResponse(response, **kwargs):
    """  Return JSON response """
    json_dump = json.dumps(response, cls=DjangoJSONEncoder)
    return HttpResponse(json_dump, mimetype="application/json", **kwargs)


class Resource(View):
    fields = None

    def serialize_asset(self, asset):
        """ Serialize object to dictionary based on fields parameter """
        return {field: getattr(asset, field) for field in self.fields}


class DetailResource(Resource):
    def get(self, request, pk):
        asset = get_object_or_404(self.model, pk=pk)
        return JsonResponse({'object': self.serialize_asset(asset)})

    def post(self, request, pk):
        asset = get_object_or_404(self.model, pk=pk)
        form = forms.SelectFileAPIForm(request.POST)
        if form.is_valid():
            destination = form.cleaned_data['destination']
            campaign_copy = copy_to_campaign(asset.path, destination)
            absolute_campaign_copy = request.build_absolute_uri(campaign_copy)
            return JsonResponse({'campaign_copy': absolute_campaign_copy})
        else:
            return HttpResponseBadRequest('Correct destination required')


class AssetListResource(Resource):
    """ Provide listing feature """
    queryset = None
    form_class = forms.FilterAPIForm
    per_page = 20
    max_per_page = 100

    def get_response_data(self, request):
        """ Construct data used for response

        Fetch assets via get_queryset and use paginator on them """
        asset_list = self.form.get_queryset(request.user, self.queryset)

        if self.form.cleaned_data['limit']:
            per_page = min(self.form.cleaned_data['limit'], self.max_per_page)
        else:
            per_page = self.per_page

        paginator = Paginator(asset_list, per_page)
        page = self.form.cleaned_data['page']
        try:
            assets = paginator.page(page)
        except PageNotAnInteger:
            page = 1
            assets = paginator.page(page)
        except EmptyPage:
            assets = []

        response = {'objects': [], 'meta': {}}
        response['objects'] = [self.serialize_asset(asset) for asset in assets]
        response['meta'] = {
            'page': page,
            'limit': per_page,
            'num_pages': paginator.num_pages,
        }
        return response

    def get(self, request):
        self.form = self.form_class(request.GET)
        if not self.form.is_valid():
            return HttpResponseBadRequest('Invalid parameters')
        response = self.get_response_data(request)
        return JsonResponse(response)


class FileBasedAsset(object):
    form_class = forms.FileFilterAPIForm
    upload_form_class = None

    def get_response_data(self, request):
        response = super(FileBasedAsset, self).get_response_data(request)
        extensions = self.form.get_used_extensions(self.queryset, request.user)
        response['meta']['extensions'] = extensions
        return response

    def post(self, request):
        """ Upload a new file """
        form = self.upload_form_class(request.POST, files=request.FILES)
        if not form.is_valid():
            return HttpResponseBadRequest(
                'Malformed request\n%s' % form.errors)

        asset = self.create_asset(request.user, form.cleaned_data['file'])
        asset.populate_fields()
        try:
            asset.full_clean()
        except ValidationError, e:
            return HttpResponseBadRequest('Malformed request\n%s' % e)
        asset.save()

        asset_object = self.serialize_asset(asset)

        # Create a copy to campaign
        destination = form.cleaned_data['destination']
        campaign_copy = copy_to_campaign(asset.path, destination)
        absolute_campaign_copy = request.build_absolute_uri(campaign_copy)

        return JsonResponse({
            'object': asset_object,
            'campaign_copy': absolute_campaign_copy,
        })


class TagResource(View):
    """ Provide list of tags used in the system """

    def get(self, request):
        user = request.user
        global_or_users = Q(assets__creator=user) | Q(assets__is_global=True)
        tags = Tag.objects.filter(global_or_users).distinct()
        return JsonResponse({
            'objects': [{'id': tag.id, 'name': tag.name} for tag in tags]
        })


class UserResource(View):
    """ Provide list of users for autocompletion """
    LIMIT_RESULTS = 10

    def get_user_representation(self, user):
        name = '%s %s' % (user.first_name, user.last_name)
        if name.strip():
            return "%s (%s)" % (name, user.email)
        else:
            return user.email

    def _is_matched_user(self, user, search):
        """ Does user match the search query? """
        return search.lower() in self.get_user_representation(user).lower()

    def search(self, search):
        """ Search for people who are on the site

        Simple search in username, first_name, and last_name is not enough;
        when searching for "John Lu" won't find me "John Luke". Doing
        the search in a plain SQL command using concatenate would be easy, but
        it is DB specific.

        There is a nice workaround: Search by the first word of the search
        query. It filters down the list of potential users to a smaller amount.
        Run proper search on the set in Python.

        User set shouldn't be humongous and there is no need for special
        systems like Solr.

        :param user: User doing the search
        :param search: Search query
        :return: List of users satisfing the search query
        """
        users = User.objects.all()
        if search:
            first_word = search.split()[0]
            users = users.filter(
                Q(username__icontains=first_word) |
                Q(first_name__icontains=first_word) |
                Q(last_name__icontains=first_word))

            # Do python filtering
            users = [
                user for user in users
                if self._is_matched_user(user, search)
            ]

        return users[:self.LIMIT_RESULTS]

    def serialize(self, user):
        """ Return either full name or username """
        return {'id': user.id, 'name': self.get_user_representation(user)}

    def get(self, request):
        users = self.search(request.GET.get('search', ''))
        return JsonResponse({
            'objects': sorted([
                self.serialize(user) for user in users
                if user.pk != request.user.pk
            ]),
        })


class ImageListResource(FileBasedAsset, AssetListResource):
    queryset = ImageAsset.objects.all()
    upload_form_class = forms.UploadImageAPIForm
    fields = (
        'id', 'name', 'description', 'height', 'width', 'size',
        'date_created', 'date_modified')

    def serialize_asset(self, image):
        """ Create thumbnail """
        asset_dict = super(ImageListResource, self).serialize_asset(image)
        size = settings.ASSET_IMAGE_THUMBNAIL_SIZE
        asset_dict['thumbnail'] = thumbnail(image.image.name, size).url
        asset_dict['select_url'] = reverse('asset_library:image_api_detail',
                                           args=[image.pk])
        return asset_dict

    def create_asset(self, creator, uploaded_file):
        return ImageAsset(
            name=uploaded_file.name, creator=creator, image=uploaded_file)


class FileListResource(FileBasedAsset, AssetListResource):
    queryset = FileAsset.objects.all()
    upload_form_class = forms.UploadFileAPIForm
    fields = (
        'id', 'name', 'description', 'thumbnail_url', 'extension', 'size',
        'date_created', 'date_modified')

    def serialize_asset(self, file_asset):
        """ Add name of file without its path,
        e.g. /media/file.txt becomes file.txt """
        asset_dict = super(FileListResource, self).serialize_asset(file_asset)
        asset_dict['filename'] = os.path.basename(file_asset.file.name)
        asset_dict['select_url'] = reverse('asset_library:file_api_detail',
                                           args=[file_asset.pk])
        return asset_dict

    def create_asset(self, creator, uploaded_file):
        return FileAsset(
            name=uploaded_file.name, creator=creator, file=uploaded_file)


class SnippetListResource(AssetListResource):
    queryset = SnippetAsset.objects.all()
    fields = (
        'id', 'name', 'description', 'contents', 'date_created',
        'date_modified')

    def serialize_asset(self, snippet_asset):
        """ Add name of file without its path,
        e.g. /media/file.txt becomes file.txt """
        asset_dict = super(SnippetListResource, self).serialize_asset(
            snippet_asset)
        asset_dict['length'] = len(asset_dict['contents'])
        return asset_dict


class ImageDetailResource(DetailResource):
    model = ImageAsset
    fields = (
        'id', 'name', 'description', 'url', 'height', 'width', 'size',
        'date_created', 'date_modified')


class FileDetailResource(DetailResource):
    model = FileAsset
    fields = (
        'id', 'name', 'description', 'url', 'size', 'date_created',
        'date_modified')


class ImageEditor(View):
    """ ImageEditor provides the following filters to edit images:
    - crop
    - grayscale
    - rotate
     """
    def crop(self, image, x1, y1, x2, y2):
        """ Crop an image """
        return image.crop((x1, y1, x2, y2))

    def rotate(self, image, angle):
        """ Rotate an image """
        return image.rotate(-angle)

    def grayscale(self, image):
        """ Grayscale an image """
        if image.format == 'PNG':
            return image.convert('LA')
        else:
            return ImageOps.grayscale(image)

    def post(self, request):
        form = forms.ImageEditorAPIForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest(
                'Malformed request\n%s' % form.errors)

        path = form.cleaned_data['src']
        image = Image.open(path)
        if form.cleaned_data['transformation'] == form.CROP:
            x1, y1 = form.cleaned_data['x1'], form.cleaned_data['y1']
            x2, y2 = form.cleaned_data['x2'], form.cleaned_data['y2']
            image = self.crop(image, x1, y1, x2, y2)
        elif form.cleaned_data['transformation'] == form.ROTATE:
            angle = form.cleaned_data['angle']
            image = self.rotate(image, angle)
        elif form.cleaned_data['transformation'] == form.GRAYSCALE:
            image = self.grayscale(image)
        else:
            return HttpResponseBadRequest('Unknown transformation')

        result = create_copy_name(path)
        image.save(result, image.format)
        src = path_to_media_uri(result)
        width, height = image.size
        return JsonResponse({
            'src': request.build_absolute_uri(src),
            'width': width,
            'height': height,
        })
