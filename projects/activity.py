from .models import ProjectActivity


def record_activity(project, actor, kind, text):
    return ProjectActivity.objects.create(project=project, actor=actor, kind=kind, text=text)
