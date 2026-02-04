from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.management import call_command
from django.db.models import Q
from .forms import SalespersonCreationForm
from .models import User
from teams.models import TeamMembership, Group
import tempfile
import os
from datetime import datetime

def is_manager(user):
    return user.role in ['admin', 'vp', 'avp', 'supervisor', 'asm', 'teamlead']

def is_admin(user):
    return user.role in ['admin', 'vp']

def is_executive(user):
    return user.role in ['admin', 'president', 'gm', 'vp']

def can_view_teams(user):
    return user.role in ['admin', 'president', 'gm', 'vp', 'avp', 'asm']

def can_manage_groups(user):
    return user.role in ['admin', 'president', 'gm', 'vp', 'avp', 'asm', 'supervisor']

@login_required
@user_passes_test(is_manager)
def create_salesperson(request):
    if request.method == 'POST':
        form = SalespersonCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home') # Or wherever you want to redirect after creation
    else:
        form = SalespersonCreationForm()
    return render(request, 'users/salesperson_form.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def user_management(request):
    """Admin page to manage all users with pagination and search"""
    # Get search query
    search_query = request.GET.get('search', '')
    
    # Start with all users
    users_list = User.objects.all()
    
    # Apply search filter if query exists
    if search_query:
        users_list = users_list.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(initials__icontains=search_query)
        )
    
    # Order users
    users_list = users_list.order_by('role', 'username')
    
    # Pagination
    page_size = request.GET.get('page_size', '20')  # Default to 20 users per page
    try:
        page_size = int(page_size)
        if page_size not in [10, 20, 50, 100]:
            page_size = 20
    except (ValueError, TypeError):
        page_size = 20
    
    paginator = Paginator(users_list, page_size)
    page = request.GET.get('page', 1)
    
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)
    
    context = {
        'users': users,
        'search_query': search_query,
        'page_size': page_size,
        'total_users': paginator.count,
    }
    
    return render(request, 'users/user_management.html', context)


