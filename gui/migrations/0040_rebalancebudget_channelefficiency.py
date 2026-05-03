# Generated migration for RebalanceBudget and ChannelEfficiency models

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gui', '0039_inboundfeelog'),
    ]

    operations = [
        migrations.CreateModel(
            name='RebalanceBudget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now)),
                ('spent_sats', models.BigIntegerField(default=0)),
            ],
            options={
                'app_label': 'gui',
            },
        ),
        migrations.CreateModel(
            name='ChannelEfficiency',
            fields=[
                ('chan_id', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('peer_alias', models.CharField(max_length=32)),
                ('efficiency_score', models.FloatField(default=0.0)),
                ('earned_7d', models.FloatField(default=0.0)),
                ('rebal_costs_7d', models.FloatField(default=0.0)),
                ('revenue_per_sat_hour', models.FloatField(default=0.0)),
                ('updated', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'app_label': 'gui',
            },
        ),
    ]
