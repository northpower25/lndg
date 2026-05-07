from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from ..models import NotificationSettings
from gui.lnd_deps import lightning_pb2 as ln
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps.lnd_connect import lnd_connect
from lndg import settings
from .utils import grpc_error_message, is_login_required, get_local_settings, graph_links, network_links

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def home(request):
    if request.method != 'GET':
        return redirect('home')
    try:
        stub = lnrpc.LightningStub(lnd_connect())
        node_info = stub.GetInfo(ln.GetInfoRequest())
    except Exception as e:
        error = grpc_error_message(e)
        return render(request, 'error.html', {'error': error})
    return render(request, 'home.html', {
        'node_info': {'color': node_info.color, 'alias': node_info.alias, 'version': node_info.version, 'identity_pubkey': node_info.identity_pubkey, 'uris': node_info.uris},
        'local_settings': get_local_settings('AR-'),
        'notification_cfg': NotificationSettings.load(),
        'network': 'testnet/' if settings.LND_NETWORK == 'testnet' else '',
        'graph_links': graph_links(),
        'network_links': network_links(),
    })
