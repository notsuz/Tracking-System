(function () {
    'use strict';

    // ---------- Password visibility toggles ----------
    document.querySelectorAll('.toggle-pw').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const input = this.previousElementSibling;
            const icon = this.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.replace('fa-eye', 'fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.replace('fa-eye-slash', 'fa-eye');
            }
        });
    });

    // ---------- Live password rule checker ----------
    const newPwInput = document.getElementById('newPassword');
    const rules = {
        'rule-length': v => v.length >= 8,
        'rule-upper': v => /[A-Z]/.test(v),
        'rule-lower': v => /[a-z]/.test(v),
        'rule-number': v => /[0-9]/.test(v),
        'rule-special': v => /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`;]/.test(v),
    };

    if (newPwInput) {
        newPwInput.addEventListener('input', function () {
            const v = this.value;
            Object.keys(rules).forEach(function (id) {
                const el = document.getElementById(id);
                if (el) el.classList.toggle('valid', rules[id](v));
            });
        });
    }

    // ---------- Helpers ----------
    function getCookie(name) {
        const value = '; ' + document.cookie;
        const parts = value.split('; ' + name + '=');
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    function showMsg(type, message) {
        const container = document.getElementById('messageContainer');
        if (!container) return;
        container.innerHTML =
            '<div class="alert alert-' + (type === 'success' ? 'success' : 'danger') +
            ' alert-dismissible fade show">' + message +
            '<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ---------- Form submit ----------
    const form = document.getElementById('changePasswordForm');
    if (!form) return;

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        const oldPw = document.getElementById('oldPassword').value;
        const newPw = document.getElementById('newPassword').value;
        const confirmPw = document.getElementById('confirmPassword').value;

        // Client-side checks
        if (!oldPw || !newPw || !confirmPw) {
            return showMsg('error', 'Please fill in all three fields.');
        }
        if (newPw !== confirmPw) {
            return showMsg('error', 'New passwords do not match.');
        }
        const failed = Object.keys(rules).filter(function (id) { return !rules[id](newPw); });
        if (failed.length) {
            return showMsg('error', 'Password does not meet all requirements.');
        }

        // Submit
        const btn = document.getElementById('submitBtn');
        const original = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Updating...';

        fetch('/api/accounts/change-password/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            credentials: 'same-origin',   // ← CRITICAL: send sessionid + csrftoken
            redirect: 'manual',           // ← detect 302 instead of following it
            body: JSON.stringify({
                old_password: oldPw,
                new_password: newPw,
                confirm_password: confirmPw,
            }),
        })
            .then(function (r) {
                // If it's a redirect (302/opaque), user is not authenticated
                if (r.type === 'opaqueredirect' || r.status === 0 || r.status === 302) {
                    throw new Error('Session expired. Please log out and log back in.');
                }
                return r.text().then(function (text) {
                    let body = null;
                    try { body = JSON.parse(text); } catch (_) { /* HTML */ }
                    return { ok: r.ok, status: r.status, body: body, raw: text };
                });
            })
            .then(function (res) {
                if (!res.ok) {
                    let msg = 'Failed to update password.';
                    if (res.body) {
                        msg = res.body.detail
                            || (res.body.non_field_errors && res.body.non_field_errors[0])
                            || (res.body.old_password && res.body.old_password[0])
                            || (res.body.new_password && res.body.new_password[0])
                            || (res.body.confirm_password && res.body.confirm_password[0])
                            || msg;
                    } else if (res.status === 403) {
                        msg = 'CSRF check failed. Refresh the page and try again.';
                    } else if (res.status === 500) {
                        msg = 'Server error. Check the Django console.';
                    }
                    throw new Error(msg);
                }

                showMsg('success', 'Password updated! Redirecting...');
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                setTimeout(function () { window.location.href = '/login/'; }, 1500);
            })
            .catch(function (err) {
                console.error('Change password error:', err);
                showMsg('error', err.message);
                btn.disabled = false;
                btn.innerHTML = original;
            });
    });
})();