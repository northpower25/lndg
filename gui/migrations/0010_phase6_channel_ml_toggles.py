from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gui", "0009_phase6_usermode_policy_bound"),
    ]

    operations = [
        migrations.AddField(
            model_name="channels",
            name="ml_autofee_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="channels",
            name="ml_rebalance_enabled",
            field=models.BooleanField(default=True),
        ),
    ]

