from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gui', '0040_rebalancebudget_channelefficiency'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tg_enabled', models.BooleanField(default=False)),
                ('tg_bot_token', models.CharField(blank=True, default='', max_length=100)),
                ('tg_chat_id', models.CharField(blank=True, default='', max_length=50)),
                ('notify_rebalance_success', models.BooleanField(default=True)),
                ('notify_rebalance_fail', models.BooleanField(default=False)),
                ('notify_channel_inactive', models.BooleanField(default=True)),
                ('notify_autofee', models.BooleanField(default=False)),
            ],
            options={
                'app_label': 'gui',
            },
        ),
    ]
