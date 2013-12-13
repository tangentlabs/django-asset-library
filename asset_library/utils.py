from urlparse import urlparse, urljoin
import base64
import errno
import logging
import os
import shutil
from uuid import uuid4

from sorl.thumbnail import get_thumbnail

from django.conf import settings
from django.db.models import get_model
from django.utils._os import safe_join

ImageAsset = get_model('asset_library', 'ImageAsset')
Tag = get_model('asset_library', 'Tag')

logger = logging.getLogger(__name__)


def clean_images(image_urls, image_paths):
    """
    Cleans all images from images_path which are not in image_urls list
    """

    images_dir = os.path.join(settings.MEDIA_ROOT, image_paths)
    if not os.path.exists(images_dir):
        return
    image_urls = [urlparse(u.strip()).path for u in image_urls]
    images_url_path = urljoin(settings.MEDIA_URL, image_paths)
    image_urls = [u for u in image_urls if u.startswith(images_url_path)]
    dir_images = [
        os.path.join(image_paths, f)
        for f in os.listdir(images_dir)
        if os.path.isfile(os.path.join(images_dir, f))
    ]
    image_urls = [media_uri_to_path(u, False) for u in image_urls]
    images_to_clean = [i for i in dir_images if i not in image_urls]
    for image in images_to_clean:
        remove_image(image)


def copy_media_file(file_relative_path, copy_filename):
    def _get_str_uuid():
        r_uuid = base64.urlsafe_b64encode(uuid4().bytes)
        return r_uuid.replace('=', '')

    file_path = settings.MEDIA_ROOT + file_relative_path
    ext = os.path.splitext(file_path)[1]

    unique_filename = _get_str_uuid()

    rel_new_file_path = copy_filename + unique_filename + ext
    full_new_file_path = settings.MEDIA_ROOT + rel_new_file_path

    new_dir = os.path.dirname(full_new_file_path)
    if not os.path.exists(new_dir):
        os.makedirs(new_dir)

    shutil.copyfile(file_path, full_new_file_path)

    return rel_new_file_path


def thumbnail(image, geometry):
    format = 'PNG' if image.lower().endswith('.png') else 'JPEG'
    return get_thumbnail(image, geometry, format=format)


def remove_image(image):
    path = os.path.join(settings.MEDIA_ROOT, image)
    if os.path.exists(path):
        os.remove(path)


def media_uri_to_path(url, absolute=False):
    """ Resolve Image URL to file path to image """
    path = urlparse(url.strip()).path
    if path.startswith(settings.MEDIA_URL):
        path = path[len(settings.MEDIA_URL):]
    if absolute:
        path = os.path.join(settings.MEDIA_ROOT, path)
    return path


def path_to_media_uri(path):
    """ Convert path to image url (inside MEDIA_ROOT) """
    assert path.startswith(settings.MEDIA_ROOT)
    path = path[len(settings.MEDIA_ROOT):].lstrip('/')
    return os.path.join(settings.MEDIA_URL, path)


def create_copy_name(path):
    """ Return name of new version of the file

    The current implementation returns UUID name with preserved extension.
    """
    file_dir, file_name = os.path.split(path)
    __, extension = os.path.splitext(file_name)
    base_name = str(uuid4()).replace('-', '')
    file_name = base_name + extension
    return os.path.join(file_dir, file_name)


def copy_to_campaign(filepath, destination):
    """ Copy file to campaign directory

    :param filepath: path to file to which be copied
    :param destination: campaign directory where file should be copied
    :returns:
    :param real_path: Path that OS accepts for copying, e.g
    :returns: URL to copied filed
    """
    original_basename = os.path.basename(filepath)
    directory = safe_join(settings.MEDIA_ROOT, destination)
    proposed_path = os.path.join(directory, original_basename)
    final_destination = create_copy_name(proposed_path)
    base_name = os.path.basename(final_destination)
    media_url = safe_join(settings.MEDIA_URL, destination, base_name)

    try:
        os.makedirs(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.exception("Failed to create a directory [%s]" % directory)
            raise

    shutil.copyfile(filepath, final_destination)
    return media_url


def get_extension(filename):
    """ Return uppercased extension of file
    Example of transformation: 'image.jpg' => '.jpg' => 'jpg' """
    extension_with_dot = os.path.splitext(filename)[1]
    return extension_with_dot[1:].upper()
