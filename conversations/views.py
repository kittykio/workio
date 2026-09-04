from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from accounts.models import User
from .forms import MessageForm
from .models import Conversation, Message

@login_required
def inbox(request):
    conversations = Conversation.objects.for_user(request.user).prefetch_related("participants", "messages")
    rows = [{"conversation": item, "other": item.other_participant(request.user), "unread": item.messages.exclude(sender=request.user).filter(read_at__isnull=True).count()} for item in conversations]
    return render(request, "conversations/inbox.html", {"rows": rows})

@login_required
def start(request, username):
    other = get_object_or_404(User, username=username)
    if other == request.user:
        return redirect("inbox")
    conversation = Conversation.objects.filter(participants=request.user).filter(participants=other).first()
    if not conversation:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other)
    return redirect("conversation_detail", pk=conversation.pk)

@login_required
def detail(request, pk):
    conversation = get_object_or_404(Conversation.objects.prefetch_related("participants", "messages__sender"), pk=pk)
    if not conversation.participants.filter(pk=request.user.pk).exists():
        raise PermissionDenied
    conversation.messages.exclude(sender=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())
    form = MessageForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        message = form.save(commit=False)
        message.conversation = conversation
        message.sender = request.user
        message.save()
        conversation.save(update_fields=["updated_at"])
        from notifications.services import notify
        for recipient in conversation.participants.exclude(pk=request.user.pk):
            notify(recipient, request.user, "message", f"New message from {request.user.display_name}", reverse("conversation_detail", kwargs={"pk": conversation.pk}))
        return redirect("conversation_detail", pk=pk)
    return render(request, "conversations/detail.html", {"conversation": conversation, "other": conversation.other_participant(request.user), "form": form})

@login_required
def attachment_download(request, pk, message_pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.participants.filter(pk=request.user.pk).exists():
        raise PermissionDenied
    message = get_object_or_404(Message, pk=message_pk, conversation=conversation)
    if not message.attachment:
        raise PermissionDenied
    filename = message.attachment.name.rsplit("/", 1)[-1]
    return FileResponse(message.attachment.open("rb"), as_attachment=True, filename=filename)


@login_required
def message_feed(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.participants.filter(pk=request.user.pk).exists():
        raise PermissionDenied
    try:
        after = max(0, int(request.GET.get("after", 0)))
    except (TypeError, ValueError):
        after = 0
    messages = conversation.messages.filter(pk__gt=after).select_related("sender")[:100]
    conversation.messages.exclude(sender=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())
    return JsonResponse({"messages": [{"id": item.pk, "body": item.body, "sender": item.sender.display_name, "mine": item.sender_id == request.user.pk, "created": item.created_at.strftime("%b %d, %I:%M %p"), "attachment": reverse("message_attachment", kwargs={"pk": conversation.pk, "message_pk": item.pk}) if item.attachment else "", "attachment_name": item.attachment.name.rsplit("/", 1)[-1] if item.attachment else ""} for item in messages]})

# Keep the model import local to this module's query construction.
from django.db import models
from django.urls import reverse
