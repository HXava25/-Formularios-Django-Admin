from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import Solicitud
from .sanitizers import sanitize_input

User = get_user_model()


class RegistroUsuarioForm(UserCreationForm):
    first_name = forms.CharField(
        label="Nombre",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "given-name"}),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "email")
        labels = {"username": "Usuario"}

    def clean_email(self):
        email = sanitize_input(self.cleaned_data["email"]).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Ya existe una cuenta con ese correo electrónico.")
        return email

    def clean_first_name(self):
        name = sanitize_input(self.cleaned_data["first_name"])
        if len(name) < 2:
            raise ValidationError("El nombre debe tener al menos 2 caracteres.")
        return name


class SolicitudForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ("asunto", "categoria", "prioridad", "descripcion")
        widgets = {
            "asunto": forms.TextInput(
                attrs={"placeholder": "Ej. No puedo acceder al portal", "maxlength": 100}
            ),
            "categoria": forms.Select(),
            "prioridad": forms.Select(),
            "descripcion": forms.Textarea(
                attrs={
                    "rows": 6,
                    "maxlength": 3000,
                    "placeholder": "Cuéntanos qué ocurrió y qué esperabas que sucediera.",
                }
            ),
        }

    def clean_asunto(self):
        asunto = sanitize_input(self.cleaned_data["asunto"])
        if len(asunto) < 8:
            raise ValidationError("El asunto debe tener al menos 8 caracteres.")
        return asunto

    def clean_descripcion(self):
        descripcion = sanitize_input(self.cleaned_data["descripcion"], multiline=True)
        if len(descripcion) < 20:
            raise ValidationError("Agrega más contexto (mínimo 20 caracteres).")
        return descripcion

    def clean(self):
        cleaned_data = super().clean()
        asunto = cleaned_data.get("asunto")
        descripcion = cleaned_data.get("descripcion")

        if asunto and descripcion and asunto.casefold() in descripcion.casefold():
            self.add_error(
                "descripcion",
                "La descripción debe aportar detalles adicionales al asunto.",
            )
        return cleaned_data


class FiltroSolicitudForm(forms.Form):
    q = forms.CharField(
        label="Buscar",
        required=False,
        max_length=100,
        widget=forms.TextInput(
            attrs={"placeholder": "Buscar por asunto o descripción", "type": "search"}
        ),
    )
    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[("", "Todos los estados"), *Solicitud.Estado.choices],
    )
    categoria = forms.ChoiceField(
        label="Categoría",
        required=False,
        choices=[("", "Todas las categorías"), *Solicitud.Categoria.choices],
    )

    def clean_q(self):
        return sanitize_input(self.cleaned_data.get("q", ""))


class EstadoSolicitudForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ("estado",)
