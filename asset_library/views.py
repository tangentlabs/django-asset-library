from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse_lazy, reverse
from django.db.models import get_model, Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import ListView, CreateView, DetailView, \
    UpdateView, DeleteView, FormView, View

from . import forms

User = get_model('auth', 'User')
Tag = get_model('asset_library', 'Tag')
Asset = get_model('asset_library', 'Asset')
ImageAsset = get_model('asset_library', 'ImageAsset')
SnippetAsset = get_model('asset_library', 'SnippetAsset')
FileAsset = get_model('asset_library', 'FileAsset')


#######################
# Abstract asset views
#######################


class AssetListView(ListView):
    context_object_name = 'assets'
    template_name = 'asset_library/library_list.html'
    form_class = forms.FilterAssetsForm
    base_url = reverse_lazy('asset_library:library_list')
    paginate_by = 10

    def get(self, request):
        self.form = self.form_class(request.GET)
        if self.form.is_valid():
            return super(AssetListView, self).get(request)
        else:
            messages.error(request, "Invalid filtering options")
            return redirect(self.base_url)

    def get_queryset(self):
        """ Apply filters based on filtering form """
        return self.form.get_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super(AssetListView, self).get_context_data(**kwargs)
        ctx['form'] = self.form
        ctx['params'] = self.form.cleaned_data

        user = self.request.user

        # All assets, not only paginated
        assets = self.form.apply_source(Asset.objects.all(), user)
        # Related tags to those assets
        tags = Tag.objects.filter(assets__pk__in=assets)
        # Get usage count and order by names
        ctx['tags'] = tags.annotate(count=Count('pk')).order_by('name')
        ctx['untagged_count'] = assets.filter(tags=None).count()

        # Asset types that can be used
        ctx['images_enabled'] = settings.ASSET_IMAGES
        ctx['files_enabled'] = settings.ASSET_FILES
        ctx['snippets_enabled'] = settings.ASSET_SNIPPETS

        ctx['can_edit_global_image'] = (
            user.has_perm(ImageAsset.GLOBAL_PERMISSION))
        ctx['can_edit_global_file'] = (
            user.has_perm(FileAsset.GLOBAL_PERMISSION))
        ctx['can_edit_global_snippet'] = (
            user.has_perm(SnippetAsset.GLOBAL_PERMISSION))

        return ctx

    def get_paginate_by(self, queryset):
        """
        Paginate by specified value in querystring, or use default class
        property value.
        """
        return self.request.GET.get('paginateby', self.paginate_by)


class AssetUploadFileView(View):

    def get(self, request):
        messages.error(request, _("Missing file for file upload"))
        return HttpResponseRedirect(reverse('asset_library:library_list'))

    def post(self, request):
        """ Try to determine the type of asset: image or file asset """
        asset = None
        # Is the file image?
        image_form = forms.UploadImageForm(request.POST, files=request.FILES)
        if image_form.is_valid():
            image = image_form.cleaned_data['file']
            asset = ImageAsset.objects.create(
                name=image.name, creator=request.user, image=image)

        # Is the file at least allowed file asset?
        file_form = forms.UploadFileForm(request.POST, files=request.FILES)
        if not asset and file_form.is_valid():
            file = file_form.cleaned_data['file']
            asset = FileAsset.objects.create(
                name=file.name, creator=request.user, file=file)

        if asset:
            # Redirect to edit mode
            messages.info(
                request, _("A new asset '%s' was created") % asset.name)
            return HttpResponseRedirect(asset.get_update_url())
        else:
            # Error message
            messages.error(request, _("That type of file is not allowed"))
            return HttpResponseRedirect(reverse('asset_library:library_list'))


