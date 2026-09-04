from .models import ActiveTimer


def active_timer(request):
    if not request.user.is_authenticated:
        return {}
    timer = ActiveTimer.objects.filter(user=request.user).select_related("project").first()
    return {"active_timer": timer}
