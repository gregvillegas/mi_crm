from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from customers.models import Customer
from sales_funnel.models import SalesFunnel
from sales_proposals.context_processors import proposal_approval_notifications
from sales_proposals.forms import ProposalAttachmentForm, ProposalForm, ProposalItemForm
from sales_proposals.models import Proposal, ProposalApprovalStep, ProposalAttachment, ProposalItem
from sales_proposals.views import _get_proposal_email_signature_context, update_sales_funnel
from teams.models import Group, Team, TeamMembership


User = get_user_model()


class ProposalApprovalWorkflowTests(TestCase):
    def setUp(self):
        self.password = 'testpass123'
        self.salesperson = User.objects.create_user(
            username='ae_user',
            password=self.password,
            role='salesperson',
            first_name='Aira',
            last_name='Exec',
            email='ae@example.com',
        )
        self.supervisor = User.objects.create_user(
            username='sup_user',
            password=self.password,
            role='supervisor',
            first_name='Sally',
            last_name='Supervisor',
            email='sup@example.com',
        )
        self.asm = User.objects.create_user(
            username='asm_user',
            password=self.password,
            role='asm',
            first_name='Andy',
            last_name='Asm',
            email='asm@example.com',
        )
        self.avp = User.objects.create_user(
            username='avp_user',
            password=self.password,
            role='avp',
            first_name='Ava',
            last_name='Avp',
            email='avp@example.com',
        )

        self.team = Team.objects.create(name='North Team', avp=self.avp, asm=self.asm)
        self.group = Group.objects.create(name='North Group', team=self.team, supervisor=self.supervisor)
        TeamMembership.objects.create(user=self.salesperson, group=self.group)

        self.customer = Customer.objects.create(
            company_name='Acme Corp',
            contact_person_name='Wilfred Cruz',
            email='wilfred@acme.test',
            salesperson=self.salesperson,
        )
        self.proposal = Proposal.objects.create(
            customer=self.customer,
            created_by=self.salesperson,
            subject='Network Refresh',
            approval_required=True,
            approval_status='in_progress',
            approval_total_php=Decimal('1500000.00'),
        )
        self.step1 = ProposalApprovalStep.objects.create(
            proposal=self.proposal,
            level=1,
            approver=self.supervisor,
            status='pending',
        )
        self.step2 = ProposalApprovalStep.objects.create(
            proposal=self.proposal,
            level=2,
            approver=self.asm,
            status='pending',
        )
        self.factory = RequestFactory()

    def test_approvals_inbox_only_shows_current_pending_level(self):
        self.client.force_login(self.asm)
        asm_response = self.client.get(reverse('approvals_inbox'))
        self.assertEqual(asm_response.status_code, 200)
        self.assertNotContains(asm_response, self.proposal.proposal_number)

        self.client.force_login(self.supervisor)
        supervisor_response = self.client.get(reverse('approvals_inbox'))
        self.assertEqual(supervisor_response.status_code, 200)
        self.assertContains(supervisor_response, self.proposal.proposal_number)

    def test_later_approver_cannot_approve_before_current_level(self):
        self.client.force_login(self.asm)
        response = self.client.post(reverse('approve_proposal', args=[self.proposal.pk]), {'comment': 'Approved'})

        self.assertRedirects(response, reverse('proposal_detail', args=[self.proposal.pk]))
        self.step1.refresh_from_db()
        self.step2.refresh_from_db()
        self.assertEqual(self.step1.status, 'pending')
        self.assertEqual(self.step2.status, 'pending')

        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertTrue(any('Approval order is enforced' in message for message in messages))

    def test_next_approver_can_act_after_previous_level_approves(self):
        self.client.force_login(self.supervisor)
        self.client.post(reverse('approve_proposal', args=[self.proposal.pk]), {'comment': 'Level 1 ok'})

        self.step1.refresh_from_db()
        self.assertEqual(self.step1.status, 'approved')

        self.client.force_login(self.asm)
        response = self.client.post(reverse('approve_proposal', args=[self.proposal.pk]), {'comment': 'Level 2 ok'})

        self.assertRedirects(response, reverse('proposal_detail', args=[self.proposal.pk]))
        self.step2.refresh_from_db()
        self.proposal.refresh_from_db()
        self.assertEqual(self.step2.status, 'approved')
        self.assertEqual(self.proposal.approval_status, 'approved')

    def test_bell_notifications_follow_current_approver(self):
        request = self.factory.get('/')
        request.user = self.supervisor
        supervisor_context = proposal_approval_notifications(request)
        self.assertEqual(supervisor_context['proposal_approval_notification_count'], 1)
        self.assertEqual(supervisor_context['proposal_approval_notifications'][0]['title'], self.proposal.proposal_number)

        self.step1.status = 'approved'
        self.step1.save(update_fields=['status'])

        asm_request = self.factory.get('/')
        asm_request.user = self.asm
        asm_context = proposal_approval_notifications(asm_request)
        self.assertEqual(asm_context['proposal_approval_notification_count'], 1)
        self.assertEqual(asm_context['proposal_approval_notifications'][0]['title'], self.proposal.proposal_number)

    def test_tier_escalation_rebuilds_chain_to_level_three(self):
        self.proposal.approval_total_php = Decimal('3951360.00')
        self.proposal.save(update_fields=['approval_total_php'])

        self.proposal.ensure_approval_chain()

        steps = list(self.proposal.approval_steps.order_by('level'))
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0].approver_id, self.supervisor.id)
        self.assertEqual(steps[1].approver_id, self.asm.id)
        self.assertEqual(steps[2].approver_id, self.avp.id)
        self.assertTrue(all(step.status == 'pending' for step in steps))

    def test_tier_escalation_restarts_partial_approvals_safely(self):
        self.step1.status = 'approved'
        self.step1.save(update_fields=['status'])
        self.proposal.approval_total_php = Decimal('3951360.00')
        self.proposal.save(update_fields=['approval_total_php'])

        self.proposal.ensure_approval_chain()
        self.proposal.refresh_from_db()
        steps = list(self.proposal.approval_steps.order_by('level'))

        self.assertEqual(len(steps), 3)
        self.assertEqual([step.status for step in steps], ['pending', 'pending', 'pending'])
        self.assertEqual(self.proposal.approval_status, 'in_progress')


