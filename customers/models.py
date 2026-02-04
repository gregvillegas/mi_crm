from django.db import models
from users.models import User
import json

class Customer(models.Model):
    INDUSTRY_CHOICES = [
		('agriculture','Agriculture & Agribusiness'),
		('automotive','Automotive'),
		('business','Business Process Outsourcing (BPO)'),
		('construction','Construction & Engineering'),
		('defense','Defense & Security'),
		('digital','Digital Services / IT Services'),
		('education','Education & Training'),
		('energy','Energy & Power'),
		('financial','Financial Services & Banking'),
		('government','Government & Public Sector'),
		('healthcare','Healthcare & Medical Services'),
		('hospitality','Hospitality & Tourism'),
		('manufacturing','Manufacturing'),
		('media','Media, Entertainment & Publishing'),
		('mining','Mining & Quarrying'),
		('pharmaceuticals','Pharmaceuticals & Life Sciences'),
		('realestate','Real Estate & Property Development'),
		('retail','Retail & E-commerce'),
		('general','General Services <for consultancy, repair, logistics, etc.>'),
		('technology','Technology <Hardware & Software>'),
		('telecommunications','Telecommunications'),
		('transportation','Transportation & Logistics'),
		('utilities','Utilities <Water, Gas, Electricity>'),
		('wholesale','Wholesale & Distribution'),
		('others','Others <or anything not covered>'),
    ]
    
    TERRITORY_CHOICES = [
		('caloocan','Caloocan'),
		('laspinas','Las Piñas'),
		('makati','Makati'),
		('malabon','Malabon'),
		('mandaluyong','Mandaluyong'),
		('manila','Manila (capital city)'),
		('marikina','Marikina'),
		('muntinlupa','Muntinlupa'),
		('navotas','Navotas'),
		('paranaque','Parañaque'),
		('pasay','Pasay'),
		('pasig','Pasig'),
		('quezoncity','Quezon City'),
		('sanjuan','San Juan'),
		('taguig','Taguig'),
		('valenzuela','Valenzuela'),
		('outsidencr','Outside NCR'),
    ]
    
    # Basic Information
    company_name = models.CharField(max_length=100)
    contact_person_name = models.CharField(max_length=100)
    contact_person_position = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Contact person's job title or position"
    )
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    # Business Information
    industry = models.CharField(
        max_length=50, 
        choices=INDUSTRY_CHOICES, 
        blank=True,
        help_text="Customer's industry sector"
    )
    territory = models.CharField(
        max_length=50, 
        choices=TERRITORY_CHOICES, 
        blank=True,
        help_text="Geographic territory/area"
    )
    
    # Status and Classification
    is_vip = models.BooleanField(
        default=False, 
        verbose_name='VIP/Millionaire Account',
        help_text='Mark as VIP or high-value millionaire account for special handling'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this customer account is active'
    )
    
    # Assignment
    salesperson = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='customers', 
        limit_choices_to={'role': 'salesperson', 'is_active': True}
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_vip']),
            models.Index(fields=['is_active']),
            models.Index(fields=['industry']),
            models.Index(fields=['territory']),
        ]

    def __str__(self):
        status_indicators = []
        if self.is_vip:
            status_indicators.append('VIP')
        if not self.is_active:
            status_indicators.append('INACTIVE')
        
        name = f"{self.company_name} ({self.contact_person_name})"
        if status_indicators:
            name += f" [{', '.join(status_indicators)}]"
        return name
    
    @property
    def full_name(self):
        return f"{self.company_name} ({self.contact_person_name})"
    
    @property
    def display_status(self):
        """Return a human-readable status string"""
        if self.is_vip and self.is_active:
            return "VIP Active"
        elif self.is_vip and not self.is_active:
            return "VIP Inactive"
        elif not self.is_vip and self.is_active:
            return "Active"
        else:
            return "Inactive"
    
    def create_backup(self, changed_by, reason="Manual backup"):
        """Create a backup of the current customer state"""
        backup_data = {
            'company_name': self.company_name,
            'contact_person_name': self.contact_person_name,
            'contact_person_position': self.contact_person_position,
            'email': self.email,
            'phone_number': self.phone_number,
            'address': self.address,
            'industry': self.industry,
            'territory': self.territory,
            'is_vip': self.is_vip,
            'is_active': self.is_active,
            'salesperson_id': self.salesperson.id if self.salesperson else None,
            'salesperson_username': self.salesperson.username if self.salesperson else None,
        }
        
        return CustomerBackup.objects.create(
            customer=self,
            backup_data=json.dumps(backup_data),
            changed_by=changed_by,
            reason=reason
        )


