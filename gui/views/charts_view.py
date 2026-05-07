from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from lndg import settings
from .utils import is_login_required
from gui.backends.registry import get_capabilities


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/charts/'), settings.LOGIN_REQUIRED)
def charts_view(request):
    caps = get_capabilities()
    return render(request, 'charts.html', {'capabilities': caps})
