from django.urls import path

from . import pairing_views

urlpatterns = [
    path("couples/create/", pairing_views.create_couple, name="couple-create"),
    path("invites/create/", pairing_views.create_invite, name="invite-create"),
    path("invites/<uuid:token>/", pairing_views.validate_invite, name="invite-validate"),
    path("invites/<uuid:token>/accept/", pairing_views.accept_invite, name="invite-accept"),
]
