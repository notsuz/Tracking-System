/* ============================================================
   intern-dashboard.js — session-cookie authentication
   Day totals across multiple sessions; timers stop on logout
   ============================================================ */

function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

var durationInterval = null;
var breakInterval = null;
var __forceLoggedOutHandled = false;

// ---------- Greeting ----------
(function () {
    var h = new Date().getHours();
    var el = document.getElementById('greeting');
    if (el) el.textContent = h < 12 ? 'Morning' : h < 17 ? 'Afternoon' : 'Evening';
})();

function fmtHMS(sec) {
    sec = Math.max(0, Math.floor(sec));
    var h = String(Math.floor(sec / 3600)).padStart(2, '0');
    var m = String(Math.floor((sec % 3600) / 60)).padStart(2, '0');
    var s = String(sec % 60).padStart(2, '0');
    return h + ':' + m + ':' + s;
}

function fmtMS(sec) {
    sec = Math.max(0, Math.floor(sec));
    var m = String(Math.floor(sec / 60)).padStart(2, '0');
    var s = String(sec % 60).padStart(2, '0');
    return m + ':' + s;
}

function parseHMS(str) {
    if (!str) return 0;
    var parts = String(str).split(':').map(Number);
    return (parts[0] || 0) * 3600 + (parts[1] || 0) * 60 + (parts[2] || 0);
}

// Kill every running timer. Called at the start of loadAttendance()
// so no interval can ever leak between polls.
function stopAllTimers() {
    if (durationInterval) { clearInterval(durationInterval); durationInterval = null; }
    if (breakInterval) { clearInterval(breakInterval); breakInterval = null; }
}

// ---------- Force logout handler ----------
function handleForceLogout() {
    if (__forceLoggedOutHandled) return;
    __forceLoggedOutHandled = true;

    stopAllTimers();

    try {
        sessionStorage.setItem(
            'logout_reason',
            'You were logged out by your Team Lead. Please log in again.'
        );
    } catch (e) { /* ignore */ }

    // Show overlay, then redirect to /logout/
    showForceLogoutOverlay();

    setTimeout(function () {
        window.location.href = '/logout/';
    }, 2000);
}

// ---------- Force logout overlay ----------
function showForceLogoutOverlay() {
    var existing = document.getElementById('forceLogoutOverlay');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.id = 'forceLogoutOverlay';
    overlay.innerHTML =
        '<div style="' +
            'position:fixed;inset:0;background:rgba(15,20,35,0.85);' +
            'backdrop-filter:blur(4px);z-index:10000;' +
            'display:flex;align-items:center;justify-content:center;padding:20px;' +
        '">' +
            '<div style="' +
                'background:#fff;border-radius:16px;padding:40px;' +
                'max-width:420px;width:100%;text-align:center;' +
                'box-shadow:0 25px 60px rgba(0,0,0,0.3);' +
            '">' +
                '<div style="' +
                    'width:80px;height:80px;background:#f8d7da;color:#721c24;' +
                    'border-radius:50%;display:inline-flex;align-items:center;' +
                    'justify-content:center;font-size:2rem;margin-bottom:20px;' +
                '">' +
                    '<i class="fas fa-power-off"></i>' +
                '</div>' +
                '<h3 style="font-size:1.3rem;font-weight:700;margin-bottom:8px;color:#2c3e50;">' +
                    'You were logged out' +
                '</h3>' +
                '<p style="color:#7f8c8d;margin-bottom:20px;">' +
                    'Your Team Lead ended your session. Please log in again.' +
                '</p>' +
                '<div style="' +
                    'width:40px;height:40px;margin:0 auto;' +
                    'border:4px solid #e3e6f0;border-top-color:#4e73df;' +
                    'border-radius:50%;animation:spin 0.8s linear infinite;' +
                '"></div>' +
                '<style>@keyframes spin { to { transform: rotate(360deg); } }</style>' +
            '</div>' +
        '</div>';
    document.body.appendChild(overlay);
}

