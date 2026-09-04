from django.conf import settings
from django.db import models
from django.db.models import Q

class ConversationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(participants=user).distinct().order_by("-updated_at")

class Conversation(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    project = models.ForeignKey("projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="conversations")
    updated_at = models.DateTimeField(auto_now=True)
    objects = ConversationQuerySet.as_manager()

    def other_participant(self, user):
        return self.participants.exclude(pk=user.pk).first()

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField(max_length=2000, blank=True)
    attachment = models.FileField(upload_to="message_files/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
