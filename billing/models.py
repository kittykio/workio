from decimal import Decimal
from django.conf import settings
from django.db import models
from django.urls import reverse


class TimeEntry(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="time_entries")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="time_entries")
    date = models.DateField()
    hours = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=240)
    billable = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]


class ActiveTimer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="active_timer")
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="active_timers")
    description = models.CharField(max_length=240)
    billable = models.BooleanField(default=True)
    started_at = models.DateTimeField()

    class Meta:
        ordering = ["started_at"]


class Expense(models.Model):
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="expenses")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses")
    date = models.DateField()
    vendor = models.CharField(max_length=140)
    description = models.CharField(max_length=240)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    billable = models.BooleanField(default=True)
    receipt = models.FileField(upload_to="receipts/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    @property
    def receipt_name(self):
        return self.receipt.name.rsplit("/", 1)[-1] if self.receipt else ""


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="invoices")
    number = models.CharField(max_length=30, unique=True)
    issued_on = models.DateField()
    due_on = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_on", "-pk"]

    @property
    def subtotal(self):
        return sum((item.amount for item in self.items.all()), Decimal("0.00"))

    @property
    def total(self):
        return self.subtotal

    def get_absolute_url(self):
        return reverse("invoice_detail", kwargs={"pk": self.pk})


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    source_time_entry = models.OneToOneField(TimeEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice_item")
    source_expense = models.OneToOneField(Expense, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoice_item")
    description = models.CharField(max_length=240)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def amount(self):
        return self.quantity * self.rate
