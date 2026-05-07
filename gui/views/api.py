from django.db.models import Q
from django_filters import FilterSet, CharFilter, DateTimeFilter, NumberFilter
from datetime import datetime
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..serializers import *  # noqa: F403
from ..models import Payments, PaymentHops, Invoices, Forwards, Channels, Rebalancer, LocalSettings, Peers, Onchain, Closures, Resolutions, PendingHTLCs, FailedHTLCs, InboundFeeLog, PeerEvents, TradeSales
from lndg import settings
from django.shortcuts import get_object_or_404

class PaymentsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Payments.objects.all().order_by('-creation_date')
    serializer_class = PaymentSerializer
    filterset_fields = {'status':['exact','lt','gt'], 'creation_date':['lte','gte'], 'chan_out': ['exact'], 'index': ['lt']}


class PaymentHopsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = PaymentHops.objects.all()
    serializer_class = PaymentHopsSerializer


class InvoicesViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Invoices.objects.all().order_by('-creation_date')
    serializer_class = InvoiceSerializer
    filterset_fields = {'state': ['exact','lt', 'gt'], 'is_revenue': ['exact'], 'settle_date': ['gte'], 'chan_in': ['exact'], 'index': ['lt']}

    def update(self, request, pk=None):
        setting = get_object_or_404(Invoices.objects.all(), pk=pk)
        serializer = InvoiceSerializer(setting, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)


class ForwardsFilter(FilterSet):
    chan_in_or_out = CharFilter(method='filter_chan_in_or_out', label='Chan In Or Out')
    forward_date__lte = DateTimeFilter(field_name='forward_date', lookup_expr='lte')
    forward_date__gte = DateTimeFilter(field_name='forward_date', lookup_expr='gte')
    forward_date__lt = DateTimeFilter(field_name='forward_date', lookup_expr='lt')
    forward_date__gt = DateTimeFilter(field_name='forward_date', lookup_expr='gt')
    id__lt = NumberFilter(field_name='id', lookup_expr='lt')

    def filter_chan_in_or_out(self, queryset, name, value):
        return queryset.filter(
            Q(chan_id_in__exact=value) | Q(chan_id_out__exact=value)
        )

    class Meta:
        model = Forwards
        fields = ['chan_in_or_out', 'forward_date__lte', 'forward_date__gte', 'forward_date__lt', 'forward_date__gt', 'id__lt']


class ForwardsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Forwards.objects.all().order_by('-id')
    serializer_class = ForwardSerializer
    filterset_class = ForwardsFilter


class PeersViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Peers.objects.all()
    serializer_class = PeerSerializer


class OnchainViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Onchain.objects.all()
    serializer_class = OnchainSerializer
    filterset_fields = {'time_stamp': ['lte','gte']}


class ClosuresViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Closures.objects.all()
    serializer_class = ClosuresSerializer
    filterset_fields = {'close_height': ['lte','gte']}


class ResolutionsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Resolutions.objects.all()
    serializer_class = ResolutionsSerializer


class PendingHTLCViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = PendingHTLCs.objects.all()
    serializer_class = PendingHTLCSerializer


class PeerEventsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = PeerEvents.objects.all().order_by('-id')
    serializer_class = PeerEventsSerializer
    filterset_fields = {'chan_id': ['exact'], 'id': ['lt']}


class TradeSalesViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = TradeSales.objects.all()
    serializer_class = TradeSalesSerializer

    def update(self, request, pk):
        rebalance = get_object_or_404(self.queryset, pk=pk)
        serializer = self.get_serializer(rebalance, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)


class FeeLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Autofees.objects.all().order_by('-id')
    serializer_class = FeeLogSerializer
    filterset_fields = {'chan_id': ['exact'], 'id': ['lt']}


class InboundFeeLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = InboundFeeLog.objects.all().order_by('-id')
    serializer_class = InboundFeeLogSerializer
    filterset_fields = {'chan_id': ['exact'], 'id': ['lt']}


class FailedHTLCFilter(FilterSet):
    chan_in_or_out = CharFilter(method='filter_chan_in_or_out', label='Chan In Or Out')
    chan_id_in = CharFilter(field_name='chan_id_in', lookup_expr='exact')
    chan_id_out = CharFilter(field_name='chan_id_out', lookup_expr='exact')
    wire_failure__lt = NumberFilter(field_name='wire_failure', lookup_expr='lt')
    wire_failure__gt = NumberFilter(field_name='wire_failure', lookup_expr='gt')
    id__lt = NumberFilter(field_name='id', lookup_expr='lt')

    def filter_chan_in_or_out(self, queryset, name, value):
        return queryset.filter(
            Q(chan_id_in__exact=value) | Q(chan_id_out__exact=value)
        )

    class Meta:
        model = FailedHTLCs
        fields = ['chan_in_or_out', 'chan_id_in', 'chan_id_out', 'wire_failure__lt', 'wire_failure__gt', 'id__lt']


class FailedHTLCViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = FailedHTLCs.objects.all().order_by('-id')
    serializer_class = FailedHTLCSerializer
    filterset_class = FailedHTLCFilter


class LocalSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = LocalSettings.objects.all()
    serializer_class = LocalSettingsSerializer

    def update(self, request, pk):
        setting = get_object_or_404(self.queryset, pk=pk)
        serializer = LocalSettingsSerializer(setting, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)


class ChannelsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Channels.objects.all()
    serializer_class = ChannelSerializer
    filterset_fields = ['is_open', 'private', 'is_active', 'auto_rebalance']

    def update(self, request, pk):
        channel = get_object_or_404(self.queryset, pk=pk)
        serializer = ChannelSerializer(channel, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)


class RebalancerViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated] if settings.LOGIN_REQUIRED else []
    queryset = Rebalancer.objects.all().order_by('-id')
    serializer_class = RebalancerSerializer
    filterset_fields = {'status':['lt','gt','exact'], 'payment_hash':['exact'], 'stop':['gt'], 'last_hop_pubkey':['exact'], 'id':['lt']}

    def create(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

    def update(self, request, pk):
        rebalance = get_object_or_404(self.queryset, pk=pk)
        serializer = RebalancerSerializer(rebalance, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            rebalance.stop = datetime.now()
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

