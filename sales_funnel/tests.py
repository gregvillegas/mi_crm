import csv
import io
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from sales_funnel.models import SalesFunnel
from users.models import User


class SalesFunnelDashboardFilterTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin_sf',
            password='testpass123',
            role='admin',
            email='admin_sf@example.com',
        )
        self.salesperson = User.objects.create_user(
            username='seller_sf',
            password='testpass123',
            role='salesperson',
            email='seller_sf@example.com',
            initials='SFS',
        )
        self.client.force_login(self.admin)

        SalesFunnel.objects.create(
            date_created=date(2026, 5, 1),
            company_name='Alpha Network Systems',
            brand='Cisco',
            requirement_description='Network refresh',
            cost=Decimal('100000.00'),
            retail=Decimal('150000.00'),
            stage='quoted',
            salesperson=self.salesperson,
            probability=50,
        )
        SalesFunnel.objects.create(
            date_created=date(2026, 5, 2),
            company_name='Beta Enterprise Solutions',
            brand='IBM',
            requirement_description='Server modernization',
            cost=Decimal('200000.00'),
            retail=Decimal('300000.00'),
            stage='quoted',
            salesperson=self.salesperson,
            probability=60,
        )

    def test_dashboard_brand_filter_supports_typeable_partial_match(self):
        response = self.client.get(
            reverse('sales_funnel:dashboard'),
            {'brand': 'cis'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alpha Network Systems')
        self.assertNotContains(response, 'Beta Enterprise Solutions')
        self.assertContains(response, 'value="Cisco"', html=False)

    def test_export_uses_brand_filter_and_includes_brand_column(self):
        response = self.client.get(
            reverse('sales_funnel:export'),
            {'brand': 'ibm'},
        )

        self.assertEqual(response.status_code, 200)
        reader = csv.reader(io.StringIO(response.content.decode('utf-8')))
        rows = list(reader)

        self.assertEqual(rows[0][0:4], ['Date', 'Company', 'Brand', 'Stage'])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1], 'Beta Enterprise Solutions')
        self.assertEqual(rows[1][2], 'IBM')
