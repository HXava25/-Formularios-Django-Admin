from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Solicitud

User = get_user_model()


class SafeUserAdmin(admin.ModelAdmin):
    list_display = ("username", "first_name", "email", "is_active", "date_joined")
    list_filter = ("is_active", "date_joined")
    search_fields = ("username", "first_name", "email")
    readonly_fields = ("username", "last_login", "date_joined")
    fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "groups",
        "last_login",
        "date_joined",
    )
    filter_horizontal = ("groups",)


admin.site.unregister(User)
admin.site.register(User, SafeUserAdmin)


@admin.action(description="Marcar solicitudes seleccionadas como en progreso")
def marcar_en_progreso(modeladmin, request, queryset):
    total = queryset.exclude(estado=Solicitud.Estado.CERRADA).update(
        estado=Solicitud.Estado.EN_PROGRESO,
        resuelta_en=None,
        actualizado_en=timezone.now(),
    )
    modeladmin.message_user(
        request,
        f"{total} solicitud(es) actualizada(s).",
        messages.SUCCESS,
    )


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "asunto",
        "solicitante",
        "categoria",
        "prioridad",
        "estado",
        "creado_en",
        "dias_abierta",
    )
    list_filter = ("estado", "categoria", "prioridad", "creado_en")
    search_fields = ("asunto", "descripcion", "solicitante__username", "solicitante__email")
    readonly_fields = ("solicitante", "creado_en", "actualizado_en", "resuelta_en")
    ordering = ("-creado_en",)
    actions = (marcar_en_progreso,)
    fieldsets = (
        ("Solicitud", {"fields": ("asunto", "categoria", "prioridad", "descripcion")}),
        ("Seguimiento", {"fields": ("estado", "solicitante")}),
        (
            "Auditoría",
            {"fields": ("creado_en", "actualizado_en", "resuelta_en"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Días abierta", ordering="creado_en")
    def dias_abierta(self, obj):
        return obj.dias_abierta

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)