// ---------- Attendance ----------
function loadAttendance() {
    // Always kill any running timers first — prevents duplicated intervals
    stopAllTimers();

    fetch('/api/attendance/current/', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!data.session) {
                handleForceLogout();
                return;
            }

            var s = data.session;

            // Force-logged-out → kick to login
            if (s.status === 'force_logged_out') {
                handleForceLogout();
                return;
            }

            var dayDuration = data.day_total_duration || '00:00:00';
            var dayBreak = data.day_total_break || '00:00:00';
            var completedToday = data.completed_today_duration || '0:00:00';
            var sessionCount = data.session_count || 1;

            // ---- Stat cards ----
            document.getElementById('statDuration').textContent = dayDuration.substring(0, 5);
            document.getElementById('statBreak').textContent = dayBreak.substring(0, 5);
            document.getElementById('statLogins').textContent = s.login_count || 1;

            // ---- Meta line ----
            var countLabel = sessionCount + ' session' + (sessionCount > 1 ? 's' : '') + ' today';
            document.getElementById('loginCountMeta').textContent = countLabel;
            document.getElementById('loginTimeMeta').textContent =
                new Date(s.login_time).toLocaleTimeString();
            document.getElementById('breakTimeMeta').textContent = dayBreak;

            // ---- Active: run timers ----
            if (s.status === 'active') {
                document.getElementById('statusText').textContent = 'Active Session';
                document.getElementById('sessionCard').classList.remove('completed');
                document.getElementById('endDutyBtn').disabled = false;
                document.getElementById('startBreakBtn').disabled = false;
                document.getElementById('startBreakBtn').style.display = 'inline-block';
                document.getElementById('endBreakBtn').style.display = 'none';
                startDurationCounter(s.login_time, completedToday);
                checkBreakStatus();
                return;
            }

            // ---- Completed: freeze, no timers ----
            if (s.status === 'completed') {
                document.getElementById('statusText').textContent = 'Session Completed';
                document.getElementById('sessionCard').classList.add('completed');
                document.getElementById('sessionTimer').textContent =
                    dayDuration.substring(0, 8);
                document.getElementById('startBreakBtn').disabled = true;
                document.getElementById('endDutyBtn').disabled = true;
                document.getElementById('startBreakBtn').style.display = 'inline-block';
                document.getElementById('endBreakBtn').style.display = 'none';
            }
        })
        .catch(function (err) { console.error('Attendance load failed:', err); });
}

function startDurationCounter(loginTime, completedTodayDuration) {
    if (durationInterval) { clearInterval(durationInterval); durationInterval = null; }

    var offsetSecs = parseHMS(completedTodayDuration);
    var start = new Date(loginTime);

    var tick = function () {
        var liveDiff = Math.floor((new Date() - start) / 1000);
        var total = liveDiff + offsetSecs;
        document.getElementById('sessionTimer').textContent = fmtHMS(total);
    };
    tick();
    durationInterval = setInterval(tick, 1000);
}

// ---------- Break ----------
function checkBreakStatus() {
    fetch('/api/breaks/current/', { credentials: 'same-origin' })
        .then(function (r) {
            if (r.status === 404) return null;
            return r.json();
        })
        .then(function (data) {
            var startBtn = document.getElementById('startBreakBtn');
            var endBtn = document.getElementById('endBreakBtn');

            if (data && data.status === 'active') {
                startBtn.style.display = 'none';
                endBtn.style.display = 'inline-block';
                startBreakCounter(data.start_time, data.break_type_display || 'Break');
            } else {
                startBtn.style.display = 'inline-block';
                endBtn.style.display = 'none';
                if (breakInterval) { clearInterval(breakInterval); breakInterval = null; }
            }
        })
        .catch(function () {
            document.getElementById('startBreakBtn').style.display = 'inline-block';
            document.getElementById('endBreakBtn').style.display = 'none';
        });
}

function startBreakCounter(startTime, typeName) {
    if (breakInterval) { clearInterval(breakInterval); breakInterval = null; }
    var start = new Date(startTime);
    var tick = function () {
        var diff = Math.floor((new Date() - start) / 1000);
        document.getElementById('breakTimeMeta').textContent = fmtHMS(diff);
        var endBtn = document.getElementById('endBreakBtn');
        if (endBtn) {
            endBtn.innerHTML = '<i class="fas fa-check"></i> End ' + typeName + ' (' + fmtMS(diff) + ')';
        }
    };
    tick();
    breakInterval = setInterval(tick, 1000);
}

// ---------- Start break from modal ----------
document.querySelectorAll('.break-type-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
        var type = this.getAttribute('data-type');
        var notes = document.getElementById('breakNotes').value.trim();
        startBreak(type, notes);
    });
});

