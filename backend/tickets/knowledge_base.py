"""
Knowledge Base search tool for the AI agent.

Search hits the RAG index first (ingested PDFs, see tickets/rag.py). The
hardcoded articles below stay as a fallback for when no documents have been
ingested yet, or when nothing in the index clears the similarity threshold.
"""
from typing import List, Dict

from .rag import search_chunks


# Mock knowledge base articles
# Replace these with real documentation later
KB_ARTICLES = [
    {
        "id": "KB001",
        "title": "Password Reset Guide",
        "category": "technical",
        "content": """To reset your password:
1. Go to the login page and click 'Forgot Password'
2. Enter your registered email address
3. Check your email for a reset link (check spam folder too)
4. Click the link and enter your new password
5. Link expires in 24 hours - request a new one if needed.
Contact support if you don't receive the email within 5 minutes.""",
        "tags": ["password", "reset", "login", "forgot", "email"]
    },
    {
        "id": "KB002",
        "title": "Two-Factor Authentication (2FA) Troubleshooting",
        "category": "technical",
        "content": """If you're not receiving 2FA codes:
1. Check your phone number is correct in account settings
2. Ensure your phone has signal/internet connection
3. Try requesting a new code (wait 30 seconds between attempts)
4. Check if your authenticator app time is synced
5. Use backup codes if available (Settings > Security > Backup Codes)
Contact support to disable 2FA if you're completely locked out.""",
        "tags": ["2fa", "two-factor", "authentication", "code", "locked", "security"]
    },
    {
        "id": "KB003",
        "title": "Billing and Refund Policy",
        "category": "billing",
        "content": """Our refund policy:
- Full refund available within 30 days of purchase
- Pro-rated refund for annual plans cancelled mid-term
- Duplicate charges are refunded within 3-5 business days
- To request a refund: go to Settings > Billing > Request Refund
- Include your invoice number for faster processing
For billing disputes, contact billing@company.com with your account ID.""",
        "tags": ["refund", "billing", "charge", "invoice", "payment", "cancel"]
    },
    {
        "id": "KB004",
        "title": "Account Locked - Recovery Steps",
        "category": "account",
        "content": """If your account is locked:
1. Wait 30 minutes - accounts auto-unlock after failed attempts
2. Use 'Forgot Password' to reset credentials
3. Check if your account was suspended (you'll receive an email)
4. Contact support with your username and registered email
5. Provide ID verification if requested by our team
Accounts are locked after 5 failed login attempts as a security measure.""",
        "tags": ["locked", "account", "suspended", "access", "login", "failed"]
    },
    {
        "id": "KB005",
        "title": "Data Export and Download",
        "category": "general",
        "content": """To export your data:
1. Go to Settings > Privacy > Export Data
2. Select the data types you want to export
3. Click 'Request Export' - processing takes up to 24 hours
4. You'll receive an email with a download link
5. The download link expires after 7 days
Exported data includes: profile, activity history, and content you've created.""",
        "tags": ["export", "download", "data", "privacy", "backup"]
    },
    {
        "id": "KB006",
        "title": "How to Delete Your Account",
        "category": "account",
        "content": """To permanently delete your account:
1. Go to Settings > Account > Delete Account
2. Enter your password to confirm
3. Choose immediate deletion or 30-day grace period
4. All your data will be permanently deleted
5. This action cannot be undone
Note: Active subscriptions must be cancelled before account deletion.""",
        "tags": ["delete", "account", "close", "remove", "cancel", "gdpr"]
    },
    {
        "id": "KB007",
        "title": "Slack Integration Guide",
        "category": "general",
        "content": """To integrate with Slack:
1. Go to Settings > Integrations > Slack
2. Click 'Connect to Slack' and authorize the app
3. Choose which workspace and channel to connect
4. Configure notification preferences
5. Test the integration with a test message
Slack integration supports: notifications, alerts, and command shortcuts.""",
        "tags": ["slack", "integration", "connect", "webhook", "notification"]
    },
    {
        "id": "KB008",
        "title": "API Rate Limits and Upgrades",
        "category": "technical",
        "content": """API rate limits by plan:
- Free: 100 requests/hour
- Pro: 1,000 requests/hour  
- Business: 10,000 requests/hour
- Enterprise: Unlimited (contact sales)

To increase your limit:
1. Upgrade your plan in Settings > Billing
2. Contact sales@company.com for Enterprise pricing
3. Implement request caching to reduce API calls
4. Use webhooks instead of polling where possible""",
        "tags": ["api", "rate limit", "requests", "upgrade", "enterprise"]
    },
    {
        "id": "KB009",
        "title": "Security - Suspicious Email or Phishing",
        "category": "technical",
        "content": """If you received a suspicious email:
1. Do NOT click any links or download attachments
2. Check the sender email - official emails come from @company.com only
3. We will NEVER ask for your password via email
4. Forward the suspicious email to security@company.com
5. Change your password immediately if you clicked any links
Report all phishing attempts - it helps protect other users too.""",
        "tags": ["phishing", "suspicious", "email", "security", "breach", "scam"]
    },
    {
        "id": "KB010",
        "title": "Account Ownership Transfer",
        "category": "account",
        "content": """To transfer account ownership:
1. Go to Settings > Account > Transfer Ownership
2. Enter the new owner's email address
3. The new owner will receive a confirmation email
4. Both parties must confirm the transfer
5. Billing will be transferred to the new owner's payment method
Note: You must be the account owner to initiate a transfer.""",
        "tags": ["transfer", "ownership", "account", "handover", "employee"]
    },
    {
        "id": "KB011",
        "title": "Upgrading or Downgrading Your Plan",
        "category": "billing",
        "content": """To change your subscription plan:
1. Go to Settings > Billing > Change Plan
2. Select your new plan from the available options
3. Upgrades take effect immediately with pro-rated billing
4. Downgrades take effect at the end of your current billing period
5. You will receive a confirmation email with updated invoice details
For Enterprise plan inquiries, contact sales@company.com directly.""",
        "tags": ["upgrade", "downgrade", "plan", "subscription", "billing", "pricing"]
    },
    {
        "id": "KB012",
        "title": "Mobile App Troubleshooting",
        "category": "technical",
        "content": """If the mobile app is crashing or not working:
1. Force close the app and reopen it
2. Check for app updates in the App Store or Google Play
3. Restart your device
4. Clear the app cache (Settings > Apps > Clear Cache)
5. Uninstall and reinstall the app
6. Ensure your OS is updated (iOS 15+ or Android 10+ required)
If the issue persists, report it with your device model and OS version.""",
        "tags": ["mobile", "app", "crash", "startup", "ios", "android", "install"]
    },
    {
        "id": "KB013",
        "title": "Updating Billing Address and Payment Method",
        "category": "billing",
        "content": """To update your billing information:
1. Go to Settings > Billing > Payment Methods
2. Click 'Edit' next to your current payment method
3. Update your card details or billing address
4. Click 'Save Changes'
5. Changes apply to your next billing cycle
For VAT or tax ID updates, contact billing@company.com with your invoice number.""",
        "tags": ["billing", "address", "payment", "card", "update", "invoice", "tax"]
    },
    {
        "id": "KB014",
        "title": "Enterprise Plan Features and Pricing",
        "category": "billing",
        "content": """Enterprise plan includes:
- Unlimited API requests
- Dedicated account manager
- Custom SLA (99.99% uptime guarantee)
- Single Sign-On (SSO) support
- Advanced security and compliance (SOC2, GDPR)
- Volume discounts for 100+ seats
- Priority 24/7 support

To get Enterprise pricing:
1. Contact sales@company.com
2. Schedule a demo call
3. Receive a custom quote within 2 business days""",
        "tags": ["enterprise", "pricing", "plan", "sso", "compliance", "volume", "discount", "seats"]
    },
    {
        "id": "KB015",
        "title": "Single Sign-On (SSO) Setup",
        "category": "technical",
        "content": """To configure SSO for your organization:
1. Go to Settings > Security > Single Sign-On
2. Choose your identity provider (Okta, Azure AD, Google Workspace)
3. Enter your IdP metadata URL or upload the XML file
4. Configure attribute mapping (email, name, role)
5. Test SSO login with a test account before enabling for all users
6. Enable SSO enforcement for all team members
Note: SSO is available on Business and Enterprise plans only.""",
        "tags": ["sso", "single sign-on", "okta", "azure", "google", "saml", "authentication"]
    },
    {
        "id": "KB016",
        "title": "Webhook Configuration Guide",
        "category": "technical",
        "content": """To set up webhooks:
1. Go to Settings > Developer > Webhooks
2. Click 'Add Webhook'
3. Enter your endpoint URL (must be HTTPS)
4. Select the events you want to receive
5. Copy the webhook secret for signature verification
6. Test the webhook with the 'Send Test Event' button
Retry policy: Failed webhooks are retried 3 times with exponential backoff.
Webhook payloads are signed with HMAC-SHA256.""",
        "tags": ["webhook", "api", "integration", "events", "endpoint", "developer"]
    },
    {
        "id": "KB017",
        "title": "GDPR and Data Privacy Requests",
        "category": "general",
        "content": """For GDPR and data privacy requests:
- Right to Access: Request a copy of all your data (Settings > Privacy > Export)
- Right to Deletion: Delete your account and all associated data
- Right to Rectification: Update incorrect personal data in your profile
- Data Processing Agreement (DPA): Contact legal@company.com
- Privacy questions: privacy@company.com

We comply with GDPR, CCPA, and other data protection regulations.
All requests are processed within 30 days as required by law.""",
        "tags": ["gdpr", "privacy", "data", "deletion", "access", "compliance", "dpa", "ccpa"]
    },
    {
        "id": "KB018",
        "title": "Team Member Roles and Permissions",
        "category": "account",
        "content": """Available team roles:
- Owner: Full access, billing control, can delete account
- Admin: Full access except billing and account deletion
- Manager: Can manage team members and view all data
- Member: Standard access to assigned projects
- Viewer: Read-only access

To change a team member's role:
1. Go to Settings > Team > Members
2. Click on the member's name
3. Select the new role from the dropdown
4. Changes take effect immediately""",
        "tags": ["roles", "permissions", "team", "admin", "member", "access", "manage"]
    },
    {
        "id": "KB019",
        "title": "Email Notification Settings",
        "category": "general",
        "content": """To manage email notifications:
1. Go to Settings > Notifications > Email
2. Toggle on/off specific notification types:
   - Account activity alerts
   - Billing and invoice notifications
   - Product updates and newsletters
   - Security alerts (recommended: always on)
3. Click Save to apply changes
To unsubscribe from all marketing emails, click the unsubscribe link in any email.
Security alerts cannot be fully disabled for account safety.""",
        "tags": ["email", "notification", "unsubscribe", "alerts", "newsletter", "settings"]
    },
    {
        "id": "KB020",
        "title": "Recovering a Deleted Account",
        "category": "account",
        "content": """If you accidentally deleted your account:
- Accounts deleted within the last 30 days can be recovered
- After 30 days, deletion is permanent and irreversible

To recover your account:
1. Go to the login page and click 'Recover Account'
2. Enter your registered email address
3. Check your email for a recovery link
4. Click the link within 24 hours to restore your account
5. All your data will be fully restored

Contact support immediately if you need help with account recovery.""",
        "tags": ["recover", "deleted", "account", "restore", "reactivate", "lost"]
    },
]


