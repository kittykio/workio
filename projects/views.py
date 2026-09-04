from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count, Q, Sum
from django.urls import reverse
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta, timezone as dt_timezone
from decimal import Decimal
from notifications.services import notify
from accounts.models import User
from .forms import AutomationRuleForm, CommentForm, IntakeQuestionForm, IntakeResponseForm, InvitationForm, MilestoneForm, MilestoneReviewForm, PaymentInstallmentForm, ProjectFileForm, ProjectForm, ProposalForm, ProposalItemForm, ProposalResponseForm, SavedWorkViewForm, ServiceInquiryForm, ServiceOfferingForm, TaskForm, WorkflowStageForm, WorkOccurrenceForm, WorkTemplateForm
from .models import AutomationRule, IntakeQuestion, Milestone, PaymentInstallment, Project, ProjectComment, ProjectFile, ProjectInvitation, Proposal, ProposalItem, SavedWorkView, ServiceInquiry, ServiceOffering, Task, WorkflowStage, WorkOccurrence, WorkTemplate
from .activity import record_activity
from .automations import run_event_automations
from .scheduling import generate_occurrences

def allowed(project, user):
    return user in (project.freelancer, project.client)

@login_required
def project_list(request):
    projects = Project.objects.for_user(request.user).select_related("freelancer", "client")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    work_type = request.GET.get("work_type", "").strip()
    billing_type = request.GET.get("billing_type", "").strip()
    work_mode = request.GET.get("work_mode", "").strip()
    tags = request.GET.get("tags", "").strip()
    saved_id = request.GET.get("saved", "").strip()
    if saved_id:
        saved = get_object_or_404(SavedWorkView, pk=saved_id, owner=request.user)
        query, status, work_type, billing_type, work_mode, tags = saved.query, saved.status, saved.work_type, saved.billing_type, saved.work_mode, saved.tags
    if query:
        projects = projects.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(client__first_name__icontains=query) | Q(client__last_name__icontains=query) | Q(freelancer__first_name__icontains=query) | Q(freelancer__last_name__icontains=query)).distinct()
    if status in Project.Status.values:
        projects = projects.filter(status=status)
    elif status:
        projects = projects.filter(custom_status__iexact=status)
    if work_type:
        projects = projects.filter(work_type__iexact=work_type)
    if billing_type in Project.BillingType.values:
        projects = projects.filter(billing_type=billing_type)
    if work_mode in Project.WorkMode.values:
        projects = projects.filter(work_mode=work_mode)
    if tags:
        projects = projects.filter(tags__icontains=tags)
    all_projects = Project.objects.for_user(request.user)
    context = {
        "projects": projects, "query": query, "selected_status": status, "selected_work_type": work_type,
        "selected_billing_type": billing_type, "selected_work_mode": work_mode, "selected_tags": tags,
        "statuses": Project.Status.choices, "billing_types": Project.BillingType.choices, "work_modes": Project.WorkMode.choices,
        "work_types": all_projects.exclude(work_type="").values_list("work_type", flat=True).distinct().order_by("work_type"),
        "saved_views": request.user.saved_work_views.all(), "save_view_form": SavedWorkViewForm(),
    }
    return render(request, "projects/list.html", context)


@login_required
def saved_view_create(request):
    if request.method != "POST":
        raise PermissionDenied
    form = SavedWorkViewForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.owner = request.user
        item.query = request.POST.get("q", "").strip()
        item.status = request.POST.get("status", "").strip()
        item.work_type = request.POST.get("work_type", "").strip()
        item.billing_type = request.POST.get("billing_type", "").strip()
        item.work_mode = request.POST.get("work_mode", "").strip()
        item.tags = request.POST.get("tags", "").strip()
        item.save()
        messages.success(request, "Saved work view created.")
    return redirect("project_list")


@login_required
def saved_view_delete(request, view_pk):
    item = get_object_or_404(SavedWorkView, pk=view_pk, owner=request.user)
    if request.method != "POST":
        raise PermissionDenied
    item.delete()
    messages.success(request, "Saved work view deleted.")
    return redirect("project_list")


@login_required
def workflow_board(request):
    if request.user.role != "freelancer":
        raise PermissionDenied
    stages = request.user.workflow_stages.prefetch_related("projects__client")
    unassigned = request.user.freelance_projects.filter(workflow_stage__isnull=True).select_related("client")
    return render(request, "projects/workflow_board.html", {"stages": stages, "unassigned": unassigned})


@login_required
def workflow_stage_create(request):
    if request.user.role != "freelancer" or request.method != "POST":
        raise PermissionDenied
    form = WorkflowStageForm(request.POST)
    if form.is_valid():
        stage = form.save(commit=False)
        stage.owner = request.user
        stage.save()
        messages.success(request, "Workflow stage created.")
    return redirect("workflow_board")


@login_required
def workflow_stage_edit(request, stage_pk):
    stage = get_object_or_404(WorkflowStage, pk=stage_pk, owner=request.user)
    form = WorkflowStageForm(request.POST or None, instance=stage)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Workflow stage updated.")
        return redirect("workflow_board")
    return render(request, "projects/workflow_stage_form.html", {"form": form, "stage": stage})


@login_required
def workflow_stage_delete(request, stage_pk):
    stage = get_object_or_404(WorkflowStage, pk=stage_pk, owner=request.user)
    if request.method != "POST":
        raise PermissionDenied
    stage.delete()
    messages.success(request, "Workflow stage deleted. Its work is now unassigned.")
    return redirect("workflow_board")


