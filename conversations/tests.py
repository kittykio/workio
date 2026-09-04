from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from .models import Conversation, Message


class ConversationTests(TestCase):
    def setUp(self):
        self.first = User.objects.create_user("first", "first@example.com", "pass")
        self.second = User.objects.create_user("second", "second@example.com", "pass", role="client")
        self.outsider = User.objects.create_user("third", "third@example.com", "pass")
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.first, self.second)

    def test_participant_can_send_message(self):
        self.client.force_login(self.first)
        self.client.post(reverse("conversation_detail", kwargs={"pk": self.conversation.pk}), {"body": "Hello!"})
        self.assertTrue(Message.objects.filter(body="Hello!", sender=self.first).exists())

    def test_outsider_cannot_read_conversation(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("conversation_detail", kwargs={"pk": self.conversation.pk}))
        self.assertEqual(response.status_code, 403)

    def test_empty_message_is_rejected(self):
        self.client.force_login(self.first)
        self.client.post(reverse("conversation_detail", kwargs={"pk": self.conversation.pk}), {"body": ""})
        self.assertEqual(Message.objects.count(), 0)

    def test_live_feed_returns_new_messages_and_marks_them_read(self):
        message = Message.objects.create(conversation=self.conversation, sender=self.second, body="Live update")
        self.client.force_login(self.first)
        payload = self.client.get(reverse("message_feed", kwargs={"pk": self.conversation.pk}), {"after": 0}).json()
        self.assertEqual(payload["messages"][0]["body"], "Live update")
        message.refresh_from_db()
        self.assertIsNotNone(message.read_at)

    def test_outsider_cannot_access_live_feed(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(reverse("message_feed", kwargs={"pk": self.conversation.pk})).status_code, 403)

    def test_conversation_views_render_other_participant_avatar(self):
        self.second.avatar = "avatars/jordan.jpg"
        self.second.save(update_fields=["avatar"])
        self.client.force_login(self.first)
        detail = self.client.get(reverse("conversation_detail", kwargs={"pk": self.conversation.pk}))
        inbox = self.client.get(reverse("inbox"))
        self.assertContains(detail, self.second.avatar.url)
        self.assertContains(inbox, self.second.avatar.url)
        self.assertContains(detail, "chat-person")
        self.assertContains(inbox, "inbox-copy")