class AssetCreateView(CreateView):
    context_object_name = 'asset'
    template_name = 'asset_library/library_create.html'
    success_url = reverse_lazy('asset_library:library_list')

    def get_form_kwargs(self):
        """ Pass user into form """
        kwargs = super(AssetCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class AssetDetailView(DetailView):
    context_object_name = 'asset'

    def get_queryset(self):
        return self.model.objects.filter(
            Q(creator=self.request.user, is_global=False) | Q(is_global=True))


class AssetUpdateView(UpdateView):
    context_object_name = 'asset'
    success_url = reverse_lazy('asset_library:library_list')

    def get_form_kwargs(self):
        """ Pass user into form """
        kwargs = super(AssetUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        """ Based on permissions allow only personal or personal and global
        assets """
        global_perm = self.request.user.has_perm(self.model.GLOBAL_PERMISSION)
        if global_perm:
            return self.model.objects.filter(
                Q(creator=self.request.user) |
                Q(is_global=True))
        else:
            return self.model.objects.filter(
                creator=self.request.user, is_global=False)

    def get_context_data(self, **kwargs):
        ctx = super(AssetUpdateView, self).get_context_data(**kwargs)
        global_edit_perm = ctx['asset'].GLOBAL_PERMISSION
        ctx['can_edit_globals'] = self.request.user.has_perm(global_edit_perm)
        return ctx

    def form_valid(self, form):
        response = super(AssetUpdateView, self).form_valid(form)
        messages.info(
            self.request,
            _('The asset details have been updated.'))
        return response


class AssetDeleteView(DeleteView):
    context_object_name = 'asset'
    success_url = reverse_lazy('asset_library:library_list')

    def get_queryset(self):
        """ Based on permissions allow only personal or personal and global
        assets """
        global_perm = self.request.user.has_perm(self.model.GLOBAL_PERMISSION)
        if global_perm:
            return self.model.objects.filter(
                Q(creator=self.request.user) | Q(is_global=True))
        else:
            return self.model.objects.filter(
                creator=self.request.user, is_global=False)

    def delete(self, request, *args, **kwargs):
        response = super(AssetDeleteView, self).delete(
            request, *args, **kwargs)
        messages.info(self.request, _('Asset has been deleted!'))
        return response


class AssetShareView(FormView):
    form_class = forms.ShareAssetForm
    model = Asset
    template_name = 'asset_library/library_share.html'
    success_url = reverse_lazy('asset_library:library_list')
    view_name = None

    def get(self, request, pk, *args, **kwargs):
        self.asset = get_object_or_404(
            self.model, pk=pk, creator=request.user, is_global=False)
        return super(AssetShareView, self).get(request, *args, **kwargs)

    def post(self, request, pk, *args, **kwargs):
        self.asset = get_object_or_404(
            self.model, pk=pk, creator=self.request.user, is_global=False)
        return super(AssetShareView, self).post(request, *args, **kwargs)

    def get_form_kwargs(self):
        """ Pass user object to form """
        kwargs = super(AssetShareView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """ Share the asset """
        shared_with = form.cleaned_data['shared_with']
        self.asset.share(self.request.user, shared_with)

        messages.info(
            self.request,
            _('Asset was shared with user %s') % shared_with)
        return super(AssetShareView, self).form_valid(form)


class AssetAcceptView(View):
    def post(self, request, pk):
        asset = get_object_or_404(Asset, pk=pk, creator=request.user)
        asset.accept_shared()
        messages.info(
            request,
            _("Shared asset '%s' was accepted") % asset.name)
        return HttpResponseRedirect(reverse('asset_library:library_list'))


class AssetRejectView(View):
    def post(self, request, pk):
        asset = get_object_or_404(Asset, pk=pk, creator=request.user)
        asset.reject_shared()
        messages.info(
            request,
            _("Shared asset '%s' was rejected and deleted") % asset.name)
        return HttpResponseRedirect(reverse('asset_library:library_list'))

####################
# Image assets view
####################


class ImageCreateView(AssetCreateView):
    template_name = 'asset_library/image_create.html'
    model = ImageAsset
    form_class = forms.ImageAssetCreateForm


class ImageDetailView(AssetDetailView):
    template_name = 'asset_library/image_detail.html'
    model = ImageAsset


class ImageUpdateView(AssetUpdateView):
    template_name = 'asset_library/image_update.html'
    model = ImageAsset
    form_class = forms.ImageAssetForm


class ImageDeleteView(AssetDeleteView):
    template_name = 'asset_library/image_delete.html'
    model = ImageAsset


class ImageShareView(AssetShareView):
    model = ImageAsset
    view_name = 'asset_library:image_share'

#####################
# Snippet assets view
#####################


class SnippetCreateView(AssetCreateView):
    template_name = 'asset_library/snippet_create.html'
    model = SnippetAsset
    form_class = forms.SnippetAssetForm


class SnippetDetailView(AssetDetailView):
    template_name = 'asset_library/snippet_detail.html'
    model = SnippetAsset


class SnippetUpdateView(AssetUpdateView):
    template_name = 'asset_library/snippet_update.html'
    form_class = forms.SnippetAssetForm
    model = SnippetAsset


class SnippetDeleteView(AssetDeleteView):
    template_name = 'asset_library/snippet_delete.html'
    model = SnippetAsset


class SnippetShareView(AssetShareView):
    model = SnippetAsset
    view_name = 'asset_library:snippet_share'

####################
# File assets view
####################


class FileCreateView(AssetCreateView):
    template_name = 'asset_library/file_create.html'
    model = FileAsset
    form_class = forms.FileAssetCreateForm


class FileDetailView(AssetDetailView):
    template_name = 'asset_library/file_detail.html'
    model = FileAsset


class FileUpdateView(AssetUpdateView):
    template_name = 'asset_library/file_update.html'
    form_class = forms.FileAssetForm
    model = FileAsset


class FileDeleteView(AssetDeleteView):
    template_name = 'asset_library/file_delete.html'
    model = FileAsset


class FileShareView(AssetShareView):
    model = FileAsset
    view_name = 'asset_library:file_share'
