# Admin User Setup Guide

This guide explains how to create an admin user for the CRM system, especially after deleting `db.sqlite3`.

## The Problem

When you run `python manage.py createsuperuser`, it creates a user with the default role 'salesperson' instead of 'admin' because of this line in `users/models.py`:

```python
role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='salesperson')
```

## Solutions

### Option 1: Use Custom Management Command (Recommended)

We've created a custom Django management command that creates an admin user with the correct role:

```bash
python manage.py createadmin
```

This will prompt you for:
- Username
- Email (optional)
- Password
- Password confirmation

The command automatically sets:
- `role='admin'`
- `is_staff=True`
- `is_superuser=True`
- `is_active=True`

#### Non-interactive usage:
```bash
python manage.py createadmin --username admin --email admin@example.com --noinput
```

### Option 2: Use the Standalone Script

If you prefer a standalone Python script:

```bash
python create_admin_user.py
```

This script provides the same functionality as the management command but can be run independently.

### Option 3: Complete Database Reset Script

For a complete database reset (delete db.sqlite3, run migrations, create admin):

```bash
python reset_database.py
```

This script will:
1. ⚠️  **Delete your existing database** (with confirmation)
2. Clean up old migration files
3. Create fresh migrations
4. Run migrations
5. Create an admin user
6. Provide next steps

## Manual Method (Using Django Shell)

If you prefer to do it manually:

```bash
python manage.py shell
```

Then in the shell:
```python
from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.create_user(
    username='admin',
    email='admin@example.com',  # optional
    password='your_password',
    role='admin',  # This is the key!
    is_staff=True,
    is_superuser=True,
    is_active=True
)

print(f"Admin user created: {user.username} (role: {user.role})")
```

## After Creating Admin User

1. Start the development server:
   ```bash
   python manage.py runserver
   ```

2. Visit the admin interface:
   ```
   http://localhost:8000/admin/
   ```

3. Login with your admin credentials

4. You should now have full access to:
   - Django admin interface
   - All CRM functionality
   - User management
   - Team and group management

## Verifying Admin User

To verify your admin user was created correctly:

```bash
python manage.py shell -c "
from users.models import User
admin_user = User.objects.filter(role='admin').first()
if admin_user:
    print(f'✅ Admin user found: {admin_user.username}')
    print(f'   Role: {admin_user.role}')
    print(f'   Staff: {admin_user.is_staff}')
    print(f'   Superuser: {admin_user.is_superuser}')
else:
    print('❌ No admin user found')
"
```

## Available User Roles

The CRM system supports these roles:
- `admin` - Full system access
- `president` - Executive level
- `gm` - General Manager
- `vp` - Vice President  
- `avp` - Assistant Vice President
- `asm` - Area Sales Manager
- `sm` - Sales Manager
- `supervisor` - Team Supervisor
- `teamlead` - Team Lead
- `salesperson` - Sales Representative (default)

Choose the appropriate role based on the user's responsibilities in your organization.
