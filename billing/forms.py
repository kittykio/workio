from django import forms
from django.forms import inlineformset_factory
from .models import ActiveTimer, Expense, Invoice, InvoiceItem, TimeEntry


class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ("date", "hours", "description", "billable")
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "hours": forms.NumberInput(attrs={"step": "0.25", "min": "0.25"})}

    def clean_hours(self):
        hours = self.cleaned_data["hours"]
        if hours <= 0 or hours > 24:
            raise forms.ValidationError("Enter between 0.25 and 24 hours.")
        return hours


class TimerStartForm(forms.ModelForm):
    class Meta:
        model = ActiveTimer
        fields = ("description", "billable")
        widgets = {"description": forms.TextInput(attrs={"placeholder": "What are you working on?", "autofocus": True})}


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ("date", "vendor", "description", "amount", "billable", "receipt")
        widgets = {"date": forms.DateInput(attrs={"type": "date"}), "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"})}

    def clean_receipt(self):
        receipt = self.cleaned_data.get("receipt")
        if receipt and receipt.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Receipts must be 10 MB or smaller.")
        return receipt


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ("number", "issued_on", "due_on", "status", "notes")
        widgets = {"issued_on": forms.DateInput(attrs={"type": "date"}), "due_on": forms.DateInput(attrs={"type": "date"}), "notes": forms.Textarea(attrs={"rows": 3})}


class InvoiceCreateForm(InvoiceForm):
    time_entries = forms.ModelMultipleChoiceField(queryset=TimeEntry.objects.none(), required=False, widget=forms.CheckboxSelectMultiple, help_text="Selected entries become individual invoice lines.")
    expenses = forms.ModelMultipleChoiceField(queryset=Expense.objects.none(), required=False, widget=forms.CheckboxSelectMultiple, help_text="Selected expenses are billed at their exact amount.")
    hourly_rate = forms.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=10, help_text="Applied to all selected time entries.")

    def __init__(self, *args, project=None, freelancer=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields["time_entries"].queryset = TimeEntry.objects.filter(project=project, billable=True, invoice_item__isnull=True).order_by("date", "pk")
            self.fields["expenses"].queryset = Expense.objects.filter(project=project, billable=True, invoice_item__isnull=True).order_by("date", "pk")
        if freelancer and freelancer.hourly_rate is not None:
            self.fields["hourly_rate"].initial = freelancer.hourly_rate

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("time_entries") and cleaned.get("hourly_rate") is None:
            self.add_error("hourly_rate", "Enter an hourly rate for the selected time entries.")
        return cleaned


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ("description", "quantity", "rate")
        widgets = {"quantity": forms.NumberInput(attrs={"step": "0.25"}), "rate": forms.NumberInput(attrs={"step": "0.01"})}

    def has_changed(self):
        if self.is_bound and not self.instance.pk:
            description = self.data.get(self.add_prefix("description"), "").strip()
            rate = self.data.get(self.add_prefix("rate"), "").strip()
            if not description and not rate:
                return False
        return super().has_changed()


InvoiceItemFormSet = inlineformset_factory(Invoice, InvoiceItem, form=InvoiceItemForm, extra=3, can_delete=True)
