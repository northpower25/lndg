from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone

# Create your models here.
class Payments(models.Model):
    creation_date = models.DateTimeField()
    payment_hash = models.CharField(max_length=64, primary_key=True)
    value = models.FloatField()
    fee = models.FloatField()
    status = models.IntegerField()
    index = models.IntegerField()
    chan_out = models.CharField(max_length=20, null=True)
    chan_out_alias = models.CharField(null=True, max_length=32)
    keysend_preimage = models.CharField(null=True, max_length=64)
    message = models.CharField(null=True, max_length=1000)
    cleaned = models.BooleanField(default=False)
    rebal_chan = models.CharField(max_length=20, null=True)
    class Meta:
        app_label = 'gui'

class PaymentHops(models.Model):
    payment_hash = models.ForeignKey('Payments', on_delete=models.CASCADE)
    attempt_id = models.IntegerField()
    step = models.IntegerField()
    chan_id = models.CharField(max_length=20)
    alias = models.CharField(max_length=32)
    chan_capacity = models.BigIntegerField()
    node_pubkey = models.CharField(max_length=66)
    amt = models.FloatField()
    fee = models.FloatField()
    cost_to = models.FloatField()
    class Meta:
        app_label = 'gui'
        unique_together = (('payment_hash', 'attempt_id', 'step'),)

class Invoices(models.Model):
    creation_date = models.DateTimeField()
    settle_date = models.DateTimeField(null=True, default=None)
    r_hash = models.CharField(max_length=64, primary_key=True)
    value = models.FloatField()
    amt_paid = models.BigIntegerField()
    state = models.IntegerField()
    chan_in = models.CharField(max_length=20, null=True)
    chan_in_alias = models.CharField(null=True, max_length=32)
    keysend_preimage = models.CharField(null=True, max_length=64)
    message = models.CharField(null=True, max_length=1000)
    sender = models.CharField(null=True, max_length=66)
    sender_alias = models.CharField(null=True, max_length=32)
    index = models.IntegerField()
    is_revenue = models.BooleanField(default=False)
    class Meta:
        app_label = 'gui'

class Forwards(models.Model):
    forward_date = models.DateTimeField()
    chan_id_in = models.CharField(max_length=20)
    chan_id_out = models.CharField(max_length=20)
    chan_in_alias = models.CharField(null=True, max_length=32)
    chan_out_alias = models.CharField(null=True, max_length=32)
    amt_in_msat = models.BigIntegerField()
    amt_out_msat = models.BigIntegerField()
    fee = models.FloatField()
    inbound_fee = models.FloatField()
    class Meta:
        app_label = 'gui'

