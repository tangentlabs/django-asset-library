from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from asset_library.app import application

urlpatterns = patterns(
    '',
    url(r'^asset-library/', include(application.urls)),
    url(r'^admin/', include(admin.site.urls)),
)
