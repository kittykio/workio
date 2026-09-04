from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
import uuid
from django.utils import timezone


class ProjectQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(Q(freelancer=user) | Q(client=user)).distinct()


class Project(models.Model):
    class Status(models.TextChoices):
        PLANNING = "planning", "Planning"
        ACTIVE = "active", "In progress"
        REVIEW = "review", "In review"
        COMPLETED = "completed", "Completed"

    class WorkMode(models.TextChoices):
        FLEXIBLE = "flexible", "Flexible / not applicable"
        REMOTE = "remote", "Remote"
        ONSITE = "onsite", "On-site"
        HYBRID = "hybrid", "Hybrid"

    class BillingType(models.TextChoices):
        HOURLY = "hourly", "Hourly"
        FIXED = "fixed", "Fixed price"
        SESSION = "session", "Per appointment or session"
        MILESTONE = "milestone", "By stage or milestone"
        RECURRING = "recurring", "Recurring"
        CUSTOM = "custom", "Custom / not yet decided"

    class Recurrence(models.TextChoices):
        NONE = "none", "Does not repeat"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        CUSTOM = "custom", "Custom schedule"

    class PricingUnit(models.TextChoices):
        HOUR = "hour", "Hour"
        SESSION = "session", "Session / appointment"
        DAY = "day", "Day"
        ITEM = "item", "Item / product"
        MILE = "mile", "Mile / kilometer"
        WORD = "word", "Word"
        DELIVERY = "delivery", "Delivery / trip"
        FIXED = "fixed", "Whole engagement"
        CUSTOM = "custom", "Custom unit"

    title = models.CharField(max_length=140)
    description = models.TextField()
    freelancer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="freelance_projects")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_projects")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNING)
    work_type = models.CharField(max_length=100, blank=True)
    work_mode = models.CharField(max_length=12, choices=WorkMode.choices, default=WorkMode.FLEXIBLE)
    billing_type = models.CharField(max_length=12, choices=BillingType.choices, default=BillingType.CUSTOM)
    location = models.CharField(max_length=180, blank=True)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    recurrence = models.CharField(max_length=12, choices=Recurrence.choices, default=Recurrence.NONE)
    pricing_unit = models.CharField(max_length=12, choices=PricingUnit.choices, default=PricingUnit.FIXED)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tags = models.CharField(max_length=300, blank=True)
    intake_notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    custom_details = models.JSONField(default=dict, blank=True)
    organization = models.CharField(max_length=160, blank=True)
    contact_name = models.CharField(max_length=140, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    custom_status = models.CharField(max_length=60, blank=True)
    workflow_stage = models.ForeignKey("WorkflowStage", on_delete=models.SET_NULL, null=True, blank=True, related_name="projects")
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = ProjectQuerySet.as_manager()

    class Meta:
        ordering = ["-updated_at"]

    def get_absolute_url(self):
        return reverse("project_detail", kwargs={"pk": self.pk})

    def __str__(self):
        return self.title


class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    milestone = models.ForeignKey("Milestone", on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
    title = models.CharField(max_length=160)
    completed = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Milestone(models.Model):
    class ReviewStatus(models.TextChoices):
        DRAFT = "draft", "In progress"
        SUBMITTED = "submitted", "Awaiting review"
        CHANGES = "changes", "Changes requested"
        APPROVED = "approved", "Approved"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    review_status = models.CharField(max_length=12, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    review_note = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "due_date", "pk"]

    def __str__(self):
        return self.title


class ProjectComment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_comments")
    body = models.TextField(max_length=3000)
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ProjectFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="files")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_files")
    file = models.FileField(upload_to="project_files/%Y/%m/")
    label = models.CharField(max_length=140, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        return self.file.name.rsplit("/", 1)[-1]


class ProjectInvitation(models.Model):
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_invitations_sent")
    client_email = models.EmailField()
    client_name = models.CharField(max_length=120, blank=True)
    project_title = models.CharField(max_length=140)
    project_description = models.TextField()
    work_type = models.CharField(max_length=100, blank=True)
    work_mode = models.CharField(max_length=12, choices=Project.WorkMode.choices, default=Project.WorkMode.FLEXIBLE)
    billing_type = models.CharField(max_length=12, choices=Project.BillingType.choices, default=Project.BillingType.CUSTOM)
    location = models.CharField(max_length=180, blank=True)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    recurrence = models.CharField(max_length=12, choices=Project.Recurrence.choices, default=Project.Recurrence.NONE)
    pricing_unit = models.CharField(max_length=12, choices=Project.PricingUnit.choices, default=Project.PricingUnit.FIXED)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tags = models.CharField(max_length=300, blank=True)
    intake_notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    custom_details = models.JSONField(default=dict, blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    deadline = models.DateField(null=True, blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    accepted_project = models.OneToOneField(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="source_invitation")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def status(self):
        if self.accepted_project_id:
            return "Accepted"
        return "Expired" if self.is_expired else "Pending"

    def get_absolute_url(self):
        return reverse("invitation_detail", kwargs={"token": self.token})


class WorkTemplate(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="work_templates")
    name = models.CharField(max_length=100)
    work_type = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    work_mode = models.CharField(max_length=12, choices=Project.WorkMode.choices, default=Project.WorkMode.FLEXIBLE)
    billing_type = models.CharField(max_length=12, choices=Project.BillingType.choices, default=Project.BillingType.CUSTOM)
    recurrence = models.CharField(max_length=12, choices=Project.Recurrence.choices, default=Project.Recurrence.NONE)
    pricing_unit = models.CharField(max_length=12, choices=Project.PricingUnit.choices, default=Project.PricingUnit.FIXED)
    default_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    default_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    default_tags = models.CharField(max_length=300, blank=True)
    default_terms = models.TextField(blank=True)
    checklist = models.TextField(blank=True, help_text="One checklist item per line.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["owner", "name"], name="unique_work_template_name_per_owner")]

    def __str__(self):
        return self.name


class IntakeQuestion(models.Model):
    class Kind(models.TextChoices):
        TEXT = "text", "Short text"
        LONG_TEXT = "long_text", "Long text"
        NUMBER = "number", "Number"
        DATE = "date", "Date"
        YES_NO = "yes_no", "Yes / no"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="intake_questions")
    label = models.CharField(max_length=180)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.TEXT)
    required = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]


class IntakeResponse(models.Model):
    question = models.OneToOneField(IntakeQuestion, on_delete=models.CASCADE, related_name="response")
    answered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="intake_responses")
    value = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class AutomationRule(models.Model):
    class Trigger(models.TextChoices):
        BEFORE_START = "before_start", "Before scheduled start"
        TERMS_ACCEPTED = "terms_accepted", "When terms are accepted"
        WORK_COMPLETED = "work_completed", "When work is completed"

    class Recipient(models.TextChoices):
        CLIENT = "client", "Client"
        FREELANCER = "freelancer", "Freelancer"
        BOTH = "both", "Both participants"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="automation_rules")
    name = models.CharField(max_length=100)
    trigger = models.CharField(max_length=20, choices=Trigger.choices)
    days_before = models.PositiveSmallIntegerField(default=1, help_text="Used for scheduled-start reminders.")
    recipient = models.CharField(max_length=12, choices=Recipient.choices, default=Recipient.CLIENT)
    message = models.CharField(max_length=300, help_text="Use {work} to insert the work title.")
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["owner", "name"], name="unique_automation_name_per_owner")]


