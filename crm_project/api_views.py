from rest_framework import viewsets, permissions
from sales_funnel.models import SalesFunnel
from sales_proposals.models import Proposal
from sales_monitoring.models import SalesActivity
from crm_project.serializers import SalesFunnelSerializer, ProposalSerializer, SalesActivitySerializer
from django.db.models import Q

class SalesFunnelViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Sales Funnel
    """
    queryset = SalesFunnel.objects.all()
    serializer_class = SalesFunnelSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'gm', 'vp', 'avp']:
            return SalesFunnel.objects.all()
        # For salespeople, show only their own funnel
        return SalesFunnel.objects.filter(salesperson=user)

class ProposalViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Proposals
    """
    queryset = Proposal.objects.all()
    serializer_class = ProposalSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'gm', 'vp', 'avp']:
            return Proposal.objects.all()
        # For salespeople, show only their own proposals
        return Proposal.objects.filter(created_by=user)

class SalesActivityViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Sales Activities
    """
    queryset = SalesActivity.objects.all()
    serializer_class = SalesActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'gm', 'vp', 'avp']:
            return SalesActivity.objects.all()
        # For salespeople, show only their own activities
        return SalesActivity.objects.filter(salesperson=user)
