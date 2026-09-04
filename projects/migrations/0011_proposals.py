from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0010_automation_rules"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Proposal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)), ("scope", models.TextField()), ("amount", models.DecimalField(decimal_places=2, max_digits=10)), ("deposit_amount", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("pricing_unit", models.CharField(choices=[("hour", "Hour"), ("session", "Session / appointment"), ("day", "Day"), ("item", "Item / product"), ("mile", "Mile / kilometer"), ("word", "Word"), ("delivery", "Delivery / trip"), ("fixed", "Whole engagement"), ("custom", "Custom unit")], default="fixed", max_length=12)),
                ("terms", models.TextField(blank=True)), ("valid_until", models.DateField(blank=True, null=True)), ("status", models.CharField(choices=[("draft", "Draft"), ("sent", "Awaiting response"), ("accepted", "Accepted"), ("declined", "Declined")], default="draft", max_length=12)),
                ("sent_at", models.DateTimeField(blank=True, null=True)), ("responded_at", models.DateTimeField(blank=True, null=True)), ("response_note", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="proposals_created", to=settings.AUTH_USER_MODEL)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="proposals", to="projects.project")),
            ], options={"ordering": ["-created_at"]},
        ),
    ]
