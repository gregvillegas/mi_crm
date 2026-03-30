from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db import models
from django.db.models import Sum
from .models import Customer, CustomerBackup, CustomerHistory, DelinquencyRecord, CustomerNote, CustomerContact
from .forms import CustomerForm, CustomerContactFormSet
from users.models import User
from teams.models import Team, Group, TeamMembership
from sales_funnel.models import SalesFunnel
from sales_proposals.models import Proposal
from sales_monitoring.models import SalesActivity, ProofOfConcept
from customer_service.models import Ticket
import csv
import io

def is_manager(user):
    return user.role in ['admin', 'avp', 'supervisor', 'asm', 'teamlead']

def is_executive(user):
    return user.role in ['admin', 'president', 'gm', 'vp']

def is_admin_or_exec(user):
    return user.role in ['admin', 'gm', 'vp']

@login_required
def add_customer_note(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            CustomerNote.objects.create(
                customer=customer,
                author=request.user,
                content=content
            )
            messages.success(request, 'Note added successfully.')
        else:
            messages.error(request, 'Note content cannot be empty.')
    return redirect('customer_detail', pk=pk)

@login_required
def customer_list(request):
    user = request.user
    customers = Customer.objects.none()
    view_mode = request.GET.get('view', 'table')

    # Get base customer queryset based on user role
    if user.role in ['admin', 'president', 'gm', 'vp']:
        # Executives have full access to all customers
        customers = Customer.objects.all()
    elif user.role == 'avp':
        teams = Team.objects.filter(avp=user)
        groups = Group.objects.filter(team__in=teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        salespeople = User.objects.filter(id__in=salespeople_ids)
        customers = Customer.objects.filter(salesperson__in=salespeople)
    elif user.role == 'asm':
        # ASM can see customers from their assigned teams
        asm_teams = user.asm_teams.all()
        groups = Group.objects.filter(team__in=asm_teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        salespeople = User.objects.filter(id__in=salespeople_ids)
        customers = Customer.objects.filter(salesperson__in=salespeople)
    elif user.role == 'supervisor':
        groups = Group.objects.filter(supervisor=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        salespeople = User.objects.filter(id__in=salespeople_ids)
        customers = Customer.objects.filter(salesperson__in=salespeople)
    elif user.role == 'teamlead':
        # Teamlead can see customers from their assigned group
        teamlead_groups = Group.objects.filter(teamlead=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=teamlead_groups).values_list('user_id', flat=True)
        salespeople = User.objects.filter(id__in=salespeople_ids)
        customers = Customer.objects.filter(salesperson__in=salespeople)
    elif user.role == 'salesperson':
        customers = Customer.objects.filter(salesperson=user)

    # Apply filters based on GET parameters
    status_filter = request.GET.get('status')
    vip_filter = request.GET.get('vip')
    industry_filter = request.GET.get('industry')
    territory_filter = request.GET.get('territory')
    search_query = request.GET.get('search')
    salesperson_filter = request.GET.get('salesperson')
    
    if status_filter == 'active':
        customers = customers.filter(is_active=True)
    elif status_filter == 'inactive':
        customers = customers.filter(is_active=False)
    
    if vip_filter == 'yes':
        customers = customers.filter(is_vip=True)
    elif vip_filter == 'no':
        customers = customers.filter(is_vip=False)
    
    if industry_filter and industry_filter != '':
        customers = customers.filter(industry=industry_filter)
    
    if territory_filter and territory_filter != '':
        customers = customers.filter(territory=territory_filter)
    
    if search_query:
        customers = customers.filter(
            models.Q(company_name__icontains=search_query) |
            models.Q(contact_person_name__icontains=search_query) |
            models.Q(email__icontains=search_query)
        )
    
    # Salesperson filter
    if salesperson_filter:
        if salesperson_filter == 'unassigned':
            customers = customers.filter(salesperson__isnull=True)
        else:
            try:
                sp_id = int(salesperson_filter)
                customers = customers.filter(salesperson_id=sp_id)
            except ValueError:
                pass
    
    # Order by VIP status first, then by creation date
    customers = customers.select_related('salesperson').order_by('-is_vip', '-created_at')
    
    # Available salespeople for filter dropdown (active only)
    available_salespeople = User.objects.filter(role='salesperson', is_active=True).order_by('first_name','last_name','username')
    
    # Determine if user can see admin actions column
    # Admin, VP, GM: Full access
    # AVP, ASM, Supervisor: Transfer access
    can_manage_customers = user.role in ['admin', 'gm', 'vp', 'avp', 'asm', 'supervisor']

    # Get filter options for the template
    context = {
        'customers': customers,
        'view_mode': view_mode,
        'show_actions': can_manage_customers,
        'industry_choices': Customer.INDUSTRY_CHOICES,
        'territory_choices': Customer.TERRITORY_CHOICES,
        'available_salespeople': available_salespeople,
        'current_filters': {
            'status': status_filter,
            'vip': vip_filter,
            'industry': industry_filter,
            'territory': territory_filter,
            'search': search_query or '',
            'salesperson': salesperson_filter or '',
            'view': view_mode,
        },
        'stats': {
            'total': customers.count(),
            'vip_count': customers.filter(is_vip=True).count(),
            'active_count': customers.filter(is_active=True).count(),
            'inactive_count': customers.filter(is_active=False).count(),
        }
    }
    
    return render(request, 'customers/customer_list.html', context)

@login_required
def customer_contacts(request, pk):
    """Return up to 4 contacts for a customer in JSON for dependent dropdowns."""
    customer = get_object_or_404(Customer, pk=pk)
    # Convert queryset to list of dicts
    additional = list(CustomerContact.objects.filter(customer=customer).order_by('-is_primary','name').values('id','name','position','email','phone','is_primary'))
    # Always include legacy main contact as an option
    main_contact = {
        'id': 'main',
        'name': customer.contact_person_name or '',
        'position': customer.contact_person_position or '',
        'email': customer.email or '',
        'phone': customer.phone_number or '',
        'is_primary': False
    }
    # If no additional primary is set, make main contact primary by default
    if not any(c.get('is_primary') for c in additional):
        main_contact['is_primary'] = True
    # Build final list with main first, then additional (de-duplicate by name+email)
    seen = set()
    contacts = []
    for c in [main_contact] + additional:
        key = (c.get('name','').strip().lower(), (c.get('email') or '').strip().lower())
        if key in seen:
            continue
        seen.add(key)
        contacts.append(c)
    return JsonResponse({'contacts': contacts})

@login_required
def delinquent_list(request):
    user = request.user
    records = DelinquencyRecord.objects.filter(status__in=['open','watch']).select_related('customer','salesperson')
    # Filters (simplified to match current UI/fields)
    search = request.GET.get('search')
    tin = request.GET.get('tin')
    partner = request.GET.get('partner')
    ae = request.GET.get('ae')
    if search:
        records = records.filter(
            models.Q(customer__company_name__icontains=search) |
            models.Q(remarks__icontains=search)
        )
    if tin:
        records = records.filter(tin_number__icontains=tin)
    if partner:
        records = records.filter(partner_name__icontains=partner)
    if ae:
        try:
            ae_id = int(ae)
            records = records.filter(models.Q(salesperson_id=ae_id))
        except Exception:
            pass
    # Available AE list for dropdown (all)
    from users.models import User
    available_ae = User.objects.filter(is_active=True, role__in=['salesperson','supervisor','asm','avp'])
    context = {
        'records': records.order_by('customer__company_name'),
        'current_filters': {
            'search': search or '',
            'tin': tin or '',
            'partner': partner or '',
            'ae': int(ae) if (ae and ae.isdigit()) else '',
        },
        'available_ae': available_ae.order_by('first_name','last_name','username')
    }
    return render(request, 'customers/delinquent_list.html', context)

@login_required
def create_customer(request):
    user = request.user
    
    # Check permissions - managers can create any customer
    # Salespeople are temporarily restricted from adding customers
    if user.role not in ['admin', 'gm', 'vp', 'avp', 'supervisor', 'asm', 'teamlead']:
        messages.error(request, "You don't have permission to create customers.")
        return redirect('customer_list')
    
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            contact_formset = CustomerContactFormSet(request.POST, instance=customer)
            if contact_formset.is_valid():
                contact_formset.save()
                messages.success(request, f'Customer "{customer.company_name}" has been created successfully!')
                return redirect('customer_list')
            else:
                # Show errors with the saved instance bound formset
                context = {
                    'form': form,
                    'contact_formset': contact_formset,
                    'title': 'Create New Customer',
                    'is_salesperson_form': False
                }
                return render(request, 'customers/customer_form.html', context)
        else:
            contact_formset = CustomerContactFormSet(request.POST)
            context = {
                'form': form,
                'contact_formset': contact_formset,
                'title': 'Create New Customer',
                'is_salesperson_form': False
            }
            return render(request, 'customers/customer_form.html', context)
    else:
        form = CustomerForm()
        contact_formset = CustomerContactFormSet()
        context = {
            'form': form,
            'contact_formset': contact_formset,
            'title': 'Create New Customer',
            'is_salesperson_form': False
        }
    
    return render(request, 'customers/customer_form.html', context)

@login_required
def transfer_customer(request, pk):
    # Permission check: Admin, VP, GM, AVP, Supervisor, ASM
    if request.user.role not in ['admin', 'vp', 'gm', 'avp', 'supervisor', 'asm']:
        messages.error(request, "You don't have permission to transfer customers.")
        return redirect('customer_list')

    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        new_salesperson_id = request.POST.get('salesperson')
        new_salesperson = get_object_or_404(User, id=new_salesperson_id, role='salesperson')
        customer.salesperson = new_salesperson
        customer.save()
        messages.success(request, f'Customer "{customer.company_name}" has been transferred to {new_salesperson.get_full_name()}.')
        return redirect('customer_list')

    # Get available salespeople based on role (could be filtered by team in future)
    salespeople = User.objects.filter(role='salesperson', is_active=True)
    return render(request, 'customers/transfer_customer.html', {'customer': customer, 'salespeople': salespeople})


def is_admin(user):
    return user.role == 'admin'

@login_required
@user_passes_test(is_admin)
def export_customers(request):
    """Export all customers to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers_export.csv"'
    
    writer = csv.writer(response)
    # Write header
    writer.writerow([
        'Company Name', 'Contact Person Name', 'Contact Person Position', 'Email', 'Phone Number', 'Address', 
        'Industry', 'Territory', 'VIP Status', 'Active Status', 'Salesperson Initials',
        'Created At', 'Updated At'
    ])
    
    # Write customer data
    customers = Customer.objects.all().select_related('salesperson')
    for customer in customers:
        salesperson_initials = customer.salesperson.initials if customer.salesperson and customer.salesperson.initials else ''
        writer.writerow([
            customer.company_name,
            customer.contact_person_name,
            customer.contact_person_position,
            customer.email,
            customer.phone_number,
            customer.address,
            customer.get_industry_display() if customer.industry else '',
            customer.get_territory_display() if customer.territory else '',
            'Yes' if customer.is_vip else 'No',
            'Yes' if customer.is_active else 'No',
            salesperson_initials,
            customer.created_at.strftime('%Y-%m-%d %H:%M:%S') if customer.created_at else '',
            customer.updated_at.strftime('%Y-%m-%d %H:%M:%S') if customer.updated_at else '',
        ])
    
    return response

@login_required
@user_passes_test(is_admin)
def import_customers(request):
    """Import customers from CSV"""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please select a CSV file to upload.')
            return redirect('customer_list')
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return redirect('customer_list')
        
        try:
            # Read CSV file content
            content = csv_file.read()
            
            # Try decoding with different encodings
            decoded_file = None
            for encoding in ['utf-8', 'cp1252', 'latin-1']:
                try:
                    decoded_file = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if decoded_file is None:
                messages.error(request, 'Unable to read the CSV file. Unsupported encoding.')
                return redirect('customer_list')

            csv_data = csv.reader(io.StringIO(decoded_file))
            
            # Skip header row
            next(csv_data, None)
            
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(csv_data, start=2):
                if len(row) < 5:  # Minimum required fields
                    errors.append(f'Row {row_num}: Not enough columns')
                    continue
                
                # Extract all columns based on export format
                company_name = row[0] if len(row) > 0 else ''
                contact_person_name = row[1] if len(row) > 1 else ''
                contact_person_position = row[2] if len(row) > 2 else ''
                email = row[3] if len(row) > 3 else ''
                phone_number = row[4] if len(row) > 4 else ''
                address = row[5] if len(row) > 5 else ''
                industry = row[6] if len(row) > 6 else ''
                territory = row[7] if len(row) > 7 else ''
                vip_status = row[8] if len(row) > 8 else 'No'
                active_status = row[9] if len(row) > 9 else 'Yes'
                salesperson_initials = row[10] if len(row) > 10 else ''
                # Skip Created At and Updated At (columns 11-12) as they're auto-generated
                
                if not company_name or not contact_person_name or not email:
                    errors.append(f'Row {row_num}: Company name, contact person name, and email are required')
                    continue
                
                # Check if customer already exists
                if Customer.objects.filter(email=email).exists():
                    errors.append(f'Row {row_num}: Customer with email {email} already exists')
                    continue
                
                # Validate and convert industry
                industry_value = ''
                if industry:
                    industry_lower = industry.lower()
                    industry_mapping = {choice[1].lower(): choice[0] for choice in Customer.INDUSTRY_CHOICES}
                    if industry_lower in industry_mapping:
                        industry_value = industry_mapping[industry_lower]
                    else:
                        # Try to find partial match
                        for display, value in Customer.INDUSTRY_CHOICES:
                            if industry_lower in display.lower():
                                industry_value = value
                                break
                        if not industry_value:
                            errors.append(f'Row {row_num}: Invalid industry "{industry}"')
                            continue
                
                # Validate and convert territory
                territory_value = ''
                if territory:
                    territory_lower = territory.lower()
                    territory_mapping = {choice[1].lower(): choice[0] for choice in Customer.TERRITORY_CHOICES}
                    if territory_lower in territory_mapping:
                        territory_value = territory_mapping[territory_lower]
                    else:
                        # Try to find partial match
                        for display, value in Customer.TERRITORY_CHOICES:
                            if territory_lower in display.lower():
                                territory_value = value
                                break
                        if not territory_value:
                            errors.append(f'Row {row_num}: Invalid territory "{territory}"')
                            continue
                
                # Parse VIP status
                is_vip = vip_status.lower() in ['yes', 'true', '1']
                
                # Parse active status
                is_active = active_status.lower() in ['yes', 'true', '1']
                
                # Get salesperson if initials are provided
                salesperson = None
                if salesperson_initials:
                    try:
                        salesperson = User.objects.get(initials=salesperson_initials, role='salesperson', is_active=True)
                    except User.DoesNotExist:
                        errors.append(f'Row {row_num}: Active salesperson with initials "{salesperson_initials}" not found')
                        continue
                
                # Create customer
                try:
                    Customer.objects.create(
                        company_name=company_name,
                        contact_person_name=contact_person_name,
                        contact_person_position=contact_person_position,
                        email=email,
                        phone_number=phone_number,
                        address=address,
                        industry=industry_value,
                        territory=territory_value,
                        is_vip=is_vip,
                        is_active=is_active,
                        salesperson=salesperson
                    )
                    imported_count += 1
                except Exception as e:
                    errors.append(f'Row {row_num}: Error creating customer - {str(e)}')
            
            if imported_count > 0:
                messages.success(request, f'Successfully imported {imported_count} customers.')
            
            if errors:
                error_message = f'Encountered {len(errors)} errors:\n' + '\n'.join(errors[:10])
                if len(errors) > 10:
                    error_message += f'\n... and {len(errors) - 10} more errors.'
                messages.warning(request, error_message)
                
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
        
        return redirect('customer_list')
    
    return render(request, 'customers/import_customers.html')

@login_required
@user_passes_test(is_admin)
def download_sample_csv(request):
    """Download a sample CSV template for customer import"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customer_import_sample.csv"'
    
    writer = csv.writer(response)
    # Write header - matching export format
    writer.writerow([
        'Company Name', 'Contact Person Name', 'Contact Person Position', 'Email', 'Phone Number', 'Address', 
        'Industry', 'Territory', 'VIP Status', 'Active Status', 'Salesperson Initials',
        'Created At', 'Updated At'
    ])
    
    # Write sample data with correct choice values
    writer.writerow([
        'ABC Corporation', 'John Doe', 'CEO', 'john.doe@abccorp.com', '+1234567890', '123 Main St, Makati City, Metro Manila', 
        'Technology', 'Makati City', 'Yes', 'Yes', 'JDS',
        '2024-01-15 09:30:00', '2024-01-20 14:45:00'
    ])
    writer.writerow([
        'XYZ Industries', 'Jane Smith', 'Purchasing Manager', 'jane.smith@xyzind.com', '+0987654321', '456 Oak Ave, Pasig City, Metro Manila', 
        'Manufacturing', 'Pasig City', 'No', 'Yes', '',
        '2024-01-16 11:20:00', '2024-01-25 16:15:00'
    ])
    writer.writerow([
        'Global Tech Solutions', 'Michael Johnson', 'Finance Director', 'mjohnson@globaltech.com', '+1122334455', '789 Pine St, Ortigas Center, Metro Manila', 
        'Finance & Banking', 'Ortigas', 'Yes', 'No', 'MRP',
        '2024-01-17 08:15:00', '2024-01-30 10:30:00'
    ])
    
    return response


@login_required
@user_passes_test(is_admin)
def toggle_customer_vip(request, pk):
    """Toggle customer VIP status (AJAX endpoint)"""
    if request.method == 'POST':
        try:
            customer = get_object_or_404(Customer, pk=pk)
            old_vip_status = customer.is_vip
            customer.is_vip = not customer.is_vip
            customer.save()
            
            # Log history event
            action = 'vip_enabled' if customer.is_vip else 'vip_disabled'
            description = f"Customer VIP status changed from {'VIP' if old_vip_status else 'Regular'} to {'VIP' if customer.is_vip else 'Regular'} by {request.user.get_full_name() or request.user.username}"
            
            history_entry = CustomerHistory(
                customer=customer,
                action=action,
                description=description,
                changed_by=request.user,
                salesperson_at_time=customer.salesperson,
                old_value={'is_vip': old_vip_status},
                new_value={'is_vip': customer.is_vip},
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            history_entry.save()
            
            return JsonResponse({
                'success': True,
                'message': f'{customer.full_name} VIP status updated.',
                'is_vip': customer.is_vip
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


@login_required
def customer_history(request, pk):
    """View complete history of a customer for tracking and salesperson attribution"""
    customer = get_object_or_404(Customer, pk=pk)
    
    # Check if user has permission to view this customer
    user = request.user
    has_access = False
    
    if user.role in ['admin', 'president', 'gm', 'vp']:
        has_access = True
    elif user.role == 'avp':
        teams = Team.objects.filter(avp=user)
        groups = Group.objects.filter(team__in=teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        has_access = customer.salesperson_id in salespeople_ids
    elif user.role == 'asm':
        asm_teams = user.asm_teams.all()
        groups = Group.objects.filter(team__in=asm_teams)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        has_access = customer.salesperson_id in salespeople_ids
    elif user.role == 'supervisor':
        groups = Group.objects.filter(supervisor=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
        has_access = customer.salesperson_id in salespeople_ids
    elif user.role == 'teamlead':
        teamlead_groups = Group.objects.filter(teamlead=user)
        salespeople_ids = TeamMembership.objects.filter(group__in=teamlead_groups).values_list('user_id', flat=True)
        has_access = customer.salesperson_id in salespeople_ids
    elif user.role == 'salesperson':
        has_access = customer.salesperson == user
    
    if not has_access:
        messages.error(request, 'You do not have permission to view this customer history.')
        return redirect('customer_list')
    
    # Get history records
    history = CustomerHistory.objects.filter(customer=customer).select_related(
        'changed_by', 'salesperson_at_time'
    ).order_by('-timestamp')
    
    # Get summary statistics
    history_stats = {
        'total_changes': history.count(),
        'vip_changes': history.filter(action__in=['vip_enabled', 'vip_disabled']).count(),
        'status_changes': history.filter(action__in=['activated', 'deactivated']).count(),
        'salesperson_changes': history.filter(action__in=['salesperson_assigned', 'salesperson_changed', 'salesperson_removed']).count(),
        'field_updates': history.filter(action='field_updated').count(),
    }
    
    # Get unique salespeople who have handled this customer
    salespeople_history = history.filter(
        salesperson_at_time__isnull=False
    ).values_list(
        'salesperson_at_time__username',
        'salesperson_at_time__first_name',
        'salesperson_at_time__last_name',
        'salesperson_at_time__initials'
    ).distinct()
    
    context = {
        'customer': customer,
        'history': history,
        'history_stats': history_stats,
        'salespeople_history': salespeople_history,
    }
    
    return render(request, 'customers/customer_history.html', context)


# =====================================================================
# ADMIN CUSTOMER MANAGEMENT & BACKUP/RESTORE FUNCTIONALITY
# =====================================================================

@login_required
@user_passes_test(is_admin_or_exec)
def edit_customer(request, pk):
    """Admin can edit customer details with automatic backup"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        # Create backup before making changes
        customer.create_backup(
            changed_by=request.user,
            reason="Before admin edit"
        )
        
        form = CustomerForm(request.POST, instance=customer)
        contact_formset = CustomerContactFormSet(request.POST, instance=customer)
        if form.is_valid() and contact_formset.is_valid():
            form.save()
            contacts = contact_formset.save()
            messages.success(request, f'Customer "{customer.full_name}" has been updated successfully. Backup created automatically.')
            return redirect('customer_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerForm(instance=customer)
        contact_formset = CustomerContactFormSet(instance=customer)
    
    # Get recent backups for this customer
    recent_backups = CustomerBackup.objects.filter(customer=customer)[:5]
    
    context = {
        'form': form,
        'customer': customer,
        'contact_formset': contact_formset,
        'recent_backups': recent_backups,
        'is_edit': True
    }
    
    return render(request, 'customers/customer_form.html', context)

@login_required
@user_passes_test(is_admin)
def create_delinquency(request):
    from .forms import DelinquencyCreateForm
    from .models import DelinquentCustomer, DelinquencyRecord
    if request.method == 'POST':
        form = DelinquencyCreateForm(request.POST)
        if form.is_valid():
            company = form.cleaned_data['company_name'].strip()
            assigned_ae = form.cleaned_data.get('assigned_ae') or ''
            email = (form.cleaned_data.get('email') or '').strip().lower()
            status = form.cleaned_data['status']
            tin = form.cleaned_data.get('tin_number') or ''
            partner = form.cleaned_data.get('partner_name') or ''
            date_delivered = form.cleaned_data.get('date_delivered')
            last_payment = form.cleaned_data.get('last_payment_date')
            remarks = form.cleaned_data.get('remarks') or ''
            dcustomer = DelinquentCustomer.objects.create(
                company_name=company,
                assigned_ae=assigned_ae,
                email=email
            )
            DelinquencyRecord.objects.create(
                customer=dcustomer,
                salesperson=None,
                status=status,
                tin_number=tin,
                partner_name=partner,
                date_delivered=date_delivered,
                last_payment_date=last_payment,
                remarks=remarks,
                created_by=request.user
            )
            messages.success(request, 'Delinquency record created.')
            return redirect('delinquent_list')
    else:
        form = DelinquencyCreateForm()
    return render(request, 'customers/delinquency_form.html', {'form': form, 'title': 'Add Delinquency Record'})

@login_required
@user_passes_test(is_admin)
def import_delinquencies(request):
    """Import delinquency records from CSV (Excel saved as CSV).
    Accepted columns (case-insensitive, flexible):
      - Company: company_name, company, company name
      - Email: email
      - Contact Person: contact_person, contact, contact person
      - TIN: tin_number, tin, tin number, tin no
      - Amount Due: amount_due, amount, balance, ar amount
      - Due Date: due_date, due, due date
      - Last Payment Date: last_payment_date, last payment, last payment date
      - Status: status (open|resolved|watch)
      - Remarks/Notes: remarks, notes
      - Salesperson: salesperson_username, salesperson, ae, collector, initials
    """
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please select a CSV file to upload.')
            return redirect('delinquent_list')
        try:
            import csv, io
            # Read raw bytes and try multiple encodings (common for Excel CSV)
            raw = csv_file.read()
            decoded_text = None
            for enc in ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1', 'iso-8859-1', 'utf-16', 'macroman']:
                try:
                    decoded_text = raw.decode(enc)
                    break
                except Exception:
                    continue
            if decoded_text is None:
                messages.error(request, 'Unable to read CSV: unsupported encoding.')
                return redirect('delinquent_list')
            sio = io.StringIO(decoded_text)
            # Try to sniff delimiter if needed
            try:
                sample = decoded_text[:4096]
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
            except csv.Error:
                dialect = 'excel'
            sio.seek(0)
            reader = csv.DictReader(sio, dialect=dialect)
            created = 0
            from decimal import Decimal
            from django.utils.dateparse import parse_date
            from datetime import datetime

            def first_of(row, keys):
                for k in keys:
                    # try exact, lower, title
                    v = row.get(k) or row.get(k.lower()) or row.get(k.title())
                    if v not in [None, '']:
                        return v
                return ''

            def parse_amount(s):
                if s is None:
                    return Decimal('0')
                s = str(s).strip()
                s = s.replace('₱', '').replace(',', '').replace(' ', '')
                negative = False
                if s.startswith('(') and s.endswith(')'):
                    negative = True
                    s = s[1:-1]
                try:
                    val = Decimal(s)
                    return -val if negative else val
                except Exception:
                    return Decimal('0')

            def parse_date_flexible(s):
                if not s:
                    return None
                s = str(s).strip()
                # Try pandas-like excel serial?
                try:
                    # If it's a float-like excel serial number, skip here; left for future enhancement
                    pass
                except Exception:
                    pass
                # Try built-in ISO parser first
                d = parse_date(s)
                if d:
                    return d
                # Try a set of common formats (02/15/26, 15/02/2026, etc.)
                formats = ['%m/%d/%y','%m/%d/%Y','%d/%m/%y','%d/%m/%Y','%b %d %Y','%d-%b-%Y']
                for fmt in formats:
                    try:
                        return datetime.strptime(s, fmt).date()
                    except Exception:
                        continue
                return None

            for row in reader:
                company = first_of(row, ['company_name', 'company', 'Company Name'])
                email = first_of(row, ['email', 'Email'])
                assigned_ae_val = first_of(row, ['assigned_ae', 'Assigned AE', 'AE', 'Account Executive', 'contact_person', 'Contact Person'])
                remarks = first_of(row, ['remarks', 'notes', 'Remarks', 'Notes'])
                tin_number = first_of(row, ['tin_number', 'TIN', 'TIN Number', 'Tin No', 'Tin #'])
                partner_name = first_of(row, ['partner_name', 'Partners Name', 'Partner Name', 'Partner', 'Partner_Name'])
                status = (first_of(row, ['status', 'Status']) or 'open').lower()
                amount_str = first_of(row, ['amount_due', 'Amount Due', 'amount', 'Amount', 'balance', 'Balance', 'AR Amount'])
                date_delivered_str = first_of(row, ['date_delivered', 'date_deliver', 'Date Delivered', 'Date Deliver'])
                last_payment_str = first_of(row, ['last_payment_date', 'last_payment', 'Last Payment Date', 'Last Payment'])
                sp_val = first_of(row, ['salesperson_username', 'Salesperson Username', 'salesperson', 'Salesperson', 'ae', 'AE', 'collector', 'Collector', 'initials', 'Initials', 'Account Executive'])

                from decimal import Decimal
                amount = parse_amount(amount_str)
                date_delivered = parse_date_flexible(date_delivered_str) if date_delivered_str else None
                last_payment = parse_date_flexible(last_payment_str) if last_payment_str else None
                # Find or create delinquent customer (separate table)
                from .models import DelinquentCustomer
                dcustomer = None
                if email:
                    dcustomer = DelinquentCustomer.objects.filter(email__iexact=email).first()
                if not dcustomer and company:
                    dcustomer = DelinquentCustomer.objects.filter(company_name__iexact=company).first()
                if dcustomer and assigned_ae_val:
                    if (dcustomer.assigned_ae or '').strip().lower() in ['', 'unknown'] or dcustomer.assigned_ae != assigned_ae_val:
                        dcustomer.assigned_ae = assigned_ae_val
                        dcustomer.save(update_fields=['assigned_ae'])
                if not dcustomer and company:
                    dcustomer = DelinquentCustomer.objects.create(
                        company_name=company,
                        assigned_ae=assigned_ae_val or '',
                        email=email or ''
                    )
                # Find salesperson
                salesperson = None
                if sp_val:
                    # Try by username first
                    salesperson = User.objects.filter(username__iexact=sp_val, is_active=True).first()
                    # Fallback to initials match
                    if not salesperson:
                        salesperson = User.objects.filter(initials__iexact=sp_val, is_active=True).first()
                if dcustomer:
                    final_remarks = remarks
                    DelinquencyRecord.objects.create(
                        customer=dcustomer,
                        salesperson=salesperson,
                        status=status if status in ['open','resolved','watch'] else 'open',
                        tin_number=tin_number,
                        partner_name=partner_name,
                        date_delivered=date_delivered,
                        last_payment_date=last_payment,
                        remarks=final_remarks,
                        created_by=request.user
                    )
                    created += 1
            messages.success(request, f'Imported {created} delinquency records.')
            return redirect('delinquent_list')
        except Exception as e:
            messages.error(request, f'Import failed: {e}')
            return redirect('delinquent_list')
    return render(request, 'customers/delinquency_import.html', {'title': 'Import Delinquency Records'})

@login_required
@user_passes_test(is_admin)
def download_delinquency_sample_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="delinquency_sample.csv"'
    import csv
    writer = csv.writer(response)
    writer.writerow(['company_name','email','assigned_ae','tin_number','partner_name','date_delivered','last_payment_date','status','remarks','salesperson_username'])
    writer.writerow(['Acme Corp','billing@acme.com','J. Rabe','000-123-456','Micro Image','2026-02-15','2026-01-15','open','Hard to collect due to long processing','jsmith'])
    return response

@login_required
@user_passes_test(is_admin)
def export_delinquencies(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="delinquency_export.csv"'
    import csv
    writer = csv.writer(response)
    writer.writerow([
        'company_name','email','assigned_ae','tin_number','status','partner_name','date_delivered','last_payment_date','remarks','salesperson_username','created_by','updated_at'
    ])
    qs = DelinquencyRecord.objects.select_related('customer','salesperson','created_by').all().order_by('customer__company_name')
    for rec in qs:
        writer.writerow([
            rec.customer.company_name,
            rec.customer.email,
            rec.customer.assigned_ae,
            rec.tin_number or '',
            rec.get_status_display(),
            rec.partner_name or '',
            rec.date_delivered.isoformat() if rec.date_delivered else '',
            rec.last_payment_date.isoformat() if rec.last_payment_date else '',
            rec.remarks.replace('\n',' ').strip() if rec.remarks else '',
            rec.salesperson.username if rec.salesperson else '',
            rec.created_by.username if rec.created_by else '',
            rec.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        ])
    return response
 
@login_required
@user_passes_test(is_admin)
def clear_delinquencies(request):
    if request.method == 'POST':
        count = DelinquencyRecord.objects.count()
        DelinquencyRecord.objects.all().delete()
        messages.success(request, f'Cleared {count} delinquency records.')
        return redirect('delinquent_list')
    return render(request, 'customers/confirm_clear_delinquencies.html', {})


@login_required
@user_passes_test(is_admin)
def customer_backups(request, pk):
    """View all backups for a specific customer"""
    customer = get_object_or_404(Customer, pk=pk)
    backups = CustomerBackup.objects.filter(customer=customer)
    
    context = {
        'customer': customer,
        'backups': backups
    }
    
    return render(request, 'customers/customer_backups.html', context)


@login_required
@user_passes_test(is_admin)
def create_manual_backup(request, pk):
    """Create a manual backup of customer data"""
    if request.method == 'POST':
        customer = get_object_or_404(Customer, pk=pk)
        reason = request.POST.get('reason', 'Manual backup by admin')
        
        try:
            backup = customer.create_backup(
                changed_by=request.user,
                reason=reason
            )
            messages.success(request, f'Manual backup created successfully for "{customer.full_name}".')
        except Exception as e:
            messages.error(request, f'Error creating backup: {str(e)}')
        
        return redirect('customer_backups', pk=pk)
    
    return redirect('customer_list')


@login_required
@user_passes_test(is_admin)
def restore_customer(request, customer_pk, backup_pk):
    """Restore customer from a specific backup"""
    customer = get_object_or_404(Customer, pk=customer_pk)
    backup = get_object_or_404(CustomerBackup, pk=backup_pk, customer=customer)
    
    if request.method == 'POST':
        try:
            backup.restore(restored_by=request.user)
            messages.success(
                request, 
                f'Customer "{customer.full_name}" has been restored from backup '
                f'created on {backup.created_at.strftime("%Y-%m-%d %H:%M:%S")}.'
            )
            return redirect('customer_list')
        except Exception as e:
            messages.error(request, f'Error restoring customer: {str(e)}')
            return redirect('customer_backups', pk=customer_pk)
    
    # Show confirmation page
    backup_data = backup.get_backup_data()
    context = {
        'customer': customer,
        'backup': backup,
        'backup_data': backup_data
    }
    
    return render(request, 'customers/restore_customer.html', context)


@login_required
@user_passes_test(is_admin)
def backup_overview(request):
    """Overview of all customer backups in the system"""
    # Get statistics
    total_customers = Customer.objects.count()
    total_backups = CustomerBackup.objects.count()
    customers_with_backups = Customer.objects.filter(backups__isnull=False).distinct().count()
    
    # Get recent backups across all customers
    recent_backups = CustomerBackup.objects.select_related('customer', 'changed_by').order_by('-created_at')[:20]
    
    # Get customers with most backups
    customers_by_backup_count = Customer.objects.annotate(
        backup_count=models.Count('backups')
    ).filter(backup_count__gt=0).order_by('-backup_count')[:10]
    
    # Calculate coverage percentage
    coverage_percent = 0
    if total_customers > 0:
        coverage_percent = round((customers_with_backups * 100) / total_customers)
    
    context = {
        'stats': {
            'total_customers': total_customers,
            'total_backups': total_backups,
            'customers_with_backups': customers_with_backups,
            'customers_without_backups': total_customers - customers_with_backups,
            'coverage_percent': coverage_percent,
        },
        'recent_backups': recent_backups,
        'customers_by_backup_count': customers_by_backup_count,
    }
    
    return render(request, 'customers/backup_overview.html', context)


@login_required
@user_passes_test(is_admin)
def toggle_customer_active(request, pk):
    """Toggle customer active status (AJAX endpoint)"""
    if request.method == 'POST':
        try:
            customer = get_object_or_404(Customer, pk=pk)
            old_active_status = customer.is_active
            customer.is_active = not customer.is_active
            customer.save()
            
            # Log history event
            action = 'activated' if customer.is_active else 'deactivated'
            description = f"Customer status changed from {'Active' if old_active_status else 'Inactive'} to {'Active' if customer.is_active else 'Inactive'} by {request.user.get_full_name() or request.user.username}"
            
            history_entry = CustomerHistory(
                customer=customer,
                action=action,
                description=description,
                changed_by=request.user,
                salesperson_at_time=customer.salesperson,
                old_value={'is_active': old_active_status},
                new_value={'is_active': customer.is_active},
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            history_entry.save()
            
            status = 'activated' if customer.is_active else 'deactivated'
            return JsonResponse({
                'success': True,
                'message': f'{customer.full_name} has been {status}.',
                'is_active': customer.is_active
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def customer_detail(request, pk):
    """360-degree view of a customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    # Check permissions (reuse existing logic or simplify)
    # For now, allow access if user can see customer_list or is owner
    
    # Gather Data
    active_deals = SalesFunnel.objects.filter(customer=customer).exclude(deal_outcome__in=['won', 'lost', 'cancelled'])
    all_deals = SalesFunnel.objects.filter(customer=customer).order_by('-created_at')
    won_deals = SalesFunnel.objects.filter(customer=customer, deal_outcome='won')
    
    proposals = Proposal.objects.filter(customer=customer).order_by('-created_at')
    
    # Get all activities for this customer
    all_activities = SalesActivity.objects.filter(customer=customer).select_related('activity_type', 'salesperson').order_by('-scheduled_start')
    recent_activities = all_activities[:5]
    
    # Get POCs
    pocs = ProofOfConcept.objects.filter(customer=customer).select_related('lead_engineer').order_by('-created_at')
    active_pocs_count = pocs.filter(status__in=['planned', 'ongoing']).count()
    
    # Get Tickets
    tickets = Ticket.objects.filter(customer=customer).select_related('assigned_to').order_by('-created_at')
    open_tickets_count = tickets.exclude(status__in=['resolved', 'closed', 'rejected']).count()
    
    # Get Notes
    notes = CustomerNote.objects.filter(customer=customer).select_related('author').order_by('-created_at')
    
    # Stats
    total_won_value = won_deals.aggregate(total=Sum('retail'))['total'] or 0
    
    context = {
        'customer': customer,
        'active_deals': active_deals,
        'all_deals': all_deals,
        'active_deals_count': active_deals.count(),
        'proposals': proposals,
        'activities': all_activities,
        'recent_activities': recent_activities,
        'pocs': pocs,
        'pocs_count': active_pocs_count,
        'tickets': tickets,
        'open_tickets_count': open_tickets_count,
        'notes': notes,
        'total_won_value': total_won_value,
    }
    return render(request, 'customers/customer_detail.html', context)
