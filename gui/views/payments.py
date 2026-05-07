from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Sum, IntegerField, F, Value, FloatField, ExpressionWrapper, DurationField, DateTimeField
from django.db.models.functions import Round, TruncDay
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from pandas import DataFrame
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..forms import *  # noqa: F403
from ..serializers import *  # noqa: F403
from ..models import Payments, Invoices, Forwards, Channels, Onchain, TradeSales
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from secrets import token_bytes
from gui.jobs.trade import create_trade_details
from .utils import is_login_required, graph_links

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def income(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        filter_90day = datetime.now() - timedelta(days=90)
        filter_30day = datetime.now() - timedelta(days=30)
        filter_7day = datetime.now() - timedelta(days=7)
        filter_1day = datetime.now() - timedelta(days=1)
        node_info = stub.GetInfo(ln.GetInfoRequest())
        invoices = Invoices.objects.filter(state=1, is_revenue=True)
        invoices_90day = invoices.filter(settle_date__gte=filter_90day)
        invoices_30day = invoices.filter(settle_date__gte=filter_30day)
        invoices_7day = invoices.filter(settle_date__gte=filter_7day)
        invoices_1day = invoices.filter(settle_date__gte=filter_1day)
        payments = Payments.objects.filter(status=2)
        payments_90day = payments.filter(creation_date__gte=filter_90day)
        payments_30day = payments.filter(creation_date__gte=filter_30day)
        payments_7day = payments.filter(creation_date__gte=filter_7day)
        payments_1day = payments.filter(creation_date__gte=filter_1day)
        onchain_txs = Onchain.objects.all()
        onchain_txs_90day = onchain_txs.filter(time_stamp__gte=filter_90day)
        onchain_txs_30day = onchain_txs.filter(time_stamp__gte=filter_30day)
        onchain_txs_7day = onchain_txs.filter(time_stamp__gte=filter_7day)
        onchain_txs_1day = onchain_txs.filter(time_stamp__gte=filter_1day)
        closures = Closures.objects.all()
        closures_90day = Closures.objects.filter(close_height__gte=(node_info.block_height - 12960))
        closures_30day = Closures.objects.filter(close_height__gte=(node_info.block_height - 4320))
        closures_7day = Closures.objects.filter(close_height__gte=(node_info.block_height - 1008))
        closures_1day = Closures.objects.filter(close_height__gte=(node_info.block_height - 144))
        forwards = Forwards.objects.all()
        forwards_90day = forwards.filter(forward_date__gte=filter_90day)
        forwards_30day = forwards.filter(forward_date__gte=filter_30day)
        forwards_7day = forwards.filter(forward_date__gte=filter_7day)
        forwards_1day = forwards.filter(forward_date__gte=filter_1day)
        forward_count = forwards.count()
        forward_count_90day = forwards_90day.count()
        forward_count_30day = forwards_30day.count()
        forward_count_7day = forwards_7day.count()
        forward_count_1day = forwards_1day.count()
        forward_amount = 0 if forward_count == 0 else int(forwards.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        forward_amount_90day = 0 if forward_count_90day == 0 else int(forwards_90day.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        forward_amount_30day = 0 if forward_count_30day == 0 else int(forwards_30day.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        forward_amount_7day = 0 if forward_count_7day == 0 else int(forwards_7day.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        forward_amount_1day = 0 if forward_count_1day == 0 else int(forwards_1day.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        total_revenue = 0 if forward_count == 0 else int(forwards.aggregate(Sum('fee'))['fee__sum'])
        total_revenue_90day = 0 if forward_count_90day == 0 else int(forwards_90day.aggregate(Sum('fee'))['fee__sum'])
        total_revenue_30day = 0 if forward_count_30day == 0 else int(forwards_30day.aggregate(Sum('fee'))['fee__sum'])
        total_revenue_7day = 0 if forward_count_7day == 0 else int(forwards_7day.aggregate(Sum('fee'))['fee__sum'])
        total_revenue_1day = 0 if forward_count_1day == 0 else int(forwards_1day.aggregate(Sum('fee'))['fee__sum'])
        total_received = 0 if invoices.count() == 0 else int(invoices.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_received_90day = 0 if invoices_90day.count() == 0 else int(invoices_90day.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_received_30day = 0 if invoices_30day.count() == 0 else int(invoices_30day.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_received_7day = 0 if invoices_7day.count() == 0 else int(invoices_7day.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_received_1day = 0 if invoices_1day.count() == 0 else int(invoices_1day.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_revenue += total_received
        total_revenue_90day += total_received_90day
        total_revenue_30day += total_received_30day
        total_revenue_7day += total_received_7day
        total_revenue_1day += total_received_1day
        total_revenue_ppm = 0 if forward_amount == 0 else int(total_revenue/(forward_amount/1000000))
        total_revenue_ppm_90day = 0 if forward_amount_90day == 0 else int(total_revenue_90day/(forward_amount_90day/1000000))
        total_revenue_ppm_30day = 0 if forward_amount_30day == 0 else int(total_revenue_30day/(forward_amount_30day/1000000))
        total_revenue_ppm_7day = 0 if forward_amount_7day == 0 else int(total_revenue_7day/(forward_amount_7day/1000000))
        total_revenue_ppm_1day = 0 if forward_amount_1day == 0 else int(total_revenue_1day/(forward_amount_1day/1000000))
        total_sent = 0 if payments.count() == 0 else int(payments.aggregate(Sum('value'))['value__sum'])
        total_sent_90day = 0 if payments_90day.count() == 0 else int(payments_90day.aggregate(Sum('value'))['value__sum'])
        total_sent_30day = 0 if payments_30day.count() == 0 else int(payments_30day.aggregate(Sum('value'))['value__sum'])
        total_sent_7day = 0 if payments_7day.count() == 0 else int(payments_7day.aggregate(Sum('value'))['value__sum'])
        total_sent_1day = 0 if payments_1day.count() == 0 else int(payments_1day.aggregate(Sum('value'))['value__sum'])
        total_fees = 0 if payments.count() == 0 else int(payments.aggregate(Sum('fee'))['fee__sum'])
        total_fees_90day = 0 if payments_90day.count() == 0 else int(payments_90day.aggregate(Sum('fee'))['fee__sum'])
        total_fees_30day = 0 if payments_30day.count() == 0 else int(payments_30day.aggregate(Sum('fee'))['fee__sum'])
        total_fees_7day = 0 if payments_7day.count() == 0 else int(payments_7day.aggregate(Sum('fee'))['fee__sum'])
        total_fees_1day = 0 if payments_1day.count() == 0 else int(payments_1day.aggregate(Sum('fee'))['fee__sum'])
        total_fees_ppm = 0 if total_sent == 0 else int(total_fees/(total_sent/1000000))
        total_fees_ppm_90day = 0 if total_sent_90day == 0 else int(total_fees_90day/(total_sent_90day/1000000))
        total_fees_ppm_30day = 0 if total_sent_30day == 0 else int(total_fees_30day/(total_sent_30day/1000000))
        total_fees_ppm_7day = 0 if total_sent_7day == 0 else int(total_fees_7day/(total_sent_7day/1000000))
        total_fees_ppm_1day = 0 if total_sent_1day == 0 else int(total_fees_1day/(total_sent_1day/1000000))
        onchain_costs = 0 if onchain_txs.count() == 0 else onchain_txs.aggregate(Sum('fee'))['fee__sum']
        onchain_costs_90day = 0 if onchain_txs_90day.count() == 0 else onchain_txs_90day.aggregate(Sum('fee'))['fee__sum']
        onchain_costs_30day = 0 if onchain_txs_30day.count() == 0 else onchain_txs_30day.aggregate(Sum('fee'))['fee__sum']
        onchain_costs_7day = 0 if onchain_txs_7day.count() == 0 else onchain_txs_7day.aggregate(Sum('fee'))['fee__sum']
        onchain_costs_1day = 0 if onchain_txs_1day.count() == 0 else onchain_txs_1day.aggregate(Sum('fee'))['fee__sum']
        close_fees = closures.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures.exists() else 0
        close_fees_90day = closures_90day.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures_90day.exists() else 0
        close_fees_30day = closures_30day.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures_30day.exists() else 0
        close_fees_7day = closures_7day.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures_7day.exists() else 0
        close_fees_1day = closures_1day.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures_1day.exists() else 0
        onchain_costs += close_fees
        onchain_costs_90day += close_fees_90day
        onchain_costs_30day += close_fees_30day
        onchain_costs_7day += close_fees_7day
        onchain_costs_1day += close_fees_1day
        profits = int(total_revenue-total_fees-onchain_costs)
        profits_90day = int(total_revenue_90day-total_fees_90day-onchain_costs_90day)
        profits_30day = int(total_revenue_30day-total_fees_30day-onchain_costs_30day)
        profits_7day = int(total_revenue_7day-total_fees_7day-onchain_costs_7day)
        profits_1day = int(total_revenue_1day-total_fees_1day-onchain_costs_1day)
        context = {
            'node_info': node_info,
            'forward_count': forward_count,
            'forward_count_90day': forward_count_90day,
            'forward_count_30day': forward_count_30day,
            'forward_count_7day': forward_count_7day,
            'forward_count_1day': forward_count_1day,
            'forward_amount': forward_amount,
            'forward_amount_90day': forward_amount_90day,
            'forward_amount_30day': forward_amount_30day,
            'forward_amount_7day': forward_amount_7day,
            'forward_amount_1day': forward_amount_1day,
            'total_revenue': total_revenue,
            'total_revenue_90day': total_revenue_90day,
            'total_revenue_30day': total_revenue_30day,
            'total_revenue_7day': total_revenue_7day,
            'total_revenue_1day': total_revenue_1day,
            'total_fees': total_fees,
            'total_fees_90day': total_fees_90day,
            'total_fees_30day': total_fees_30day,
            'total_fees_7day': total_fees_7day,
            'total_fees_1day': total_fees_1day,
            'total_fees_ppm': total_fees_ppm,
            'total_fees_ppm_90day': total_fees_ppm_90day,
            'total_fees_ppm_30day': total_fees_ppm_30day,
            'total_fees_ppm_7day': total_fees_ppm_7day,
            'total_fees_ppm_1day': total_fees_ppm_1day,
            'onchain_costs': onchain_costs,
            'onchain_costs_90day': onchain_costs_90day,
            'onchain_costs_30day': onchain_costs_30day,
            'onchain_costs_7day': onchain_costs_7day,
            'onchain_costs_1day': onchain_costs_1day,
            'total_revenue_ppm': total_revenue_ppm,
            'total_revenue_ppm_90day': total_revenue_ppm_90day,
            'total_revenue_ppm_30day': total_revenue_ppm_30day,
            'total_revenue_ppm_7day': total_revenue_ppm_7day,
            'total_revenue_ppm_1day': total_revenue_ppm_1day,
            'profits': profits,
            'profits_90day': profits_90day,
            'profits_30day': profits_30day,
            'profits_7day': profits_7day,
            'profits_1day': profits_1day,
            'profits_ppm': 0 if forward_amount == 0  else int(profits/(forward_amount/1000000)),
            'profits_ppm_90day': 0 if forward_amount_90day == 0  else int(profits_90day/(forward_amount_90day/1000000)),
            'profits_ppm_30day': 0 if forward_amount_30day == 0  else int(profits_30day/(forward_amount_30day/1000000)),
            'profits_ppm_7day': 0 if forward_amount_7day == 0  else int(profits_7day/(forward_amount_7day/1000000)),
            'profits_ppm_1day': 0 if forward_amount_1day == 0  else int(profits_1day/(forward_amount_1day/1000000)),
            'percent_cost': 0 if total_revenue == 0 else int(((total_fees+onchain_costs)/total_revenue)*100),
            'percent_cost_90day': 0 if total_revenue_90day == 0 else int(((total_fees_90day+onchain_costs_90day)/total_revenue_90day)*100),
            'percent_cost_30day': 0 if total_revenue_30day == 0 else int(((total_fees_30day+onchain_costs_30day)/total_revenue_30day)*100),
            'percent_cost_7day': 0 if total_revenue_7day == 0 else int(((total_fees_7day+onchain_costs_7day)/total_revenue_7day)*100),
            'percent_cost_1day': 0 if total_revenue_1day == 0 else int(((total_fees_1day+onchain_costs_1day)/total_revenue_1day)*100),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
        }
        return render(request, 'income.html', context)
    else:
        return redirect('home')


@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def chart(request):
    payments = Payments.objects.filter(status=2).annotate(dt=TruncDay('creation_date')).values('dt').annotate(cost=Sum('fee', output_field=FloatField()), revenue=Value(0, output_field=FloatField()), onchain=Value(0))
    invoices = Invoices.objects.filter(state=1, is_revenue=True).annotate(dt=TruncDay('settle_date')).values('dt').annotate(cost=Value(0, output_field=FloatField()), revenue=Sum('amt_paid', output_field=FloatField()), onchain=Value(0))
    forwards = Forwards.objects.annotate(dt=TruncDay('forward_date')).values('dt').annotate(cost=Value(0, output_field=FloatField()), revenue=Sum('fee', output_field=FloatField()), onchain=Value(0))
    onchain = Onchain.objects.annotate(dt=TruncDay('time_stamp')).values('dt').annotate(cost=Value(0, output_field=FloatField()), revenue=Value(0, output_field=FloatField()), onchain=Sum('fee'))

    # Estimate blockchain timing parameters
    first_record = Onchain.objects.order_by('time_stamp').first()
    first_date = first_record.time_stamp
    first_block = first_record.block_height
    last_record = Onchain.objects.order_by('time_stamp').last()
    last_date = last_record.time_stamp
    last_block = last_record.block_height
    time_interval_per_block = timedelta(minutes=10)
    if last_block > first_block:
        time_interval_per_block =  (last_date - first_date) / (last_block - first_block)
    offset = first_date - first_block * time_interval_per_block
    # Convert close_height to datetime
    datetime_from_blocks = TruncDay(
        ExpressionWrapper(
            offset
            + ExpressionWrapper(
                F('close_height') * time_interval_per_block,
                output_field=DurationField(),
            ),
            output_field=DateTimeField()
        )
    )
    closures = Closures.objects.annotate(dt=datetime_from_blocks).values('dt').annotate(cost=Value(0, output_field=FloatField()), revenue=Value(0, output_field=FloatField()), onchain=Sum('closing_costs'))
    balance = DataFrame.from_records(payments.union(invoices, forwards, onchain, closures).values('dt', 'cost', 'revenue', 'onchain'))
    results = balance.groupby('dt').sum().reset_index().sort_values('dt')
    return Response(results.to_dict(orient='records'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def payments(request):
    if request.method == 'GET':
        context = {
            'payments': Payments.objects.exclude(status=3).annotate(ppm=Round((Sum('fee')*1000000)/Sum('value'), output_field=IntegerField())).order_by('-creation_date')[:150],
        }
        return render(request, 'payments.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def invoices(request):
    if request.method == 'GET':
        context = {
            'invoices': Invoices.objects.filter(state=1).order_by('-creation_date')[:150],
        }
        return render(request, 'invoices.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def trades(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        context = {
            'trade_link': create_trade_details(stub)
        }
        return render(request, 'trades.html', context)
    else:
        return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def forwards(request):
    if request.method == 'GET':
        return render(request, 'forwards.html')
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def keysends(request):
    if request.method == 'GET':
        context = {
            'keysends': Invoices.objects.filter(keysend_preimage__isnull=False).order_by('-settle_date')
        }
        return render(request, 'keysends.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def add_invoice_form(request):
    if request.method == 'POST':
        form = AddInvoiceForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
                response = stub.AddInvoice(ln.Invoice(value=form.cleaned_data['value']))
                messages.success(request, 'Invoice created! ' + str(response.payment_request))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Invoice creation failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def add_invoice(request):
    serializer = AddInvoiceSerializer(data=request.data)
    if serializer.is_valid() and serializer.validated_data['value'] >= 0:
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            response = stub.AddInvoice(ln.Invoice(value=serializer.validated_data['value']))
            return Response({'message': 'Invoice created!', 'data':str(response.payment_request)})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Invoice creation failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'})


def get_new_address(stub, legacy=False):
    version = stub.GetInfo(ln.GetInfoRequest()).version
    # Verify sufficient version to handle p2tr address creation
    if float(version[:4]) >= 0.15 and not legacy:
        response = stub.NewAddress(ln.NewAddressRequest(type=4))
    else:
        response = stub.NewAddress(ln.NewAddressRequest(type=0))
    return response


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def new_address(request):
    serializer = NewAddressSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            response = get_new_address(stub, legacy=serializer.validated_data['legacy'])
            return Response({'message': 'Retrieved new deposit address!', 'data':str(response.address)})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Address creation failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'}, status=400)


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def consolidate_utxos(request):
    serializer = ConsolidateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            self_addr = get_new_address(stub).address
            txid = stub.SendCoins(ln.SendCoinsRequest(addr=self_addr, send_all=True, sat_per_vbyte=serializer.validated_data['sat_per_vbyte'])).txid
            return Response({'message': f'Successfully consolidated UXTOs: {txid}', 'txid':txid})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Failed to consolidate utxos! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'}, status=400)


@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def api_balances(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        balances = stub.WalletBalance(ln.WalletBalanceRequest())
        pending_channels = stub.PendingChannels(ln.PendingChannelsRequest())
        limbo_balance = pending_channels.total_limbo_balance
        pending_open_balance = 0
        if pending_channels.pending_open_channels:
            target_resp = pending_channels.pending_open_channels
            for i in range(0,len(target_resp)):
                pending_open_balance += target_resp[i].channel.local_balance
        channels = Channels.objects.filter(is_open=1)
        offchain_balance = channels.aggregate(Sum('local_balance'))['local_balance__sum'] + channels.aggregate(Sum('pending_outbound'))['pending_outbound__sum'] + pending_open_balance + limbo_balance
        target = {'total_balance':(balances.total_balance + offchain_balance),'offchain_balance':offchain_balance,'onchain_balance':balances.total_balance, 'confirmed_balance':balances.confirmed_balance, 'unconfirmed_balance':balances.unconfirmed_balance}
        return Response({'message': 'success', 'data':target})
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        return Response({'error': 'Failed to get wallet balances! Error: ' + error_msg})


@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def api_income(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        try:
            days = int(request.GET.urlencode()[1:])
        except:
            days = None
        day_filter = datetime.now() - timedelta(days=days) if days else None
        node_info = stub.GetInfo(ln.GetInfoRequest())
        payments = Payments.objects.filter(status=2).filter(creation_date__gte=day_filter) if day_filter else Payments.objects.filter(status=2)
        onchain_txs = Onchain.objects.filter(time_stamp__gte=day_filter) if day_filter else Onchain.objects.all()
        closures = Closures.objects.filter(close_height__gte=(node_info.block_height - (days*144))) if days else Closures.objects.all()
        forwards = Forwards.objects.filter(forward_date__gte=day_filter) if day_filter else Forwards.objects.all()
        forward_count = forwards.count()
        forward_amount = 0 if forward_count == 0 else int(forwards.aggregate(Sum('amt_out_msat'))['amt_out_msat__sum']/1000)
        total_revenue = 0 if forward_count == 0 else int(forwards.aggregate(Sum('fee'))['fee__sum'])
        invoices = Invoices.objects.filter(state=1, is_revenue=True).filter(settle_date__gte=day_filter) if day_filter else Invoices.objects.filter(state=1, is_revenue=True)
        total_received = 0 if invoices.count() == 0 else int(invoices.aggregate(Sum('amt_paid'))['amt_paid__sum'])
        total_revenue += total_received
        total_revenue_ppm = 0 if forward_amount == 0 else int(total_revenue/(forward_amount/1000000))
        total_sent = 0 if payments.count() == 0 else int(payments.aggregate(Sum('value'))['value__sum'])
        total_fees = 0 if payments.count() == 0 else int(payments.aggregate(Sum('fee'))['fee__sum'])
        total_fees_ppm = 0 if total_sent == 0 else int(total_fees/(total_sent/1000000))
        onchain_costs = 0 if onchain_txs.count() == 0 else onchain_txs.aggregate(Sum('fee'))['fee__sum']
        close_fees = closures.aggregate(Sum('closing_costs'))['closing_costs__sum'] if closures.exists() else 0
        onchain_costs += close_fees
        profits = int(total_revenue-total_fees-onchain_costs)
        target = {
            'forward_count': forward_count,
            'forward_amount': forward_amount,
            'total_revenue': total_revenue,
            'total_revenue_ppm': total_revenue_ppm,
            'total_fees': total_fees,
            'total_fees_ppm': total_fees_ppm,
            'onchain_costs': onchain_costs,
            'profits': profits,
            'profits_ppm': 0 if forward_amount == 0  else int(profits/(forward_amount/1000000)),
            'percent_cost': 0 if total_revenue == 0 else int(((total_fees+onchain_costs)/total_revenue)*100),
        }
        return Response({'message': 'success', 'data':target})
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        return Response({'error': 'Failed to get revenue stats! Error: ' + error_msg})


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def create_trade(request):
    serializer = CreateTradeSerializer(data=request.data)
    if serializer.is_valid():
        description = serializer.validated_data['description']
        price = serializer.validated_data['price']
        sale_type = serializer.validated_data['type']
        secret = serializer.validated_data['secret']
        expiry = serializer.validated_data['expiry']
        sale_limit = serializer.validated_data['sale_limit']
        trade_id = token_bytes(32).hex()
        try:
            new_trade = TradeSales(id=trade_id, description=description, price=price, secret=secret, expiry=expiry, sale_type=sale_type, sale_limit=sale_limit)
            new_trade.save()
            return Response({'message': f'Created trade: {description}', 'id': new_trade.id, 'description': new_trade.description, 'price': new_trade.price, 'expiry': new_trade.expiry, 'sale_type': new_trade.sale_type, 'secret': new_trade.secret, 'sale_count': new_trade.sale_count, 'sale_limit': new_trade.sale_limit})
        except Exception as e:
            error = str(e)
            return Response({'error': f'Error creating trade: {error}'})
    else:
        return Response({'error': serializer.error_messages})


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def export_accounting(request):
    """bos accounting – export all financial events as a CSV download."""
    import csv
    from django.http import StreamingHttpResponse

    class EchoWriter:
        def write(self, value):
            return value

    def rows():
        yield ['date', 'type', 'amount_sats', 'fee_sats', 'notes']
        for f in Forwards.objects.all().order_by('forward_date'):
            yield [
                f.forward_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'forwarding_revenue',
                int(f.amt_out_msat / 1000),
                int(f.fee),
                f'in:{f.chan_id_in} out:{f.chan_id_out}',
            ]
        for p in Payments.objects.filter(status=2).order_by('creation_date'):
            row_type = 'rebalance_cost' if p.rebal_chan else 'payment_sent'
            yield [
                p.creation_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                row_type,
                int(p.value),
                int(p.fee),
                p.payment_hash,
            ]
        for inv in Invoices.objects.filter(state=1, is_revenue=True).order_by('settle_date'):
            yield [
                inv.settle_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'invoice_received',
                int(inv.amt_paid),
                0,
                inv.r_hash,
            ]
        for tx in Onchain.objects.all().order_by('-block_height'):
            yield [
                tx.time_stamp.strftime('%Y-%m-%dT%H:%M:%SZ') if tx.time_stamp else '',
                'onchain_fee',
                int(tx.amount),
                int(tx.fee),
                tx.tx_hash,
            ]

    pseudo_buffer = EchoWriter()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse(
        (writer.writerow(row) for row in rows()),
        content_type='text/csv',
    )
    response['Content-Disposition'] = 'attachment; filename="lndg_accounting.csv"'
    return response



@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def clean_failed_payments(request):
    """bos clean-failed-payments – delete in-flight and failed payment records."""
    try:
        deleted, _ = Payments.objects.filter(status__in=[1, 3]).delete()
        return Response({'message': f'Removed {deleted} failed/in-flight payment record(s).'})
    except Exception:
        return Response({'error': 'Failed to clean payments. Check server logs.'}, status=500)



@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def decode_invoice(request):
    """Decode a BOLT11 payment request without paying it (used by pay-invoice modal)."""
    serializer = DecodeInvoiceSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': 'Invalid request!'}, status=400)
    payment_request = serializer.validated_data['payment_request']
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        resp = stub.DecodePayReq(ln.PayReqString(pay_req=payment_request))
        return Response({
            'message': 'Decoded successfully',
            'data': {
                'destination': resp.destination,
                'payment_hash': resp.payment_hash,
                'num_satoshis': resp.num_satoshis,
                'timestamp': resp.timestamp,
                'expiry': resp.expiry,
                'description': resp.description,
                'cltv_expiry': resp.cltv_expiry,
            }
        })
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_end = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_end]
        return Response({'error': f'Decode failed: {error_msg}'})



@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def pay_invoice(request):
    """bos pay – pay a BOLT11 payment request via LND."""
    serializer = PayInvoiceSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': 'Invalid request!'}, status=400)
    payment_request = serializer.validated_data['payment_request']
    max_fee_sats = serializer.validated_data['max_fee_sats']
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        resp = stub.SendPaymentSync(ln.SendRequest(
            payment_request=payment_request,
            fee_limit=ln.FeeLimit(fixed=max_fee_sats),
        ))
        if resp.payment_error:
            return Response({'error': f'Payment failed: {resp.payment_error}'})
        return Response({
            'message': 'Payment sent!',
            'data': {
                'payment_hash': resp.payment_hash.hex(),
                'payment_preimage': resp.payment_preimage.hex(),
            }
        })
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_end = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_end]
        return Response({'error': f'Payment failed: {error_msg}'})


