from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0013_saved_work_views")]

    operations = [
        migrations.CreateModel(
            name="PaymentInstallment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("label", models.CharField(max_length=140)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)), ("due_date", models.DateField(blank=True, null=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("paid", "Paid"), ("waived", "Waived")], default="pending", max_length=10)),
                ("paid_at", models.DateTimeField(blank=True, null=True)), ("notes", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payment_installments", to="projects.project")),
            ], options={"ordering": ["due_date", "pk"]},
        ),
    ]
