from django.test import TestCase
from django.urls import reverse
from django.core import mail
from .models import User
from projects.models import Project
from .models import PortfolioItem, Review
from billing.models import Invoice, InvoiceItem, TimeEntry
from conversations.models import Conversation
from datetime import date, timedelta


class AccountTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(reverse("signup"), {"username": "newuser", "first_name": "New", "last_name": "User", "email": "new@example.com", "role": "freelancer", "password1": "a-strong-pass-123", "password2": "a-strong-pass-123"})
        self.assertRedirects(response, reverse("profile_edit", kwargs={"username": "newuser"}))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_user_cannot_edit_another_profile(self):
        first = User.objects.create_user("first", "first@example.com", "pass")
        User.objects.create_user("second", "second@example.com", "pass")
        self.client.force_login(first)
        response = self.client.get(reverse("profile_edit", kwargs={"username": "second"}))
        self.assertRedirects(response, reverse("profile", kwargs={"username": "second"}))

    def test_profile_exposes_clear_owner_edit_controls(self):
        owner = User.objects.create_user("profileowner", "profile@example.com", "pass", role="freelancer")
        self.client.force_login(owner)
        response = self.client.get(owner.get_absolute_url())
        edit_url = reverse("profile_edit", kwargs={"username": owner.username})
        self.assertContains(response, f'href="{edit_url}#id_skills"')
        self.assertContains(response, "Edit expertise")
        self.assertContains(response, "Add case study")

    def test_client_profile_hides_freelancer_portfolio_sections(self):
        owner = User.objects.create_user("clientowner", "clientowner@example.com", "pass", role="client")
        self.client.force_login(owner)
        profile_response = self.client.get(owner.get_absolute_url())
        self.assertNotContains(profile_response, "Expertise")
        self.assertNotContains(profile_response, "Selected work")
        response = self.client.post(reverse("portfolio_create"), {
            "title": "Campaign launch",
            "summary": "Led the launch from planning through delivery.",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(PortfolioItem.objects.filter(owner=owner).exists())

    def test_profile_form_normalizes_expertise(self):
        owner = User.objects.create_user("skilled", "skilled@example.com", "pass", role="freelancer")
        self.client.force_login(owner)
        response = self.client.post(reverse("profile_edit", kwargs={"username": owner.username}), {
            "first_name": "Skilled",
            "last_name": "Person",
            "skills": "Django, django,  Product Design ",
        })
        self.assertRedirects(response, owner.get_absolute_url())
        owner.refresh_from_db()
        self.assertEqual(owner.skills, "Django, Product Design")

    def test_existing_avatar_has_clear_photo_controls(self):
        owner = User.objects.create_user("avatarowner", "avatarowner@example.com", "pass")
        owner.avatar = "avatars/existing.jpg"
        owner.save(update_fields=["avatar"])
        self.client.force_login(owner)
        response = self.client.get(reverse("profile_edit", kwargs={"username": owner.username}))
        self.assertContains(response, "Current photo")
        self.assertContains(response, "Choose a replacement")
        self.assertContains(response, "Remove current photo")
        self.assertNotContains(response, "Clear:")

        response = self.client.post(
            reverse("profile_edit", kwargs={"username": owner.username}),
            {"first_name": "Avatar", "last_name": "Owner", "avatar-clear": "on"},
        )
        self.assertRedirects(response, owner.get_absolute_url())
        owner.refresh_from_db()
        self.assertFalse(owner.avatar)

    def test_empty_avatar_editor_renders_preview_placeholder(self):
        owner = User.objects.create_user("noavatar", "noavatar@example.com", "pass")
        self.client.force_login(owner)
        response = self.client.get(reverse("profile_edit", kwargs={"username": owner.username}))
        self.assertContains(response, 'id="avatar-preview"')
        self.assertContains(response, "No photo selected")
        self.assertContains(response, "Choose a photo")

    def test_directory_searches_freelancer_skills(self):
        User.objects.create_user("django_dev", "dev@example.com", "pass", role="freelancer", skills="Django, PostgreSQL")
        User.objects.create_user("designer", "design@example.com", "pass", role="freelancer", skills="Figma")
        response = self.client.get(reverse("freelancer_directory"), {"q": "PostgreSQL"})
        self.assertContains(response, "django_dev")
        self.assertNotContains(response, "designer")

    def test_freelancer_can_manage_only_own_portfolio(self):
        owner = User.objects.create_user("owner", "owner@example.com", "pass", role="freelancer")
        other = User.objects.create_user("other", "other@example.com", "pass", role="freelancer")
        item = PortfolioItem.objects.create(owner=owner, title="Case", summary="A result")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("portfolio_edit", kwargs={"pk": item.pk})).status_code, 403)
        self.client.force_login(owner)
        self.client.post(reverse("portfolio_delete", kwargs={"pk": item.pk}))
        self.assertFalse(PortfolioItem.objects.filter(pk=item.pk).exists())

    def test_client_can_review_only_completed_own_project_once(self):
        freelancer = User.objects.create_user("reviewed", "reviewed@example.com", "pass", role="freelancer")
        client = User.objects.create_user("reviewer", "reviewer@example.com", "pass", role="client")
        active = Project.objects.create(title="Active", description="Work", freelancer=freelancer, client=client, budget=100, status="active")
        completed = Project.objects.create(title="Done", description="Work", freelancer=freelancer, client=client, budget=100, status="completed")
        self.client.force_login(client)
        self.assertEqual(self.client.get(reverse("review_create", kwargs={"project_pk": active.pk})).status_code, 403)
        self.client.post(reverse("review_create", kwargs={"project_pk": completed.pk}), {"rating": 5, "body": "Excellent work"})
        self.assertTrue(Review.objects.filter(project=completed, rating=5).exists())
        self.assertEqual(self.client.get(reverse("review_create", kwargs={"project_pk": completed.pk})).status_code, 403)

    def test_signup_preserves_safe_invitation_redirect(self):
        response = self.client.post(reverse("signup"), {"username": "invited", "first_name": "Invite", "last_name": "Client", "email": "invite@example.com", "role": "client", "password1": "a-strong-pass-123", "password2": "a-strong-pass-123", "next": "/projects/invitations/example/"})
        self.assertRedirects(response, "/projects/invitations/example/", fetch_redirect_response=False)

    def test_signup_rejects_external_redirect(self):
        response = self.client.post(reverse("signup"), {"username": "safe", "first_name": "Safe", "last_name": "Client", "email": "safe@example.com", "role": "client", "password1": "a-strong-pass-123", "password2": "a-strong-pass-123", "next": "https://evil.example/"})
        self.assertRedirects(response, reverse("profile_edit", kwargs={"username": "safe"}))

    def test_account_email_must_remain_unique(self):
        first = User.objects.create_user("emailone", "one@example.com", "pass")
        User.objects.create_user("emailtwo", "two@example.com", "pass")
        self.client.force_login(first)
        response = self.client.post(reverse("account_settings"), {"email": "two@example.com", "email_notifications": "on"})
        self.assertContains(response, "already uses this email")
        first.refresh_from_db(); self.assertEqual(first.email, "one@example.com")

    def test_password_change_keeps_user_signed_in(self):
        user = User.objects.create_user("changer", "changer@example.com", "old-password-123")
        self.client.force_login(user)
        response = self.client.post(reverse("password_change"), {"old_password": "old-password-123", "new_password1": "new-password-456", "new_password2": "new-password-456"})
        self.assertRedirects(response, reverse("password_change_done"))
        self.assertEqual(self.client.get(reverse("account_settings")).status_code, 200)

    def test_password_reset_sends_non_disclosing_email_flow(self):
        User.objects.create_user("resetme", "reset@example.com", "old-password-123")
        response = self.client.post(reverse("password_reset"), {"email": "reset@example.com"})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/reset/", mail.outbox[0].body)
        self.client.post(reverse("password_reset"), {"email": "missing@example.com"})
        self.assertEqual(len(mail.outbox), 1)

    def test_dashboard_summarizes_participant_finances_and_time(self):
        freelancer = User.objects.create_user("metrics", "metrics@example.com", "pass", role="freelancer")
        client = User.objects.create_user("metricsclient", "metricsclient@example.com", "pass", role="client")
        project = Project.objects.create(title="Metrics project", description="Work", freelancer=freelancer, client=client, budget=1000, status="active")
        TimeEntry.objects.create(project=project, user=freelancer, date=date.today(), hours="3.50", description="Work")
        invoice = Invoice.objects.create(project=project, number="INV-METRICS", issued_on=date.today(), due_on=date.today() + timedelta(days=10), status="sent")
        InvoiceItem.objects.create(invoice=invoice, description="Work", quantity=2, rate=100)
        self.client.force_login(freelancer)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["active_count"], 1)
        self.assertEqual(response.context["month_hours"], 3.5)
        self.assertEqual(response.context["outstanding"], 200)

    def test_dashboard_activity_uses_actor_current_avatar(self):
        freelancer = User.objects.create_user("activeavatar", "activeavatar@example.com", "pass", role="freelancer")
        client = User.objects.create_user("activityclient", "activityclient@example.com", "pass", role="client")
        freelancer.avatar = "avatars/current-profile.jpg"
        freelancer.save(update_fields=["avatar"])
        project = Project.objects.create(title="Avatar project", description="Work", freelancer=freelancer, client=client, budget=100)
        from projects.models import ProjectActivity
        ProjectActivity.objects.create(project=project, actor=freelancer, kind="project", text="Updated the project")
        self.client.force_login(client)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, freelancer.avatar.url)
        self.assertContains(response, 'class="avatar activity-avatar"')

    def test_dashboard_messages_use_other_participant_profile(self):
        freelancer = User.objects.create_user("messagefreelancer", "messagefreelancer@example.com", "pass", role="freelancer")
        client = User.objects.create_user("messageclient", "messageclient@example.com", "pass", role="client", first_name="Jordan", last_name="Lee")
        client.avatar = "avatars/jordan-current.jpg"
        client.save(update_fields=["avatar"])
        conversation = Conversation.objects.create()
        conversation.participants.add(freelancer, client)
        self.client.force_login(freelancer)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Jordan Lee")
        self.assertContains(response, client.avatar.url)
