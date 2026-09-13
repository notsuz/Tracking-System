/* ============================================================
   base.js — global helpers, sidebar, notifications, availability
   ============================================================ */

// ---------- Django user data ----------
window.DJANGO = (function () {
    var el = document.getElementById('django-user-data');
    if (!el) return {};
    try { return JSON.parse(el.textContent); } catch (e) { return {}; }
})();

function getToken() { return null; }
function isUserAuthenticated() { return !!(window.DJANGO && window.DJANGO.isAuthenticated); }
function getUserRole() { return (window.DJANGO && window.DJANGO.role) || ''; }

// ---------- CSRF + API helpers ----------
window.getCookie = function (name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
};

window.api = {
    _fetch: function (url, method, body) {
        var opts = {
            method: method || 'GET',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
        };
        if (method && method !== 'GET') {
            opts.headers['X-CSRFToken'] = window.getCookie('csrftoken');
        }
        if (body !== undefined && body !== null) {
            opts.body = JSON.stringify(body);
        }
        return fetch(url, opts).then(function (r) {
            return r.text().then(function (txt) {
                var data = null;
                try { data = JSON.parse(txt); } catch (e) { data = { raw: txt }; }
                return { ok: r.ok, status: r.status, body: data };
            });
        });
    },
    get: function (url) {
        return this._fetch(url, 'GET').then(function (res) {
            if (!res.ok) throw new Error((res.body && res.body.detail) || 'Request failed');
            return res.body;
        });
    },
    post: function (url, body) {
        return this._fetch(url, 'POST', body || {}).then(function (res) {
            if (!res.ok) {
                var msg = (res.body && (res.body.detail || res.body.error)) || 'Request failed';
                throw new Error(msg);
            }
            return res.body;
        });
    },
    patch: function (url, body) {
        return this._fetch(url, 'PATCH', body || {}).then(function (res) {
            if (!res.ok) {
                var msg = (res.body && (res.body.detail || res.body.error)) || 'Request failed';
                throw new Error(msg);
            }
            return res.body;
        });
    },
    del: function (url) {
        return this._fetch(url, 'DELETE').then(function (res) {
            if (!res.ok) throw new Error('Delete failed');
            return res.body;
        });
    },
};

// ============================================================
// SIDEBAR
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    var toggle = document.getElementById('sidebarToggle');
    var sidebar = document.getElementById('sidebar');
    var content = document.getElementById('content');
    var overlay = document.getElementById('sidebarOverlay');

    if (toggle && sidebar) {
        toggle.addEventListener('click', function () {
            if (window.innerWidth <= 992) {
                sidebar.classList.toggle('mobile-open');
                if (overlay) overlay.classList.toggle('show');
            } else {
                sidebar.classList.toggle('collapsed');
                if (content) content.classList.toggle('expanded');
            }
        });
    }
    if (overlay) {
        overlay.addEventListener('click', function () {
            if (sidebar) sidebar.classList.remove('mobile-open');
            this.classList.remove('show');
        });
    }
});

// ============================================================
// LIVE CLOCK
// ============================================================
function updateClock() {
    var el = document.getElementById('liveClock');
    if (el) el.innerHTML = '<i class="fas fa-clock"></i> ' + new Date().toLocaleTimeString();
}
setInterval(updateClock, 1000);
document.addEventListener('DOMContentLoaded', updateClock);

// ============================================================
// TOAST
// ============================================================
function showToast(type, message) {
    var existing = document.querySelector('.toast-container');
    if (existing) existing.remove();

    var colors = {
        success: 'var(--success, #1cc88a)',
        warning: 'var(--warning, #f6c23e)',
        error:   'var(--danger,  #e74a3b)',
        info:    'var(--info,    #36b9cc)'
    };

    var container = document.createElement('div');
    container.className = 'toast-container';
    container.innerHTML =
        '<div class="toast show" role="alert" style="border-left:4px solid ' + (colors[type] || '#333') + ';">' +
        '<div class="toast-body">' + message + '</div>' +
        '</div>';
    document.body.appendChild(container);
    setTimeout(function () { if (container.parentNode) container.remove(); }, 4500);
}
window.showToast = showToast;

// ============================================================
// LOGOUT
// ============================================================
function logoutUser() {
    window.location.href = '/logout/';
}
window.logoutUser = logoutUser;

