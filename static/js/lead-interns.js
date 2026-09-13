/* ============================================================
   lead-interns.js — availability checks + force logout
   Uses window.api from base.js
   ============================================================ */

var allInterns = [];

// ---------- Helpers ----------
function safeStr(v, fallback) {
    return (v === null || v === undefined) ? (fallback || '') : String(v);
}

function safeTime(v) {
    if (!v) return '--:--';
    var s = String(v);
    return s.length > 8 ? s.substring(0, 8) : s;
}

// ---------- Load ----------
function loadInterns() {
    api.get('/api/reports/current-status/')
        .then(function (data) {
            allInterns = (data && data.interns) || [];
            renderInterns();
        })
        .catch(function (err) {
            console.error('loadInterns failed:', err);
            var tbody = document.getElementById('internsBody');
            if (tbody) {
                tbody.innerHTML =
                    '<tr><td colspan="10" class="text-center text-danger py-4">' +
                    'Failed to load interns</td></tr>';
            }
        });
}

function renderInterns() {
    var searchEl = document.getElementById('searchInput');
    var statusEl = document.getElementById('statusFilter');
    var onlyEl = document.getElementById('onlyOnline');

    var search = searchEl ? searchEl.value.trim().toLowerCase() : '';
    var statusFilter = statusEl ? statusEl.value : '';
    var onlyOnline = onlyEl ? onlyEl.checked : false;

    var filtered = allInterns.filter(function (i) {
        if (search) {
            var hay = (safeStr(i.username) + ' ' + safeStr(i.email) + ' ' + safeStr(i.name)).toLowerCase();
            if (hay.indexOf(search) === -1) return false;
        }
        if (statusFilter && i.status !== statusFilter) return false;
        if (onlyOnline && i.status === 'offline') return false;
        return true;
    });

    var tbody = document.getElementById('internsBody');
    if (!tbody) return;

    if (!filtered.length) {
        tbody.innerHTML =
            '<tr><td colspan="10" class="empty-state">' +
            '<i class="fas fa-users"></i><p class="mb-0">No interns match your filters</p></td></tr>';
        return;
    }

    var html = '';
    filtered.forEach(function (i) {
        try {
            var statusClass = 'offline', statusText = 'Offline';
            if (i.status === 'active') { statusClass = 'online'; statusText = 'Online'; }
            else if (i.status === 'on_break') { statusClass = 'on_break'; statusText = 'On Break'; }

            // ---------- Last Check cell ----------
            var checkCell = '<span class="text-muted">—</span>';
            var lcs = i.last_check_status;
            if (i.pending_check || lcs === 'pending') {
                checkCell = '<span class="badge bg-warning text-dark">Pending</span>';
            } else if (lcs === 'responded') {
                checkCell = '<span class="badge bg-success">Responded</span>';
            } else if (lcs === 'missed') {
                checkCell = '<span class="badge bg-danger">Missed</span>';
            }

            var isOnline = i.status === 'active' || i.status === 'on_break';
            var username = safeStr(i.username, '—');
            var name = safeStr(i.name, username);
            var email = safeStr(i.email, '—');
            var duration = safeTime(i.duration);
            var breakDuration = safeTime(i.break_duration);
            var loginCount = i.login_count || 1;

            html +=
                '<tr>' +
                '<td><input type="checkbox" class="intern-checkbox" data-id="' + i.id + '" ' +
                (isOnline ? '' : 'disabled') + '></td>' +
                '<td><span class="badge bg-secondary">' + username + '</span></td>' +
                '<td>' + name + '</td>' +
                '<td>' + email + '</td>' +
                '<td><span class="status-indicator ' + statusClass + '"></span> ' + statusText + '</td>' +
                '<td>' + duration + '</td>' +
                '<td>' + breakDuration + '</td>' +
                '<td><span class="badge bg-info">' + loginCount + '</span></td>' +
                '<td>' + checkCell + '</td>' +
                '<td class="text-end">' +
                '<button class="btn btn-sm btn-outline-primary me-1" ' +
                'data-action="check" data-id="' + i.id + '" data-username="' + username + '" ' +
                (isOnline ? '' : 'disabled title="Intern is offline"') + '>' +
                '<i class="fas fa-question-circle"></i> Check</button>' +
                '<button class="btn btn-sm btn-outline-danger me-1" ' +
                'data-action="logout" data-id="' + i.id + '" data-username="' + username + '" ' +
                (isOnline ? '' : 'disabled title="Intern is offline"') + '>' +
                '<i class="fas fa-power-off"></i></button>' +
                '<a href="/lead/assign-task/?intern=' + i.id + '" ' +
                'class="btn btn-sm btn-outline-success" title="Assign Task">' +
                '<i class="fas fa-tasks"></i></a>' +
                '</td>' +
                '</tr>';
        } catch (err) {
            console.error('Row render error for intern', i && i.id, err);
        }
    });
    tbody.innerHTML = html;

    // Attach click handlers
    tbody.querySelectorAll('button[data-action="check"]').forEach(function (b) {
        b.addEventListener('click', function () {
            var id = parseInt(this.getAttribute('data-id'), 10);
            var uname = this.getAttribute('data-username');
            sendCheck([id], uname);
        });
    });
    tbody.querySelectorAll('button[data-action="logout"]').forEach(function (b) {
        b.addEventListener('click', function () {
            var id = parseInt(this.getAttribute('data-id'), 10);
            var uname = this.getAttribute('data-username');
            forceLogout(id, uname);
        });
    });

    var selectAll = document.getElementById('selectAllInterns');
    if (selectAll) selectAll.checked = false;
}

