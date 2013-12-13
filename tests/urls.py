from asset_library.app import application
from django.conf.urls import patterns, include

urlpatterns = patterns(
    '',
    (r'^asset-library/', include(application.urls)),
)
