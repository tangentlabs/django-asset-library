from django.conf import settings
from django.conf.urls import url, patterns, include
from django.contrib.auth.decorators import login_required


from . import api, views


class AssetLibraryApplication(object):
    name = 'asset_library'
    api_version = 2

    # Common list for all assets
    library_list = views.AssetListView
    library_upload = views.AssetUploadFileView
    library_accept = views.AssetAcceptView
    library_reject = views.AssetRejectView

    # Image assets
    image_create = views.ImageCreateView
    image_detail = views.ImageDetailView
    image_update = views.ImageUpdateView
    image_delete = views.ImageDeleteView
    image_share = views.ImageShareView

    # Snippet assets
    snippet_create = views.SnippetCreateView
    snippet_detail = views.SnippetDetailView
    snippet_update = views.SnippetUpdateView
    snippet_delete = views.SnippetDeleteView
    snippet_share = views.SnippetShareView

    # File assets
    file_create = views.FileCreateView
    file_detail = views.FileDetailView
    file_update = views.FileUpdateView
    file_delete = views.FileDeleteView
    file_share = views.FileShareView

    # API resources
    tag_resource = api.TagResource
    user_resource = api.UserResource
    image_list_resource = api.ImageListResource
    image_detail_resource = api.ImageDetailResource
    snippet_list_resource = api.SnippetListResource
    file_list_resource = api.FileListResource
    file_detail_resource = api.FileDetailResource
    image_editor = api.ImageEditor

    def __init__(self, app_name=None, **kwargs):
        self.app_name = app_name
        # Set all kwargs as object attributes
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

    @property
    def api(self):
        urlpatterns = patterns(
            '',
            url(r'^users/$', self.user_resource.as_view()),
            url(r'^tags/$', self.tag_resource.as_view()),
            url(r'^images/$', self.image_list_resource.as_view()),
            url(r'^images/(?P<pk>\d+)/$',
                self.image_detail_resource.as_view(), name='image_api_detail'),
            url(r'^images/transformations/$',
                self.image_editor.as_view(), name='image-editor'),
            url(r'^files/$', self.file_list_resource.as_view()),
            url(r'^files/(?P<pk>\d+)/$',
                self.file_detail_resource.as_view(), name='file_api_detail'),
            url(r'^snippets/$', self.snippet_list_resource.as_view()),
        )

        # Apply API login required decorator
        for pattern in urlpatterns:
            pattern._callback = api.api_login_required(pattern._callback)

        return urlpatterns

    @property
    def standalone(self):
        image_asset_urls = patterns(
            '',
            url(r'^images/create/$',
                self.image_create.as_view(), name='image_create'),
            url(r'^images/(?P<pk>\d+)/$',
                self.image_detail.as_view(), name='image_detail'),
            url(r'^images/(?P<pk>\d+)/edit/$',
                self.image_update.as_view(), name='image_update'),
            url(r'^images/(?P<pk>\d+)/delete/$',
                self.image_delete.as_view(), name='image_delete'),
            url(r'^images/(?P<pk>\d+)/share/$',
                self.image_share.as_view(), name='image_share'),
            url(r'^images/(?P<pk>\d+)/accept/$',
                self.library_accept.as_view(), name='image_accept'),
            url(r'^images/(?P<pk>\d+)/reject/$',
                self.library_reject.as_view(), name='image_reject'),
        )

        snippet_asset_urls = patterns(
            '',
            url(r'^snippets/create/$',
                self.snippet_create.as_view(), name='snippet_create'),
            url(r'^snippets/(?P<pk>\d+)/$',
                self.snippet_detail.as_view(), name='snippet_detail'),
            url(r'^snippets/(?P<pk>\d+)/edit/$',
                self.snippet_update.as_view(), name='snippet_update'),
            url(r'^snippets/(?P<pk>\d+)/delete/$',
                self.snippet_delete.as_view(), name='snippet_delete'),
            url(r'^snippets/(?P<pk>\d+)/share/$',
                self.snippet_share.as_view(), name='snippet_share'),
            url(r'^snippets/(?P<pk>\d+)/accept/$',
                self.library_accept.as_view(), name='snippet_accept'),
            url(r'^snippets/(?P<pk>\d+)/reject/$',
                self.library_reject.as_view(), name='snippet_reject'),
        )

        file_asset_urls = patterns(
            '',
            url(r'^files/create/$',
                self.file_create.as_view(), name='file_create'),
            url(r'^files/(?P<pk>\d+)/$',
                self.file_detail.as_view(), name='file_detail'),
            url(r'^files/(?P<pk>\d+)/edit/$',
                self.file_update.as_view(), name='file_update'),
            url(r'^files/(?P<pk>\d+)/delete/$',
                self.file_delete.as_view(), name='file_delete'),
            url(r'^files/(?P<pk>\d+)/share/$',
                self.file_share.as_view(), name='file_share'),
            url(r'^files/(?P<pk>\d+)/accept/$',
                self.library_accept.as_view(), name='file_accept'),
            url(r'^files/(?P<pk>\d+)/reject/$',
                self.library_reject.as_view(), name='file_reject'),
        )

        # Allow modularity for assets
        urls = patterns(
            '', url(r'^$', self.library_list.as_view(), name='library_list'),
        )
        if settings.ASSET_IMAGES or settings.ASSET_FILES:
            urls += patterns(
                '',
                url(r'^upload-file/$',
                    self.library_upload.as_view(), name="upload_file")
            )
        if settings.ASSET_IMAGES:
            urls += image_asset_urls
        if settings.ASSET_SNIPPETS:
            urls += snippet_asset_urls
        if settings.ASSET_FILES:
            urls += file_asset_urls

        # Require login for asset library
        for pattern in urls:
            pattern._callback = login_required(pattern._callback)

        return urls

    def get_urls(self):
        no_enabled_assets = not settings.ASSET_IMAGES and \
            not settings.ASSET_SNIPPETS and \
            not settings.ASSET_FILES
        if no_enabled_assets:
            # Completely disable asset library
            return patterns('')

        # Standalone goes to /, api under api/vN/
        standalone = self.standalone
        api = patterns(
            '', url('api/v%d/' % self.api_version, include(self.api)),
        )
        return standalone + api

    @property
    def urls(self):
        """ Set application and instance namespace """
        return self.get_urls(), self.app_name, self.name


application = AssetLibraryApplication()
