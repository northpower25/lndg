from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import NotificationSettings
from lndg import settings
from .utils import is_login_required

@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
def notification_settings(request):
    """Show and save the NotificationSettings singleton."""
    cfg = NotificationSettings.load()
    if request.method == 'POST':
        def _bool(key, default=False):
            return request.POST.get(key, '').lower() in ('true', '1', 'on', 'yes')

        cfg.tg_enabled = _bool('tg_enabled')
        cfg.tg_bot_token = request.POST.get('tg_bot_token', '').strip()
        cfg.tg_chat_id = request.POST.get('tg_chat_id', '').strip()
        cfg.notify_rebalance_success = _bool('notify_rebalance_success')
        cfg.notify_rebalance_fail = _bool('notify_rebalance_fail')
        cfg.notify_channel_inactive = _bool('notify_channel_inactive')
        cfg.notify_autofee = _bool('notify_autofee')
        cfg.save()
        messages.success(request, 'Notification settings saved.')
        return redirect('home')
    # GET – redirect to home (settings are embedded there)
    return redirect('home')



@is_login_required(login_required(login_url='/lndg-admin/login/?next=/'), settings.LOGIN_REQUIRED)
@api_view(['POST'])
def test_notification(request):
    """Send a test notification via all enabled backends."""
    try:
        import notify as notify_module
        result = notify_module.send_notification('🔔 LNDg test notification – your setup is working!')
        tg_ok = result.get('telegram')
        summary = {}
        if tg_ok is not None:
            summary['telegram'] = 'sent' if tg_ok else 'failed'
        if not summary:
            return Response({'message': 'No notification backends enabled. Configure Telegram first.'}, status=400)
        return Response({'message': 'Test notification dispatched.', 'results': summary})
    except Exception:
        return Response({'error': 'Notification test failed. Check server logs for details.'}, status=500)
