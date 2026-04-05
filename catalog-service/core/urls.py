from django.urls import path
from .views import CatalogBrowseAPIView, CatalogListCreateAPIView

urlpatterns = [
    path("catalog/", CatalogListCreateAPIView.as_view()),
    path("catalog/browse/", CatalogBrowseAPIView.as_view()),
]
