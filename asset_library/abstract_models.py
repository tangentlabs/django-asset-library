import os
from PIL import Image

from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils.managers import InheritanceManager

from .validators import validate_file_extension, validate_image_extension
from .utils import get_extension

IMAGE_GLOBAL_PERMISSION = 'global_image_assets'
FILE_GLOBAL_PERMISSION = 'global_file_assets'
SNIPPET_GLOBAL_PERMISSION = 'global_snippet_assets'


class AbstractTag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name


class AbstractAsset(models.Model):
    name = models.CharField(max_length=255)
    tags = models.ManyToManyField('asset_library.Tag', related_name="assets")
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    description = models.TextField(_("Usage notes"), blank=True)
    creator = models.ForeignKey('auth.User')
    is_global = models.BooleanField(_("Is global?"), default=False)
    shared_by = models.ForeignKey('auth.User', related_name="shared_assets",
                                  null=True, blank=True)

    # When fetching assets, automatically downcast them
    objects = InheritanceManager()

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    @property
    def asset_type(self):
        """ Convenience access to the type of asset:
        either ImageAsset, FileAsset, or SnippetAsset """
        return self.__class__.__name__

    def _create_deep_copy(self, **kwargs):
        """ Create a deep copy of an asset (e.g. for sharing assets)

        Usual tricks how to do deep copies (e.g. model.pk = None; model.save())
        don't work here because of multi-table inheritance.

        Instead dig up list of fields and ignore primary keys (pk of model and
        asset_ptr used for multi-table inheritance). Tags have to be treated
        differently because it is a ManyToManyField.

        :param kwargs: Explicit initial values for fields values overwriting
        :returns: a deep copy of an asset
        """
        # Find actual model, i.e. ImageAsset, SnippetAsset, FileAsset, etc.
        model = type(self)
        # Fields worth copying
        fields = [field for field in model._meta.fields
                  if not field.primary_key]
        # Initial dictionary of field names and values
        initials = dict(
            (field.name, field.value_from_object(self))
            for field in fields
        )
        # Take extra care of tags as it is a ManyToMany field
        tags = kwargs.pop('tags', self.tags.all())
        # Let overwrite initials
        initials.update(kwargs)
        # Create a new asset
        asset = model.objects.create(**initials)
        asset.tags = tags
        return asset

    def share(self, shared_by, shared_with):
        """ Share asset

        DB schema requires that shared_with becomes creator (owner) of
        the asset and shared_by becomes shared_by field"""
        return self._create_deep_copy(creator=shared_with, shared_by=shared_by)

    def accept_shared(self):
        """ Move asset from inbox to standard assets """
        self.shared_by = None
        self.save()

    def reject_shared(self):
        """ Delete shared asset """
        self.delete()


class ImageMixin(models.Model):
    image = models.ImageField(upload_to='asset_library/images/',
                              width_field='width', height_field='height',
                              validators=[validate_image_extension])
    width = models.IntegerField()
    height = models.IntegerField()
    # Size of the image in bytes
    size = models.IntegerField()
    extension = models.CharField(max_length=50)
    # Copyright information
    copyright_holder = models.CharField(max_length=255, blank=True)
    copyright_date = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True
        permissions = (
            (IMAGE_GLOBAL_PERMISSION, "Can manage global image assets"),
        )

    GLOBAL_PERMISSION = "asset_library.%s" % IMAGE_GLOBAL_PERMISSION

    def save(self, *args, **kwargs):
        self.populate_fields()
        super(ImageMixin, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('asset_library:image_detail', args=[self.id])

    def get_update_url(self):
        return reverse('asset_library:image_update', args=[self.id])

    def get_share_url(self):
        return reverse('asset_library:image_share', args=[self.id])

    def get_delete_url(self):
        return reverse('asset_library:image_delete', args=[self.id])

    def get_accept_shared_url(self):
        return reverse('asset_library:image_accept', args=[self.id])

    def get_reject_shared_url(self):
        return reverse('asset_library:image_reject', args=[self.id])

    @property
    def path(self):
        """ Return path to the image """
        return self.image.path

    @property
    def url(self):
        """ Return url to the image """
        return self.image.url

    def get_extension(self):
        """ Return real image extension """
        im = Image.open(self.image)
        return im.format.upper()

    def populate_fields(self):
        """ Set derived fields extensions & size """
        if not self.extension:
            self.extension = self.get_extension()
        if not self.size:
            self.size = self.image.size


class SnippetMixin(models.Model):
    contents = models.TextField()

    class Meta:
        abstract = True
        permissions = (
            (SNIPPET_GLOBAL_PERMISSION, "Can manage global snippet assets"),
        )

    GLOBAL_PERMISSION = "asset_library.%s" % SNIPPET_GLOBAL_PERMISSION

    def get_absolute_url(self):
        return reverse('asset_library:snippet_detail', args=[self.id])

    def get_update_url(self):
        return reverse('asset_library:snippet_update', args=[self.id])

    def get_share_url(self):
        return reverse('asset_library:snippet_share', args=[self.id])

    def get_delete_url(self):
        return reverse('asset_library:snippet_delete', args=[self.id])

    def get_accept_shared_url(self):
        return reverse('asset_library:snippet_accept', args=[self.id])

    def get_reject_shared_url(self):
        return reverse('asset_library:snippet_reject', args=[self.id])


class FileMixin(models.Model):
    file = models.FileField(
        upload_to='asset_library/files/',
        validators=[validate_file_extension])
    # Size of the file in bytes
    size = models.IntegerField()
    extension = models.CharField(max_length=50)

    class Meta:
        abstract = True
        permissions = (
            (FILE_GLOBAL_PERMISSION, "Can manage global file assets"),
        )

    GLOBAL_PERMISSION = "asset_library.%s" % FILE_GLOBAL_PERMISSION

    def save(self, *args, **kwargs):
        self.populate_fields()
        super(FileMixin, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('asset_library:file_detail', args=[self.id])

    def get_update_url(self):
        return reverse('asset_library:file_update', args=[self.id])

    def get_share_url(self):
        return reverse('asset_library:file_share', args=[self.id])

    def get_delete_url(self):
        return reverse('asset_library:file_delete', args=[self.id])

    def get_accept_shared_url(self):
        return reverse('asset_library:file_accept', args=[self.id])

    def get_reject_shared_url(self):
        return reverse('asset_library:file_reject', args=[self.id])

    @property
    def path(self):
        """ Return path to the file """
        return self.file.path

    @property
    def url(self):
        """ Return url to the file """
        return self.file.url

    @property
    def thumbnail_url(self):
        """ URL of icon representing file """
        base_path = settings.ASSET_FILE_THUMBNAILS_PATH
        default_thumbnail = base_path + 'default.png'

        thumbnail = base_path + self.extension.lower() + '.png'
        thumbnail_path = finders.find(thumbnail)

        if not thumbnail_path or not os.path.exists(thumbnail_path):
            thumbnail = default_thumbnail

        return staticfiles_storage.url(thumbnail)

    def populate_fields(self):
        """ Set derived fields extensions & size """
        if not self.extension:
            self.extension = get_extension(self.file.name)
        if not self.size:
            self.size = self.file.size
