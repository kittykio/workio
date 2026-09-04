"""Cross-app regression tests for behavior not covered by the app-local suites."""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.forms import PortfolioItemForm
from accounts.models import PortfolioItem, User
from billing.forms import InvoiceCreateForm, TimeEntryForm
from billing.models import Invoice, InvoiceItem, TimeEntry
from conversations.forms import MessageForm
from conversations.models import Conversation, Message
from notifications.context_processors import notification_counts
from notifications.models import Notification
from notifications.services import notify
from projects.forms import ProjectFileForm
from projects.models import Milestone, Project, ProjectFile, ProjectInvitation, Task


class AppCase(TestCase):
    def setUp(self):
        self.freelancer = User.objects.create_user(
            "freelancer_extra", "freelancer-extra@example.com", "pass",
            role=User.Role.FREELANCER, first_name="Ada", last_name="Lovelace",
            skills="Python, Django", hourly_rate=Decimal("75.00"),
        )
        self.client_user = User.objects.create_user(
            "client_extra", "client-extra@example.com", "pass", role=User.Role.CLIENT
        )
        self.outsider = User.objects.create_user(
            "outsider_extra", "outsider-extra@example.com", "pass"
        )
        self.project = Project.objects.create(
            title="Coverage project", description="Regression coverage",
            freelancer=self.freelancer, client=self.client_user, budget=1000,
        )


class AccountCoverageTests(AppCase):
    def test_public_pages_dashboard_profile_edit_and_settings(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
        self.client.force_login(self.freelancer)
        self.assertRedirects(
            self.client.get(reverse("home")), reverse("dashboard"), fetch_redirect_response=False
        )
        with patch("accounts.views.render") as render:
            render.return_value = HttpResponse()
            self.client.get(reverse("dashboard"))
            self.assertEqual(render.call_args.args[1], "dashboard.html")
        self.assertContains(self.client.get(self.freelancer.get_absolute_url()), "Ada")
        response = self.client.post(
            reverse("profile_edit", kwargs={"username": self.freelancer.username}),
            {"first_name": "Augusta", "last_name": "Lovelace", "headline": "Engineer"},
        )
        self.assertRedirects(response, self.freelancer.get_absolute_url())
        self.client.post(reverse("account_settings"), {"email": " NEW@example.com "})
        self.freelancer.refresh_from_db()
        self.assertEqual(self.freelancer.email, "new@example.com")

    def test_user_helpers_and_portfolio_crud(self):
        self.assertEqual(self.freelancer.display_name, "Ada Lovelace")
        self.assertEqual(self.freelancer.initials, "AL")
        self.assertEqual(self.freelancer.skill_list, ["Python", "Django"])
        self.assertIsNone(self.freelancer.average_rating)
        self.client.force_login(self.freelancer)
        response = self.client.post(
            reverse("portfolio_create"),
            {"title": "Case study", "summary": "Result", "skills": "Python, UX"},
        )
        item = PortfolioItem.objects.get()
        self.assertRedirects(response, self.freelancer.get_absolute_url())
        self.assertEqual(item.skill_list, ["Python", "UX"])
        self.client.post(
            reverse("portfolio_edit", kwargs={"pk": item.pk}),
            {"title": "Updated", "summary": "Result", "skills": "Django"},
        )
        item.refresh_from_db()
        self.assertEqual(item.title, "Updated")
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("portfolio_create")).status_code, 403)

    def test_upload_size_validation(self):
        image = SimpleUploadedFile("large.png", b"x", content_type="image/png")
        image.size = 8 * 1024 * 1024 + 1
        form = PortfolioItemForm({"title": "Large", "summary": "Image"}, {"image": image})
        self.assertFalse(form.is_valid())
        upload = SimpleUploadedFile("large.txt", b"x")
        upload.size = 15 * 1024 * 1024 + 1
        form = ProjectFileForm({"label": "Large"}, {"file": upload})
        self.assertFalse(form.is_valid())