// ============================================================
// NOTIFICATIONS
// ============================================================
(function () {
    var bell = document.getElementById('notificationBell');
    var dropdown = document.getElementById('notificationDropdown');
    if (!bell || !dropdown) return;

    bell.addEventListener('click', function (e) {
        e.stopPropagation();
        dropdown.classList.toggle('show');
        if (dropdown.classList.contains('show')) loadNotifications();
    });
    document.addEventListener('click', function (e) {
        if (!dropdown.contains(e.target) && e.target !== bell) {
            dropdown.classList.remove('show');
        }
    });
})();

function loadNotifications() {
    if (!isUserAuthenticated()) return;
    api.get('/api/notifications/?is_read=false')
        .then(function (data) {
            var items = data.results || data || [];
            var list = document.getElementById('notificationList');
            var badge = document.getElementById('notificationBadge');
            if (!list) return;

            if (!items.length) {
                list.innerHTML = '<div class="empty-state"><i class="fas fa-bell-slash"></i><p class="mb-0">No new notifications</p></div>';
                if (badge) badge.style.display = 'none';
                return;
            }
            if (badge) {
                badge.textContent = items.length;
                badge.style.display = 'inline-block';
            }
            var html = '';
            items.forEach(function (n) {
                var iconClass = 'info', icon = 'fa-info-circle';
                if (n.notification_type === 'availability_missed') { iconClass = 'danger';  icon = 'fa-exclamation-triangle'; }
                else if (n.notification_type === 'task_assigned')   { iconClass = 'info';    icon = 'fa-tasks'; }
                else if (n.notification_type === 'task_completed')  { iconClass = 'success'; icon = 'fa-check-circle'; }
                html +=
                    '<div class="notification-item ' + (n.is_read ? '' : 'unread') + '" onclick="markRead(' + n.id + ')">' +
                    '<div class="ni-icon ' + iconClass + '"><i class="fas ' + icon + '"></i></div>' +
                    '<div><div class="ni-text">' + n.message + '</div>' +
                    '<div class="ni-time">' + timeAgo(n.created_at) + '</div></div></div>';
            });
            list.innerHTML = html;
        })
        .catch(function () { /* silent */ });
}

var __lastUnreadCount = null;

function loadNotificationCount() {
    if (!isUserAuthenticated()) return;
    api.get('/api/notifications/unread-count/')
        .then(function (data) {
            var badge = document.getElementById('notificationBadge');
            if (badge) {
                if (data.unread_count > 0) {
                    badge.textContent = data.unread_count;
                    badge.style.display = 'inline-block';
                } else {
                    badge.style.display = 'none';
                }
            }
            if (__lastUnreadCount !== null && data.unread_count > __lastUnreadCount) {
                document.dispatchEvent(new CustomEvent('notifications:new'));
            }
            __lastUnreadCount = data.unread_count;
        })
        .catch(function () { /* silent */ });
}

function markRead(id) {
    api.post('/api/notifications/mark-read/', { notification_ids: [id] })
        .then(function () { loadNotifications(); loadNotificationCount(); })
        .catch(function () {});
}
window.markRead = markRead;

function markAllRead() {
    api.post('/api/notifications/mark-read/', {})
        .then(function () { loadNotifications(); loadNotificationCount(); })
        .catch(function () {});
}
window.markAllRead = markAllRead;

function timeAgo(dateStr) {
    var d = new Date(dateStr);
    var s = Math.floor((new Date() - d) / 1000);
    if (s < 60)    return 'just now';
    if (s < 3600)  return Math.floor(s / 60) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}

// ============================================================
// AVAILABILITY POPUP (interns only)
// ============================================================
var availabilityInterval = null;

// Must match AVAILABILITY_RESPONSE_TIMEOUT in config/settings.py
var AVAILABILITY_TIMEOUT_SECONDS = 300;

// Track check ids we've already dismissed (either by responding or timing out)
var __dismissedCheckIds = {};

function checkAvailability() {
    if (!isUserAuthenticated() || getUserRole() !== 'intern') return;

    api.get('/api/availability/pending/')
        .then(function (data) {
            if (!data || !data.id) {
                hideAvailabilityPopup();
                return;
            }

            var checkId = String(data.id);
            if (__dismissedCheckIds[checkId]) {
                // Already handled (responded or missed) — do not show again
                return;
            }

            showAvailabilityPopup(data);
        })
        .catch(function () {
            // 404 = no pending check → hide popup if visible
            hideAvailabilityPopup();
        });
}

