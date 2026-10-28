from django import forms

from reservations.models import Reservation


class ReservationUpdateForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ("room", "starts_at", "ends_at", "internal_note")
        widgets = {
            "starts_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
            "ends_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
            "internal_note": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["starts_at"].input_formats = ("%Y-%m-%dT%H:%M",)
        self.fields["ends_at"].input_formats = ("%Y-%m-%dT%H:%M",)

    def clean(self):
        cleaned_data = super().clean()
        starts_at = cleaned_data.get("starts_at")
        ends_at = cleaned_data.get("ends_at")

        if starts_at and ends_at and ends_at <= starts_at:
            raise forms.ValidationError(
                "La fecha de fin debe ser posterior a la fecha de inicio."
            )

        return cleaned_data


class ReservationHoldForm(forms.Form):
    reason = forms.CharField(
        label="Motivo",
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
