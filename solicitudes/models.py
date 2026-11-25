from django.conf import settings
from django.core.validators import MaxLengthValidator, MinLengthValidator, RegexValidator
from django.db import models
from django.utils import timezone

from .sanitizers import sanitize_input


class Solicitud(models.Model):
    class Categoria(models.TextChoices):
        GENERAL = "general", "Consulta general"
        ACCESO = "acceso", "Acceso a cuenta"
        SEGURIDAD = "seguridad", "Seguridad"
        PLATAFORMA = "plataforma", "Plataforma"

    class Prioridad(models.TextChoices):
        BAJA = "baja", "Baja"
        NORMAL = "normal", "Normal"
        ALTA = "alta", "Alta"
        CRITICA = "critica", "Crítica"

    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        EN_PROGRESO = "en_progreso", "En progreso"
        RESUELTA = "resuelta", "Resuelta"
        CERRADA = "cerrada", "Cerrada"

    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitudes",
    )
    asunto = models.CharField(
        "asunto",
        max_length=100,
        validators=[
            MinLengthValidator(8, "Escribe un asunto de al menos 8 caracteres."),
            RegexValidator(
                regex=r"^[\w\s.,:;¿?¡!()/#\-áéíóúÁÉÍÓÚñÑ]+$",
                message="El asunto contiene caracteres no permitidos.",
            ),
        ],
    )
    categoria = models.CharField(
        "categoría",
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.GENERAL,
    )
    descripcion = models.TextField(
        "descripción",
        validators=[
            MinLengthValidator(20, "Describe el problema con al menos 20 caracteres."),
            MaxLengthValidator(3000, "La descripción no puede superar 3000 caracteres."),
        ],
    )
    prioridad = models.CharField(
        "prioridad",
        max_length=10,
        choices=Prioridad.choices,
        default=Prioridad.NORMAL,
    )
    estado = models.CharField(
        "estado",
        max_length=15,
        choices=Estado.choices,
        default=Estado.ABIERTA,
    )
    creado_en = models.DateTimeField("creada", default=timezone.now, editable=False)
    actualizado_en = models.DateTimeField("actualizada", auto_now=True)
    resuelta_en = models.DateTimeField("resuelta", null=True, blank=True)

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "solicitud"
        verbose_name_plural = "solicitudes"
        permissions = [
            ("view_all_solicitudes", "Puede ver todas las solicitudes"),
            ("manage_solicitudes", "Puede gestionar solicitudes"),
        ]

    def __str__(self):
        return f"#{self.pk} · {self.asunto}"

    def clean(self):
        super().clean()
        self.asunto = sanitize_input(self.asunto)
        self.descripcion = sanitize_input(self.descripcion, multiline=True)
        if (
            self.prioridad == self.Prioridad.CRITICA
            and self.categoria not in {self.Categoria.SEGURIDAD, self.Categoria.ACCESO}
        ):
            from django.core.exceptions import ValidationError

            raise ValidationError(
                {
                    "prioridad": (
                        "La prioridad crítica solo aplica a solicitudes de seguridad "
                        "o acceso a cuenta."
                    )
                }
            )
        if self.estado == self.Estado.RESUELTA and self.resuelta_en is None:
            self.resuelta_en = timezone.now()
        elif self.estado != self.Estado.RESUELTA:
            self.resuelta_en = None

    @property
    def dias_abierta(self):
        end = self.resuelta_en or timezone.now()
        return max((end - self.creado_en).days, 0)
