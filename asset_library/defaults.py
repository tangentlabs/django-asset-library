import os
location = lambda x: os.path.join(os.path.dirname(__file__), x)

ASSET_API_ROOT = '/asset-library/api/v2/'
ASSET_IMAGES = True
ASSET_SNIPPETS = True
ASSET_FILES = True

ASSET_IMAGE_THUMBNAIL_SIZE = '150x150'
ASSET_IMAGE_EXTENSIONS = [
    'BMP', 'GIF', 'IM', 'JPEG', 'JPG', 'MSP', 'PCX', 'PNG',
    'PPM', 'SPIDER', 'TIF', 'TIFF', 'XBM',
]

ASSET_FILE_THUMBNAILS_PATH = 'asset_library/file_icons/'
ASSET_FILE_EXTENSIONS = [
    'DOC', 'RTF', 'PDF', 'CSV', 'XLS', 'ZIP', 'EPS', 'JPEG',
]

ASSET_TEMPLATE_DIR = location('template/asset_library/')
