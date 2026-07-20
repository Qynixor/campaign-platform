# main/validators.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
import re

class SymbolValidator:
    """
    Validate that the password contains at least one symbol.
    """
    def __init__(self, min_symbols=1):
        self.min_symbols = min_symbols
    
    def validate(self, password, user=None):
        # Define symbols
        symbols = r'[!@#$%^&*(),.?":{}|<>]'
        
        if len(re.findall(symbols, password)) < self.min_symbols:
            raise ValidationError(
                _("Your password must contain at least %(min_symbols)d symbol (e.g., !@#$%^&*)"),
                code='password_no_symbol',
                params={'min_symbols': self.min_symbols},
            )
    
    def get_help_text(self):
        return _("Your password must contain at least one symbol (e.g., !@#$%^&*)")