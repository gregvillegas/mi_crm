#!/usr/bin/env python
"""
Script to check if admin user exists and display user information.
Usage: python check_admin.py
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def check_admin_user():
    print("🔍 Checking for admin users...")
    print("=" * 40)
    
    # Find admin users
    admin_users = User.objects.filter(role='admin')
    
    if admin_users.exists():
        print(f"✅ Found {admin_users.count()} admin user(s):")
        for user in admin_users:
            print(f"\n👤 Username: {user.username}")
            print(f"   Email: {user.email or 'Not set'}")
            print(f"   Role: {user.role}")
            print(f"   Staff: {'Yes' if user.is_staff else 'No'}")
            print(f"   Superuser: {'Yes' if user.is_superuser else 'No'}")
            print(f"   Active: {'Yes' if user.is_active else 'No'}")
    else:
        print("❌ No admin users found!")
        print("\nTo create an admin user, run one of these commands:")
        print("  python manage.py createadmin")
        print("  python create_admin_user.py")
        print("  python reset_database.py")
    
    # Show all users and their roles
    print("\n📊 All users in system:")
    print("-" * 40)
    all_users = User.objects.all().order_by('role', 'username')
    
    if all_users.exists():
        role_counts = {}
        for user in all_users:
            role = user.get_role_display()
            role_counts[role] = role_counts.get(role, 0) + 1
            status = "Active" if user.is_active else "Inactive"
            print(f"  {user.username:15} | {role:15} | {status}")
        
        print("\n📈 User role summary:")
        for role, count in sorted(role_counts.items()):
            print(f"  {role}: {count}")
    else:
        print("  No users found in system.")

if __name__ == '__main__':
    check_admin_user()
