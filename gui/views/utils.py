from ..models import LocalSettings, Channels
from gui.lnd_deps import lightning_pb2 as ln
from lndg import settings
from requests import get

def graph_links():
    if LocalSettings.objects.filter(key='GUI-GraphLinks').exists():
        graph_links = str(LocalSettings.objects.filter(key='GUI-GraphLinks')[0].value)
    else:
        LocalSettings(key='GUI-GraphLinks', value='https://mempool.space/lightning').save()
        graph_links = 'https://mempool.space/lightning'
    return graph_links

def network_links():
    if LocalSettings.objects.filter(key='GUI-NetLinks').exists():
        network_links = str(LocalSettings.objects.filter(key='GUI-NetLinks')[0].value)
    else:
        LocalSettings(key='GUI-NetLinks', value='https://mempool.space').save()
        network_links = 'https://mempool.space'
    return network_links

def get_tx_fees(txid):
    base_url = network_links() + ('/testnet' if settings.LND_NETWORK == 'testnet' else '') + '/api/tx/'
    request_data = get(base_url + txid).json()
    fee = request_data['fee']
    return fee

def pending_channel_details(channel_point):
    funding_txid, output_index = channel_point.split(':')
    if Channels.objects.filter(funding_txid=funding_txid, output_index=output_index).exists():
        channel = Channels.objects.filter(funding_txid=funding_txid, output_index=output_index)[0]
        return {'short_chan_id':channel.short_chan_id,'chan_id':channel.chan_id,'alias':channel.alias}
    else:
        return {'short_chan_id':None,'chan_id':None,'alias':None}

class is_login_required(object):
    def __init__(self, dec, condition):
        self.decorator = dec
        self.condition = condition

    def __call__(self, func):
        if not self.condition:
            # No login required
            return func
        return self.decorator(func)


def find_next_block_maturity(force_closing_channel):
    #print (f"{datetime.now().strftime('%c')} : {force_closing_channel=}")
    if force_closing_channel.blocks_til_maturity > 0:
        return force_closing_channel.blocks_til_maturity
    for pending_htlc in force_closing_channel.pending_htlcs:
        if pending_htlc.blocks_til_maturity > 0:
            #print (f"{datetime.now().strftime('%c')} : {pending_htlc=}")
            return pending_htlc.blocks_til_maturity
    return -1


