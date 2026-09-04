from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from projects.models import Project
from projects.views import allowed
from projects.activity import record_activity
from notifications.services import notify
from .forms import ExpenseForm, InvoiceCreateForm, InvoiceForm, InvoiceItemFormSet, TimeEntryForm, TimerStartForm
from .models import ActiveTimer, Expense, Invoice, InvoiceItem, TimeEntry


@login_required
def timer_start(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if request.user != project.freelancer:
        raise PermissionDenied
    existing = ActiveTimer.objects.filter(user=request.user).select_related("project").first()
    if existing:
        messages.error(request, f"Stop your timer for {existing.project.title} before starting another.")
        return redirect(existing.project)
    form = TimerStartForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        timer = form.save(commit=False)
        timer.user, timer.project, timer.started_at = request.user, project, timezone.now()
        timer.save()
        messages.success(request, "Timer started.")
        return redirect(project)
    return render(request, "billing/timer_start.html", {"form": form, "project": project})


@login_required
@transaction.atomic
def timer_stop(request):
    if request.method != "POST":
        raise PermissionDenied
    timer = get_object_or_404(ActiveTimer.objects.select_for_update().select_related("project"), user=request.user)
    elapsed = Decimal(str((timezone.now() - timer.started_at).total_seconds())) / Decimal("3600")
    hours = min(Decimal("24.00"), max(Decimal("0.01"), elapsed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)))
    entry = TimeEntry.objects.create(project=timer.project, user=request.user, date=timezone.localdate(), hours=hours, description=timer.description, billable=timer.billable)
    project = timer.project
    timer.delete()
    record_activity(project, request.user, "time", f"Tracked {entry.hours} hours: {entry.description}")
    messages.success(request, f"Timer stopped. {entry.hours} hours added to your ledger.")
    return redirect(project)


@login_required
def expense_list(request):
    projects = Project.objects.for_user(request.user)
    expenses = Expense.objects.filter(project__in=projects).select_related("project", "user", "invoice_item__invoice")
    project_id = request.GET.get("project", "")
    billing = request.GET.get("billing", "")
    if project_id.isdigit():
        expenses = expenses.filter(project_id=project_id)
    if billing == "unbilled":
        expenses = expenses.filter(billable=True, invoice_item__isnull=True)
    elif billing in {"billable", "nonbillable"}:
        expenses = expenses.filter(billable=billing == "billable")
    total = expenses.aggregate(total=Sum("amount"))["total"] or 0
    return render(request, "billing/expense_list.html", {"expenses": expenses, "projects": projects, "total": total, "selected_project": project_id, "selected_billing": billing})


@login_required
def expense_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if request.user != project.freelancer:
        raise PermissionDenied
    form = ExpenseForm(request.POST or None, request.FILES or None, initial={"date": date.today()})
    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False)
        expense.project, expense.user = project, request.user
        expense.save()
        record_activity(project, request.user, "expense", f"Recorded ${expense.amount} expense: {expense.description}")
        messages.success(request, "Expense recorded.")
        return redirect("expense_list")
    return render(request, "billing/expense_form.html", {"form": form, "project": project})


@login_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense.objects.select_related("project"), pk=pk)
    if request.user != expense.user or hasattr(expense, "invoice_item"):
        raise PermissionDenied
    form = ExpenseForm(request.POST or None, request.FILES or None, instance=expense)
    if request.method == "POST" and form.is_valid():
        expense = form.save()
        record_activity(expense.project, request.user, "expense", f"Updated expense: {expense.description}")
        messages.success(request, "Expense updated.")
        return redirect("expense_list")
    return render(request, "billing/expense_form.html", {"form": form, "project": expense.project, "editing": True})


@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense.objects.select_related("project"), pk=pk)
    if request.method != "POST" or request.user != expense.user or hasattr(expense, "invoice_item"):
        raise PermissionDenied
    project, description = expense.project, expense.description
    if expense.receipt:
        expense.receipt.delete(save=False)
    expense.delete()
    record_activity(project, request.user, "expense", f"Deleted expense: {description}")
    messages.success(request, "Expense deleted.")
    return redirect("expense_list")


@login_required
def expense_receipt(request, pk):
    expense = get_object_or_404(Expense.objects.select_related("project"), pk=pk)
    if not allowed(expense.project, request.user) or not expense.receipt:
        raise PermissionDenied
    return FileResponse(expense.receipt.open("rb"), as_attachment=True, filename=expense.receipt_name)


@login_required
def time_list(request):
    entries = TimeEntry.objects.filter(project__in=Project.objects.for_user(request.user)).select_related("project", "user", "invoice_item__invoice")
    projects = Project.objects.for_user(request.user)
    project_id = request.GET.get("project")
    billing = request.GET.get("billing")
    if project_id and project_id.isdigit():
        entries = entries.filter(project_id=project_id)
    if billing in {"billable", "nonbillable"}:
        entries = entries.filter(billable=billing == "billable")
    elif billing == "unbilled":
        entries = entries.filter(billable=True, invoice_item__isnull=True)
    total = entries.aggregate(value=Sum("hours"))["value"] or 0
    billable_total = entries.filter(billable=True).aggregate(value=Sum("hours"))["value"] or 0
    return render(request, "billing/time_list.html", {"entries": entries, "total": total, "billable_total": billable_total, "nonbillable_total": total - billable_total, "projects": projects, "selected_project": project_id or "", "selected_billing": billing or ""})