@login_required
@user_passes_test(is_admin)
def toggle_user_active(request, user_id):
    """Toggle user active status (AJAX endpoint)"""
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Don't allow admin to deactivate themselves
            if user == request.user:
                return JsonResponse({
                    'success': False, 
                    'message': 'You cannot deactivate your own account.'
                })
            
            # Toggle active status
            user.is_active = not user.is_active
            user.save()
            
            action = 'activated' if user.is_active else 'deactivated'
            return JsonResponse({
                'success': True,
                'message': f'User {user.username} has been {action}.',
                'is_active': user.is_active
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
@user_passes_test(is_admin)
def create_user(request):
    """Create a new user"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        initials = request.POST.get('initials', '').upper()  # Convert to uppercase
        role = request.POST.get('role')
        password = request.POST.get('password')
        is_active = request.POST.get('is_active') == 'on'
        
        # Basic validation
        if not all([username, email, first_name, last_name, role, password]):
            messages.error(request, 'All fields are required.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        else:
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    initials=initials,
                    role=role,
                    password=password,
                    is_active=is_active
                )
                messages.success(request, f'User {username} created successfully.')
                return redirect('user_management')
            except Exception as e:
                messages.error(request, f'Error creating user: {str(e)}')
    
    return render(request, 'users/create_user.html', {
        'roles': User.ROLE_CHOICES
    })


@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    """Edit an existing user"""
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        initials = request.POST.get('initials', '').upper()  # Convert to uppercase
        role = request.POST.get('role')
        password = request.POST.get('password')
        is_active = request.POST.get('is_active') == 'on'
        
        # Basic validation
        if not all([username, email, first_name, last_name, role]):
            messages.error(request, 'All fields except password are required.')
        elif User.objects.filter(username=username).exclude(id=user_id).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exclude(id=user_id).exists():
            messages.error(request, 'Email already exists.')
        else:
            try:
                # Update user fields
                user_obj.username = username
                user_obj.email = email
                user_obj.first_name = first_name
                user_obj.last_name = last_name
                user_obj.initials = initials
                user_obj.role = role
                user_obj.is_active = is_active
                
                # Update password if provided
                if password:
                    user_obj.set_password(password)
                
                user_obj.save()
                messages.success(request, f'User {username} updated successfully.')
                return redirect('user_management')
            except Exception as e:
                messages.error(request, f'Error updating user: {str(e)}')
    
    return render(request, 'users/edit_user.html', {
        'user_obj': user_obj,
        'roles': User.ROLE_CHOICES
    })


@login_required
@user_passes_test(is_manager)
def transfer_salesperson(request, user_id):
    """Transfer a salesperson to another group"""
    salesperson = get_object_or_404(User, id=user_id, role='salesperson')
    
    # Get current team membership
    try:
        current_membership = salesperson.team_membership
    except TeamMembership.DoesNotExist:
        current_membership = None
    
    if request.method == 'POST':
        new_group_id = request.POST.get('new_group')
        
        if not new_group_id:
            messages.error(request, 'Please select a group.')
        else:
            try:
                new_group = get_object_or_404(Group, id=new_group_id)
                
                # Update or create team membership
                if current_membership:
                    current_membership.group = new_group
                    current_membership.save()
                else:
                    TeamMembership.objects.create(
                        user=salesperson,
                        group=new_group
                    )
                
                messages.success(request, f'Salesperson {salesperson.username} has been transferred to {new_group.name}.')
                return redirect('user_management')
                
            except Exception as e:
                messages.error(request, f'Error transferring salesperson: {str(e)}')
    
    # Get all groups for the dropdown
    groups = Group.objects.all().select_related('team')
    
    return render(request, 'users/transfer_salesperson.html', {
        'salesperson': salesperson,
        'current_membership': current_membership,
        'groups': groups
    })


@login_required
@user_passes_test(can_manage_groups)
def assign_teamlead(request, user_id):
    """Assign a teamlead to a group"""
    teamlead = get_object_or_404(User, id=user_id, role='teamlead')
    
    # Get current group assignment
    current_group = Group.objects.filter(teamlead=teamlead).first()
    
    if request.method == 'POST':
        new_group_id = request.POST.get('new_group')
        
        if not new_group_id:
            # Remove teamlead assignment
            if current_group:
                current_group.teamlead = None
                current_group.save()
                messages.success(request, f'Teamlead {teamlead.username} has been unassigned from {current_group.name}.')
            else:
                messages.info(request, f'Teamlead {teamlead.username} was not assigned to any group.')
        else:
            try:
                new_group = get_object_or_404(Group, id=new_group_id)
                
                # Remove from current group if assigned
                if current_group:
                    current_group.teamlead = None
                    current_group.save()
                
                # Assign to new group
                new_group.teamlead = teamlead
                new_group.save()
                
                messages.success(request, f'Teamlead {teamlead.username} has been assigned to {new_group.name}.')
                
            except Exception as e:
                messages.error(request, f'Error assigning teamlead: {str(e)}')
                
        return redirect('user_management')
    
    # Get available groups (filter by user's access if needed)
    if request.user.role == 'asm':
        # ASM can only assign teamleads to groups within their teams
        user_teams = request.user.asm_teams.all()
        groups = Group.objects.filter(team__in=user_teams)
    else:
        groups = Group.objects.all().select_related('team')
    
    return render(request, 'users/assign_teamlead.html', {
        'teamlead': teamlead,
        'current_group': current_group,
        'groups': groups
    })


@login_required
@user_passes_test(is_admin)
def export_users_json(request):
    """Export all users, teams, and relationships to JSON for production deployment"""
    try:
        # Get export options from request
        include_passwords = request.GET.get('include_passwords', 'false').lower() == 'true'
        include_inactive = request.GET.get('include_inactive', 'true').lower() == 'true'
        pretty_print = request.GET.get('pretty', 'true').lower() == 'true'
        
        # Create temporary file for export
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_file_path = temp_file.name
        
        # Prepare export arguments
        export_args = [
            '--output', temp_file_path,
        ]
        
        if include_passwords:
            export_args.append('--include-passwords')
        
        if include_inactive:
            export_args.append('--include-inactive')
            
        if pretty_print:
            export_args.append('--pretty')
        
        # Run export command
        call_command('export_users', *export_args)
        
        # Read the generated file
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            export_content = f.read()
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        # Generate filename for download
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f'crm_users_export_{timestamp}.json'
        
        # Create HTTP response with file download
        response = HttpResponse(export_content, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(export_content)
        
        # Add success message for next page load
        messages.success(request, f'User export completed successfully! Downloaded: {filename}')
        
        return response
        
    except Exception as e:
        messages.error(request, f'Export failed: {str(e)}')
        return redirect('user_management')
