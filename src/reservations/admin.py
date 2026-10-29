from django.contrib import admin

from reservations.models import Customer, Reservation, Room


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user")
    search_fields = ("display_name", "user__username", "user__email")


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "floor", "capacity")
    search_fields = ("name",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("customer", "room", "status", "starts_at", "ends_at")
    list_filter = ("status", "room")
    search_fields = ("customer__display_name", "customer__user__email", "room__name")
    readonly_fields = ("status", "hold_reason", "cancel_reason")
