from django.urls import path

from .views import (
    backup_create,
    backup_list,
    capabilities,
    chart_channel_health,
    chart_fee_volume,
    chart_liquidity,
    cleaner_run,
    cockpit_stats,
    health,
    user_settings,
)

urlpatterns = [
    path("health/", health, name="api-v2-health"),
    path("user/settings/", user_settings, name="api-v2-user-settings"),
    path("cockpit/", cockpit_stats, name="api-v2-cockpit"),
    path("capabilities/", capabilities, name="api-v2-capabilities"),
    path("charts/liquidity/", chart_liquidity, name="api-v2-chart-liquidity"),
    path("charts/channel-health/", chart_channel_health, name="api-v2-chart-channel-health"),
    path("charts/fee-volume/", chart_fee_volume, name="api-v2-chart-fee-volume"),
    path("cleaner/run/", cleaner_run, name="api-v2-cleaner-run"),
    path("backup/create/", backup_create, name="api-v2-backup-create"),
    path("backup/", backup_list, name="api-v2-backup-list"),
]