class CustomerHistory(models.Model):
    """Model to track all changes made to customers for audit trail and salesperson credit"""
    
    ACTION_CHOICES = [
        ('created', 'Customer Created'),
        ('updated', 'Customer Updated'),
        ('vip_enabled', 'Became VIP Customer'),
        ('vip_disabled', 'VIP Status Removed'),
        ('activated', 'Customer Activated'),
        ('deactivated', 'Customer Deactivated'),
        ('salesperson_assigned', 'Salesperson Assigned'),
        ('salesperson_changed', 'Salesperson Changed'),
        ('salesperson_removed', 'Salesperson Removed'),
        ('restored', 'Restored from Backup'),
        ('imported', 'Imported from CSV'),
        ('field_updated', 'Field Updated'),
        ('deal_won', 'Deal Marked Won'),
        ('deal_lost', 'Deal Marked Lost'),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='history',
        help_text='The customer this history entry belongs to'
    )
    
    action = models.CharField(
        max_length=25,
        choices=ACTION_CHOICES,
        help_text='Type of action performed'
    )
    
    description = models.TextField(
        help_text='Detailed description of what changed'
    )
    
    # Track both the person who made the change and the salesperson at the time
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='customer_changes_made',
        help_text='The user who made this change'
    )
    
    salesperson_at_time = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_history_as_salesperson',
        help_text='The salesperson assigned to the customer at the time of this change'
    )
    
    # Store previous and new values for important changes
    old_value = models.JSONField(
        null=True,
        blank=True,
        help_text='Previous value before the change (JSON format)'
    )
    
    new_value = models.JSONField(
        null=True,
        blank=True,
        help_text='New value after the change (JSON format)'
    )
    
    # Additional context
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP address of the user who made the change'
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text='User agent string of the browser used'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='When this change occurred'
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['customer', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['salesperson_at_time', '-timestamp']),
            models.Index(fields=['changed_by', '-timestamp']),
        ]
        verbose_name = 'Customer History'
        verbose_name_plural = 'Customer Histories'

class DelinquencyRecord(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('resolved', 'Resolved'),
        ('watch', 'Watch List'),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='delinquency_records')
    salesperson = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role': 'salesperson'}, related_name='delinquency_customers')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    tin_number = models.CharField(max_length=50, blank=True)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField(null=True, blank=True)
    last_payment_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_delinquencies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['salesperson']),
        ]

    def __str__(self):
        return f"{self.customer.company_name} - {self.get_status_display()} ₱{self.amount_due}"
    
    def __str__(self):
        return f"{self.customer.company_name} - {self.get_action_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @property
    def action_icon(self):
        """Return FontAwesome icon for the action"""
        icons = {
            'created': 'fas fa-plus-circle text-success',
            'updated': 'fas fa-edit text-primary',
            'vip_enabled': 'fas fa-star text-warning',
            'vip_disabled': 'far fa-star text-muted',
            'activated': 'fas fa-toggle-on text-success',
            'deactivated': 'fas fa-toggle-off text-danger',
            'salesperson_assigned': 'fas fa-user-plus text-info',
            'salesperson_changed': 'fas fa-user-edit text-warning',
            'salesperson_removed': 'fas fa-user-minus text-secondary',
            'restored': 'fas fa-undo text-info',
            'imported': 'fas fa-file-import text-primary',
            'field_updated': 'fas fa-pencil-alt text-secondary',
        }
        return icons.get(self.action, 'fas fa-circle text-secondary')
    
    @property
    def action_color(self):
        """Return Bootstrap color class for the action"""
        colors = {
            'created': 'success',
            'updated': 'primary',
            'vip_enabled': 'warning',
            'vip_disabled': 'secondary',
            'activated': 'success',
            'deactivated': 'danger',
            'salesperson_assigned': 'info',
            'salesperson_changed': 'warning',
            'salesperson_removed': 'secondary',
            'restored': 'info',
            'imported': 'primary',
            'field_updated': 'secondary',
        }
        return colors.get(self.action, 'secondary')
    
    @classmethod
    def log_customer_change(cls, customer, action, description, changed_by=None, 
                           old_value=None, new_value=None, request=None):
        """Convenience method to log a customer change"""
        history_entry = cls(
            customer=customer,
            action=action,
            description=description,
            changed_by=changed_by,
            salesperson_at_time=customer.salesperson,
            old_value=old_value,
            new_value=new_value
        )
        
        # Extract request info if available
        if request:
            history_entry.ip_address = request.META.get('REMOTE_ADDR')
            history_entry.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Truncate if too long
        
        history_entry.save()
        return history_entry


class CustomerBackup(models.Model):
    """Model to store customer backup data for restoration purposes"""
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE,
        related_name='backups',
        help_text='The customer this backup belongs to'
    )
    backup_data = models.TextField(
        help_text='JSON data containing the customer state at backup time'
    )
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text='The user who made the change that triggered this backup'
    )
    reason = models.CharField(
        max_length=200,
        default='Manual backup',
        help_text='Reason for creating this backup'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When this backup was created'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', '-created_at']),
        ]
        verbose_name = 'Customer Backup'
        verbose_name_plural = 'Customer Backups'
    
    def __str__(self):
        return f"Backup of {self.customer.company_name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def get_backup_data(self):
        """Return the backup data as a Python dictionary"""
        try:
            return json.loads(self.backup_data)
        except json.JSONDecodeError:
            return {}
    
    def restore(self, restored_by):
        """Restore the customer to this backup state"""
        backup_data = self.get_backup_data()
        if not backup_data:
            raise ValueError("Invalid backup data")
        
        # Create a backup of current state before restoring
        self.customer.create_backup(
            changed_by=restored_by,
            reason=f"Before restore from backup {self.id}"
        )
        
        # Restore the customer data
        for field, value in backup_data.items():
            if field == 'salesperson_id' and value:
                try:
                    salesperson = User.objects.get(id=value, role='salesperson')
                    self.customer.salesperson = salesperson
                except User.DoesNotExist:
                    # If salesperson doesn't exist anymore, leave as null
                    self.customer.salesperson = None
            elif field not in ['salesperson_id', 'salesperson_username']:
                setattr(self.customer, field, value)
        
        self.customer.save()
        
        # Create a restoration log entry
        CustomerBackup.objects.create(
            customer=self.customer,
            backup_data=json.dumps({
                'restored_from_backup_id': self.id,
                'restored_at': self.created_at.isoformat(),
                'restored_reason': self.reason
            }),
            changed_by=restored_by,
            reason=f"Restored from backup {self.id}"
        )
