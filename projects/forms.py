from django import forms
from accounts.models import User
from .models import AutomationRule, IntakeQuestion, IntakeResponse, Milestone, PaymentInstallment, Project, ProjectComment, ProjectFile, ProjectInvitation, Proposal, ProposalItem, SavedWorkView, ServiceInquiry, ServiceOffering, Task, WorkflowStage, WorkOccurrence, WorkTemplate


class CustomDetailsMixin:
    custom_details_text = forms.CharField(
        required=False,
        label="Custom details",
        help_text="Add one detail per line, such as Vehicle: 12-foot truck or Language: Japanese.",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Detail: Value"}),
    )

    def _set_custom_details_initial(self):
        details = getattr(self.instance, "custom_details", {}) or {}
        self.fields["custom_details_text"].initial = "\n".join(f"{key}: {value}" for key, value in details.items())

    def clean_custom_details_text(self):
        details = {}
        for line in self.cleaned_data.get("custom_details_text", "").splitlines():
            if not line.strip():
                continue
            if ":" not in line:
                raise forms.ValidationError("Each custom detail must use the format “Label: Value”.")
            key, value = line.split(":", 1)
            key = key.strip()
            if not key:
                raise forms.ValidationError("Each custom detail needs a label.")
            details[key] = value.strip()
        return details

    def save(self, commit=True):
        self.instance.custom_details = self.cleaned_data.get("custom_details_text", {})
        return super().save(commit=commit)


class ProjectForm(CustomDetailsMixin, forms.ModelForm):
    custom_details_text = forms.CharField(required=False, label="Custom details", help_text="Add one detail per line, such as Vehicle: 12-foot truck or Language: Japanese.", widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Detail: Value"}))

    class Meta:
        model = Project
        fields = ("title", "work_type", "description", "client", "organization", "contact_name", "contact_email", "contact_phone", "work_mode", "location", "scheduled_start", "scheduled_end", "recurrence", "billing_type", "pricing_unit", "quantity", "unit_rate", "deposit_amount", "budget", "deadline", "tags", "intake_notes", "terms", "status", "workflow_stage", "custom_status")
        widgets = {"description": forms.Textarea(attrs={"rows": 5}), "deadline": forms.DateInput(attrs={"type": "date"}), "scheduled_start": forms.DateTimeInput(attrs={"type": "datetime-local"}), "scheduled_end": forms.DateTimeInput(attrs={"type": "datetime-local"}), "intake_notes": forms.Textarea(attrs={"rows": 4}), "terms": forms.Textarea(attrs={"rows": 5})}
        labels = {
            "title": "Work title",
            "work_type": "Type of work or service",
            "location": "Location or meeting details",
            "billing_type": "How is this work billed?",
            "budget": "Estimated value or budget",
            "deadline": "Target or end date",
            "intake_notes": "Requirements and intake information",
            "terms": "Scope, terms, or agreement",
            "tags": "Tags (comma-separated)",
            "custom_status": "Custom workflow label",
        }
        help_texts = {"work_type": "For example: photo session, childcare booking, design, tutoring, repair, or consulting."}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = User.objects.filter(role=User.Role.CLIENT)
        owner = user or getattr(self.instance, "freelancer", None)
        self.fields["workflow_stage"].queryset = WorkflowStage.objects.filter(owner=owner) if getattr(owner, "pk", None) else WorkflowStage.objects.none()
        self.fields["work_mode"].required = False
        self.fields["billing_type"].required = False
        self.fields["recurrence"].required = False
        self.fields["pricing_unit"].required = False
        self.fields["deposit_amount"].required = False
        self._set_custom_details_initial()

    def clean_work_mode(self):
        return self.cleaned_data.get("work_mode") or Project.WorkMode.FLEXIBLE

    def clean_billing_type(self):
        return self.cleaned_data.get("billing_type") or Project.BillingType.CUSTOM

    def clean_recurrence(self):
        return self.cleaned_data.get("recurrence") or Project.Recurrence.NONE

    def clean_pricing_unit(self):
        return self.cleaned_data.get("pricing_unit") or Project.PricingUnit.FIXED

    def clean_deposit_amount(self):
        return self.cleaned_data.get("deposit_amount") or 0

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ("title", "milestone", "due_date")
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["milestone"].queryset = Milestone.objects.filter(project=project) if project else Milestone.objects.none()


class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = ("title", "description", "due_date")
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}), "description": forms.Textarea(attrs={"rows": 2})}


