import json
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.hashers import make_password
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import User
from teams.models import Team, Group, TeamMembership


class Command(BaseCommand):
    help = 'Import users, teams, groups, and relationships from JSON export file'

    def add_arguments(self, parser):
        parser.add_argument(
            'import_file',
            type=str,
            help='Path to the JSON export file to import',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without making any changes',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing users instead of skipping them',
        )
        parser.add_argument(
            '--default-password',
            type=str,
            default='ChangeMe123!',
            help='Default password for users without password hashes (default: ChangeMe123!)',
        )
        parser.add_argument(
            '--skip-relationships',
            action='store_true',
            help='Skip importing team relationships and memberships',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force import even if validation warnings exist',
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write('Starting user import process...\n')
            
            # Load and validate import file
            import_data = self.load_import_file(options['import_file'])
            
            # Validate import data
            validation_result = self.validate_import_data(import_data, options)
            
            if not validation_result['valid'] and not options['force']:
                raise CommandError('Import validation failed. Use --force to override.')
            
            # Perform import
            if options['dry_run']:
                self.perform_dry_run(import_data, options)
            else:
                self.perform_import(import_data, options)
                
        except FileNotFoundError:
            raise CommandError(f'Import file not found: {options["import_file"]}')
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON file: {str(e)}')
        except Exception as e:
            raise CommandError(f'Import failed: {str(e)}')

    def load_import_file(self, file_path):
        """Load and parse the import JSON file"""
        self.stdout.write(f'📁 Loading import file: {file_path}')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate basic structure
        required_keys = ['export_info', 'users', 'teams', 'groups', 'memberships']
        for key in required_keys:
            if key not in data:
                raise CommandError(f'Invalid import file: missing "{key}" section')
        
        self.stdout.write(f'✅ Import file loaded successfully')
        self.stdout.write(f'   📊 Export date: {data["export_info"].get("timestamp", "unknown")}')
        self.stdout.write(f'   👥 Users to import: {len(data["users"])}')
        self.stdout.write(f'   🏢 Teams to import: {len(data["teams"])}')
        self.stdout.write(f'   👨‍💼 Groups to import: {len(data["groups"])}')
        self.stdout.write(f'   🔗 Memberships to import: {len(data["memberships"])}')
        
        return data

    def validate_import_data(self, import_data, options):
        """Validate the import data for potential issues"""
        self.stdout.write('\\n🔍 Validating import data...')
        
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Check for duplicate usernames
        usernames = [user['username'] for user in import_data['users']]
        duplicate_usernames = set([x for x in usernames if usernames.count(x) > 1])
        if duplicate_usernames:
            validation_result['errors'].append(f'Duplicate usernames in import: {duplicate_usernames}')
            validation_result['valid'] = False
        
        # Check for existing users
        existing_users = []
        for user in import_data['users']:
            if User.objects.filter(username=user['username']).exists():
                existing_users.append(user['username'])
        
        if existing_users:
            if options['update_existing']:
                validation_result['warnings'].append(f'{len(existing_users)} existing users will be updated')
            else:
                validation_result['warnings'].append(f'{len(existing_users)} existing users will be skipped')
        
        # Check password availability
        users_without_passwords = [u for u in import_data['users'] if 'password_hash' not in u]
        if users_without_passwords:
            validation_result['warnings'].append(
                f'{len(users_without_passwords)} users will get default password: {options["default_password"]}'
            )
        
        # Display validation results
        if validation_result['errors']:
            self.stdout.write(self.style.ERROR('❌ Validation Errors:'))
            for error in validation_result['errors']:
                self.stdout.write(self.style.ERROR(f'   • {error}'))
        
        if validation_result['warnings']:
            self.stdout.write(self.style.WARNING('⚠️  Validation Warnings:'))
            for warning in validation_result['warnings']:
                self.stdout.write(self.style.WARNING(f'   • {warning}'))
        
        if validation_result['valid'] and not validation_result['warnings']:
            self.stdout.write(self.style.SUCCESS('✅ Validation passed - ready to import'))
        
        return validation_result

    def perform_dry_run(self, import_data, options):
        """Perform a dry run to show what would be imported"""
        self.stdout.write(self.style.WARNING('\\n🔍 DRY RUN - No changes will be made\\n'))
        
        # Simulate user imports
        for user in import_data['users']:
            username = user['username']
            role = user['role']
            
            if User.objects.filter(username=username).exists():
                if options['update_existing']:
                    self.stdout.write(f'  🔄 Would update user: {username} ({role})')
                else:
                    self.stdout.write(f'  ⏭️  Would skip existing user: {username} ({role})')
            else:
                self.stdout.write(f'  ✅ Would create user: {username} ({role})')
        
        self.stdout.write(f'\\n📊 Dry run summary:')
        self.stdout.write(f'   Users to process: {len(import_data["users"])}')
        self.stdout.write(f'   Teams to process: {len(import_data["teams"])}')
        self.stdout.write(f'   Groups to process: {len(import_data["groups"])}')
        self.stdout.write(f'   Memberships to process: {len(import_data["memberships"])}')

    def perform_import(self, import_data, options):
        """Perform the actual import with transaction safety"""
        self.stdout.write('\\n🚀 Starting import process...\\n')
        
        stats = {
            'users_created': 0,
            'users_updated': 0,
            'users_skipped': 0,
            'teams_created': 0,
            'groups_created': 0,
            'memberships_created': 0,
            'errors': []
        }
        
        try:
            with transaction.atomic():
                # Import users first
                self.import_users(import_data['users'], options, stats)
                
                if not options['skip_relationships']:
                    # Import teams
                    self.import_teams(import_data['teams'], options, stats)
                    
                    # Import groups
                    self.import_groups(import_data['groups'], options, stats)
                    
                    # Import memberships
                    self.import_memberships(import_data['memberships'], options, stats)
                
                # Display final results
                self.display_import_results(stats)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Import failed and was rolled back: {str(e)}'))
            raise

    def import_users(self, users_data, options, stats):
        """Import user accounts"""
        self.stdout.write('👥 Importing users...')
        
        for user_data in users_data:
            try:
                username = user_data['username']
                existing_user = User.objects.filter(username=username).first()
                
                if existing_user:
                    if options['update_existing']:
                        self.update_user(existing_user, user_data, options)
                        stats['users_updated'] += 1
                        self.stdout.write(f'  🔄 Updated: {username}')
                    else:
                        stats['users_skipped'] += 1
                        self.stdout.write(f'  ⏭️  Skipped: {username} (already exists)')
                else:
                    self.create_user(user_data, options)
                    stats['users_created'] += 1
                    self.stdout.write(f'  ✅ Created: {username}')
                    
            except Exception as e:
                error_msg = f'Failed to import user {user_data.get("username", "unknown")}: {str(e)}'
                stats['errors'].append(error_msg)
                self.stdout.write(self.style.ERROR(f'  ❌ {error_msg}'))

    def create_user(self, user_data, options):
        """Create a new user"""
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            initials=user_data.get('initials', ''),
            role=user_data['role'],
            is_active=user_data['is_active'],
            is_staff=user_data['is_staff'],
            is_superuser=user_data['is_superuser'],
        )
        
        # Set password
        if 'password_hash' in user_data and user_data['password_hash']:
            user.password = user_data['password_hash']
        else:
            user.password = make_password(options['default_password'])
        
        # Set dates
        if user_data.get('date_joined'):
            user.date_joined = datetime.fromisoformat(user_data['date_joined'])
        
        user.full_clean()
        user.save()

    def update_user(self, user, user_data, options):
        """Update an existing user"""
        user.email = user_data['email']
        user.first_name = user_data['first_name']
        user.last_name = user_data['last_name']
        user.initials = user_data.get('initials', '')
        user.role = user_data['role']
        user.is_active = user_data['is_active']
        user.is_staff = user_data['is_staff']
        user.is_superuser = user_data['is_superuser']
        
        # Only update password if provided in import
        if 'password_hash' in user_data and user_data['password_hash']:
            user.password = user_data['password_hash']
        
        user.full_clean()
        user.save()

    def import_teams(self, teams_data, options, stats):
        """Import teams"""
        self.stdout.write('🏢 Importing teams...')
        
        for team_data in teams_data:
            try:
                team, created = Team.objects.get_or_create(
                    name=team_data['name'],
                    defaults={
                        'description': team_data['description'],
                    }
                )
                
                # Set AVP if specified
                if team_data.get('avp_username'):
                    try:
                        avp = User.objects.get(username=team_data['avp_username'])
                        team.avp = avp
                        team.save()
                    except User.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'  ⚠️  AVP not found: {team_data["avp_username"]}'))
                
                # Add ASMs
                if team_data.get('asm_usernames'):
                    for asm_username in team_data['asm_usernames']:
                        try:
                            asm = User.objects.get(username=asm_username)
                            team.asms.add(asm)
                        except User.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f'  ⚠️  ASM not found: {asm_username}'))
                
                if created:
                    stats['teams_created'] += 1
                    self.stdout.write(f'  ✅ Created team: {team.name}')
                else:
                    self.stdout.write(f'  🔄 Updated team: {team.name}')
                    
            except Exception as e:
                error_msg = f'Failed to import team {team_data.get("name", "unknown")}: {str(e)}'
                stats['errors'].append(error_msg)
                self.stdout.write(self.style.ERROR(f'  ❌ {error_msg}'))

    def import_groups(self, groups_data, options, stats):
        """Import groups"""
        self.stdout.write('👨‍💼 Importing groups...')
        
        for group_data in groups_data:
            try:
                # Find team
                team = None
                if group_data.get('team_name'):
                    team = Team.objects.filter(name=group_data['team_name']).first()
                
                group, created = Group.objects.get_or_create(
                    name=group_data['name'],
                    defaults={
                        'description': group_data['description'],
                        'team': team,
                    }
                )
                
                # Set supervisor and teamlead
                if group_data.get('supervisor_username'):
                    try:
                        supervisor = User.objects.get(username=group_data['supervisor_username'])
                        group.supervisor = supervisor
                    except User.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'  ⚠️  Supervisor not found: {group_data["supervisor_username"]}'))
                
                if group_data.get('teamlead_username'):
                    try:
                        teamlead = User.objects.get(username=group_data['teamlead_username'])
                        group.teamlead = teamlead
                    except User.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'  ⚠️  Team lead not found: {group_data["teamlead_username"]}'))
                
                group.save()
                
                if created:
                    stats['groups_created'] += 1
                    self.stdout.write(f'  ✅ Created group: {group.name}')
                else:
                    self.stdout.write(f'  🔄 Updated group: {group.name}')
                    
            except Exception as e:
                error_msg = f'Failed to import group {group_data.get("name", "unknown")}: {str(e)}'
                stats['errors'].append(error_msg)
                self.stdout.write(self.style.ERROR(f'  ❌ {error_msg}'))

    def import_memberships(self, memberships_data, options, stats):
        """Import team memberships"""
        self.stdout.write('🔗 Importing team memberships...')
        
        for membership_data in memberships_data:
            try:
                # Find user and group
                user = User.objects.filter(username=membership_data['user_username']).first()
                group = Group.objects.filter(name=membership_data['group_name']).first()
                
                if not user:
                    self.stdout.write(self.style.WARNING(f'  ⚠️  User not found: {membership_data["user_username"]}'))
                    continue
                
                if not group:
                    self.stdout.write(self.style.WARNING(f'  ⚠️  Group not found: {membership_data["group_name"]}'))
                    continue
                
                membership, created = TeamMembership.objects.get_or_create(
                    user=user,
                    group=group,
                    defaults={}
                )
                
                if created:
                    stats['memberships_created'] += 1
                    self.stdout.write(f'  ✅ Added {user.username} to {group.name}')
                else:
                    self.stdout.write(f'  ⏭️  Membership already exists: {user.username} in {group.name}')
                    
            except Exception as e:
                error_msg = f'Failed to import membership: {str(e)}'
                stats['errors'].append(error_msg)
                self.stdout.write(self.style.ERROR(f'  ❌ {error_msg}'))

    def display_import_results(self, stats):
        """Display the final import results"""
        self.stdout.write('\\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('🎉 IMPORT COMPLETED'))
        self.stdout.write('='*50)
        self.stdout.write(f'👥 Users created: {stats["users_created"]}')
        self.stdout.write(f'🔄 Users updated: {stats["users_updated"]}')
        self.stdout.write(f'⏭️  Users skipped: {stats["users_skipped"]}')
        self.stdout.write(f'🏢 Teams created: {stats["teams_created"]}')
        self.stdout.write(f'👨‍💼 Groups created: {stats["groups_created"]}')
        self.stdout.write(f'🔗 Memberships created: {stats["memberships_created"]}')
        
        if stats['errors']:
            self.stdout.write(f'❌ Errors encountered: {len(stats["errors"])}')
            for error in stats['errors']:
                self.stdout.write(self.style.ERROR(f'   • {error}'))
        else:
            self.stdout.write(self.style.SUCCESS('✅ No errors encountered'))
        
        self.stdout.write('\\n🔐 IMPORTANT: Users imported without password hashes have been assigned the default password.')
        self.stdout.write('   Please remind users to change their passwords on first login.')
