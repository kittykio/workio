from django.urls import path
from . import views

urlpatterns = [
    path("settings/account/", views.account_settings, name="account_settings"),
    path("", views.freelancer_directory, name="freelancer_directory"),
    path("portfolio/new/", views.portfolio_create, name="portfolio_create"),
    path("portfolio/<int:pk>/edit/", views.portfolio_edit, name="portfolio_edit"),
    path("portfolio/<int:pk>/delete/", views.portfolio_delete, name="portfolio_delete"),
    path("reviews/project/<int:project_pk>/new/", views.review_create, name="review_create"),
    path("<str:username>/", views.profile, name="profile"),
    path("<str:username>/edit/", views.profile_edit, name="profile_edit"),
]