def get_local_settings(*prefixes):
    form = []
    if 'AR-' in prefixes:
        form.append({'unit': '', 'form_id': 'update_channels', 'id': 'update_channels'})
        form.append({'unit': '', 'form_id': 'enabled', 'value': 0, 'label': 'AR Enabled', 'id': 'AR-Enabled', 'title':'This enables or disables the auto-scheduling function', 'min':0, 'max':1},)
        form.append({'unit': '%', 'form_id': 'target_percent', 'value': 3.0, 'label': 'AR Target Amount', 'id': 'AR-Target%', 'title': 'The percentage of the total capacity to target as the rebalance amount. Default 3', 'min':0.1, 'max':100})
        form.append({'unit': 'min', 'form_id': 'target_time', 'value': 5, 'label': 'AR Target Time', 'id': 'AR-Time', 'title': 'The time spent in minutes for each individual rebalance attempt. Default 5', 'min':1, 'max':60})
        form.append({'unit': 'ppm', 'form_id': 'fee_rate', 'value': 500, 'label': 'AR Max Fee Rate', 'id': 'AR-MaxFeeRate', 'title': 'The max rate we can ever use to refill a channel with outbound. Default 500', 'min':1, 'max':5000})
        form.append({'unit': '%', 'form_id': 'outbound_percent', 'value': 75, 'label': 'AR Target Out Above', 'id': 'AR-Outbound%', 'title': 'Default oTarget% for new channels. When a channel is not AR enabled; the oTarget% is the minimum outbound a channel must have to be a source for refilling another channel. Default 75', 'min':1, 'max':100})
        form.append({'unit': '%', 'form_id': 'inbound_percent', 'value': 90, 'label': 'AR Target In Above', 'id': 'AR-Inbound%', 'title': 'Default iTarget% for new channels. When a channel is AR enabled; the iTarget% is the minimum inbound a channel must have before selected for auto rebalance. Default 90', 'min':1, 'max':100})
        form.append({'unit': '%', 'form_id': 'max_cost', 'value': 65, 'label': 'AR Max Cost', 'id': 'AR-MaxCost%', 'title': 'The ppm to target which is the percentage of the outbound fee rate for the channel being refilled. Default 65', 'min':1, 'max':100})
        form.append({'unit': '%', 'form_id': 'variance', 'value': 0, 'label': 'AR Variance', 'id': 'AR-Variance', 'title': 'The percentage of the target amount to be randomly varied with every rebalance attempt. Default 0', 'min':0, 'max':100})
        form.append({'unit': 'min', 'form_id': 'wait_period', 'value': 30, 'label': 'AR Wait Period', 'id': 'AR-WaitPeriod', 'title': 'The minutes we should wait after a failed attempt before trying again. Default 30', 'min':1, 'max':10080})
        form.append({'unit': '', 'form_id': 'autopilot', 'value': 0, 'label': 'Autopilot', 'id': 'AR-Autopilot', 'title': 'This enables or disables the Auto-Rebalance function for individual channels based on flow (automatically acts upon suggestions on this page: /actions)', 'min':0, 'max':1})
        form.append({'unit': 'days', 'form_id': 'autopilotdays', 'value': 7, 'label': 'Autopilot Days', 'id': 'AR-APDays', 'title': 'Number of days to consider for autopilot calculations. Default 7', 'min':0, 'max':100})
        form.append({'unit': '', 'form_id': 'workers', 'value': 1, 'label': 'Workers', 'id': 'AR-Workers', 'title': 'Number of concurrent rebalance workers to run at once (use a proper value for your hardware, this will increase the load on the lnd server). Default 1', 'min':1, 'max':12})
        form.append({'unit': 'ppm', 'form_id': 'ar_maxPPM', 'value': 0, 'label': 'AR Max PPM', 'id': 'AR-MaxPPM', 'title': 'Maximum estimated PPM cost for a rebalance attempt. 0 = disabled (no limit). Default 0', 'min':0, 'max':5000})
        form.append({'unit': 'sats', 'form_id': 'ar_dailyBudget', 'value': 0, 'label': 'AR Daily Budget', 'id': 'AR-DailyBudget', 'title': 'Maximum sats to spend on rebalancing fees per day. 0 = unlimited. Default 0', 'min':0, 'max':10000000})
        form.append({'unit': 'sats', 'form_id': 'ar_weeklyBudget', 'value': 0, 'label': 'AR Weekly Budget', 'id': 'AR-WeeklyBudget', 'title': 'Maximum sats to spend on rebalancing fees per week. 0 = unlimited. Default 0', 'min':0, 'max':10000000})
    if 'AF-' in prefixes:
        form.append({'unit': '', 'form_id': 'af_enabled', 'value': 0, 'label': 'Autofee', 'id': 'AF-Enabled', 'title': 'Enable/Disable All Auto-fee functionality', 'min':0, 'max':1})
        form.append({'unit': '', 'form_id': 'af_inbound', 'value': 0, 'label': 'Inbound Fees', 'id': 'AF-InboundFees', 'title': 'Enable/Disable Inbound Auto-fee functionality', 'min':0, 'max':1})
        form.append({'unit': 'ppm', 'form_id': 'af_maxRate', 'value': 2500, 'label': 'AF Max Rate', 'id': 'AF-MaxRate', 'title': 'Maximum Rate that can be adjusted to. Default 2500', 'min':0, 'max':5000})
        form.append({'unit': 'ppm', 'form_id': 'af_minRate', 'value': 0, 'label': 'AF Min Rate', 'id': 'AF-MinRate', 'title': 'Minimum Rate that can be adjusted to. Default 0', 'min':0, 'max':5000})
        form.append({'unit': 'ppm', 'form_id': 'af_increment', 'value': 5, 'label': 'AF Increment', 'id': 'AF-Increment', 'title': 'Target fee rate will always be a multiple of this value. Default 5', 'min':1, 'max':100})
        form.append({'unit': 'x', 'form_id': 'af_multiplier', 'value': 5, 'label': 'AF Multiplier', 'id': 'AF-Multiplier', 'title': 'Multiplier to be applied to Auto-Fee adjustments. Default 5', 'min':1, 'max':100})
        form.append({'unit': '', 'form_id': 'af_failedHTLCs', 'value': 25, 'label': 'AF FailedHTLCs', 'id': 'AF-FailedHTLCs', 'title': 'Failed HTLCs required since last fee update to trigger a fee increase (when chan liq% is below AR-LowLiq). Default 25', 'min':1, 'max':100})
        form.append({'unit': 'hours', 'form_id': 'af_updateHours', 'value': 24, 'label': 'AF Update', 'id': 'AF-UpdateHours', 'title': 'Minimum number of hours between fee updates for an individual channel. Default 24', 'min':1, 'max':100})
        form.append({'unit': '%', 'form_id': 'af_lowliq', 'value': 15, 'label': 'AF LowLiq', 'id': 'AF-LowLiqLimit', 'title': 'Limit for running low liq AF rules (increase when failed htlcs + no inbound). Default 15', 'min':0, 'max':100})
        form.append({'unit': '%', 'form_id': 'af_excess', 'value': 95, 'label': 'AF Excess', 'id': 'AF-ExcessLimit', 'title': 'Limit for running excess liq AF rules (decrease for stagnant channels and those with assisting revenues). Default 95', 'min':0, 'max':100})
        form.append({'unit': '', 'form_id': 'af_timeOfDay', 'value': 0, 'label': 'AF Time of Day', 'id': 'AF-TimeOfDay', 'title': 'Enable time-of-day fee adjustments (peak-hour discounts). Default Off', 'min':0, 'max':1})
        form.append({'unit': '%', 'form_id': 'af_liqRewardFactor', 'value': 20, 'label': 'AF Liq Reward', 'id': 'AF-LiquidityRewardFactor', 'title': 'Percentage discount applied to inbound fee for channels with low inbound liquidity to incentivise routing. Default 20', 'min':0, 'max':100})
        form.append({'unit': '', 'form_id': 'af_competitorFees', 'value': 0, 'label': 'AF Competitor Fees', 'id': 'AF-CompetitorFees', 'title': 'Enable competitor-fee awareness: consider peer fee rates when adjusting fees. Default Off', 'min':0, 'max':1})
    if 'GUI-' in prefixes:
        form.append({'unit': '', 'form_id': 'gui_graphLinks', 'value': 'https://mempool.space/lightning', 'label': 'Graph URL', 'id': 'GUI-GraphLinks', 'title': 'Preferred Graph URL. Default https://mempool.space/lightning'})
        form.append({'unit': '', 'form_id': 'gui_netLinks', 'value': 'https://mempool.space', 'label': 'NET URL', 'id': 'GUI-NetLinks', 'title': 'Preferred NET URL. Default https://mempool.space'})
        form.append({'unit': '', 'form_id': 'gui_numberFormat', 'value': 'de', 'label': 'Number Format', 'id': 'GUI-NumberFormat', 'title': "Number thousands separator: 'de' = European (1.000.000), 'en' = English (1,000,000). Default de", 'options': [('de', 'European (1.000.000)'), ('en', 'English (1,000,000)')]})
    if 'LND-' in prefixes:
        form.append({'unit': '', 'form_id': 'lnd_cleanPayments', 'value': 0, 'label': 'LND Clean Payments', 'id': 'LND-CleanPayments', 'title': 'Clean LND Payments (toggles failed payment clean-up routine)', 'min':0, 'max':1})
        form.append({'unit': 'days', 'form_id': 'lnd_retentionDays', 'value': 30, 'label': 'LND Retention', 'id': 'LND-RetentionDays', 'title': 'LND Retention days for failed payment data', 'min':1, 'max':1000})
        form.append({'unit': '', 'form_id': 'lnd_disableMPP', 'value': 0, 'label': 'Disable MPP', 'id': 'LND-DisableMPP', 'title': 'Disable Multi-Path Payments (MPP) for rebalancing. Default Off', 'min':0, 'max':1})

    for prefix in prefixes:
        ar_settings = LocalSettings.objects.filter(key__contains=prefix).values('key', 'value').order_by('key')
        for field in form:
            for sett in ar_settings:
                if field['id'] == sett['key']:
                    field['value'] = sett['value']
                    break
    return form


def point(ch: Channels):
    channel_point = ln.ChannelPoint()
    channel_point.funding_txid_bytes = bytes.fromhex(ch.funding_txid)
    channel_point.funding_txid_str = ch.funding_txid
    channel_point.output_index = ch.output_index
    return channel_point

