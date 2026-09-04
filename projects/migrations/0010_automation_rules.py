from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0009_contacts_intake_and_workflow"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="AutomationRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("trigger", models.CharField(choices=[("before_start", "Before scheduled start"), ("terms_accepted", "When terms are accepted"), ("work_completed", "When work is completed")], max_length=20)),
                ("days_before", models.PositiveSmallIntegerField(default=1, help_text="Used for scheduled-start reminders.")),
                ("recipient", models.CharField(choices=[("client", "Client"), ("freelancer", "Freelancer"), ("both", "Both participants")], default="client", max_length=12)),
                ("message", models.CharField(help_text="Use {work} to insert the work title.", max_length=300)),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="automation_rules", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AutomationRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_key", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="automation_runs", to="projects.project")),
                ("rule", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="projects.automationrule")),
            ],
        ),
        migrations.AddConstraint(model_name="automationrule", constraint=models.UniqueConstraint(fields=("owner", "name"), name="unique_automation_name_per_owner")),
        migrations.AddConstraint(model_name="automationrun", constraint=models.UniqueConstraint(fields=("rule", "project", "event_key"), name="unique_automation_run")),
    ]
