from datetime import timedelta

from django.utils import timezone

from notifications.services import notify
from .models import AutomationRule, AutomationRun, Project


def _recipients(rule, project):
    if rule.recipient == AutomationRule.Recipient.CLIENT:
        return [project.client]
    if rule.recipient == AutomationRule.Recipient.FREELANCER:
        return [project.freelancer]
    return [project.freelancer, project.client]


def _execute(rule, project, event_key):
    _, created = AutomationRun.objects.get_or_create(rule=rule, project=project, event_key=event_key)
    if not created:
        return False
    message = rule.message.replace("{work}", project.title)
    for recipient in _recipients(rule, project):
        actor = project.client if recipient == project.freelancer else project.freelancer
        notify(recipient, actor, "automation", message, project.get_absolute_url())
    return True


def run_event_automations(project, trigger):
    rules = AutomationRule.objects.filter(owner=project.freelancer, trigger=trigger, enabled=True)
    event_key = f"{trigger}:{timezone.now().date().isoformat()}"
    return sum(_execute(rule, project, event_key) for rule in rules)


def run_due_automations(now=None):
    now = now or timezone.now()
    total = 0
    rules = AutomationRule.objects.filter(trigger=AutomationRule.Trigger.BEFORE_START, enabled=True).select_related("owner")
    for rule in rules:
        cutoff = now + timedelta(days=rule.days_before)
        projects = Project.objects.filter(freelancer=rule.owner, scheduled_start__gte=now, scheduled_start__lte=cutoff).select_related("freelancer", "client")
        for project in projects:
            event_key = f"start:{project.scheduled_start.isoformat()}"
            total += _execute(rule, project, event_key)
    return total
