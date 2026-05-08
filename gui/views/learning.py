from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from lndg import settings

from .utils import is_login_required


@is_login_required(login_required(login_url='/lndg-admin/login/?next=/learning/'), settings.LOGIN_REQUIRED)
def learning_center(request):
    return render(request, 'learning_center.html')
