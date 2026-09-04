from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect, render
from conversations.models import Conversation
from projects.models import Project, ProjectActivity, Task
from billing.models import Invoice, TimeEntry
from .forms import AccountSettingsForm, PortfolioItemForm, ProfileForm, ReviewForm, SignupForm
from .models import PortfolioItem, Review, User


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "home.html")


def signup(request):
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        next_url = request.POST.get("next", "")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("profile_edit", username=user.username)
    return render(request, "registration/signup.html", {"form": form, "next": request.GET.get("next", "")})


@login_required
def dashboard(request):
    projects = Project.objects.for_user(request.user).select_related("freelancer", "client")
    conversations = Conversation.objects.for_user(request.user).prefetch_related("participants", "messages")[:4]
    message_rows = [{"conversation": chat, "other": chat.other_participant(request.user)} for chat in conversations]
    invoices = Invoice.objects.filter(project__in=projects).prefetch_related("items")
    outstanding = sum((invoice.total for invoice in invoices.filter(status__in=[Invoice.Status.SENT, Invoice.Status.OVERDUE])), 0)
    paid = sum((invoice.total for invoice in invoices.filter(status=Invoice.Status.PAID)), 0)
    month_start = timezone.localdate().replace(day=1)
    month_hours = TimeEntry.objects.filter(project__in=projects, date__gte=month_start).aggregate(total=Sum("hours"))["total"] or 0
    upcoming_limit = timezone.localdate() + timedelta(days=14)
    upcoming_tasks = Task.objects.filter(project__in=projects, completed=False, due_date__isnull=False, due_date__lte=upcoming_limit).select_related("project").order_by("due_date")[:6]
    activities = ProjectActivity.objects.filter(project__in=projects).select_related("actor", "project")[:8]
    context = {"projects": projects[:5], "project_count": projects.count(), "active_count": projects.exclude(status=Project.Status.COMPLETED).count(), "message_rows": message_rows, "outstanding": outstanding, "paid": paid, "month_hours": month_hours, "upcoming_tasks": upcoming_tasks, "activities": activities}
    return render(request, "dashboard.html", context)


def profile(request, username):
    person = get_object_or_404(User, username=username)
    portfolio = person.portfolio_items.all()
    reviews = person.reviews_received.select_related("reviewer", "project")[:8]
    return render(request, "accounts/profile.html", {"person": person, "portfolio": portfolio, "reviews": reviews})


@login_required
def profile_edit(request, username):
    if request.user.username != username:
        return redirect("profile", username=username)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("profile", username=username)
    return render(request, "accounts/profile_edit.html", {"form": form})


@login_required
def account_settings(request):
    form = AccountSettingsForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account settings updated.")
        return redirect("account_settings")
    return render(request, "accounts/account_settings.html", {"form": form})


def freelancer_directory(request):
    people = User.objects.filter(role=User.Role.FREELANCER).order_by("first_name", "username")
    query = request.GET.get("q", "").strip()
    skill = request.GET.get("skill", "").strip()
    if query:
        people = people.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(username__icontains=query) | Q(headline__icontains=query) | Q(skills__icontains=query))
    if skill:
        people = people.filter(skills__icontains=skill)
    return render(request, "accounts/directory.html", {"people": people, "query": query, "skill": skill})


@login_required
def portfolio_create(request):
    if request.user.role != User.Role.FREELANCER:
        raise PermissionDenied
    form = PortfolioItemForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False); item.owner = request.user; item.save()
        messages.success(request, "Portfolio case study added.")
        return redirect(request.user)
    return render(request, "accounts/portfolio_form.html", {"form": form})


@login_required
def portfolio_edit(request, pk):
    item = get_object_or_404(PortfolioItem, pk=pk)
    if item.owner != request.user:
        raise PermissionDenied
    form = PortfolioItemForm(request.POST or None, request.FILES or None, instance=item)
    if request.method == "POST" and form.is_valid():
        form.save(); messages.success(request, "Case study updated."); return redirect(request.user)
    return render(request, "accounts/portfolio_form.html", {"form": form, "item": item, "editing": True})


@login_required
def portfolio_delete(request, pk):
    item = get_object_or_404(PortfolioItem, pk=pk)
    if item.owner != request.user or request.method != "POST":
        raise PermissionDenied
    if item.image:
        item.image.delete(save=False)
    item.delete(); messages.success(request, "Case study deleted.")
    return redirect(request.user)


@login_required
def review_create(request, project_pk):
    project = get_object_or_404(Project.objects.select_related("client", "freelancer"), pk=project_pk)
    if request.user != project.client or project.status != Project.Status.COMPLETED or hasattr(project, "review"):
        raise PermissionDenied
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False); review.project = project; review.reviewer = request.user; review.freelancer = project.freelancer; review.save()
        messages.success(request, "Thank you for reviewing this collaboration.")
        from notifications.services import notify
        notify(project.freelancer, request.user, "review", f"{request.user.display_name} left you a {review.rating}-star review", project.freelancer.get_absolute_url() + "#reviews")
        return redirect(project.freelancer)
    return render(request, "accounts/review_form.html", {"form": form, "project": project})
