from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from lndg import settings
from .utils import is_login_required
from gui.backends.registry import get_capabilities
from gui.models import Channels, UserMode


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/onboarding/'), settings.LOGIN_REQUIRED)
def onboarding(request):
    caps = get_capabilities()
    open_channel_count = Channels.objects.filter(is_open=True).count()
    mode = UserMode.load()
    start_step = 1 if not mode.onboarding_step else min(5, mode.onboarding_step + 1)
    context = {
        'capabilities': caps,
        'node_info': {
            'open_channel_count': open_channel_count,
        },
        'onboarding_step': start_step,
        'onboarding_completed': mode.onboarding_completed,
        'user_language': mode.language or 'en',
    }
    return render(request, 'onboarding.html', context)
