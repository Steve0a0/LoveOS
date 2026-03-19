import logging

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger("loveos.audit")


def get_couple(user):
    """
    Return the Couple the user belongs to, or None.
    Uses the reverse OneToOne relation on CoupleMember (couple_membership).
    """
    membership = getattr(user, "couple_membership", None)
    return membership.couple if membership else None


def require_couple_response(user):
    """
    Return (couple, None) if the user is paired,
    or (None, error_response) if not.  Keeps views DRY.
    """
    couple = get_couple(user)
    if couple is None:
        return None, Response(
            {"detail": "You must be in a couple to use this feature."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return couple, None
