import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ImportantDate
from .date_serializers import DateCreateSerializer, DateSerializer
from .permissions import require_couple_response

logger = logging.getLogger("loveos.audit")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def date_list_create(request):
    couple, err = require_couple_response(request.user)
    if err:
        return err

    if request.method == "GET":
        dates = (
            ImportantDate.objects.filter(couple=couple)
            .select_related("created_by__profile")
            .order_by("date")
        )
        return Response(DateSerializer(dates, many=True).data)

    # POST
    serializer = DateCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(couple=couple, created_by=request.user)
    obj = ImportantDate.objects.select_related("created_by__profile").get(
        pk=serializer.instance.pk
    )
    logger.info("date.created user=%s couple=%s date=%s", request.user.pk, couple.pk, obj.pk)
    return Response(DateSerializer(obj).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def date_detail(request, pk):
    couple, err = require_couple_response(request.user)
    if err:
        return err

    try:
        obj = ImportantDate.objects.select_related("created_by__profile").get(
            pk=pk, couple=couple
        )
    except ImportantDate.DoesNotExist:
        return Response(
            {"detail": "Date not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == "DELETE":
        logger.info("date.deleted user=%s couple=%s date=%s", request.user.pk, couple.pk, obj.pk)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    serializer = DateCreateSerializer(obj, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    obj.refresh_from_db()
    logger.info("date.updated user=%s couple=%s date=%s", request.user.pk, couple.pk, obj.pk)
    return Response(DateSerializer(obj).data)
