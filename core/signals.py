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
    # Login can run in contexts without MessageMiddleware, such as test helpers.
    messages.info(
        request,
        f"💡 **Inspiration for Today:** {quote}",
        fail_silently=True,
    )
