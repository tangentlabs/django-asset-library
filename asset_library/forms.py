import os

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import get_model
from django.db.models.query_utils import Q
from django.utils.translation import ugettext_noop as _

from .utils import media_uri_to_path
from .validators import validate_destination_path, validate_file_extension, \
    validate_image_extension

User = get_model('auth', 'User')
Tag = get_model('asset_library', 'Tag')
Asset = get_model('asset_library', 'Asset')
ImageAsset = get_model('asset_library', 'ImageAsset')
SnippetAsset = get_model('asset_library', 'SnippetAsset')
FileAsset = get_model('asset_library', 'FileAsset')


class AssetForm(forms.ModelForm):
    TAG_SEPARATOR = ','
    tags = forms.CharField(
        label=_("Space separated tags"), initial='', required=False)

    def __init__(self, user=None, *args, **kwargs):
        super(AssetForm, self).__init__(*args, **kwargs)
        self.user = user

        # Hide is_global for user with insufficient permissions
        if not user.has_perm(self.instance.GLOBAL_PERMISSION):
            self.fields['is_global'].widget = forms.HiddenInput()

        if hasattr(self.instance, "tags"):
            tag_names = (tag.name for tag in self.instance.tags.all())
        else:
            tag_names = []
        self.initial['tags'] = self.TAG_SEPARATOR.join(tag_names)

    def clean_tags(self):
        """ Parse tags into list """
        tag_list = self.cleaned_data.get('tags', '')
        return set(tag.strip() for tag in tag_list.split(self.TAG_SEPARATOR))

    def clean_is_global(self):
        """ Global flag can be set only by user with has enough permissions """
        is_global = self.cleaned_data.get('is_global', False)
        has_perm = self.user.has_perm(self.instance.GLOBAL_PERMISSION)
        if is_global and not has_perm:
            raise ValidationError('Insufficient permissions')
        return is_global

    def save(self, *args, **kwargs):
        """ Allow initial save and set tags field """
        instance = super(AssetForm, self).save(commit=False, *args, **kwargs)
        if not hasattr(self.instance, 'creator'):
            instance.creator = self.user
        instance.save()

        # Set tags
        instance.tags = [
            Tag.objects.get_or_create(name=tag_name)[0]
            for tag_name in self.cleaned_data.get('tags', []) if tag_name
        ]

        return instance


class ImageAssetCreateForm(AssetForm):
    class Meta:
        model = ImageAsset
        fields = ('name', 'image', 'description', 'is_global')


class ImageAssetForm(AssetForm):
    class Meta:
        model = ImageAsset
        fields = ('name', 'description', 'is_global')


class FileAssetCreateForm(AssetForm):
    class Meta:
        model = FileAsset
        fields = ('name', 'file', 'description', 'is_global')


class FileAssetForm(AssetForm):
    class Meta:
        model = FileAsset
        fields = ('name', 'description', 'is_global')


class SnippetAssetForm(AssetForm):
    class Meta:
        model = SnippetAsset
        fields = ('name', 'contents', 'description', 'is_global')


class ShareAssetForm(forms.Form):
    shared_with = forms.ModelChoiceField(
        widget=forms.TextInput, queryset=User.objects.all())

    def __init__(self, user=None, *args, **kwargs):
        super(ShareAssetForm, self).__init__(*args, **kwargs)
        self.user = user

    def clean_shared_with(self):
        """ Shared_with has to be different from user """
        shared_with = self.cleaned_data.get('shared_with')
        if shared_with.pk == self.user.pk:
            raise ValidationError("Can't share asset to yourself")
        return shared_with


class UploadImageForm(forms.Form):
    file = forms.ImageField(validators=[validate_image_extension])


class UploadFileForm(forms.Form):
    file = forms.FileField(validators=[validate_file_extension])


