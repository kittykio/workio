from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0015_proposal_items"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="WorkflowStage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=60)),
                ("color", models.CharField(default="#174c3c", max_length=7)), ("order", models.PositiveSmallIntegerField(default=0)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="workflow_stages", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering": ["order", "pk"]},
        ),
        migrations.AddField(model_name="project", name="workflow_stage", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="projects", to="projects.workflowstage")),
        migrations.AddConstraint(model_name="workflowstage", constraint=models.UniqueConstraint(fields=("owner", "name"), name="unique_workflow_stage_name")),
    ]
