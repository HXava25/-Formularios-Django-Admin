import logging

from .sanitizers import sanitize_input


logger = logging.getLogger("solicitudes.security")

SANITIZABLE_POST_FIELDS = frozenset(
    {"asunto", "descripcion", "nombre_contacto", "email_contacto"}
)


class InputSanitizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST":
            sanitized = request.POST.copy()
            for field in SANITIZABLE_POST_FIELDS:
                if field in sanitized:
                    sanitized.setlist(
                        field,
                        [
                            sanitize_input(value, multiline=field == "descripcion")
                            for value in sanitized.getlist(field)
                        ],
                    )
            request.POST = sanitized
        return self.get_response(request)


class AuditSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        actor = request.user.get_username() if request.user.is_authenticated else "anonymous"
        logger.info(
            "request method=%s path=%s status=%s actor=%s",
            request.method,
            request.path,
            response.status_code,
            actor,
        )
        admin_inline_assets = (
            " style-src 'self' 'unsafe-inline';"
            " script-src 'self' 'unsafe-inline';"
            if request.path.startswith("/admin/")
            else " style-src 'self'; script-src 'self';"
        )
        response.setdefault(
            "Content-Security-Policy",
            "default-src 'self';"
            + admin_inline_assets
            + " img-src 'self' data:;"
            + " object-src 'none';"
            + " form-action 'self';"
            + " frame-ancestors 'none';"
            + " base-uri 'self'",
        )
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response
