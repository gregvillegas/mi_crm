from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from customers.models import Customer
from sales_proposals.context_processors import proposal_approval_notifications
from sales_proposals.forms import ProposalItemForm
from sales_proposals.models import Proposal, ProposalApprovalStep, ProposalItem
from sales_proposals.views import _get_proposal_email_signature_context
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

        self.assertEqual(len(signature['company_social_links']), 3)
        self.assertTrue(all(item['icon_cid'] for item in signature['company_social_links']))
        self.assertEqual(signature['company_website_icon_cid'], 'signature-website-icon')
        self.assertEqual(signature['anniversary_image_cid'], 'company-28-years')
        self.assertEqual(len(signature['inline_images']), 5)
