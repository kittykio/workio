from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0016_workflow_stages"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="ServiceOffering",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("title", models.CharField(max_length=140)), ("description", models.TextField()), ("work_type", models.CharField(blank=True, max_length=100)),
                ("billing_type", models.CharField(choices=[("hourly", "Hourly"), ("fixed", "Fixed price"), ("session", "Per appointment or session"), ("milestone", "By stage or milestone"), ("recurring", "Recurring"), ("custom", "Custom / not yet decided")], default="custom", max_length=12)),
                ("pricing_unit", models.CharField(choices=[("hour", "Hour"), ("session", "Session / appointment"), ("day", "Day"), ("item", "Item / product"), ("mile", "Mile / kilometer"), ("word", "Word"), ("delivery", "Delivery / trip"), ("fixed", "Whole engagement"), ("custom", "Custom unit")], default="custom", max_length=12)),
                ("starting_price", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)), ("work_mode", models.CharField(choices=[("flexible", "Flexible / not applicable"), ("remote", "Remote"), ("onsite", "On-site"), ("hybrid", "Hybrid")], default="flexible", max_length=12)),
                ("typical_duration", models.CharField(blank=True, max_length=100)), ("active", models.BooleanField(default=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_offerings", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="ServiceInquiry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("message", models.TextField()), ("budget", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("preferred_date", models.DateField(blank=True, null=True)), ("location", models.CharField(blank=True, max_length=180)), ("status", models.CharField(choices=[("new", "New"), ("discussing", "Discussing"), ("converted", "Converted to work"), ("closed", "Closed")], default="new", max_length=12)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("client", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_inquiries", to=settings.AUTH_USER_MODEL)),
                ("converted_project", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_inquiry", to="projects.project")),
                ("offering", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inquiries", to="projects.serviceoffering")),
            ], options={"ordering": ["-created_at"]},
        ),
    ]