// ---------- Send availability check ----------
function sendCheck(userIds, username) {
    if (!userIds || !userIds.length) {
        showToast('warning', 'No interns selected.');
        return;
    }

    api.post('/api/availability/send/', { user_ids: userIds })
        .then(function (data) {
            var createdCount = (data && data.created_count) || 0;
            var errCount = (data && data.error_count) || 0;

            if (createdCount > 0) {
                showToast('success',
                    'Sent to ' + createdCount + ' intern' + (createdCount > 1 ? 's' : '') + '.');
            }
            if (errCount > 0) {
                (data.errors || []).forEach(function (e) {
                    showToast('warning', (e.username || ('User ' + e.user_id)) + ': ' + e.error);
                });
            }
            if (createdCount === 0 && errCount === 0) {
                showToast('error', 'Failed to send check.');
            }

            // Refresh immediately so the row shows "Pending"
            loadInterns();
        })
        .catch(function (err) {
            showToast('error', (err && err.message) || 'Network error while sending check.');
        });
}

// ---------- Force logout ----------
function forceLogout(id, username) {
    var label = username || 'this intern';
    if (!confirm('Force logout ' + label + '? This ends their session for today.')) return;

    api.post('/api/attendance/force-logout/' + id + '/', {
        reason: 'Force logged out by Team Lead',
    })
        .then(function () {
            showToast('success', (username || 'Intern') + ' has been logged out.');
            loadInterns();
        })
        .catch(function (err) {
            showToast('error', (err && err.message) || 'Failed to force logout.');
        });
}

// ---------- Bulk check ----------
var bulkBtn = document.getElementById('bulkCheckBtn');
if (bulkBtn) {
    bulkBtn.addEventListener('click', function () {
        var ids = [];
        document.querySelectorAll('.intern-checkbox:checked').forEach(function (cb) {
            var id = parseInt(cb.getAttribute('data-id'), 10);
            if (!isNaN(id)) ids.push(id);
        });
        if (!ids.length) {
            showToast('warning', 'Please select at least one intern.');
            return;
        }
        sendCheck(ids, null);
    });
}

// ---------- Select-all ----------
var selectAllEl = document.getElementById('selectAllInterns');
if (selectAllEl) {
    selectAllEl.addEventListener('change', function () {
        var checked = this.checked;
        document.querySelectorAll('.intern-checkbox:not(:disabled)').forEach(function (cb) {
            cb.checked = checked;
        });
    });
}

// ---------- Filters ----------
var searchEl = document.getElementById('searchInput');
var statusEl = document.getElementById('statusFilter');
var onlyEl = document.getElementById('onlyOnline');
if (searchEl) searchEl.addEventListener('input', renderInterns);
if (statusEl) statusEl.addEventListener('change', renderInterns);
if (onlyEl) onlyEl.addEventListener('change', renderInterns);

// ---------- Live refresh ----------
document.addEventListener('notifications:new', function () {
    loadInterns();
});
document.addEventListener('visibilitychange', function () {
    if (!document.hidden) loadInterns();
});

// ---------- Init ----------
loadInterns();
setInterval(loadInterns, 30000);   // dev: 3s. Use 30000 in production.