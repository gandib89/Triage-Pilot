from rest_framework.throttling import AnonRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Blunts credential stuffing against /api/token/."""
    scope = 'login'


class RegisterRateThrottle(AnonRateThrottle):
    """Blunts mass account creation against /api/register/."""
    scope = 'register'
