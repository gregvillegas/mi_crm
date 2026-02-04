from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import CommandError
import getpass
import sys

User = get_user_model()

class Command(BaseCommand):
    help = 'Create an admin superuser with proper role'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            help='Username for the admin user',
        )
        parser.add_argument(
            '--email',
            help='Email address for the admin user',
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Don\'t prompt for user input',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email')
        noinput = options.get('noinput')
        
        if not noinput:
            # Interactive mode
            if not username:
                username = input('Username: ')
            
            if not email:
                email = input('Email address (optional): ') or None
            
            # Get password
            while True:
                password = getpass.getpass('Password: ')
                password2 = getpass.getpass('Password (again): ')
                
                if password != password2:
                    self.stderr.write('Passwords do not match. Please try again.')
                    continue
                
                if len(password) < 3:
                    self.stderr.write('Password is too short. Please try again.')
                    continue
                
                break
        else:
            # Non-interactive mode requires username and password
            if not username:
                raise CommandError('Username is required in non-interactive mode')
            password = None  # Will be set to unusable password

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User with username "{username}" already exists.')

        try:
            # Create the admin user
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role='admin',  # This is the key part - set role to admin
                is_staff=True,
                is_superuser=True,
                is_active=True
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Admin user "{username}" created successfully!')
            )
            
            # Display user info
            self.stdout.write(f'Username: {user.username}')
            self.stdout.write(f'Email: {user.email or "Not set"}')
            self.stdout.write(f'Role: {user.role}')
            self.stdout.write(f'Staff status: {user.is_staff}')
            self.stdout.write(f'Superuser status: {user.is_superuser}')
            
        except Exception as e:
            raise CommandError(f'Error creating admin user: {e}')