class MilestoneReviewForm(forms.Form):
    decision = forms.ChoiceField(choices=(("approved", "Approve milestone"), ("changes", "Request changes")), widget=forms.RadioSelect)
    note = forms.CharField(required=False, max_length=1500, widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Share feedback with the freelancer…"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == "changes" and not cleaned.get("note", "").strip():
            self.add_error("note", "Please explain what needs to change.")
        return cleaned


class CommentForm(forms.ModelForm):
    class Meta:
        model = ProjectComment
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"rows": 3, "placeholder": "Share an update or ask a question…"})}


class ProjectFileForm(forms.ModelForm):
    class Meta:
        model = ProjectFile
        fields = ("file", "label")

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > 15 * 1024 * 1024:
            raise forms.ValidationError("Files must be 15 MB or smaller.")
        return upload


class InvitationForm(CustomDetailsMixin, forms.ModelForm):
    custom_details_text = forms.CharField(required=False, label="Custom details", help_text="Add one detail per line, such as Vehicle: 12-foot truck or Language: Japanese.", widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Detail: Value"}))

    class Meta:
        model = ProjectInvitation
        fields = ("client_email", "client_name", "project_title", "work_type", "project_description", "work_mode", "location", "scheduled_start", "scheduled_end", "recurrence", "billing_type", "pricing_unit", "quantity", "unit_rate", "deposit_amount", "budget", "deadline", "tags", "intake_notes", "terms")
        widgets = {"project_description": forms.Textarea(attrs={"rows": 5}), "deadline": forms.DateInput(attrs={"type": "date"}), "scheduled_start": forms.DateTimeInput(attrs={"type": "datetime-local"}), "scheduled_end": forms.DateTimeInput(attrs={"type": "datetime-local"}), "intake_notes": forms.Textarea(attrs={"rows": 4}), "terms": forms.Textarea(attrs={"rows": 5})}
        labels = {
            "project_title": "Work title",
            "work_type": "Type of work or service",
            "project_description": "What does the work involve?",
            "location": "Location or meeting details",
            "billing_type": "How is this work billed?",
            "budget": "Estimated value or budget",
            "deadline": "Target or end date",
            "intake_notes": "Requirements and intake information",
            "terms": "Scope, terms, or agreement",
            "tags": "Tags (comma-separated)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["work_mode"].required = False
        self.fields["billing_type"].required = False
        self.fields["recurrence"].required = False
        self.fields["pricing_unit"].required = False
        self.fields["deposit_amount"].required = False
        self._set_custom_details_initial()

    def clean_work_mode(self):
        return self.cleaned_data.get("work_mode") or Project.WorkMode.FLEXIBLE

    def clean_billing_type(self):
        return self.cleaned_data.get("billing_type") or Project.BillingType.CUSTOM

    def clean_recurrence(self):
        return self.cleaned_data.get("recurrence") or Project.Recurrence.NONE

    def clean_pricing_unit(self):
        return self.cleaned_data.get("pricing_unit") or Project.PricingUnit.FIXED

    def clean_deposit_amount(self):
        return self.cleaned_data.get("deposit_amount") or 0

    def clean_client_email(self):
        return self.cleaned_data["client_email"].strip().lower()


class WorkTemplateForm(forms.ModelForm):
    class Meta:
        model = WorkTemplate
        fields = ("name", "work_type", "description", "work_mode", "billing_type", "recurrence", "pricing_unit", "default_rate", "default_deposit", "default_tags", "default_terms", "checklist")
        widgets = {"description": forms.Textarea(attrs={"rows": 3}), "default_terms": forms.Textarea(attrs={"rows": 4}), "checklist": forms.Textarea(attrs={"rows": 6, "placeholder": "One reusable checklist item per line"})}


class IntakeQuestionForm(forms.ModelForm):
    class Meta:
        model = IntakeQuestion
        fields = ("label", "kind", "required")


class IntakeResponseForm(forms.Form):
    def __init__(self, *args, questions, **kwargs):
        super().__init__(*args, **kwargs)
        self.questions = list(questions)
        for question in self.questions:
            existing = getattr(question, "response", None)
            options = {"label": question.label, "required": question.required, "initial": existing.value if existing else ""}
            if question.kind == IntakeQuestion.Kind.LONG_TEXT:
                field = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), **options)
            elif question.kind == IntakeQuestion.Kind.NUMBER:
                field = forms.DecimalField(**options)
            elif question.kind == IntakeQuestion.Kind.DATE:
                field = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), **options)
            elif question.kind == IntakeQuestion.Kind.YES_NO:
                field = forms.ChoiceField(choices=(("", "Select…"), ("yes", "Yes"), ("no", "No")), **options)
            else:
                field = forms.CharField(**options)
            self.fields[f"question_{question.pk}"] = field

    def save(self, user):
        for question in self.questions:
            value = self.cleaned_data.get(f"question_{question.pk}", "")
            IntakeResponse.objects.update_or_create(question=question, defaults={"answered_by": user, "value": str(value or "")})


