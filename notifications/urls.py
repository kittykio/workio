from django.urls import path
from . import views
urlpatterns = [
    path("", views.notification_list, name="notification_list"),
    path("feed/", views.notification_feed, name="notification_feed"),
    path("<int:pk>/open/", views.notification_open, name="notification_open"),
    path("read-all/", views.read_all, name="notifications_read_all"),
]

