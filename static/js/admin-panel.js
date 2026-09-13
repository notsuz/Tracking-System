/* ============================================================
   admin-panel.js
   ============================================================ */

function csrf() {
    return (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
}

function token() {
    return localStorage.getItem('access_token');
}

function authHeaders(extra) {
    return Object.assign(
        {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf(),
        },
        extra || {}
    );
}

// ============================================================
// DASHBOARD PAGE — Overview + Recent Users
// ============================================================
if (document.getElementById('totalUsers')) {
    loadOverview();
    loadDashboardUsers();
}

function loadOverview() {
    fetch('/api/accounts/admin/overview/', { credentials: 'same-origin' })
        .then(r => r.json())
        .then(data => {
            document.getElementById('totalUsers').textContent = data.users.total || 0;
            document.getElementById('totalInterns').textContent = data.users.interns || 0;
            document.getElementById('totalLeads').textContent = data.users.team_leads || 0;
            document.getElementById('totalAdmins').textContent = data.users.admins || 0;

            document.getElementById('todayOnline').textContent = data.today.online || 0;
            document.getElementById('todayDuration').textContent = data.today.total_duration || '00:00';
            document.getElementById('todayTasks').textContent = data.today.tasks_completed || 0;
            document.getElementById('availRate').textContent = data.availability.response_rate || '0%';

            document.getElementById('weekDuration').textContent = data.week.total_duration || '00:00';
            document.getElementById('weekBreak').textContent = data.week.total_break || '00:00';
            document.getElementById('weekTasksAssigned').textContent = data.week.tasks_assigned || 0;
            document.getElementById('weekTasksCompleted').textContent = data.week.tasks_completed || 0;

            document.getElementById('availTotal').textContent = data.availability.total_checks || 0;
            document.getElementById('availResponded').textContent = data.availability.responded || 0;
            document.getElementById('availMissed').textContent = data.availability.missed || 0;
            document.getElementById('availRateDetail').textContent = data.availability.response_rate || '0%';
        })
        .catch(err => console.error('Failed to load overview:', err));
}

function loadDashboardUsers() {
    fetch('/api/accounts/admin/users/', {
        headers: authHeaders(),
        credentials: 'same-origin',
    })
        .then(r => r.json())
        .then(data => {
            const users = data.results || data || [];
            const recent = users.slice(0, 5);
            const tbody = document.getElementById('recentUsersBody');

            if (!recent.length) {
                tbody.innerHTML =
                    '<tr><td colspan="6" class="empty-state">' +
                    '<i class="fas fa-users"></i>' +
                    '<p class="mb-0">No users yet</p></td></tr>';
                return;
            }

            let html = '';
            recent.forEach(u => {
                html +=
                    '<tr>' +
                    '<td><strong>' + u.username + '</strong></td>' +
                    '<td>' + (u.first_name || '') + ' ' + (u.last_name || '') + '</td>' +
                    '<td>' + u.email + '</td>' +
                    '<td><span class="role-badge ' + u.role + '">' + (u.role_display || u.role) + '</span></td>' +
                    '<td>' + (u.is_active ? 'Active' : 'Disabled') + '</td>' +
                    '<td>' + (u.must_change_password ? 'Yes' : 'No') + '</td>' +
                    '</tr>';
            });
            tbody.innerHTML = html;
        })
        .catch(err => console.error('Failed to load users:', err));
}

// ============================================================
// USERS PAGE — list, reset password, delete
// ============================================================
if (document.getElementById('usersBody')) {
    loadUsers();
    document.getElementById('searchInput')?.addEventListener('input', debounce(loadUsers, 400));
    document.getElementById('roleFilter')?.addEventListener('change', loadUsers);
    document.getElementById('confirmResetBtn')?.addEventListener('click', doResetPassword);
}

function loadUsers() {
    const params = new URLSearchParams();
    const s = document.getElementById('searchInput')?.value.trim();
    const r = document.getElementById('roleFilter')?.value;
    if (s) params.append('search', s);
    if (r) params.append('role', r);

    fetch('/api/accounts/admin/users/?' + params.toString(), {
        headers: authHeaders(),
        credentials: 'same-origin',
    })
        .then(r => r.json())
        .then(data => {
            const users = data.results || data || [];
            const tbody = document.getElementById('usersBody');
            if (!users.length) {
                tbody.innerHTML =
                    '<tr><td colspan="7" class="empty-state">' +
                    '<i class="fas fa-users"></i>' +
                    '<p class="mb-0">No users found</p></td></tr>';
                return;
            }
            let html = '';
            users.forEach(u => {
                const currentUser = window.DJANGO && window.DJANGO.username === u.username;
                html +=
                    '<tr>' +
                    '<td><strong>' + u.username + '</strong></td>' +
                    '<td>' + (u.first_name || '') + ' ' + (u.last_name || '') + '</td>' +
                    '<td>' + u.email + '</td>' +
                    '<td><span class="role-badge ' + u.role + '">' + (u.role_display || u.role) + '</span></td>' +
                    '<td>' + (u.is_active ? 'Active' : 'Disabled') + '</td>' +
                    '<td><span class="badge-pw ' + (u.must_change_password ? 'yes' : 'no') + '">' +
                        (u.must_change_password ? 'Yes' : 'No') + '</span></td>' +
                    '<td class="text-end">' +
                        '<button class="btn btn-sm btn-outline-warning" onclick="openResetModal(' + u.id + ', \'' + u.username + '\')">' +
                        '<i class="fas fa-key"></i></button>' +
                        (currentUser ? '' :
                            '<button class="btn btn-sm btn-outline-danger" onclick="deleteUser(' + u.id + ', \'' + u.username + '\')">' +
                            '<i class="fas fa-trash"></i></button>') +
                    '</td>' +
                    '</tr>';
            });
            tbody.innerHTML = html;
        });
}

let resetTargetId = null;
function openResetModal(userId, username) {
    resetTargetId = userId;
    document.getElementById('resetUsername').textContent = username;
    document.getElementById('resetNewPassword').value = '';
    new bootstrap.Modal(document.getElementById('resetPasswordModal')).show();
}

function doResetPassword() {
    const pw = document.getElementById('resetNewPassword').value;
    if (!pw) return showToast('error', 'Enter a password');

    fetch('/api/accounts/admin/users/' + resetTargetId + '/reset-password/', {
        method: 'POST',
        headers: authHeaders(),
        credentials: 'same-origin',
        body: JSON.stringify({ new_password: pw })
    })
        .then(r => r.json().then(b => ({ ok: r.ok, body: b })))
        .then(({ ok, body }) => {
            if (!ok) {
                const msg = Object.values(body).flat()[0] || 'Failed to reset';
                throw new Error(msg);
            }
            bootstrap.Modal.getInstance(document.getElementById('resetPasswordModal')).hide();
            showToast('success', body.message);
            loadUsers();
        })
        .catch(err => showToast('error', err.message));
}

function deleteUser(id, username) {
    if (!confirm('Delete user "' + username + '"? This cannot be undone.')) return;
    fetch('/api/accounts/admin/users/' + id + '/', {
        method: 'DELETE',
        headers: authHeaders(),
        credentials: 'same-origin',
    })
        .then(r => {
            if (r.status === 204) {
                showToast('success', 'User deleted');
                loadUsers();
            } else {
                return r.json().then(b => { throw new Error(b.error || 'Delete failed'); });
            }
        })
        .catch(err => showToast('error', err.message));
}

// ============================================================
// CREATE USER PAGE
// ============================================================
if (document.getElementById('createUserForm')) {
    document.getElementById('generatePassword')?.addEventListener('click', function () {
        const pw = generateStrongPassword();
        document.getElementById('password').value = pw;
    });

    document.getElementById('createUserForm').addEventListener('submit', function (e) {
        e.preventDefault();
        const btn = document.getElementById('submitBtn');
        const original = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Creating...';
        btn.disabled = true;
        document.getElementById('messageContainer').innerHTML = '';

        const payload = {
            username: document.getElementById('username').value.trim(),
            email: document.getElementById('email').value.trim(),
            first_name: document.getElementById('firstName').value.trim(),
            last_name: document.getElementById('lastName').value.trim(),
            role: document.getElementById('role').value,
            phone: document.getElementById('phone').value.trim(),
            date_of_joining: document.getElementById('dateOfJoining').value || null,
            password: document.getElementById('password').value
        };

        fetch('/api/accounts/admin/users/create/', {
            method: 'POST',
            headers: authHeaders(),
            credentials: 'same-origin',
            body: JSON.stringify(payload)
        })
            .then(r => r.json().then(b => ({ ok: r.ok, body: b })))
            .then(({ ok, body }) => {
                if (!ok) {
                    let msg = '';
                    if (typeof body === 'object') {
                        msg = Object.entries(body).map(([k, v]) =>
                            '<strong>' + k + ':</strong> ' + (Array.isArray(v) ? v.join(', ') : v)
                        ).join('<br>');
                    } else msg = body;
                    throw new Error(msg);
                }
                document.getElementById('messageContainer').innerHTML =
                    '<div class="alert alert-success">' +
                    '<i class="fas fa-check-circle"></i> User <strong>' + body.username +
                    '</strong> created! Redirecting...</div>';
                setTimeout(() => window.location.href = '/admin-panel/users/', 1500);
            })
            .catch(err => {
                document.getElementById('messageContainer').innerHTML =
                    '<div class="alert alert-danger">' + err.message + '</div>';
                btn.innerHTML = original;
                btn.disabled = false;
            });
    });
}

// ============================================================
// Utilities
// ============================================================
function generateStrongPassword() {
    const upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
    const lower = 'abcdefghijkmnopqrstuvwxyz';
    const digits = '23456789';
    const special = '!@#$%^&*';
    const pick = (s) => s[Math.floor(Math.random() * s.length)];
    let pw = '';
    pw += pick(upper) + pick(lower) + pick(digits) + pick(special);
    const all = upper + lower + digits + special;
    for (let i = 0; i < 6; i++) pw += pick(all);
    return pw.split('').sort(() => Math.random() - 0.5).join('');
}

function debounce(fn, ms) {
    let t;
    return function (...args) {
        clearTimeout(t);
        t = setTimeout(() => fn.apply(this, args), ms);
    };
}