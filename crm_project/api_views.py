import threading

from django.core.management import call_command
from django.db.models import F, Min, Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from crm_project.serializers import (
    CampaignDetailSerializer,
    CampaignListSerializer,
    CustomerCreateRequestSerializer,
    CustomerDetailSerializer,
    CustomerDirectCreateSerializer,
    CustomerListSerializer,
    ProposalApprovalDecisionSerializer,
    ProposalApprovalInboxSerializer,
    ProposalDetailSerializer,
    ProposalCreateSerializer,
    ProposalListSerializer,
    SalesActivityCreateSerializer,
    SalesActivityDetailSerializer,
    SalesActivityListSerializer,
    SalesFunnelSerializer,
    get_visible_activity_queryset,
    get_visible_customer_queryset,
    get_visible_proposal_queryset,
    MANAGER_ROLES,
    EXEC_ROLES,
)
from customers.models import Customer, CustomerCreateRequest
from mass_mailing.models import Campaign
from mass_mailing.rendering import render_campaign_html
from mass_mailing.views import get_allowed_campaigns, get_recipient_context
from sales_funnel.models import SalesFunnel
from sales_monitoring.models import SalesActivity
from sales_proposals.models import Proposal, ProposalApprovalStep
from teams.models import Group, TeamMembership


class SalesFunnelViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesFunnel.objects.all()
    serializer_class = SalesFunnelSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        qs = SalesFunnel.objects.select_related('customer', 'salesperson', 'proposal')
        if user.role in EXEC_ROLES or user.role == 'avp':
            return qs
        if user.role == 'salesperson':
            return qs.filter(salesperson=user)
        if user.role == 'supervisor':
            groups = Group.objects.filter(supervisor=user)
            salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
            return qs.filter(Q(salesperson_id__in=salesperson_ids) | Q(salesperson=user))
        if user.role == 'teamlead':
            groups = Group.objects.filter(teamlead=user)
            salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
            return qs.filter(Q(salesperson_id__in=salesperson_ids) | Q(salesperson=user))
        if user.role == 'asm':
            groups = Group.objects.filter(team__in=user.asm_teams.all())
            salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
            return qs.filter(Q(salesperson_id__in=salesperson_ids) | Q(salesperson=user))
        return qs.none()


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return (
            get_visible_customer_queryset(self.request.user)
            .select_related('salesperson')
            .prefetch_related('contacts')
            .order_by('company_name')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomerDirectCreateSerializer
        if self.action == 'retrieve':
            return CustomerDetailSerializer
        return CustomerListSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role not in MANAGER_ROLES:
            return Response(
                {'detail': 'Salespeople should submit customer create requests from Android.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        return Response(
            CustomerDetailSerializer(customer, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class CustomerCreateRequestViewSet(viewsets.ModelViewSet):
    queryset = CustomerCreateRequest.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = CustomerCreateRequest.objects.select_related('requested_by', 'reviewed_by').order_by('-created_at')
        if self.request.user.role in EXEC_ROLES or self.request.user.role == 'avp':
            return qs
        if self.request.user.role == 'salesperson':
            return qs.filter(requested_by=self.request.user)
        return qs.none()

    def get_serializer_class(self):
        return CustomerCreateRequestSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != 'salesperson':
            return Response(
                {'detail': 'Only salespeople can submit customer create requests.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        create_request = serializer.save()
        return Response(
            CustomerCreateRequestSerializer(create_request, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def pending(self, request):
        if request.user.role not in EXEC_ROLES and request.user.role != 'avp':
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        qs = self.get_queryset().filter(status='pending')
        serializer = self.get_serializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def mine(self, request):
        qs = self.get_queryset()
        serializer = self.get_serializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if request.user.role not in EXEC_ROLES and request.user.role != 'avp':
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        create_request = self.get_object()
        if create_request.status != 'pending':
            return Response({'detail': 'This request is no longer pending.'}, status=status.HTTP_400_BAD_REQUEST)

        customer = create_request.approve(request.user)
        return Response({
            'detail': 'Customer request approved.',
            'request': CustomerCreateRequestSerializer(create_request, context={'request': request}).data,
            'customer': CustomerDetailSerializer(customer, context={'request': request}).data,
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if request.user.role not in EXEC_ROLES and request.user.role != 'avp':
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        create_request = self.get_object()
        if create_request.status != 'pending':
            return Response({'detail': 'This request is no longer pending.'}, status=status.HTTP_400_BAD_REQUEST)

        note = request.data.get('note', '')
        create_request.reject(request.user, notes=note)
        return Response({
            'detail': 'Customer request rejected.',
            'request': CustomerCreateRequestSerializer(create_request, context={'request': request}).data,
        })


class ProposalViewSet(viewsets.ModelViewSet):
    queryset = Proposal.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return (
            get_visible_proposal_queryset(self.request.user)
            .select_related('customer', 'created_by')
            .prefetch_related('items', 'approval_steps__approver')
            .order_by('-created_at')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return ProposalCreateSerializer
        if self.action == 'retrieve':
            return ProposalDetailSerializer
        if self.action in ['approve', 'reject']:
            return ProposalApprovalDecisionSerializer
        return ProposalListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        proposal = serializer.save()
        return Response(
            ProposalDetailSerializer(proposal, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        steps = (
            ProposalApprovalStep.objects
            .filter(approver=request.user, status='pending')
            .annotate(
                current_pending_level=Min(
                    'proposal__approval_steps__level',
                    filter=Q(proposal__approval_steps__status='pending'),
                )
            )
            .filter(level=F('current_pending_level'))
            .select_related('proposal', 'proposal__customer')
            .order_by('-proposal__approval_submitted_at', '-created_at')
        )
        serializer = ProposalApprovalInboxSerializer(steps, many=True, context={'request': request})
        return Response(serializer.data)

    def _proposal_decision(self, request, proposal, approved):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        current_step = proposal.get_current_pending_step()
        step = (
            ProposalApprovalStep.objects
            .filter(proposal=proposal, approver=request.user, status='pending')
            .order_by('level')
            .first()
        )

        if not step:
            return Response(
                {'detail': 'No pending approval step assigned to you.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not current_step or current_step.id != step.id:
            waiting_label = f'Level {current_step.level}' if current_step else 'the current approval level'
            waiting_name = (
                current_step.approver.get_full_name() or current_step.approver.username
                if current_step and current_step.approver else 'the assigned approver'
            )
            return Response(
                {'detail': f'Approval order is enforced. Please wait for {waiting_label} ({waiting_name}) first.'},
                status=status.HTTP_409_CONFLICT,
            )

        step.status = 'approved' if approved else 'rejected'
        step.decided_at = timezone.now()
        step.comment = serializer.validated_data.get('comment', '')
        step.save(update_fields=['status', 'decided_at', 'comment'])

        if approved:
            next_step = ProposalApprovalStep.objects.filter(proposal=proposal, status='pending').order_by('level').first()
            if not next_step:
                proposal.approval_status = 'approved'
                proposal.approved_at = timezone.now()
                proposal.save(update_fields=['approval_status', 'approved_at'])
                detail = 'Proposal fully approved.'
            else:
                detail = 'Step approved. Awaiting next approver.'
        else:
            proposal.approval_status = 'rejected'
            proposal.save(update_fields=['approval_status'])
            detail = 'Proposal rejected.'

        proposal.refresh_from_db()
        return Response({
            'detail': detail,
            'proposal': ProposalDetailSerializer(proposal, context={'request': request}).data,
        })

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        proposal = self.get_object()
        return self._proposal_decision(request, proposal, approved=True)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        proposal = self.get_object()
        return self._proposal_decision(request, proposal, approved=False)


class SalesActivityViewSet(viewsets.ModelViewSet):
    queryset = SalesActivity.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return (
            get_visible_activity_queryset(self.request.user)
            .select_related(
                'activity_type',
                'customer',
                'salesperson',
                'call_details',
                'meeting_details',
                'email_details',
                'proposal_details',
                'task_details',
            )
            .prefetch_related('logs__changed_by')
            .order_by('-scheduled_start', '-created_at')
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return SalesActivityCreateSerializer
        if self.action == 'retrieve':
            return SalesActivityDetailSerializer
        return SalesActivityListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        activity = serializer.save()
        return Response(
            SalesActivityDetailSerializer(activity, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Campaign.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return (
            get_allowed_campaigns(self.request.user)
            .select_related('created_by')
            .prefetch_related('recipients')
            .order_by('-created_at')
        )

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CampaignDetailSerializer
        return CampaignListSerializer

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        campaign = self.get_object()
        sample_recipient = campaign.recipients.first()
        if sample_recipient:
            context_dict = get_recipient_context(sample_recipient)
        else:
            context_dict = {
                'contact_name': 'John Doe',
                'company_name': 'Sample Company Inc.',
            }

        rendered_body = render_campaign_html(campaign, context_dict, preview=True)
        return Response({
            'campaign_id': campaign.id,
            'subject': campaign.subject,
            'rendered_body': rendered_body,
        })

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        campaign = self.get_object()
        if campaign.status != 'draft':
            return Response(
                {'detail': 'This campaign is already scheduled or sending.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        campaign.status = 'scheduled'
        if not campaign.scheduled_for:
            campaign.scheduled_for = timezone.now()
        campaign.save(update_fields=['status', 'scheduled_for'])

        def run_worker():
            try:
                campaign.refresh_from_db()
                if campaign.status == 'cancelled':
                    return
                now = timezone.now()
                if campaign.scheduled_for and campaign.scheduled_for > now:
                    import time
                    time.sleep((campaign.scheduled_for - now).total_seconds())
                call_command('process_mail_queue')
            except Exception:
                return

        threading.Thread(target=run_worker, daemon=True).start()

        return Response({
            'detail': 'Campaign has been queued for sending.',
            'campaign': CampaignDetailSerializer(campaign, context={'request': request}).data,
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        campaign = self.get_object()
        if campaign.status in ['completed', 'cancelled']:
            return Response(
                {'detail': 'This campaign cannot be cancelled anymore.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if campaign.status == 'draft':
            campaign_id = campaign.id
            campaign.delete()
            return Response({
                'detail': 'Draft campaign deleted successfully.',
                'campaign_id': campaign_id,
                'deleted': True,
            })

        campaign.status = 'cancelled'
        campaign.save(update_fields=['status'])
        return Response({
            'detail': 'Campaign has been cancelled. No further emails will be sent.',
            'campaign': CampaignDetailSerializer(campaign, context={'request': request}).data,
        })
