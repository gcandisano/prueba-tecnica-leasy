from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from reservations.constants import RESERVATION_HOLDABLE_STATUSES
from reservations.exceptions import ReservationError
from reservations.forms import ReservationHoldForm, ReservationUpdateForm
from reservations.models import Reservation
from reservations.services import ReservationLifecycleService, ReservationUpdateService
from shared.mixins import AuthenticatedPermissionRequiredMixin


class ReservationListView(LoginRequiredMixin, AuthenticatedPermissionRequiredMixin, View):
    permission_required = "reservations.view_reservation"

    def get(self, request: HttpRequest) -> HttpResponse:
        reservations = Reservation.objects.select_related("customer__user", "room")
        return render(
            request,
            "reservations/list.html",
            {"reservations": reservations},
        )


class ReservationDetailView(
    LoginRequiredMixin, AuthenticatedPermissionRequiredMixin, View
):
    permission_required = "reservations.view_reservation"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        reservation = get_object_or_404(
            Reservation.objects.select_related("customer__user", "room"),
            pk=pk,
        )
        return render(
            request,
            "reservations/detail.html",
            {
                "reservation": reservation,
                "can_change": request.user.has_perm("reservations.change_reservation"),
                "can_hold": (
                    request.user.has_perm("reservations.hold_reservation")
                    and reservation.status in RESERVATION_HOLDABLE_STATUSES
                ),
            },
        )


class ReservationUpdateView(
    LoginRequiredMixin, AuthenticatedPermissionRequiredMixin, View
):
    permission_required = "reservations.change_reservation"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        reservation = get_object_or_404(Reservation, pk=pk)
        form = ReservationUpdateForm(instance=reservation)
        return render(
            request,
            "reservations/edit.html",
            {"reservation": reservation, "form": form},
        )

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        reservation = get_object_or_404(Reservation, pk=pk)
        form = ReservationUpdateForm(request.POST, instance=reservation)
        if not form.is_valid():
            return render(
                request,
                "reservations/edit.html",
                {"reservation": reservation, "form": form},
                status=422,
            )

        ReservationUpdateService().update_reservation(
            reservation_id=reservation.id,
            room_id=form.cleaned_data["room"].id,
            starts_at=form.cleaned_data["starts_at"],
            ends_at=form.cleaned_data["ends_at"],
            internal_note=form.cleaned_data["internal_note"],
        )
        messages.success(request, "Reserva actualizada.")
        return redirect("reservation_detail", pk=reservation.id)


class ReservationConfirmView(
    LoginRequiredMixin, AuthenticatedPermissionRequiredMixin, View
):
    permission_required = "reservations.change_reservation"

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        ReservationLifecycleService().confirm_reservation(
            reservation_id=pk,
            actor_id=request.user.id,
        )
        messages.success(request, "Reserva confirmada.")
        return redirect("reservation_detail", pk=pk)


class ReservationHoldView(
    LoginRequiredMixin, AuthenticatedPermissionRequiredMixin, View
):
    permission_required = "reservations.hold_reservation"

    def get(self, request: HttpRequest, pk) -> HttpResponse:
        reservation = get_object_or_404(
            Reservation.objects.select_related("customer__user", "room"),
            pk=pk,
        )
        form = ReservationHoldForm()
        return render(
            request,
            "reservations/hold.html",
            {"reservation": reservation, "form": form},
        )

    def post(self, request: HttpRequest, pk) -> HttpResponse:
        reservation = get_object_or_404(
            Reservation.objects.select_related("customer__user", "room"),
            pk=pk,
        )
        form = ReservationHoldForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "reservations/hold.html",
                {"reservation": reservation, "form": form},
                status=422,
            )

        try:
            ReservationLifecycleService().hold_reservation(
                reservation_id=reservation.id,
                reason=form.cleaned_data["reason"],
                actor_id=request.user.id,
            )
        except ReservationError as exc:
            messages.error(request, exc.detail)
        else:
            messages.success(request, "Reserva puesta en espera.")
        return redirect("reservation_detail", pk=reservation.id)
