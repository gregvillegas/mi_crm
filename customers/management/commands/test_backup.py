from django.core.management.base import BaseCommand
from customers.models import Customer, CustomerBackup
from users.models import User


class Command(BaseCommand):
    help = 'Test the customer backup functionality'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Customer Backup Functionality'))
        
        # Get the admin user
        try:
            admin_user = User.objects.filter(role='admin').first()
            if not admin_user:
                self.stdout.write(self.style.ERROR('No admin user found'))
                return
            
            self.stdout.write(f'Using admin user: {admin_user.username}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting admin user: {e}'))
            return
        
        # Get the first customer
        try:
            customer = Customer.objects.first()
            if not customer:
                self.stdout.write(self.style.WARNING('No customers found'))
                return
            
            self.stdout.write(f'Testing with customer: {customer.full_name}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting customer: {e}'))
            return
        
        # Test backup creation
        try:
            backup = customer.create_backup(
                changed_by=admin_user,
                reason="Test backup from management command"
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Backup created successfully with ID: {backup.id}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error creating backup: {e}'))
            return
        
        # Test backup data retrieval
        try:
            backup_data = backup.get_backup_data()
            self.stdout.write(self.style.SUCCESS('✅ Backup data retrieved successfully:'))
            for key, value in backup_data.items():
                self.stdout.write(f'  {key}: {value}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error retrieving backup data: {e}'))
            return
        
        # Test listing backups
        try:
            all_backups = CustomerBackup.objects.filter(customer=customer)
            self.stdout.write(self.style.SUCCESS(f'✅ Customer has {all_backups.count()} backups'))
            
            for backup in all_backups[:3]:  # Show first 3 backups
                self.stdout.write(f'  - {backup.created_at} by {backup.changed_by}: {backup.reason}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error listing backups: {e}'))
        
        # Test data modification and backup
        try:
            original_name = customer.company_name
            customer.company_name = "Test Modified Name"
            
            # Create backup before change
            pre_change_backup = customer.create_backup(
                changed_by=admin_user,
                reason="Before test modification"
            )
            
            customer.save()
            self.stdout.write(self.style.SUCCESS('✅ Customer name modified and backup created'))
            
            # Restore original name
            customer.company_name = original_name
            customer.save()
            
            self.stdout.write(self.style.SUCCESS('✅ Customer name restored to original'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error in modification test: {e}'))
        
        # Final statistics
        try:
            total_customers = Customer.objects.count()
            total_backups = CustomerBackup.objects.count()
            customers_with_backups = Customer.objects.filter(backups__isnull=False).distinct().count()
            
            self.stdout.write(self.style.SUCCESS('\n📊 BACKUP SYSTEM STATISTICS:'))
            self.stdout.write(f'Total customers: {total_customers}')
            self.stdout.write(f'Total backups: {total_backups}')
            self.stdout.write(f'Customers with backups: {customers_with_backups}')
            self.stdout.write(f'Coverage: {round((customers_with_backups * 100) / total_customers if total_customers > 0 else 0)}%')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error getting statistics: {e}'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Backup system test completed successfully!'))
