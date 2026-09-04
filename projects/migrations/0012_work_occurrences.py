from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0011_proposals"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="WorkOccurrence",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("starts_at", models.DateTimeField()), ("ends_at", models.DateTimeField(blank=True, null=True)), ("location", models.CharField(blank=True, max_length=180)),
                ("status", models.CharField(choices=[("scheduled", "Scheduled"), ("in_progress", "In progress"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="scheduled", max_length=14)),
                ("checked_in_at", models.DateTimeField(blank=True, null=True)), ("checked_out_at", models.DateTimeField(blank=True, null=True)), ("notes", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("checked_in_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="work_checkins", to=settings.AUTH_USER_MODEL)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="occurrences", to="projects.project")),
            ], options={"ordering": ["starts_at", "pk"]},
        ),
        migrations.AddConstraint(model_name="workoccurrence", constraint=models.UniqueConstraint(fields=("project", "starts_at"), name="unique_work_occurrence_start")),
    ]