function hideAvailabilityPopup() {
    var popup = document.getElementById('availabilityPopup');
    if (!popup) return;
    if (availabilityInterval) clearInterval(availabilityInterval);
    popup.classList.remove('show');
    popup.removeAttribute('data-check-id');
}

function showAvailabilityPopup(data) {
    var popup = document.getElementById('availabilityPopup');
    if (!popup) return;

    var checkId = String(data.id);
    var currentId = popup.getAttribute('data-check-id');

    // Already showing this same check? Leave it alone — timer keeps running
    if (popup.classList.contains('show') && currentId === checkId) {
        return;
    }

    // Compute remaining time from created_at
    var elapsed = 0;
    if (data.created_at) {
        var createdAt = new Date(data.created_at);
        elapsed = (Date.now() - createdAt.getTime()) / 1000;
    }
    var timeLeft = Math.max(0, Math.ceil(AVAILABILITY_TIMEOUT_SECONDS - elapsed));

    // Already expired on arrival — mark dismissed and hide
    if (timeLeft <= 0) {
        __dismissedCheckIds[checkId] = true;
        hideAvailabilityPopup();
        // Tell the server it's missed
        api.post('/api/availability/miss/', { check_id: checkId }).catch(function () {});
        return;
    }

    // Show it
    popup.setAttribute('data-check-id', checkId);
    popup.classList.add('show');

    var timerEl = document.getElementById('popupTimer');
    function renderTimer() {
        var m = Math.floor(timeLeft / 60);
        var s = timeLeft % 60;
        if (timerEl) {
            timerEl.textContent =
                String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
        }
    }
    renderTimer();

    if (availabilityInterval) clearInterval(availabilityInterval);
    availabilityInterval = setInterval(function () {
        timeLeft--;
        renderTimer();

        if (timeLeft <= 0) {
            clearInterval(availabilityInterval);

            // Mark dismissed so it never shows again
            __dismissedCheckIds[checkId] = true;

            popup.classList.remove('show');
            popup.removeAttribute('data-check-id');
            showToast('warning', 'You missed the availability check.');

            // Tell the server it's missed
            api.post('/api/availability/miss/', { check_id: checkId }).catch(function () {});
        }
    }, 1000);

    var btn = document.getElementById('respondAvailability');
    if (btn) {
        btn.disabled = false;
        btn.textContent = "I'm Here";
        btn.onclick = function () {
            clearInterval(availabilityInterval);

            // Mark dismissed immediately so a stale poll won't re-show it
            __dismissedCheckIds[checkId] = true;

            respondAvailability(checkId);
            popup.classList.remove('show');
            popup.removeAttribute('data-check-id');
        };
    }
}

function respondAvailability(checkId) {
    api.post('/api/availability/respond/', {})
        .then(function () {
            showToast('success', 'Availability confirmed.');
        })
        .catch(function (err) {
            var msg = (err && err.message) || 'Failed to respond.';
            if (/expired/i.test(msg)) msg = 'The check expired before you responded.';
            else if (/no pending/i.test(msg)) msg = 'No pending check for you right now.';
            else if (/auth|session/i.test(msg)) msg = 'Your session expired. Please log in again.';
            showToast('error', msg);
        });
}

// ============================================================
// SIDEBAR TASK COUNT (interns)
// ============================================================
function updateSidebarTaskCount() {
    if (!isUserAuthenticated() || getUserRole() !== 'intern') return;
    var badge = document.getElementById('sidebarTaskCount');
    if (!badge) return;

    api.get('/api/tasks/my-tasks/')
        .then(function (data) {
            var tasks = data.results || data || [];
            badge.textContent = tasks.length;
        })
        .catch(function () { /* silent */ });
}
window.updateSidebarTaskCount = updateSidebarTaskCount;

// ============================================================
// BOOT
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    if (!isUserAuthenticated()) return;

    loadNotificationCount();
    setInterval(loadNotificationCount, 30000);   // dev: 10s. Use 30000 in prod.

    updateSidebarTaskCount();

    if (getUserRole() === 'intern') {
        setTimeout(checkAvailability, 500);
        setInterval(checkAvailability, 30000);     // dev: 3s. Use 30000 in prod.
    }
});