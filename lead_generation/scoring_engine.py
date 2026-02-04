from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import math
import json
from .models import Lead, LeadActivity
from .scoring_models import (
    ScoringCriteria, ScoringRule, LeadScoringProfile, 
    ActivityScoringRule, LeadScoreHistory, ScoringAlert, ProfileCriteria
)

class LeadScoringEngine:
    """Advanced lead scoring engine with configurable rules"""
    
    def __init__(self, profile=None):
        """Initialize with a specific scoring profile"""
        self.profile = profile or LeadScoringProfile.objects.filter(
            is_default=True, is_active=True
        ).first()
        
        if not self.profile:
            # Create default profile if none exists
            self.profile = self._create_default_profile()
    
    def calculate_lead_score(self, lead, save_history=True):
        """Calculate comprehensive lead score using all active criteria"""
        
        score_breakdown = {
            'demographic': 0,
            'firmographic': 0,
            'behavioral': 0,
            'engagement': 0,
            'source': 0,
            'temporal': 0,
            'total': 0,
            'details': {}
        }
        
        # Get active criteria for this profile
        criteria_list = self.profile.criteria.filter(is_active=True)
        
        for criteria in criteria_list:
            criteria_score = self._evaluate_criteria(lead, criteria)
            score_breakdown[criteria.criteria_type] += criteria_score
            score_breakdown['details'][criteria.name] = criteria_score
        
        # Calculate total score
        total_score = sum([
            score_breakdown['demographic'],
            score_breakdown['firmographic'], 
            score_breakdown['behavioral'],
            score_breakdown['engagement'],
            score_breakdown['source'],
            score_breakdown['temporal']
        ])
        
        # Ensure score is within bounds (0-100)
        total_score = max(0, min(100, total_score))
        score_breakdown['total'] = total_score
        
        # Update lead score
        old_score = lead.lead_score
        lead.lead_score = total_score
        lead.save(update_fields=['lead_score'])
        
        # Save score history
        if save_history:
            self._save_score_history(lead, score_breakdown, old_score)
        
        # Check for scoring alerts
        self._check_scoring_alerts(lead, old_score, total_score)
        
        return score_breakdown
    
    def _evaluate_criteria(self, lead, criteria):
        """Evaluate a specific scoring criteria against a lead"""
        total_points = 0
        
        # Get all active rules for this criteria
        rules = criteria.rules.filter(is_active=True).order_by('order')
        
        for rule in rules:
            points = rule.evaluate_lead(lead)
            total_points += points
        
        # Apply criteria weight
        weighted_score = total_points * float(criteria.weight)
        
        # Ensure doesn't exceed max score for this criteria
        return min(weighted_score, criteria.max_score)
    
    def calculate_behavioral_score(self, lead):
        """Calculate behavioral score based on activities with time decay"""
        
        activities = lead.activities.all()
        behavioral_score = 0
        now = timezone.now()
        
        # Get activity scoring rules
        activity_rules = ActivityScoringRule.objects.filter(is_active=True)
        
        for activity in activities:
            # Find matching scoring rules
            from django.db import models
            matching_rules = activity_rules.filter(
                models.Q(activity_type='') | models.Q(activity_type=activity.activity_type),
                models.Q(outcome='') | models.Q(outcome=activity.outcome)
            )
            
            for rule in matching_rules:
                # Calculate base points
                points = rule.points_per_activity
                
                # Apply time decay if configured
                days_old = (now - activity.created_at).days
                if days_old > rule.decay_days:
                    decay_factor = math.exp(-rule.decay_rate * (days_old - rule.decay_days))
                    points = int(points * decay_factor)
                
                behavioral_score += points
        
        return max(0, min(100, behavioral_score))
    
    def calculate_engagement_score(self, lead):
        """Calculate engagement score based on recency and frequency"""
        
        activities = lead.activities.all()
        if not activities.exists():
            return 0
        
        now = timezone.now()
        
        # Recency score (0-40 points)
        last_activity = activities.order_by('-created_at').first()
        days_since_last = (now - last_activity.created_at).days
        
        if days_since_last <= 1:
            recency_score = 40
        elif days_since_last <= 3:
            recency_score = 30
        elif days_since_last <= 7:
            recency_score = 20
        elif days_since_last <= 14:
            recency_score = 10
        else:
            recency_score = 0
        
        # Frequency score (0-30 points)
        thirty_days_ago = now - timedelta(days=30)
        recent_activities = activities.filter(created_at__gte=thirty_days_ago)
        activity_count = recent_activities.count()
        
        if activity_count >= 10:
            frequency_score = 30
        elif activity_count >= 5:
            frequency_score = 20
        elif activity_count >= 2:
            frequency_score = 10
        else:
            frequency_score = 0
        
        # Engagement quality score (0-30 points)
        positive_outcomes = recent_activities.filter(
            outcome__in=['interested', 'meeting_scheduled', 'proposal_requested']
        ).count()
        
        quality_score = min(30, positive_outcomes * 10)
        
        return recency_score + frequency_score + quality_score
    
    def _save_score_history(self, lead, score_breakdown, old_score):
        """Save lead score change to history"""
        
        score_change = score_breakdown['total'] - old_score
        
        LeadScoreHistory.objects.create(
            lead=lead,
            total_score=score_breakdown['total'],
            demographic_score=score_breakdown['demographic'],
            firmographic_score=score_breakdown['firmographic'],
            behavioral_score=score_breakdown['behavioral'],
            engagement_score=score_breakdown['engagement'],
            source_score=score_breakdown['source'],
            temporal_score=score_breakdown['temporal'],
            scoring_profile=self.profile,
            calculation_details=score_breakdown['details'],
            score_change=score_change,
            change_reason="Automated scoring calculation"
        )
    
    def _check_scoring_alerts(self, lead, old_score, new_score):
        """Check if scoring alerts should be triggered"""
        
        # Hot lead alert
        if new_score >= self.profile.hot_lead_threshold and old_score < self.profile.hot_lead_threshold:
            ScoringAlert.objects.create(
                lead=lead,
                alert_type='hot_lead',
                priority='high',
                title=f"🔥 Hot Lead Alert: {lead.full_name}",
                message=f"Lead score reached {new_score} (threshold: {self.profile.hot_lead_threshold})",
                threshold_value=self.profile.hot_lead_threshold,
                current_score=new_score,
                assigned_to=lead.assigned_to,
                notify_supervisors=True
            )
        
        # Significant score increase
        score_increase = new_score - old_score
        if score_increase >= 20:
            ScoringAlert.objects.create(
                lead=lead,
                alert_type='score_increase',
                priority='medium',
                title=f"📈 Score Increase: {lead.full_name}",
                message=f"Lead score increased by {score_increase} points to {new_score}",
                current_score=new_score,
                assigned_to=lead.assigned_to
            )
        
        # Assignment needed alert
        if new_score >= self.profile.auto_assign_threshold and not lead.assigned_to:
            ScoringAlert.objects.create(
                lead=lead,
                alert_type='assignment_needed',
                priority='high',
                title=f"🎯 Assignment Needed: {lead.full_name}",
                message=f"High-scoring lead ({new_score} points) needs salesperson assignment",
                threshold_value=self.profile.auto_assign_threshold,
                current_score=new_score,
                notify_supervisors=True
            )
    
    def _create_default_profile(self):
        """Create a default scoring profile with standard criteria"""
        
        with transaction.atomic():
            # Create default profile
            profile = LeadScoringProfile.objects.create(
                name="Default Lead Scoring",
                description="Default lead scoring profile with standard criteria",
                is_default=True,
                auto_assign_threshold=80,
                hot_lead_threshold=75
            )
            
            # Create default criteria
            criteria_data = [
                {
                    'name': 'Company Size',
                    'criteria_type': 'firmographic',
                    'description': 'Score based on company size',
                    'weight': 1.5,
                    'max_score': 25
                },
                {
                    'name': 'Annual Revenue',
                    'criteria_type': 'firmographic', 
                    'description': 'Score based on annual revenue',
                    'weight': 2.0,
                    'max_score': 25
                },
                {
                    'name': 'Budget Range',
                    'criteria_type': 'demographic',
                    'description': 'Score based on budget range',
                    'weight': 2.0,
                    'max_score': 20
                },
                {
                    'name': 'Timeline Urgency',
                    'criteria_type': 'temporal',
                    'description': 'Score based on purchase timeline',
                    'weight': 1.5,
                    'max_score': 15
                },
                {
                    'name': 'Lead Source Quality',
                    'criteria_type': 'source',
                    'description': 'Score based on lead source effectiveness',
                    'weight': 1.0,
                    'max_score': 10
                },
                {
                    'name': 'Profile Completeness',
                    'criteria_type': 'demographic',
                    'description': 'Score based on profile information completeness',
                    'weight': 0.5,
                    'max_score': 5
                }
            ]
            
            for criteria_info in criteria_data:
                criteria = ScoringCriteria.objects.create(**criteria_info)
                
                # Associate with profile
                from .scoring_models import ProfileCriteria
                ProfileCriteria.objects.create(
                    profile=profile,
                    criteria=criteria,
                    weight_multiplier=1.0,
                    is_enabled=True
                )
            
            # Create default scoring rules
            self._create_default_rules()
            
            return profile
    
    def _create_default_rules(self):
        """Create default scoring rules"""
        
        # Get criteria
        company_size_criteria = ScoringCriteria.objects.get(name='Company Size')
        revenue_criteria = ScoringCriteria.objects.get(name='Annual Revenue')
        budget_criteria = ScoringCriteria.objects.get(name='Budget Range')
        timeline_criteria = ScoringCriteria.objects.get(name='Timeline Urgency')
        source_criteria = ScoringCriteria.objects.get(name='Lead Source Quality')
        completeness_criteria = ScoringCriteria.objects.get(name='Profile Completeness')
        
        # Company Size Rules
        company_size_rules = [
            {'field_name': 'company_size', 'operator': 'eq', 'value': '"1000+"', 'points': 25},
            {'field_name': 'company_size', 'operator': 'eq', 'value': '"501-1000"', 'points': 20},
            {'field_name': 'company_size', 'operator': 'eq', 'value': '"201-500"', 'points': 15},
            {'field_name': 'company_size', 'operator': 'eq', 'value': '"51-200"', 'points': 10},
            {'field_name': 'company_size', 'operator': 'eq', 'value': '"11-50"', 'points': 5},
        ]
        
        for rule_data in company_size_rules:
            ScoringRule.objects.create(
                criteria=company_size_criteria,
                **rule_data
            )
        
        # Annual Revenue Rules
        revenue_rules = [
            {'field_name': 'annual_revenue', 'operator': 'eq', 'value': '"over_100m"', 'points': 25},
            {'field_name': 'annual_revenue', 'operator': 'eq', 'value': '"50m_100m"', 'points': 20},
            {'field_name': 'annual_revenue', 'operator': 'eq', 'value': '"10m_50m"', 'points': 15},
            {'field_name': 'annual_revenue', 'operator': 'eq', 'value': '"5m_10m"', 'points': 10},
            {'field_name': 'annual_revenue', 'operator': 'eq', 'value': '"1m_5m"', 'points': 5},
        ]
        
        for rule_data in revenue_rules:
            ScoringRule.objects.create(
                criteria=revenue_criteria,
                **rule_data
            )
        
        # Budget Range Rules
        budget_rules = [
            {'field_name': 'budget_range', 'operator': 'eq', 'value': '"over_1m"', 'points': 20},
            {'field_name': 'budget_range', 'operator': 'eq', 'value': '"500k_1m"', 'points': 15},
            {'field_name': 'budget_range', 'operator': 'eq', 'value': '"100k_500k"', 'points': 12},
            {'field_name': 'budget_range', 'operator': 'eq', 'value': '"50k_100k"', 'points': 8},
            {'field_name': 'budget_range', 'operator': 'eq', 'value': '"10k_50k"', 'points': 5},
        ]
        
        for rule_data in budget_rules:
            ScoringRule.objects.create(
                criteria=budget_criteria,
                **rule_data
            )
        
        # Timeline Rules
        timeline_rules = [
            {'field_name': 'timeline', 'operator': 'eq', 'value': '"immediate"', 'points': 15},
            {'field_name': 'timeline', 'operator': 'eq', 'value': '"short_term"', 'points': 12},
            {'field_name': 'timeline', 'operator': 'eq', 'value': '"medium_term"', 'points': 8},
            {'field_name': 'timeline', 'operator': 'eq', 'value': '"long_term"', 'points': 4},
        ]
        
        for rule_data in timeline_rules:
            ScoringRule.objects.create(
                criteria=timeline_criteria,
                **rule_data
            )
        
        # Profile Completeness Rules
        completeness_rules = [
            {'field_name': 'phone_number', 'operator': 'is_not_null', 'value': '""', 'points': 1},
            {'field_name': 'company_name', 'operator': 'is_not_null', 'value': '""', 'points': 1},
            {'field_name': 'job_title', 'operator': 'is_not_null', 'value': '""', 'points': 1},
            {'field_name': 'industry', 'operator': 'is_not_null', 'value': '""', 'points': 1},
            {'field_name': 'territory', 'operator': 'is_not_null', 'value': '""', 'points': 1},
        ]
        
        for rule_data in completeness_rules:
            ScoringRule.objects.create(
                criteria=completeness_criteria,
                **rule_data
            )
        
        # Create default activity scoring rules
        activity_rules = [
            {
                'name': 'Successful Call',
                'activity_type': 'call',
                'outcome': 'successful',
                'points_per_activity': 10,
                'max_points_per_day': 30
            },
            {
                'name': 'Meeting Scheduled',
                'activity_type': '',
                'outcome': 'meeting_scheduled',
                'points_per_activity': 15,
                'max_points_per_day': 45
            },
            {
                'name': 'Showed Interest',
                'activity_type': '',
                'outcome': 'interested',
                'points_per_activity': 12,
                'max_points_per_day': 36
            },
            {
                'name': 'Proposal Requested',
                'activity_type': '',
                'outcome': 'proposal_requested',
                'points_per_activity': 20,
                'max_points_per_day': 60
            },
            {
                'name': 'Demo Conducted',
                'activity_type': 'demo',
                'outcome': 'successful',
                'points_per_activity': 18,
                'max_points_per_day': 54
            },
            {
                'name': 'Email Response',
                'activity_type': 'email',
                'outcome': 'interested',
                'points_per_activity': 8,
                'max_points_per_day': 24
            }
        ]
        
        for activity_rule in activity_rules:
            ActivityScoringRule.objects.create(**activity_rule)
    
    def bulk_recalculate_scores(self, lead_queryset=None):
        """Recalculate scores for multiple leads"""
        
        if lead_queryset is None:
            lead_queryset = Lead.objects.filter(is_active=True)
        
        updated_count = 0
        
        for lead in lead_queryset:
            try:
                self.calculate_lead_score(lead)
                updated_count += 1
            except Exception as e:
                print(f"Error calculating score for lead {lead.id}: {e}")
        
        return updated_count
    
    def get_score_explanation(self, lead):
        """Get detailed explanation of how a lead's score was calculated"""
        
        explanation = {
            'lead': lead,
            'total_score': lead.lead_score,
            'criteria_breakdown': [],
            'activity_impact': self.calculate_behavioral_score(lead),
            'engagement_impact': self.calculate_engagement_score(lead)
        }
        
        # Get criteria breakdown
        criteria_list = self.profile.criteria.filter(is_active=True)
        
        for criteria in criteria_list:
            criteria_score = self._evaluate_criteria(lead, criteria)
            
            # Get matching rules
            matching_rules = []
            for rule in criteria.rules.filter(is_active=True):
                points = rule.evaluate_lead(lead)
                if points > 0:
                    matching_rules.append({
                        'rule': rule,
                        'points': points
                    })
            
            explanation['criteria_breakdown'].append({
                'criteria': criteria,
                'score': criteria_score,
                'matching_rules': matching_rules
            })
        
        return explanation