class AutomationRun(models.Model):
    rule = models.ForeignKey(AutomationRule, on_delete=models.CASCADE, related_name="runs")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="automation_runs")
    event_key = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["rule", "project", "event_key"], name="unique_automation_run")]


class Proposal(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Awaiting response"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="proposals")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="proposals_created")
    title = models.CharField(max_length=160)
    scope = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pricing_unit = models.CharField(max_length=12, choices=Project.PricingUnit.choices, default=Project.PricingUnit.FIXED)
    terms = models.TextField(blank=True)
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    sent_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    response_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_expired(self):
        return bool(self.valid_until and self.valid_until < timezone.localdate() and self.status == self.Status.SENT)


class WorkOccurrence(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="occurrences")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.SCHEDULED)
    checked_in_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="work_checkins")
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at", "pk"]
        constraints = [models.UniqueConstraint(fields=["project", "starts_at"], name="unique_work_occurrence_start")]


class SavedWorkView(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_work_views")
    name = models.CharField(max_length=80)
    query = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=60, blank=True)
    work_type = models.CharField(max_length=100, blank=True)
    billing_type = models.CharField(max_length=12, blank=True)
    work_mode = models.CharField(max_length=12, blank=True)
    tags = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["owner", "name"], name="unique_saved_work_view_name")]


class PaymentInstallment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        WAIVED = "waived", "Waived"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="payment_installments")
    label = models.CharField(max_length=140)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "pk"]

    @property
    def is_overdue(self):
        return bool(self.status == self.Status.PENDING and self.due_date and self.due_date < timezone.localdate())


class ProposalItem(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=240)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=12, choices=Project.PricingUnit.choices, default=Project.PricingUnit.CUSTOM)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "pk"]

    @property
    def amount(self):
        return self.quantity * self.rate


class WorkflowStage(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="workflow_stages")
    name = models.CharField(max_length=60)
    color = models.CharField(max_length=7, default="#174c3c")
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "pk"]
        constraints = [models.UniqueConstraint(fields=["owner", "name"], name="unique_workflow_stage_name")]

    def __str__(self):
        return self.name


class ServiceOffering(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_offerings")
    title = models.CharField(max_length=140)
    description = models.TextField()
    work_type = models.CharField(max_length=100, blank=True)
    billing_type = models.CharField(max_length=12, choices=Project.BillingType.choices, default=Project.BillingType.CUSTOM)
    pricing_unit = models.CharField(max_length=12, choices=Project.PricingUnit.choices, default=Project.PricingUnit.CUSTOM)
    starting_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    work_mode = models.CharField(max_length=12, choices=Project.WorkMode.choices, default=Project.WorkMode.FLEXIBLE)
    typical_duration = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]


class ServiceInquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        DISCUSSING = "discussing", "Discussing"
        CONVERTED = "converted", "Converted to work"
        CLOSED = "closed", "Closed"

    offering = models.ForeignKey(ServiceOffering, on_delete=models.CASCADE, related_name="inquiries")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_inquiries")
    message = models.TextField()
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=180, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    converted_project = models.OneToOneField(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="source_inquiry")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ProjectActivity(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="activities")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="project_activities")
    kind = models.CharField(max_length=30)
    text = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
