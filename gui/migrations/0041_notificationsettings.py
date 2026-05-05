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
                ('nostr_enabled', models.BooleanField(default=False)),
                ('nostr_privkey', models.CharField(
                    blank=True, default='', max_length=64,
                    help_text='32-byte hex private key for NOSTR signing (NIP-01)')),
                ('nostr_relays', models.TextField(
                    blank=True, default='wss://relay.damus.io,wss://nos.lol',
                    help_text='Comma-separated list of NOSTR relay WebSocket URLs')),
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
