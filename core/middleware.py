from django.shortcuts import redirect
from django.urls import resolve
from django.utils import timezone
from django.contrib.auth import get_user_model


class ForcePasswordChangeMiddleware:
    """
    If a logged-in user has must_change_password=True, force them to
    /change-password/ before they can access any other page.

    Skips:
      - All /api/... paths (so API calls aren't redirected)
      - All /admin/... paths (so Django admin works)
      - Static / media / swagger / redoc
      - Named URLs in EXEMPT_URL_NAMES
    """

    EXEMPT_URL_NAMES = {
        'change_password',
        'logout',
        'login',
        'session_login',
        'token_refresh',
        'admin:index',
        'admin:logout',
        'password_change',
        'password_change_done',
    }

    EXEMPT_PATH_PREFIXES = (
        '/api/',
        '/admin/',
        '/static/',
        '/media/',
        '/swagger',
        '/redoc',
        '/logout/',
        '/login/',
        '/change-password/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware entirely for these prefixes
        if any(request.path.startswith(p) for p in self.EXEMPT_PATH_PREFIXES):
            return self.get_response(request)

        if (
            hasattr(request, 'user')
            and request.user.is_authenticated
            and getattr(request.user, 'must_change_password', False)
        ):
            try:
                match = resolve(request.path_info)
                if match.url_name not in self.EXEMPT_URL_NAMES:
                    return redirect('change_password')
            except Exception:
                pass

        return self.get_response(request)


class UpdateLastSeenMiddleware:
    """
    Bump User.last_login on any request, throttled to once every 5 minutes.

    This turns `last_login` from "when they signed in" into "when they were
    last active", which is what the team leads status page needs to show
    an accurate online indicator.
    """

    THROTTLE_SECONDS = 300  # 5 minutes

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            user = request.user
            now = timezone.now()
            last = user.last_login

            # Only update if last update was more than THROTTLE_SECONDS ago
            if not last or (now - last).total_seconds() > self.THROTTLE_SECONDS:
                User = get_user_model()
                # Use .update() to avoid triggering signals and full save
                User.objects.filter(pk=user.pk).update(last_login=now)
                # Keep the in-memory user fresh for the rest of this request
                user.last_login = now

        return self.get_response(request)