class Channels(models.Model):
    remote_pubkey = models.CharField(max_length=66)
    chan_id = models.CharField(max_length=20, primary_key=True)
    short_chan_id = models.CharField(max_length=20)
    funding_txid = models.CharField(max_length=64)
    output_index = models.IntegerField()
    capacity = models.BigIntegerField()
    local_balance = models.BigIntegerField()
    remote_balance = models.BigIntegerField()
    unsettled_balance = models.BigIntegerField()
    local_commit = models.IntegerField()
    local_chan_reserve = models.IntegerField()
    num_updates = models.IntegerField()
    initiator = models.BooleanField()
    alias = models.CharField(max_length=32)
    total_sent = models.BigIntegerField()
    total_received = models.BigIntegerField()
    private = models.BooleanField()
    pending_outbound = models.BigIntegerField()
    pending_inbound = models.BigIntegerField()
    htlc_count = models.IntegerField()
    local_base_fee = models.IntegerField()
    local_fee_rate = models.IntegerField()
    local_inbound_base_fee = models.IntegerField()
    local_inbound_fee_rate = models.IntegerField()
    local_disabled = models.BooleanField()
    local_cltv = models.IntegerField()
    local_min_htlc_msat = models.BigIntegerField()
    local_max_htlc_msat = models.BigIntegerField()
    remote_base_fee = models.IntegerField()
    remote_fee_rate = models.IntegerField()
    remote_inbound_base_fee = models.IntegerField()
    remote_inbound_fee_rate = models.IntegerField()
    remote_disabled = models.BooleanField()
    remote_cltv = models.IntegerField()
    remote_min_htlc_msat = models.BigIntegerField()
    remote_max_htlc_msat = models.BigIntegerField()
    push_amt = models.BigIntegerField()
    close_address = models.CharField(max_length=100)
    is_active = models.BooleanField()
    is_open = models.BooleanField()
    last_update = models.DateTimeField()
    auto_rebalance = models.BooleanField(default=False)
    ar_amt_target = models.BigIntegerField()
    ar_in_target = models.IntegerField()
    ar_out_target = models.IntegerField()
    ar_max_cost = models.IntegerField()
    fees_updated = models.DateTimeField(default=timezone.now)
    auto_fees = models.BooleanField()
    ml_rebalance_enabled = models.BooleanField(default=True)
    ml_autofee_enabled = models.BooleanField(default=True)
    notes = models.TextField(default='', blank=True)

    def save(self, *args, **kwargs):
        if self.auto_fees is None:
            if LocalSettings.objects.filter(key='AF-Enabled').exists():
                enabled = int(LocalSettings.objects.filter(key='AF-Enabled')[0].value)
            else:
                LocalSettings(key='AF-Enabled', value='0').save()
                enabled = 0
            self.auto_fees = False if enabled == 0 else True
        if not self.ar_out_target:
            if LocalSettings.objects.filter(key='AR-Outbound%').exists():
                outbound_setting = int(LocalSettings.objects.filter(key='AR-Outbound%')[0].value)
            else:
                LocalSettings(key='AR-Outbound%', value='75').save()
                outbound_setting = 75
            self.ar_out_target = outbound_setting
        if not self.ar_in_target:
            if LocalSettings.objects.filter(key='AR-Inbound%').exists():
                inbound_setting = int(LocalSettings.objects.filter(key='AR-Inbound%')[0].value)
            else:
                LocalSettings(key='AR-Inbound%', value='90').save()
                inbound_setting = 90
            self.ar_in_target = inbound_setting
        if not self.ar_amt_target:
            if LocalSettings.objects.filter(key='AR-Target%').exists():
                amt_setting = float(LocalSettings.objects.filter(key='AR-Target%')[0].value)
            else:
                LocalSettings(key='AR-Target%', value='3').save()
                amt_setting = 3
            self.ar_amt_target = int((amt_setting/100) * self.capacity)
        if not self.ar_max_cost:
            if LocalSettings.objects.filter(key='AR-MaxCost%').exists():
                cost_setting = int(LocalSettings.objects.filter(key='AR-MaxCost%')[0].value)
            else:
                LocalSettings(key='AR-MaxCost%', value='65').save()
                cost_setting = 65
            self.ar_max_cost = cost_setting
        super(Channels, self).save(*args, **kwargs)

    class Meta:
        app_label = 'gui'

class Peers(models.Model):
    pubkey = models.CharField(max_length=66, primary_key=True)
    alias = models.CharField(null=True, max_length=32)
    address = models.CharField(max_length=100)
    sat_sent = models.BigIntegerField()
    sat_recv = models.BigIntegerField()
    inbound = models.BooleanField()
    connected = models.BooleanField()
    last_reconnected = models.DateTimeField(null=True, default=None)
    ping_time = models.BigIntegerField(default=0)
    class Meta:
        app_label = 'gui'

class Rebalancer(models.Model):
    requested = models.DateTimeField(default=timezone.now)
    value = models.IntegerField()
    fee_limit = models.FloatField()
    outgoing_chan_ids = models.TextField(default='[]')
    last_hop_pubkey = models.CharField(default='', max_length=66)
    target_alias = models.CharField(default='', max_length=32)
    duration = models.IntegerField()
    start = models.DateTimeField(null=True, default=None)
    stop = models.DateTimeField(null=True, default=None)
    status = models.IntegerField(default=0)
    payment_hash = models.CharField(max_length=64, null=True, default=None)
    manual = models.BooleanField(default=False)
    fees_paid = models.FloatField(null=True, default=None)
    class Meta:
        app_label = 'gui'

