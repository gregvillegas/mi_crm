
import os
import django
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, F

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from users.models import User
from teams.models import Group, Team, TeamMembership
from sales_monitoring.models import SalesActivity
from sales_funnel.models import SalesFunnel

def test_fiscal_year_logic():
    print("Testing Fiscal Year Logic...")
    
    # 1. Setup Test Data
    # Create Team, Group, Salesperson
    try:
        user = User.objects.create(username='test_sup_fy', email='test_sup_fy@example.com', role='supervisor')
        salesperson = User.objects.create(username='test_sp_fy', email='test_sp_fy@example.com', role='salesperson')
        
        team = Team.objects.create(name='Test Team FY')
        group = Group.objects.create(name='Test Group FY', team=team, supervisor=user)
        
        membership = TeamMembership.objects.create(user=salesperson, group=group, quota=100000)
        
        # Create some won deals in different months
        # Fiscal Year 2026: Dec 2025 - Nov 2026
        
        # Deal in Dec 2025 (Should be in FY 2026)
        SalesFunnel.objects.create(
            salesperson=salesperson,
            company_name="Deal Dec 2025",
            date_created=datetime(2025, 12, 1).date(),
            deal_outcome='won',
            closed_date=datetime(2025, 12, 15).date(),
            retail=10000,
            cost=5000
        )
        
        # Deal in Jan 2026 (Should be in FY 2026)
        SalesFunnel.objects.create(
            salesperson=salesperson,
            company_name="Deal Jan 2026",
            date_created=datetime(2026, 1, 1).date(),
            deal_outcome='won',
            closed_date=datetime(2026, 1, 15).date(),
            retail=20000,
            cost=10000
        )
        
        # Deal in Nov 2026 (Should be in FY 2026)
        SalesFunnel.objects.create(
            salesperson=salesperson,
            company_name="Deal Nov 2026",
            date_created=datetime(2026, 11, 1).date(),
            deal_outcome='won',
            closed_date=datetime(2026, 11, 15).date(),
            retail=30000,
            cost=15000
        )
        
        # Deal in Dec 2026 (Should be in FY 2027, NOT 2026)
        SalesFunnel.objects.create(
            salesperson=salesperson,
            company_name="Deal Dec 2026",
            date_created=datetime(2026, 12, 1).date(),
            deal_outcome='won',
            closed_date=datetime(2026, 12, 15).date(),
            retail=40000,
            cost=20000
        )
        
    except Exception as e:
        print(f"Setup failed (might be existing data): {e}")
        # Try to retrieve if existing
        salesperson = User.objects.get(username='test_sp_fy')
        
    # 2. Simulate View Logic
    # Assume we are viewing March 2026
    month_start = datetime(2026, 3, 1).date()
    
    if month_start.month == 12:
        fiscal_year = month_start.year + 1
    else:
        fiscal_year = month_start.year
        
    print(f"Selected Month: {month_start}")
    print(f"Calculated Fiscal Year: {fiscal_year}")
    
    fiscal_start = datetime(fiscal_year - 1, 12, 1).date()
    fiscal_end = datetime(fiscal_year, 11, 30).date()
    
    print(f"Fiscal Range: {fiscal_start} to {fiscal_end}")
    
    fiscal_months = []
    curr = fiscal_start
    for _ in range(12):
        fiscal_months.append({
            'date': curr,
            'label': curr.strftime('%b').upper(), 
        })
        if curr.month == 12:
            curr = curr.replace(year=curr.year + 1, month=1)
        else:
            curr = curr.replace(month=curr.month + 1)
            
    print("Fiscal Months:", [m['label'] for m in fiscal_months])
    
    # Calculate Data
    monthly_data = []
    sp_fiscal_deals = SalesFunnel.objects.filter(
        salesperson=salesperson,
        deal_outcome='won',
        closed_date__gte=fiscal_start,
        closed_date__lte=fiscal_end
    )
    
    print(f"Total Won Deals in Fiscal Year: {sp_fiscal_deals.count()}")
    
    for m in fiscal_months:
        m_start = m['date']
        if m_start.month == 12:
                m_end = m_start.replace(year=m_start.year + 1, month=1) - timedelta(days=1)
        else:
                m_end = m_start.replace(month=m_start.month + 1) - timedelta(days=1)
        
        m_profit = sp_fiscal_deals.filter(
            closed_date__gte=m_start,
            closed_date__lte=m_end
        ).aggregate(total=Sum(F('retail') - F('cost')))['total'] or 0
        
        monthly_data.append(m_profit)
        print(f"  {m['label']}: {m_profit}")

    # Verify results
    # Dec 2025: 5000 profit
    # Jan 2026: 10000 profit
    # Nov 2026: 15000 profit
    # Dec 2026: Should not be included
    
    if monthly_data[0] == 5000 and monthly_data[1] == 10000 and monthly_data[11] == 15000:
        print("\nSUCCESS: Fiscal year data calculated correctly.")
    else:
        print(f"\nFAILURE: Data mismatch. Expected [5000, 10000, ..., 15000]. Got {monthly_data}")

    # Cleanup
    # Clean up created objects
    SalesFunnel.objects.filter(salesperson=salesperson).delete()
    TeamMembership.objects.filter(user=salesperson).delete()
    Group.objects.filter(name='Test Group FY').delete()
    Team.objects.filter(name='Test Team FY').delete()
    User.objects.filter(username__in=['test_sup_fy', 'test_sp_fy']).delete()

if __name__ == "__main__":
    test_fiscal_year_logic()
