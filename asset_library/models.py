from .abstract_models import \
    AbstractTag, AbstractAsset, ImageMixin, FileMixin, SnippetMixin

"""
Asset library currently uses the following data model:

                 +--------------+
                 |     Tag      |
                 |              |
                 +------+-------+
                        |
                        |
                        |
                 +------+-------+
                 |    Asset     |
                 |              |
                 +------+-------+
                        |
                        |
                        |
       +----------------+-----------------+
       |                |                 |
       |                |                 |
       |                |                 |
+------+-------+ +------+-------+ +-------+------+
|  ImageAsset  | | SnippetAsset | |  FileAsset   |
|              | |              | |              |
+--------------+ +--------------+ +--------------+

Asset library uses multi-table inheritance instead of having 3 tables
(each asset type one) and 6 relationships with tags.
It is generally discouraged, see book Two Scoops of Django, Chapter 6.

Asset library takes advantage of the infrastructure. With multi-table
inheritance asset library can show all types of assets mixed together in same
way.
"""


class Tag(AbstractTag):
    pass


class Asset(AbstractAsset):
    pass


class ImageAsset(ImageMixin, Asset):
    pass


class SnippetAsset(SnippetMixin, Asset):
    pass


class FileAsset(FileMixin, Asset):
    pass