class ProjectCoverageTests(AppCase):
    def test_project_list_create_and_edit(self):
        self.client.force_login(self.freelancer)
        with patch("projects.views.render") as render:
            render.return_value = HttpResponse()
            self.client.get(reverse("project_list"), {"q": "Coverage", "status": "planning"})
            projects = render.call_args.args[2]["projects"]
            self.assertEqual(list(projects), [self.project])
        response = self.client.post(reverse("project_create"), {
            "title": "Created", "description": "New", "client": self.client_user.pk,
            "budget": "500", "status": Project.Status.ACTIVE,
        })
        created = Project.objects.get(title="Created")
        self.assertRedirects(response, created.get_absolute_url())
        self.client.post(reverse("project_edit", kwargs={"pk": created.pk}), {
            "title": "Renamed", "description": "New", "client": self.client_user.pk,
            "budget": "500", "status": Project.Status.ACTIVE,
        })
        created.refresh_from_db()
        self.assertEqual(str(created), "Renamed")
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("project_create")).status_code, 403)

    def test_task_and_milestone_crud_and_toggle(self):
        task = Task.objects.create(project=self.project, title="Draft")
        milestone = Milestone.objects.create(project=self.project, title="Phase one")
        self.assertEqual(str(task), "Draft")
        self.assertEqual(str(milestone), "Phase one")
        self.client.force_login(self.freelancer)
        self.client.post(reverse("task_toggle", kwargs={"pk": self.project.pk, "task_pk": task.pk}))
        task.refresh_from_db()
        self.assertTrue(task.completed)
        self.client.post(reverse("task_edit", kwargs={"pk": self.project.pk, "task_pk": task.pk}), {
            "title": "Final", "milestone": milestone.pk,
        })
        task.refresh_from_db()
        self.assertEqual(task.title, "Final")
        self.client.post(reverse("milestone_edit", kwargs={"pk": self.project.pk, "milestone_pk": milestone.pk}), {
            "title": "Delivery", "description": "Ship it",
        })
        milestone.refresh_from_db()
        self.assertEqual(milestone.title, "Delivery")
        self.client.post(reverse("milestone_delete", kwargs={"pk": self.project.pk, "milestone_pk": milestone.pk}))
        self.assertFalse(Milestone.objects.filter(pk=milestone.pk).exists())

    def test_invitation_detail_resend_cancel_and_status(self):
        invitation = ProjectInvitation.objects.create(
            inviter=self.freelancer, client_email="invite@example.com", project_title="Invite",
            project_description="Scope", budget=200, expires_at=timezone.now() + timedelta(days=1),
        )
        self.assertEqual(invitation.status, "Pending")
        self.assertEqual(self.client.get(invitation.get_absolute_url()).status_code, 200)
        self.client.force_login(self.freelancer)
        self.assertEqual(self.client.get(reverse("invitation_list")).status_code, 200)
        old_expiry = invitation.expires_at
        self.client.post(reverse("invitation_resend", kwargs={"token": invitation.token}))
        invitation.refresh_from_db()
        self.assertGreater(invitation.expires_at, old_expiry)
        self.client.post(reverse("invitation_cancel", kwargs={"token": invitation.token}))
        self.assertFalse(ProjectInvitation.objects.filter(pk=invitation.pk).exists())
        expired = ProjectInvitation.objects.create(
            inviter=self.freelancer, client_email="old@example.com", project_title="Old",
            project_description="Scope", budget=200, expires_at=timezone.now() - timedelta(seconds=1),
        )
        self.assertTrue(expired.is_expired)
        self.assertEqual(expired.status, "Expired")

    def test_file_upload_download_delete_and_permissions(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            self.client.force_login(self.client_user)
            self.client.post(reverse("file_upload", kwargs={"pk": self.project.pk}), {
                "label": "Notes", "file": SimpleUploadedFile("notes.txt", b"hello"),
            })
            item = ProjectFile.objects.get()
            self.assertEqual(item.filename, "notes.txt")
            response = self.client.get(reverse("file_download", kwargs={"pk": self.project.pk, "file_pk": item.pk}))
            self.assertEqual(b"".join(response.streaming_content), b"hello")
            self.client.force_login(self.outsider)
            self.assertEqual(self.client.get(reverse("file_download", kwargs={"pk": self.project.pk, "file_pk": item.pk})).status_code, 403)
            self.client.force_login(self.freelancer)
            self.client.post(reverse("file_delete", kwargs={"pk": self.project.pk, "file_pk": item.pk}))
            self.assertFalse(ProjectFile.objects.exists())


class BillingCoverageTests(AppCase):
    def test_forms_reject_invalid_hours_and_missing_rate(self):
        self.assertFalse(TimeEntryForm({"date": date.today(), "hours": 0, "description": "Bad"}).is_valid())
        entry = TimeEntry.objects.create(
            project=self.project, user=self.freelancer, date=date.today(), hours=1, description="Work"
        )
        form = InvoiceCreateForm({
            "number": "INV-X", "issued_on": date.today(), "due_on": date.today(),
            "status": "draft", "time_entries": [entry.pk], "hourly_rate": "",
        }, project=self.project, freelancer=self.freelancer)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.fields["hourly_rate"].initial, Decimal("75.00"))

    def test_ledgers_invoice_lists_details_and_client_payment(self):
        TimeEntry.objects.create(project=self.project, user=self.freelancer, date=date.today(), hours=2, description="Internal", billable=False)
        invoice = Invoice.objects.create(
            project=self.project, number="INV-PAY", issued_on=date.today(),
            due_on=date.today() + timedelta(days=7), status=Invoice.Status.SENT,
        )
        InvoiceItem.objects.create(invoice=invoice, description="Build", quantity=2, rate=50)
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("time_list"), {"billing": "nonbillable"}).context["total"], Decimal("2"))
        self.assertContains(self.client.get(reverse("invoice_list")), "INV-PAY")
        self.assertEqual(self.client.get(invoice.get_absolute_url()).status_code, 200)
        self.client.post(reverse("invoice_status", kwargs={"pk": invoice.pk}), {"status": Invoice.Status.PAID})
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(invoice.get_absolute_url()).status_code, 403)

    def test_freelancer_cannot_invoice_someone_elses_project(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(reverse("invoice_create", kwargs={"project_pk": self.project.pk})).status_code, 403)


