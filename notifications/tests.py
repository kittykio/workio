from django.test import TestCase
from django.urls import reverse
from django.core import mail
from accounts.models import User
from .services import notify

class NotificationTests(TestCase):
    def test_feed_only_contains_current_users_notifications(self):
        first = User.objects.create_user("n1", "n1@example.com", "pass")
        second = User.objects.create_user("n2", "n2@example.com", "pass")
        notify(first, second, "message", "Hello", "/messages/")
        notify(second, first, "message", "Other", "/messages/")
        self.client.force_login(first)
        payload = self.client.get(reverse("notification_feed")).json()
        self.assertEqual(payload["unread"], 1)
        self.assertEqual(payload["items"][0]["text"], "Hello")

    def test_email_preference_controls_notification_delivery(self):
        recipient = User.objects.create_user("emailrecipient", "notify@example.com", "pass", email_notifications=True)
        actor = User.objects.create_user("emailactor", "actor@example.com", "pass")
        notify(recipient, actor, "message", "A useful update", "/messages/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("A useful update", mail.outbox[0].body)
