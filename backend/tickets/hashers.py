from django.contrib.auth.hashers import Argon2PasswordHasher


class TriagePilotArgon2PasswordHasher(Argon2PasswordHasher):
    """Argon2id with explicit cost params, first in PASSWORD_HASHERS so new
    and changed passwords hash here; PBKDF2 stays configured so existing
    hashes keep verifying until each user's next password change."""
    time_cost = 2
    memory_cost = 19456
    parallelism = 1
