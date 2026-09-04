from datetime import date, timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.models import User
from projects.models import Project
from .forms import ExpenseForm
from .models import ActiveTimer, Expense, Invoice, InvoiceItem, TimeEntry


class BillingTests(TestCase):
    def setUp(self):
        self.freelancer = User.objects.create_user("freelancer", "f2@example.com", "pass", role="freelancer")
        self.client_user = User.objects.create_user("client", "c2@example.com", "pass", role="client")
        self.project = Project.objects.create(title="Portal", description="Build", freelancer=self.freelancer, client=self.client_user, budget=2000)

    def test_freelancer_can_log_time(self):
        self.client.force_login(self.freelancer)
        self.client.post(reverse("time_create", kwargs={"project_pk": self.project.pk}), {"date": date.today(), "hours": "2.50", "description": "Design", "billable": "on"})
        self.assertEqual(TimeEntry.objects.get().hours, Decimal("2.50"))

    def test_client_cannot_log_time(self):
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("time_create", kwargs={"project_pk": self.project.pk})).status_code, 403)

    def test_invoice_total_and_status_permissions(self):
        invoice = Invoice.objects.create(project=self.project, number="INV-001", issued_on=date.today(), due_on=date.today() + timedelta(days=14))
        InvoiceItem.objects.create(invoice=invoice, description="Development", quantity=Decimal("4"), rate=Decimal("125"))
        self.assertEqual(invoice.total, Decimal("500"))
        self.client.force_login(self.client_user)
        self.client.post(reverse("invoice_status", kwargs={"pk": invoice.pk}), {"status": "sent"})
        invoice.refresh_from_db(); self.assertEqual(invoice.status, "draft")
        self.client.force_login(self.freelancer)
        self.client.post(reverse("invoice_status", kwargs={"pk": invoice.pk}), {"status": "sent"})
        invoice.refresh_from_db(); self.assertEqual(invoice.status, "sent")

    def test_only_freelancer_can_edit_or_delete_draft(self):
        invoice = Invoice.objects.create(project=self.project, number="INV-EDIT", issued_on=date.today(), due_on=date.today() + timedelta(days=14))
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("invoice_edit", kwargs={"pk": invoice.pk})).status_code, 403)
        self.assertEqual(self.client.post(reverse("invoice_delete", kwargs={"pk": invoice.pk})).status_code, 403)
        self.client.force_login(self.freelancer)
        self.assertEqual(self.client.get(reverse("invoice_edit", kwargs={"pk": invoice.pk})).status_code, 200)
        self.client.post(reverse("invoice_delete", kwargs={"pk": invoice.pk}))
        self.assertFalse(Invoice.objects.filter(pk=invoice.pk).exists())

    def test_sent_invoice_cannot_be_edited_or_deleted(self):
        invoice = Invoice.objects.create(project=self.project, number="INV-SENT", issued_on=date.today(), due_on=date.today() + timedelta(days=14), status="sent")
        self.client.force_login(self.freelancer)
        self.assertEqual(self.client.get(reverse("invoice_edit", kwargs={"pk": invoice.pk})).status_code, 403)
        self.assertEqual(self.client.post(reverse("invoice_delete", kwargs={"pk": invoice.pk})).status_code, 403)

    def test_time_owner_can_edit_and_delete_entry(self):
        entry = TimeEntry.objects.create(project=self.project, user=self.freelancer, date=date.today(), hours="1.00", description="Old")
        self.client.force_login(self.freelancer)
        self.client.post(reverse("time_edit", kwargs={"pk": entry.pk}), {"date": date.today(), "hours": "2.25", "description": "Updated", "billable": "on"})
        entry.refresh_from_db(); self.assertEqual(entry.hours, Decimal("2.25"))
        self.client.post(reverse("time_delete", kwargs={"pk": entry.pk}))
        self.assertFalse(TimeEntry.objects.filter(pk=entry.pk).exists())

    def test_client_cannot_manage_freelancers_time(self):
        entry = TimeEntry.objects.create(project=self.project, user=self.freelancer, date=date.today(), hours="1.00", description="Work")
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("time_edit", kwargs={"pk": entry.pk})).status_code, 403)
        self.assertEqual(self.client.post(reverse("time_delete", kwargs={"pk": entry.pk})).status_code, 403)

    def test_time_ledger_filters_billable_entries(self):
        TimeEntry.objects.create(project=self.project, user=self.freelancer, date=date.today(), hours="2.00", description="Billable", billable=True)
        TimeEntry.objects.create(project=self.project, user=self.freelancer, date=date.today(), hours="1.00", description="Internal", billable=False)
        self.client.force_login(self.freelancer)
        response = self.client.get(reverse("time_list"), {"billing": "billable"})
        self.assertEqual(list(response.context["entries"].values_list("description", flat=True)), ["Billable"])

    def test_invoice_can_convert_unbilled_time_into_traceable_lines(self):
        entry = TimeEntry.objects.create(project=self.project, user=self.freelancer, date=date.today(), hours="2.50", description="Django development", billable=True)
        self.client.force_login(self.freelancer)
        data = {"number": "INV-TIME", "issued_on": date.today(), "due_on": date.today() + timedelta(days=14), "status": "draft", "notes": "", "time_entries": [entry.pk], "hourly_rate": "120.00", "items-TOTAL_FORMS": "3", "items-INITIAL_FORMS": "0", "items-MIN_NUM_FORMS": "0", "items-MAX_NUM_FORMS": "1000"}
        response = self.client.post(reverse("invoice_create", kwargs={"project_pk": self.project.pk}), data)
        invoice = Invoice.objects.get(number="INV-TIME")
        self.assertRedirects(response, invoice.get_absolute_url())
        item = invoice.items.get()
        self.assertEqual(item.source_time_entry, entry)
        self.assertEqual(item.amount, Decimal("300.0000"))
        response = self.client.get(reverse("invoice_create", kwargs={"project_pk": self.project.pk}))
        self.assertNotIn(entry, response.context["form"].fields["time_entries"].queryset)

    def test_invoiced_time_cannot_be_edited_or_deleted(self):
        entry = TimeEntry.objects.create(project=self.project, user=self.freelancer, date=date.today(), hours="1.00", description="Billed")
        invoice = Invoice.objects.create(project=self.project, number="INV-LOCK", issued_on=date.today(), due_on=date.today() + timedelta(days=14))
        InvoiceItem.objects.create(invoice=invoice, source_time_entry=entry, description="Billed", quantity=1, rate=100)
        self.client.force_login(self.freelancer)
        self.assertEqual(self.client.get(reverse("time_edit", kwargs={"pk": entry.pk})).status_code, 403)
        self.assertEqual(self.client.post(reverse("time_delete", kwargs={"pk": entry.pk})).status_code, 403)

    def test_timer_creates_rounded_time_entry_when_stopped(self):
        self.client.force_login(self.freelancer)
        self.client.post(reverse("timer_start", kwargs={"project_pk": self.project.pk}), {"description": "Live implementation", "billable": "on"})
        timer = ActiveTimer.objects.get(user=self.freelancer)
        timer.started_at = timezone.now() - timedelta(hours=1, minutes=15)
        timer.save(update_fields=["started_at"])
        response = self.client.post(reverse("timer_stop"))
        self.assertRedirects(response, self.project.get_absolute_url())
        entry = TimeEntry.objects.get(description="Live implementation")
        self.assertEqual(entry.hours, Decimal("1.25"))
        self.assertTrue(entry.billable)
        self.assertFalse(ActiveTimer.objects.filter(user=self.freelancer).exists())

    def test_only_freelancer_can_start_project_timer(self):
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("timer_start", kwargs={"project_pk": self.project.pk})).status_code, 403)

    def test_second_timer_is_blocked_and_global_bar_is_visible(self):
        ActiveTimer.objects.create(user=self.freelancer, project=self.project, description="Already running", started_at=timezone.now())
        self.client.force_login(self.freelancer)
        response = self.client.post(reverse("timer_start", kwargs={"project_pk": self.project.pk}), {"description": "Another"})
        self.assertRedirects(response, self.project.get_absolute_url())
        self.assertEqual(ActiveTimer.objects.filter(user=self.freelancer).count(), 1)
        self.assertContains(self.client.get(reverse("dashboard")), "Already running")

    def test_freelancer_can_create_and_manage_unbilled_expense(self):
        self.client.force_login(self.freelancer)
        response = self.client.post(reverse("expense_create", kwargs={"project_pk": self.project.pk}), {"date": date.today(), "vendor": "Cloud Host", "description": "Hosting", "amount": "24.50", "billable": "on"})
        self.assertRedirects(response, reverse("expense_list"))
        expense = Expense.objects.get()
        self.client.post(reverse("expense_edit", kwargs={"pk": expense.pk}), {"date": date.today(), "vendor": "Cloud Host", "description": "Production hosting", "amount": "30.00", "billable": "on"})
        expense.refresh_from_db(); self.assertEqual(expense.amount, Decimal("30.00"))
        self.client.post(reverse("expense_delete", kwargs={"pk": expense.pk}))
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())

    def test_client_cannot_create_or_manage_expense(self):
        expense = Expense.objects.create(project=self.project, user=self.freelancer, date=date.today(), vendor="Vendor", description="Cost", amount=10)
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("expense_create", kwargs={"project_pk": self.project.pk})).status_code, 403)
        self.assertEqual(self.client.get(reverse("expense_edit", kwargs={"pk": expense.pk})).status_code, 403)

    def test_project_participant_can_download_receipt_but_outsider_cannot(self):
        receipt = SimpleUploadedFile("receipt.txt", b"receipt-data", content_type="text/plain")
        expense = Expense.objects.create(project=self.project, user=self.freelancer, date=date.today(), vendor="Vendor", description="Cost", amount=10, receipt=receipt)
        self.client.force_login(self.client_user)
        self.assertEqual(self.client.get(reverse("expense_receipt", kwargs={"pk": expense.pk})).status_code, 200)
        outsider = User.objects.create_user("expense-outsider", "expense-outsider@example.com", "pass")
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(reverse("expense_receipt", kwargs={"pk": expense.pk})).status_code, 403)

    def test_invoice_can_include_expense_only_once(self):
        expense = Expense.objects.create(project=self.project, user=self.freelancer, date=date.today(), vendor="Stock Library", description="Licensed images", amount="45.00", billable=True)
        self.client.force_login(self.freelancer)
        data = {"number": "INV-EXPENSE", "issued_on": date.today(), "due_on": date.today() + timedelta(days=14), "status": "draft", "notes": "", "expenses": [expense.pk], "hourly_rate": "100", "items-TOTAL_FORMS": "3", "items-INITIAL_FORMS": "0", "items-MIN_NUM_FORMS": "0", "items-MAX_NUM_FORMS": "1000"}
        self.client.post(reverse("invoice_create", kwargs={"project_pk": self.project.pk}), data)
        item = Invoice.objects.get(number="INV-EXPENSE").items.get()
        self.assertEqual(item.source_expense, expense)
        self.assertEqual(item.amount, Decimal("45.00"))
        response = self.client.get(reverse("invoice_create", kwargs={"project_pk": self.project.pk}))
        self.assertNotIn(expense, response.context["form"].fields["expenses"].queryset)
        self.assertEqual(self.client.get(reverse("expense_edit", kwargs={"pk": expense.pk})).status_code, 403)

    def test_timer_stop_requires_post_and_clamps_short_sessions(self):
        ActiveTimer.objects.create(
            user=self.freelancer,
            project=self.project,
            description="Quick correction",
            billable=False,
            started_at=timezone.now(),
        )
        self.client.force_login(self.freelancer)
        self.assertEqual(self.client.get(reverse("timer_stop")).status_code, 403)
        self.client.post(reverse("timer_stop"))
        entry = TimeEntry.objects.get(description="Quick correction")
        self.assertEqual(entry.hours, Decimal("0.01"))
        self.assertFalse(entry.billable)

    def test_expense_ledger_filters_project_and_billing_state(self):
        other_project = Project.objects.create(
            title="Other", description="Other work", freelancer=self.freelancer,
            client=self.client_user, budget=100,
        )
        billable = Expense.objects.create(
            project=self.project, user=self.freelancer, date=date.today(), vendor="A",
            description="Billable", amount=10, billable=True,
        )
        Expense.objects.create(
            project=self.project, user=self.freelancer, date=date.today(), vendor="B",
            description="Internal", amount=5, billable=False,
        )
        billed = Expense.objects.create(
            project=other_project, user=self.freelancer, date=date.today(), vendor="C",
            description="Already billed", amount=20, billable=True,
        )
        invoice = Invoice.objects.create(
            project=other_project, number="INV-FILTER", issued_on=date.today(), due_on=date.today(),
        )
        InvoiceItem.objects.create(
            invoice=invoice, source_expense=billed, description="Billed", quantity=1, rate=20,
        )
        self.client.force_login(self.freelancer)
        response = self.client.get(reverse("expense_list"), {"project": self.project.pk})
        self.assertEqual(set(response.context["expenses"]), set(self.project.expenses.all()))
        response = self.client.get(reverse("expense_list"), {"billing": "nonbillable"})
        self.assertEqual(list(response.context["expenses"].values_list("description", flat=True)), ["Internal"])
        response = self.client.get(reverse("expense_list"), {"billing": "unbilled"})
        self.assertIn(billable, response.context["expenses"])
        self.assertNotIn(billed, response.context["expenses"])

    def test_expense_receipt_size_missing_file_and_deletion(self):
        oversized = SimpleUploadedFile("large.pdf", b"x", content_type="application/pdf")
        oversized.size = 10 * 1024 * 1024 + 1
        form = ExpenseForm({
            "date": date.today(), "vendor": "Vendor", "description": "Receipt",
            "amount": "10.00", "billable": "on",
        }, {"receipt": oversized})
        self.assertFalse(form.is_valid())
        no_receipt = Expense.objects.create(
            project=self.project, user=self.freelancer, date=date.today(), vendor="None",
            description="No receipt", amount=5,
        )
        self.client.force_login(self.freelancer)
        self.assertEqual(self.client.get(reverse("expense_receipt", kwargs={"pk": no_receipt.pk})).status_code, 403)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            expense = Expense.objects.create(
                project=self.project, user=self.freelancer, date=date.today(), vendor="Vendor",
                description="With receipt", amount=10,
                receipt=SimpleUploadedFile("receipt.txt", b"receipt"),
            )
            self.client.post(reverse("expense_delete", kwargs={"pk": expense.pk}))
            self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())

    def test_sent_invoice_creation_notifies_client(self):
        self.client.force_login(self.freelancer)
        data = {
            "number": "INV-NOTIFY", "issued_on": date.today(),
            "due_on": date.today() + timedelta(days=14), "status": "sent", "notes": "",
            "hourly_rate": "100", "items-TOTAL_FORMS": "3", "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0", "items-MAX_NUM_FORMS": "1000",
        }
        response = self.client.post(reverse("invoice_create", kwargs={"project_pk": self.project.pk}), data)
        invoice = Invoice.objects.get(number="INV-NOTIFY")
        self.assertRedirects(response, invoice.get_absolute_url())
        notification = self.client_user.notifications.get(kind="invoice")
        self.assertIn("INV-NOTIFY", notification.text)
