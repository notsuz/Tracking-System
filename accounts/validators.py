from django.core.exceptions import ValidationError
import re


class StrongPasswordValidator:
    """
    Validates password contains:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit
    - At least 1 special character
    """
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        errors = []
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long.")
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least 1 uppercase letter.")
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least 1 lowercase letter.")
        if not re.search(r'[0-9]', password):
            errors.append("Password must contain at least 1 number.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`;]', password):
            errors.append("Password must contain at least 1 special character (!@#$%^&* etc.).")
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            "Your password must be at least 8 characters long and contain "
            "at least 1 uppercase letter, 1 lowercase letter, 1 number, "
            "and 1 special character."
        )