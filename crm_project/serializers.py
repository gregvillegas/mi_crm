from rest_framework import serializers
from sales_funnel.models import SalesFunnel
from sales_proposals.models import Proposal
from sales_monitoring.models import SalesActivity, ActivityType
from users.models import User
from customers.models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'company_name', 'contact_person', 'email', 'mobile_number']

class SalesFunnelSerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source='get_stage_display', read_only=True)
    customer_name = serializers.CharField(source='customer.company_name', read_only=True, allow_null=True, default="Unknown")
    
    class Meta:
        model = SalesFunnel
        fields = ['id', 'company_name', 'requirement_description', 'cost', 'retail', 
                  'stage', 'stage_display', 'expected_close_date', 'probability', 
                  'customer_name', 'created_at']

class ProposalSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    customer_name = serializers.CharField(source='customer.company_name', read_only=True)
    
    class Meta:
        model = Proposal
        fields = ['id', 'proposal_number', 'subject', 'customer_name', 'date', 
                  'total_amount', 'status', 'status_display', 'currency', 'created_at']

class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
        fields = ['id', 'name', 'icon', 'color']

class SalesActivitySerializer(serializers.ModelSerializer):
    activity_type_details = ActivityTypeSerializer(source='activity_type', read_only=True)
    customer_name = serializers.CharField(source='customer.company_name', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SalesActivity
        fields = ['id', 'title', 'description', 'activity_type', 'activity_type_details',
                  'customer_name', 'status', 'status_display', 'priority', 
                  'scheduled_start', 'scheduled_end', 'actual_start', 'actual_end',
                  'created_at']
