from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from customers.models import (
    Customer,
    CustomerContact,
    CustomerCreateRequest,
    CustomerHistory,
)
from mass_mailing.models import Campaign, CampaignRecipient
from sales_funnel.models import SalesFunnel
from sales_monitoring.models import (
    ActivityLog,
    ActivityType,
    CallActivity,
    EmailActivity,
    MeetingActivity,
    ProposalActivity,
    SalesActivity,
    TaskActivity,
)
from sales_proposals.models import (
    Proposal,
    ProposalApprovalStep,
    ProposalChangeLog,
    ProposalItem,
)
from teams.models import Group, Team, TeamMembership
from users.models import User


EXEC_ROLES = {'admin', 'president', 'gm', 'vp'}
MANAGER_ROLES = EXEC_ROLES | {'avp', 'asm', 'supervisor', 'teamlead'}


def get_visible_customer_queryset(user):
    if user.role in EXEC_ROLES or user.role == 'avp':
        return Customer.objects.all()
    if user.role == 'salesperson':
        return Customer.objects.filter(salesperson=user)
    if user.role == 'supervisor':
        groups = Group.objects.filter(supervisor=user)
        salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        return Customer.objects.filter(Q(salesperson_id__in=salesperson_ids) | Q(salesperson=user))
    if user.role == 'teamlead':
        groups = Group.objects.filter(teamlead=user)
        salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        return Customer.objects.filter(Q(salesperson_id__in=salesperson_ids) | Q(salesperson=user))
    if user.role == 'asm':
        groups = Group.objects.filter(team__in=user.asm_teams.all())
        salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        return Customer.objects.filter(Q(salesperson_id__in=salesperson_ids) | Q(salesperson=user))
    return Customer.objects.none()


def get_visible_proposal_queryset(user):
    if user.role in EXEC_ROLES:
        return Proposal.objects.all()
    if user.role == 'salesperson':
        return Proposal.objects.filter(created_by=user)
    if user.role == 'supervisor':
        managed_groups = user.managed_groups.all()
        member_ids = []
        for group in managed_groups:
            member_ids.extend(group.members.values_list('user_id', flat=True))
        member_ids.append(user.id)
        return Proposal.objects.filter(created_by_id__in=member_ids)
    if user.role == 'teamlead':
        led_groups = user.led_groups.all()
        member_ids = []
        for group in led_groups:
            member_ids.extend(group.members.values_list('user_id', flat=True))
        member_ids.append(user.id)
        return Proposal.objects.filter(created_by_id__in=member_ids)
    if user.role == 'asm':
        member_ids = []
        for team in user.asm_teams.all():
            for group in team.groups.all():
                member_ids.extend(group.members.values_list('user_id', flat=True))
                if group.supervisor:
                    member_ids.append(group.supervisor.id)
        member_ids.append(user.id)
        return Proposal.objects.filter(created_by_id__in=member_ids)
    if user.role == 'avp':
        member_ids = []
        for team in Team.objects.filter(avp=user):
            for group in team.groups.all():
                member_ids.extend(group.members.values_list('user_id', flat=True))
                if group.supervisor:
                    member_ids.append(group.supervisor.id)
        member_ids.append(user.id)
        return Proposal.objects.filter(created_by_id__in=member_ids)
    return Proposal.objects.none()


def get_visible_activity_queryset(user):
    if user.role in EXEC_ROLES or user.role == 'avp':
        return SalesActivity.objects.all()
    if user.role == 'salesperson':
        return SalesActivity.objects.filter(salesperson=user)
    if user.role == 'supervisor':
        groups = user.managed_groups.all()
        salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        return SalesActivity.objects.filter(salesperson_id__in=salesperson_ids)
    if user.role == 'teamlead':
        groups = user.led_groups.all()
        salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        return SalesActivity.objects.filter(salesperson_id__in=salesperson_ids)
    if user.role == 'asm':
        groups = Group.objects.filter(team__in=user.asm_teams.all())
        salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        return SalesActivity.objects.filter(salesperson_id__in=salesperson_ids)
    return SalesActivity.objects.none()