class LocalSettings(models.Model):
    key = models.CharField(primary_key=True, default=None, max_length=20)
    value = models.CharField(default=None, max_length=50)
    class Meta:
        app_label = 'gui'

class Onchain(models.Model):
    tx_hash = models.CharField(max_length=64, primary_key=True)
    amount = models.BigIntegerField()
    block_hash = models.CharField(max_length=64)
    block_height = models.IntegerField()
    time_stamp = models.DateTimeField()
    fee = models.IntegerField()
    label = models.CharField(max_length=100)
    class Meta:
        app_label = 'gui'

class Closures(models.Model):
    chan_id = models.CharField(max_length=20)
    funding_txid = models.CharField(max_length=64)
    funding_index = models.IntegerField()
    closing_tx = models.CharField(max_length=64)
    remote_pubkey = models.CharField(max_length=66)
    capacity = models.BigIntegerField()
    close_height = models.IntegerField()
    settled_balance = models.BigIntegerField()
    time_locked_balance = models.BigIntegerField()
    close_type = models.IntegerField()
    open_initiator = models.IntegerField()
    close_initiator = models.IntegerField()
    resolution_count = models.IntegerField()
    closing_costs = models.IntegerField(default=0)
    class Meta:
        app_label = 'gui'
        unique_together = (('funding_txid', 'funding_index'),)

class Resolutions(models.Model):
    chan_id = models.CharField(max_length=20)
    resolution_type = models.IntegerField()
    outcome = models.IntegerField()
    outpoint_tx = models.CharField(max_length=64)
    outpoint_index = models.IntegerField()
    amount_sat = models.BigIntegerField()
    sweep_txid = models.CharField(max_length=64)
    class Meta:
        app_label = 'gui'

class PendingHTLCs(models.Model):
    chan_id = models.CharField(max_length=20)
    alias = models.CharField(max_length=32)
    incoming = models.BooleanField()
    amount = models.BigIntegerField()
    hash_lock = models.CharField(max_length=64)
    expiration_height = models.IntegerField()
    forwarding_channel = models.CharField(max_length=20)
    forwarding_alias = models.CharField(max_length=32)
    class Meta:
        app_label = 'gui'