class ScoringAutomation:
    """Automated scoring actions and triggers"""
    
    @classmethod
    def auto_assign_leads(cls, threshold_score=80):
        """Automatically assign high-scoring leads to available salespeople"""
        
        # Get unassigned high-scoring leads
        high_score_leads = Lead.objects.filter(
            assigned_to__isnull=True,
            lead_score__gte=threshold_score,
            is_active=True
        )
        
        # Get available salespeople (you might want to add workload balancing)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        available_salespeople = User.objects.filter(
            is_active=True
        )
        
        assigned_count = 0
        
        for lead in high_score_leads:
            if available_salespeople.exists():
                # Simple round-robin assignment (you can implement more sophisticated logic)
                salesperson = available_salespeople[assigned_count % available_salespeople.count()]
                
                lead.assigned_to = salesperson
                lead.save(update_fields=['assigned_to'])
                
                # Log assignment activity
                LeadActivity.objects.create(
                    lead=lead,
                    activity_type='note',
                    title='Auto-Assignment',
                    description=f'Automatically assigned to {salesperson.username} based on high lead score ({lead.lead_score})',
                    performed_by=None,
                    outcome='successful'
                )
                
                assigned_count += 1
        
        return assigned_count
    
    @classmethod
    def update_lead_priorities(cls):
        """Update lead priorities based on scores"""
        
        # Update priorities based on score ranges
        Lead.objects.filter(lead_score__gte=80, is_active=True).update(priority='hot')
        Lead.objects.filter(lead_score__range=(60, 79), is_active=True).update(priority='high')
        Lead.objects.filter(lead_score__range=(40, 59), is_active=True).update(priority='medium')
        Lead.objects.filter(lead_score__lt=40, is_active=True).update(priority='low')
        
        return True
    
    @classmethod
    def mark_qualified_leads(cls, threshold_score=70):
        """Automatically mark leads as qualified based on score"""
        
        qualified_count = Lead.objects.filter(
            lead_score__gte=threshold_score,
            is_qualified=False,
            is_active=True
        ).update(is_qualified=True)
        
        return qualified_count
    
    @classmethod
    def schedule_follow_ups(cls):
        """Schedule follow-ups for leads based on their scores and status"""
        
        from datetime import datetime, timedelta
        
        # Get leads that need follow-up scheduling
        leads_needing_followup = Lead.objects.filter(
            next_follow_up_date__isnull=True,
            status__in=['new', 'contacted'],
            is_active=True
        )
        
        updated_count = 0
        
        for lead in leads_needing_followup:
            # Calculate follow-up date based on score
            if lead.lead_score >= 80:  # Hot leads - 1 day
                follow_up_date = timezone.now() + timedelta(days=1)
            elif lead.lead_score >= 60:  # High priority - 3 days
                follow_up_date = timezone.now() + timedelta(days=3)
            elif lead.lead_score >= 40:  # Medium priority - 1 week
                follow_up_date = timezone.now() + timedelta(days=7)
            else:  # Low priority - 2 weeks
                follow_up_date = timezone.now() + timedelta(days=14)
            
            lead.next_follow_up_date = follow_up_date
            lead.save(update_fields=['next_follow_up_date'])
            updated_count += 1
        
        return updated_count
