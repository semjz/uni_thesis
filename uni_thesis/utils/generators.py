import secrets
import string

def random_numeric_string(n):
    return ''.join(secrets.choice(string.digits) for _ in range(n))