class FailedHTLCs(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    amount = models.IntegerField()
    chan_id_in = models.CharField(max_length=20)
    chan_id_out = models.CharField(max_length=20)
    chan_in_alias = models.CharField(null=True, max_length=32)
    chan_out_alias = models.CharField(null=True, max_length=32)
    chan_out_liq = models.BigIntegerField(null=True)
    chan_out_pending = models.BigIntegerField(null=True)
    wire_failure = models.IntegerField()
    failure_detail = models.IntegerField()
    missed_fee = models.FloatField()
    class Meta:
        app_label = 'gui'

class Autopilot(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    chan_id = models.CharField(max_length=20)
    peer_alias = models.CharField(max_length=32)
    setting = models.CharField(max_length=20)
    old_value = models.IntegerField()
    new_value = models.IntegerField()
    class Meta:
        app_label = 'gui'

class Autofees(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    chan_id = models.CharField(max_length=20)
    peer_alias = models.CharField(max_length=32)
    setting = models.CharField(max_length=20)
    old_value = models.IntegerField()
    new_value = models.IntegerField()
    class Meta:
        app_label = 'gui'

class InboundFeeLog(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    chan_id = models.CharField(max_length=20)
    peer_alias = models.CharField(max_length=32)
    setting = models.CharField(max_length=20)
    old_value = models.IntegerField()
    new_value = models.IntegerField()
    class Meta:
        app_label = 'gui'

class PendingChannels(models.Model):
    funding_txid = models.CharField(max_length=64)
    output_index = models.IntegerField()
    local_base_fee = models.IntegerField(null=True, default=None)
    local_fee_rate = models.IntegerField(null=True, default=None)
    local_cltv = models.IntegerField(null=True, default=None)
    auto_rebalance = models.BooleanField(null=True, default=None)
    ar_amt_target = models.BigIntegerField(null=True, default=None)
    ar_in_target = models.IntegerField(null=True, default=None)
    ar_out_target = models.IntegerField(null=True, default=None)
    ar_max_cost = models.IntegerField(null=True, default=None)
    auto_fees = models.BooleanField(null=True, default=None)
    class Meta:
        app_label = 'gui'
        unique_together = (('funding_txid', 'output_index'),)

class AvoidNodes(models.Model):
    pubkey = models.CharField(max_length=66, primary_key=True)
    notes = models.CharField(null=True, max_length=1000)
    updated = models.DateTimeField(default=timezone.now)
    class Meta:
        app_label = 'gui'

class PeerEvents(models.Model):
    timestamp = models.DateTimeField(default=timezone.now)
    chan_id = models.CharField(max_length=20)
    peer_alias = models.CharField(max_length=32)
    event = models.CharField(max_length=20)
    old_value = models.BigIntegerField(null=True)
    new_value = models.BigIntegerField()
    out_liq = models.BigIntegerField()
    class Meta:
        app_label = 'gui'

class HistFailedHTLC(models.Model):
    date = models.DateField(default=timezone.now)
    chan_id_in = models.CharField(max_length=20)
    chan_id_out = models.CharField(max_length=20)
    chan_in_alias = models.CharField(null=True, max_length=32)
    chan_out_alias = models.CharField(null=True, max_length=32)
    htlc_count = models.IntegerField()
    amount_sum = models.BigIntegerField()
    fee_sum = models.BigIntegerField()
    liq_avg = models.BigIntegerField()
    pending_avg = models.BigIntegerField()
    balance_count = models.IntegerField()
    downstream_count = models.IntegerField()
    other_count = models.IntegerField()
    class Meta:
        app_label = 'gui'
        unique_together = (('date', 'chan_id_in', 'chan_id_out'),)

class TradeSales(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    creation_date = models.DateTimeField(default=timezone.now)
    expiry = models.DateTimeField(null=True)
    description = models.CharField(max_length=100)
    price = models.BigIntegerField()
    sale_type = models.IntegerField()
    secret = models.CharField(null=True, max_length=1000)
    sale_limit = models.IntegerField(null=True)
    sale_count = models.IntegerField(default=0)

class RebalanceBudget(models.Model):
    date = models.DateField(default=timezone.now)
    spent_sats = models.BigIntegerField(default=0)
    class Meta:
        app_label = 'gui'

class ChannelEfficiency(models.Model):
    chan_id = models.CharField(max_length=20, primary_key=True)
    peer_alias = models.CharField(max_length=32)
    efficiency_score = models.FloatField(default=0.0)
    earned_7d = models.FloatField(default=0.0)
    rebal_costs_7d = models.FloatField(default=0.0)
    revenue_per_sat_hour = models.FloatField(default=0.0)
    updated = models.DateTimeField(default=timezone.now)
    class Meta:
        app_label = 'gui'

class NotificationSettings(models.Model):
    """Singleton model that stores notification backend configuration."""
    # Telegram
    tg_enabled = models.BooleanField(default=False)
    tg_bot_token = models.CharField(max_length=100, blank=True, default='')
    tg_chat_id = models.CharField(max_length=50, blank=True, default='')
    # External integrations (opt-in only; R-SEC-4)
    mempool_enabled = models.BooleanField(default=False)
    amboss_enabled = models.BooleanField(default=False)
    amboss_api_key = models.CharField(max_length=255, blank=True, default='')
    # Event triggers
    notify_rebalance_success = models.BooleanField(default=True)
    notify_rebalance_fail = models.BooleanField(default=False)
    notify_channel_inactive = models.BooleanField(default=True)
    notify_autofee = models.BooleanField(default=False)
    notify_mempool_low_fee = models.BooleanField(default=False)

    class Meta:
        app_label = 'gui'

    @classmethod
    def load(cls):
        """Return the singleton row, creating it if it doesn't exist."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class UserMode(models.Model):
    """Singleton model that stores the user's UI mode preferences and AI feature flags."""

    MODE_GUIDED = 'guided'
    MODE_ADVANCED = 'advanced'
    MODE_EXPERT = 'expert'
    MODE_CHOICES = [
        (MODE_GUIDED, 'Guided'),
        (MODE_ADVANCED, 'Advanced'),
        (MODE_EXPERT, 'Expert'),
    ]

    AI_MODE_OFF = 'off'
    AI_MODE_ADVISORY = 'advisory'
    AI_MODE_SHADOW = 'shadow'
    AI_MODE_POLICY_BOUND = 'policy_bound'
    AI_MODE_CHOICES = [
        (AI_MODE_OFF, 'Off'),
        (AI_MODE_ADVISORY, 'Advisory'),
        (AI_MODE_SHADOW, 'Shadow'),
        (AI_MODE_POLICY_BOUND, 'Policy-Bound (Expert)'),
    ]

    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default=MODE_ADVANCED)
    onboarding_step = models.IntegerField(default=0)
    onboarding_completed = models.BooleanField(default=False)
    language = models.CharField(max_length=8, default='en')
    updated_at = models.DateTimeField(auto_now=True)

    # AI feature flags – all default off (R-AI-2)
    ai_mode = models.CharField(max_length=16, choices=AI_MODE_CHOICES, default=AI_MODE_OFF)
    # policy_bound: Human confirmation required before each ML-triggered action (6-D)
    ai_policy_bound_confirm = models.BooleanField(default=True)
    ai_explain_always = models.BooleanField(default=False)
    ai_min_data_days = models.IntegerField(default=30)
    ai_max_auto_actions_day = models.IntegerField(default=0)
    ai_cooldown_minutes = models.IntegerField(default=60)
    ai_shadow_log_enabled = models.BooleanField(default=False)

    class Meta:
        app_label = 'gui'

    @classmethod
    def load(cls) -> 'UserMode':
        """Return the singleton row, creating it if it doesn't exist."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ChannelSnapshot(models.Model):
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    channel_id = models.CharField(max_length=20, db_index=True)
    local_balance_sat = models.BigIntegerField()
    remote_balance_sat = models.BigIntegerField()
    capacity_sat = models.BigIntegerField()
    local_fee_rate = models.IntegerField(default=0)
    local_base_fee = models.IntegerField(default=0)
    local_disabled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    class Meta:
        app_label = 'gui'
        indexes = [models.Index(fields=['channel_id', 'timestamp'])]


class ForwardingAggregate(models.Model):
    WINDOW_1D = '1d'
    WINDOW_7D = '7d'
    WINDOW_30D = '30d'
    WINDOW_CHOICES = [
        (WINDOW_1D, '1d'),
        (WINDOW_7D, '7d'),
        (WINDOW_30D, '30d'),
    ]

    window = models.CharField(max_length=4, choices=WINDOW_CHOICES)
    channel_id = models.CharField(max_length=20, db_index=True)
    window_start = models.DateTimeField(db_index=True)
    in_msat = models.BigIntegerField(default=0)
    out_msat = models.BigIntegerField(default=0)
    fees_msat = models.BigIntegerField(default=0)
    forward_count = models.IntegerField(default=0)
    fail_count = models.IntegerField(default=0)

    class Meta:
        app_label = 'gui'
        unique_together = (('window', 'channel_id', 'window_start'),)


class ChangeLog(models.Model):
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    change_type = models.CharField(max_length=64)
    target_channel_id = models.CharField(max_length=20, blank=True, default='', db_index=True)
    actor = models.CharField(max_length=128)
    old_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    rationale = models.JSONField(default=dict, blank=True)
    policy_run_ref = models.CharField(max_length=64, blank=True, default='')

    class Meta:
        app_label = 'gui'


class BackupLog(models.Model):
    """Audit record for every backup (settings export or database dump)."""

    TYPE_SETTINGS = 'settings'
    TYPE_DATABASE = 'database'
    TYPE_CHOICES = [
        (TYPE_SETTINGS, 'Settings JSON'),
        (TYPE_DATABASE, 'Database Dump'),
    ]

    STATUS_OK = 'ok'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_OK, 'OK'),
        (STATUS_FAILED, 'Failed'),
    ]

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    backup_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    file_path = models.CharField(max_length=512, blank=True, default='')
    file_size_bytes = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True, default='')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_OK)
    actor = models.CharField(max_length=128, default='manual')
    error_message = models.TextField(blank=True, default='')

    class Meta:
        app_label = 'gui'


class Recommendation(models.Model):
    TYPE_OPEN = 'open'
    TYPE_SPLICE_IN = 'splice_in'
    TYPE_SPLICE_OUT = 'splice_out'
    TYPE_CLOSE = 'close'
    TYPE_REBALANCE = 'rebalance'
    TYPE_FEE = 'fee'
    TYPE_CHOICES = [
        (TYPE_OPEN, 'Open Channel'),
        (TYPE_SPLICE_IN, 'Splice In'),
        (TYPE_SPLICE_OUT, 'Splice Out'),
        (TYPE_CLOSE, 'Close / Deprioritize'),
        (TYPE_REBALANCE, 'Rebalance'),
        (TYPE_FEE, 'Fee Strategy'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_APPLIED = 'applied'
    STATUS_DISMISSED = 'dismissed'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPLIED, 'Applied'),
        (STATUS_DISMISSED, 'Dismissed'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    RISK_LOW = 'low'
    RISK_MEDIUM = 'medium'
    RISK_HIGH = 'high'
    RISK_CHOICES = [
        (RISK_LOW, 'Low'),
        (RISK_MEDIUM, 'Medium'),
        (RISK_HIGH, 'High'),
    ]

    CONFIDENCE_HEURISTIC = 'heuristic'
    CONFIDENCE_RULE_BASED = 'rule_based'
    CONFIDENCE_ML_SHADOW = 'ml_shadow'
    CONFIDENCE_ML_MODEL = 'ml_model'
    CONFIDENCE_LABEL_CHOICES = [
        (CONFIDENCE_HEURISTIC, 'Heuristic'),
        (CONFIDENCE_RULE_BASED, 'Rule Based'),
        (CONFIDENCE_ML_SHADOW, 'ML Shadow'),
        (CONFIDENCE_ML_MODEL, 'ML Model'),
    ]

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    rec_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    target_chan_id = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    target_pubkey = models.CharField(max_length=66, null=True, blank=True)
    rationale = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(default=0.0)
    confidence_label = models.CharField(
        max_length=16, choices=CONFIDENCE_LABEL_CHOICES, default=CONFIDENCE_HEURISTIC
    )
    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES, default=RISK_LOW)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    dry_run_result = models.JSONField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'gui'


class Policy(models.Model):
    TYPE_AUTO_FEE = 'auto_fee'
    TYPE_REBALANCE = 'rebalance'
    TYPE_NOTIFY = 'notify'
    TYPE_CHOICES = [
        (TYPE_AUTO_FEE, 'Auto Fee'),
        (TYPE_REBALANCE, 'Rebalance'),
        (TYPE_NOTIFY, 'Notify'),
    ]

    MODE_GUIDED = 'guided'
    MODE_ADVANCED = 'advanced'
    MODE_EXPERT = 'expert'
    MODE_CHOICES = [
        (MODE_GUIDED, 'Guided'),
        (MODE_ADVANCED, 'Advanced'),
        (MODE_EXPERT, 'Expert'),
    ]

    name = models.CharField(max_length=100)
    policy_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    definition = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False)
    dry_run = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_run = models.DateTimeField(null=True, blank=True)
    mode_required = models.CharField(max_length=10, choices=MODE_CHOICES, default=MODE_ADVANCED)

    class Meta:
        app_label = 'gui'


class PolicyRun(models.Model):
    policy = models.ForeignKey('Policy', on_delete=models.CASCADE)
    executed_at = models.DateTimeField(default=timezone.now, db_index=True)
    was_dry_run = models.BooleanField(default=True)
    trigger_data = models.JSONField(default=dict, blank=True)
    actions_taken = models.JSONField(default=dict, blank=True)
    outcome = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = 'gui'


class SpliceLog(models.Model):
    TYPE_IN = 'in'
    TYPE_OUT = 'out'
    TYPE_CHOICES = [
        (TYPE_IN, 'Splice In'),
        (TYPE_OUT, 'Splice Out'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_BROADCAST = 'broadcast'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_BROADCAST, 'Broadcast'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_FAILED, 'Failed'),
    ]

    channel_id = models.CharField(max_length=20, db_index=True)
    splice_type = models.CharField(max_length=5, choices=TYPE_CHOICES)
    amount_sat = models.BigIntegerField()
    on_chain_fee_sat = models.BigIntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    txid = models.CharField(max_length=64, blank=True, default='')
    initiated_at = models.DateTimeField(default=timezone.now, db_index=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    rationale = models.JSONField(default=dict, blank=True)
    recommendation = models.ForeignKey('Recommendation', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        app_label = 'gui'
        indexes = [models.Index(fields=['channel_id', 'initiated_at'])]


class RebalanceMLRecord(models.Model):
    """Shadow-learning telemetry for ML-guided rebalance decisions."""

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    source_chan_id = models.CharField(max_length=20, db_index=True)
    target_chan_id = models.CharField(max_length=20, db_index=True)
    amount_sat = models.BigIntegerField()
    fee_ppm = models.IntegerField(default=0)
    hour_of_day = models.IntegerField(default=0)
    day_of_week = models.IntegerField(default=0)
    success = models.BooleanField(default=False)
    routing_revenue_delta_24h = models.BigIntegerField(default=0)
    routing_revenue_delta_7d = models.BigIntegerField(default=0)
    ml_predicted_success_prob = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    ml_confidence = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )

    class Meta:
        app_label = 'gui'
        indexes = [
            models.Index(fields=['source_chan_id', 'target_chan_id', 'timestamp']),
        ]


class AutoFeeMLRecord(models.Model):
    """Shadow-learning telemetry for ML-guided auto-fee adjustments."""

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    chan_id = models.CharField(max_length=20, db_index=True)
    param_name = models.CharField(max_length=32)
    old_value = models.BigIntegerField(default=0)
    new_value = models.BigIntegerField(default=0)
    trigger_reason = models.CharField(max_length=128, blank=True, default='')
    ml_confidence = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    routing_volume_delta_24h = models.BigIntegerField(default=0)
    routing_revenue_delta_24h = models.BigIntegerField(default=0)
    escalation_level = models.IntegerField(default=0)

    class Meta:
        app_label = 'gui'
        indexes = [models.Index(fields=['chan_id', 'timestamp'])]


class PeerNetworkSnapshot(models.Model):
    """Gossip-network snapshot for a peer pubkey (6-C).

    Collected periodically by the gossip collector.  Used by the recommendation
    engine for dynamic fee-target adjustment based on a peer's network position.
    """

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    pubkey = models.CharField(max_length=66, db_index=True)
    alias = models.CharField(max_length=64, blank=True, default='')
    channel_count = models.IntegerField(default=0)
    total_capacity_sat = models.BigIntegerField(default=0)
    avg_fee_rate_ppm = models.FloatField(default=0.0)
    last_gossip_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'gui'
        indexes = [models.Index(fields=['pubkey', 'timestamp'])]
