import calendar
from datetime import timedelta

from .models import Project, WorkOccurrence


def _next_month(value):
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def generate_occurrences(project, count=12):
    if not project.scheduled_start:
        return []
    duration = (project.scheduled_end - project.scheduled_start) if project.scheduled_end else timedelta(hours=1)
    current = project.scheduled_start
    created = []
    total = count if project.recurrence in {Project.Recurrence.DAILY, Project.Recurrence.WEEKLY, Project.Recurrence.MONTHLY} else 1
    for _ in range(total):
        occurrence, was_created = WorkOccurrence.objects.get_or_create(
            project=project,
            starts_at=current,
            defaults={"ends_at": current + duration, "location": project.location},
        )
        if was_created:
            created.append(occurrence)
        if project.recurrence == Project.Recurrence.DAILY:
            current += timedelta(days=1)
        elif project.recurrence == Project.Recurrence.WEEKLY:
            current += timedelta(weeks=1)
        elif project.recurrence == Project.Recurrence.MONTHLY:
            current = _next_month(current)
        else:
            break
    return created
