from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib import messages
import random
from .quotes import MOTIVATIONAL_QUOTES

@receiver(user_logged_in)
def show_motivational_quote(sender, user, request, **kwargs):
    """
    Display a random motivational quote when a user logs in.
    """
    quote = random.choice(MOTIVATIONAL_QUOTES)
    # Using 'info' level for the message so it shows up prominently but isn't an error/success notification per se
    # Alternatively, we could use a custom level or just stick with info/success.
    # The user requested an "alert", so messages framework is perfect.
    messages.info(request, f"💡 **Inspiration for Today:** {quote}")
