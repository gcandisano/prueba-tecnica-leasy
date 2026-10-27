from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from reservations.constants import (
    RESERVATION_STATUS_CHOICES,
    RESERVATION_STATUS_REQUESTED,
)


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    display_name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.display_name


class Room(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    floor = models.PositiveIntegerField(default=1)
    capacity = models.PositiveIntegerField(default=1)

    def __str__(self) -> str:
        return self.name


class Reservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="reservations",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="reservations",
    )
    status = models.CharField(
        max_length=32,
        choices=RESERVATION_STATUS_CHOICES,
        default=RESERVATION_STATUS_REQUESTED,
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    internal_note = models.TextField(blank=True)
    cancel_reason = models.TextField(blank=True)
    hold_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("starts_at",)
        permissions = (
            ("hold_reservation", "Can put reservation on hold"),
        )

    def __str__(self) -> str:
        return f"{self.customer} · {self.room} · {self.starts_at:%Y-%m-%d %H:%M}"
