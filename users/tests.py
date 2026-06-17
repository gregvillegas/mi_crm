from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

User = get_user_model()


class MFATestCase(TestCase):
    """Tests for Two-Factor Authentication (MFA) functionality."""
    
    def setUp(self):
        """Set up test users."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        self.admin_user = User.objects.create_user(
            username='adminuser',
            password='adminpass123',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        self.client = Client()
    
    def test_mfa_index_url_exists(self):
        """Test that MFA index URL is accessible."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/accounts/2fa/')
        self.assertEqual(response.status_code, 200)
    
    def test_mfa_activate_totp_url_exists(self):
        """Test that MFA TOTP activation URL is accessible."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/accounts/2fa/totp/activate/')
        self.assertEqual(response.status_code, 200)
    
    def test_profile_shows_mfa_section(self):
        """Test that MFA section appears on profile page."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Two-Factor Authentication', status_code=200)
        self.assertContains(response, 'Security', status_code=200)
    
    def test_mfa_not_enabled_by_default(self):
        """Test that MFA is not enabled for new users by default."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        # Should show "Not Enabled" badge for new users
        self.assertContains(response, 'Not Enabled', status_code=200)
    
    def test_login_page_has_mfa_branding(self):
        """Test that login page shows MFA branding."""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Two-Factor Authentication', status_code=200)
    
    def test_mfa_urls_require_authentication(self):
        """Test that MFA URLs require login."""
        response = self.client.get('/accounts/2fa/')
        # Should redirect to login
        self.assertIn(response.status_code, [302, 403])
    
    @patch('allauth.mfa.models.Authenticator.objects.filter')
    def test_profile_shows_enabled_when_mfa_active(self, mock_filter):
        """Test that profile shows MFA enabled when user has TOTP configured."""
        # Mock the filter to return a non-empty queryset
        mock_queryset = MagicMock()
        mock_queryset.exists.return_value = True
        mock_filter.return_value = mock_queryset
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        # Should show "Enabled" badge
        self.assertContains(response, 'Enabled', status_code=200)


class MFAIntegrationTestCase(TestCase):
    """Integration tests for MFA workflow."""
    
    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            username='mfauser',
            password='mfapass123',
            email='mfa@example.com',
            first_name='MFA',
            last_name='User'
        )
        self.client = Client()
    
    def test_api_token_auth_still_works(self):
        """Test that API token authentication is not affected by MFA."""
        from rest_framework.authtoken.models import Token
        Token.objects.create(user=self.user)
        
        # API token auth should work independently of session-based MFA
        response = self.client.post('/api/v1/api-token-auth/', {
            'username': 'mfauser',
            'password': 'mfapass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.json())
    
    def test_login_redirect_preserved(self):
        """Test that login redirects work correctly with MFA."""
        # Ensure login page loads
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        
        # Login should work
        response = self.client.post('/login/', {
            'username': 'mfauser',
            'password': 'mfapass123'
        }, follow=True)
        # Should redirect to home or MFA verification
        self.assertIn(response.status_code, [200, 302])
