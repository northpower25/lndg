from django.contrib import messages
from django.shortcuts import render, redirect
from django.db.models import Sum, IntegerField, Count, Max, F, Q, Value
from django.db.models.functions import Round, Coalesce
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..forms import *
from ..serializers import *
from ..models import Channels, LocalSettings, AvoidNodes, Onchain, Forwards, Rebalancer, Payments, PaymentHops, Invoices, Closures, Resolutions, Peers, PendingChannels, PendingHTLCs, FailedHTLCs, HistFailedHTLC, Autopilot, Autofees, PeerEvents
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps import walletkit_pb2 as walletrpc
from gui.lnd_deps import walletkit_pb2_grpc as walletstub
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from os import path
from pandas import DataFrame, merge
from .utils import is_login_required, get_local_settings, graph_links, network_links

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def advanced(request):
    if request.method == 'GET':
        channels = Channels.objects.filter(is_open=True).annotate(outbound_percent=((Sum('local_balance')+Sum('pending_outbound'))*1000)/Sum('capacity'), inbound_percent=((Sum('remote_balance')+Sum('pending_inbound'))*1000)/Sum('capacity')).order_by('-is_active', 'outbound_percent')
        channels_df = DataFrame.from_records(channels.values())
        if channels_df.shape[0] > 0:
            channels_df['out_percent'] = channels_df.apply(lambda row: int(round(row['outbound_percent']/10, 0)), axis=1)
            channels_df['in_percent'] = channels_df.apply(lambda row: int(round(row['inbound_percent']/10, 0)), axis=1)
            channels_df['local_balance'] = channels_df.apply(lambda row: row.local_balance + row.pending_outbound, axis=1)
            channels_df['remote_balance'] = channels_df.apply(lambda row: row.remote_balance + row.pending_inbound, axis=1)
            channels_df['fee_ratio'] = channels_df.apply(lambda row: 100 if row['local_fee_rate'] == 0 else int(round(((row['remote_fee_rate']/row['local_fee_rate'])*1000)/10, 0)), axis=1)
            channels_df['local_min_htlc'] = channels_df['local_min_htlc_msat']/1000
            channels_df['local_max_htlc'] = channels_df['local_max_htlc_msat']/1000
        context = {
            'channels': channels_df.to_dict(orient='records'),
            'local_settings': get_local_settings('AF-', 'AR-', 'GUI-', 'LND-'),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'graph_links': graph_links(),
            'network_links': network_links()
        }
        return render(request, 'advanced.html', context)
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def logs(request):
    if request.method == 'GET':
        try:
            count = request.GET.get('tail', 20)
            grep = request.GET.get('grep', None)
            docker_logfile = '/app/data/lndg-controller.log'
            supervisord_logfile = '/var/log/lndg-controller.log'
            if path.exists(docker_logfile):
                logfile = docker_logfile
            elif path.exists(supervisord_logfile):
                logfile = supervisord_logfile
            else:
                return render(request, 'error.html', {'error': 'Log file not found. Expected at ' + docker_logfile + ' or ' + supervisord_logfile})
            file_size = path.getsize(logfile)-2
            if file_size == 0:
                logs = ['Logs are empty....']
            else:
                target_size = 128*int(count)
                read_size = min(target_size, file_size)
                with open(logfile, "rb") as reader:
                    reader.seek(-read_size, 2)
                    logs = []
                    for line in reader.readlines():
                        log_line = line.decode('utf-8')
                        if grep:
                            if str(grep) in log_line:
                                logs.append(log_line)
                        else:
                            logs.append(log_line)
            return render(request, 'logs.html', {'logs': logs})
        except Exception as e:
            return render(request, 'error.html', {'error': str(e)})
    return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def reset(request):
    if request.method == 'GET':
        context = {
            'tables':[
                {'name':'Forwards', 'count': Forwards.objects.count()},
                {'name':'Payments', 'count': Payments.objects.count()},
                {'name':'PaymentHops', 'count': PaymentHops.objects.count()},
                {'name':'Invoices', 'count': Invoices.objects.count()},
                {'name':'Rebalancer', 'count': Rebalancer.objects.count()},
                {'name':'Closures', 'count': Closures.objects.count()},
                {'name':'Resolutions', 'count': Resolutions.objects.count()},
                {'name':'Peers', 'count': Peers.objects.count()},
                {'name':'Channels', 'count': Channels.objects.count()},
                {'name':'PendingChannels', 'count': PendingChannels.objects.count()},
                {'name':'Onchain', 'count': Onchain.objects.count()},
                {'name':'PendingHTLCs', 'count': PendingHTLCs.objects.count()},
                {'name':'FailedHTLCs', 'count': FailedHTLCs.objects.count()},
                {'name':'HistFailedHTLC', 'count': HistFailedHTLC.objects.count()},
                {'name':'Autopilot', 'count': Autopilot.objects.count()},
                {'name':'Autofees', 'count': Autofees.objects.count()},
                {'name':'AvoidNodes', 'count': AvoidNodes.objects.count()},
                {'name':'PeerEvents', 'count': PeerEvents.objects.count()},
                {'name':'LocalSettings', 'count': LocalSettings.objects.count()}
            ]
        }
        return render(request, 'reset.html', context)
    else:
        return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def update_keysend(request):
    if request.method == 'POST':
        form = UpdateKeysend(request.POST)
        if form.is_valid() and Invoices.objects.filter(r_hash=form.cleaned_data['r_hash']).exists():
            r_hash = form.cleaned_data['r_hash']
            db_invoice = Invoices.objects.filter(r_hash=r_hash)[0]
            db_invoice.is_revenue = not db_invoice.is_revenue
            db_invoice.save()
            messages.success(request, ('Marked' if db_invoice.is_revenue else 'Unmarked') + ' invoice ' + str(r_hash) + ' as revenue.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def add_avoid(request):
    if request.method == 'POST':
        form = AddAvoid(request.POST)
        if form.is_valid():
            pubkey = form.cleaned_data['pubkey']
            notes = form.cleaned_data['notes']
            AvoidNodes(pubkey=pubkey, notes=notes).save()
            messages.success(request, 'Successfully added node ' + str(pubkey) + ' to the avoid list.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def remove_avoid(request):
    if request.method == 'POST':
        form = RemoveAvoid(request.POST)
        if form.is_valid() and AvoidNodes.objects.filter(pubkey=form.cleaned_data['pubkey']).exists():
            pubkey = form.cleaned_data['pubkey']
            AvoidNodes.objects.filter(pubkey=pubkey).delete()
            messages.success(request, 'Successfully removed node ' + str(pubkey) + ' from the avoid list.')
        else:
            messages.error(request, 'Invalid Request. Please try again.')
    return redirect(request.META.get('HTTP_REFERER'))


@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def forwards_summary(request):
    filter_1day = datetime.now() - timedelta(days=1)
    filter_7day = datetime.now() - timedelta(days=7)
    summary_out = Forwards.objects.values(chan_id=F('chan_id_out')).annotate(
        count_outgoing_1day=Count('id', filter=Q(forward_date__gte=filter_1day)),
        sum_outgoing_1day=Coalesce(Sum('amt_out_msat', filter=Q(forward_date__gte=filter_1day)), 0),
        count_outgoing_7day=Count('id', filter=Q(forward_date__gte=filter_7day)),
        sum_outgoing_7day=Coalesce(Sum('amt_out_msat', filter=Q(forward_date__gte=filter_7day)), 0),
        sum_fees_1day=Coalesce(Sum('fee', filter=Q(forward_date__gte=filter_1day)), 0.0),
        sum_fees_7day=Coalesce(Sum('fee', filter=Q(forward_date__gte=filter_7day)), 0.0),
        count_incoming_1day=Value(0),
        sum_incoming_1day=Value(0),
        count_incoming_7day=Value(0),
        sum_incoming_7day=Value(0)
    ).filter(
        Q(count_outgoing_1day__gt=0) |
        Q(sum_outgoing_1day__gt=0) |
        Q(count_outgoing_7day__gt=0) |
        Q(sum_outgoing_7day__gt=0) |
        Q(sum_fees_1day__gt=0) |
        Q(sum_fees_7day__gt=0)
    )

    summary_in = Forwards.objects.values(chan_id=F('chan_id_in')).annotate(
        count_outgoing_1day=Value(0),
        sum_outgoing_1day=Value(0),
        count_outgoing_7day=Value(0),
        sum_outgoing_7day=Value(0),
        sum_fees_1day=Value(0),
        sum_fees_7day=Value(0),
        count_incoming_1day=Count('id', filter=Q(forward_date__gte=filter_1day)),
        sum_incoming_1day=Coalesce(Sum('amt_in_msat', filter=Q(forward_date__gte=filter_1day)), 0),
        count_incoming_7day=Count('id', filter=Q(forward_date__gte=filter_7day)),
        sum_incoming_7day=Coalesce(Sum('amt_in_msat', filter=Q(forward_date__gte=filter_7day)), 0)
    ).filter(
        Q(count_incoming_1day__gt=0) |
        Q(sum_incoming_1day__gt=0) |
        Q(count_incoming_7day__gt=0) |
        Q(sum_incoming_7day__gt=0)
    )

    return Response({'results': summary_out.union(summary_in)})


def get_channeldb_file_size():
    try:
        # Create the Enable setting if it doesn't exist ---
        enabled_setting = LocalSettings.objects.filter(key='RemoteFSEnabled').first()
        if not enabled_setting:
            LocalSettings.objects.create(key='RemoteFSEnabled', value='0')  # Default: disabled
            # IMPORTANT: We do NOT create other settings here.
            # Only once enabled at /api/settings/RemoteFSEnabled/, we create the rest to avoid boilerplate
            enabled = False  # Since we just created it, it's disabled.
        else:
            # Read the Enable setting ---
            enabled = bool(int(LocalSettings.objects.get(key='RemoteFSEnabled').value))

        if enabled:
            # Only import paramiko if enabled
            import paramiko

            # Create connection settings only if enabled AND they don't exist ---
            host = LocalSettings.objects.filter(key='RemoteFSHost').first()
            if not host:
                LocalSettings.objects.create(key='RemoteFSHost', value='')
                host_value = LocalSettings.objects.get(key='RemoteFSHost').value
            else:
                host_value = host.value

            user = LocalSettings.objects.filter(key='RemoteFSUser').first()
            if not user:
                LocalSettings.objects.create(key='RemoteFSUser', value='')
                user_value = LocalSettings.objects.get(key='RemoteFSUser').value
            else:
                user_value = user.value

            port = LocalSettings.objects.filter(key='RemoteFSPort').first()
            if not port:
                LocalSettings.objects.create(key='RemoteFSPort', value='22')  # Default SSH port
                port_value = LocalSettings.objects.get(key='RemoteFSPort').value
            else:
                port_value = port.value

            db_path = LocalSettings.objects.filter(key='RemoteFSPath').first()
            if not db_path:
                default_path = '/home/admin/.lnd/data/graph/mainnet/channel.db'
                LocalSettings.objects.create(key='RemoteFSPath', value=default_path)
                db_path_value = LocalSettings.objects.get(key='RemoteFSPath').value
            else:
                db_path_value = db_path.value

            # Read the connection settings ---
            port = int(port_value)  # Ensure port is an integer
            channel_db_path = db_path_value if db_path_value else settings.LND_DATABASE_PATH # Use settings path if db path is blank

            # Check for required settings
            if not host_value or not user_value:
                print("Error: Remote file size enabled, but host or user is not set.")
                return round(path.getsize(path.expanduser(settings.LND_DATABASE_PATH))*0.000000001, 3)

            # --- Paramiko logic ---
            try:
                # Create SSH client
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Automatically add host keys

                # Connect to the remote host (eg 10.1.1.2, lnd, 22)
                ssh.connect(hostname=host_value, username=user_value, port=port)

                # Open an SFTP session
                sftp = ssh.open_sftp()

                # Get file stats
                file_stat = sftp.stat(channel_db_path)

                # Get file size
                file_size_bytes = file_stat.st_size

                # Close connections
                sftp.close()
                ssh.close()

                return round(file_size_bytes * 0.000000001, 3)

            except Exception as e:
                print(f"Error retrieving file size with paramiko: {e}")
                return round(path.getsize(path.expanduser(settings.LND_DATABASE_PATH))*0.000000001, 3) # Fallback
            # --- End Paramiko logic ---

        else:
            # Use the original default behavior (local file size)
            return round(path.getsize(path.expanduser(settings.LND_DATABASE_PATH))*0.000000001, 3)

    except Exception as e:
        # Handle exceptions
        print(f"Error retrieving channel.db file size: {e}")
        return 0


@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def node_info(request):
    stub = lnrpc.LightningStub(lnd_connect())
    node_info = stub.GetInfo(ln.GetInfoRequest())
    balances = stub.WalletBalance(ln.WalletBalanceRequest())
    pending_channels = stub.PendingChannels(ln.PendingChannelsRequest())

    limbo_balance = pending_channels.total_limbo_balance
    pending_open = None
    pending_closed = None
    pending_force_closed = None
    waiting_for_close = None
    pending_open_balance = 0
    pending_closing_balance = 0
    if pending_channels.pending_open_channels:
        target_resp = pending_channels.pending_open_channels
        peers = Peers.objects.all()
        pending_changes = PendingChannels.objects.all()
        pending_open = []
        inbound_setting = int(LocalSettings.objects.filter(key='AR-Inbound%')[0].value) if LocalSettings.objects.filter(key='AR-Inbound%').exists() else 90
        outbound_setting = int(LocalSettings.objects.filter(key='AR-Outbound%')[0].value) if LocalSettings.objects.filter(key='AR-Outbound%').exists() else 75
        amt_setting = float(LocalSettings.objects.filter(key='AR-Target%')[0].value) if LocalSettings.objects.filter(key='AR-Target%').exists() else 3
        cost_setting = int(LocalSettings.objects.filter(key='AR-MaxCost%')[0].value) if LocalSettings.objects.filter(key='AR-MaxCost%').exists() else 65
        auto_fees = int(LocalSettings.objects.filter(key='AF-Enabled')[0].value) if LocalSettings.objects.filter(key='AF-Enabled').exists() else 0
        for i in range(0,len(target_resp)):
            item = {}
            pending_open_balance += target_resp[i].channel.local_balance
            funding_txid = target_resp[i].channel.channel_point.split(':')[0]
            output_index = target_resp[i].channel.channel_point.split(':')[1]
            updated = pending_changes.filter(funding_txid=funding_txid,output_index=output_index).exists()
            item['alias'] = peers.filter(pubkey=target_resp[i].channel.remote_node_pub)[0].alias if peers.filter(pubkey=target_resp[i].channel.remote_node_pub).exists() else ''
            item['remote_node_pub'] = target_resp[i].channel.remote_node_pub
            item['channel_point'] = target_resp[i].channel.channel_point
            item['funding_txid'] = funding_txid
            item['output_index'] = output_index
            item['capacity'] = target_resp[i].channel.capacity
            item['local_balance'] = target_resp[i].channel.local_balance
            item['remote_balance'] = target_resp[i].channel.remote_balance
            item['local_chan_reserve_sat'] = target_resp[i].channel.local_chan_reserve_sat
            item['remote_chan_reserve_sat'] = target_resp[i].channel.remote_chan_reserve_sat
            item['initiator'] = target_resp[i].channel.initiator
            item['commitment_type'] = target_resp[i].channel.commitment_type
            item['commit_fee'] = target_resp[i].commit_fee
            item['commit_weight'] = target_resp[i].commit_weight
            item['fee_per_kw'] = target_resp[i].fee_per_kw
            item['local_base_fee'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].local_base_fee if updated else ''
            item['local_fee_rate'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].local_fee_rate if updated else ''
            item['local_cltv'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].local_cltv if updated else ''
            item['auto_rebalance'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].auto_rebalance if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].auto_rebalance != None else False
            item['ar_amt_target'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_amt_target if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_amt_target != None else int((amt_setting/100) * target_resp[i].channel.capacity)
            item['ar_in_target'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_in_target if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_in_target != None else inbound_setting
            item['ar_out_target'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_out_target if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_out_target != None else outbound_setting
            item['ar_max_cost'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_max_cost if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].ar_max_cost != None else cost_setting
            item['auto_fees'] = pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].auto_fees if updated and pending_changes.filter(funding_txid=funding_txid,output_index=output_index)[0].auto_fees != None else (False if auto_fees == 0 else True)
            pending_open.append(item)
    if pending_channels.pending_closing_channels:
        target_resp = pending_channels.pending_closing_channels
        pending_closed = []
        for i in range(0,len(target_resp)):
            pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
            'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat,'limbo_balance':target_resp[i].limbo_balance,'closing_txid':target_resp[i].closing_txid}
            pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
            pending_closed.append(pending_item)
    if pending_channels.pending_force_closing_channels:
        target_resp = pending_channels.pending_force_closing_channels
        pending_force_closed = []
        for i in range(0,len(target_resp)):
            pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'initiator':target_resp[i].channel.initiator,
            'commitment_type':target_resp[i].channel.commitment_type,'closing_txid':target_resp[i].closing_txid,'limbo_balance':target_resp[i].limbo_balance,'maturity_height':target_resp[i].maturity_height,'blocks_til_maturity':target_resp[i].blocks_til_maturity if target_resp[i].blocks_til_maturity > 0 else find_next_block_maturity(target_resp[i]),
            'maturity_datetime':(datetime.now()+timedelta(minutes=(10*target_resp[i].blocks_til_maturity if target_resp[i].blocks_til_maturity > 0 else 10*find_next_block_maturity(target_resp[i]) )))}
            pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
            pending_force_closed.append(pending_item)
    if pending_channels.waiting_close_channels:
        target_resp = pending_channels.waiting_close_channels
        waiting_for_close = []
        for i in range(0,len(target_resp)):
            pending_closing_balance += target_resp[i].limbo_balance
            pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
            'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat, 'limbo_balance':target_resp[i].limbo_balance,'closing_txid':target_resp[i].closing_txid}
            pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
            waiting_for_close.append(pending_item)
    limbo_balance -= pending_closing_balance
    try:
        db_size = get_channeldb_file_size()
    except:
        db_size = 0
    return Response({
        'version': node_info.version,
        'num_peers': node_info.num_peers,
        'synced_to_graph': node_info.synced_to_graph,
        'synced_to_chain': node_info.synced_to_chain,
        'num_active_channels': node_info.num_active_channels,
        'num_inactive_channels': node_info.num_inactive_channels,
        'chains': [chain.chain+"-"+chain.network for chain in node_info.chains],
        'block': {'hash': node_info.block_hash, 'height': node_info.block_height},
        'balance': {
            'limbo': limbo_balance,
            'onchain': balances.total_balance,
            'confirmed': balances.confirmed_balance,
            'unconfirmed': balances.unconfirmed_balance,
            'total': balances.total_balance + pending_open_balance + limbo_balance,
        },
        'pending_open': pending_open,
        'pending_closed': pending_closed,
        'pending_force_closed': pending_force_closed,
        'waiting_for_close': waiting_for_close,
        'db_size': db_size
    })


@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def get_info(request):
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        response = stub.GetInfo(ln.GetInfoRequest())
        target = {'identity_pubkey':response.identity_pubkey, 'alias':response.alias, 'num_active_channels':response.num_active_channels, 'num_peers':response.num_peers, 'block_height':response.block_height, 'block_hash':response.block_hash,'synced_to_chain':response.synced_to_chain,'testnet':response.testnet,'uris':[uri for uri in response.uris],'best_header_timestamp':response.best_header_timestamp,'version':response.version,'num_inactive_channels':response.num_inactive_channels,'chains':[{'chain':response.chains[i].chain,'network':response.chains[i].network} for i in range(0,len(response.chains))],'color':response.color,'synced_to_graph':response.synced_to_graph}
        return Response({'message': 'success', 'data':target})
    except Exception as e:
        error = str(e)
        details_index = error.find('details =') + 11
        debug_error_index = error.find('debug_error_string =') - 3
        error_msg = error[details_index:debug_error_index]
        return Response({'error': 'Failed to call getinfo! Error: ' + error_msg})


@api_view(['POST'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def reset_api(request):
    serializer = ResetSerializer(data=request.data)
    if serializer.is_valid():
        table = serializer.validated_data['table']
        tables = {
            'Forwards': Forwards.objects.all(),
            'Payments': Payments.objects.all(),
            'PaymentHops': PaymentHops.objects.all(),
            'Invoices': Invoices.objects.all(),
            'Rebalancer': Rebalancer.objects.all(),
            'Closures': Closures.objects.all(),
            'Resolutions': Resolutions.objects.all(),
            'Peers': Peers.objects.all(),
            'Channels': Channels.objects.all(),
            'PendingChannels': PendingChannels.objects.all(),
            'Onchain': Onchain.objects.all(),
            'PendingHTLCs': PendingHTLCs.objects.all(),
            'FailedHTLCs': FailedHTLCs.objects.all(),
            'HistFailedHTLC': HistFailedHTLC.objects.all(),
            'Autopilot': Autopilot.objects.all(),
            'Autofees': Autofees.objects.all(),
            'AvoidNodes': AvoidNodes.objects.all(),
            'PeerEvents': PeerEvents.objects.all(),
            'LocalSettings': LocalSettings.objects.all()
        }
        try:
            target_table = tables[table]
            target_table.delete()
            return Response({'message': f'Successfully deleted table: {table}'})
        except Exception as e:
            error = str(e)
            return Response({'error': f'Error deleting table: {error}'})
    else:
        return Response({'error': serializer.error_messages})

@api_view(['GET'])
@is_login_required(permission_classes([IsAuthenticated]), settings.LOGIN_REQUIRED)
def cert_validity(request):
    """bos cert-validity-days – return days remaining on the LND TLS certificate."""
    import ssl, subprocess
    from datetime import timezone as tz
    try:
        cert_path = path.expanduser(settings.LND_TLS_PATH)
        result = subprocess.run(
            ['openssl', 'x509', '-noout', '-enddate'],
            input=open(cert_path, 'rb').read(),
            capture_output=True,
        )
        expiry_str = result.stdout.decode().strip().replace('notAfter=', '')
        try:
            expiry_dt = datetime.strptime(expiry_str, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=tz.utc)
        except ValueError:
            expiry_dt = datetime.strptime(expiry_str, '%b  %d %H:%M:%S %Y %Z').replace(tzinfo=tz.utc)
        days_remaining = (expiry_dt - datetime.now(tz=tz.utc)).days
        return Response({
            'message': 'success',
            'data': {
                'days_remaining': days_remaining,
                'expiry': expiry_dt.strftime('%Y-%m-%d'),
            }
        })
    except Exception:
        return Response({'error': 'Failed to read TLS certificate. Check server logs.'}, status=500)

# ---------------------------------------------------------------------------
# Notification Settings
# ---------------------------------------------------------------------------

