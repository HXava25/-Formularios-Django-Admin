from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from .forms import (
    EstadoSolicitudForm,
    FiltroSolicitudForm,
    RegistroUsuarioForm,
    SolicitudForm,
)
from .models import Solicitud


def registro(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistroUsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Tu cuenta está lista. Ya puedes registrar una solicitud.")
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    solicitudes = Solicitud.objects.select_related("solicitante")
    es_operador = request.user.has_perm("solicitudes.view_all_solicitudes")
    if not es_operador:
        solicitudes = solicitudes.filter(solicitante=request.user)

    filtro = FiltroSolicitudForm(request.GET or None)
    if filtro.is_valid():
        q = filtro.cleaned_data["q"]
        estado = filtro.cleaned_data["estado"]
        categoria = filtro.cleaned_data["categoria"]
        if q:
            solicitudes = solicitudes.filter(
                Q(asunto__icontains=q) | Q(descripcion__icontains=q)
            )
        if estado:
            solicitudes = solicitudes.filter(estado=estado)
        if categoria:
            solicitudes = solicitudes.filter(categoria=categoria)

    stats = Solicitud.objects.all()
    if not es_operador:
        stats = stats.filter(solicitante=request.user)
    summary = stats.aggregate(
        total=Count("id"),
        abiertas=Count("id", filter=Q(estado=Solicitud.Estado.ABIERTA)),
        en_progreso=Count("id", filter=Q(estado=Solicitud.Estado.EN_PROGRESO)),
        resueltas=Count(
            "id",
            filter=Q(estado__in=[Solicitud.Estado.RESUELTA, Solicitud.Estado.CERRADA]),
        ),
    )
    return render(
        request,
        "solicitudes/dashboard.html",
        {
            "solicitudes": solicitudes,
            "filtro": filtro,
            "summary": summary,
            "es_operador": es_operador,
        },
    )


@login_required
def solicitud_crear(request):
    form = SolicitudForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        solicitud = form.save(commit=False)
        solicitud.solicitante = request.user
        solicitud.full_clean()
        solicitud.save()
        messages.success(request, "Solicitud registrada correctamente.")
        return redirect("solicitud_detalle", pk=solicitud.pk)
    return render(
        request,
        "solicitudes/solicitud_form.html",
        {"form": form, "titulo": "Cuéntanos qué necesitas", "submit_label": "Enviar solicitud"},
    )


@login_required
def solicitud_detalle(request, pk):
    solicitud = get_object_or_404(
        Solicitud.objects.select_related("solicitante"),
        pk=pk,
    )
    if (
        not request.user.has_perm("solicitudes.view_all_solicitudes")
        and solicitud.solicitante_id != request.user.pk
    ):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    estado_form = EstadoSolicitudForm(instance=solicitud)
    return render(
        request,
        "solicitudes/solicitud_detail.html",
        {"solicitud": solicitud, "estado_form": estado_form},
    )


class SolicitudEstadoView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "solicitudes.manage_solicitudes"
    raise_exception = True
    http_method_names = ["post", "options"]

    def post(self, request, pk):
        solicitud = get_object_or_404(Solicitud, pk=pk)
        form = EstadoSolicitudForm(request.POST, instance=solicitud)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.actualizado_en = timezone.now()
            try:
                solicitud.full_clean()
            except ValidationError as error:
                for field, errors in error.message_dict.items():
                    for message in errors:
                        form.add_error(field if field in form.fields else None, message)
            if not form.errors:
                solicitud.save()
                messages.success(request, "Se actualizó el estado de la solicitud.")
                return redirect("solicitud_detalle", pk=solicitud.pk)
        messages.error(request, "No se pudo actualizar el estado. Revisa el formulario.")
        return redirect("solicitud_detalle", pk=solicitud.pk)
