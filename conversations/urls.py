from django.urls import path
from . import views
urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("start/<str:username>/", views.start, name="conversation_start"),
    path("<int:pk>/", views.detail, name="conversation_detail"),
    path("<int:pk>/attachments/<int:message_pk>/", views.attachment_download, name="message_attachment"),
    path("<int:pk>/feed/", views.message_feed, name="message_feed"),
]
