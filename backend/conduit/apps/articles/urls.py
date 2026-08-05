from django.conf.urls import include, url

from rest_framework.routers import DefaultRouter

from .views import (
    ArticleViewSet, ArticlesFavoriteAPIView, ArticlesFeedAPIView,
    CommentsListCreateAPIView, CommentsDestroyAPIView, TagListAPIView
)

router = DefaultRouter(trailing_slash=False)
router.register(r'articles', ArticleViewSet)

app_name = 'articles'

urlpatterns = [
    url(r'^articles/feed/?$', ArticlesFeedAPIView.as_view()),

    url(r'^articles/(?P<article_slug>[-\w]+)/favorite/?$',
        ArticlesFavoriteAPIView.as_view()),

    url(r'^articles/(?P<article_slug>[-\w]+)/comments/?$',
        CommentsListCreateAPIView.as_view()),

    url(r'^articles/(?P<article_slug>[-\w]+)/comments/(?P<comment_pk>[\d]+)/?$',
        CommentsDestroyAPIView.as_view()),

    url(r'^tags/?$', TagListAPIView.as_view()),

    # Must come last: the router's detail route (`articles/<slug>`) would
    # otherwise shadow the more specific literal routes above (e.g. matching
    # "feed" in /articles/feed as a slug lookup instead of the feed view).
    url(r'^', include(router.urls)),
]
