"""
The invariant this bug broke: a submitted ticket must be visible to staff in
the triage queue whether or not the agent ever succeeds. The queue lists
DecisionLogs, so that means the row exists from creation, independently of
inference.
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .agent import apply_triage
from .models import DecisionLog, Ticket


class TriageVisibilityTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user('cust', password='pw')
        self.staff = User.objects.create_user('staffer', password='pw')
        self.staff.profile.role = 'staff'
        self.staff.profile.save()

        self.as_customer = APIClient()
        self.as_customer.force_authenticate(self.customer)
        self.as_staff = APIClient()
        self.as_staff.force_authenticate(self.staff)

    def submit(self):
        """Create a ticket without letting the real agent thread start."""
        with patch('tickets.views.triage_in_background') as kick:
            res = self.as_customer.post(
                '/api/tickets/', {'subject': 'hi', 'body': 'it broke'})
        self.assertEqual(res.status_code, 201)
        self.assertTrue(kick.called, 'triage should be kicked off server-side')
        return Ticket.objects.get(pk=res.data['id'])

    def pending_ticket_ids(self):
        res = self.as_staff.get('/api/decisions/?status=pending')
        self.assertEqual(res.status_code, 200)
        rows = res.data.get('results', res.data)
        return {row['ticket']['id'] for row in rows}

    def test_ticket_is_in_the_staff_queue_before_the_agent_runs(self):
        ticket = self.submit()
        self.assertIn(ticket.pk, self.pending_ticket_ids())

    def test_ticket_stays_in_the_queue_when_the_agent_fails(self):
        ticket = self.submit()
        decision = ticket.decisions.get()

        with patch('tickets.agent.categorize_ticket',
                   side_effect=Exception('ollama is down')):
            with self.assertRaises(Exception):
                apply_triage(ticket, decision)

        decision.refresh_from_db()
        self.assertEqual(decision.triage_error, 'ollama is down')
        self.assertIn(ticket.pk, self.pending_ticket_ids())

    def test_retry_fills_in_the_existing_row_rather_than_adding_one(self):
        ticket = self.submit()

        fake = {
            'category': 'billing', 'urgency': 'high', 'confidence': 90,
            'reasoning': 'looks like a refund', 'action': 'reply',
            'drafted_response': 'Refund is on its way.',
            'escalation_reason': '', 'sources_cited': ['KB003'],
            'kb_articles_found': 1,
        }
        with patch('tickets.agent.categorize_ticket', return_value=fake):
            res = self.as_staff.post(f'/api/tickets/{ticket.pk}/triage/')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(DecisionLog.objects.filter(ticket=ticket).count(), 1)

        decision = ticket.decisions.get()
        self.assertEqual(decision.proposed_action, 'Refund is on its way.')
        self.assertEqual(decision.triage_error, '')
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'in_review')


class RefreshTokenSecurityTests(TestCase):
    """
    Covers the cookie-transport + reuse-detection hardening: the refresh
    token never appears in a JSON body, and replaying an already-rotated one
    kills every token descended from that login, not just the replayed jti.
    """

    def setUp(self):
        self.user = User.objects.create_user('cust2', password='pw12345')
        self.client = APIClient()

    def login(self):
        res = self.client.post(
            '/api/token/', {'username': 'cust2', 'password': 'pw12345'})
        self.assertEqual(res.status_code, 200)
        return res

    def test_login_returns_access_only_and_sets_httponly_cookie(self):
        res = self.login()
        self.assertIn('access', res.data)
        self.assertNotIn('refresh', res.data)
        cookie = res.cookies.get('refresh_token')
        self.assertIsNotNone(cookie)
        self.assertTrue(cookie['httponly'])

    def test_refresh_rotates_cookie_and_returns_new_access(self):
        first = self.login()
        res = self.client.post('/api/token/refresh/')
        self.assertEqual(res.status_code, 200)
        self.assertNotEqual(res.data['access'], first.data['access'])
        self.assertNotIn('refresh', res.data)

    def test_missing_refresh_cookie_is_401_with_detail_shape(self):
        res = self.client.post('/api/token/refresh/')
        self.assertEqual(res.status_code, 401)
        self.assertIn('detail', res.data)

    def test_replayed_refresh_token_revokes_the_whole_family(self):
        self.login()
        stolen = self.client.cookies['refresh_token'].value

        legit = self.client.post('/api/token/refresh/')
        self.assertEqual(legit.status_code, 200)
        rotated = self.client.cookies['refresh_token'].value

        # Attacker replays the pre-rotation token.
        self.client.cookies['refresh_token'] = stolen
        replay = self.client.post('/api/token/refresh/')
        self.assertEqual(replay.status_code, 401)

        # The legitimate holder's already-rotated token is dead too, since
        # the server can't tell attacker and victim apart once this happens.
        self.client.cookies['refresh_token'] = rotated
        after = self.client.post('/api/token/refresh/')
        self.assertEqual(after.status_code, 401)

    def test_logout_blacklists_refresh_and_clears_cookie(self):
        self.login()
        res = self.client.post('/api/logout/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.cookies['refresh_token'].value, '')

        again = self.client.post('/api/token/refresh/')
        self.assertEqual(again.status_code, 401)
