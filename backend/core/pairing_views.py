import logging
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Couple, CoupleMember, Invite
from .serializers import CoupleSerializer, InviteSerializer, UserSerializer

logger = logging.getLogger("loveos.audit")

INVITE_EXPIRY_DAYS = 7


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_couple(request):
    """Create a new couple and add the current user as the first member."""
    # Check if user is already in a couple
    if hasattr(request.user, "couple_membership"):
        return Response(
            {"detail": "You are already in a couple."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    couple = Couple.objects.create(
        name=request.data.get("name", ""),
    )
    CoupleMember.objects.create(couple=couple, user=request.user)
    logger.info("couple.created user=%s couple=%s", request.user.pk, couple.pk)

    return Response(
        CoupleSerializer(couple).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_invite(request):
    """Generate an invite link for the current user's couple."""
    membership = getattr(request.user, "couple_membership", None)
    if not membership:
        return Response(
            {"detail": "You must create a couple first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    couple = membership.couple

    # Check if couple already has 2 members
    if couple.members.count() >= 2:
        return Response(
            {"detail": "Your couple already has two members."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Expire any previous pending invites for this couple
    Invite.objects.filter(couple=couple, status=Invite.Status.PENDING).update(
        status=Invite.Status.EXPIRED
    )

    invite = Invite.objects.create(
        couple=couple,
        invited_by=request.user,
        invited_email=request.data.get("email", ""),
        expires_at=timezone.now() + timedelta(days=INVITE_EXPIRY_DAYS),
    )
    logger.info("invite.created user=%s couple=%s invite=%s", request.user.pk, couple.pk, invite.pk)

    app_url = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else "http://localhost:3000"
    invite_link = f"{app_url}/invite/{invite.code}"

    return Response(
        {
            **InviteSerializer(invite).data,
            "invite_link": invite_link,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def validate_invite(request, token):
    """Check if an invite token is valid and can be accepted."""
    try:
        invite = Invite.objects.select_related("couple").get(code=token)
    except Invite.DoesNotExist:
        return Response(
            {"detail": "Invite not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    errors = []

    if invite.status != Invite.Status.PENDING:
        errors.append(f"This invite has already been {invite.status}.")

    if invite.expires_at and invite.expires_at < timezone.now():
        errors.append("This invite has expired.")
        # Mark it expired
        if invite.status == Invite.Status.PENDING:
            invite.status = Invite.Status.EXPIRED
            invite.save(update_fields=["status"])

    if invite.couple.members.count() >= 2:
        errors.append("This couple already has two members.")

    if hasattr(request.user, "couple_membership"):
        errors.append("You are already in a couple.")

    if invite.invited_by == request.user:
        errors.append("You cannot accept your own invite.")

    if errors:
        return Response(
            {"detail": " ".join(errors), "valid": False},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            "valid": True,
            "couple_name": invite.couple.name,
            "invited_by": invite.invited_by.profile.display_name
            if hasattr(invite.invited_by, "profile")
            else invite.invited_by.email,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_invite(request, token):
    """Accept an invite and join the couple."""
    try:
        invite = Invite.objects.select_related("couple").get(code=token)
    except Invite.DoesNotExist:
        return Response(
            {"detail": "Invite not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Re-validate everything
    if invite.status != Invite.Status.PENDING:
        return Response(
            {"detail": f"This invite has already been {invite.status}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if invite.expires_at and invite.expires_at < timezone.now():
        invite.status = Invite.Status.EXPIRED
        invite.save(update_fields=["status"])
        return Response(
            {"detail": "This invite has expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if invite.couple.members.count() >= 2:
        return Response(
            {"detail": "This couple already has two members."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if hasattr(request.user, "couple_membership"):
        return Response(
            {"detail": "You are already in a couple."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if invite.invited_by == request.user:
        return Response(
            {"detail": "You cannot accept your own invite."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Join the couple
    try:
        CoupleMember.objects.create(couple=invite.couple, user=request.user)
    except IntegrityError:
        return Response(
            {"detail": "You are already in a couple."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Mark invite as accepted
    invite.status = Invite.Status.ACCEPTED
    invite.save(update_fields=["status"])
    logger.info(
        "invite.accepted user=%s couple=%s invite=%s",
        request.user.pk, invite.couple.pk, invite.pk,
    )

    # Expire all other pending invites for this couple
    Invite.objects.filter(
        couple=invite.couple, status=Invite.Status.PENDING
    ).update(status=Invite.Status.EXPIRED)

    return Response(
        {
            "detail": "You have joined the couple!",
            "couple": CoupleSerializer(invite.couple).data,
            "user": UserSerializer(request.user).data,
        },
        status=status.HTTP_200_OK,
    )
