from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Blunts credential stuffing against /api/token/."""
    scope = 'login'


class RegisterRateThrottle(AnonRateThrottle):
    """Blunts mass account creation against /api/register/."""
    scope = 'register'


class TriageRetryThrottle(UserRateThrottle):
    """Each call runs two LLM inferences against the one shared Ollama
    process — without this a user loop could pin it indefinitely."""
    scope = 'triage_retry'
