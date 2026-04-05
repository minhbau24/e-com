"""URL patterns for the api app (e-com-service)."""

from django.urls import path

from core.views_chat import ChatView
from core.views_health import HealthView
from core.views_recommend import RecommendView
from core.views_search import SearchProxyView
from core.views_track import TrackView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("chat", ChatView.as_view(), name="chat"),
    path("search", SearchProxyView.as_view(), name="search-proxy"),
    path("recommend/<str:user_id>", RecommendView.as_view(), name="recommend"),
    path("track", TrackView.as_view(), name="track"),
]
