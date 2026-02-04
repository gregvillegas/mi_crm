from django.db import models
from users.models import User

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    avp = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_teams', limit_choices_to={'role__in': ['avp', 'vp', 'gm', 'president']})
    asm = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='asm_teams', blank=True, null=True, limit_choices_to={'role': 'asm'})

    def __str__(self):
        return self.name

class Group(models.Model):
    # Group type choices
    GROUP_TYPE_CHOICES = [
        ('regular', 'Regular Sales Group'),
        ('tsg', 'Technical Sales Group'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='groups')
    
    # Group type field
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES, default='regular',
                              help_text='Regular groups have supervisors, TSG groups are managed directly by AVPs')
    
    # Supervisor field for regular groups (can be null for TSG groups)
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_groups', 
                                limit_choices_to={'role__in': ['supervisor', 'asm']},
                                null=True, blank=True,
                                help_text='Required for regular groups, not used for TSG groups')
    
    # Teamlead stays the same for all group types
    teamlead = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='led_groups', 
                             blank=True, null=True, limit_choices_to={'role': 'teamlead'})

    def __str__(self):
        if self.group_type == 'tsg':
            return f"{self.name} [TSG - {self.team.name}]"
        return f"{self.name} ({self.team.name})"
        
    def get_manager(self):
        """Return the manager of this group - either supervisor (regular) or AVP (TSG)"""
        if self.group_type == 'tsg':
            return self.team.avp  # TSG groups managed by team's AVP
        return self.supervisor  # Regular groups managed by supervisor
        
    def get_manager_role(self):
        """Return the role title of the manager"""
        if self.group_type == 'tsg':
            return 'AVP'  # TSG groups managed by AVP
        elif self.supervisor and self.supervisor.role == 'asm':
            return 'ASM (Acting Supervisor)'  # ASM acting as supervisor
        return 'Supervisor'  # Regular groups managed by supervisor
        
    def is_tsg(self):
        """Check if this is a Technical Sales Group"""
        return self.group_type == 'tsg'
        
    def clean(self):
        """Validate the group configuration"""
        from django.core.exceptions import ValidationError
        
        if self.group_type == 'tsg':
            # TSG groups should not have a supervisor
            if self.supervisor:
                raise ValidationError("TSG groups are managed by AVPs, not supervisors. Leave supervisor field empty.")
        else:
            # Regular groups must have a supervisor
            if not self.supervisor:
                raise ValidationError("Regular groups must have a supervisor assigned.")
        
    def save(self, *args, **kwargs):
        self.clean()  # Validate before saving
        super().save(*args, **kwargs)
        
    class Meta:
        ordering = ['team__name', 'group_type', 'name']

class TeamMembership(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='team_membership')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='members')
    quota = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Sales quota for this user in this group (Profit based)"
    )

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"

class SupervisorCommitment(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='supervisor_commitments')
    supervisor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='monthly_commitments',
        limit_choices_to={'role__in': ['supervisor', 'asm']}
    )
    month = models.DateField()
    target_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.supervisor.username} {self.month.strftime('%Y-%m')} {self.group.name}"

    class Meta:
        unique_together = ('group', 'month')
        ordering = ['-month']

class SupervisorCommitmentLog(models.Model):
    CHANGE_CHOICES = [
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
        ('no_change', 'No Change'),
    ]
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='commitment_logs')
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commitment_logs')
    month = models.DateField()
    previous_target = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    new_target = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    change_type = models.CharField(max_length=20, choices=CHANGE_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commitment_changes')
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.group.name} {self.month.strftime('%Y-%m')} {self.change_type} {self.previous_target}->{self.new_target}"

    class Meta:
        ordering = ['-changed_at']

class PersonalContribution(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='personal_contributions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_contributions', limit_choices_to={'role__in': ['avp', 'asm']})
    month = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} {self.group.name} {self.month.strftime('%Y-%m')} ₱{self.amount}"

    class Meta:
        unique_together = ('group', 'user', 'month')
        ordering = ['-month']

class AsmPersonalTarget(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='asm_targets')
    asm = models.ForeignKey(User, on_delete=models.CASCADE, related_name='asm_team_targets', limit_choices_to={'role': 'asm'})
    month = models.DateField()
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.team.name} ASM {self.asm.username} {self.month.strftime('%Y-%m')} ₱{self.target_amount}"
    
    class Meta:
        unique_together = ('team', 'asm', 'month')
        ordering = ['-month']

class RoleMonthlyQuota(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='role_monthly_quotas', limit_choices_to={'role__in': ['supervisor', 'asm', 'avp']})
    month = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'month')
        ordering = ['-month']

    def __str__(self):
        return f"{self.user.username} {self.month.strftime('%Y-%m')} ₱{self.amount}"
