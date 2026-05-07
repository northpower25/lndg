from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Sum, IntegerField, Count, Max, Q
from django.db.models.functions import Round
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..forms import *  # noqa: F403
from ..serializers import *  # noqa: F403
from ..models import Channels, LocalSettings, PendingChannels, Peers, Forwards, Rebalancer, Payments, Invoices, Autofees, AvoidNodes, FailedHTLCs
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from pandas import DataFrame
from .utils import is_login_required, get_local_settings, graph_links, network_links, get_tx_fees, point
import gui.jobs.auto_fees as af

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def channels(request):
    if request.method == 'GET':
        filter_7day = datetime.now() - timedelta(days=7)
        filter_30day = datetime.now() - timedelta(days=30)
        forwards = Forwards.objects.filter(forward_date__gte=filter_30day)
        payments = Payments.objects.filter(status=2, creation_date__gte=filter_30day, rebal_chan__isnull=False)
        invoices = Invoices.objects.filter(state=1, r_hash__in=payments.values_list('payment_hash'))
        channels = Channels.objects.filter(is_open=True, private=False)
        channels_df = DataFrame.from_records(channels.values())
        if channels_df.shape[0] > 0:
            forwards_df_30d = DataFrame.from_records(forwards.values())
            forwards_df_7d = DataFrame.from_records(forwards.filter(forward_date__gte=filter_7day).values())
            forwards_df_in_30d_sum = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
            forwards_df_out_30d_sum = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
            forwards_df_in_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
            forwards_df_out_7d_sum = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
            forwards_df_in_30d_count = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_in', as_index=True).count()
            forwards_df_out_30d_count = DataFrame() if forwards_df_30d.empty else forwards_df_30d.groupby('chan_id_out', as_index=True).count()
            forwards_df_in_7d_count = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_in', as_index=True).count()
            forwards_df_out_7d_count = DataFrame() if forwards_df_7d.empty else forwards_df_7d.groupby('chan_id_out', as_index=True).count()
            payments_df_30d = DataFrame.from_records(payments.values())
            payments_df_7d = DataFrame.from_records(payments.filter(creation_date__gte=filter_7day).values())
            payments_df_30d_sum = DataFrame() if payments_df_30d.empty else payments_df_30d.groupby('chan_out', as_index=True).sum(numeric_only=True)
            payments_df_7d_sum = DataFrame() if payments_df_7d.empty else payments_df_7d.groupby('chan_out', as_index=True).sum(numeric_only=True)
            payments_df_30d_count = DataFrame() if payments_df_30d.empty else payments_df_30d.groupby('chan_out', as_index=True).count()
            payments_df_7d_count = DataFrame() if payments_df_7d.empty else payments_df_7d.groupby('chan_out', as_index=True).count()
            invoices_df_30d = DataFrame.from_records(invoices.values())
            invoices_df_7d = DataFrame.from_records(invoices.filter(settle_date__gte=filter_7day).values())
            invoices_df_30d_sum = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True).sum(numeric_only=True)
            invoices_df_7d_sum = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).sum(numeric_only=True)
            invoices_df_30d_count = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True).count()
            invoices_df_7d_count = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).count()
            invoice_hashes_7d = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
            invoice_hashes_30d = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True)['r_hash'].apply(list)
            channels_df['mil_capacity'] = channels_df.apply(lambda row: round(row.capacity/1000000, 1), axis=1)
            channels_df['local_balance'] = channels_df.apply(lambda row: row.local_balance + row.pending_outbound, axis=1)
            channels_df['remote_balance'] = channels_df.apply(lambda row: row.remote_balance + row.pending_inbound, axis=1)
            channels_df['routed_in_7day'] = channels_df.apply(lambda row: forwards_df_in_7d_count.loc[row.chan_id].amt_out_msat if (forwards_df_in_7d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['routed_out_7day'] = channels_df.apply(lambda row: forwards_df_out_7d_count.loc[row.chan_id].amt_out_msat if (forwards_df_out_7d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['routed_in_30day'] = channels_df.apply(lambda row: forwards_df_in_30d_count.loc[row.chan_id].amt_out_msat if (forwards_df_in_30d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['routed_out_30day'] = channels_df.apply(lambda row: forwards_df_out_30d_count.loc[row.chan_id].amt_out_msat if (forwards_df_out_30d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_routed_in_7day'] = channels_df.apply(lambda row: int(forwards_df_in_7d_sum.loc[row.chan_id].amt_out_msat/100000000)/10 if (forwards_df_in_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_routed_out_7day'] = channels_df.apply(lambda row: int(forwards_df_out_7d_sum.loc[row.chan_id].amt_out_msat/100000000)/10 if (forwards_df_out_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_routed_in_30day'] = channels_df.apply(lambda row: int(forwards_df_in_30d_sum.loc[row.chan_id].amt_out_msat/100000000)/10 if (forwards_df_in_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_routed_out_30day'] = channels_df.apply(lambda row: int(forwards_df_out_30d_sum.loc[row.chan_id].amt_out_msat/100000000)/10 if (forwards_df_out_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['rebal_in_30day'] = channels_df.apply(lambda row: invoices_df_30d_count.loc[row.chan_id].amt_paid if invoices_df_30d_count.empty == False and (invoices_df_30d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['rebal_out_30day'] = channels_df.apply(lambda row: payments_df_30d_count.loc[row.chan_id].value if payments_df_30d_count.empty == False and (payments_df_30d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_rebal_in_30day'] = channels_df.apply(lambda row: int(invoices_df_30d_sum.loc[row.chan_id].amt_paid/100000)/10 if invoices_df_30d_count.empty == False and (invoices_df_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_rebal_out_30day'] = channels_df.apply(lambda row: int(payments_df_30d_sum.loc[row.chan_id].value/100000)/10 if payments_df_30d_count.empty == False and (payments_df_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['rebal_in_7day'] = channels_df.apply(lambda row: invoices_df_7d_count.loc[row.chan_id].amt_paid if invoices_df_7d_count.empty == False and (invoices_df_7d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['rebal_out_7day'] = channels_df.apply(lambda row: payments_df_7d_count.loc[row.chan_id].value if payments_df_7d_count.empty == False and (payments_df_7d_count.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_rebal_in_7day'] = channels_df.apply(lambda row: int(invoices_df_7d_sum.loc[row.chan_id].amt_paid/100000)/10 if invoices_df_7d_count.empty == False and (invoices_df_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['amt_rebal_out_7day'] = channels_df.apply(lambda row: int(payments_df_7d_sum.loc[row.chan_id].value/100000)/10 if payments_df_7d_count.empty == False and (payments_df_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['revenue_7day'] = channels_df.apply(lambda row: int(forwards_df_out_7d_sum.loc[row.chan_id].fee) if forwards_df_out_7d_sum.empty == False and (forwards_df_out_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['revenue_30day'] = channels_df.apply(lambda row: int(forwards_df_out_30d_sum.loc[row.chan_id].fee) if forwards_df_out_30d_sum.empty == False and (forwards_df_out_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['revenue_assist_7day'] = channels_df.apply(lambda row: int(forwards_df_in_7d_sum.loc[row.chan_id].fee) if forwards_df_in_7d_sum.empty == False and (forwards_df_in_7d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['revenue_assist_30day'] = channels_df.apply(lambda row: int(forwards_df_in_30d_sum.loc[row.chan_id].fee) if forwards_df_in_30d_sum.empty == False and (forwards_df_in_30d_sum.index == row.chan_id).any() else 0, axis=1)
            channels_df['costs_7day'] = channels_df.apply(lambda row: 0 if row['rebal_in_7day'] == 0 else int(payments_df_7d.set_index('payment_hash', inplace=False).loc[invoice_hashes_7d[row.chan_id] if invoice_hashes_7d.empty == False and (invoice_hashes_7d.index == row.chan_id).any() else []]['fee'].sum()), axis=1)
            channels_df['costs_30day'] = channels_df.apply(lambda row: 0 if row['rebal_in_30day'] == 0 else int(payments_df_30d.set_index('payment_hash', inplace=False).loc[invoice_hashes_30d[row.chan_id] if invoice_hashes_30d.empty == False and (invoice_hashes_30d.index == row.chan_id).any() else []]['fee'].sum()), axis=1)
            channels_df['profits_7day'] = channels_df.apply(lambda row: row['revenue_7day'] - row['costs_7day'], axis=1)
            channels_df['profits_30day'] = channels_df.apply(lambda row: row['revenue_30day'] - row['costs_30day'], axis=1)
            channels_df['open_block'] = channels_df.apply(lambda row: int(row.chan_id)>>40, axis=1)
            apy_7day = round((channels_df['profits_7day'].sum()*5214.2857)/channels_df['local_balance'].sum(), 2)
            apy_30day = round((channels_df['profits_30day'].sum()*1216.6667)/channels_df['local_balance'].sum(), 2)
            active_updates = channels_df['num_updates'].sum()
            channels_df['updates'] = channels_df.apply(lambda row: 0 if active_updates == 0 else int(round((row['num_updates']/active_updates)*100, 0)), axis=1)
            node_outbound = channels_df['local_balance'].sum()
            node_capacity = channels_df['capacity'].sum()
            if node_capacity > 0:
                outbound_ratio = node_outbound/node_capacity
                channels_df['apy_7day'] = channels_df.apply(lambda row: round((row['profits_7day']*5214.2857)/(row['capacity']*outbound_ratio), 2), axis=1)
                channels_df['apy_30day'] = channels_df.apply(lambda row: round((row['profits_30day']*1216.6667)/(row['capacity']*outbound_ratio), 2), axis=1)
                channels_df['cv_7day'] = channels_df.apply(lambda row: round((row['revenue_7day']*5214.2857)/(row['capacity']*outbound_ratio) + (row['revenue_assist_7day']*5214.2857)/(row['capacity']*(1-outbound_ratio)), 2), axis=1)
                channels_df['cv_30day'] = channels_df.apply(lambda row: round((row['revenue_30day']*1216.6667)/(row['capacity']*outbound_ratio) + (row['revenue_assist_30day']*1216.6667)/(row['capacity']*(1-outbound_ratio)), 2), axis=1)
            else:
                channels_df['apy_7day'] = 0.0
                channels_df['apy_30day'] = 0.0
                channels_df['cv_7day'] = 0.0
                channels_df['cv_30day'] = 0.0
        else:
            apy_7day = 0
            apy_30day = 0
        context = {
            'channels': [] if channels_df.empty else channels_df.sort_values(by=['cv_30day'], ascending=False).to_dict(orient='records'),
            'apy_7day': apy_7day,
            'apy_30day': apy_30day,
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'channels.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def fees(request):
    if request.method == 'GET':
        channels = Channels.objects.filter(is_open=True, private=False)
        results_df = af.main(channels)
        context = {
            'channels': [] if results_df.empty else results_df.sort_values(by=['out_percent']).to_dict(orient='records'),
            'local_settings': get_local_settings('AF-'),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'fee_rates.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def channel(request):
    if request.method == 'GET':
        chan_id = request.GET.urlencode()[1:]
        if Channels.objects.filter(chan_id=chan_id).exists():
            filter_1day = datetime.now() - timedelta(days=1)
            filter_7day = datetime.now() - timedelta(days=7)
            filter_30day = datetime.now() - timedelta(days=30)
            forwards_df = DataFrame.from_records(Forwards.objects.filter(Q(chan_id_in=chan_id) | Q(chan_id_out=chan_id)).values())
            payments_df = DataFrame.from_records(Payments.objects.filter(status=2).filter(chan_out=chan_id).filter(rebal_chan__isnull=False).annotate(ppm=Round((Sum('fee')*1000000)/Sum('value'), output_field=IntegerField())).values())
            rebal_payments = Payments.objects.filter(status=2).filter(rebal_chan=chan_id)
            invoices_df = DataFrame.from_records(Invoices.objects.filter(state=1).filter(chan_in=chan_id).filter(r_hash__in=rebal_payments).values())
            channels_df = DataFrame.from_records(Channels.objects.filter(is_open=True).values())
            if channels_df.empty:
                node_outbound = 0
                node_capacity = 0
            else:
                node_outbound = channels_df['local_balance'].sum()
                node_capacity = channels_df['capacity'].sum()
            channel = Channels.objects.filter(chan_id=chan_id)
            channels_df = DataFrame.from_records(channel.values())
            rebalancer_df = DataFrame.from_records(Rebalancer.objects.filter(last_hop_pubkey=channels_df['remote_pubkey'][0]).annotate(ppm=Round((Sum('fee_limit')*1000000)/Sum('value'), output_field=IntegerField())).order_by('-id').values())
            failed_htlc_df = DataFrame.from_records(FailedHTLCs.objects.exclude(wire_failure=99).filter(Q(chan_id_in=chan_id) | Q(chan_id_out=chan_id)).order_by('-id').values())
            peer_info_df = DataFrame.from_records(Peers.objects.filter(pubkey=channels_df['remote_pubkey'][0]).values())
            channels_df['local_balance'] = channels_df['local_balance'] + channels_df['pending_outbound']
            channels_df['remote_balance'] = channels_df['remote_balance'] + channels_df['pending_inbound']
            channels_df['in_percent'] = ((channels_df['remote_balance']/channels_df['capacity'])*100).round(0).astype(int)
            channels_df['out_percent'] = ((channels_df['local_balance']/channels_df['capacity'])*100).round(0).astype(int)
            channels_df['open_block'] = channels_df['chan_id'].apply(lambda row: int(row)>>40).astype(int)
            channels_df['routed_in'] = 0
            channels_df['routed_in_30day'] = 0
            channels_df['routed_in_7day'] = 0
            channels_df['routed_in_1day'] = 0
            channels_df['routed_out'] = 0
            channels_df['routed_out_30day'] = 0
            channels_df['routed_out_7day'] = 0
            channels_df['routed_out_1day'] = 0
            channels_df['amt_routed_in'] = 0
            channels_df['amt_routed_in_30day'] = 0
            channels_df['amt_routed_in_7day'] = 0
            channels_df['amt_routed_in_7day_fees'] = 0
            channels_df['amt_routed_in_1day'] = 0
            channels_df['amt_routed_out'] = 0
            channels_df['amt_routed_out_30day'] = 0
            channels_df['amt_routed_out_7day'] = 0
            channels_df['amt_routed_out_7day_fees'] = 0
            channels_df['amt_routed_out_1day'] = 0
            channels_df['average_in'] = 0
            channels_df['average_in_30day'] = 0
            channels_df['average_in_7day'] = 0
            channels_df['average_in_1day'] = 0
            channels_df['average_out'] = 0
            channels_df['average_out_30day'] = 0
            channels_df['average_out_7day'] = 0
            channels_df['average_out_1day'] = 0
            channels_df['revenue'] = 0
            channels_df['revenue_30day'] = 0
            channels_df['revenue_7day'] = 0
            channels_df['revenue_7day_fees'] = 0
            channels_df['revenue_1day'] = 0
            channels_df['revenue_assist'] = 0
            channels_df['revenue_assist_30day'] = 0
            channels_df['revenue_assist_7day'] = 0
            channels_df['revenue_assist_7day_fees'] = 0
            channels_df['revenue_assist_1day'] = 0
            channels_df['rebal_out'] = 0
            channels_df['rebal_out_30day'] = 0
            channels_df['rebal_out_7day'] = 0
            channels_df['rebal_out_1day'] = 0
            channels_df['amt_rebal_out'] = 0
            channels_df['amt_rebal_out_30day'] = 0
            channels_df['amt_rebal_out_7day'] = 0
            channels_df['amt_rebal_out_1day'] = 0
            channels_df['rebal_in'] = 0
            channels_df['rebal_in_30day'] = 0
            channels_df['rebal_in_7day'] = 0
            channels_df['rebal_in_1day'] = 0
            channels_df['amt_rebal_in'] = 0
            channels_df['amt_rebal_in_30day'] = 0
            channels_df['amt_rebal_in_7day'] = 0
            channels_df['amt_rebal_in_1day'] = 0
            channels_df['costs'] = 0
            channels_df['costs_30day'] = 0
            channels_df['costs_7day'] = 0
            channels_df['costs_1day'] = 0
            channels_df['attempts'] = 0
            channels_df['attempts_30day'] = 0
            channels_df['attempts_7day'] = 0
            channels_df['attempts_1day'] = 0
            channels_df['success'] = 0
            channels_df['success_30day'] = 0
            channels_df['success_7day'] = 0
            channels_df['success_1day'] = 0
            channels_df['success_rate'] = 0
            channels_df['success_rate_30day'] = 0
            channels_df['success_rate_7day'] = 0
            channels_df['success_rate_1day'] = 0
            channels_df['failed_out'] = 0
            channels_df['failed_out_30day'] = 0
            channels_df['failed_out_7day'] = 0
            channels_df['failed_out_1day'] = 0
            start_date = None
            if failed_htlc_df.shape[0]> 0:
                channels_df['failed_out'] = len(failed_htlc_df[(failed_htlc_df['chan_id_out']==chan_id) & (failed_htlc_df['wire_failure']==15) & (failed_htlc_df['failure_detail']==6) & (failed_htlc_df['amount']>failed_htlc_df['chan_out_liq']+failed_htlc_df['chan_out_pending'])])
                failed_htlc_df_30d = failed_htlc_df.loc[failed_htlc_df['timestamp'] >= filter_30day]
                if failed_htlc_df_30d.shape[0]> 0:
                    channels_df['failed_out_30day'] = len(failed_htlc_df_30d[(failed_htlc_df_30d['chan_id_out']==chan_id) & (failed_htlc_df_30d['wire_failure']==15) & (failed_htlc_df_30d['failure_detail']==6) & (failed_htlc_df_30d['amount']>failed_htlc_df_30d['chan_out_liq']+failed_htlc_df_30d['chan_out_pending'])])
                    failed_htlc_df_7d = failed_htlc_df_30d.loc[failed_htlc_df_30d['timestamp'] >= filter_7day]
                    if failed_htlc_df_7d.shape[0]> 0:
                        channels_df['failed_out_7day'] = len(failed_htlc_df_7d[(failed_htlc_df_7d['chan_id_out']==chan_id) & (failed_htlc_df_7d['wire_failure']==15) & (failed_htlc_df_7d['failure_detail']==6) & (failed_htlc_df_7d['amount']>failed_htlc_df_7d['chan_out_liq']+failed_htlc_df_7d['chan_out_pending'])])
                        failed_htlc_df_1d = failed_htlc_df_7d.loc[failed_htlc_df_7d['timestamp'] >= filter_1day]
                        if failed_htlc_df_1d.shape[0]> 0:
                            channels_df['failed_out_1day'] = len(failed_htlc_df_1d[(failed_htlc_df_1d['chan_id_out']==chan_id) & (failed_htlc_df_1d['wire_failure']==15) & (failed_htlc_df_1d['failure_detail']==6) & (failed_htlc_df_1d['amount']>failed_htlc_df_1d['chan_out_liq']+failed_htlc_df_1d['chan_out_pending'])])
            if rebalancer_df.shape[0]> 0:
                channels_df['attempts'] = len(rebalancer_df[(rebalancer_df['status']>=2) & (rebalancer_df['status']<400)])
                channels_df['success'] = len(rebalancer_df[rebalancer_df['status']==2])
                channels_df['success_rate'] = 0 if channels_df['attempts'].iloc[0] == 0 else ((channels_df['success']/channels_df['attempts'])*100).astype(int)
                rebalancer_df_30d = rebalancer_df.loc[rebalancer_df['stop'] >= filter_30day]
                if rebalancer_df_30d.shape[0]> 0:
                    channels_df['attempts_30day'] = len(rebalancer_df_30d[(rebalancer_df_30d['status']>=2) & (rebalancer_df_30d['status']<400)])
                    channels_df['success_30day'] = len(rebalancer_df_30d[rebalancer_df_30d['status']==2])
                    channels_df['success_rate_30day'] = 0 if channels_df['attempts_30day'].iloc[0] == 0 else ((channels_df['success_30day']/channels_df['attempts_30day'])*100).astype(int)
                    rebalancer_df_7d = rebalancer_df_30d.loc[rebalancer_df_30d['stop'] >= filter_7day]
                    if rebalancer_df_7d.shape[0]> 0:
                        channels_df['attempts_7day'] = len(rebalancer_df_7d[(rebalancer_df_7d['status']>=2) & (rebalancer_df_7d['status']<400)])
                        channels_df['success_7day'] = len(rebalancer_df_7d[rebalancer_df_7d['status']==2])
                        channels_df['success_rate_7day'] = 0 if channels_df['attempts_7day'].iloc[0] == 0 else ((channels_df['success_7day']/channels_df['attempts_7day'])*100).astype(int)
                        rebalancer_df_1d = rebalancer_df_7d.loc[rebalancer_df_7d['stop'] >= filter_1day]
                        if rebalancer_df_1d.shape[0]> 0:
                            channels_df['attempts_1day'] = len(rebalancer_df_1d[(rebalancer_df_1d['status']>=2) & (rebalancer_df_1d['status']<400)])
                            channels_df['success_1day'] = len(rebalancer_df_1d[rebalancer_df_1d['status']==2])
                            channels_df['success_rate_1day'] = 0 if channels_df['attempts_1day'].iloc[0] == 0 else ((channels_df['success_1day']/channels_df['attempts_1day'])*100).astype(int)
            if forwards_df.shape[0]> 0:
                forwards_in_df = forwards_df[forwards_df['chan_id_in'] == chan_id]
                forwards_out_df = forwards_df[forwards_df['chan_id_out'] == chan_id]
                forwards_df['amt_in'] = (forwards_df['amt_in_msat']/1000).astype(int)
                forwards_df['amt_out'] = (forwards_df['amt_out_msat']/1000).astype(int)
                forwards_df['ppm'] = (forwards_df['fee']/(forwards_df['amt_out']/1000000)).astype(int)
            else:
                forwards_in_df = DataFrame()
                forwards_out_df = DataFrame()
            if forwards_in_df.shape[0]> 0:
                forwards_in_df_count = forwards_in_df.groupby('chan_id_in', as_index=True).count()
                forwards_in_df_sum = forwards_in_df.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                channels_df['routed_in'] = forwards_in_df_count.loc[chan_id].amt_out_msat
                channels_df['amt_routed_in'] = int(forwards_in_df_sum.loc[chan_id].amt_out_msat/1000)
                channels_df['average_in'] = 0 if channels_df['routed_in'].iloc[0] == 0 else (channels_df['amt_routed_in']/channels_df['routed_in']).astype(int)
                channels_df['revenue_assist'] = int(forwards_in_df_sum.loc[chan_id].fee) if forwards_in_df_sum.empty == False else 0
                forwards_in_df_30d = forwards_in_df.loc[forwards_in_df['forward_date'] >= filter_30day]
                if forwards_in_df_30d.shape[0] > 0:
                    forwards_in_df_30d_count = forwards_in_df_30d.groupby('chan_id_in', as_index=True).count()
                    forwards_in_df_30d_sum = forwards_in_df_30d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                    channels_df['routed_in_30day'] = forwards_in_df_30d_count.loc[chan_id].amt_out_msat
                    channels_df['amt_routed_in_30day'] = int(forwards_in_df_30d_sum.loc[chan_id].amt_out_msat/1000)
                    channels_df['average_in_30day'] = 0 if channels_df['routed_in_30day'].iloc[0] == 0 else (channels_df['amt_routed_in_30day']/channels_df['routed_in_30day']).astype(int)
                    channels_df['revenue_assist_30day'] = int(forwards_in_df_30d_sum.loc[chan_id].fee) if forwards_in_df_30d_sum.empty == False else 0
                    forwards_in_df_7d = forwards_in_df_30d.loc[forwards_in_df_30d['forward_date'] >= filter_7day]
                    if forwards_in_df_7d.shape[0] > 0:
                        forwards_in_df_7d_count = forwards_in_df_7d.groupby('chan_id_in', as_index=True).count()
                        forwards_in_df_7d_sum = forwards_in_df_7d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                        channels_df['routed_in_7day'] = forwards_in_df_7d_count.loc[chan_id].amt_out_msat
                        channels_df['amt_routed_in_7day'] = int(forwards_in_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                        channels_df['average_in_7day'] = 0 if channels_df['routed_in_7day'].iloc[0] == 0 else (channels_df['amt_routed_in_7day']/channels_df['routed_in_7day']).astype(int)
                        channels_df['revenue_assist_7day'] = int(forwards_in_df_7d_sum.loc[chan_id].fee)
                        forwards_in_df_7d_sum = forwards_in_df_7d[forwards_in_df_7d['amt_out_msat']>=1000000].groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                        if forwards_in_df_7d_sum.shape[0] > 0:
                            channels_df['amt_routed_in_7day_fees'] = int(forwards_in_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['revenue_assist_7day_fees'] = int(forwards_in_df_7d_sum.loc[chan_id].fee)
                        forwards_in_df_1d = forwards_in_df_7d.loc[forwards_in_df_7d['forward_date'] >= filter_1day]
                        if forwards_in_df_1d.shape[0] > 0:
                            forwards_in_df_1d_count = forwards_in_df_1d.groupby('chan_id_in', as_index=True).count()
                            forwards_in_df_1d_sum = forwards_in_df_1d.groupby('chan_id_in', as_index=True).sum(numeric_only=True)
                            channels_df['routed_in_1day'] = forwards_in_df_1d_count.loc[chan_id].amt_out_msat
                            channels_df['amt_routed_in_1day'] = int(forwards_in_df_1d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['average_in_1day'] = 0 if channels_df['routed_in_1day'].iloc[0] == 0 else (channels_df['amt_routed_in_1day']/channels_df['routed_in_1day']).astype(int)
                            channels_df['revenue_assist_1day'] = int(forwards_in_df_1d_sum.loc[chan_id].fee)
            if forwards_out_df.shape[0]> 0:
                start_date = forwards_out_df['forward_date'].min()
                forwards_out_df_count = forwards_out_df.groupby('chan_id_out', as_index=True).count()
                forwards_out_df_sum = forwards_out_df.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
                channels_df['routed_out'] = forwards_out_df_count.loc[chan_id].amt_out_msat
                channels_df['amt_routed_out'] = int(forwards_out_df_sum.loc[chan_id].amt_out_msat/1000)
                channels_df['average_out'] = 0 if channels_df['routed_out'].iloc[0] == 0 else (channels_df['amt_routed_out']/channels_df['routed_out']).astype(int)
                channels_df['revenue'] = int(forwards_out_df_sum.loc[chan_id].fee) if forwards_out_df_sum.empty == False else 0
                forwards_out_df_30d = forwards_out_df.loc[forwards_out_df['forward_date'] >= filter_30day]
                if forwards_out_df_30d.shape[0] > 0:
                    forwards_out_df_30d_count = forwards_out_df_30d.groupby('chan_id_out', as_index=True).count()
                    forwards_out_df_30d_sum = forwards_out_df_30d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
                    channels_df['routed_out_30day'] = forwards_out_df_30d_count.loc[chan_id].amt_out_msat
                    channels_df['amt_routed_out_30day'] = int(forwards_out_df_30d_sum.loc[chan_id].amt_out_msat/1000)
                    channels_df['average_out_30day'] = 0 if channels_df['routed_out_30day'].iloc[0] == 0 else (channels_df['amt_routed_out_30day']/channels_df['routed_out_30day']).astype(int)
                    channels_df['revenue_30day'] = int(forwards_out_df_30d_sum.loc[chan_id].fee) if forwards_out_df_30d_sum.empty == False else 0
                    forwards_out_df_7d = forwards_out_df_30d.loc[forwards_out_df_30d['forward_date'] >= filter_7day]
                    if forwards_out_df_7d.shape[0] > 0:
                        forwards_out_df_7d_count = forwards_out_df_7d.groupby('chan_id_out', as_index=True).count()
                        forwards_out_df_7d_sum = forwards_out_df_7d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
                        channels_df['routed_out_7day'] = forwards_out_df_7d_count.loc[chan_id].amt_out_msat
                        channels_df['amt_routed_out_7day'] = int(forwards_out_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                        channels_df['average_out_7day'] = 0 if channels_df['routed_out_7day'].iloc[0] == 0 else (channels_df['amt_routed_out_7day']/channels_df['routed_out_7day']).astype(int)
                        channels_df['revenue_7day'] = int(forwards_out_df_7d_sum.loc[chan_id].fee)
                        forwards_out_df_7d_sum = forwards_out_df_7d[forwards_out_df_7d['amt_out_msat']>=1000000].groupby('chan_id_out', as_index=True).sum(numeric_only=True)
                        if forwards_out_df_7d_sum.shape[0] > 0:
                            channels_df['amt_routed_out_7day_fees'] = int(forwards_out_df_7d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['revenue_7day_fees'] = int(forwards_out_df_7d_sum.loc[chan_id].fee)
                        forwards_out_df_1d = forwards_out_df_7d.loc[forwards_out_df_7d['forward_date'] >= filter_1day]
                        if forwards_out_df_1d.shape[0] > 0:
                            forwards_out_df_1d_count = forwards_out_df_1d.groupby('chan_id_out', as_index=True).count()
                            forwards_out_df_1d_sum = forwards_out_df_1d.groupby('chan_id_out', as_index=True).sum(numeric_only=True)
                            channels_df['routed_out_1day'] = forwards_out_df_1d_count.loc[chan_id].amt_out_msat
                            channels_df['amt_routed_out_1day'] = int(forwards_out_df_1d_sum.loc[chan_id].amt_out_msat/1000)
                            channels_df['average_out_1day'] = 0 if channels_df['routed_out_1day'].iloc[0] == 0 else (channels_df['amt_routed_out_1day']/channels_df['routed_out_1day']).astype(int)
                            channels_df['revenue_1day'] = int(forwards_out_df_1d_sum.loc[chan_id].fee)
            if payments_df.shape[0] > 0:
                payments_df_count = payments_df.groupby('chan_out', as_index=True).count()
                payments_df_sum = payments_df.groupby('chan_out', as_index=True).sum(numeric_only=True)
                channels_df['rebal_out'] = payments_df_count.loc[chan_id].value
                channels_df['amt_rebal_out'] = int(payments_df_sum.loc[chan_id].value)
                payments_df_30d = payments_df.loc[payments_df['creation_date'] >= filter_30day]
                if payments_df_30d.shape[0] > 0:
                    payments_df_30d_count = payments_df_30d.groupby('chan_out', as_index=True).count()
                    payments_df_30d_sum = payments_df_30d.groupby('chan_out', as_index=True).sum(numeric_only=True)
                    channels_df['rebal_out_30day'] = payments_df_30d_count.loc[chan_id].value
                    channels_df['amt_rebal_out_30day'] = int(payments_df_30d_sum.loc[chan_id].value)
                    payments_df_7d = payments_df_30d.loc[payments_df_30d['creation_date'] >= filter_7day]
                    if payments_df_7d.shape[0] > 0:
                        payments_df_7d_count = payments_df_7d.groupby('chan_out', as_index=True).count()
                        payments_df_7d_sum = payments_df_7d.groupby('chan_out', as_index=True).sum(numeric_only=True)
                        channels_df['rebal_out_7day'] = payments_df_7d_count.loc[chan_id].value
                        channels_df['amt_rebal_out_7day'] = int(payments_df_7d_sum.loc[chan_id].value)
                        payments_df_1d = payments_df_7d.loc[payments_df_7d['creation_date'] >= filter_1day]
                        if payments_df_1d.shape[0] > 0:
                            payments_df_1d_count = payments_df_1d.groupby('chan_out', as_index=True).count()
                            payments_df_1d_sum = payments_df_1d.groupby('chan_out', as_index=True).sum(numeric_only=True)
                            channels_df['rebal_out_1day'] = payments_df_1d_count.loc[chan_id].value
                            channels_df['amt_rebal_out_1day'] = int(payments_df_1d_sum.loc[chan_id].value)
            if invoices_df.shape[0]> 0:
                invoices_df_30d = invoices_df.loc[invoices_df['settle_date'] >= filter_30day]
                invoices_df_7d = invoices_df_30d.loc[invoices_df_30d['settle_date'] >= filter_7day]
                invoices_df_1d = invoices_df_7d.loc[invoices_df_7d['settle_date'] >= filter_1day]
                invoices_df_count = DataFrame() if invoices_df.empty else invoices_df.groupby('chan_in', as_index=True).count()
                invoices_df_30d_count = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True).count()
                invoices_df_7d_count = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).count()
                invoices_df_1d_count = DataFrame() if invoices_df_1d.empty else invoices_df_1d.groupby('chan_in', as_index=True).count()
                invoices_df_sum = DataFrame() if invoices_df.empty else invoices_df.groupby('chan_in', as_index=True).sum(numeric_only=True)
                invoices_df_30d_sum = DataFrame() if invoices_df_30d.empty else invoices_df_30d.groupby('chan_in', as_index=True).sum(numeric_only=True)
                invoices_df_7d_sum = DataFrame() if invoices_df_7d.empty else invoices_df_7d.groupby('chan_in', as_index=True).sum(numeric_only=True)
                invoices_df_1d_sum = DataFrame() if invoices_df_1d.empty else invoices_df_1d.groupby('chan_in', as_index=True).sum(numeric_only=True)
                channels_df['rebal_in'] = invoices_df_count.loc[chan_id].amt_paid if invoices_df_count.empty == False else 0
                channels_df['rebal_in_30day'] = invoices_df_30d_count.loc[chan_id].amt_paid if invoices_df_30d_count.empty == False else 0
                channels_df['rebal_in_7day'] = invoices_df_7d_count.loc[chan_id].amt_paid if invoices_df_7d_count.empty == False else 0
                channels_df['rebal_in_1day'] = invoices_df_1d_count.loc[chan_id].amt_paid if invoices_df_1d_count.empty == False else 0
                channels_df['amt_rebal_in'] = int(invoices_df_sum.loc[chan_id].amt_paid) if invoices_df_count.empty == False else 0
                channels_df['amt_rebal_in_30day'] = int(invoices_df_30d_sum.loc[chan_id].amt_paid) if invoices_df_30d_count.empty == False else 0
                channels_df['amt_rebal_in_7day'] = int(invoices_df_7d_sum.loc[chan_id].amt_paid) if invoices_df_7d_count.empty == False else 0
                channels_df['amt_rebal_in_1day'] = int(invoices_df_1d_sum.loc[chan_id].amt_paid) if invoices_df_1d_count.empty == False else 0
                rebal_payments_df = DataFrame.from_records(rebal_payments.filter(value__gte=1000).values())
                if rebal_payments_df.shape[0] > 0:
                    invoice_hashes = DataFrame() if invoices_df.empty else invoices_df.loc[invoices_df['value'] >= 1000].groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_30d = DataFrame() if invoices_df_30d.empty else invoices_df_30d.loc[invoices_df_30d['value'] >= 1000].groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_7d = DataFrame() if invoices_df_7d.empty else invoices_df_7d.loc[invoices_df_7d['value'] >= 1000].groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    invoice_hashes_1d = DataFrame() if invoices_df_1d.empty else invoices_df_1d.loc[invoices_df_1d['value'] >= 1000].groupby('chan_in', as_index=True)['r_hash'].apply(list)
                    channels_df['costs'] = 0 if channels_df['rebal_in'][0] == 0 or invoice_hashes.empty == True else int(rebal_payments_df.set_index('payment_hash', inplace=False).loc[invoice_hashes[chan_id]]['fee'].sum())
                    channels_df['costs_30day'] = 0 if channels_df['rebal_in_30day'][0] == 0 or invoice_hashes_30d.empty == True else int(rebal_payments_df.set_index('payment_hash', inplace=False).loc[invoice_hashes_30d[chan_id]]['fee'].sum())
                    channels_df['costs_7day'] = 0 if channels_df['rebal_in_7day'][0] == 0 or invoice_hashes_7d.empty == True else int(rebal_payments_df.set_index('payment_hash', inplace=False).loc[invoice_hashes_7d[chan_id]]['fee'].sum())
                    channels_df['costs_1day'] = 0 if channels_df['rebal_in_1day'][0] == 0 or invoice_hashes_1d.empty == True else int(rebal_payments_df.set_index('payment_hash', inplace=False).loc[invoice_hashes_1d[chan_id]]['fee'].sum())
            channels_df['costs'] += Closures.objects.filter(funding_txid=channels_df['funding_txid'][0],funding_index=channels_df['output_index'][0])[0].closing_costs if Closures.objects.filter(funding_txid=channels_df['funding_txid'][0],funding_index=channels_df['output_index'][0]).exists() else 0
            channels_df['profits'] = channels_df['revenue'] - channels_df['costs']
            channels_df['profits_30day'] = channels_df['revenue_30day'] - channels_df['costs_30day']
            channels_df['profits_7day'] = channels_df['revenue_7day'] - channels_df['costs_7day']
            channels_df['profits_1day'] = channels_df['revenue_1day'] - channels_df['costs_1day']
            channels_df['profits_vol'] = 0 if channels_df['amt_routed_out'].iloc[0] == 0 else (channels_df['profits']/(channels_df['amt_routed_out']/1000000)).astype(int)
            channels_df['profits_vol_30day'] = 0 if channels_df['amt_routed_out_30day'].iloc[0] == 0 else (channels_df['profits_30day']/(channels_df['amt_routed_out_30day']/1000000)).astype(int)
            channels_df['profits_vol_7day'] = 0 if channels_df['amt_routed_out_7day'].iloc[0] == 0 else (channels_df['profits_7day']/(channels_df['amt_routed_out_7day']/1000000)).astype(int)
            channels_df['profits_vol_1day'] = 0 if channels_df['amt_routed_out_1day'].iloc[0] == 0 else (channels_df['profits_1day']/(channels_df['amt_routed_out_1day']/1000000)).astype(int)
            channels_df = channels_df.copy()
            channels_df['out_rate'] = int((channels_df['revenue_7day_fees']/channels_df['amt_routed_out_7day_fees'])*1000000) if channels_df['amt_routed_out_7day_fees'][0] > 0 else 0
            channels_df['rebal_ppm'] = int((channels_df['costs_7day']/channels_df['amt_rebal_in_7day'])*1000000) if channels_df['amt_rebal_in_7day'][0] > 0 else 0
            channels_df['assisted_ratio'] = round((channels_df['revenue_assist_7day_fees'] if channels_df['revenue_7day_fees'][0] == 0 else channels_df['revenue_assist_7day_fees']/channels_df['revenue_7day_fees']), 2)
            channels_df['inbound_can'] = ((channels_df['remote_balance']*100)/channels_df['capacity'])/channels_df['ar_in_target']
            channels_df['fee_ratio'] = 100 if channels_df['local_fee_rate'].iloc[0] == 0 else (round((channels_df['remote_fee_rate']/channels_df['local_fee_rate'])*1000/10)).astype(int)
            channels_df['fee_check'] = 1 if channels_df['ar_max_cost'].iloc[0] == 0 else (((channels_df['fee_ratio']/channels_df['ar_max_cost'])*1000)/10).round(0).astype(int)
            channels_df = channels_df.copy()
            channels_df['steps'] = 0 if channels_df['inbound_can'].iloc[0] < 1 else (((channels_df['in_percent']-channels_df['ar_in_target'])/((channels_df['ar_amt_target']/channels_df['capacity'])*100))+0.999).astype(int)
            channels_df['apy'] = 0.0
            channels_df['apy_30day'] = 0.0
            channels_df['apy_7day'] = 0.0
            channels_df['apy_1day'] = 0.0
            channels_df['assisted_apy'] = 0.0
            channels_df['assisted_apy_30day'] = 0.0
            channels_df['assisted_apy_7day'] = 0.0
            channels_df['assisted_apy_1day'] = 0.0
            channels_df['cv'] = 0.0
            channels_df['cv_30day'] = 0.0
            channels_df['cv_7day'] = 0.0
            channels_df['cv_1day'] = 0.0
            if node_capacity > 0:
                outbound_ratio = node_outbound/node_capacity
                if start_date is not None:
                    time_delta = datetime.now() - start_date.to_pydatetime()
                    days_routing = time_delta.days + (time_delta.seconds/86400)
                    channels_df['apy'] = round(((channels_df['profits']/days_routing)*36500)/(channels_df['capacity']*outbound_ratio), 2)
                    channels_df['assisted_apy'] = round(((channels_df['revenue_assist']/days_routing)*36500)/(channels_df['capacity']*(1-outbound_ratio)), 2)
                    channels_df['cv'] = round(((channels_df['revenue']/days_routing)*36500)/(channels_df['capacity']*outbound_ratio) + channels_df['assisted_apy'], 2)
                channels_df['apy_30day'] = round((channels_df['profits_30day']*1216.6667)/(channels_df['capacity']*outbound_ratio), 2)
                channels_df['apy_7day'] = round((channels_df['profits_7day']*5214.2857)/(channels_df['capacity']*outbound_ratio), 2)
                channels_df['apy_1day'] = round((channels_df['profits_1day']*36500)/(channels_df['capacity']*outbound_ratio), 2)
                channels_df['assisted_apy_30day'] = round((channels_df['revenue_assist_30day']*1216.6667)/(channels_df['capacity']*(1-outbound_ratio)), 2)
                channels_df['assisted_apy_7day'] = round((channels_df['revenue_assist_7day']*5214.2857)/(channels_df['capacity']*(1-outbound_ratio)), 2)
                channels_df['assisted_apy_1day'] = round((channels_df['revenue_assist_1day']*36500)/(channels_df['capacity']*(1-outbound_ratio)), 2)
                channels_df['cv_30day'] = round((channels_df['revenue_30day']*1216.6667)/(channels_df['capacity']*outbound_ratio) + channels_df['assisted_apy_30day'], 2)
                channels_df['cv_7day'] = round((channels_df['revenue_7day']*5214.2857)/(channels_df['capacity']*outbound_ratio) + channels_df['assisted_apy_7day'], 2)
                channels_df['cv_1day'] = round((channels_df['revenue_1day']*36500)/(channels_df['capacity']*outbound_ratio) + channels_df['assisted_apy_1day'], 2)
            autofees_df = DataFrame.from_records(Autofees.objects.filter(chan_id=chan_id).filter(timestamp__gte=filter_30day).order_by('-id').values())
            if autofees_df.shape[0]> 0:
                autofees_df['change'] = autofees_df.apply(lambda row: 0 if row.old_value == 0 else round((row.new_value-row.old_value)*100/row.old_value, 1), axis=1)
            results_df = af.main(channel)
            channels_df['new_rate'] = results_df[results_df['chan_id']==chan_id]['new_rate']
            channels_df['adjustment'] = results_df[results_df['chan_id']==chan_id]['adjustment']
            channels_df['net_routed_7day'] = results_df[results_df['chan_id']==chan_id]['net_routed_7day']
        else:
            channels_df = DataFrame()
            payments_df = DataFrame()
            invoices_df = DataFrame()
            peer_info_df = DataFrame()
            autofees_df = DataFrame()
        context = {
            'chan_id': chan_id,
            'channel': [] if channels_df.empty else channels_df.to_dict(orient='records')[0],
            'incoming_htlcs': PendingHTLCs.objects.filter(chan_id=chan_id).filter(incoming=True).order_by('hash_lock'),
            'outgoing_htlcs': PendingHTLCs.objects.filter(chan_id=chan_id).filter(incoming=False).order_by('hash_lock'),
            'peer_info': [] if peer_info_df.empty else peer_info_df.to_dict(orient='records')[0],
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links(),
            'autofees': [] if autofees_df.empty else autofees_df.to_dict(orient='records'),
        }
        try:
            return render(request, 'channel.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def opens(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        self_pubkey = stub.GetInfo(ln.GetInfoRequest()).identity_pubkey
        current_peers = Channels.objects.filter(is_open=True).values_list('remote_pubkey')
        exlcude_list = AvoidNodes.objects.values_list('pubkey')
        filter_60day = datetime.now() - timedelta(days=60)
        payments_60day = Payments.objects.filter(creation_date__gte=filter_60day, status=2).values_list('payment_hash')
        open_list = PaymentHops.objects.filter(payment_hash__in=payments_60day).exclude(node_pubkey=self_pubkey).exclude(node_pubkey__in=current_peers).exclude(node_pubkey__in=exlcude_list).values('node_pubkey').annotate(ppm=(Sum('fee')/Sum('amt'))*1000000, score=Round((Round(Count('id')/1, output_field=IntegerField())+Round(Sum('amt')/100000, output_field=IntegerField()))/10, output_field=IntegerField()), count=Count('id'), amount=Sum('amt'), fees=Sum('fee'), sum_cost_to=Sum('cost_to')/(Sum('amt')/1000000), alias=Max('alias')).exclude(score=0).order_by('-score', 'ppm')[:21]
        context = {
            'open_list': open_list,
            'avoid_list': AvoidNodes.objects.all(),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
        }
        return render(request, 'open_list.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def unprofitable_channels(request):
    if request.method == 'GET':
        # Get the timeframe from the request, default to 30 days
        timeframe = request.GET.get('timeframe', '30')
        timeframe_options = {
            '1': {'days': 1, 'name': '1 Day'},
            '7': {'days': 7, 'name': '7 Days'},
            '30': {'days': 30, 'name': '30 Days'},
            '90': {'days': 90, 'name': '90 Days'}
        }

        selected_timeframe = timeframe_options.get(timeframe, timeframe_options['30'])
        filter_date = datetime.now() - timedelta(days=selected_timeframe['days'])

        # Get active channels in a single query
        channels = Channels.objects.filter(is_active=True, is_open=True)
        channel_ids = [c.chan_id for c in channels]

        # Get current block height once
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            current_block_height = stub.GetInfo(ln.GetInfoRequest()).block_height
        except Exception as e:
            print(f"Error getting current block height: {e}")
            current_block_height = 0 

        VERY_NEW_DAYS = 7
        ESTABLISHED_DAYS = 30
        MAX_AGE_BONUS = 2.0

        channel_metrics_dict = {chan_id: {
            'routed_out_sats': 0,
            'last_routing': None,
            'last_routing_amount': 0,
            'rebalanced_out_sats': 0, # For display of rebalances OUT
            'last_rebalance': None,    # For display of last rebalance OUT
            'last_rebalance_amount': 0, # For display of last rebalance OUT amount
            'fee_revenue': 0,
            'rebalance_fee_cost': 0, # THIS WILL BE THE CORRECTED COST FOR PROFIT
            'assisted_revenue': 0
        } for chan_id in channel_ids}

        # 1. Get outbound forwarding stats (routing out) - Populates 'fee_revenue'
        out_forwards = Forwards.objects.filter(
            chan_id_out__in=channel_ids,
            forward_date__gte=filter_date
        )

        for forward in out_forwards:
            chan_id = forward.chan_id_out
            metrics = channel_metrics_dict[chan_id]
            metrics['routed_out_sats'] += int(forward.amt_out_msat / 1000) if forward.amt_out_msat else 0
            metrics['fee_revenue'] += forward.fee if forward.fee else 0
            if metrics['last_routing'] is None or forward.forward_date > metrics['last_routing']:
                metrics['last_routing'] = forward.forward_date
                metrics['last_routing_amount'] = int(forward.amt_out_msat / 1000) if forward.amt_out_msat else 0

        # 2. Get inbound forwarding stats (assisted revenue) - Populates 'assisted_revenue'
        in_forwards = Forwards.objects.filter(
            chan_id_in__in=channel_ids,
            forward_date__gte=filter_date
        )

        for forward in in_forwards:
            chan_id = forward.chan_id_in
            channel_metrics_dict[chan_id]['assisted_revenue'] += forward.fee if forward.fee else 0

        # --- Calculate rebalance_fee_cost for PROFIT (cost of rebalances INTO the channel) ---
        # This section calculates the cost component for the profit metric accurately.
        all_rebalance_payments_in_period = Payments.objects.filter(
            creation_date__gte=filter_date,
            status=2,
            rebal_chan__isnull=False 
        )
        payment_fees_by_hash = {p.payment_hash: p.fee for p in all_rebalance_payments_in_period}

        rebalance_invoices_into_our_channels = Invoices.objects.filter(
            chan_in__in=channel_ids,
            state=1, 
            settle_date__gte=filter_date,
            r_hash__in=all_rebalance_payments_in_period.values_list('payment_hash', flat=True)
        )

        for invoice in rebalance_invoices_into_our_channels:
            chan_id_receiving_rebalance = invoice.chan_in
            if chan_id_receiving_rebalance in channel_metrics_dict:
                cost_of_this_rebalance_in = payment_fees_by_hash.get(invoice.r_hash, 0)
                channel_metrics_dict[chan_id_receiving_rebalance]['rebalance_fee_cost'] += cost_of_this_rebalance_in
        # --- End of rebalance_fee_cost calculation for profit ---

        # 3. Get outbound rebalance data FOR DISPLAY PURPOSES (rebalanced_out_sats, last_rebalance)
        # This data is for display columns like "Rebalanced Out Sats" and "Last Rebalance (Out)".
        # It does NOT contribute to the 'rebalance_fee_cost' used in profit calculation.
        rebalance_payments_out_for_display = Payments.objects.filter(
            chan_out__in=channel_ids, 
            creation_date__gte=filter_date,
            status=2, 
            rebal_chan__isnull=False 
        )

        for payment in rebalance_payments_out_for_display:
            chan_id = payment.chan_out 
            if chan_id in channel_metrics_dict: # Ensure channel is in our scope
                metrics = channel_metrics_dict[chan_id]
                metrics['rebalanced_out_sats'] += payment.value if payment.value else 0
                # Update last_rebalance and last_rebalance_amount if this payment is later
                if metrics['last_rebalance'] is None or payment.creation_date > metrics['last_rebalance']:
                    metrics['last_rebalance'] = payment.creation_date
                    metrics['last_rebalance_amount'] = payment.value if payment.value else 0

        # Calculate normalized metrics for each channel
        outbound_activities = []
        outbound_ratios = []  # NEW: Track outbound activity as a ratio of channel capacity
        assisted_revenues = []
        fee_rates = []

        for chan_id, metrics_data in channel_metrics_dict.items(): # Changed metrics to metrics_data to avoid conflict
            # Get channel object to access capacity
            channel_obj = next((c for c in channels if c.chan_id == chan_id), None)
            if channel_obj:
                total_outbound = metrics_data['routed_out_sats'] + metrics_data['rebalanced_out_sats']
                outbound_activities.append(total_outbound)

                # Calculate outbound ratio (outbound activity / channel capacity)
                capacity = channel_obj.capacity or 1  # Avoid division by zero
                outbound_ratio = total_outbound / capacity
                outbound_ratios.append(outbound_ratio)

                assisted_revenues.append(metrics_data['assisted_revenue'])
                fee_rate = getattr(channel_obj, 'local_fee_rate', 0) or 0
                fee_rates.append(fee_rate)

        # Find min/max values for normalization
        max_outbound = max(outbound_activities) if outbound_activities else 1
        max_outbound_ratio = max(outbound_ratios) if outbound_ratios else 1
        max_assisted = max(assisted_revenues) if assisted_revenues else 1
        max_fee_rate = max(fee_rates) if fee_rates else 1000

        # Thresholds for high/medium/low classifications
        # NEW: Use ratio-based thresholds for activity
        high_ratio_threshold = max(max_outbound_ratio * 0.7, 0.5)  # At least 50% of capacity or 70% of max ratio
        medium_ratio_threshold = max(max_outbound_ratio * 0.3, 0.2)  # At least 20% of capacity or 30% of max ratio
        high_assisted_threshold = max_assisted * 0.7
        medium_assisted_threshold = max_assisted * 0.3
        high_fee_threshold = max(max_fee_rate, 1000) * 0.7
        medium_fee_threshold = max(max_fee_rate, 1000) * 0.3

        # Build the final channel metrics list
        channel_metrics = []

        for channel in channels:
            chan_id = channel.chan_id
            metrics = channel_metrics_dict[chan_id] # Use 'metrics' here as it's conventional in this loop

            # Calculate profit (fee revenue - rebalance costs)
            # THIS NOW USES THE CORRECTED 'rebalance_fee_cost'
            profit = metrics['fee_revenue'] - metrics['rebalance_fee_cost']

            # Format last routing and rebalance for display
            last_routing_display = { # Renamed to avoid conflict if 'last_routing' is a direct key
                'date': metrics['last_routing'],
                'amount': metrics['last_routing_amount']
            } if metrics['last_routing'] else None

            last_rebalance_display = { # Renamed
                'date': metrics['last_rebalance'], # This is last rebalance OUT
                'amount': metrics['last_rebalance_amount'] # This is last rebalance OUT amount
            } if metrics['last_rebalance'] else None

            # Calculate local ratio (percentage of capacity that is local balance)
            local_ratio = channel.local_balance / channel.capacity if channel.capacity > 0 else 0
            local_ratio_pct = round(local_ratio * 100, 2)

            # Get activity metrics
            routing_out = metrics['routed_out_sats']
            rebalancing_out = metrics['rebalanced_out_sats']
            total_outbound = routing_out + rebalancing_out
            assisted_revenue = metrics['assisted_revenue']

            # NEW: Calculate outbound ratio (outbound activity / channel capacity)
            outbound_ratio = total_outbound / channel.capacity if channel.capacity > 0 else 0

            # Get fee rate
            local_fee_rate = getattr(channel, 'local_fee_rate', 0) or 0

            # Calculate priority score based on activity and fees
            # Lower score = better (less stuck), higher score = worse (more stuck)
            # We'll use a score from 0-7 matching your priority list

            # Start with worst score
            priority_score = 7.0

            # Check conditions using ratio-based thresholds
            if outbound_ratio > high_ratio_threshold and local_fee_rate > high_fee_threshold:
                # 1) High routing out ratio with high local_fee_rate
                priority_score = 1.0
            elif outbound_ratio > high_ratio_threshold and assisted_revenue > high_assisted_threshold:
                # 2) High rebalancing out ratio with high assisted revenue
                priority_score = 2.0
            elif outbound_ratio > medium_ratio_threshold and local_fee_rate > medium_fee_threshold:
                # 3) Medium routing out ratio with medium local_fee_rate
                priority_score = 3.0
            elif outbound_ratio > medium_ratio_threshold and assisted_revenue > medium_assisted_threshold:
                # 4) Medium rebalancing out ratio with medium assisted revenue
                priority_score = 4.0
            elif outbound_ratio > 0 and local_fee_rate > 0:
                # 5) Low routing out ratio and low local_fee_rate
                priority_score = 5.0
            elif outbound_ratio > 0 and assisted_revenue > 0:
                # 6) Low rebalancing out ratio and low assisted revenue
                priority_score = 6.0
            # else: 7) No activity and no compensation (already set as default)

            # Apply assisted revenue bonus
            if assisted_revenue > high_assisted_threshold:
                # Significant bonus for high assisted revenue
                assisted_bonus = 1.5
                priority_score = max(1.0, priority_score - assisted_bonus)
            elif assisted_revenue > medium_assisted_threshold:
                # Moderate bonus for medium assisted revenue
                assisted_bonus = 0.75
                priority_score = max(1.0, priority_score - assisted_bonus)
            elif assisted_revenue > 0:
                # Small bonus for any assisted revenue
                assisted_bonus = 0.25
                priority_score = max(1.0, priority_score - assisted_bonus)

            # Apply local liquidity adjustment
            # If local_ratio is low, reduce the penalty (improve the score)
            low_local_threshold = 0.2  # 20% or less is considered low local liquidity
            high_local_threshold = 0.8  # 80% or more is considered high local liquidity

            if local_ratio <= low_local_threshold:
                # Significant improvement for channels with very low local liquidity
                local_liquidity_adjustment = 3.0 * (1 - (local_ratio / low_local_threshold))
                priority_score = max(1.0, priority_score - local_liquidity_adjustment)
            elif local_ratio >= high_local_threshold:
                # Slight penalty for channels with very high local liquidity
                local_liquidity_adjustment = 0.5 * ((local_ratio - high_local_threshold) / (1 - high_local_threshold))
                priority_score = min(7.0, priority_score + local_liquidity_adjustment)

            age_bonus = 0.0
            if current_block_height > 0 and channel.chan_id: # Ensure we have data
                try:
                    opening_block_height = int(channel.chan_id) >> 40
                    if opening_block_height > 0: # Ensure valid opening height
                        channel_age_blocks = max(0, current_block_height - opening_block_height)
                        channel_age_days = channel_age_blocks / 144 # Approx days

                        if channel_age_days < VERY_NEW_DAYS:
                            # Max bonus for very new channels
                            age_bonus = MAX_AGE_BONUS
                        elif channel_age_days < ESTABLISHED_DAYS:
                            # Linearly decreasing bonus for channels between 7 and 30 days
                            age_progress = (channel_age_days - VERY_NEW_DAYS) / (ESTABLISHED_DAYS - VERY_NEW_DAYS)
                            age_bonus = MAX_AGE_BONUS * (1 - age_progress)
                        # else: age_bonus remains 0 for established channels

                except Exception as e:
                    # Handle potential errors during age calculation gracefully
                    print(f"Error calculating age for chan_id {channel.chan_id}: {e}")
                    channel_age_days = -1 # Indicate unknown age
            else:
                 channel_age_days = -1 # Indicate unknown age if block height or chan_id missing


            # Apply the age bonus, ensuring score doesn't go below 1.0
            priority_score = max(1.0, priority_score - age_bonus)

            # Normalize to 0-1 scale (divide by 7)
            smart_stuck_index = round(priority_score / 7.0, 2)

            # Add metrics to the list
            channel_metrics.append({
                'chan_id': chan_id,
                'alias': channel.alias or "---",
                'routed_out_sats': routing_out,
                'last_routing': last_routing_display,
                'rebalanced_out_sats': rebalancing_out,
                'last_rebalance': last_rebalance_display,
                'profit': profit,
                'assisted_revenue': assisted_revenue,
                'initiator': channel.initiator,
                'capacity': channel.capacity,
                'capacity_millions': round(channel.capacity / 1000000, 1),
                'local_balance': channel.local_balance,
                'remote_balance': channel.remote_balance,
                'local_ratio': local_ratio_pct,
                'stuck_index': smart_stuck_index,
                'local_fee_rate': local_fee_rate,
                'outbound_ratio': round(outbound_ratio * 100, 2),  # Add this to show the ratio as percentage
                'priority_rank': round(priority_score, 1),  # Shows the exact ranking with adjustment
                'age_days': round(channel_age_days) if channel_age_days >= 0 else 'N/A' # Add age for display
            })

        # Sort by profit (ascending to show least profitable first)
        channel_metrics.sort(key=lambda x: x['profit'])

        context = {
            'channels': channel_metrics,
            'timeframe': timeframe,
            'timeframe_name': selected_timeframe['name'],
            'timeframe_options': timeframe_options
        }

        return render(request, 'unprofitable_channels.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def actions(request):
    if request.method == 'GET':
        channels = Channels.objects.filter(is_active=True, is_open=True, private=False).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity'), inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity'))
        filter_7day = datetime.now() - timedelta(days=7)
        forwards = Forwards.objects.filter(forward_date__gte=filter_7day)
        action_list = []
        for channel in channels:
            result = {}
            result['chan_id'] = channel.chan_id
            result['short_chan_id'] = channel.short_chan_id
            result['remote_pubkey'] = channel.remote_pubkey
            result['alias'] = channel.alias
            result['capacity'] = channel.capacity
            result['local_balance'] = channel.local_balance + channel.pending_outbound
            result['remote_balance'] = channel.remote_balance + channel.pending_inbound
            result['outbound_percent'] = int(round(channel.outbound_percent/10, 0))
            result['inbound_percent'] = int(round(channel.inbound_percent/10, 0))
            result['unsettled_balance'] = channel.unsettled_balance
            result['local_base_fee'] = channel.local_base_fee
            result['local_fee_rate'] = channel.local_fee_rate
            result['remote_base_fee'] = channel.remote_base_fee
            result['remote_fee_rate'] = channel.remote_fee_rate
            result['routed_in_7day'] = forwards.filter(chan_id_in=channel.chan_id).count()
            result['routed_out_7day'] = forwards.filter(chan_id_out=channel.chan_id).count()
            result['i7D'] = 0 if result['routed_in_7day'] == 0 else int(forwards.filter(chan_id_in=channel.chan_id).aggregate(Sum('amt_in_msat'))['amt_in_msat__sum']/10000000)/100
            result['o7D'] = 0 if result['routed_out_7day'] == 0 else int(forwards.filter(chan_id_out=channel.chan_id).aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/10000000)/100
            result['auto_rebalance'] = channel.auto_rebalance
            result['ar_target'] = channel.ar_in_target
            if result['o7D'] > (result['i7D']*1.10) and result['outbound_percent'] > 75:
                #print('Case 1: Pass')
                continue
            elif result['o7D'] > (result['i7D']*1.10) and result['inbound_percent'] > 75 and channel.auto_rebalance == False:
                if channel.local_fee_rate <= channel.remote_fee_rate:
                    #print('Case 6: Peer Fee Too High')
                    result['output'] = 'Peer Fee Too High'
                    result['reason'] = 'o7D > i7D AND Inbound Liq > 75% AND Local Fee < Remote Fee'
                    continue
                #print('Case 2: Enable AR')
                result['output'] = 'Enable AR'
                result['reason'] = 'o7D > i7D AND Inbound Liq > 75%'
            elif result['o7D'] < (result['i7D']*1.10) and result['outbound_percent'] > 75 and channel.auto_rebalance == True:
                #print('Case 3: Disable AR')
                result['output'] = 'Disable AR'
                result['reason'] = 'o7D < i7D AND Outbound Liq > 75%'
            elif result['o7D'] < (result['i7D']*1.10) and result['inbound_percent'] > 75:
                #print('Case 4: Pass')
                continue
            else:
                #print('Case 5: Pass')
                continue
            if len(result) > 0:
                action_list.append(result)
        context = {
            'action_list': action_list,
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'action_list.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_channel(request):
    if request.method == 'POST':
        form = UpdateChannel(request.POST)
        if form.is_valid() and Channels.objects.filter(chan_id=form.cleaned_data['chan_id']).exists():
            chan_id = form.cleaned_data['chan_id']
            target = form.cleaned_data['target']
            update_target = int(form.cleaned_data['update_target'])
            db_channel = Channels.objects.get(chan_id=chan_id)
            if update_target == 0:
                stub = lnrpc.LightningStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=target, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv))
                db_channel.local_base_fee = target
                db_channel.save()
                messages.success(request, 'Base fee for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            elif update_target == 1:
                stub = lnrpc.LightningStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(target/1000000), time_lock_delta=db_channel.local_cltv))
                old_fee_rate = db_channel.local_fee_rate
                db_channel.local_fee_rate = target
                db_channel.fees_updated = datetime.now()
                db_channel.save()
                Autofees(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, setting=("Manual"), old_value=old_fee_rate, new_value=db_channel.local_fee_rate).save()
                messages.success(request, 'Fee rate for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            elif update_target == 12:
                stub = lnrpc.LightningStub(lnd_connect())
                version = stub.GetInfo(ln.GetInfoRequest()).version
                if float(version[:4]) >= 0.18:
                    channel_point = point(db_channel)
                    inbound_fee_rate = db_channel.local_inbound_fee_rate if db_channel.local_inbound_fee_rate else 0
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, inbound_fee=ln.InboundFee(base_fee_msat=target, fee_rate_ppm=inbound_fee_rate)))
                    db_channel.local_inbound_base_fee = target
                    db_channel.save()
                    messages.success(request, 'Inbound base fee for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
                else:
                    messages.error(request, 'LND version too low to set inbound fees, update to v0.18+')
            elif update_target == 13:
                stub = lnrpc.LightningStub(lnd_connect())
                version = stub.GetInfo(ln.GetInfoRequest()).version
                if float(version[:4]) >= 0.18:
                    channel_point = point(db_channel)
                    inbound_base_fee = db_channel.local_inbound_base_fee if db_channel.local_inbound_base_fee else 0
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, inbound_fee=ln.InboundFee(base_fee_msat=inbound_base_fee, fee_rate_ppm=target)))
                    db_channel.local_inbound_fee_rate = target
                    db_channel.save()
                    messages.success(request, 'Inbound fee rate for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
                else:
                    messages.error(request, 'LND version too low to set inbound fees, update to v0.18+')
            elif update_target == 2:
                db_channel.ar_amt_target = target
                db_channel.save()
                messages.success(request, 'Auto rebalancer target amount for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            elif update_target == 3:
                db_channel.ar_in_target = target
                db_channel.save()
                messages.success(request, 'Auto rebalancer inbound target for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 4:
                db_channel.ar_out_target = target
                db_channel.save()
                messages.success(request, 'Auto rebalancer outbound target for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 5:
                db_channel.auto_rebalance = True if db_channel.auto_rebalance == False else False
                db_channel.save()
                messages.success(request, 'Auto rebalancer status for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(db_channel.auto_rebalance))
            elif update_target == 6:
                db_channel.ar_max_cost = target
                db_channel.save()
                messages.success(request, 'Auto rebalancer max cost for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 7:
                stub = lnrouter.RouterStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChanStatus(lnr.UpdateChanStatusRequest(chan_point=channel_point, action=0)) if target == 1 else stub.UpdateChanStatus(lnr.UpdateChanStatusRequest(chan_point=channel_point, action=1))
                db_channel.local_disabled = False if target == 1 else True
                db_channel.save()
                messages.success(request, 'Toggled channel state for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') to a value of: ' + ('Enabled' if target == 1 else 'Disabled'))
                if target == 0:
                    messages.warning(request, 'Use with caution, while a channel is disabled (local fees highlighted in red) it will not route out.')
            elif update_target == 8:
                db_channel.auto_fees = True if db_channel.auto_fees == False else False
                db_channel.save()
                messages.success(request, 'Auto fees status for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(db_channel.auto_fees))
            elif update_target == 9:
                stub = lnrpc.LightningStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=target))
                db_channel.local_cltv = target
                db_channel.save()
                messages.success(request, 'CLTV for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(float(target)))
            elif update_target == 10:
                stub = lnrpc.LightningStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, min_htlc_msat_specified=True, min_htlc_msat=int(target*1000)))
                db_channel.local_min_htlc_msat = int(target*1000)
                db_channel.save()
                messages.success(request, 'Min HTLC for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(float(target)))
            elif update_target == 11:
                stub = lnrpc.LightningStub(lnd_connect())
                channel_point = point(db_channel)
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, max_htlc_msat=int(target*1000)))
                db_channel.local_max_htlc_msat = int(target*1000)
                db_channel.save()
                messages.success(request, 'Max HTLC for channel ' + str(db_channel.alias) + ' (' + str(db_channel.chan_id) + ') updated to a value of: ' + str(target))
            else:
                messages.error(request, 'Invalid target code. Please try again.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_pending(request):
    if request.method == 'POST':
        form = UpdatePending(request.POST)
        if form.is_valid():
            funding_txid = form.cleaned_data['funding_txid']
            output_index = form.cleaned_data['output_index']
            target = form.cleaned_data['target']
            update_target = int(form.cleaned_data['update_target'])
            if PendingChannels.objects.filter(funding_txid=funding_txid, output_index=output_index).exists():
                pending_channel = PendingChannels.objects.filter(funding_txid=funding_txid, output_index=output_index)[0]
            else:
                pending_channel = PendingChannels(funding_txid=funding_txid, output_index=output_index)
                pending_channel.save()
            if update_target == 0:
                pending_channel.local_base_fee = target
                pending_channel.save()
                messages.success(request, 'Base fee for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target))
            elif update_target == 1:
                pending_channel.local_fee_rate = target
                pending_channel.save()
                messages.success(request, 'Fee rate for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target))
            elif update_target == 2:
                pending_channel.ar_amt_target = target
                pending_channel.save()
                messages.success(request, 'Auto rebalancer target amount for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target))
            elif update_target == 3:
                pending_channel.ar_in_target = target
                pending_channel.save()
                messages.success(request, 'Auto rebalancer inbound target for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 4:
                pending_channel.ar_out_target = target
                pending_channel.save()
                messages.success(request, 'Auto rebalancer outbound target for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 5:
                pending_channel.auto_rebalance = True if pending_channel.auto_rebalance == False or pending_channel.auto_rebalance == None else False
                pending_channel.save()
                messages.success(request, 'Auto rebalancer status for pending pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(pending_channel.auto_rebalance))
            elif update_target == 6:
                pending_channel.ar_max_cost = target
                pending_channel.save()
                messages.success(request, 'Auto rebalancer max cost for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target) + '%')
            elif update_target == 8:
                auto_fees = int(LocalSettings.objects.filter(key='AF-Enabled')[0].value) if LocalSettings.objects.filter(key='AF-Enabled').exists() else 0
                pending_channel.auto_fees = True if pending_channel.auto_fees == False or (pending_channel.auto_fees == None and auto_fees == 0) else False
                pending_channel.save()
                messages.success(request, 'Auto fees status for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(pending_channel.auto_fees))
            elif update_target == 9:
                pending_channel.local_cltv = target
                pending_channel.save()
                messages.success(request, 'CLTV for pending channel (' + str(funding_txid) + ') updated to a value of: ' + str(target))
            else:
                messages.error(request, 'Invalid target code. Please try again.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_setting(request):
    if request.method == 'POST':
        form = UpdateSetting(request.POST)
        if form.is_valid():
            key = form.cleaned_data['key']
            value = form.cleaned_data['value']
            if key == 'ALL-oRate':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect())
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    channel_point = point(db_channel)
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(target/1000000), time_lock_delta=db_channel.local_cltv))
                    old_fee_rate = db_channel.local_fee_rate
                    db_channel.local_fee_rate = target
                    db_channel.fees_updated = datetime.now()
                    db_channel.save()
                    Autofees(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, setting=("Manual"), old_value=old_fee_rate, new_value=db_channel.local_fee_rate).save()
                messages.success(request, 'Fee rate for all open channels updated to a value of: ' + str(target))
            elif key == 'ALL-oBase':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect())
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    channel_point = point(db_channel)
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=target, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv))
                    db_channel.local_base_fee = target
                    db_channel.save()
                messages.success(request, 'Base fee for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-iRate':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect())
                version = stub.GetInfo(ln.GetInfoRequest()).version
                if float(version[:4]) >= 0.18:
                    channels = Channels.objects.filter(is_open=True)
                    for db_channel in channels:
                        channel_point = point(db_channel)
                        inbound_base_fee = db_channel.local_inbound_base_fee if db_channel.local_inbound_base_fee else 0
                        stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, inbound_fee=ln.InboundFee(base_fee_msat=inbound_base_fee, fee_rate_ppm=target)))
                        db_channel.local_inbound_fee_rate = target
                        db_channel.save()
                    messages.success(request, 'Inbound fee rate for all open channels updated to a value of: ' + str(target))
                else:
                    messages.error(request, 'LND version too low to set inbound fees, update to v0.18+')
            elif key == 'ALL-iBase':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect())
                version = stub.GetInfo(ln.GetInfoRequest()).version
                if float(version[:4]) >= 0.18:
                    channels = Channels.objects.filter(is_open=True)
                    for db_channel in channels:
                        channel_point = point(db_channel)
                        inbound_fee_rate = db_channel.local_inbound_fee_rate if db_channel.local_inbound_fee_rate else 0
                        stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, inbound_fee=ln.InboundFee(base_fee_msat=target, fee_rate_ppm=inbound_fee_rate)))
                        db_channel.local_inbound_base_fee = target
                        db_channel.save()
                    messages.success(request, 'Inbound base fee for all channels updated to a value of: ' + str(target))
                else:
                    messages.error(request, 'LND version too low to set inbound fees, update to v0.18+')
            elif key == 'ALL-CLTV':
                target = int(value)
                stub = lnrpc.LightningStub(lnd_connect())
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    channel_point = point(db_channel)
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=target))
                    db_channel.local_cltv = target
                    db_channel.save()
                messages.success(request, 'CLTV for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-minHTLC':
                target = int(float(value)*1000)
                stub = lnrpc.LightningStub(lnd_connect())
                channels = Channels.objects.filter(is_open=True)
                for db_channel in channels:
                    channel_point = point(db_channel)
                    stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(chan_point=channel_point, base_fee_msat=db_channel.local_base_fee, fee_rate=(db_channel.local_fee_rate/1000000), time_lock_delta=db_channel.local_cltv, min_htlc_msat_specified=True, min_htlc_msat=target))
                    db_channel.local_min_htlc_msat = target
                    db_channel.save()
                messages.success(request, 'Min HTLC for all channels updated to a value of: ' + str(float(value)))
            elif key == 'ALL-Amts':
                target = int(value)
                channels = Channels.objects.filter(is_open=True).update(ar_amt_target=target)
                messages.success(request, 'AR target amounts for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-MaxCost':
                target = int(value)
                channels = Channels.objects.filter(is_open=True).update(ar_max_cost=target)
                messages.success(request, 'AR max cost %s for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-oTarget':
                target = int(value)
                channels = Channels.objects.filter(is_open=True).update(ar_out_target=target)
                messages.success(request, 'AR outbound liquidity target %s for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-iTarget':
                target = int(value)
                channels = Channels.objects.filter(is_open=True).update(ar_in_target=target)
                messages.success(request, 'AR inbound liquidity target %s for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-AR':
                target = int(value)
                channels = Channels.objects.filter(is_open=True).update(auto_rebalance=target)
                messages.success(request, 'Auto-Rebalance targeting for all channels updated to a value of: ' + str(target))
            elif key == 'ALL-AF':
                target = int(value)
                channels = Channels.objects.filter(is_open=True, private=False).update(auto_fees=target)
                messages.success(request, 'Auto Fees setting for all channels updated to a value of: ' + str(target))
                try:
                    db_enabled = LocalSettings.objects.get(key='AF-UpdateHours')
                except:
                    LocalSettings(key='AF-UpdateHours', value='24').save()
                    db_enabled = LocalSettings.objects.get(key='AF-UpdateHours')
                db_enabled.value = target
                db_enabled.save()
                messages.success(request, 'Updated autofees update hours setting to: ' + str(target))
            else:
                messages.error(request, 'Invalid Request. Please try again. [' + key +']')
        else:
            messages.error(request, 'Invalid Request Form. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_closing(request):
    if request.method == 'POST':
        form = UpdateClosing(request.POST)
        if form.is_valid() and Closures.objects.filter(funding_txid=form.cleaned_data['funding_txid'], funding_index=form.cleaned_data['funding_index']).exists():
            funding_txid = form.cleaned_data['funding_txid']
            funding_index = form.cleaned_data['funding_index']
            target = int(form.cleaned_data['target'])
            db_closing = Closures.objects.filter(funding_txid=funding_txid, funding_index=funding_index)[0]
            db_closing.closing_costs = target
            db_closing.save()
            messages.success(request, 'Updated closing costs for ' + str(funding_txid) + ':' + str(funding_index) + ' updated to a value of: ' + str(target))
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def get_fees(request):
    if request.method == 'GET':
        missing_fees = Closures.objects.exclude(close_type__in=[4, 5]).exclude(open_initiator=2, resolution_count=0).filter(closing_costs=0)
        if missing_fees:
            for missing_fee in missing_fees:
                prior_closures = Closures.objects.filter(id__lt=missing_fee.id).values_list('chan_id', flat=True)
                swept = list(Resolutions.objects.filter(chan_id__in=prior_closures).values_list('sweep_txid', flat=True))
                try:
                    txid = missing_fee.closing_tx
                    closing_costs = get_tx_fees(txid) if missing_fee.open_initiator == 1 else 0
                    for resolution in Resolutions.objects.filter(chan_id=missing_fee.chan_id).exclude(resolution_type=2):
                        if resolution.sweep_txid not in swept:
                            closing_costs += get_tx_fees(resolution.sweep_txid)
                            swept.append(resolution.sweep_txid)
                    missing_fee.closing_costs = closing_costs
                    missing_fee.save()
                except Exception as error:
                    messages.error(request, f"Error getting closure fees: {txid=} {error=}")
                    return redirect(request.META.get('HTTP_REFERER'))
    return redirect(request.META.get('HTTP_REFERER'))


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def chan_policy(request):
    serializer = UpdateChanPolicy(data=request.data)
    if serializer.is_valid() and Channels.objects.filter(chan_id=serializer.validated_data['chan_id']).exists():
        chan_id = serializer.validated_data['chan_id']
        db_channel = Channels.objects.get(chan_id=chan_id)
        channel_point = point(db_channel)
        return_response = {}
        try:
            if serializer.validated_data['base_fee'] is not None or serializer.validated_data['fee_rate'] is not None or serializer.validated_data['cltv'] is not None or serializer.validated_data['min_htlc'] is not None or serializer.validated_data['max_htlc'] is not None or serializer.validated_data['inbound_base_fee'] is not None or serializer.validated_data['inbound_fee_rate'] is not None:
                base_fee_msat = serializer.validated_data['base_fee'] if serializer.validated_data['base_fee'] is not None else db_channel.local_base_fee
                fee_rate = (serializer.validated_data['fee_rate']/1000000) if serializer.validated_data['fee_rate'] is not None else (db_channel.local_fee_rate/1000000)
                inbound_base_fee_msat = serializer.validated_data['inbound_base_fee'] if serializer.validated_data['inbound_base_fee'] is not None else db_channel.local_inbound_base_fee
                inbound_fee_rate = serializer.validated_data['inbound_fee_rate'] if serializer.validated_data['inbound_fee_rate'] is not None else db_channel.local_inbound_fee_rate
                time_lock_delta = serializer.validated_data['cltv'] if serializer.validated_data['cltv'] is not None else db_channel.local_cltv
                min_htlc_msat = int(serializer.validated_data['min_htlc']*1000) if serializer.validated_data['min_htlc'] is not None else db_channel.local_min_htlc_msat
                max_htlc_msat = int(serializer.validated_data['max_htlc']*1000) if serializer.validated_data['max_htlc'] is not None else db_channel.local_max_htlc_msat
                stub = lnrpc.LightningStub(lnd_connect())
                version = stub.GetInfo(ln.GetInfoRequest()).version
                kwargs = {'chan_point':channel_point, 'base_fee_msat':base_fee_msat, 'fee_rate':fee_rate, 'time_lock_delta':time_lock_delta, 'min_htlc_msat_specified':True, 'min_htlc_msat':min_htlc_msat, 'max_htlc_msat':max_htlc_msat}
                if serializer.validated_data['inbound_base_fee'] or serializer.validated_data['inbound_fee_rate']:
                    if float(version[:4]) >= 0.18:
                        kwargs['inbound_fee'] = ln.InboundFee(base_fee_msat = inbound_base_fee_msat if inbound_base_fee_msat else 0, fee_rate_ppm = inbound_fee_rate if inbound_fee_rate else 0)
                    else:
                        return Response({'error': 'LND version too low to set inbound fees, update to v0.18+'})
                stub.UpdateChannelPolicy(ln.PolicyUpdateRequest(**kwargs))
                if serializer.validated_data['base_fee'] is not None:
                    db_channel.local_base_fee = serializer.validated_data['base_fee']
                    db_channel.save()
                    return_response['base_fee'] = serializer.validated_data['base_fee']
                if serializer.validated_data['fee_rate'] is not None:
                    old_fee_rate = db_channel.local_fee_rate
                    db_channel.local_fee_rate = serializer.validated_data['fee_rate']
                    db_channel.fees_updated = datetime.now()
                    db_channel.save()
                    return_response['fee_rate'] = serializer.validated_data['fee_rate']
                    Autofees(chan_id=db_channel.chan_id, peer_alias=db_channel.alias, setting=("Manual"), old_value=old_fee_rate, new_value=db_channel.local_fee_rate).save()
                if serializer.validated_data['inbound_base_fee'] is not None:
                    db_channel.local_inbound_base_fee = serializer.validated_data['inbound_base_fee']
                    db_channel.save()
                    return_response['inbound_base_fee'] = serializer.validated_data['inbound_base_fee']
                if serializer.validated_data['inbound_fee_rate'] is not None:
                    db_channel.local_inbound_fee_rate = serializer.validated_data['inbound_fee_rate']
                    db_channel.save()
                    return_response['inbound_fee_rate'] = serializer.validated_data['inbound_fee_rate']
                if serializer.validated_data['cltv'] is not None:
                    db_channel.local_cltv = serializer.validated_data['cltv']
                    db_channel.save()
                    return_response['cltv'] = serializer.validated_data['cltv']
                if serializer.validated_data['min_htlc'] is not None:
                    db_channel.local_min_htlc_msat = int(serializer.validated_data['min_htlc']*1000)
                    db_channel.save()
                    return_response['min_htlc'] = serializer.validated_data['min_htlc']
                if serializer.validated_data['max_htlc'] is not None:
                    db_channel.local_max_htlc_msat = int(serializer.validated_data['max_htlc']*1000)
                    db_channel.save()
                    return_response['max_htlc'] = serializer.validated_data['max_htlc']
            if serializer.validated_data['disabled'] is not None:
                stub = lnrouter.RouterStub(lnd_connect())
                stub.UpdateChanStatus(lnr.UpdateChanStatusRequest(chan_point=channel_point, action=0)) if serializer.validated_data['disabled'] == 0 else stub.UpdateChanStatus(lnr.UpdateChanStatusRequest(chan_point=channel_point, action=1))
                db_channel.local_disabled = False if serializer.validated_data['disabled'] == 0 else True
                db_channel.save()
                return_response['disabled'] = serializer.validated_data['base_fee']
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': f'Channel policy update failed! Error: {error_msg}'})
        return Response(return_response)
    else:
        return Response({'error': 'Invalid request!'})

