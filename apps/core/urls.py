from django.urls import path

from .views.site_view import FooterBadgeListView


urlpatterns = [
    path('footer-badges/', FooterBadgeListView.as_view()),
]
