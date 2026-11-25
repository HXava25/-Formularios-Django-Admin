from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib import admin
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .admin import SafeUserAdmin
from .forms import SolicitudForm
from .models import Solicitud

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class SolicitudFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ana", password="StrongPass123!")

    def datos(self, **overrides):
        data = {
            "asunto": "Problema de acceso",
            "categoria": Solicitud.Categoria.ACCESO,
            "prioridad": Solicitud.Prioridad.NORMAL,
            "descripcion": "No puedo ingresar al sistema desde esta mañana.",
        }
        data.update(overrides)
        return data

    def test_sanitizes_text_and_validates_cross_field_rules(self):
        form = SolicitudForm(
            self.datos(
                asunto="  Problema   de acceso  ",
                descripcion="  El portal   muestra un error al iniciar sesión.  ",
            )
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["asunto"], "Problema de acceso")
        self.assertEqual(
            form.cleaned_data["descripcion"],
            "El portal muestra un error al iniciar sesión.",
        )

        invalid = SolicitudForm(
            self.datos(
                categoria=Solicitud.Categoria.GENERAL,
                prioridad=Solicitud.Prioridad.CRITICA,
            )
        )
        self.assertFalse(invalid.is_valid())
        self.assertIn("prioridad", invalid.errors)

    def test_form_errors_show_on_field_for_duplicate_subject(self):
        form = SolicitudForm(
            self.datos(
                asunto="No puedo acceder",
                descripcion="No puedo acceder porque la página no responde.",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("descripcion", form.errors)

    def test_html_is_not_interpreted_as_markup(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("solicitud_crear"),
            self.datos(asunto="<script>alerta</script>"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Solicitud.objects.exists())


@override_settings(SECURE_SSL_REDIRECT=False)
class SolicitudAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="propietaria", password="StrongPass123!")
        self.other = User.objects.create_user(username="otra", password="StrongPass123!")
        self.solicitud = Solicitud.objects.create(
            solicitante=self.owner,
            asunto="Consulta sobre mi cuenta",
            categoria=Solicitud.Categoria.GENERAL,
            descripcion="Necesito ayuda con la configuración de mi cuenta.",
        )

    def test_users_only_see_their_own_requests(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("solicitud_detalle", args=[self.solicitud.pk]))
        self.assertEqual(response.status_code, 403)

    def test_permissioned_operator_can_see_all_requests(self):
        permission = Permission.objects.get(codename="view_all_solicitudes")
        self.other.user_permissions.add(permission)
        self.client.force_login(self.other)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, self.solicitud.asunto)

    def test_create_requires_login_and_response_has_security_headers(self):
        response = self.client.get(reverse("solicitud_crear"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('solicitud_crear')}")

        self.client.force_login(self.owner)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])

    def test_state_change_requires_permission_and_post(self):
        url = reverse("solicitud_estado", args=[self.solicitud.pk])
        self.client.force_login(self.owner)
        response = self.client.post(url, {"estado": Solicitud.Estado.RESUELTA})
        self.assertEqual(response.status_code, 403)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado, Solicitud.Estado.ABIERTA)


@override_settings(SECURE_SSL_REDIRECT=False)
class FullFlowTests(TestCase):
    def test_registration_request_access_and_logout_flow(self):
        registration = self.client.post(
            reverse("registro"),
            {
                "username": "camila",
                "first_name": "Camila",
                "email": "camila@example.com",
                "password1": "Verde-Mesa-7391!",
                "password2": "Verde-Mesa-7391!",
            },
        )
        self.assertRedirects(registration, reverse("dashboard"))
        user = User.objects.get(username="camila")
        self.assertTrue(user.is_authenticated)

        created = self.client.post(
            reverse("solicitud_crear"),
            {
                "asunto": "Acceso al portal de cursos",
                "categoria": Solicitud.Categoria.ACCESO,
                "prioridad": Solicitud.Prioridad.ALTA,
                "descripcion": "El portal no reconoce mi cuenta institucional desde hoy.",
            },
        )
        solicitud = Solicitud.objects.get(solicitante=user)
        self.assertRedirects(created, reverse("solicitud_detalle", args=[solicitud.pk]))

        logout = self.client.post(reverse("logout"))
        self.assertRedirects(logout, reverse("login"))
        private_page = self.client.get(reverse("dashboard"))
        self.assertRedirects(
            private_page,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )

    def test_csrf_is_required_for_request_submission(self):
        client = Client(enforce_csrf_checks=True)
        user = User.objects.create_user(username="csrf", password="StrongPass123!")
        client.force_login(user)
        response = client.post(
            reverse("solicitud_crear"),
            {
                "asunto": "Solicitud de acceso",
                "categoria": Solicitud.Categoria.ACCESO,
                "prioridad": Solicitud.Prioridad.NORMAL,
                "descripcion": "Necesito ayuda para ingresar a mi cuenta institucional.",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Solicitud.objects.exists())

    def test_user_admin_does_not_expose_password_or_staff_flags(self):
        user_admin = admin.site._registry[User]
        self.assertIsInstance(user_admin, SafeUserAdmin)
        self.assertNotIn("password", user_admin.fields)
        self.assertNotIn("is_staff", user_admin.fields)
        self.assertNotIn("is_superuser", user_admin.fields)
