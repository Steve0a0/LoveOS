from django.contrib import admin

from .models import (
    Couple,
    CoupleMember,
    ImportantDate,
    Invite,
    LocationPoint,
    LocationShareSession,
    Memory,
    Note,
    Profile,
    PushSubscription,
    SafeCheckEvent,
)

admin.site.register(Profile)
admin.site.register(Couple)
admin.site.register(CoupleMember)
admin.site.register(Invite)
admin.site.register(Note)
admin.site.register(ImportantDate)
admin.site.register(Memory)
admin.site.register(SafeCheckEvent)
admin.site.register(LocationShareSession)
admin.site.register(LocationPoint)
admin.site.register(PushSubscription)
