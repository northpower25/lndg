from django.db import migrations, models
import django.utils.timezone


def create_default_policy_templates(apps, schema_editor):
    Policy = apps.get_model('gui', 'Policy')
    templates = [
        {
            "name": "Auto Fee – Conservative",
            "policy_type": "auto_fee",
            "mode_required": "advanced",
            "definition": {
                "strategy": "conservative",
                "risk_label": "low",
                "delta_percent": 10,
                "cooldown_minutes": 10080,
                "run_interval_minutes": 10080,
                "limits": {
                    "max_delta_percent": 10,
                    "max_delta_ppm": 200,
                    "max_changes_per_window": 1,
                },
            },
        },
        {
            "name": "Auto Fee – Balanced",
            "policy_type": "auto_fee",
            "mode_required": "advanced",
            "definition": {
                "strategy": "balanced",
                "risk_label": "medium",
                "delta_percent": 20,
                "cooldown_minutes": 2880,
                "run_interval_minutes": 2880,
                "limits": {
                    "max_delta_percent": 20,
                    "max_delta_ppm": 400,
                    "max_changes_per_window": 1,
                },
            },
        },
        {
            "name": "Auto Fee – Revenue Seeking",
            "policy_type": "auto_fee",
            "mode_required": "expert",
            "definition": {
                "strategy": "revenue_seeking",
                "risk_label": "high",
                "delta_percent": 40,
                "cooldown_minutes": 1440,
                "run_interval_minutes": 1440,
                "limits": {
                    "max_delta_percent": 40,
                    "max_delta_ppm": 800,
                    "max_changes_per_window": 1,
                },
            },
        },
    ]

    for template in templates:
        Policy.objects.get_or_create(
            name=template["name"],
            policy_type=template["policy_type"],
            defaults={
                "definition": template["definition"],
                "dry_run": True,
                "is_active": False,
                "mode_required": template["mode_required"],
            },
        )


def reverse_default_policy_templates(apps, schema_editor):
    Policy = apps.get_model('gui', 'Policy')
    Policy.objects.filter(
        name__in=[
            "Auto Fee – Conservative",
            "Auto Fee – Balanced",
            "Auto Fee – Revenue Seeking",
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gui', '0005_policy_recommendation_policyrun_splicelog'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutoFeeMLRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('chan_id', models.CharField(db_index=True, max_length=20)),
                ('param_name', models.CharField(max_length=32)),
                ('old_value', models.BigIntegerField(default=0)),
                ('new_value', models.BigIntegerField(default=0)),
                ('trigger_reason', models.CharField(blank=True, default='', max_length=128)),
                ('ml_confidence', models.FloatField(default=0.0)),
                ('routing_volume_delta_24h', models.BigIntegerField(default=0)),
                ('routing_revenue_delta_24h', models.BigIntegerField(default=0)),
                ('escalation_level', models.IntegerField(default=0)),
            ],
            options={
                'indexes': [models.Index(fields=['chan_id', 'timestamp'], name='gui_autofee_chan_id_e081db_idx')],
            },
        ),
        migrations.CreateModel(
            name='RebalanceMLRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('source_chan_id', models.CharField(db_index=True, max_length=20)),
                ('target_chan_id', models.CharField(db_index=True, max_length=20)),
                ('amount_sat', models.BigIntegerField()),
                ('fee_ppm', models.IntegerField(default=0)),
                ('hour_of_day', models.IntegerField(default=0)),
                ('day_of_week', models.IntegerField(default=0)),
                ('success', models.BooleanField(default=False)),
                ('routing_revenue_delta_24h', models.BigIntegerField(default=0)),
                ('routing_revenue_delta_7d', models.BigIntegerField(default=0)),
                ('ml_predicted_success_prob', models.FloatField(default=0.0)),
                ('ml_confidence', models.FloatField(default=0.0)),
            ],
            options={
                'indexes': [models.Index(fields=['source_chan_id', 'target_chan_id', 'timestamp'], name='gui_rebalan_source__90b5a4_idx')],
            },
        ),
        migrations.RunPython(
            create_default_policy_templates,
            reverse_default_policy_templates,
        ),
    ]
