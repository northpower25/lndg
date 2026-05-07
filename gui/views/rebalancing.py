from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Sum, IntegerField, Count, Max, F, Q, Case, When, Value, FloatField
from django.db.models.functions import Round
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..forms import *
from ..serializers import *
from ..models import Channels, Rebalancer, LocalSettings, Autopilot, Autofees, InboundFeeLog
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
import af
from .utils import is_login_required, get_local_settings, graph_links

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def rebalances(request):
    if request.method == 'GET':
        try:
            return render(request, 'rebalances.html')
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def rebalancing(request):
    if request.method == 'GET':
        context = {
            'local_settings': get_local_settings('AR-'),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
        }
        return render(request, 'rebalancing.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def autopilot(request):
    if request.method == 'GET':
        chan_id = request.GET.urlencode()[1:]
        filter_21d = datetime.now() - timedelta(days=21)
        autopilot = Autopilot.objects.filter(timestamp__gte=filter_21d).order_by('-id') if chan_id == "" else Autopilot.objects.filter(chan_id = chan_id).filter(timestamp__gte=filter_21d).order_by('-id')
        context = {
            'autopilot': autopilot
        }
        return render(request, 'autopilot.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def outbound_fee_log(request):
    if request.method == 'GET':
        try:
            chan_id = request.GET.urlencode()[1:]
            filter_7d = datetime.now() - timedelta(days=7)
            outbound_fee_log_df = DataFrame.from_records(Autofees.objects.filter(timestamp__gte=filter_7d).order_by('-id').values() if chan_id == "" else Autofees.objects.filter(chan_id=chan_id).filter(timestamp__gte=filter_7d).order_by('-id').values())
            if outbound_fee_log_df.shape[0]> 0:
                outbound_fee_log_df['change'] = outbound_fee_log_df.apply(lambda row: 0 if row.old_value == 0 else round((row.new_value-row.old_value)*100/row.old_value, 1), axis=1)
            context = {
                'outbound_fee_log': [] if outbound_fee_log_df.empty else outbound_fee_log_df.to_dict(orient='records')
            }
            return render(request, 'outbound_fee_log.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def inbound_fee_log(request):
    if request.method == 'GET':
        try:
            chan_id = request.GET.urlencode()[1:]
            filter_7d = datetime.now() - timedelta(days=7)
            inbound_fee_log_df = DataFrame.from_records(InboundFeeLog.objects.filter(timestamp__gte=filter_7d).order_by('-id').values() if chan_id == "" else InboundFeeLog.objects.filter(chan_id=chan_id).filter(timestamp__gte=filter_7d).order_by('-id').values())
            if inbound_fee_log_df.shape[0]> 0:
                inbound_fee_log_df['change'] = inbound_fee_log_df.apply(lambda row: 0 if row.old_value == 0 else round((row.new_value-row.old_value)*100/row.old_value, 1), axis=1)
            context = {
                'inbound_fee_log': [] if inbound_fee_log_df.empty else inbound_fee_log_df.to_dict(orient='records')
            }
            return render(request, 'inbound_fee_log.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def rebalance(request):
    if request.method == 'POST':
        form = RebalancerForm(request.POST)
        if form.is_valid():
            try:
                if Channels.objects.filter(is_active=True, is_open=True, remote_pubkey=form.cleaned_data['last_hop_pubkey']).exists() or form.cleaned_data['last_hop_pubkey'] == '':
                    chan_ids = [ch.chan_id for ch in form.cleaned_data['outgoing_chan_ids']]
                    if len(chan_ids) > 0:
                        if form.cleaned_data['last_hop_pubkey'] != '':
                            target_channel = Channels.objects.filter(is_active=True, is_open=True, remote_pubkey=form.cleaned_data['last_hop_pubkey']).first()
                            target_alias = target_channel.alias if target_channel.alias != '' else target_channel.remote_pubkey[:12]
                        else:
                            target_alias = ''
                        fee_limit = round(form.cleaned_data['fee_limit']*form.cleaned_data['value']*0.000001, 3)
                        Rebalancer(value=form.cleaned_data['value'], fee_limit=fee_limit, outgoing_chan_ids=str(chan_ids).replace('\'', ''), last_hop_pubkey=form.cleaned_data['last_hop_pubkey'], target_alias=target_alias, duration=form.cleaned_data['duration'], manual=True).save()
                        messages.success(request, 'Rebalancer request created!')
                    else:
                        messages.error(request, 'You must select atleast one outgoing channel.')
                else:
                    messages.error(request, 'Target peer is invalid or unknown.')
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Error entering rebalancer request! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_settings(request):
    if request.method == 'POST':
        template = [{'form_id': 'enabled', 'value': 0, 'parse': lambda x: int(x),'id': 'AR-Enabled'},
                    {'form_id': 'target_percent', 'value': 3.0, 'parse': lambda x: float(x),'id': 'AR-Target%'},
                    {'form_id': 'target_time', 'value': 5, 'parse': lambda x: int(x),'id': 'AR-Time'},
                    {'form_id': 'fee_rate', 'value': 500, 'parse': lambda x: int(x),'id': 'AR-MaxFeeRate'},
                    {'form_id': 'outbound_percent', 'value': 75, 'parse': lambda x: int(x),'id': 'AR-Outbound%'},
                    {'form_id': 'inbound_percent', 'value': 90, 'parse': lambda x: int(x),'id': 'AR-Inbound%'},
                    {'form_id': 'max_cost', 'value': 65, 'parse': lambda x: int(x),'id': 'AR-MaxCost%'},
                    {'form_id': 'variance', 'value': 0, 'parse': lambda x: int(x),'id': 'AR-Variance'},
                    {'form_id': 'wait_period', 'value': 30, 'parse': lambda x: int(x),'id': 'AR-WaitPeriod'},
                    {'form_id': 'autopilot', 'value': 0, 'parse': lambda x: int(x),'id': 'AR-Autopilot'},
                    {'form_id': 'autopilotdays', 'value': 7, 'parse': lambda x: int(x),'id': 'AR-APDays'},
                    {'form_id': 'workers', 'value': 1, 'parse': lambda x: int(x),'id': 'AR-Workers'},
                    #AF
                    {'form_id': 'af_enabled', 'value': 0, 'parse': lambda x: int(x),'id': 'AF-Enabled'},
                    {'form_id': 'af_inbound', 'value': 0, 'parse': lambda x: int(x),'id': 'AF-InboundFees'},
                    {'form_id': 'af_maxRate', 'value': 2500, 'parse': lambda x: int(x),'id': 'AF-MaxRate'},
                    {'form_id': 'af_minRate', 'value': 0, 'parse': lambda x: int(x),'id': 'AF-MinRate'},
                    {'form_id': 'af_increment', 'value': 5, 'parse': lambda x: int(x),'id': 'AF-Increment'},
                    {'form_id': 'af_multiplier', 'value': 5, 'parse': lambda x: int(x),'id': 'AF-Multiplier'},
                    {'form_id': 'af_failedHTLCs', 'value': 25, 'parse': lambda x: int(x),'id': 'AF-FailedHTLCs'},
                    {'form_id': 'af_updateHours', 'value': 24, 'parse': lambda x: int(x),'id': 'AF-UpdateHours'},
                    {'form_id': 'af_lowliq', 'value': 15, 'parse': lambda x: int(x),'id': 'AF-LowLiqLimit'},
                    {'form_id': 'af_excess', 'value': 95, 'parse': lambda x: int(x),'id': 'AF-ExcessLimit'},
                    {'form_id': 'af_timeOfDay', 'value': 0, 'parse': lambda x: int(x),'id': 'AF-TimeOfDay'},
                    {'form_id': 'af_liqRewardFactor', 'value': 20, 'parse': lambda x: int(x),'id': 'AF-LiquidityRewardFactor'},
                    {'form_id': 'af_competitorFees', 'value': 0, 'parse': lambda x: int(x),'id': 'AF-CompetitorFees'},
                    #AR budget/ppm
                    {'form_id': 'ar_maxPPM', 'value': 0, 'parse': lambda x: int(x),'id': 'AR-MaxPPM'},
                    {'form_id': 'ar_dailyBudget', 'value': 0, 'parse': lambda x: int(x),'id': 'AR-DailyBudget'},
                    {'form_id': 'ar_weeklyBudget', 'value': 0, 'parse': lambda x: int(x),'id': 'AR-WeeklyBudget'},
                    #GUI
                    {'form_id': 'gui_graphLinks', 'value': 'https://mempool.space/lightning', 'parse': lambda x: str(x),'id': 'GUI-GraphLinks'},
                    {'form_id': 'gui_netLinks', 'value': 'https://mempool.space', 'parse': lambda x: str(x),'id': 'GUI-NetLinks'},
                    {'form_id': 'gui_numberFormat', 'value': 'de', 'parse': lambda x: str(x) if str(x) in ('de', 'en') else 'de', 'id': 'GUI-NumberFormat'},
                    #LND
                    {'form_id': 'lnd_cleanPayments', 'value': 0, 'parse': lambda x: int(x), 'id': 'LND-CleanPayments'},
                    {'form_id': 'lnd_retentionDays', 'value': 30, 'parse': lambda x: int(x), 'id': 'LND-RetentionDays'},
                    {'form_id': 'lnd_disableMPP', 'value': 0, 'parse': lambda x: int(x), 'id': 'LND-DisableMPP'},
                    ]

        form = LocalSettingsForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Invalid Request. Please try again.')
        else:
            update_channels = form.cleaned_data['update_channels']
            for field in template:
                value = form.cleaned_data[field['form_id']]
                if value is not None:
                    value = field['parse'](value)
                    try:
                        db_value = LocalSettings.objects.get(key=field['id'])
                    except:
                        LocalSettings(key=field['id'], value=field['value']).save()
                        db_value = LocalSettings.objects.get(key=field['id'])
                    if db_value.value == str(value) or len(str(value)) == 0:
                        continue
                    db_value.value = value
                    db_value.save()

                    if update_channels and field['id'] in ['AR-Target%', 'AR-Outbound%','AR-Inbound%','AR-MaxCost%']:
                        if field['id'] == 'AR-Target%':
                            Channels.objects.all().update(ar_amt_target=Round(F('capacity')*(value/100), output_field=IntegerField()))
                        elif field['id'] == 'AR-Outbound%':
                            Channels.objects.all().update(ar_out_target=value)
                        elif field['id'] == 'AR-Inbound%':
                            Channels.objects.all().update(ar_in_target=value)
                        elif field['id'] == 'AR-MaxCost%':
                            Channels.objects.all().update(ar_max_cost=value)
                        messages.success(request, 'All channels ' + field['id'] + ' updated to: ' + str(value))
                    else:
                        messages.success(request, field['id'] + ' updated to: ' + str(value))

    return redirect(request.META.get('HTTP_REFERER'))


@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def rebalance_stats(request):
    try:
        filter_7day = datetime.now() - timedelta(days=7)
        rebalances = Rebalancer.objects.filter(stop__gt=filter_7day).values('last_hop_pubkey').annotate(attempts=Count('last_hop_pubkey'), successes=Sum(Case(When(status=2, then=1), output_field=IntegerField())))
        return Response(rebalances)
    except Exception as e:
        error = str(e)
        return Response({'error': 'Unable to fetch stats! Error: ' + error})

