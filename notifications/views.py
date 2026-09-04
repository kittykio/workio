from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import Notification

@login_required
def notification_list(request):
    return render(request, "notifications/list.html", {"notifications": request.user.notifications.select_related("actor")[:50]})

@login_required
def notification_feed(request):
    items = request.user.notifications.select_related("actor")[:8]
    return JsonResponse({"unread": request.user.notifications.filter(read_at__isnull=True).count(), "items": [{"text": item.text, "url": item.url, "created": item.created_at.isoformat(), "read": bool(item.read_at)} for item in items]})

@login_required
def notification_open(request, pk):
    item = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not item.read_at:
        item.read_at = timezone.now(); item.save(update_fields=["read_at"])
    return redirect(item.url or "notification_list")

@login_required
def read_all(request):
    if request.method == "POST":
        request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    return redirect("notification_list")