def get_assignable_salespeople_queryset(user):
    if user.role in EXEC_ROLES:
        return User.objects.filter(role='salesperson', is_active=True)
    if user.role == 'supervisor':
        groups = user.managed_groups.all()
        salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        return User.objects.filter(id__in=salesperson_ids, is_active=True)
    if user.role == 'teamlead':
        groups = user.led_groups.all()
        salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        return User.objects.filter(id__in=salesperson_ids, is_active=True)
    if user.role == 'asm':
        groups = Group.objects.filter(team__in=user.asm_teams.all())
        salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        return User.objects.filter(id__in=salesperson_ids, is_active=True)
    if user.role == 'avp':
        groups = Group.objects.filter(team__in=Team.objects.filter(avp=user))
        salesperson_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        return User.objects.filter(id__in=salesperson_ids, is_active=True)
    return User.objects.none()


class CustomerContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerContact
        fields = ['id', 'name', 'position', 'email', 'phone', 'is_primary']


class CustomerListSerializer(serializers.ModelSerializer):
    salesperson_name = serializers.SerializerMethodField()
    salesperson_initials = serializers.SerializerMethodField()
    display_status = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id',
            'company_name',
            'contact_person_name',
            'contact_person_position',
            'email',
            'phone_number',
            'industry',
            'territory',
            'display_status',
            'is_active',
            'auto_inactive_flag',
            'is_millionaire_account',
            'salesperson_name',
            'salesperson_initials',
            'created_at',
        ]

    def get_salesperson_name(self, obj):
        if not obj.salesperson:
            return None
        return obj.salesperson.get_full_name() or obj.salesperson.username

    def get_salesperson_initials(self, obj):
        if not obj.salesperson:
            return None
        return obj.salesperson.initials or obj.salesperson.username[:3].upper()


class CustomerDetailSerializer(CustomerListSerializer):
    contacts = CustomerContactSerializer(many=True, read_only=True)

    class Meta(CustomerListSerializer.Meta):
        fields = CustomerListSerializer.Meta.fields + [
            'address',
            'salesperson',
            'contacts',
            'updated_at',
        ]


class CustomerDirectCreateSerializer(serializers.ModelSerializer):
    contacts = CustomerContactSerializer(many=True, required=False)

    class Meta:
        model = Customer
        fields = [
            'company_name',
            'contact_person_name',
            'contact_person_position',
            'email',
            'phone_number',
            'address',
            'industry',
            'territory',
            'is_active',
            'salesperson',
            'contacts',
        ]

    def create(self, validated_data):
        contacts_data = validated_data.pop('contacts', [])
        request = self.context['request']

        with transaction.atomic():
            customer = Customer.objects.create(
                is_vip=False,
                is_millionaire_account=False,
                **validated_data,
            )
            for contact_data in contacts_data[:4]:
                CustomerContact.objects.create(customer=customer, **contact_data)

            CustomerHistory.log_customer_change(
                customer=customer,
                action='created',
                description='Customer created via Android API',
                changed_by=request.user,
            )
        return customer


class CustomerCreateRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerCreateRequest
        fields = [
            'id',
            'company_name',
            'contact_person_name',
            'contact_person_position',
            'email',
            'phone_number',
            'address',
            'industry',
            'territory',
            'status',
            'similar_matches',
            'decision_notes',
            'requested_by',
            'requested_by_name',
            'reviewed_by',
            'reviewed_by_name',
            'created_at',
            'reviewed_at',
        ]
        read_only_fields = [
            'status',
            'similar_matches',
            'requested_by',
            'requested_by_name',
            'reviewed_by',
            'reviewed_by_name',
            'created_at',
            'reviewed_at',
        ]

    def get_requested_by_name(self, obj):
        if not obj.requested_by:
            return None
        return obj.requested_by.get_full_name() or obj.requested_by.username

    def get_reviewed_by_name(self, obj):
        if not obj.reviewed_by:
            return None
        return obj.reviewed_by.get_full_name() or obj.reviewed_by.username

    def create(self, validated_data):
        from customers.views import _find_similar_customers

        request = self.context['request']
        validated_data['requested_by'] = request.user
        validated_data['similar_matches'] = _find_similar_customers(validated_data.get('company_name', ''))
        return CustomerCreateRequest.objects.create(**validated_data)


class SalesFunnelSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    customer_name = serializers.CharField(source='customer.company_name', read_only=True, allow_null=True, default='Unknown')

    class Meta:
        model = SalesFunnel
        fields = [
            'id',
            'company_name',
            'requirement_description',
            'cost',
            'retail',
            'stage',
            'stage_display',
            'expected_close_date',
            'probability',
            'customer_name',
            'created_at',
        ]