function startBreak(breakType, notes) {
    fetch('/api/breaks/start/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ break_type: breakType, notes: notes }),
    })
        .then(function (r) {
            return r.json().then(function (b) { return { ok: r.ok, body: b }; });
        })
        .then(function (res) {
            if (!res.ok) {
                var msg = (res.body && (res.body.error
                    || (res.body.break_type && res.body.break_type[0])
                    || (res.body.non_field_errors && res.body.non_field_errors[0])))
                    || 'Failed to start break';
                showToast('error', msg);
                return;
            }
            showToast('success', res.body.message || 'Break started.');
            var modalEl = document.getElementById('breakTypeModal');
            var modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            document.getElementById('breakNotes').value = '';
            checkBreakStatus();
        })
        .catch(function () { showToast('error', 'Network error.'); });
}

// ---------- End break ----------
document.getElementById('endBreakBtn').addEventListener('click', function () {
    fetch('/api/breaks/end/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
    })
        .then(function (r) { return r.json(); })
        .then(function () {
            showToast('success', 'Break ended.');
            if (breakInterval) { clearInterval(breakInterval); breakInterval = null; }
            checkBreakStatus();
            loadAttendance();
        })
        .catch(function () { showToast('error', 'Failed to end break.'); });
});

// ---------- End duty (self logout) ----------
document.getElementById('endDutyBtn').addEventListener('click', function () {
    var summary = prompt('Please enter a brief summary of what you did today (min 10 characters):');
    if (summary === null) return;
    if (summary.trim().length < 10) {
        showToast('error', 'Summary must be at least 10 characters.');
        return;
    }

    // Freeze the timer immediately — no more counting
    stopAllTimers();

    fetch('/api/attendance/end/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ daily_summary: summary.trim() }),
    })
        .then(function (r) { return r.json(); })
        .then(function () {
            showToast('success', 'Duty ended. Have a great day.');
            loadAttendance();   // shows the frozen final state
        })
        .catch(function () {
            showToast('error', 'Failed to end duty.');
            loadAttendance();   // resume display if request failed
        });
});

// ---------- Tasks ----------
function loadTasks() {
    fetch('/api/tasks/my-tasks/', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var tasks = data.results || data || [];
            document.getElementById('statTasks').textContent = tasks.length;

            var tbody = document.getElementById('tasksBody');
            if (!tasks.length) {
                tbody.innerHTML =
                    '<tr><td colspan="5" class="empty-state">' +
                    '<i class="fas fa-clipboard-check"></i>' +
                    '<p class="mb-0">No tasks assigned yet</p></td></tr>';
                return;
            }
            var html = '';
            tasks.slice(0, 5).forEach(function (t) {
                html +=
                    '<tr>' +
                    '<td><strong>' + t.title + '</strong></td>' +
                    '<td><span class="priority-badge ' + t.priority + '">' + t.priority + '</span></td>' +
                    '<td><span class="task-status ' + t.status + '">' + t.status.replace('_', ' ') + '</span></td>' +
                    '<td>' + (t.deadline ? new Date(t.deadline).toLocaleDateString() : '—') + '</td>' +
                    '<td class="text-end">' +
                    (t.status !== 'completed'
                        ? '<button class="btn btn-sm btn-outline-success" data-id="' + t.id + '" data-action="done"><i class="fas fa-check"></i></button>'
                        : '<span class="text-success"><i class="fas fa-check-circle"></i></span>') +
                    '</td></tr>';
            });
            tbody.innerHTML = html;

            tbody.querySelectorAll('button[data-action="done"]').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    updateTask(this.getAttribute('data-id'), 'completed');
                });
            });
        })
        .catch(function (err) { console.error('Tasks load failed:', err); });
}

function updateTask(id, status) {
    fetch('/api/tasks/' + id + '/status/', {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ status: status }),
    })
        .then(function (r) { return r.json(); })
        .then(function () {
            showToast('success', 'Task updated.');
            loadTasks();
            if (typeof updateSidebarTaskCount === 'function') updateSidebarTaskCount();
        })
        .catch(function () { showToast('error', 'Failed to update task.'); });
}

// ---------- Init ----------
document.addEventListener('DOMContentLoaded', function () {
    loadAttendance();
    loadTasks();
    setInterval(loadAttendance, 30000);
});