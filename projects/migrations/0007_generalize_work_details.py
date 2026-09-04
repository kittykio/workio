from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("projects", "0006_projectcomment_edited_at")]

    operations = [
        migrations.AddField(model_name="project", name="work_type", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="project", name="work_mode", field=models.CharField(choices=[("flexible", "Flexible / not applicable"), ("remote", "Remote"), ("onsite", "On-site"), ("hybrid", "Hybrid")], default="flexible", max_length=12)),
        migrations.AddField(model_name="project", name="billing_type", field=models.CharField(choices=[("hourly", "Hourly"), ("fixed", "Fixed price"), ("session", "Per appointment or session"), ("milestone", "By stage or milestone"), ("recurring", "Recurring"), ("custom", "Custom / not yet decided")], default="custom", max_length=12)),
        migrations.AddField(model_name="project", name="location", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="projectinvitation", name="work_type", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="projectinvitation", name="work_mode", field=models.CharField(choices=[("flexible", "Flexible / not applicable"), ("remote", "Remote"), ("onsite", "On-site"), ("hybrid", "Hybrid")], default="flexible", max_length=12)),
        migrations.AddField(model_name="projectinvitation", name="billing_type", field=models.CharField(choices=[("hourly", "Hourly"), ("fixed", "Fixed price"), ("session", "Per appointment or session"), ("milestone", "By stage or milestone"), ("recurring", "Recurring"), ("custom", "Custom / not yet decided")], default="custom", max_length=12)),
        migrations.AddField(model_name="projectinvitation", name="location", field=models.CharField(blank=True, max_length=180)),
    ]
