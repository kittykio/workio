from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0012_work_occurrences"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="SavedWorkView",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=80)),
                ("query", models.CharField(blank=True, max_length=160)), ("status", models.CharField(blank=True, max_length=60)), ("work_type", models.CharField(blank=True, max_length=100)),
                ("billing_type", models.CharField(blank=True, max_length=12)), ("work_mode", models.CharField(blank=True, max_length=12)), ("tags", models.CharField(blank=True, max_length=100)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_work_views", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(model_name="savedworkview", constraint=models.UniqueConstraint(fields=("owner", "name"), name="unique_saved_work_view_name")),
    ]
