from .models import CustomerCreateRequest


def customer_request_notifications(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}

    user = request.user
    pending_qs = CustomerCreateRequest.objects.none()
    requester_qs = CustomerCreateRequest.objects.none()

    if user.role in ['admin', 'avp', 'gm', 'vp']:
        pending_qs = CustomerCreateRequest.objects.filter(status='pending').select_related('requested_by')[:5]

    if user.role == 'salesperson':
        requester_qs = CustomerCreateRequest.objects.filter(
            requested_by=user,
            requester_seen_at__isnull=True
        ).exclude(status='pending').select_related('reviewed_by').order_by('-reviewed_at', '-created_at')[:5]

    pending_count = CustomerCreateRequest.objects.filter(status='pending').count() if user.role in ['admin', 'avp', 'gm', 'vp'] else 0
    requester_unread_count = CustomerCreateRequest.objects.filter(
        requested_by=user,
        requester_seen_at__isnull=True
    ).exclude(status='pending').count() if user.role == 'salesperson' else 0

    notifications = []
    for req in pending_qs:
        notifications.append({
            'type': 'pending_request',
            'title': req.company_name,
            'message': f"Pending customer request from {req.requested_by.get_full_name() or req.requested_by.username}",
            'url_name': 'customer_create_requests',
            'status': req.status,
            'timestamp': req.created_at,
        })

    for req in requester_qs:
        decision_label = 'approved' if req.status == 'approved' else 'rejected'
        reviewer_name = req.reviewed_by.get_full_name() or req.reviewed_by.username if req.reviewed_by else 'Reviewer'
        note_suffix = f" Reason: {req.decision_notes}" if req.decision_notes else ''
        notifications.append({
            'type': 'request_decision',
            'title': req.company_name,
            'message': f"Your request was {decision_label} by {reviewer_name}.{note_suffix}",
            'url_name': 'customer_create_request_history',
            'status': req.status,
            'timestamp': req.reviewed_at or req.created_at,
        })

    notifications.sort(key=lambda item: item['timestamp'], reverse=True)

    return {
        'customer_request_notifications': notifications[:5],
        'customer_request_notification_count': pending_count + requester_unread_count,
        'customer_request_pending_count': pending_count,
        'customer_request_unread_count': requester_unread_count,
    }