@login_required
def time_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not allowed(project, request.user) or request.user != project.freelancer:
        raise PermissionDenied
    form = TimeEntryForm(request.POST or None, initial={"date": date.today()})
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.project, entry.user = project, request.user
        entry.save()
        record_activity(project, request.user, "time", f"Logged {entry.hours} hours: {entry.description}")
        return redirect(project)
    return render(request, "billing/time_form.html", {"form": form, "project": project})


@login_required
def time_edit(request, pk):
    entry = get_object_or_404(TimeEntry.objects.select_related("project"), pk=pk)
    if request.user != entry.user or request.user != entry.project.freelancer or hasattr(entry, "invoice_item"):
        raise PermissionDenied
    form = TimeEntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        entry = form.save()
        record_activity(entry.project, request.user, "time", f"Updated time entry: {entry.description}")
        messages.success(request, "Time entry updated.")
        return redirect("time_list")
    return render(request, "billing/time_form.html", {"form": form, "project": entry.project, "editing": True})


@login_required
def time_delete(request, pk):
    entry = get_object_or_404(TimeEntry.objects.select_related("project"), pk=pk)
    if request.method != "POST" or request.user != entry.user or request.user != entry.project.freelancer or hasattr(entry, "invoice_item"):
        raise PermissionDenied
    project, description = entry.project, entry.description
    entry.delete()
    record_activity(project, request.user, "time", f"Deleted time entry: {description}")
    messages.success(request, "Time entry deleted.")
    return redirect("time_list")


@login_required
def invoice_list(request):
    invoices = Invoice.objects.filter(project__in=Project.objects.for_user(request.user)).select_related("project", "project__client").prefetch_related("items")
    return render(request, "billing/invoice_list.html", {"invoices": invoices})


@login_required
@transaction.atomic
def invoice_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if request.user != project.freelancer:
        raise PermissionDenied
    initial = {"number": f"INV-{date.today():%Y%m}-{Invoice.objects.count()+1:03d}", "issued_on": date.today(), "due_on": date.today() + timedelta(days=14)}
    form = InvoiceCreateForm(request.POST or None, initial=initial, project=project, freelancer=request.user)
    invoice = Invoice(project=project)
    formset = InvoiceItemFormSet(request.POST or None, instance=invoice)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        invoice = form.save(commit=False)
        invoice.project = project
        invoice.save()
        formset.instance = invoice
        formset.save()
        rate = form.cleaned_data.get("hourly_rate")
        for entry in form.cleaned_data.get("time_entries", []):
            InvoiceItem.objects.create(invoice=invoice, source_time_entry=entry, description=f"{entry.date:%b %d} — {entry.description}", quantity=entry.hours, rate=rate)
        for expense in form.cleaned_data.get("expenses", []):
            InvoiceItem.objects.create(invoice=invoice, source_expense=expense, description=f"Expense: {expense.vendor} — {expense.description}", quantity=1, rate=expense.amount)
        record_activity(project, request.user, "invoice", f"Created invoice {invoice.number}")
        if invoice.status != Invoice.Status.DRAFT:
            notify(project.client, request.user, "invoice", f"Invoice {invoice.number} is ready", invoice.get_absolute_url())
        return redirect(invoice)
    return render(request, "billing/invoice_form.html", {"form": form, "formset": formset, "project": project, "creating": True})


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("project", "project__freelancer", "project__client").prefetch_related("items"), pk=pk)
    if not allowed(invoice.project, request.user):
        raise PermissionDenied
    return render(request, "billing/invoice_detail.html", {"invoice": invoice})


@login_required
@transaction.atomic
def invoice_edit(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("project"), pk=pk)
    if request.user != invoice.project.freelancer or invoice.status != Invoice.Status.DRAFT:
        raise PermissionDenied
    form = InvoiceForm(request.POST or None, instance=invoice)
    formset = InvoiceItemFormSet(request.POST or None, instance=invoice)
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        form.save(); formset.save()
        record_activity(invoice.project, request.user, "invoice", f"Updated draft invoice {invoice.number}")
        messages.success(request, "Draft invoice updated.")
        return redirect(invoice)
    return render(request, "billing/invoice_form.html", {"form": form, "formset": formset, "project": invoice.project, "editing": True})


@login_required
def invoice_delete(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("project"), pk=pk)
    if request.method != "POST" or request.user != invoice.project.freelancer or invoice.status != Invoice.Status.DRAFT:
        raise PermissionDenied
    project, number = invoice.project, invoice.number
    invoice.delete()
    record_activity(project, request.user, "invoice", f"Deleted draft invoice {number}")
    messages.success(request, "Draft invoice deleted.")
    return redirect("invoice_list")


@login_required
def invoice_status(request, pk):
    invoice = get_object_or_404(Invoice.objects.select_related("project"), pk=pk)
    if request.method != "POST" or not allowed(invoice.project, request.user):
        raise PermissionDenied
    status = request.POST.get("status")
    permitted = {Invoice.Status.SENT} if request.user == invoice.project.freelancer else {Invoice.Status.PAID}
    if status in permitted:
        invoice.status = status
        invoice.save(update_fields=["status"])
        record_activity(invoice.project, request.user, "invoice", f"Marked invoice {invoice.number} {invoice.get_status_display().lower()}")
        recipient = invoice.project.client if request.user == invoice.project.freelancer else invoice.project.freelancer
        notify(recipient, request.user, "invoice", f"Invoice {invoice.number} marked {invoice.get_status_display().lower()}", invoice.get_absolute_url())
        messages.success(request, f"Invoice marked {invoice.get_status_display().lower()}.")
    return redirect(invoice)
