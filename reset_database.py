#!/usr/bin/env python
"""
Complete database reset script for CRM system.
This script will:
1. Delete the existing database
2. Run migrations
3. Create an admin user
4. Optionally load sample data

Usage: python reset_database.py
"""
import os
import sys
import django
import subprocess
import getpass

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.management import execute_from_command_line

User = get_user_model()

def run_command(command, description):
    """Run a shell command and print the result"""
    print(f"\n📋 {description}")
    print("-" * 50)
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def reset_database():
    """Reset the database completely"""
    print("🗃️  CRM Database Reset Script")
    print("=" * 50)
    
    # Confirm with user
    confirm = input("\n⚠️  This will DELETE all existing data. Continue? (yes/no): ").lower()
    if confirm not in ['yes', 'y']:
        print("❌ Operation cancelled.")
        return False
    
    # Step 1: Remove existing database
    db_file = "db.sqlite3"
    if os.path.exists(db_file):
        print(f"\n🗑️  Removing existing database: {db_file}")
        os.remove(db_file)
        print("✅ Database removed successfully.")
    else:
        print("\n📝 No existing database found.")
    
    # Step 2: Remove migration files (optional, but clean)
    print("\n🧹 Cleaning up migration files...")
    for app in ['users', 'teams', 'customers', 'core']:
        migrations_dir = f"{app}/migrations"
        if os.path.exists(migrations_dir):
            for file in os.listdir(migrations_dir):
                if file.startswith('0') and file.endswith('.py'):
                    file_path = os.path.join(migrations_dir, file)
                    os.remove(file_path)
                    print(f"  Removed: {file_path}")
    
    # Step 3: Create fresh migrations
    if not run_command("python manage.py makemigrations", "Creating fresh migrations"):
        return False
    
    # Step 4: Run migrations
    if not run_command("python manage.py migrate", "Running migrations"):
        return False
    
    # Step 5: Create admin user
    print("\n👤 Creating Admin User")
    print("-" * 30)
    
    if not create_admin_user():
        return False
    
    print("\n✅ Database reset completed successfully!")
    print("\n🎉 Your CRM system is ready to use!")
    print("\nNext steps:")
    print("1. Run: python manage.py runserver")
    print("2. Visit: http://localhost:8000")
    print("3. Login with your admin credentials")
    
    return True

def create_admin_user():
    """Create an admin user interactively"""
    # Get username
    while True:
        username = input("Admin username: ").strip()
        if username:
            break
        print("Username cannot be empty.")
    
    # Get email (optional)
    email = input("Admin email (optional): ").strip() or None
    
    # Get password
    while True:
        password = getpass.getpass("Admin password: ")
        password_confirm = getpass.getpass("Confirm password: ")
        
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
            role='admin',  # This is the key - set role to admin!
            is_staff=True,
            is_superuser=True,
            is_active=True
        )
        
        print(f"\n✅ Admin user '{username}' created successfully!")
        print(f"   Role: {user.role}")
        print(f"   Staff: {user.is_staff}")
        print(f"   Superuser: {user.is_superuser}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False

if __name__ == '__main__':
    reset_database()
