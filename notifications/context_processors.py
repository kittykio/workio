def notification_counts(request):
    if not request.user.is_authenticated:
        return {}
    return {
        "unread_notification_count": request.user.notifications.filter(read_at__isnull=True).count(),
        "unread_message_count": request.user.conversations.filter(messages__read_at__isnull=True).exclude(messages__sender=request.user).distinct().count(),
    }
