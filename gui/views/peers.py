from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..forms import AddTowerForm, BatchOpenForm, CloseChannelForm, ConnectPeerForm, DeleteTowerForm, OpenChannelForm, RemoveTowerForm
from ..serializers import CloseChannelSerializer, ConnectPeerSerializer, DisconnectPeerSerializer, OpenChannelSerializer, UpdateAliasSerializer
from ..models import Channels, Onchain, Peers
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import wtclient_pb2 as wtrpc
from gui.lnd_deps import wtclient_pb2_grpc as wtstub
from gui.lnd_deps import walletkit_pb2 as walletrpc
from gui.lnd_deps import walletkit_pb2_grpc as walletstub
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from .utils import graph_links, grpc_error_message, is_login_required, network_links

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def peers(request):
    if request.method == 'GET':
        peers = Peers.objects.filter(connected=True)
        context = {
            'peers': peers,
            'num_peers': len(peers),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links()
        }
        return render(request, 'peers.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def balances(request):
    if request.method == 'GET':
        stub = walletstub.WalletKitStub(lnd_connect())
        pending_sweeps = stub.PendingSweeps(walletrpc.PendingSweepsRequest()).pending_sweeps
        sweeps = []
        for pending_sweep in pending_sweeps:
            sweep = {}
            sweep['txid_str'] = pending_sweep.outpoint.txid_bytes[::-1].hex()
            sweep['txid_index'] = pending_sweep.outpoint.output_index
            sweep['amount_sat'] = pending_sweep.amount_sat
            sweep['witness_type'] = pending_sweep.witness_type
            sweep['requested_sat_per_vbyte'] = pending_sweep.requested_sat_per_vbyte
            sweep['sat_per_vbyte'] = pending_sweep.sat_per_vbyte
            sweep['requested_conf_target'] = pending_sweep.requested_conf_target
            sweep['broadcast_attempts'] = pending_sweep.broadcast_attempts
            sweep['next_broadcast_height'] = pending_sweep.next_broadcast_height
            sweep['force'] = pending_sweep.force
            sweeps.append(sweep)
        context = {
            'utxos': stub.ListUnspent(walletrpc.ListUnspentRequest(min_confs=0, max_confs=9999999)).utxos,
            'transactions': list(Onchain.objects.filter(block_height=0)) + list(Onchain.objects.exclude(block_height=0).order_by('-block_height')),
            'pending_sweeps': sweeps,
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'network_links': network_links()
        }
        return render(request, 'balances.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def towers(request):
    if request.method == 'GET':
        try:
            stub = wtstub.WatchtowerClientStub(lnd_connect())
            towers = stub.ListTowers(wtrpc.ListTowersRequest(include_sessions=False)).towers
            active_towers = []
            inactive_towers = []
            for item in towers:
                for address in item.addresses:
                    tower = {}
                    tower['pubkey'] = item.pubkey.hex()
                    tower['address'] = address
                    tower['active'] = item.active_session_candidate
                    tower['num_sessions'] = item.num_sessions
                    active_towers.append(tower) if tower['active'] else inactive_towers.append(tower)
            stats = stub.Stats(wtrpc.StatsRequest())
            context = {
                'active_towers': active_towers,
                'inactive_towers': inactive_towers,
                'stats': stats
            }
            return render(request, 'towers.html', context)
        except Exception as e:
            error = grpc_error_message(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def add_tower_form(request):
    if request.method == 'POST':
        form = AddTowerForm(request.POST)
        if form.is_valid():
            try:
                stub = wtstub.WatchtowerClientStub(lnd_connect())
                tower = form.cleaned_data['tower']
                if tower.count('@') == 1 and len(tower.split('@')[0]) == 66:
                    peer_pubkey, host = tower.split('@')
                else:
                    raise Exception('Invalid tower connection string.')
                response = stub.AddTower(wtrpc.AddTowerRequest(pubkey=bytes.fromhex(peer_pubkey), address=host))
                messages.success(request, 'Tower addition successful!' + str(response))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Add tower request failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def delete_tower_form(request):
    if request.method == 'POST':
        form = DeleteTowerForm(request.POST)
        if form.is_valid():
            try:
                stub = wtstub.WatchtowerClientStub(lnd_connect())
                pubkey = bytes.fromhex(form.cleaned_data['pubkey'])
                address = form.cleaned_data['address']
                response = stub.RemoveTower(wtrpc.RemoveTowerRequest(pubkey=pubkey, address=address))
                messages.success(request, 'Tower deletion successful!' + str(response))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Delete tower request failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def remove_tower_form(request):
    if request.method == 'POST':
        form = RemoveTowerForm(request.POST)
        if form.is_valid():
            try:
                stub = wtstub.WatchtowerClientStub(lnd_connect())
                pubkey = bytes.fromhex(form.cleaned_data['pubkey'])
                response = stub.RemoveTower(wtrpc.RemoveTowerRequest(pubkey=pubkey))
                messages.success(request, 'Tower removal successful!' + str(response))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Remove tower request failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def batch(request):
    if request.method == 'GET':
        stub = lnrpc.LightningStub(lnd_connect())
        context = {
            'iterator': range(1,11),
            'balances': stub.WalletBalance(ln.WalletBalanceRequest())
        }
        return render(request, 'batch.html', context)
    else:
        return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def addresses(request):
    if request.method == 'GET':
        try:
            stub = walletstub.WalletKitStub(lnd_connect())
            address_data = stub.ListAddresses(walletrpc.ListAddressesRequest())
            context = {
                'address_data': address_data,
                'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
                'network_links': network_links()
            }
            return render(request, 'addresses.html', context)
        except Exception as e:
            error = grpc_error_message(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect(request.META.get('HTTP_REFERER'))


def open_peer(peer_pubkey, stub):
    if Peers.objects.filter(pubkey=peer_pubkey, connected=True).exists():
        return True
    else:
        try:
            node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
            host = node.addresses[0].addr
            ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
            stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
            return True
        except Exception:
            return False


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def batch_open(request):
    if request.method == 'POST':
        form = BatchOpenForm(request.POST)
        if form.is_valid():
            count = 0
            fail = False
            open_list = []
            stub = lnrpc.LightningStub(lnd_connect())
            if form.cleaned_data['pubkey1'] and form.cleaned_data['amt1'] and len(form.cleaned_data['pubkey1']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey1']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':peer_pubkey, 'amt':form.cleaned_data['amt1']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 1!')
            if form.cleaned_data['pubkey2'] and form.cleaned_data['amt2'] and len(form.cleaned_data['pubkey2']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey2']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey2'], 'amt':form.cleaned_data['amt2']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 2!')
            if form.cleaned_data['pubkey3'] and form.cleaned_data['amt3'] and len(form.cleaned_data['pubkey3']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey3']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey3'], 'amt':form.cleaned_data['amt3']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 3!')
            if form.cleaned_data['pubkey4'] and form.cleaned_data['amt4'] and len(form.cleaned_data['pubkey4']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey4']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey4'], 'amt':form.cleaned_data['amt4']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 4!')
            if form.cleaned_data['pubkey5'] and form.cleaned_data['amt5'] and len(form.cleaned_data['pubkey5']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey5']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey5'], 'amt':form.cleaned_data['amt5']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 5!')
            if form.cleaned_data['pubkey6'] and form.cleaned_data['amt6'] and len(form.cleaned_data['pubkey6']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey6']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey6'], 'amt':form.cleaned_data['amt6']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 6!')
            if form.cleaned_data['pubkey7'] and form.cleaned_data['amt7'] and len(form.cleaned_data['pubkey7']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey7']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey7'], 'amt':form.cleaned_data['amt7']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 7!')
            if form.cleaned_data['pubkey8'] and form.cleaned_data['amt8'] and len(form.cleaned_data['pubkey8']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey8']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey8'], 'amt':form.cleaned_data['amt8']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 8!')
            if form.cleaned_data['pubkey9'] and form.cleaned_data['amt9'] and len(form.cleaned_data['pubkey9']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey9']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey9'], 'amt':form.cleaned_data['amt9']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 9!')
            if form.cleaned_data['pubkey10'] and form.cleaned_data['amt10'] and len(form.cleaned_data['pubkey10']) == 66:
                count += 1
                peer_pubkey = form.cleaned_data['pubkey10']
                connected = open_peer(peer_pubkey, stub)
                if connected:
                    open_list.append({'pubkey':form.cleaned_data['pubkey10'], 'amt':form.cleaned_data['amt10']})
                else:
                    fail = True
                    messages.error(request, 'Unable to connect with peer 10!')
            if fail:
                return redirect('batch')
            if len (open_list) > 0:
                try:
                    channels = []
                    for open in open_list:
                        channel_open = ln.BatchOpenChannel()
                        channel_open.node_pubkey = bytes.fromhex(open['pubkey'])
                        channel_open.local_funding_amount = open['amt']
                        channels.append(channel_open)
                    response = stub.BatchOpenChannel(ln.BatchOpenChannelRequest(channels=channels, sat_per_vbyte=form.cleaned_data['fee_rate']))
                    print(response)
                    messages.success(request, 'Batch opened channels!')
                except Exception as e:
                    error = str(e)
                    details_index = error.find('details =') + 11
                    debug_error_index = error.find('debug_error_string =') - 3
                    error_msg = error[details_index:debug_error_index]
                    messages.error(request, 'Batch open failed! Error: ' + error_msg)
            else:
                messages.error(request, 'No channels specified!')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('batch')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def peerevents(request):
    if request.method == 'GET':
        try:
            return render(request, 'peerevents.html')
        except Exception as e:
            error = grpc_error_message(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def open_channel_form(request):
    if request.method == 'POST':
        form = OpenChannelForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
                peer_pubkey = form.cleaned_data['peer_pubkey']
                connected = False
                if Peers.objects.filter(pubkey=peer_pubkey, connected=True).exists():
                    connected = True
                else:
                    try:
                        node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
                        host = node.addresses[0].addr
                        ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
                        response = stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
                        connected = True
                    except Exception as e:
                        error = str(e)
                        details_index = error.find('details =') + 11
                        debug_error_index = error.find('debug_error_string =') - 3
                        error_msg = error[details_index:debug_error_index]
                        messages.error(request, 'Error connecting to new peer: ' + error_msg)
                if connected:
                    for response in stub.OpenChannel(ln.OpenChannelRequest(node_pubkey=bytes.fromhex(peer_pubkey), local_funding_amount=form.cleaned_data['local_amt'], sat_per_byte=form.cleaned_data['sat_per_byte'])):
                        messages.success(request, 'Channel created! Funding TXID: ' + str(response.chan_pending.txid[::-1].hex()) + ':' + str(response.chan_pending.output_index))
                        break
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Channel creation failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def close_channel_form(request):
    if request.method == 'POST':
        form = CloseChannelForm(request.POST)
        if form.is_valid():
            try:
                chan_id = form.cleaned_data['chan_id']
                if chan_id.count('x') == 2 and len(chan_id) >= 5:
                    target_channel = Channels.objects.filter(short_chan_id=chan_id)
                else:
                    target_channel = Channels.objects.filter(chan_id=chan_id)
                if target_channel.exists():
                    target_channel = target_channel.get()
                    funding_txid = target_channel.funding_txid
                    output_index = target_channel.output_index
                    force_close = form.cleaned_data['force']
                    target_fee = form.cleaned_data['target_fee']
                    if not force_close and not target_fee:
                        messages.error(request, 'Expected a fee rate for graceful closure. Please try again.')
                    channel_point = ln.ChannelPoint()
                    channel_point.funding_txid_bytes = bytes.fromhex(funding_txid)
                    channel_point.funding_txid_str = funding_txid
                    channel_point.output_index = output_index
                    stub = lnrpc.LightningStub(lnd_connect())
                    if force_close:
                        for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, force=True)):
                            messages.success(request, 'Channel force closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index))
                            break
                    else:
                        for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, sat_per_byte=target_fee)):
                            messages.success(request, 'Channel gracefully closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index))
                            break
                else:
                    messages.error(request, 'Channel ID is not valid. Please try again.')
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Channel close failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def connect_peer_form(request):
    if request.method == 'POST':
        form = ConnectPeerForm(request.POST)
        if form.is_valid():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
                peer_id = form.cleaned_data['peer_id']
                if peer_id.count('@') == 0 and len(peer_id) == 66:
                    peer_pubkey = peer_id
                    node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
                    host = node.addresses[0].addr
                elif peer_id.count('@') == 1 and len(peer_id.split('@')[0]) == 66:
                    peer_pubkey, host = peer_id.split('@')
                else:
                    raise Exception('Invalid peer pubkey or connection string.')
                ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
                response = stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
                messages.success(request, 'Connection successful!' + str(response))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Connection request failed! Error: ' + error_msg)
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def connect_peer(request):
    serializer = ConnectPeerSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            peer_id = serializer.validated_data['peer_id']
            if peer_id.count('@') == 0 and len(peer_id) == 66:
                peer_pubkey = peer_id
                node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
                host = node.addresses[0].addr
            elif peer_id.count('@') == 1 and len(peer_id.split('@')[0]) == 66:
                peer_pubkey, host = peer_id.split('@')
            else:
                return Response({'error': 'Invalid peer pubkey or connection string.'})
            ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
            stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
            return Response({'message': 'Connection successful!'})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Connection request failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'})


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def disconnect_peer(request):
    serializer = DisconnectPeerSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            peer_id = serializer.validated_data['peer_id']
            if len(peer_id) == 66:
                peer_pubkey = peer_id
            else:
                return Response({'error': 'Invalid peer pubkey.'})
            stub.DisconnectPeer(ln.DisconnectPeerRequest(pub_key=peer_pubkey))
            if Peers.objects.filter(pubkey=peer_id).exists():
                db_peer = Peers.objects.filter(pubkey=peer_id)[0]
                db_peer.connected = False
                db_peer.save()
            return Response({'message': 'Disconnection successful!'})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Connection request failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'})


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def open_channel(request):
    serializer = OpenChannelSerializer(data=request.data)
    if serializer.is_valid():
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            peer_pubkey = serializer.validated_data['peer_pubkey']
            connected = False
            if Peers.objects.filter(pubkey=peer_pubkey, connected=True).exists():
                connected = True
            else:
                try:
                    node = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey, include_channels=False)).node
                    host = node.addresses[0].addr
                    ln_addr = ln.LightningAddress(pubkey=peer_pubkey, host=host)
                    response = stub.ConnectPeer(ln.ConnectPeerRequest(addr=ln_addr))
                    connected = True
                except Exception as e:
                    error = str(e)
                    details_index = error.find('details =') + 11
                    debug_error_index = error.find('debug_error_string =') - 3
                    error_msg = error[details_index:debug_error_index]
                    return Response({'error': 'Error connecting to new peer: ' + error_msg})
            if connected:
                for response in stub.OpenChannel(ln.OpenChannelRequest(node_pubkey=bytes.fromhex(peer_pubkey), local_funding_amount=serializer.validated_data['local_amt'], sat_per_byte=serializer.validated_data['sat_per_byte'])):
                    return Response({'message': 'Channel created! Funding TXID: ' + str(response.chan_pending.txid[::-1].hex()) + ':' + str(response.chan_pending.output_index)})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Channel creation failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'})


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def close_channel(request):
    serializer = CloseChannelSerializer(data=request.data)
    if serializer.is_valid():
        try:
            chan_id = serializer.validated_data['chan_id']
            if chan_id.count('x') == 2 and len(chan_id) >= 5:
                target_channel = Channels.objects.filter(short_chan_id=chan_id)
            else:
                target_channel = Channels.objects.filter(chan_id=chan_id)
            if target_channel.exists():
                target_channel = target_channel.get()
                funding_txid = target_channel.funding_txid
                output_index = target_channel.output_index
                target_fee = serializer.validated_data['target_fee']
                channel_point = ln.ChannelPoint()
                channel_point.funding_txid_bytes = bytes.fromhex(funding_txid)
                channel_point.funding_txid_str = funding_txid
                channel_point.output_index = output_index
                stub = lnrpc.LightningStub(lnd_connect())
                if serializer.validated_data['force']:
                    for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, force=True)):
                        return Response({'message': 'Channel force closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index)})
                else:
                    for response in stub.CloseChannel(ln.CloseChannelRequest(channel_point=channel_point, sat_per_byte=target_fee)):
                        return Response({'message': 'Channel gracefully closed! Closing TXID: ' + str(response.close_pending.txid[::-1].hex()) + ':' + str(response.close_pending.output_index)})
            else:
                return Response({'error': 'Channel ID is not valid.'})
        except Exception as e:
            error = str(e)
            details_index = error.find('details =') + 11
            debug_error_index = error.find('debug_error_string =') - 3
            error_msg = error[details_index:debug_error_index]
            return Response({'error': 'Channel close failed! Error: ' + error_msg})
    else:
        return Response({'error': 'Invalid request!'})


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def update_alias(request):
    serializer = UpdateAliasSerializer(data=request.data)
    if serializer.is_valid():
        peer_pubkey = serializer.validated_data['peer_pubkey']
        if Channels.objects.filter(remote_pubkey=peer_pubkey).exists():
            try:
                stub = lnrpc.LightningStub(lnd_connect())
                new_alias = stub.GetNodeInfo(ln.NodeInfoRequest(pub_key=peer_pubkey)).node.alias
                update_channels = Channels.objects.filter(remote_pubkey=peer_pubkey)
                for channel in update_channels:
                    channel.alias = new_alias
                    channel.save()
                messages.success(request, 'Alias updated to: ' + str(new_alias))
            except Exception as e:
                error = str(e)
                details_index = error.find('details =') + 11
                debug_error_index = error.find('debug_error_string =') - 3
                error_msg = error[details_index:debug_error_index]
                messages.error(request, 'Error updating alias: ' + error_msg)
        else:
            messages.error(request, 'Pubkey not in channels list.')
    else:
        messages.error(request, 'Invalid Request. Please try again.')
    return redirect('home')
