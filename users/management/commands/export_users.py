import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.hashers import check_password
from django.db import transaction
from users.models import User
from teams.models import Team, Group, TeamMembership
from customers.models import Customer


class Command(BaseCommand):
    help = 'Export all users, teams, groups, and relationships to JSON for production deployment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: users_export_YYYY-MM-DD.json)',
        )
        parser.add_argument(
            '--include-passwords',
            action='store_true',
            help='Include hashed passwords in export (for complete migration)',
        )
        parser.add_argument(
            '--include-inactive',
            action='store_true',
            help='Include inactive users in export',
        )
        parser.add_argument(
            '--pretty',
            action='store_true',
            help='Pretty print JSON output',
        )

    def handle(self, *args, **options):
        try:
            # Generate default filename if not provided
            if not options['output']:
                timestamp = datetime.now().strftime('%Y-%m-%d')
                options['output'] = f'users_export_{timestamp}.json'

            self.stdout.write('Starting comprehensive user export...\n')

            # Collect all data
            export_data = self.collect_export_data(options)
            
            # Write to file
            self.write_export_file(export_data, options)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Export completed successfully!'
                    f'\n📁 File: {options["output"]}'
                    f'\n👥 Users exported: {len(export_data["users"])}'
                    f'\n🏢 Teams exported: {len(export_data["teams"])}'
                    f'\n👨‍💼 Groups exported: {len(export_data["groups"])}'
                    f'\n🔗 Memberships exported: {len(export_data["memberships"])}'
                    f'\n👤 Customer assignments: {export_data["statistics"]["customer_assignments"]}'
                )
            )
            
        except Exception as e:
            raise CommandError(f'Export failed: {str(e)}')

    def collect_export_data(self, options):
        """Collect all user-related data for export"""
        
        # Get users based on options
        users_queryset = User.objects.all()
        if not options['include_inactive']:
            users_queryset = users_queryset.filter(is_active=True)
        
        users_queryset = users_queryset.order_by('id')
        
        export_data = {
            'export_info': {
                'timestamp': datetime.now().isoformat(),
                'django_version': self.get_django_version(),
                'total_users': users_queryset.count(),
                'include_passwords': options['include_passwords'],
                'include_inactive': options['include_inactive'],
            },
            'users': [],
            'teams': [],
            'groups': [],
            'memberships': [],
            'statistics': {}
        }

        # Export Users
        self.stdout.write('📊 Exporting users...')
        customer_assignments = 0
        
        for user in users_queryset:
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'initials': user.initials,
                'role': user.role,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
            }
            
            # Include password hash if requested
            if options['include_passwords']:
                user_data['password_hash'] = user.password
            
            # Count customer assignments
            customer_count = Customer.objects.filter(salesperson=user).count()
            user_data['customer_count'] = customer_count
            customer_assignments += customer_count
            
            export_data['users'].append(user_data)
            
            if len(export_data['users']) % 10 == 0:
                self.stdout.write(f'  Exported {len(export_data["users"])} users...')

        # Export Teams
        self.stdout.write('🏢 Exporting teams...')
        for team in Team.objects.all().order_by('id'):
            team_data = {
                'id': team.id,
                'name': team.name,
                'avp_id': team.avp.id if team.avp else None,
                'avp_username': team.avp.username if team.avp else None,
                'asm_id': team.asm.id if team.asm else None,
                'asm_username': team.asm.username if team.asm else None,
            }
            
            export_data['teams'].append(team_data)

        # Export Groups
        self.stdout.write('👥 Exporting groups...')
        for group in Group.objects.all().select_related('team', 'supervisor', 'teamlead').order_by('id'):
            group_data = {
                'id': group.id,
                'name': group.name,
                'group_type': group.group_type,
                'team_id': group.team.id if group.team else None,
                'team_name': group.team.name if group.team else None,
                'supervisor_id': group.supervisor.id if group.supervisor else None,
                'supervisor_username': group.supervisor.username if group.supervisor else None,
                'teamlead_id': group.teamlead.id if group.teamlead else None,
                'teamlead_username': group.teamlead.username if group.teamlead else None,
                # For TSG groups, include AVP info
                'manager_id': group.get_manager().id if group.get_manager() else None,
                'manager_username': group.get_manager().username if group.get_manager() else None,
                'manager_role': group.get_manager_role(),
                'is_tsg': group.is_tsg(),
            }
            export_data['groups'].append(group_data)

        # Export Team Memberships
        self.stdout.write('🔗 Exporting team memberships...')
        for membership in TeamMembership.objects.all().select_related('user', 'group').order_by('id'):
            membership_data = {
                'id': membership.id,
                'user_id': membership.user.id,
                'user_username': membership.user.username,
                'group_id': membership.group.id,
                'group_name': membership.group.name,
            }
            export_data['memberships'].append(membership_data)

        # Calculate statistics
        export_data['statistics'] = {
            'total_users': len(export_data['users']),
            'active_users': len([u for u in export_data['users'] if u['is_active']]),
            'inactive_users': len([u for u in export_data['users'] if not u['is_active']]),
            'superusers': len([u for u in export_data['users'] if u['is_superuser']]),
            'staff_users': len([u for u in export_data['users'] if u['is_staff']]),
            'customer_assignments': customer_assignments,
            'role_breakdown': self.get_role_breakdown(export_data['users']),
        }

        return export_data

    def get_role_breakdown(self, users):
        """Get breakdown of users by role"""
        roles = {}
        for user in users:
            role = user['role']
            if role in roles:
                roles[role] += 1
            else:
                roles[role] = 1
        return roles

    def get_django_version(self):
        """Get Django version"""
        try:
            import django
            return django.get_version()
        except:
            return 'unknown'

    def write_export_file(self, export_data, options):
        """Write export data to JSON file"""
        try:
            with open(options['output'], 'w', encoding='utf-8') as f:
                if options['pretty']:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(export_data, f, ensure_ascii=False)
            
            # Make file readable
            os.chmod(options['output'], 0o644)
            
        except Exception as e:
            raise CommandError(f'Failed to write export file: {str(e)}')
