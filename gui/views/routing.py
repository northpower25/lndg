from django.shortcuts import render, redirect
from django.db.models import Sum, IntegerField, Count, Max
from django.db.models.functions import Round
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..serializers import BroadcastTXSerializer, BumpFeeSerializer, ProbeRouteSerializer, SignMessageSerializer
from ..models import Channels, FailedHTLCs, Forwards, Invoices, PaymentHops, Payments, Peers, PendingHTLCs
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import router_pb2 as lnr
from gui.lnd_deps import router_pb2_grpc as lnrouter
from gui.lnd_deps import walletkit_pb2 as walletrpc
from gui.lnd_deps import walletkit_pb2_grpc as walletstub
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from .utils import graph_links, grpc_error_message, is_login_required, pending_channel_details

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def route(request):
    if request.method == 'GET':
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            block_height = stub.GetInfo(ln.GetInfoRequest()).block_height
            payment_hash = request.GET.urlencode()[1:]
            route = PaymentHops.objects.filter(payment_hash=payment_hash).annotate(ppm=Round((Sum('fee')/Sum('amt'))*1000000, output_field=IntegerField())) if PaymentHops.objects.filter(payment_hash=payment_hash).exists() else None
            total_cost = round(route.aggregate(Sum('fee'))['fee__sum'],3) if route is not None else 0
            total_ppm = int(total_cost*1000000/route.filter(step=1).aggregate(Sum('amt'))['amt__sum']) if route is not None else 0
            context = {
                'payment_hash': payment_hash,
                'total_cost': total_cost,
                'total_ppm': total_ppm,
                'route': route,
                'invoices': Invoices.objects.filter(r_hash=payment_hash),
                'incoming_htlcs': PendingHTLCs.objects.filter(incoming=True, hash_lock=payment_hash).annotate(blocks_til_expiration=Sum('expiration_height')-block_height, hours_til_expiration=((Sum('expiration_height')-block_height)*10)/60).order_by('hash_lock'),
                'outgoing_htlcs': PendingHTLCs.objects.filter(incoming=False, hash_lock=payment_hash).annotate(blocks_til_expiration=Sum('expiration_height')-block_height, hours_til_expiration=((Sum('expiration_height')-block_height)*10)/60).order_by('hash_lock')
            }
            return render(request, 'route.html', context)
        except Exception as e:
            error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def routes(request):
    if request.method == 'GET':
        try:
            pubkey = request.GET.urlencode()[1:]
            context = {
                'payment_hash': pubkey,
                'route': PaymentHops.objects.filter(payment_hash__in=PaymentHops.objects.filter(node_pubkey=pubkey).order_by('-id').values_list('payment_hash')[:69]).annotate(ppm=Round((Sum('fee')/Sum('amt'))*1000000, output_field=IntegerField()))
            }
            return render(request, 'route.html', context)
        except Exception as e:
            error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def pending_htlcs(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        block_height = stub.GetInfo(ln.GetInfoRequest()).block_height
        context = {
            'incoming_htlcs': PendingHTLCs.objects.filter(incoming=True).annotate(blocks_til_expiration=Sum('expiration_height')-block_height, hours_til_expiration=((Sum('expiration_height')-block_height)*10)/60).order_by('expiration_height'),
            'outgoing_htlcs': PendingHTLCs.objects.filter(incoming=False).annotate(blocks_til_expiration=Sum('expiration_height')-block_height, hours_til_expiration=((Sum('expiration_height')-block_height)*10)/60).order_by('expiration_height')
        }
        return render(request, 'pending_htlcs.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def failed_htlcs(request):
    if request.method == 'GET':
        try:
            filter_7day = datetime.now() - timedelta(days=7)
            agg_failed_htlcs = FailedHTLCs.objects.filter(timestamp__gte=filter_7day, wire_failure=99).values('chan_id_in', 'chan_id_out').annotate(count=Count('id'), volume=Sum('amount'), chan_in_alias=Max('chan_in_alias'), chan_out_alias=Max('chan_out_alias')).order_by('-count')[:21]
            context = {
                'agg_failed_htlcs': agg_failed_htlcs
            }
            return render(request, 'failed_htlcs.html', context)
        except Exception as e:
            error = grpc_error_message(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')


@api_view(['POST'])
@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def sign_message(request):
    serializer = SignMessageSerializer(data=request.data)
    if serializer.is_valid():
        message = serializer.validated_data['message']
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            response = stub.SignMessage(ln.SignMessageRequest(msg=message.encode('utf-8'), single_hash=False))
            return Response({'message': 'Success', 'data': str(response.signature)})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': f'Sign message failed! Error: {error_msg}'})
    else:
        return Response({'error': 'Invalid request!'})


@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def pending_channels(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        response = stub.PendingChannels(ln.PendingChannelsRequest())
        if response.pending_open_channels or response.pending_closing_channels or response.pending_force_closing_channels or response.waiting_close_channels or response.total_limbo_balance:
            target = {}
            if response.pending_open_channels:
                target_resp = response.pending_open_channels
                peers = Peers.objects.all()
                pending_open_channels = []
                for i in range(0,len(target_resp)):
                    pending_item = {'alias':peers.filter(pubkey=target_resp[i].channel.remote_node_pub)[0].alias if peers.filter(pubkey=target_resp[i].channel.remote_node_pub).exists() else None,
                    'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
                    'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'commit_fee':target_resp[i].commit_fee,'commit_weight':target_resp[i].commit_weight,'fee_per_kw':target_resp[i].fee_per_kw}
                    pending_open_channels.append(pending_item)
                target.update({'pending_open': pending_open_channels})
            if response.pending_closing_channels:
                target_resp = response.pending_closing_channels
                pending_closing_channels = []
                for i in range(0,len(target_resp)):
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
                    'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'limbo_balance':target_resp[i].limbo_balance}
                    pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
                    pending_closing_channels.append(pending_item)
                target.update({'pending_closing':pending_closing_channels})
            if response.pending_force_closing_channels:
                target_resp = response.pending_force_closing_channels
                pending_force_closing_channels = []
                for i in range(0,len(target_resp)):
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'initiator':target_resp[i].channel.initiator,
                    'commitment_type':target_resp[i].channel.commitment_type,'closing_txid':target_resp[i].closing_txid,'limbo_balance':target_resp[i].limbo_balance,'maturity_height':target_resp[i].maturity_height,'blocks_til_maturity':target_resp[i].blocks_til_maturity,'maturity_datetime':(datetime.now()+timedelta(minutes=(10*target_resp[i].blocks_til_maturity)))}
                    pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
                    pending_force_closing_channels.append(pending_item)
                target.update({'pending_force_closing':pending_force_closing_channels})
            if response.waiting_close_channels:
                target_resp = response.waiting_close_channels
                waiting_close_channels = []
                for i in range(0,len(target_resp)):
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
                    'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type,'limbo_balance':target_resp[i].limbo_balance}
                    pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
                    waiting_close_channels.append(pending_item)
                target.update({'waiting_close':waiting_close_channels})
            if response.total_limbo_balance:
                total_limbo_balance = {'total_limbo_balance':response.total_limbo_balance}
                target.update(total_limbo_balance)
            return Response({'message': 'success', 'data':target})
        else:
            return Response({'message': 'success', 'data':None})
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        return Response({'error': 'Failed to get pending channels! Error: ' + error_msg})


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def bump_fee(request):
    serializer = BumpFeeSerializer(data=request.data)
    if serializer.is_valid():
        txid = serializer.validated_data['txid']
        index = serializer.validated_data['index']
        target_fee = serializer.validated_data['target_fee']
        force = serializer.validated_data['force']
        try:
            target_outpoint = ln.OutPoint()
            target_outpoint.txid_str = txid
            target_outpoint.output_index = index
            stub = walletstub.WalletKitStub(lnd_connect())
            stub.BumpFee(walletrpc.BumpFeeRequest(outpoint=target_outpoint, sat_per_vbyte=target_fee, force=force))
            return Response({'message': f'Fee bumped to {target_fee} sats/vbyte for outpoint: {txid}:{index}'})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': f'Fee bump failed! Error: {error_msg}'})
    else:
        return Response({'error': 'Invalid request!'})


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def broadcast_tx(request):
    serializer = BroadcastTXSerializer(data=request.data)
    if serializer.is_valid():
        raw_tx = serializer.validated_data['raw_tx']
        try:
            stub = walletstub.WalletKitStub(lnd_connect())
            response = stub.PublishTransaction(walletrpc.Transaction(tx_hex=bytes.fromhex(raw_tx)))
            if response.publish_error == '':
                return Response({'message': 'Successfully broadcast tx!'})
            else:
                return Response({'error': f'Error while broadcasting TX: {response.publish_error}'})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': f'TX broadcast failed! Error: {error_msg}'})
    else:
        return Response({'error': 'Invalid request!'})


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def sankey(request):
    return render(request, 'sankey.html', {
        'graph_links': graph_links(),
        'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
    })


@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def sankey_data(request):
    mode = request.GET.get('mode', 'routing')
    days = request.GET.get('days', '30')

    if days == 'all':
        filter_date = None
    else:
        try:
            filter_date = datetime.now() - timedelta(days=int(days))
        except (ValueError, TypeError):
            filter_date = datetime.now() - timedelta(days=30)

    links = []
    nodes_set = set()

    if mode == 'routing':
        qs = Forwards.objects
        if filter_date:
            qs = qs.filter(forward_date__gte=filter_date)
        rows = qs.values('chan_in_alias', 'chan_out_alias').annotate(amount=Sum('amt_out_msat')).filter(amount__gt=0)
        flow_dict = defaultdict(int)
        for row in rows:
            src = row['chan_in_alias'] or 'Unknown'
            tgt = row['chan_out_alias'] or 'Unknown'
            amt = int(row['amount'] // 1000)
            if src != tgt and amt > 0:
                flow_dict[(src, tgt)] += amt
        for (src, tgt), amt in flow_dict.items():
            links.append({'source': src, 'target': tgt, 'value': amt})
            nodes_set.add(src)
            nodes_set.add(tgt)
    elif mode == 'rebalancing':
        qs = Payments.objects.filter(status=2, rebal_chan__isnull=False)
        if filter_date:
            qs = qs.filter(creation_date__gte=filter_date)
        chan_id_to_alias = {str(c.chan_id): c.alias for c in Channels.objects.filter(is_open=True)}

        def resolve_alias(chan_id):
            chan_id_str = str(chan_id) if chan_id is not None else None
            return chan_id_to_alias.get(chan_id_str, chan_id_str) if chan_id_str else 'Unknown'

        flow_dict = defaultdict(int)
        # Non-MPP payments: attribute directly via chan_out_alias
        for p in qs.exclude(chan_out='MPP').values('chan_out_alias', 'rebal_chan', 'value'):
            src = p['chan_out_alias'] or 'Unknown'
            tgt = resolve_alias(p['rebal_chan'])
            amt = int(p['value'] or 0)
            if src != tgt and amt > 0:
                flow_dict[(src, tgt)] += amt
        # MPP payments: use first-hop PaymentHops records to attribute volume to the actual outgoing channels
        mpp_payments = list(qs.filter(chan_out='MPP').values('payment_hash', 'rebal_chan'))
        if mpp_payments:
            mpp_hash_to_rebal = {p['payment_hash']: p['rebal_chan'] for p in mpp_payments}
            first_hops = PaymentHops.objects.filter(
                payment_hash_id__in=mpp_hash_to_rebal.keys(),
                step=1
            ).values('payment_hash_id', 'alias', 'amt')
            for hop in first_hops:
                rebal_chan_id = mpp_hash_to_rebal.get(hop['payment_hash_id'])
                if rebal_chan_id is None:
                    continue
                tgt = resolve_alias(rebal_chan_id)
                src = hop['alias'] or 'Unknown'
                # Strip any appended status annotation (e.g. "[ 2-1-0-0 ]") from the alias
                if '[' in src:
                    src = src[:src.index('[')].strip()
                amt = int(hop['amt'] or 0)
                if src and src != tgt and amt > 0:
                    flow_dict[(src, tgt)] += amt
        for (src, tgt), amt in flow_dict.items():
            links.append({'source': src, 'target': tgt, 'value': amt})
            nodes_set.add(src)
            nodes_set.add(tgt)

    nodes = [{'id': n, 'name': n} for n in sorted(nodes_set)]
    return Response({'nodes': nodes, 'links': links})

# ---------------------------------------------------------------------------
# BOS-equivalent features
# ---------------------------------------------------------------------------


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def probe_route(request):
    """bos probe – estimate the routing fee for a payment to a destination."""
    serializer = ProbeRouteSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': 'Invalid request!'}, status=400)
    dest_pubkey = serializer.validated_data['dest_pubkey']
    amount_sats = serializer.validated_data['amount_sats']
    try:
        router_stub = lnrouter.RouterStub(lnd_connect())
        resp = router_stub.EstimateRouteFee(lnr.RouteFeeRequest(
            dest=bytes.fromhex(dest_pubkey),
            amt_sat=amount_sats,
        ))
        return Response({
            'message': 'Route fee estimated',
            'data': {
                'routing_fee_msat': resp.routing_fee_msat,
                'routing_fee_sats': resp.routing_fee_msat / 1000,
                'time_lock_delay': resp.time_lock_delay,
            }
        })
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_end = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_end]
        return Response({'error': f'Probe failed: {error_msg}'})