class ConversationCoverageTests(AppCase):
    def setUp(self):
        super().setUp()
        self.conversation = Conversation.objects.create(project=self.project)
        self.conversation.participants.add(self.freelancer, self.client_user)

    def test_inbox_start_reuses_conversation_and_self_redirects(self):
        self.client.force_login(self.freelancer)
        self.assertEqual(self.client.get(reverse("inbox")).status_code, 200)
        response = self.client.get(reverse("conversation_start", kwargs={"username": self.client_user.username}))
        self.assertRedirects(response, reverse("conversation_detail", kwargs={"pk": self.conversation.pk}))
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertRedirects(
            self.client.get(reverse("conversation_start", kwargs={"username": self.freelancer.username})),
            reverse("inbox"),
        )

    def test_start_new_conversation_and_invalid_feed_cursor(self):
        fourth = User.objects.create_user("fourth", "fourth@example.com", "pass")
        self.client.force_login(self.freelancer)
        self.client.get(reverse("conversation_start", kwargs={"username": fourth.username}))
        self.assertEqual(Conversation.objects.count(), 2)
        Message.objects.create(conversation=self.conversation, sender=self.client_user, body="Hello")
        payload = self.client.get(reverse("message_feed", kwargs={"pk": self.conversation.pk}), {"after": "bad"}).json()
        self.assertEqual(payload["messages"][0]["body"], "Hello")
        self.assertFalse(payload["messages"][0]["mine"])

    def test_attachment_validation_download_and_missing_attachment(self):
        self.assertFalse(MessageForm({"body": ""}).is_valid())
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            message = Message.objects.create(
                conversation=self.conversation, sender=self.freelancer,
                attachment=SimpleUploadedFile("brief.txt", b"brief"),
            )
            self.client.force_login(self.client_user)
            response = self.client.get(reverse("message_attachment", kwargs={"pk": self.conversation.pk, "message_pk": message.pk}))
            self.assertEqual(b"".join(response.streaming_content), b"brief")
            no_file = Message.objects.create(conversation=self.conversation, sender=self.freelancer, body="text")
            self.assertEqual(self.client.get(reverse("message_attachment", kwargs={"pk": self.conversation.pk, "message_pk": no_file.pk})).status_code, 403)


class NotificationAndCommandCoverageTests(AppCase):
    def test_notification_pages_open_read_all_and_self_notify(self):
        self.assertIsNone(notify(self.freelancer, self.freelancer, "self", "Ignored"))
        item = notify(self.freelancer, self.client_user, "message", "Read me", "")
        self.client.force_login(self.freelancer)
        self.assertContains(self.client.get(reverse("notification_list")), "Read me")
        self.assertRedirects(self.client.get(reverse("notification_open", kwargs={"pk": item.pk})), reverse("notification_list"))
        item.refresh_from_db()
        self.assertIsNotNone(item.read_at)
        second = notify(self.freelancer, self.client_user, "message", "Another")
        self.client.post(reverse("notifications_read_all"))
        second.refresh_from_db()
        self.assertIsNotNone(second.read_at)

    def test_context_processor_anonymous_and_authenticated_counts(self):
        request = type("Request", (), {"user": type("Anonymous", (), {"is_authenticated": False})()})()
        self.assertEqual(notification_counts(request), {})
        conversation = Conversation.objects.create()
        conversation.participants.add(self.freelancer, self.client_user)
        Message.objects.create(conversation=conversation, sender=self.client_user, body="Unread")
        Notification.objects.create(recipient=self.freelancer, text="Unread", kind="message")
        request.user = self.freelancer
        counts = notification_counts(request)
        self.assertEqual(counts["unread_notification_count"], 1)
        self.assertEqual(counts["unread_message_count"], 1)

    def test_seed_demo_is_idempotent(self):
        output = StringIO()
        call_command("seed_demo", stdout=output)
        call_command("seed_demo", stdout=output)
        self.assertIn("Demo ready", output.getvalue())
        self.assertEqual(User.objects.filter(username="maya").count(), 1)
        self.assertEqual(Invoice.objects.filter(number="INV-DEMO-001").count(), 1)
