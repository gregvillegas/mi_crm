#!/usr/bin/env python
"""
Script to create an admin user after resetting the database.
Usage: python create_admin_user.py
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth import get_user_model
import getpass

User = get_user_model()

def create_admin_user():
    print("Creating admin user for CRM system")
    print("=" * 40)
    
    # Get username
    while True:
        username = input("Username: ").strip()
        if username:
            if User.objects.filter(username=username).exists():
                print(f"User '{username}' already exists. Please choose another username.")
                continue
            break
        print("Username cannot be empty.")
    
    # Get email (optional)
    email = input("Email address (optional): ").strip() or None
    
    # Get password
    while True:
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Password (again): ")
        
        if password != password_confirm:
            print("Passwords don't match. Please try again.")
            continue
            
        if len(password) < 3:
            print("Password is too short. Please use at least 3 characters.")
            continue
            
        break
    
    try:
        # Create the admin user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role='admin',  # Set role to admin
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
        
        print("\n" + "=" * 40)
        print("✅ Admin user created successfully!")
        print(f"Username: {user.username}")
        print(f"Email: {user.email or 'Not set'}")
        print(f"Role: {user.role}")
        print(f"Staff status: {user.is_staff}")
        print(f"Superuser status: {user.is_superuser}")
        print("=" * 40)
        
        return user
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return None

if __name__ == '__main__':
    create_admin_user()