class FilterAssetsForm(forms.Form):
    INBOX, GLOBAL_ASSETS, YOUR_ASSETS = ('inbox', 'global', 'personal')
    SOURCES = (
        (YOUR_ASSETS, YOUR_ASSETS),
        (GLOBAL_ASSETS, GLOBAL_ASSETS),
        (INBOX, INBOX),
    )
    source = forms.ChoiceField(choices=SOURCES, widget=forms.HiddenInput,
                               initial=YOUR_ASSETS, required=False)

    IMAGE_TYPE, FILE_TYPE, SNIPPET_TYPE = ('images', 'files', 'snippets')
    ASSET_TYPES = (
        (IMAGE_TYPE, IMAGE_TYPE),
        (FILE_TYPE, FILE_TYPE),
        (SNIPPET_TYPE, SNIPPET_TYPE),
    )
    asset_type = forms.ChoiceField(choices=ASSET_TYPES,
                                   widget=forms.HiddenInput, required=False)

    GRID, TABLE = ("grid", "table")
    list_type = forms.ChoiceField(choices=((GRID, GRID), (TABLE, TABLE)),
                                  initial=GRID, widget=forms.HiddenInput,
                                  required=False)

    untagged = forms.NullBooleanField(widget=forms.HiddenInput, initial=False,
                                      required=False)
    tag = forms.ModelChoiceField(queryset=Tag.objects.all(),
                                 widget=forms.HiddenInput, required=False)

    search = forms.CharField(
        label=_("Search"), required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Search'}))

    SORT_NAME, SORT_NEW_FIRST, SORT_OLD_FIRST = (
        "name", "new_first", "old_first")

    SORT_OPTIONS = (
        (SORT_NAME, _("Name: A-Z")),
        (SORT_NEW_FIRST, _("Most recent first")),
        (SORT_OLD_FIRST, _("Oldest first")),
    )

    sortby = forms.ChoiceField(choices=SORT_OPTIONS, label=_("Sort By"),
                               initial=SORT_NAME, required=False)

    SORT_ASSET_NAME = "asset_name"
    SORT_EDITED = "edited"
    SORT_TABLE_OPTIONS = (
        (SORT_ASSET_NAME, SORT_ASSET_NAME),
        ('-' + SORT_ASSET_NAME, '-' + SORT_ASSET_NAME),
        (SORT_EDITED, SORT_EDITED),
        ('-' + SORT_EDITED, '-' + SORT_EDITED),
    )
    order_by = forms.ChoiceField(choices=SORT_TABLE_OPTIONS,
                                 widget=forms.HiddenInput, required=False)

    PAGINATE_STEP = 10
    PAGINATE_MAX = 50
    PAGINATE_STEP_OPTIONS = (
        (x, x) for x in range(PAGINATE_STEP, PAGINATE_MAX+1, PAGINATE_STEP)
    )

    paginateby = forms.ChoiceField(
        choices=PAGINATE_STEP_OPTIONS, label=_("Paginate By"),
        widget=forms.Select(attrs={'class': 'change-submit'}), required=False)

    def clean_list_type(self):
        """ Set default list type """
        list_type = self.cleaned_data.get('list_type')
        return list_type if list_type else self.fields['list_type'].initial

    def apply_source(self, queryset, user):
        """ Filter queryset by source """
        source = self.cleaned_data.get('source')
        if not source:
            # Without source show global and personal assets without inbox
            return queryset.filter(
                Q(is_global=True) | Q(creator=user), shared_by__isnull=True)
        elif source == self.INBOX:
            return queryset.filter(
                is_global=False, creator=user, shared_by__isnull=False)
        elif source == self.YOUR_ASSETS:
            # Show personal assets without shared assets
            return queryset.filter(
                is_global=False, creator=user, shared_by__isnull=True)
        else:
            return queryset.filter(is_global=True)

    def get_queryset(self, user):
        """ Get queryset based on parameters (filtering, sorting) """
        data = self.cleaned_data

        # Start with a new queryset specific to certain type
        if data['asset_type'] == self.IMAGE_TYPE:
            queryset = ImageAsset.objects.all()
            subclasses = ['imageasset']
            if not settings.ASSET_IMAGES:
                raise ValidationError("Images not enabled")
        elif data['asset_type'] == self.FILE_TYPE:
            queryset = FileAsset.objects.all()
            subclasses = ['fileasset']
            if not settings.ASSET_FILES:
                raise ValidationError("Files not enabled")
        elif data['asset_type'] == self.SNIPPET_TYPE:
            queryset = SnippetAsset.objects.all()
            subclasses = ['snippetasset']
            if not settings.ASSET_SNIPPETS:
                raise ValidationError("Snippets not enabled")
        else:
            # Limit allowed assets
            queryset = Asset.objects.all()
            subclasses = []
            if settings.ASSET_IMAGES:
                subclasses.append('imageasset')
            if settings.ASSET_SNIPPETS:
                subclasses.append('snippetasset')
            if settings.ASSET_FILES:
                subclasses.append('fileasset')
        queryset = queryset.select_subclasses(*subclasses)

        queryset = self.apply_source(queryset, user)

        if data['untagged']:
            queryset = queryset.filter(tags__isnull=True)
        elif data['tag']:
            queryset = queryset.filter(tags=data['tag'])

        if data['search']:
            queryset = queryset.filter(name__contains=data['search'])

        orderby = None
        if data['order_by']:
            if data['order_by'].startswith('-'):
                orderby = '-'
                data['order_by'] = data['order_by'][1:]
            else:
                orderby = ''

            if data['order_by'] == self.SORT_ASSET_NAME:
                orderby += 'name'
            elif data['order_by'] == self.SORT_EDITED:
                orderby += 'date_modified'
        else:
            if data['sortby'] == self.SORT_NAME:
                orderby = 'name'
            elif data['sortby'] == self.SORT_NEW_FIRST:
                orderby = '-date_created'
            elif data['sortby'] == self.SORT_OLD_FIRST:
                orderby = 'date_created'

        if orderby:
            queryset = queryset.order_by(orderby)

        return queryset


class FilterAPIForm(forms.Form):
    GLOBAL_ASSETS, YOUR_ASSETS = ('global', 'personal')
    SOURCES = (
        (YOUR_ASSETS, YOUR_ASSETS),
        (GLOBAL_ASSETS, GLOBAL_ASSETS),
    )
    source = forms.ChoiceField(choices=SOURCES, required=False)

    search = forms.CharField(required=False)
    without_tags = forms.BooleanField(required=False)
    tag = forms.ModelChoiceField(queryset=Tag.objects.all(), required=False)

    SORT_NAME, SORT_NEW_FIRST, SORT_OLD_FIRST = (
        "name", "newest_first", "oldest_first")

    SORT_OPTIONS = (
        (SORT_NAME, SORT_NAME),
        (SORT_NEW_FIRST, SORT_NEW_FIRST),
        (SORT_OLD_FIRST, SORT_OLD_FIRST),
    )
    sort_by = forms.ChoiceField(choices=SORT_OPTIONS, required=False)

    limit = forms.IntegerField(min_value=0, required=False)
    page = forms.IntegerField(min_value=0, required=False)

    def get_queryset(self, user, queryset):
        """ Get queryset based on parameters (filtering, sorting) """
        data = self.cleaned_data

        if data['sort_by'] == self.SORT_NEW_FIRST:
            queryset = queryset.order_by('-date_created')
        elif data['sort_by'] == self.SORT_OLD_FIRST:
            queryset = queryset.order_by('date_created')
        else:
            queryset = queryset.extra(select={
                'lower_name': 'lower("asset_library_asset"."name")'}
            ).order_by('lower_name')

        if data['source'] == self.GLOBAL_ASSETS:
            queryset = queryset.filter(is_global=True)
        elif data['source'] == self.YOUR_ASSETS:
            queryset = queryset.filter(
                creator=user, is_global=False, shared_by__isnull=True)
        else:
            # Show personal or global asset but not shared ones
            queryset = queryset.filter(
                Q(creator=user) | Q(is_global=True),
                shared_by__isnull=True)

        if data['search']:
            queryset = queryset.filter(name__icontains=data['search'])

        if data['without_tags']:
            queryset = queryset.filter(tags__isnull=True)
        elif data['tag']:
            queryset = queryset.filter(tags=data['tag'])

        return queryset


class FileFilterAPIForm(FilterAPIForm):
    extension = forms.CharField(required=False)

    def _build_extension_filter(self, extensions):
        """ Convert a comma-separated list of extensions in a filter """
        extension_filter = Q()
        for extension in extensions.split(','):
            extension = extension.strip()
            if extension:
                extension_filter |= Q(extension__iexact=extension)
        return extension_filter

    def get_queryset(self, user, queryset):
        queryset = super(FileFilterAPIForm, self).get_queryset(user, queryset)
        extensions = self.cleaned_data.get('extension')
        if extensions:
            extension_filter = self._build_extension_filter(extensions)
            queryset = queryset.filter(extension_filter)
        return queryset

    def get_used_extensions(self, queryset, user):
        # Find user's or system-wide assets
        assets = queryset.filter(Q(is_global=True) | Q(creator=user))

        # Don't display extensions that user can't use in this context
        extensions = self.cleaned_data.get('extension')
        if extensions:
            extension_filter = self._build_extension_filter(extensions)
            assets = assets.filter(extension_filter)

        extensions_queryset = assets.values('extension').distinct()
        return [ext['extension'] for ext in extensions_queryset]


class SelectFileAPIForm(forms.Form):
    destination = forms.CharField(validators=[validate_destination_path])

    def clean_destination(self):
        """ Convert destination from URI to absolute path """
        destination = self.cleaned_data['destination']
        return media_uri_to_path(destination)


class UploadFileAPIForm(SelectFileAPIForm):
    file = forms.FileField()


class UploadImageAPIForm(SelectFileAPIForm):
    # Check that image is actually image
    file = forms.ImageField()


class ImageEditorAPIForm(forms.Form):
    src = forms.CharField()
    CROP, ROTATE, GRAYSCALE = ('crop', 'rotate', 'grayscale')

    transformation = forms.ChoiceField(choices=(
        (CROP, CROP), (ROTATE, ROTATE), (GRAYSCALE, GRAYSCALE)))

    # Crop options
    x1 = forms.IntegerField(min_value=0, required=False)
    y1 = forms.IntegerField(min_value=0, required=False)
    x2 = forms.IntegerField(min_value=0, required=False)
    y2 = forms.IntegerField(min_value=0, required=False)

    # Rotation options
    angle = forms.IntegerField(required=False)

    def clean_src(self):
        """ Transform image URI into file path """
        src = self.cleaned_data['src']
        try:
            path = media_uri_to_path(src, True)
        except ValueError:
            path = None

        if not path or not os.path.exists(path):
            raise ValidationError("Not existing path")

        return path

    def clean_angle(self):
        """ Convert angle into range (0, 360) """
        angle = self.cleaned_data['angle']
        if angle:
            angle = angle % 360
        return angle

    def clean(self):
        """ Require parameters based on transformation """
        cleaned_data = super(ImageEditorAPIForm, self).clean()

        transformation = cleaned_data.get('transformation')
        if transformation == self.CROP:
            x1 = cleaned_data.get('x1')
            y1 = cleaned_data.get('y1')
            x2 = cleaned_data.get('x2')
            y2 = cleaned_data.get('y2')

            if x1 is None or y1 is None or x2 is None or y2 is None:
                msg = 'Required field'
                self._errors['x1'], self._errors['y1'] = msg, msg
                self._errors['x2'], self._errors['y2'] = msg, msg

        elif transformation == self.ROTATE:
            angle = cleaned_data.get('angle')
            if not angle:
                self._errors['angle'] = 'Required field'

        return cleaned_data
