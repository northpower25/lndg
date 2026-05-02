import django
from django.db.models import Sum
from datetime import datetime, timedelta
from os import environ
from pandas import DataFrame, Series
environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import Forwards, Channels, LocalSettings, FailedHTLCs

def _get_setting(key, default):
    """Fetch a LocalSetting by key, creating it with the default value if absent."""
    obj = LocalSettings.objects.filter(key=key).first()
    if obj is not None:
        return type(default)(obj.value)
    LocalSettings(key=key, value=str(default)).save()
    return default

def main(channels):
    channels_df = DataFrame.from_records(channels.values())
    if channels_df.shape[0] == 0:
        return DataFrame()
    filter_1day = datetime.now() - timedelta(days=1)
    filter_7day = datetime.now() - timedelta(days=7)

    # --- Load all LocalSettings ---
    max_rate         = _get_setting('AF-MaxRate',              2500)
    min_rate         = _get_setting('AF-MinRate',              0)
    increment        = _get_setting('AF-Increment',            5)
    multiplier       = _get_setting('AF-Multiplier',           5)
    failed_htlc_limit= _get_setting('AF-FailedHTLCs',          25)
    update_hours     = _get_setting('AF-UpdateHours',          24)
    lowliq_limit     = _get_setting('AF-LowLiqLimit',          15)
    excess_limit     = _get_setting('AF-ExcessLimit',          95)
    # New settings
    time_of_day      = _get_setting('AF-TimeOfDay',            0)    # 0=off, 1=on
    liq_reward_factor= _get_setting('AF-LiquidityRewardFactor',20)   # % discount for low inbound
    competitor_fees  = _get_setting('AF-CompetitorFees',       0)    # 0=off, 1=on

    if lowliq_limit >= excess_limit:
        print('Invalid thresholds detected, using defaults...')
        lowliq_limit = 5
        excess_limit = 95

    # --- Fetch forwarding data ---
    forwards = Forwards.objects.filter(forward_date__gte=filter_7day, amt_out_msat__gte=1000000)
    forwards_1d = forwards.filter(forward_date__gte=filter_1day)
    
    forwards_df_in_1d_sum = DataFrame.from_records(
        forwards_1d.values('chan_id_in').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 
        index='chan_id_in'
    ) if forwards_1d.exists() else DataFrame()
    
    forwards_df_in_7d_sum = DataFrame.from_records(
        forwards.values('chan_id_in').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 
        index='chan_id_in'
    ) if forwards.exists() else DataFrame()
    
    forwards_df_out_7d_sum = DataFrame.from_records(
        forwards.values('chan_id_out').annotate(amt_out_msat=Sum('amt_out_msat'), fee=Sum('fee')), 
        index='chan_id_out'
    ) if forwards.exists() else DataFrame()

    # --- Compute per-channel routing metrics ---
    if not forwards_df_in_1d_sum.empty:
        channels_df['amt_routed_in_1day'] = channels_df['chan_id'].map(
            forwards_df_in_1d_sum['amt_out_msat'].floordiv(1000)
        ).fillna(0).astype(int)
    else:
        channels_df['amt_routed_in_1day'] = 0
    if not forwards_df_in_7d_sum.empty:
        channels_df['amt_routed_in_7day'] = channels_df['chan_id'].map(
            forwards_df_in_7d_sum['amt_out_msat'].floordiv(1000)
        ).fillna(0).astype(int)
    else:
        channels_df['amt_routed_in_7day'] = 0
    if not forwards_df_out_7d_sum.empty:
        channels_df['amt_routed_out_7day'] = channels_df['chan_id'].map(
            forwards_df_out_7d_sum['amt_out_msat'].floordiv(1000)
        ).fillna(0).astype(int)
    else:
        channels_df['amt_routed_out_7day'] = 0

    channels_df['net_routed_7day'] = (
        (channels_df['amt_routed_out_7day'] - channels_df['amt_routed_in_7day']) / channels_df['capacity']
    ).round(1)
    
    channels_df['local_balance'] = channels_df['local_balance'] + channels_df['pending_outbound']
    channels_df['remote_balance'] = channels_df['remote_balance'] + channels_df['pending_inbound']
    channels_df['out_percent'] = ((channels_df['local_balance'] / channels_df['capacity']) * 100).round(0).astype(int)
    channels_df['in_percent'] = ((channels_df['remote_balance'] / channels_df['capacity']) * 100).round(0).astype(int)
    channels_df['eligible'] = (datetime.now() - channels_df['fees_updated']).dt.total_seconds() > (update_hours * 3600)

    # --- Compute failed HTLCs per channel ---
    filter_last_updated = datetime.now() - timedelta(hours=update_hours)
    failed_htlc_df = DataFrame.from_records(
        FailedHTLCs.objects.filter(timestamp__gte=filter_last_updated, wire_failure=15, failure_detail=6).values()
    )
    if not failed_htlc_df.empty:
        failed_htlc_df = failed_htlc_df[
            failed_htlc_df['amount'] > (failed_htlc_df['chan_out_liq'] + failed_htlc_df['chan_out_pending'])
        ]
        failed_out_1day_series = failed_htlc_df['chan_id_out'].value_counts()
    else:
        failed_out_1day_series = Series(dtype='int64')
    channels_df['failed_out_1day'] = channels_df['chan_id'].map(failed_out_1day_series).fillna(0).astype(int)

    # --- Compute revenue metrics ---
    if not forwards_df_in_7d_sum.empty:
        channels_df['revenue_assist_7day'] = channels_df['chan_id'].map(
            forwards_df_in_7d_sum['fee']
        ).fillna(0).astype(float)
    else:
        channels_df['revenue_assist_7day'] = 0.0

    if not forwards_df_out_7d_sum.empty:
        channels_df['revenue_7day'] = channels_df['chan_id'].map(
            forwards_df_out_7d_sum['fee']
        ).fillna(0).astype(float)
    else:
        channels_df['revenue_7day'] = 0.0

    # --- 1.4 Revenue-per-sat-hour metric (earned sats per million capacity per hour over 7 days) ---
    # Formula: (earned_sats_7d / capacity / 168_hours) * 1_000_000
    channels_df['revenue_per_sat_hour'] = (
        (channels_df['revenue_7day'] / channels_df['capacity'].replace(0, 1)) / 168.0
    ) * 1_000_000

    # --- 1.2 Time-of-day factor ---
    # Compute per-channel time-of-day peak factor: ratio of current-hour average forwarding
    # volume to the overall hourly average over the last 7 days.
    if time_of_day == 1 and forwards.exists():
        current_hour = datetime.now().hour
        # Determine if current hour is in the top-half of active hours
        fwd_by_hour = DataFrame.from_records(
            forwards.values('chan_id_out', 'forward_date', 'amt_out_msat')
        )
        if not fwd_by_hour.empty:
            fwd_by_hour['hour'] = fwd_by_hour['forward_date'].apply(
                lambda d: d.hour if hasattr(d, 'hour') else datetime.fromisoformat(str(d)).hour
            )
            hourly_totals = fwd_by_hour.groupby('hour')['amt_out_msat'].sum()
            total_volume = hourly_totals.sum()
            if total_volume > 0:
                current_hour_volume = hourly_totals.get(current_hour, 0)
                avg_hourly_volume = total_volume / 24.0
                # tod_factor > 1 → busy hour → can charge more
                # tod_factor < 1 → quiet hour → should charge less
                tod_factor = current_hour_volume / avg_hourly_volume if avg_hourly_volume > 0 else 1.0
            else:
                tod_factor = 1.0
        else:
            tod_factor = 1.0
    else:
        tod_factor = 1.0

    # --- Aggregate data by remote_pubkey ---
    group_df = channels_df.groupby('remote_pubkey').agg({
        'local_balance': 'sum',
        'capacity': 'sum',
        'failed_out_1day': 'sum',
        'amt_routed_in_1day': 'sum',
        'amt_routed_in_7day': 'sum',
        'amt_routed_out_7day': 'sum',
        'revenue_7day': 'sum',
        'revenue_assist_7day': 'sum',
        'revenue_per_sat_hour': 'mean',
        'remote_fee_rate': 'first',   # representative peer rate for competitor comparison
    }).rename(columns={
        'local_balance': 'total_local_balance',
        'capacity': 'total_capacity',
        'failed_out_1day': 'total_failed_out_1day',
        'amt_routed_in_1day': 'total_amt_routed_in_1day',
        'amt_routed_in_7day': 'total_amt_routed_in_7day',
        'amt_routed_out_7day': 'total_amt_routed_out_7day',
        'revenue_7day': 'total_revenue_7day',
        'revenue_assist_7day': 'total_revenue_assist_7day',
    })

    group_df['overall_out_percent'] = (
        (group_df['total_local_balance'] / group_df['total_capacity']) * 100
    ).where(group_df['total_capacity'] > 0, 0)

    group_df['group_net_routed_7day'] = (
        (group_df['total_amt_routed_out_7day'] - group_df['total_amt_routed_in_7day']) / group_df['total_capacity']
    ).where(group_df['total_capacity'] > 0, 0)

    # --- 1.1 Competitor fee statistics across all peers ---
    # Use median and 25th percentile of remote_fee_rate as market reference.
    active_peer_rates = channels_df.loc[
        channels_df['remote_fee_rate'] > 0, 'remote_fee_rate'
    ]
    if competitor_fees == 1 and len(active_peer_rates) >= 3:
        market_median_ppm = float(active_peer_rates.median())
        market_p25_ppm    = float(active_peer_rates.quantile(0.25))
    else:
        market_median_ppm = None
        market_p25_ppm    = None

    # --- Define outbound adjustment calculation function ---
    def compute_outbound_adjustment(row):
        base_adj = 0
        if row['overall_out_percent'] <= lowliq_limit:
            base_adj = (5 * multiplier) if (row['total_failed_out_1day'] > failed_htlc_limit and 
                                    row['total_amt_routed_in_1day'] == 0) else 0
        elif row['overall_out_percent'] < excess_limit:
            if row['total_amt_routed_in_7day'] + row['total_amt_routed_out_7day'] == 0:
                base_adj = -3 * multiplier
            elif row['group_net_routed_7day'] > 1:
                base_adj = (2 * multiplier) * (1 + row['group_net_routed_7day'])
            else:
                base_adj = 0
        else:
            if row['total_amt_routed_in_7day'] + row['total_amt_routed_out_7day'] == 0:
                base_adj = -5 * multiplier
            elif (row['group_net_routed_7day'] < 0 and 
                row['total_revenue_assist_7day'] > row['total_revenue_7day'] * 10):
                base_adj = -5 * multiplier
            else:
                base_adj = 0

        # 1.4 Revenue-per-sat-hour adjustment: channels earning less than the peer average
        # get a small rate reduction to attract more volume; high earners get a boost.
        rph = row.get('revenue_per_sat_hour', 0)
        rph_mean = channels_df['revenue_per_sat_hour'].mean()
        if rph_mean > 0:
            rph_ratio = rph / rph_mean
            if rph_ratio < 0.5:
                base_adj -= increment  # underperforming: nudge rate down
            elif rph_ratio > 2.0:
                base_adj += increment  # over-performing: can afford higher rate

        # 1.1 Competitor fee adjustment
        if market_median_ppm is not None:
            local_rate = row.get('local_fee_rate', 0)
            if local_rate > market_median_ppm * 1.5:
                base_adj -= increment  # well above market median: ease down
            elif local_rate < market_p25_ppm:
                base_adj += increment  # cheapest 25% and still busy: raise slightly

        # 1.2 Time-of-day: scale adjustment proportionally with peak factor
        if tod_factor > 1.3:
            base_adj += round(increment * (tod_factor - 1))
        elif tod_factor < 0.7:
            base_adj -= round(increment * (1 - tod_factor))

        return base_adj

    # --- Define inbound adjustment calculation function ---
    def compute_inbound_adjustment(row):
        base_adj = 0
        if row['overall_out_percent'] <= lowliq_limit:
            base_adj = (-12 * multiplier) if (row['total_failed_out_1day'] > failed_htlc_limit and 
                                    row['total_amt_routed_in_1day'] == 0) else 0
        elif row['overall_out_percent'] < excess_limit: 
            if row['total_amt_routed_in_7day'] + row['total_amt_routed_out_7day'] == 0:
                base_adj = 7 * multiplier
            elif row['group_net_routed_7day'] > 1:
                base_adj = (-5 * multiplier) * (1 + row['group_net_routed_7day'])
            else:
                base_adj = 0
        else:
            if row['total_amt_routed_in_7day'] + row['total_amt_routed_out_7day'] == 0:
                base_adj = 12 * multiplier
            elif (row['group_net_routed_7day'] < 0 and 
                row['total_revenue_assist_7day'] > row['total_revenue_7day'] * 10):
                base_adj = 12 * multiplier
            else:
                base_adj = 0

        # 1.5 Asymmetric inbound fee: if remote side has high outbound surplus
        # (they have lots of local balance = lots of inbound on our side), apply extra
        # inbound discount to invite traffic flow in that direction.
        if row['overall_out_percent'] > excess_limit:
            base_adj -= 3 * multiplier

        return base_adj

    group_df['local_fee_rate'] = channels_df.groupby('remote_pubkey')['local_fee_rate'].first()
    group_df['adjustment'] = group_df.apply(compute_outbound_adjustment, axis=1)
    group_df['inbound_adjustment'] = group_df.apply(compute_inbound_adjustment, axis=1)

    # --- Merge adjustments back to channels_df ---
    channels_df = channels_df.merge(group_df[['adjustment']], on='remote_pubkey', how='left')
    channels_df = channels_df.merge(group_df[['inbound_adjustment']], on='remote_pubkey', how='left')

    # --- Compute new outbound rates ---
    channels_df['new_rate'] = channels_df['local_fee_rate'] + channels_df['adjustment']
    channels_df['new_rate'] = (channels_df['new_rate'] / increment).round(0) * increment
    channels_df['new_rate'] = channels_df['new_rate'].clip(min_rate, max_rate)
    channels_df['adjustment'] = channels_df['new_rate'] - channels_df['local_fee_rate']

    # --- 1.3 Inbound liquidity reward: if in_percent is very low, discount outbound rate ---
    if liq_reward_factor > 0:
        low_inbound_mask = channels_df['in_percent'] < lowliq_limit
        discount = (channels_df.loc[low_inbound_mask, 'new_rate'] * liq_reward_factor / 100).round(0)
        channels_df.loc[low_inbound_mask, 'new_rate'] = (
            channels_df.loc[low_inbound_mask, 'new_rate'] - discount
        ).clip(min_rate, max_rate)
        channels_df['adjustment'] = channels_df['new_rate'] - channels_df['local_fee_rate']

    # --- Compute new inbound rates ---
    channels_df['new_inbound_rate'] = channels_df['local_inbound_fee_rate'] + channels_df['inbound_adjustment']
    channels_df['new_inbound_rate'] = (channels_df['new_inbound_rate'] / increment).round(0) * increment
    channels_df['new_inbound_rate'] = channels_df['new_inbound_rate'].clip(-((channels_df['ar_max_cost']/100)*channels_df['local_fee_rate']), 0)
    channels_df['inbound_adjustment'] = channels_df['new_inbound_rate'] - channels_df['local_inbound_fee_rate']

    # --- Return results ---
    return channels_df


if __name__ == '__main__':
    print(main(Channels.objects.filter(is_open=True))[['chan_id', 'local_fee_rate', 'new_rate', 'adjustment', 'local_inbound_fee_rate', 'new_inbound_rate', 'inbound_adjustment', 'revenue_per_sat_hour']])