def search_knowledge_base(query: str, category: str = None, max_results: int = 3) -> List[Dict]:
    """
    Search the knowledge base for relevant material.

    Tries semantic search over ingested documents first, then falls back to the
    hardcoded articles. Both paths return the same shape, so callers (and the
    agent's prompts) don't care which one answered.

    Args:
        query: Search query (ticket subject + body keywords)
        category: Optional category filter (technical/billing/account/general)
        max_results: Maximum number of results to return

    Returns:
        List of relevant KB entries with relevance scores
    """
    chunks = search_chunks(query, category=category, max_results=max_results)
    if chunks:
        return chunks
    return _search_static_articles(query, category, max_results)


def _search_static_articles(query: str, category: str = None, max_results: int = 3) -> List[Dict]:
    """Keyword scoring over the hardcoded KB_ARTICLES fallback."""
    query_words = set(query.lower().split())
    results = []

    for article in KB_ARTICLES:
        # Skip if category doesn't match (when provided)
        if category and article['category'] != category:
            continue

        # Calculate relevance score based on tag matches
        article_tags = set(article['tags'])
        title_words = set(article['title'].lower().split())

        # Count matching words
        tag_matches = len(query_words.intersection(article_tags))
        title_matches = len(query_words.intersection(title_words))
        content_matches = sum(
            1 for word in query_words if word in article['content'].lower())

        # Weighted score
        score = (tag_matches * 3) + (title_matches * 2) + (content_matches * 1)

        if score > 0:
            results.append({
                "id": article['id'],
                "title": article['title'],
                "content": article['content'],
                "category": article['category'],
                "relevance_score": score
            })

    # Sort by relevance score (highest first)
    results.sort(key=lambda x: x['relevance_score'], reverse=True)

    # Return top results
    return results[:max_results]
