from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from pandas import DataFrame, merge
from ..models import Closures, Resolutions, Channels
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from .utils import is_login_required, find_next_block_maturity, network_links, graph_links, pending_channel_details

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def closures(request):
    if request.method == 'GET':
        try:
            stub = lnrpc.LightningStub(lnd_connect())
            pending_channels = stub.PendingChannels(ln.PendingChannelsRequest())
            pending_closed = None
            pending_force_closed = None
            waiting_for_close = None
            if pending_channels.pending_closing_channels:
                target_resp = pending_channels.pending_closing_channels
                pending_closed = []
                for i in range(0,len(target_resp)):
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
                    'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat, 'limbo_balance':target_resp[i].limbo_balance, 'closing_txid':target_resp[i].closing_txid}
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
                    pending_item = {'remote_node_pub':target_resp[i].channel.remote_node_pub,'channel_point':target_resp[i].channel.channel_point,'capacity':target_resp[i].channel.capacity,'local_balance':target_resp[i].channel.local_balance,'remote_balance':target_resp[i].channel.remote_balance,'local_chan_reserve_sat':target_resp[i].channel.local_chan_reserve_sat,
                    'remote_chan_reserve_sat':target_resp[i].channel.remote_chan_reserve_sat,'initiator':target_resp[i].channel.initiator,'commitment_type':target_resp[i].channel.commitment_type, 'local_commit_fee_sat': target_resp[i].commitments.local_commit_fee_sat, 'limbo_balance':target_resp[i].limbo_balance, 'closing_txid':target_resp[i].closing_txid}
                    pending_item.update(pending_channel_details(target_resp[i].channel.channel_point))
                    waiting_for_close.append(pending_item)
            closures_df = DataFrame.from_records(Closures.objects.all().values())
            if closures_df.empty:
                merged = DataFrame()
            else:
                channels_df = DataFrame.from_records(Channels.objects.all().values('chan_id', 'short_chan_id', 'alias'))
                if channels_df.empty:
                    merged = closures_df
                    merged['alias'] = ''
                    merged['short_chan_id'] = merged.apply(lambda row: str(int(row.chan_id) >> 40) + 'x' + str(int(int(row.chan_id) >> 16) & 0xFFFFFF) + 'x' + str(int(row.chan_id) & 0xFFFF), axis=1)
                else:
                    merged = merge(closures_df, channels_df, on='chan_id', how='left')
                    merged['alias'] = merged['alias'].fillna('')
                    merged['short_chan_id'] = merged['short_chan_id'].fillna('')
                    merged['short_chan_id'] = merged.apply(lambda row: str(int(row.chan_id) >> 40) + 'x' + str(int(int(row.chan_id) >> 16) & 0xFFFFFF) + 'x' + str(int(row.chan_id) & 0xFFFF) if row.short_chan_id == '' else row.short_chan_id, axis=1)
            context = {
                'pending_closed': pending_closed,
                'pending_force_closed': pending_force_closed,
                'waiting_for_close': waiting_for_close,
                'closures': [] if merged.empty else merged.sort_values(by=['close_height'], ascending=False).to_dict(orient='records'),
                'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
                'network_links': network_links(),
                'graph_links': graph_links()
            }
            return render(request, 'closures.html', context)
        except Exception as e:
            try:
                error = str(e.code())
            except:
                error = str(e)
            return render(request, 'error.html', {'error': error})
    else:
        return redirect('home')


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def resolutions(request):
    if request.method == 'GET':
        chan_id = request.GET.urlencode()[1:]
        context = {
            'chan_id': chan_id,
            'resolutions': Resolutions.objects.filter(chan_id=chan_id),
            'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
            'network_links': network_links()
        }
        return render(request, 'resolutions.html', context)
    else:
        return redirect('home')

