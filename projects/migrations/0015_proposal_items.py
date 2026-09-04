from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("projects", "0014_payment_installments")]

    operations = [
        migrations.CreateModel(
            name="ProposalItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(max_length=240)), ("quantity", models.DecimalField(decimal_places=2, default=1, max_digits=10)),
                ("unit", models.CharField(choices=[("hour", "Hour"), ("session", "Session / appointment"), ("day", "Day"), ("item", "Item / product"), ("mile", "Mile / kilometer"), ("word", "Word"), ("delivery", "Delivery / trip"), ("fixed", "Whole engagement"), ("custom", "Custom unit")], default="custom", max_length=12)),
                ("rate", models.DecimalField(decimal_places=2, max_digits=10)), ("order", models.PositiveSmallIntegerField(default=0)),
                ("proposal", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="projects.proposal")),
            ], options={"ordering": ["order", "pk"]},
        ),
    ]
