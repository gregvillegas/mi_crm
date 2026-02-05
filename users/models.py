from django.contrib.auth.models import AbstractUser, Group as AuthGroup, Permission
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('avp', 'AVP'),
        ('supervisor', 'Supervisor'),
        ('salesperson', 'Salesperson'),
        ('vp', 'Vice President'),
        ('gm', 'General Manager'),
        ('president', 'President'),
        ('asm', 'ASM'),
        ('sm', 'Sales Manager'),
        ('teamlead', 'Teamlead'),
        ('techmgr', 'Technical Manager'),
        ('asst_techmgr', 'Assistant Technical Manager'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='salesperson')
    initials = models.CharField(max_length=3, blank=True, help_text='3-letter initials for the user (e.g., JDO for John Doe)')
    is_active = models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')

    # Add related_name to resolve clashes with the default User model
    groups = models.ManyToManyField(
        AuthGroup,
        verbose_name='groups',
        blank=True,
        help_text=(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="custom_user_set", # <--- FIX
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="custom_user_set", # <--- FIX
        related_query_name="user",
    )
