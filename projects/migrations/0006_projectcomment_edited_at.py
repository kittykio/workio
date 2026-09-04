from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0005_projectactivity")]

    operations = [
        migrations.AddField(
            model_name="projectcomment",
            name="edited_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
