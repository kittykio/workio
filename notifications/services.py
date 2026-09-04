from .models import Notification
from django.core.mail import send_mail

def notify(recipient, actor, kind, text, url=""):
    if recipient == actor:
        return None
    notification = Notification.objects.create(recipient=recipient, actor=actor, kind=kind, text=text, url=url)
    if recipient.email_notifications:
        send_mail(f"Workio: {text}", f"{text}\n\nOpen Workio: {url or '/notifications/'}", None, [recipient.email], fail_silently=True)
    return notification
