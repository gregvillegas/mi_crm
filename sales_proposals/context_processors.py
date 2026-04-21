from django.db.models import F, Min, Q
from django.urls import reverse

from .models import ProposalApprovalStep


def proposal_approval_notifications(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {
            'proposal_approval_notifications': [],
            'proposal_approval_notification_count': 0,
        }

    base_qs = (
        ProposalApprovalStep.objects
        .filter(approver=request.user, status='pending')
        .annotate(
            current_pending_level=Min(
                'proposal__approval_steps__level',
                filter=Q(proposal__approval_steps__status='pending')
            )
        )
        .filter(level=F('current_pending_level'))
        .select_related('proposal', 'proposal__customer')
        .order_by('-proposal__approval_submitted_at', '-created_at')
    )

    notifications = []
    for step in base_qs[:5]:
        notifications.append({
            'type': 'proposal_approval',
            'title': step.proposal.proposal_number,
            'message': (
                f"Level {step.level} approval pending for "
                f"{step.proposal.customer.company_name}"
            ),
            'url': reverse('proposal_detail', kwargs={'pk': step.proposal.pk}),
            'status': step.status,
            'timestamp': step.proposal.approval_submitted_at or step.created_at,
        })

    return {
        'proposal_approval_notifications': notifications,
        'proposal_approval_notification_count': base_qs.count(),
    }
