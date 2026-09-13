// Password visibility toggle
document.getElementById('togglePassword')?.addEventListener('click', function () {
    const inp = document.getElementById('password');
    const icon = this.querySelector('i');
    if (inp.type === 'password') {
        inp.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        inp.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
});

// Login form
document.getElementById('loginForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const btn = document.getElementById('loginBtn');
    const original = btn.innerHTML;

    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Signing in...';
    btn.disabled = true;
    document.getElementById('messageContainer').innerHTML = '';

    // ---- Step 1: JWT login + create Django session (same request) ----
    fetch('/api/accounts/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',          // ← CRITICAL: store sessionid cookie
        body: JSON.stringify({ username, password }),
    })
        .then(function (r) {
            if (!r.ok) {
                return r.json().then(function (err) {
                    const msg = err.detail
                        || (err.non_field_errors && err.non_field_errors[0])
                        || Object.values(err).flat()[0]
                        || 'Invalid credentials';
                    throw new Error(msg);
                });
            }
            return r.json();
        })
        .then(function (data) {
            if (!data.access) throw new Error('Login failed');

            // Store JWT for API clients
            localStorage.setItem('access_token', data.access);
            localStorage.setItem('refresh_token', data.refresh);

            // ---- Step 2: Optionally auto-create attendance (interns only) ----
            // We call session-login for backward-compat; it also sets the session.
            return fetch('/api/session-login/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',   // ← CRITICAL
                body: JSON.stringify({ user_id: data.user.id }),
            }).then(function (r) { return r.json(); });
        })
        .then(function (result) {
            if (!result.success) throw new Error(result.error || 'Session failed');

            // ---- Step 3: Redirect ----
            // If the user must change password, go there first.
            if (result.user.mustChangePassword) {
                window.location.href = '/change-password/';
                return;
            }
            const role = result.user.role;
            if (role === 'admin') window.location.href = '/admin-panel/';
            else if (role === 'team_lead') window.location.href = '/lead/dashboard/';
            else window.location.href = '/dashboard/';
        })
        .catch(function (err) {
            document.getElementById('messageContainer').innerHTML =
                '<div class="alert alert-danger alert-dismissible fade show">' +
                err.message +
                '<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>';
            btn.innerHTML = original;
            btn.disabled = false;
        });
});