class ProposalItemSerializer(serializers.ModelSerializer):
    bundle_components = serializers.SerializerMethodField()

    class Meta:
        model = ProposalItem
        fields = [
            'id',
            'part_number',
            'description',
            'quantity',
            'unit_cost',
            'unit_price',
            'availability',
            'warranty',
            'is_optional',
            'is_bundle',
            'bundled_items',
            'bundle_components',
            'amount',
            'total_cost',
        ]

    def get_bundle_components(self, obj):
        return obj.bundle_components


class ProposalApprovalStepSerializer(serializers.ModelSerializer):
    approver_name = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = ProposalApprovalStep
        fields = [
            'id',
            'level',
            'approver',
            'approver_name',
            'status',
            'comment',
            'decided_at',
            'is_current',
        ]

    def get_approver_name(self, obj):
        if not obj.approver:
            return None
        return obj.approver.get_full_name() or obj.approver.username

    def get_is_current(self, obj):
        current_step = obj.proposal.get_current_pending_step()
        return bool(current_step and current_step.id == obj.id)


class ProposalListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    customer_name = serializers.CharField(source='customer.company_name', read_only=True)
    next_approver_name = serializers.SerializerMethodField()
    current_pending_level = serializers.SerializerMethodField()

    class Meta:
        model = Proposal
        fields = [
            'id',
            'proposal_number',
            'reference_number',
            'subject',
            'customer_name',
            'date',
            'total_amount',
            'currency',
            'status',
            'status_display',
            'approval_status',
            'approval_required',
            'current_pending_level',
            'next_approver_name',
            'created_at',
        ]

    def get_next_approver_name(self, obj):
        step = obj.get_current_pending_step()
        if not step or not step.approver:
            return None
        return step.approver.get_full_name() or step.approver.username

    def get_current_pending_level(self, obj):
        step = obj.get_current_pending_step()
        return step.level if step else None