class AutomationRuleForm(forms.ModelForm):
    class Meta:
        model = AutomationRule
        fields = ("name", "trigger", "days_before", "recipient", "message", "enabled")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("trigger") != AutomationRule.Trigger.BEFORE_START:
            cleaned["days_before"] = 0
        return cleaned


class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ("title", "scope", "amount", "deposit_amount", "pricing_unit", "terms", "valid_until")
        widgets = {"scope": forms.Textarea(attrs={"rows": 6}), "terms": forms.Textarea(attrs={"rows": 5}), "valid_until": forms.DateInput(attrs={"type": "date"})}

    def clean(self):
        cleaned = super().clean()
        amount = cleaned.get("amount")
        deposit = cleaned.get("deposit_amount") or 0
        if amount is not None and deposit > amount:
            self.add_error("deposit_amount", "The deposit cannot exceed the proposal amount.")
        return cleaned


class ProposalResponseForm(forms.Form):
    decision = forms.ChoiceField(choices=((Proposal.Status.ACCEPTED, "Accept proposal"), (Proposal.Status.DECLINED, "Decline proposal")), widget=forms.RadioSelect)
    note = forms.CharField(required=False, label="Response note", widget=forms.Textarea(attrs={"rows": 4}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == Proposal.Status.DECLINED and not cleaned.get("note", "").strip():
            self.add_error("note", "Please explain why you are declining this proposal.")
        return cleaned


class WorkOccurrenceForm(forms.ModelForm):
    class Meta:
        model = WorkOccurrence
        fields = ("starts_at", "ends_at", "location", "status", "notes")
        widgets = {"starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "notes": forms.Textarea(attrs={"rows": 4})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("starts_at") and cleaned.get("ends_at") and cleaned["ends_at"] <= cleaned["starts_at"]:
            self.add_error("ends_at", "End time must be after start time.")
        return cleaned


class SavedWorkViewForm(forms.ModelForm):
    class Meta:
        model = SavedWorkView
        fields = ("name",)


class PaymentInstallmentForm(forms.ModelForm):
    class Meta:
        model = PaymentInstallment
        fields = ("label", "amount", "due_date", "notes")
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}), "notes": forms.Textarea(attrs={"rows": 3})}

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        return amount


class ProposalItemForm(forms.ModelForm):
    class Meta:
        model = ProposalItem
        fields = ("description", "quantity", "unit", "rate")

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return quantity

    def clean_rate(self):
        rate = self.cleaned_data["rate"]
        if rate < 0:
            raise forms.ValidationError("Rate cannot be negative.")
        return rate


class WorkflowStageForm(forms.ModelForm):
    class Meta:
        model = WorkflowStage
        fields = ("name", "color", "order")
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}


class ServiceOfferingForm(forms.ModelForm):
    class Meta:
        model = ServiceOffering
        fields = ("title", "description", "work_type", "billing_type", "pricing_unit", "starting_price", "work_mode", "typical_duration", "active")
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}


class ServiceInquiryForm(forms.ModelForm):
    class Meta:
        model = ServiceInquiry
        fields = ("message", "budget", "preferred_date", "location")
        widgets = {"message": forms.Textarea(attrs={"rows": 5, "placeholder": "Describe what you need, timing, quantity, and any important details."}), "preferred_date": forms.DateInput(attrs={"type": "date"})}