@login_required
def workflow_move(request, pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    if request.method != "POST":
        raise PermissionDenied
    stage_id = request.POST.get("stage", "")
    stage = get_object_or_404(WorkflowStage, pk=stage_id, owner=request.user) if stage_id else None
    project.workflow_stage = stage
    project.custom_status = stage.name if stage else ""
    project.save(update_fields=["workflow_stage", "custom_status", "updated_at"])
    record_activity(project, request.user, "workflow", f"Moved work to {stage.name if stage else 'Unassigned'}")
    return redirect("workflow_board")


def service_catalog(request, username):
    freelancer = get_object_or_404(User, username=username, role=User.Role.FREELANCER)
    offerings = freelancer.service_offerings.filter(active=True)
    if request.user == freelancer:
        offerings = freelancer.service_offerings.all()
    return render(request, "projects/service_catalog.html", {"freelancer": freelancer, "offerings": offerings})


@login_required
def service_create(request):
    if request.user.role != User.Role.FREELANCER:
        raise PermissionDenied
    form = ServiceOfferingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        offering = form.save(commit=False)
        offering.owner = request.user
        offering.save()
        messages.success(request, "Service offering published.")
        return redirect("service_catalog", username=request.user.username)
    return render(request, "projects/service_form.html", {"form": form, "heading": "Create service offering"})


@login_required
def service_edit(request, service_pk):
    offering = get_object_or_404(ServiceOffering, pk=service_pk, owner=request.user)
    form = ServiceOfferingForm(request.POST or None, instance=offering)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Service offering updated.")
        return redirect("service_catalog", username=request.user.username)
    return render(request, "projects/service_form.html", {"form": form, "heading": "Edit service offering"})


@login_required
def service_delete(request, service_pk):
    offering = get_object_or_404(ServiceOffering, pk=service_pk, owner=request.user)
    if request.method != "POST":
        raise PermissionDenied
    offering.delete()
    messages.success(request, "Service offering deleted.")
    return redirect("service_catalog", username=request.user.username)


@login_required
def service_inquire(request, service_pk):
    offering = get_object_or_404(ServiceOffering, pk=service_pk, active=True)
    if request.user.role != User.Role.CLIENT or request.user == offering.owner:
        raise PermissionDenied
    form = ServiceInquiryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        inquiry = form.save(commit=False)
        inquiry.offering = offering
        inquiry.client = request.user
        inquiry.save()
        notify(offering.owner, request.user, "inquiry", f"New inquiry for {offering.title}", reverse("inquiry_list"))
        messages.success(request, "Your inquiry was sent.")
        return redirect("service_catalog", username=offering.owner.username)
    return render(request, "projects/inquiry_form.html", {"form": form, "offering": offering})


@login_required
def inquiry_list(request):
    if request.user.role != User.Role.FREELANCER:
        raise PermissionDenied
    inquiries = ServiceInquiry.objects.filter(offering__owner=request.user).select_related("offering", "client", "converted_project")
    return render(request, "projects/inquiry_list.html", {"inquiries": inquiries})


@login_required
def inquiry_status(request, inquiry_pk, status):
    inquiry = get_object_or_404(ServiceInquiry, pk=inquiry_pk, offering__owner=request.user)
    if request.method != "POST" or status not in {ServiceInquiry.Status.DISCUSSING, ServiceInquiry.Status.CLOSED}:
        raise PermissionDenied
    inquiry.status = status
    inquiry.save(update_fields=["status"])
    notify(inquiry.client, request.user, "inquiry", f"Your inquiry for {inquiry.offering.title} is now {inquiry.get_status_display().lower()}", reverse("service_catalog", kwargs={"username": request.user.username}))
    return redirect("inquiry_list")


@login_required
def inquiry_convert(request, inquiry_pk):
    inquiry = get_object_or_404(ServiceInquiry.objects.select_related("offering", "client"), pk=inquiry_pk, offering__owner=request.user, converted_project__isnull=True)
    if request.method != "POST":
        raise PermissionDenied
    offering = inquiry.offering
    project = Project.objects.create(
        title=offering.title, description=f"{offering.description}\n\nClient request:\n{inquiry.message}", freelancer=request.user, client=inquiry.client,
        work_type=offering.work_type, work_mode=offering.work_mode, location=inquiry.location, billing_type=offering.billing_type,
        pricing_unit=offering.pricing_unit, budget=inquiry.budget or offering.starting_price or 0, deadline=inquiry.preferred_date,
    )
    inquiry.status = ServiceInquiry.Status.CONVERTED
    inquiry.converted_project = project
    inquiry.save(update_fields=["status", "converted_project"])
    record_activity(project, request.user, "inquiry", "Converted a service inquiry into work")
    notify(inquiry.client, request.user, "inquiry", f"Your inquiry became active work: {project.title}", project.get_absolute_url())
    messages.success(request, "Inquiry converted to work.")
    return redirect(project)


@login_required
def schedule_overview(request):
    occurrences = WorkOccurrence.objects.filter(project__in=Project.objects.for_user(request.user)).select_related("project", "project__freelancer", "project__client")
    selected = request.GET.get("range", "upcoming")
    if selected == "today":
        occurrences = occurrences.filter(starts_at__date=timezone.localdate())
    elif selected == "week":
        occurrences = occurrences.filter(starts_at__gte=timezone.now(), starts_at__lte=timezone.now() + timedelta(days=7))
    elif selected != "all":
        occurrences = occurrences.filter(starts_at__gte=timezone.now())
    return render(request, "projects/schedule_overview.html", {"occurrences": occurrences[:100], "selected_range": selected})


def send_invitation(request, invitation):
    invite_url = request.build_absolute_uri(invitation.get_absolute_url())
    send_mail(f"{invitation.inviter.display_name} invited you to Workio", f"You have been invited to collaborate on {invitation.project_title}.\n\nReview the invitation: {invite_url}", None, [invitation.client_email])


@login_required
def invitation_list(request):
    if request.user.role != "freelancer":
        raise PermissionDenied
    return render(request, "projects/invitation_list.html", {"invitations": request.user.project_invitations_sent.select_related("accepted_project")})


@login_required
def invitation_create(request):
    if request.user.role != "freelancer":
        raise PermissionDenied
    form = InvitationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        invitation = form.save(commit=False)
        invitation.inviter = request.user
        invitation.expires_at = timezone.now() + timedelta(days=14)
        invitation.save()
        send_invitation(request, invitation)
        from accounts.models import User
        existing = User.objects.filter(email__iexact=invitation.client_email, role=User.Role.CLIENT).first()
        if existing:
            notify(existing, request.user, "invitation", f"{request.user.display_name} invited you to {invitation.project_title}", invitation.get_absolute_url())
        messages.success(request, f"Invitation sent to {invitation.client_email}.")
        return redirect("invitation_list")
    return render(request, "projects/invitation_form.html", {"form": form})


def invitation_detail(request, token):
    invitation = get_object_or_404(ProjectInvitation.objects.select_related("inviter", "accepted_project"), token=token)
    return render(request, "projects/invitation_detail.html", {"invitation": invitation})


@login_required
def invitation_accept(request, token):
    invitation = get_object_or_404(ProjectInvitation.objects.select_related("inviter"), token=token)
    if request.method != "POST":
        raise PermissionDenied
    if invitation.accepted_project_id:
        return redirect(invitation.accepted_project)
    if invitation.is_expired:
        messages.error(request, "This invitation has expired.")
        return redirect(invitation)
    if request.user.email.lower() != invitation.client_email.lower() or request.user.role != "client":
        raise PermissionDenied
    project = Project.objects.create(
        title=invitation.project_title,
        description=invitation.project_description,
        freelancer=invitation.inviter,
        client=request.user,
        work_type=invitation.work_type,
        work_mode=invitation.work_mode,
        billing_type=invitation.billing_type,
        location=invitation.location,
        scheduled_start=invitation.scheduled_start,
        scheduled_end=invitation.scheduled_end,
        recurrence=invitation.recurrence,
        pricing_unit=invitation.pricing_unit,
        quantity=invitation.quantity,
        unit_rate=invitation.unit_rate,
        deposit_amount=invitation.deposit_amount,
        tags=invitation.tags,
        intake_notes=invitation.intake_notes,
        terms=invitation.terms,
        custom_details=invitation.custom_details,
        budget=invitation.budget,
        deadline=invitation.deadline,
        status=Project.Status.PLANNING,
    )
    record_activity(project, request.user, "project", "Accepted the project invitation")
    generate_occurrences(project)
    invitation.accepted_project = project
    invitation.save(update_fields=["accepted_project"])
    notify(invitation.inviter, request.user, "invitation", f"{request.user.display_name} accepted {invitation.project_title}", project.get_absolute_url())
    messages.success(request, "Invitation accepted. Welcome to the project.")
    return redirect(project)


@login_required
def invitation_resend(request, token):
    invitation = get_object_or_404(ProjectInvitation, token=token, inviter=request.user, accepted_project__isnull=True)
    if request.method != "POST":
        raise PermissionDenied
    invitation.expires_at = timezone.now() + timedelta(days=14)
    invitation.save(update_fields=["expires_at"])
    send_invitation(request, invitation)
    messages.success(request, "Invitation resent with a new 14-day expiry.")
    return redirect("invitation_list")


@login_required
def invitation_cancel(request, token):
    invitation = get_object_or_404(ProjectInvitation, token=token, inviter=request.user, accepted_project__isnull=True)
    if request.method != "POST":
        raise PermissionDenied
    invitation.delete()
    messages.success(request, "Invitation cancelled.")
    return redirect("invitation_list")

@login_required
def project_create(request):
    if request.user.role != "freelancer":
        raise PermissionDenied
    initial = {}
    template = None
    template_id = request.GET.get("template")
    if template_id:
        template = get_object_or_404(WorkTemplate, pk=template_id, owner=request.user)
        initial = {
            "work_type": template.work_type,
            "description": template.description,
            "work_mode": template.work_mode,
            "billing_type": template.billing_type,
            "recurrence": template.recurrence,
            "pricing_unit": template.pricing_unit,
            "unit_rate": template.default_rate,
            "deposit_amount": template.default_deposit,
            "tags": template.default_tags,
            "terms": template.default_terms,
        }
    form = ProjectForm(request.POST or None, initial=initial, user=request.user)
    if request.method == "POST" and form.is_valid():
        project = form.save(commit=False)
        project.freelancer = request.user
        project.save()
        generate_occurrences(project)
        if template:
            for line in template.checklist.splitlines():
                if line.strip():
                    Task.objects.create(project=project, title=line.strip())
        record_activity(project, request.user, "project", "Created the project")
        messages.success(request, "Project created successfully.")
        return redirect(project)
    return render(request, "projects/form.html", {"form": form})


@login_required
def template_list(request):
    if request.user.role != "freelancer":
        raise PermissionDenied
    return render(request, "projects/template_list.html", {"templates": request.user.work_templates.all()})


@login_required
def template_create(request):
    if request.user.role != "freelancer":
        raise PermissionDenied
    form = WorkTemplateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.owner = request.user
        item.save()
        messages.success(request, "Work template created.")
        return redirect("template_list")
    return render(request, "projects/template_form.html", {"form": form, "heading": "Create work template"})


@login_required
def template_edit(request, template_pk):
    item = get_object_or_404(WorkTemplate, pk=template_pk, owner=request.user)
    form = WorkTemplateForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Work template updated.")
        return redirect("template_list")
    return render(request, "projects/template_form.html", {"form": form, "heading": "Edit work template"})


@login_required
def template_delete(request, template_pk):
    item = get_object_or_404(WorkTemplate, pk=template_pk, owner=request.user)
    if request.method != "POST":
        raise PermissionDenied
    item.delete()
    messages.success(request, "Work template deleted.")
    return redirect("template_list")


@login_required
def automation_list(request):
    if request.user.role != "freelancer":
        raise PermissionDenied
    return render(request, "projects/automation_list.html", {"rules": request.user.automation_rules.all()})


@login_required
def automation_create(request):
    if request.user.role != "freelancer":
        raise PermissionDenied
    form = AutomationRuleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        rule = form.save(commit=False)
        rule.owner = request.user
        rule.save()
        messages.success(request, "Automation rule created.")
        return redirect("automation_list")
    return render(request, "projects/automation_form.html", {"form": form, "heading": "Create automation"})


@login_required
def automation_edit(request, rule_pk):
    rule = get_object_or_404(AutomationRule, pk=rule_pk, owner=request.user)
    form = AutomationRuleForm(request.POST or None, instance=rule)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Automation rule updated.")
        return redirect("automation_list")
    return render(request, "projects/automation_form.html", {"form": form, "heading": "Edit automation"})


@login_required
def automation_delete(request, rule_pk):
    rule = get_object_or_404(AutomationRule, pk=rule_pk, owner=request.user)
    if request.method != "POST":
        raise PermissionDenied
    rule.delete()
    messages.success(request, "Automation rule deleted.")
    return redirect("automation_list")


@login_required
def work_report(request):
    projects = Project.objects.for_user(request.user)
    by_status = list(projects.values("status").annotate(count=Count("id"), value=Sum("budget")).order_by("status"))
    by_type = projects.values("work_type").annotate(count=Count("id"), value=Sum("budget")).order_by("-value")[:10]
    by_billing = list(projects.values("billing_type").annotate(count=Count("id"), value=Sum("budget")).order_by("-value"))
    totals = projects.aggregate(count=Count("id"), value=Sum("budget"), deposits=Sum("deposit_amount"))
    payments = PaymentInstallment.objects.filter(project__in=projects).aggregate(scheduled=Sum("amount"), paid=Sum("amount", filter=Q(status=PaymentInstallment.Status.PAID)), outstanding=Sum("amount", filter=Q(status=PaymentInstallment.Status.PENDING)))
    status_labels = dict(Project.Status.choices)
    billing_labels = dict(Project.BillingType.choices)
    for row in by_status:
        row["label"] = status_labels.get(row["status"], row["status"])
    for row in by_billing:
        row["label"] = billing_labels.get(row["billing_type"], row["billing_type"])
    return render(request, "projects/report.html", {"by_status": by_status, "by_type": by_type, "by_billing": by_billing, "totals": totals, "payments": payments})


@login_required
def intake_manage(request, pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    form = IntakeQuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        question = form.save(commit=False)
        question.project = project
        question.order = project.intake_questions.count()
        question.save()
        messages.success(request, "Intake question added.")
        return redirect("intake_manage", pk=project.pk)
    return render(request, "projects/intake_manage.html", {"project": project, "form": form})


@login_required
def intake_question_delete(request, pk, question_pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    question = get_object_or_404(IntakeQuestion, pk=question_pk, project=project)
    if request.method != "POST":
        raise PermissionDenied
    question.delete()
    messages.success(request, "Intake question deleted.")
    return redirect("intake_manage", pk=project.pk)


@login_required
def intake_respond(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user):
        raise PermissionDenied
    questions = project.intake_questions.select_related("response")
    form = IntakeResponseForm(request.POST or None, questions=questions)
    if request.method == "POST" and form.is_valid():
        form.save(request.user)
        record_activity(project, request.user, "intake", "Updated the work requirements")
        other = project.client if request.user == project.freelancer else project.freelancer
        notify(other, request.user, "intake", f"Requirements updated for {project.title}", project.get_absolute_url())
        messages.success(request, "Requirements saved.")
        return redirect(project)
    return render(request, "projects/intake_respond.html", {"project": project, "form": form})


@login_required
def terms_accept(request, pk):
    project = get_object_or_404(Project, pk=pk, client=request.user)
    if request.method != "POST" or not project.terms:
        raise PermissionDenied
    project.terms_accepted_at = timezone.now()
    project.save(update_fields=["terms_accepted_at"])
    run_event_automations(project, AutomationRule.Trigger.TERMS_ACCEPTED)
    record_activity(project, request.user, "approval", "Accepted the work terms")
    notify(project.freelancer, request.user, "approval", f"{request.user.display_name} accepted the terms for {project.title}", project.get_absolute_url())
    messages.success(request, "Work terms accepted.")
    return redirect(project)


@login_required
def calendar_export(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user) or not project.scheduled_start:
        raise PermissionDenied

    def clean(value):
        return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")

    start = project.scheduled_start.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    end_value = project.scheduled_end or (project.scheduled_start + timedelta(hours=1))
    end = end_value.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    body = "\r\n".join(["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Workio//Work Calendar//EN", "BEGIN:VEVENT", f"UID:work-{project.pk}@workio", f"DTSTART:{start}", f"DTEND:{end}", f"SUMMARY:{clean(project.title)}", f"DESCRIPTION:{clean(project.description)}", f"LOCATION:{clean(project.location)}", "END:VEVENT", "END:VCALENDAR", ""])
    response = HttpResponse(body, content_type="text/calendar; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="work-{project.pk}.ics"'
    return response


@login_required
def schedule_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user):
        raise PermissionDenied
    return render(request, "projects/schedule.html", {"project": project, "occurrences": project.occurrences.select_related("checked_in_by")})


@login_required
def schedule_generate(request, pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    if request.method != "POST":
        raise PermissionDenied
    created = generate_occurrences(project)
    messages.success(request, f"Added {len(created)} schedule occurrence(s).")
    return redirect("schedule_detail", pk=project.pk)


@login_required
def occurrence_edit(request, pk, occurrence_pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    occurrence = get_object_or_404(WorkOccurrence, pk=occurrence_pk, project=project)
    form = WorkOccurrenceForm(request.POST or None, instance=occurrence)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Schedule occurrence updated.")
        return redirect("schedule_detail", pk=project.pk)
    return render(request, "projects/item_form.html", {"form": form, "project": project, "heading": "Edit occurrence", "cancel_url": reverse("schedule_detail", kwargs={"pk": project.pk})})


@login_required
def occurrence_check_in(request, pk, occurrence_pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user) or request.method != "POST":
        raise PermissionDenied
    occurrence = get_object_or_404(WorkOccurrence, pk=occurrence_pk, project=project, status=WorkOccurrence.Status.SCHEDULED)
    occurrence.status = WorkOccurrence.Status.IN_PROGRESS
    occurrence.checked_in_by = request.user
    occurrence.checked_in_at = timezone.now()
    occurrence.save(update_fields=["status", "checked_in_by", "checked_in_at"])
    record_activity(project, request.user, "schedule", "Checked in to scheduled work")
    return redirect("schedule_detail", pk=project.pk)


@login_required
def occurrence_check_out(request, pk, occurrence_pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user) or request.method != "POST":
        raise PermissionDenied
    occurrence = get_object_or_404(WorkOccurrence, pk=occurrence_pk, project=project, status=WorkOccurrence.Status.IN_PROGRESS)
    occurrence.status = WorkOccurrence.Status.COMPLETED
    occurrence.checked_out_at = timezone.now()
    occurrence.save(update_fields=["status", "checked_out_at"])
    record_activity(project, request.user, "schedule", "Checked out of scheduled work")
    return redirect("schedule_detail", pk=project.pk)


@login_required
def proposal_list(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user):
        raise PermissionDenied
    return render(request, "projects/proposal_list.html", {"project": project, "proposals": project.proposals.select_related("created_by")})


@login_required
def proposal_create(request, pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    initial = {"title": f"Proposal for {project.title}", "amount": project.budget, "deposit_amount": project.deposit_amount, "pricing_unit": project.pricing_unit, "terms": project.terms, "scope": project.description}
    form = ProposalForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        proposal = form.save(commit=False)
        proposal.project = project
        proposal.created_by = request.user
        proposal.save()
        record_activity(project, request.user, "proposal", "Created a proposal")
        messages.success(request, "Proposal created as a draft.")
        return redirect("proposal_detail", pk=project.pk, proposal_pk=proposal.pk)
    return render(request, "projects/proposal_form.html", {"form": form, "project": project, "heading": "Create proposal"})


@login_required
def proposal_detail(request, pk, proposal_pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user):
        raise PermissionDenied
    proposal = get_object_or_404(Proposal, pk=proposal_pk, project=project)
    return render(request, "projects/proposal_detail.html", {"project": project, "proposal": proposal, "item_form": ProposalItemForm()})


def _recalculate_proposal(proposal):
    if proposal.items.exists():
        proposal.amount = sum((item.amount for item in proposal.items.all()), Decimal("0.00"))
        proposal.save(update_fields=["amount", "updated_at"])


@login_required
def proposal_edit(request, pk, proposal_pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    proposal = get_object_or_404(Proposal, pk=proposal_pk, project=project, status=Proposal.Status.DRAFT)
    form = ProposalForm(request.POST or None, instance=proposal)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Proposal updated.")
        return redirect("proposal_detail", pk=project.pk, proposal_pk=proposal.pk)
    return render(request, "projects/proposal_form.html", {"form": form, "project": project, "heading": "Edit proposal"})


@login_required
def proposal_send(request, pk, proposal_pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    proposal = get_object_or_404(Proposal, pk=proposal_pk, project=project, status=Proposal.Status.DRAFT)
    if request.method != "POST":
        raise PermissionDenied
    _recalculate_proposal(proposal)
    proposal.status = Proposal.Status.SENT
    proposal.sent_at = timezone.now()
    proposal.save(update_fields=["status", "sent_at", "updated_at"])
    record_activity(project, request.user, "proposal", "Sent a proposal for review")
    notify(project.client, request.user, "proposal", f"New proposal for {project.title}", reverse("proposal_detail", kwargs={"pk": project.pk, "proposal_pk": proposal.pk}))
    messages.success(request, "Proposal sent to the client.")
    return redirect("proposal_detail", pk=project.pk, proposal_pk=proposal.pk)


@login_required
def proposal_item_create(request, pk, proposal_pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    proposal = get_object_or_404(Proposal, pk=proposal_pk, project=project, status=Proposal.Status.DRAFT)
    if request.method != "POST":
        raise PermissionDenied
    form = ProposalItemForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.proposal = proposal
        item.order = proposal.items.count()
        item.save()
        _recalculate_proposal(proposal)
        messages.success(request, "Proposal item added.")
    else:
        return render(request, "projects/proposal_detail.html", {"project": project, "proposal": proposal, "item_form": form}, status=400)
    return redirect("proposal_detail", pk=project.pk, proposal_pk=proposal.pk)


@login_required
def proposal_item_delete(request, pk, proposal_pk, item_pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    proposal = get_object_or_404(Proposal, pk=proposal_pk, project=project, status=Proposal.Status.DRAFT)
    item = get_object_or_404(ProposalItem, pk=item_pk, proposal=proposal)
    if request.method != "POST":
        raise PermissionDenied
    item.delete()
    _recalculate_proposal(proposal)
    messages.success(request, "Proposal item removed.")
    return redirect("proposal_detail", pk=project.pk, proposal_pk=proposal.pk)


@login_required
def proposal_respond(request, pk, proposal_pk):
    project = get_object_or_404(Project, pk=pk, client=request.user)
    proposal = get_object_or_404(Proposal, pk=proposal_pk, project=project, status=Proposal.Status.SENT)
    if proposal.is_expired:
        messages.error(request, "This proposal has expired.")
        return redirect("proposal_detail", pk=project.pk, proposal_pk=proposal.pk)
    form = ProposalResponseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        proposal.status = form.cleaned_data["decision"]
        proposal.response_note = form.cleaned_data["note"].strip()
        proposal.responded_at = timezone.now()
        proposal.save(update_fields=["status", "response_note", "responded_at", "updated_at"])
        if proposal.status == Proposal.Status.ACCEPTED:
            project.budget = proposal.amount
            project.deposit_amount = proposal.deposit_amount
            project.pricing_unit = proposal.pricing_unit
            project.terms = proposal.terms
            project.terms_accepted_at = timezone.now()
            project.save(update_fields=["budget", "deposit_amount", "pricing_unit", "terms", "terms_accepted_at", "updated_at"])
            if proposal.deposit_amount:
                PaymentInstallment.objects.get_or_create(project=project, label="Deposit", defaults={"amount": proposal.deposit_amount, "due_date": timezone.localdate()})
            balance = proposal.amount - proposal.deposit_amount
            if balance > 0:
                PaymentInstallment.objects.get_or_create(project=project, label="Final balance", defaults={"amount": balance, "due_date": project.deadline})
            run_event_automations(project, AutomationRule.Trigger.TERMS_ACCEPTED)
        verb = "accepted" if proposal.status == Proposal.Status.ACCEPTED else "declined"
        record_activity(project, request.user, "proposal", f"{verb.title()} the proposal")
        notify(project.freelancer, request.user, "proposal", f"{request.user.display_name} {verb} the proposal for {project.title}", reverse("proposal_detail", kwargs={"pk": project.pk, "proposal_pk": proposal.pk}))
        messages.success(request, f"Proposal {verb}.")
        return redirect("proposal_detail", pk=project.pk, proposal_pk=proposal.pk)
    return render(request, "projects/proposal_response.html", {"form": form, "project": project, "proposal": proposal})


@login_required
def payment_schedule(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user):
        raise PermissionDenied
    installments = project.payment_installments.all()
    totals = installments.aggregate(total=Sum("amount"), paid=Sum("amount", filter=Q(status=PaymentInstallment.Status.PAID)), pending=Sum("amount", filter=Q(status=PaymentInstallment.Status.PENDING)))
    return render(request, "projects/payment_schedule.html", {"project": project, "installments": installments, "totals": totals})


@login_required
def payment_create(request, pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    form = PaymentInstallmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.project = project
        item.save()
        record_activity(project, request.user, "payment", f"Added payment: {item.label}")
        notify(project.client, request.user, "payment", f"Payment schedule updated for {project.title}", reverse("payment_schedule", kwargs={"pk": project.pk}))
        messages.success(request, "Payment added.")
        return redirect("payment_schedule", pk=project.pk)
    return render(request, "projects/payment_form.html", {"form": form, "project": project, "heading": "Add payment"})


@login_required
def payment_edit(request, pk, payment_pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    item = get_object_or_404(PaymentInstallment, pk=payment_pk, project=project, status=PaymentInstallment.Status.PENDING)
    form = PaymentInstallmentForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Payment updated.")
        return redirect("payment_schedule", pk=project.pk)
    return render(request, "projects/payment_form.html", {"form": form, "project": project, "heading": "Edit payment"})


@login_required
def payment_status(request, pk, payment_pk, status):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    item = get_object_or_404(PaymentInstallment, pk=payment_pk, project=project)
    if request.method != "POST" or status not in {PaymentInstallment.Status.PAID, PaymentInstallment.Status.WAIVED, PaymentInstallment.Status.PENDING}:
        raise PermissionDenied
    item.status = status
    item.paid_at = timezone.now() if status == PaymentInstallment.Status.PAID else None
    item.save(update_fields=["status", "paid_at"])
    record_activity(project, request.user, "payment", f"Marked {item.label} {item.get_status_display().lower()}")
    notify(project.client, request.user, "payment", f"{item.label} marked {item.get_status_display().lower()} for {project.title}", reverse("payment_schedule", kwargs={"pk": project.pk}))
    messages.success(request, "Payment status updated.")
    return redirect("payment_schedule", pk=project.pk)


@login_required
def payment_delete(request, pk, payment_pk):
    project = get_object_or_404(Project, pk=pk, freelancer=request.user)
    item = get_object_or_404(PaymentInstallment, pk=payment_pk, project=project, status=PaymentInstallment.Status.PENDING)
    if request.method != "POST":
        raise PermissionDenied
    item.delete()
    messages.success(request, "Payment removed.")
    return redirect("payment_schedule", pk=project.pk)


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.freelancer:
        raise PermissionDenied
    old_status = project.status
    form = ProjectForm(request.POST or None, instance=project, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        generate_occurrences(project)
        if old_status != Project.Status.COMPLETED and project.status == Project.Status.COMPLETED:
            run_event_automations(project, AutomationRule.Trigger.WORK_COMPLETED)
        record_activity(project, request.user, "project", "Updated project details")
        messages.success(request, "Project details updated.")
        return redirect(project)
    return render(request, "projects/form.html", {"form": form, "project": project, "editing": True})

@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project.objects.select_related("freelancer", "client"), pk=pk)
    if not allowed(project, request.user):
        raise PermissionDenied
    completed = project.tasks.filter(completed=True).count()
    total = project.tasks.count()
    progress = round(completed / total * 100) if total else 0
    other_user = project.client if request.user == project.freelancer else project.freelancer
    hours_logged = project.time_entries.aggregate(total=Sum("hours"))["total"] or 0
    can_review = request.user == project.client and project.status == Project.Status.COMPLETED and not hasattr(project, "review")
    context = {"project": project, "task_form": TaskForm(project=project), "milestone_form": MilestoneForm(), "comment_form": CommentForm(), "file_form": ProjectFileForm(), "progress": progress, "other_user": other_user, "hours_logged": hours_logged, "can_review": can_review}
    return render(request, "projects/detail.html", context)

@login_required
def task_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user):
        raise PermissionDenied
    form = TaskForm(request.POST, project=project)
    if form.is_valid():
        task = form.save(commit=False)
        task.project = project
        task.save()
        record_activity(project, request.user, "task", f"Added task: {task.title}")
        other = project.client if request.user == project.freelancer else project.freelancer
        notify(other, request.user, "task", f"New task added to {project.title}", project.get_absolute_url())
    return redirect(project)


@login_required
def milestone_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user) or request.method != "POST":
        raise PermissionDenied
    form = MilestoneForm(request.POST)
    if form.is_valid():
        milestone = form.save(commit=False); milestone.project = project; milestone.save()
        record_activity(project, request.user, "milestone", f"Created milestone: {milestone.title}")
        other = project.client if request.user == project.freelancer else project.freelancer
        notify(other, request.user, "milestone", f"New milestone in {project.title}", project.get_absolute_url())
    return redirect(project)


@login_required
def milestone_submit(request, pk, milestone_pk):
    project = get_object_or_404(Project, pk=pk)
    milestone = get_object_or_404(Milestone, pk=milestone_pk, project=project)
    if request.method != "POST" or request.user != project.freelancer or milestone.review_status not in {Milestone.ReviewStatus.DRAFT, Milestone.ReviewStatus.CHANGES}:
        raise PermissionDenied
    milestone.review_status = Milestone.ReviewStatus.SUBMITTED
    milestone.submitted_at = timezone.now()
    milestone.reviewed_at = None
    milestone.completed = False
    milestone.save(update_fields=["review_status", "submitted_at", "reviewed_at", "completed"])
    record_activity(project, request.user, "approval", f"Submitted {milestone.title} for approval")
    notify(project.client, request.user, "approval", f"{milestone.title} is ready for your review", project.get_absolute_url() + "#milestone-" + str(milestone.pk))
    messages.success(request, "Milestone submitted for client approval.")
    return redirect(project.get_absolute_url() + "#milestone-" + str(milestone.pk))


@login_required
def milestone_review(request, pk, milestone_pk):
    project = get_object_or_404(Project, pk=pk)
    milestone = get_object_or_404(Milestone, pk=milestone_pk, project=project)
    if request.user != project.client or milestone.review_status != Milestone.ReviewStatus.SUBMITTED:
        raise PermissionDenied
    form = MilestoneReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        decision = form.cleaned_data["decision"]
        milestone.review_status = decision
        milestone.review_note = form.cleaned_data["note"].strip()
        milestone.reviewed_at = timezone.now()
        milestone.completed = decision == Milestone.ReviewStatus.APPROVED
        milestone.save(update_fields=["review_status", "review_note", "reviewed_at", "completed"])
        record_activity(project, request.user, "approval", f"{('Approved' if milestone.completed else 'Requested changes to')} {milestone.title}")
        verb = "approved" if milestone.completed else "requested changes to"
        notify(project.freelancer, request.user, "approval", f"{request.user.display_name} {verb} {milestone.title}", project.get_absolute_url() + "#milestone-" + str(milestone.pk))
        messages.success(request, "Milestone approved." if milestone.completed else "Feedback sent to the freelancer.")
        return redirect(project.get_absolute_url() + "#milestone-" + str(milestone.pk))
    return render(request, "projects/milestone_review.html", {"form": form, "project": project, "milestone": milestone})


@login_required
def comment_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user) or request.method != "POST":
        raise PermissionDenied
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False); comment.project = project; comment.author = request.user; comment.save()
        record_activity(project, request.user, "comment", "Posted a project update")
        other = project.client if request.user == project.freelancer else project.freelancer
        notify(other, request.user, "comment", f"{request.user.display_name} commented on {project.title}", project.get_absolute_url() + "#comments")
    return redirect(project.get_absolute_url() + "#comments")


@login_required
def comment_edit(request, pk, comment_pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user):
        raise PermissionDenied
    comment = get_object_or_404(ProjectComment, pk=comment_pk, project=project)
    if request.user != comment.author:
        raise PermissionDenied
    form = CommentForm(request.POST or None, instance=comment)
    if request.method == "POST" and form.is_valid():
        comment = form.save(commit=False)
        comment.edited_at = timezone.now()
        comment.save()
        record_activity(project, request.user, "comment", "Edited a project update")
        messages.success(request, "Comment updated.")
        return redirect(project.get_absolute_url() + f"#comment-{comment.pk}")
    return render(request, "projects/item_form.html", {
        "form": form,
        "project": project,
        "heading": "Edit comment",
        "cancel_url": project.get_absolute_url() + f"#comment-{comment.pk}",
    })


@login_required
def file_upload(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user) or request.method != "POST":
        raise PermissionDenied
    form = ProjectFileForm(request.POST, request.FILES)
    if form.is_valid():
        item = form.save(commit=False); item.project = project; item.uploaded_by = request.user; item.save()
        record_activity(project, request.user, "file", f"Shared file: {item.label or item.filename}")
        other = project.client if request.user == project.freelancer else project.freelancer
        notify(other, request.user, "file", f"New file shared in {project.title}", project.get_absolute_url() + "#files")
    return redirect(project.get_absolute_url() + "#files")


@login_required
def file_download(request, pk, file_pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user):
        raise PermissionDenied
    item = get_object_or_404(ProjectFile, pk=file_pk, project=project)
    return FileResponse(item.file.open("rb"), as_attachment=True, filename=item.filename)

@login_required
def task_toggle(request, pk, task_pk):
    project = get_object_or_404(Project, pk=pk)
    if not allowed(project, request.user) or request.method != "POST":
        raise PermissionDenied
    task = get_object_or_404(Task, pk=task_pk, project=project)
    task.completed = not task.completed
    task.save(update_fields=["completed"])
    record_activity(project, request.user, "task", f"Marked {task.title} {'complete' if task.completed else 'incomplete'}")
    return redirect(project)


@login_required
def task_edit(request, pk, task_pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.freelancer:
        raise PermissionDenied
    task = get_object_or_404(Task, pk=task_pk, project=project)
    form = TaskForm(request.POST or None, instance=task, project=project)
    if request.method == "POST" and form.is_valid():
        task = form.save()
        record_activity(project, request.user, "task", f"Updated task: {task.title}")
        messages.success(request, "Task updated.")
        return redirect(project)
    return render(request, "projects/item_form.html", {"form": form, "project": project, "heading": "Edit task"})


@login_required
def task_delete(request, pk, task_pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.freelancer or request.method != "POST":
        raise PermissionDenied
    task = get_object_or_404(Task, pk=task_pk, project=project)
    title = task.title
    task.delete()
    record_activity(project, request.user, "task", f"Deleted task: {title}")
    messages.success(request, "Task deleted.")
    return redirect(project)


@login_required
def milestone_edit(request, pk, milestone_pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.freelancer:
        raise PermissionDenied
    milestone = get_object_or_404(Milestone, pk=milestone_pk, project=project)
    form = MilestoneForm(request.POST or None, instance=milestone)
    if request.method == "POST" and form.is_valid():
        milestone = form.save()
        record_activity(project, request.user, "milestone", f"Updated milestone: {milestone.title}")
        messages.success(request, "Milestone updated.")
        return redirect(project)
    return render(request, "projects/item_form.html", {"form": form, "project": project, "heading": "Edit milestone"})


@login_required
def milestone_delete(request, pk, milestone_pk):
    project = get_object_or_404(Project, pk=pk)
    if request.user != project.freelancer or request.method != "POST":
        raise PermissionDenied
    milestone = get_object_or_404(Milestone, pk=milestone_pk, project=project)
    title = milestone.title
    milestone.delete()
    record_activity(project, request.user, "milestone", f"Deleted milestone: {title}")
    messages.success(request, "Milestone deleted. Its tasks were kept.")
    return redirect(project)


@login_required
def comment_delete(request, pk, comment_pk):
    project = get_object_or_404(Project, pk=pk)
    comment = get_object_or_404(ProjectComment, pk=comment_pk, project=project)
    if request.method != "POST" or request.user not in (comment.author, project.freelancer):
        raise PermissionDenied
    comment.delete()
    record_activity(project, request.user, "comment", "Deleted a project update")
    messages.success(request, "Comment deleted.")
    return redirect(project.get_absolute_url() + "#comments")


@login_required
def file_delete(request, pk, file_pk):
    project = get_object_or_404(Project, pk=pk)
    item = get_object_or_404(ProjectFile, pk=file_pk, project=project)
    if request.method != "POST" or request.user not in (item.uploaded_by, project.freelancer):
        raise PermissionDenied
    filename = item.label or item.filename
    item.file.delete(save=False)
    item.delete()
    record_activity(project, request.user, "file", f"Deleted file: {filename}")
    messages.success(request, "Shared file deleted.")
    return redirect(project.get_absolute_url() + "#files")
