from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0007_generalize_work_details"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.AddField(model_name="project", name="scheduled_start", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="project", name="scheduled_end", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="project", name="recurrence", field=models.CharField(choices=[("none", "Does not repeat"), ("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("custom", "Custom schedule")], default="none", max_length=12)),
        migrations.AddField(model_name="project", name="pricing_unit", field=models.CharField(choices=[("hour", "Hour"), ("session", "Session / appointment"), ("day", "Day"), ("item", "Item / product"), ("mile", "Mile / kilometer"), ("word", "Word"), ("delivery", "Delivery / trip"), ("fixed", "Whole engagement"), ("custom", "Custom unit")], default="fixed", max_length=12)),
        migrations.AddField(model_name="project", name="quantity", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="project", name="unit_rate", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="project", name="deposit_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="project", name="tags", field=models.CharField(blank=True, max_length=300)),
        migrations.AddField(model_name="project", name="intake_notes", field=models.TextField(blank=True)),
        migrations.AddField(model_name="project", name="terms", field=models.TextField(blank=True)),
        migrations.AddField(model_name="project", name="terms_accepted_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="project", name="custom_details", field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name="projectinvitation", name="scheduled_start", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="projectinvitation", name="scheduled_end", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="projectinvitation", name="recurrence", field=models.CharField(choices=[("none", "Does not repeat"), ("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("custom", "Custom schedule")], default="none", max_length=12)),
        migrations.AddField(model_name="projectinvitation", name="pricing_unit", field=models.CharField(choices=[("hour", "Hour"), ("session", "Session / appointment"), ("day", "Day"), ("item", "Item / product"), ("mile", "Mile / kilometer"), ("word", "Word"), ("delivery", "Delivery / trip"), ("fixed", "Whole engagement"), ("custom", "Custom unit")], default="fixed", max_length=12)),
        migrations.AddField(model_name="projectinvitation", name="quantity", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="projectinvitation", name="unit_rate", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="projectinvitation", name="deposit_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="projectinvitation", name="tags", field=models.CharField(blank=True, max_length=300)),
        migrations.AddField(model_name="projectinvitation", name="intake_notes", field=models.TextField(blank=True)),
        migrations.AddField(model_name="projectinvitation", name="terms", field=models.TextField(blank=True)),
        migrations.AddField(model_name="projectinvitation", name="custom_details", field=models.JSONField(blank=True, default=dict)),
        migrations.CreateModel(
            name="WorkTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)), ("work_type", models.CharField(blank=True, max_length=100)), ("description", models.TextField(blank=True)),
                ("work_mode", models.CharField(choices=[("flexible", "Flexible / not applicable"), ("remote", "Remote"), ("onsite", "On-site"), ("hybrid", "Hybrid")], default="flexible", max_length=12)),
                ("billing_type", models.CharField(choices=[("hourly", "Hourly"), ("fixed", "Fixed price"), ("session", "Per appointment or session"), ("milestone", "By stage or milestone"), ("recurring", "Recurring"), ("custom", "Custom / not yet decided")], default="custom", max_length=12)),
                ("recurrence", models.CharField(choices=[("none", "Does not repeat"), ("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("custom", "Custom schedule")], default="none", max_length=12)),
                ("pricing_unit", models.CharField(choices=[("hour", "Hour"), ("session", "Session / appointment"), ("day", "Day"), ("item", "Item / product"), ("mile", "Mile / kilometer"), ("word", "Word"), ("delivery", "Delivery / trip"), ("fixed", "Whole engagement"), ("custom", "Custom unit")], default="fixed", max_length=12)),
                ("default_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)), ("default_deposit", models.DecimalField(decimal_places=2, default=0, max_digits=10)), ("default_tags", models.CharField(blank=True, max_length=300)), ("default_terms", models.TextField(blank=True)), ("checklist", models.TextField(blank=True, help_text="One checklist item per line.")), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="work_templates", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(model_name="worktemplate", constraint=models.UniqueConstraint(fields=("owner", "name"), name="unique_work_template_name_per_owner")),
    ]