class ProposalDetailSerializer(ProposalListSerializer):
    customer = CustomerListSerializer(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    items = ProposalItemSerializer(many=True, read_only=True)
    approval_steps = ProposalApprovalStepSerializer(many=True, read_only=True)
    can_current_user_approve = serializers.SerializerMethodField()
    internal_cost_with_uplift = serializers.DecimalField(max_digits=14, decimal_places=4, read_only=True)
    target_subtotal_before_tax = serializers.DecimalField(max_digits=14, decimal_places=6, read_only=True)
    target_gross_profit = serializers.DecimalField(max_digits=14, decimal_places=6, read_only=True)

    class Meta(ProposalListSerializer.Meta):
        fields = ProposalListSerializer.Meta.fields + [
            'customer',
            'created_by',
            'created_by_name',
            'valid_until',
            'stock_availability',
            'contact_name',
            'contact_email',
            'contact_phone',
            'payment_terms',
            'delivery_lead_time',
            'warranty',
            'special_note',
            'introduction',
            'closing',
            'subtotal',
            'has_optional_items',
            'tax_type',
            'tax_rate',
            'tax_amount',
            'total_cost',
            'gross_profit',
            'sales_margin_pct',
            'internal_cost_with_uplift',
            'target_subtotal_before_tax',
            'target_gross_profit',
            'items',
            'approval_steps',
            'can_current_user_approve',
            'updated_at',
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_can_current_user_approve(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        return obj.can_user_decide_current_step(request.user)


class ProposalCreateItemSerializer(serializers.Serializer):
    part_number = serializers.CharField(required=False, allow_blank=True, max_length=100)
    description = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    availability = serializers.CharField(required=False, allow_blank=True, max_length=100)
    warranty = serializers.CharField(required=False, allow_blank=True, max_length=150)
    is_optional = serializers.BooleanField(required=False, default=False)


class ProposalCreateSerializer(serializers.ModelSerializer):
    items = ProposalCreateItemSerializer(many=True)

    class Meta:
        model = Proposal
        fields = [
            'customer',
            'contact_name',
            'contact_email',
            'contact_phone',
            'subject',
            'currency',
            'exchange_rate',
            'date',
            'valid_until',
            'stock_availability',
            'payment_terms',
            'delivery_lead_time',
            'cancellation_terms',
            'include_bank_details',
            'introduction',
            'special_note',
            'closing',
            'tax_type',
            'tax_rate',
            'sales_margin_pct',
            'items',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            self.fields['customer'].queryset = get_visible_customer_queryset(request.user).filter(is_active=True)

    def validate(self, attrs):
        items = attrs.get('items') or []
        if not items:
            raise serializers.ValidationError({'items': 'At least one proposal item is required.'})
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        items_data = validated_data.pop('items', [])
        customer = validated_data['customer']

        if not validated_data.get('contact_name'):
            validated_data['contact_name'] = customer.contact_person_name
        if not validated_data.get('contact_email'):
            validated_data['contact_email'] = customer.email
        if not validated_data.get('contact_phone'):
            validated_data['contact_phone'] = customer.phone_number

        from sales_proposals.views import update_sales_funnel

        with transaction.atomic():
            proposal = Proposal.objects.create(created_by=request.user, **validated_data)
            for item_data in items_data:
                ProposalItem.objects.create(proposal=proposal, **item_data)
            proposal.calculate_totals()
            proposal.ensure_approval_chain()
            update_sales_funnel(proposal)
            ProposalChangeLog.objects.create(
                proposal=proposal,
                changed_by=request.user,
                summary='Proposal created via Android API',
            )
        return proposal


class ProposalApprovalDecisionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)


class ProposalApprovalInboxSerializer(serializers.ModelSerializer):
    proposal_id = serializers.IntegerField(source='proposal.id', read_only=True)
    proposal_number = serializers.CharField(source='proposal.proposal_number', read_only=True)
    customer_name = serializers.CharField(source='proposal.customer.company_name', read_only=True)
    subject = serializers.CharField(source='proposal.subject', read_only=True)
    total_amount = serializers.DecimalField(source='proposal.total_amount', max_digits=12, decimal_places=2, read_only=True)
    currency = serializers.CharField(source='proposal.currency', read_only=True)
    approval_submitted_at = serializers.DateTimeField(source='proposal.approval_submitted_at', read_only=True)

    class Meta:
        model = ProposalApprovalStep
        fields = [
            'id',
            'proposal_id',
            'proposal_number',
            'customer_name',
            'subject',
            'total_amount',
            'currency',
            'level',
            'status',
            'approval_submitted_at',
        ]


class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
        fields = ['id', 'name', 'icon', 'color']


class CallActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CallActivity
        fields = ['phone_number', 'call_type', 'call_outcome']


class MeetingActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingActivity
        fields = ['meeting_type', 'location', 'attendees', 'meeting_outcome']


class EmailActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailActivity
        fields = ['email_type', 'subject', 'recipients', 'has_attachments', 'email_opened', 'email_responded']


class ProposalActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProposalActivity
        fields = ['proposal_title', 'proposal_value', 'currency', 'proposal_status', 'expected_decision_date', 'win_probability']


class TaskActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskActivity
        fields = ['task_category', 'estimated_hours', 'actual_hours']


class ActivityLogSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['id', 'action', 'action_display', 'description', 'changed_by_name', 'timestamp']

    def get_changed_by_name(self, obj):
        if not obj.changed_by:
            return None
        return obj.changed_by.get_full_name() or obj.changed_by.username


class SalesActivityListSerializer(serializers.ModelSerializer):
    activity_type_details = ActivityTypeSerializer(source='activity_type', read_only=True)
    customer_name = serializers.CharField(source='customer.company_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SalesActivity
        fields = [
            'id',
            'title',
            'description',
            'activity_type',
            'activity_type_details',
            'customer_name',
            'status',
            'status_display',
            'priority',
            'scheduled_start',
            'scheduled_end',
            'actual_start',
            'actual_end',
            'created_at',
        ]


class SalesActivityDetailSerializer(SalesActivityListSerializer):
    customer = CustomerListSerializer(read_only=True)
    salesperson_name = serializers.SerializerMethodField()
    call_details = CallActivitySerializer(read_only=True)
    meeting_details = MeetingActivitySerializer(read_only=True)
    email_details = EmailActivitySerializer(read_only=True)
    proposal_details = ProposalActivitySerializer(read_only=True)
    task_details = TaskActivitySerializer(read_only=True)
    logs = ActivityLogSerializer(many=True, read_only=True)

    class Meta(SalesActivityListSerializer.Meta):
        fields = SalesActivityListSerializer.Meta.fields + [
            'customer',
            'salesperson',
            'salesperson_name',
            'notes',
            'follow_up_required',
            'follow_up_date',
            'reviewed_by_supervisor',
            'supervisor_notes',
            'supervisor_reviewed_at',
            'engineer_required',
            'call_details',
            'meeting_details',
            'email_details',
            'proposal_details',
            'task_details',
            'logs',
            'updated_at',
        ]

    def get_salesperson_name(self, obj):
        return obj.salesperson.get_full_name() or obj.salesperson.username


class SalesActivityCreateSerializer(serializers.ModelSerializer):
    salesperson = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='salesperson', is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SalesActivity
        fields = [
            'title',
            'description',
            'activity_type',
            'customer',
            'salesperson',
            'status',
            'priority',
            'scheduled_start',
            'scheduled_end',
            'notes',
            'follow_up_required',
            'follow_up_date',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request:
            self.fields['customer'].queryset = get_visible_customer_queryset(request.user)
            self.fields['salesperson'].queryset = get_assignable_salespeople_queryset(request.user)

    def validate(self, attrs):
        request = self.context['request']
        user = request.user
        scheduled_start = attrs.get('scheduled_start')
        scheduled_end = attrs.get('scheduled_end')
        follow_up_required = attrs.get('follow_up_required')
        follow_up_date = attrs.get('follow_up_date')
        activity_type = attrs.get('activity_type')
        customer = attrs.get('customer')
        selected_salesperson = attrs.get('salesperson')

        if scheduled_start and scheduled_end and scheduled_end <= scheduled_start:
            raise serializers.ValidationError({'scheduled_end': 'End time must be after start time.'})

        if follow_up_required and not follow_up_date:
            raise serializers.ValidationError({'follow_up_date': 'Follow-up date is required when follow-up is marked as required.'})

        if activity_type and activity_type.requires_customer and not customer:
            raise serializers.ValidationError({'customer': f'Customer is required for {activity_type.name} activities.'})

        if user.role == 'salesperson':
            attrs['resolved_salesperson'] = user
        else:
            if customer and customer.salesperson:
                attrs['resolved_salesperson'] = customer.salesperson
            elif selected_salesperson:
                attrs['resolved_salesperson'] = selected_salesperson
            else:
                raise serializers.ValidationError({'salesperson': 'Select a salesperson, or assign the customer to a salesperson first.'})

        return attrs

    def create(self, validated_data):
        request = self.context['request']
        salesperson = validated_data.pop('resolved_salesperson')
        validated_data.pop('salesperson', None)
        activity = SalesActivity.objects.create(salesperson=salesperson, **validated_data)

        if activity.customer and (not activity.customer.is_active or activity.customer.auto_inactive_flag):
            reactivated_fields = []
            if not activity.customer.is_active:
                activity.customer.is_active = True
                reactivated_fields.append('is_active')
            if activity.customer.auto_inactive_flag:
                activity.customer.auto_inactive_flag = False
                reactivated_fields.append('auto_inactive_flag')
            if reactivated_fields:
                activity.customer.save(update_fields=reactivated_fields)

        ActivityLog.log_activity_change(
            activity=activity,
            action='created',
            description=f'Activity "{activity.title}" was created',
            changed_by=request.user,
        )
        return activity


class CampaignRecipientSerializer(serializers.ModelSerializer):
    display_company_name = serializers.CharField(read_only=True)
    display_contact_name = serializers.CharField(read_only=True)

    class Meta:
        model = CampaignRecipient
        fields = [
            'id',
            'source_type',
            'display_company_name',
            'display_contact_name',
            'email',
            'position',
            'status',
            'sent_at',
            'error_message',
        ]


class CampaignListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id',
            'name',
            'subject',
            'status',
            'recipient_mode',
            'template_type',
            'total_recipients',
            'sent_count',
            'failed_count',
            'scheduled_for',
            'created_at',
            'created_by_name',
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() or obj.created_by.username


class CampaignDetailSerializer(CampaignListSerializer):
    recipients = CampaignRecipientSerializer(many=True, read_only=True)

    class Meta(CampaignListSerializer.Meta):
        fields = CampaignListSerializer.Meta.fields + [
            'body_html',
            'hero_headline',
            'hero_intro',
            'hero_bullet_1',
            'hero_bullet_2',
            'hero_bullet_3',
            'hero_cta_label',
            'hero_cta_url',
            'include_unsubscribe',
            'recipients',
        ]


CustomerSerializer = CustomerListSerializer
ProposalSerializer = ProposalListSerializer
SalesActivitySerializer = SalesActivityListSerializer
