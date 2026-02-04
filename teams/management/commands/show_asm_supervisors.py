"""
Django management command to show groups with ASM supervisors.
Useful for tracking temporary ASM supervisors and planning transitions to permanent supervisors.

Usage:
    python manage.py show_asm_supervisors
"""
from django.core.management.base import BaseCommand
from teams.models import Group
from users.models import User


class Command(BaseCommand):
    help = 'Show groups that have ASM users acting as supervisors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--team',
            type=str,
            help='Filter by team name',
        )
        parser.add_argument(
            '--transition',
            type=int,
            help='Transition group ID from ASM supervisor to new supervisor (requires --new-supervisor)',
        )
        parser.add_argument(
            '--new-supervisor',
            type=int,
            help='User ID of the new supervisor to assign',
        )

    def handle(self, *args, **options):
        # Filter groups with ASM supervisors
        queryset = Group.objects.filter(supervisor__role='asm').select_related('supervisor', 'team')
        
        if options['team']:
            queryset = queryset.filter(team__name__icontains=options['team'])

        asm_supervised_groups = queryset.all()

        if not asm_supervised_groups:
            self.stdout.write(
                self.style.SUCCESS('✅ No groups found with ASM supervisors.')
            )
            return

        # Handle transition if requested
        if options['transition'] and options['new_supervisor']:
            try:
                group = Group.objects.get(id=options['transition'])
                new_supervisor = User.objects.get(id=options['new_supervisor'], role='supervisor')
                
                if group.supervisor.role != 'asm':
                    self.stdout.write(
                        self.style.ERROR(f'❌ Group "{group.name}" does not have an ASM supervisor.')
                    )
                    return
                
                old_supervisor = group.supervisor
                group.supervisor = new_supervisor
                group.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Successfully transitioned group "{group.name}" from '
                        f'ASM supervisor "{old_supervisor.get_full_name()}" to '
                        f'supervisor "{new_supervisor.get_full_name()}"'
                    )
                )
                return
                
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Group with ID {options["transition"]} not found.')
                )
                return
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Supervisor user with ID {options["new_supervisor"]} not found.')
                )
                return

        # Display report
        self.stdout.write('\n📋 Groups with ASM Supervisors (Temporary Arrangements):')
        self.stdout.write('=' * 70)
        
        for group in asm_supervised_groups:
            self.stdout.write(f'\n🏢 Team: {group.team.name}')
            self.stdout.write(f'   📁 Group: {group.name}')
            self.stdout.write(f'   👤 ASM Supervisor: {group.supervisor.get_full_name()} ({group.supervisor.username})')
            self.stdout.write(f'   👥 Members: {group.members.count()}')
            self.stdout.write(f'   🆔 Group ID: {group.id}')
            
            if group.teamlead:
                self.stdout.write(f'   🏅 Team Lead: {group.teamlead.get_full_name()}')

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(f'📊 Total groups with ASM supervisors: {len(asm_supervised_groups)}')
        
        # Show available supervisors for transition
        available_supervisors = User.objects.filter(role='supervisor')
        if available_supervisors.exists():
            self.stdout.write('\n👨‍💼 Available Supervisors for Transition:')
            for supervisor in available_supervisors:
                supervised_groups = supervisor.managed_groups.count()
                self.stdout.write(f'   • {supervisor.get_full_name()} (ID: {supervisor.id}) - Managing {supervised_groups} groups')
        
        self.stdout.write('\n💡 To transition a group to a permanent supervisor:')
        self.stdout.write('   python manage.py show_asm_supervisors --transition GROUP_ID --new-supervisor SUPERVISOR_ID')
        self.stdout.write('\nExample:')
        self.stdout.write('   python manage.py show_asm_supervisors --transition 5 --new-supervisor 12')
