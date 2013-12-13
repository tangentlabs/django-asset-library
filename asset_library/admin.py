from django.contrib import admin
from .models import Tag, ImageAsset, SnippetAsset, FileAsset

admin.site.register(Tag)
admin.site.register(ImageAsset)
admin.site.register(SnippetAsset)
admin.site.register(FileAsset)
