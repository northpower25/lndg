from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("gui", "0010_phase6_channel_ml_toggles"),
    ]

    operations = [
        migrations.CreateModel(
            name="PeerNetworkSnapshot",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("pubkey", models.CharField(db_index=True, max_length=66)),
                ("alias", models.CharField(blank=True, default="", max_length=64)),
                ("channel_count", models.IntegerField(default=0)),
                ("total_capacity_sat", models.BigIntegerField(default=0)),
                ("avg_fee_rate_ppm", models.FloatField(default=0.0)),
                ("last_gossip_update", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "app_label": "gui",
            },
        ),
        migrations.AddIndex(
            model_name="peernetworksnapshot",
            index=models.Index(fields=["pubkey", "timestamp"], name="gui_peernet_pubkey_ts_idx"),
        ),
    ]
