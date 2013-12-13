import os
from PIL import Image

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils._os import safe_join


def validate_file_extension(file_obj):
    """ File extension must be in ASSET_FILE_EXTENSIONS """
    __, ext = os.path.splitext(file_obj.name)
    ext = ext.lstrip('.').upper()
    # uppercase every extension in setting
    for extension in settings.ASSET_FILE_EXTENSIONS:
        if ext == extension.upper():
            return

    raise ValidationError("Extension '%s' is not allowed" % ext)


def validate_image_extension(image):
    """ Real image extension must be in ASSET_IMAGE_EXTENSIONS """
    try:
        # PIL calls .read() on the image and by the nature, all following
        # .read() return no data .seek(0) resets the state of reading so
        # the validation doesn't change the status
        image.seek(0)
        im = Image.open(image)
    except IOError:
        raise ValidationError("Not an image")
    finally:
        # Reset image again
        image.seek(0)

    ext = im.format.upper()
    # uppercase every extension in setting
    for extension in settings.ASSET_IMAGE_EXTENSIONS:
        if ext == extension.upper():
            return

    raise ValidationError("Extension '%s' is not allowed" % ext)


def validate_destination_path(destination):
    """ Destination does not reach outside of MEDIA_ROOT and destination is
    in format /<asset_type>/<template_id>/<draft_id>/ """

    if destination.startswith(settings.MEDIA_URL):
        destination = destination[len(settings.MEDIA_URL):]

    try:
        safe_join(settings.MEDIA_ROOT, destination)
    except ValueError:
        raise ValidationError("Suspicious destination")

    try:
        asset_type, template_id, draft_id = destination.strip('/').split('/')
        template_id = int(template_id)
    except ValueError:
        raise ValidationError("Suspicious destination")
