from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0008_universal_work_features"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.AddField(model_name="project", name="organization", field=models.CharField(blank=True, max_length=160)),
        migrations.AddField(model_name="project", name="contact_name", field=models.CharField(blank=True, max_length=140)),
        migrations.AddField(model_name="project", name="contact_email", field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name="project", name="contact_phone", field=models.CharField(blank=True, max_length=40)),
        migrations.AddField(model_name="project", name="custom_status", field=models.CharField(blank=True, max_length=60)),
        migrations.CreateModel(
            name="IntakeQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=180)),
                ("kind", models.CharField(choices=[("text", "Short text"), ("long_text", "Long text"), ("number", "Number"), ("date", "Date"), ("yes_no", "Yes / no")], default="text", max_length=12)),
                ("required", models.BooleanField(default=False)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="intake_questions", to="projects.project")),
            ], options={"ordering": ["order", "pk"]},
        ),
        migrations.CreateModel(
            name="IntakeResponse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("answered_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="intake_responses", to=settings.AUTH_USER_MODEL)),
                ("question", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="response", to="projects.intakequestion")),
            ],
        ),
    ]