class ProposalPricingWorkflowTests(TestCase):
    def test_item_form_allows_manual_unit_price_without_cost(self):
        form = ProposalItemForm(data={
            'part_number': 'SKU-001',
            'description': 'Manual priced service',
            'quantity': '2',
            'unit_cost': '',
            'unit_price': '125000',
            'warranty': '',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['unit_cost'], Decimal('0'))
        self.assertEqual(form.cleaned_data['unit_price'], Decimal('125000'))

    def test_item_form_requires_bundle_lines_when_bundle_is_checked(self):
        form = ProposalItemForm(data={
            'part_number': 'SERVER-001',
            'description': 'Bundled workstation',
            'quantity': '1',
            'unit_cost': '',
            'unit_price': '100000',
            'warranty': '',
            'is_bundle': 'on',
            'bundled_items': '',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('bundled_items', form.errors)

    def test_attachment_form_blocks_costing_matrix_include_in_email(self):
        upload = SimpleUploadedFile(
            'COSTING-MATRIX.xlsx',
            b'fake-excel-content',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        form = ProposalAttachmentForm(
            data={'include_in_email': 'on'},
            files={'file': upload},
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data['include_in_email'])

    def test_costing_matrix_attachment_save_forces_include_in_email_false(self):
        user = User.objects.create_user(
            username='attach_user',
            password='testpass123',
            role='salesperson',
            email='attach@example.com',
        )
        customer = Customer.objects.create(
            company_name='Attachment Corp',
            contact_person_name='Ava Buyer',
            email='buyer@attach.test',
            salesperson=user,
        )
        proposal = Proposal.objects.create(
            customer=customer,
            created_by=user,
            subject='Attachment Test',
        )
        attachment = ProposalAttachment.objects.create(
            proposal=proposal,
            file=SimpleUploadedFile('costing-matrix.xlsx', b'xlsx'),
            include_in_email=True,
            uploaded_by=user,
        )

        self.assertTrue(attachment.is_costing_matrix)
        self.assertFalse(attachment.include_in_email)

    def test_bundle_components_parse_part_numbers_and_descriptions(self):
        item = ProposalItem(
            part_number='SERVER-001',
            description='Main bundled server',
            quantity=Decimal('1'),
            unit_cost=Decimal('0'),
            unit_price=Decimal('100000'),
            is_bundle=True,
            bundled_items='B4YT6AV | Base Unit\n8C9M7AV | No Country of Origin Restriction\n3 year onsite support',
        )

        self.assertEqual(
            item.bundle_components,
            [
                {'part_number': 'B4YT6AV', 'description': 'Base Unit'},
                {'part_number': '8C9M7AV', 'description': 'No Country of Origin Restriction'},
                {'part_number': '', 'description': '3 year onsite support'},
            ],
        )

    def test_bundle_components_parse_tab_separated_excel_paste(self):
        item = ProposalItem(
            part_number='SERVER-001',
            description='Main bundled server',
            quantity=Decimal('1'),
            unit_cost=Decimal('0'),
            unit_price=Decimal('100000'),
            is_bundle=True,
            bundled_items='B4YT6AV\tBase Unit\n8C9M7AV\tNo Country of Origin Restriction',
        )

        self.assertEqual(
            item.bundle_components,
            [
                {'part_number': 'B4YT6AV', 'description': 'Base Unit'},
                {'part_number': '8C9M7AV', 'description': 'No Country of Origin Restriction'},
            ],
        )

    def test_optional_items_are_excluded_from_proposal_totals(self):
        user = User.objects.create_user(
            username='optional_user',
            password='testpass123',
            role='salesperson',
            email='optional@example.com',
        )
        customer = Customer.objects.create(
            company_name='Optional Corp',
            contact_person_name='Olive Buyer',
            email='buyer@optional.test',
            salesperson=user,
        )
        proposal = Proposal.objects.create(
            customer=customer,
            created_by=user,
            subject='Optional Item Test',
        )
        ProposalItem.objects.create(
            proposal=proposal,
            part_number='REQ-001',
            description='Required laptop',
            quantity=Decimal('1'),
            unit_cost=Decimal('20000.00'),
            unit_price=Decimal('30000.00'),
            is_optional=False,
        )
        ProposalItem.objects.create(
            proposal=proposal,
            part_number='OPT-001',
            description='Optional dock',
            quantity=Decimal('1'),
            unit_cost=Decimal('5000.00'),
            unit_price=Decimal('10000.00'),
            is_optional=True,
        )

        proposal.calculate_totals()
        proposal.refresh_from_db()

        self.assertTrue(proposal.has_optional_items)
        self.assertEqual(proposal.subtotal, Decimal('30000.00'))
        self.assertEqual(proposal.total_cost, Decimal('20000.00'))
        self.assertEqual(proposal.total_amount, Decimal('30000.00'))
        optional_item = proposal.items.get(part_number='OPT-001')
        self.assertEqual(optional_item.amount, Decimal('10000.00'))
        self.assertEqual(proposal.quoted_total_cost, Decimal('25000.00'))
        self.assertEqual(proposal.quoted_total_amount, Decimal('40000.00'))
        self.assertEqual(proposal.quoted_gross_profit, Decimal('15000.00'))

    def test_proposal_list_uses_quoted_total_when_optional_items_exist(self):
        user = User.objects.create_user(
            username='optional_list_user',
            password='testpass123',
            role='salesperson',
            email='optional-list@example.com',
        )
        customer = Customer.objects.create(
            company_name='Quoted Corp',
            contact_person_name='Quinn Buyer',
            email='buyer@quoted.test',
            salesperson=user,
        )
        proposal = Proposal.objects.create(
            customer=customer,
            created_by=user,
            subject='Quoted Proposal',
        )
        ProposalItem.objects.create(
            proposal=proposal,
            part_number='REQ-100',
            description='Required bundle base',
            quantity=Decimal('1'),
            unit_cost=Decimal('10000.00'),
            unit_price=Decimal('15000.00'),
        )
        ProposalItem.objects.create(
            proposal=proposal,
            part_number='OPT-100',
            description='Optional upgrade',
            quantity=Decimal('2'),
            unit_cost=Decimal('5000.00'),
            unit_price=Decimal('8000.00'),
            is_optional=True,
        )
        proposal.calculate_totals()

        self.client.force_login(user)
        response = self.client.get(reverse('proposal_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '31,000.00')
        self.assertNotContains(response, '15,000.00')

    def test_update_sales_funnel_uses_quoted_totals_when_optional_items_exist(self):
        user = User.objects.create_user(
            username='optional_funnel_user',
            password='testpass123',
            role='salesperson',
            email='optional-funnel@example.com',
        )
        customer = Customer.objects.create(
            company_name='Funnel Corp',
            contact_person_name='Finn Buyer',
            email='buyer@funnel.test',
            salesperson=user,
        )
        proposal = Proposal.objects.create(
            customer=customer,
            created_by=user,
            subject='Funnel Proposal',
        )
        ProposalItem.objects.create(
            proposal=proposal,
            part_number='REQ-200',
            description='Required server',
            quantity=Decimal('1'),
            unit_cost=Decimal('20000.00'),
            unit_price=Decimal('30000.00'),
        )
        ProposalItem.objects.create(
            proposal=proposal,
            part_number='OPT-200',
            description='Optional storage',
            quantity=Decimal('1'),
            unit_cost=Decimal('10000.00'),
            unit_price=Decimal('15000.00'),
            is_optional=True,
        )
        proposal.calculate_totals()

        update_sales_funnel(proposal)
        funnel_entry = SalesFunnel.objects.get(proposal=proposal)

        self.assertEqual(funnel_entry.retail, Decimal('45000.00'))
        self.assertEqual(funnel_entry.cost, Decimal('30000.00'))
        self.assertEqual(funnel_entry.display_retail, Decimal('45000.00'))
        self.assertEqual(funnel_entry.profit, Decimal('15000.00'))

    def test_proposal_list_displays_reference_number_column(self):
        user = User.objects.create_user(
            username='reference_user',
            password='testpass123',
            role='salesperson',
            email='reference@example.com',
        )
        customer = Customer.objects.create(
            company_name='Reference Corp',
            contact_person_name='Rina Buyer',
            email='buyer@reference.test',
            salesperson=user,
        )
        proposal = Proposal.objects.create(
            customer=customer,
            created_by=user,
            subject='Reference Display Test',
            reference_number='REF-2026-001',
        )

        self.client.force_login(user)
        response = self.client.get(reverse('proposal_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reference #')
        self.assertContains(response, proposal.reference_number)

    @patch('sales_proposals.views.update_sales_funnel')
    @patch('sales_proposals.views.log_sales_activity')
    @patch('sales_proposals.views.EmailMultiAlternatives')
    def test_proposal_email_excludes_costing_matrix_attachment(
        self,
        email_cls,
        _log_sales_activity,
        _update_sales_funnel,
    ):
        user = User.objects.create_user(
            username='email_user',
            password='testpass123',
            role='salesperson',
            email='sender@example.com',
        )
        customer = Customer.objects.create(
            company_name='Email Corp',
            contact_person_name='Erin Buyer',
            email='buyer@email.test',
            salesperson=user,
        )
        proposal = Proposal.objects.create(
            customer=customer,
            created_by=user,
            subject='Email Attachment Test',
        )
        ProposalItem.objects.create(
            proposal=proposal,
            description='Quoted line',
            quantity=Decimal('1'),
            unit_cost=Decimal('100.00'),
            unit_price=Decimal('150.00'),
        )
        proposal.calculate_totals()
        safe_attachment = ProposalAttachment.objects.create(
            proposal=proposal,
            file=SimpleUploadedFile('brochure.pdf', b'pdf-bytes'),
            include_in_email=True,
            uploaded_by=user,
        )
        blocked_attachment = ProposalAttachment.objects.create(
            proposal=proposal,
            file=SimpleUploadedFile('COSTING-MATRIX.xlsx', b'xlsx-bytes'),
            include_in_email=True,
            uploaded_by=user,
        )

        email_instance = email_cls.return_value
        self.client.force_login(user)
        response = self.client.post(
            reverse('proposal_email', args=[proposal.pk]),
            {
                'customer_emails': customer.email,
                'attach_id': [str(safe_attachment.id), str(blocked_attachment.id)],
            },
        )

        self.assertEqual(response.status_code, 302)
        attached_names = [call.args[0] for call in email_instance.attach.call_args_list]
        self.assertIn(f'{proposal.proposal_number}.pdf', attached_names)
        self.assertIn('brochure.pdf', attached_names)
        self.assertNotIn('COSTING-MATRIX.xlsx', attached_names)

    def test_proposal_internal_summary_uses_total_level_margin(self):
        user = User.objects.create_user(
            username='pricing_user',
            password='testpass123',
            role='salesperson',
            email='pricing@example.com',
        )
        customer = Customer.objects.create(
            company_name='Pricing Corp',
            contact_person_name='Pat Buyer',
            email='buyer@pricing.test',
            salesperson=user,
        )
        proposal = Proposal.objects.create(
            customer=customer,
            created_by=user,
            subject='Pricing Test',
            sales_margin_pct=Decimal('10.00'),
        )
        ProposalItem.objects.create(
            proposal=proposal,
            part_number='SKU-100',
            description='Server',
            quantity=Decimal('2'),
            unit_cost=Decimal('100.00'),
            unit_price=Decimal('150.00'),
        )
        ProposalItem.objects.create(
            proposal=proposal,
            part_number='SKU-200',
            description='Service',
            quantity=Decimal('1'),
            unit_cost=Decimal('0.00'),
            unit_price=Decimal('80.00'),
        )

        proposal.calculate_totals()
        proposal.refresh_from_db()

        self.assertEqual(proposal.total_cost, Decimal('200.00'))
        self.assertEqual(proposal.subtotal, Decimal('380.00'))
        self.assertEqual(proposal.internal_cost_with_uplift, Decimal('210.0000'))
        self.assertEqual(proposal.target_subtotal_before_tax, Decimal('231.000000'))

    def test_proposal_totals_are_tax_free(self):
        user = User.objects.create_user(
            username='taxfree_user',
            password='testpass123',
            role='salesperson',
            email='taxfree@example.com',
        )
        customer = Customer.objects.create(
            company_name='Tax Free Corp',
            contact_person_name='Tina Buyer',
            email='buyer@taxfree.test',
            salesperson=user,
        )
        proposal = Proposal.objects.create(
            customer=customer,
            created_by=user,
            subject='Tax Free Test',
            tax_type='VAT',
            tax_rate=Decimal('12.00'),
        )
        ProposalItem.objects.create(
            proposal=proposal,
            part_number='SKU-300',
            description='Firewall',
            quantity=Decimal('2'),
            unit_cost=Decimal('100.00'),
            unit_price=Decimal('150.00'),
        )

        proposal.calculate_totals()
        proposal.refresh_from_db()

        self.assertEqual(proposal.tax_type, 'ZERO')
        self.assertEqual(proposal.tax_rate, Decimal('0.00'))
        self.assertEqual(proposal.tax_amount, Decimal('0.00'))
        self.assertEqual(proposal.subtotal, Decimal('300.00'))
        self.assertEqual(proposal.total_amount, Decimal('300.00'))

    def test_proposal_form_uses_uppercase_bank_detail_labels(self):
        form = ProposalForm()

        self.assertNotIn('tax_type', form.fields)
        self.assertNotIn('tax_rate', form.fields)
        self.assertNotIn('sales_margin_pct', form.fields)
        self.assertNotIn('price_validity_mode', form.fields)
        self.assertNotIn('validity_subject_to_prior_sale', form.fields)
        self.assertNotIn('validity_availability_at_order', form.fields)
        self.assertIn('stock_availability', form.fields)
        item_form = ProposalItemForm()
        self.assertIn('is_optional', item_form.fields)
        self.assertIn('is_bundle', item_form.fields)
        self.assertIn('bundled_items', item_form.fields)
        self.assertEqual(form.fields['stock_availability'].label, 'Stock availability')
        self.assertEqual(form.fields['php_bank_name'].label, 'PHP bank name')
        self.assertEqual(form.fields['php_account_name'].label, 'PHP account name')
        self.assertEqual(form.fields['usd_beneficiary_name'].label, 'USD beneficiary name')
        self.assertEqual(form.fields['usd_bank_address'].label, 'USD bank address')


class ProposalEmailSignatureTests(TestCase):
    def test_signature_context_picks_up_email_signature_icons_from_templates_static(self):
        user = User.objects.create_user(
            username='signature_user',
            password='testpass123',
            role='salesperson',
            email='signature@example.com',
            first_name='Sig',
            last_name='User',
        )

        with TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            icon_dir = base_dir / 'templates' / 'core' / 'static' / 'core' / 'images' / 'email_signature'
            icon_dir.mkdir(parents=True, exist_ok=True)
            for filename in [
                'FB.png',
                'IG.png',
                'TWITT.png',
                'WEB-ICON.png',
            ]:
                (icon_dir / filename).write_bytes(b'fake-png')
            (base_dir / '28Years.png').write_bytes(b'fake-png')

            with override_settings(
                BASE_DIR=base_dir,
                COMPANY_FACEBOOK_URL='https://facebook.com/MicroImagePH',
                COMPANY_INSTAGRAM_URL='https://instagram.com/MicroImagePH',
                COMPANY_X_URL='https://twitter.com/MicroImagePH',
                COMPANY_WEBSITE_URL='https://www.microimageph.com',
                COMPANY_WEBSITE_LABEL='www.microimageph.com',
            ):
                signature = _get_proposal_email_signature_context(user)

        self.assertEqual(len(signature['company_social_links']), 4)
        self.assertTrue(all(item['icon_cid'] for item in signature['company_social_links']))
        self.assertEqual(signature['company_website_icon_cid'], 'signature-website-icon')
        self.assertEqual(signature['anniversary_image_cid'], 'company-28-years')
        self.assertEqual(len(signature['inline_images']), 5)
