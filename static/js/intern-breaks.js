/* ============================================================
   intern-breaks.js — session-cookie authentication
   ============================================================ */

function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

var breakTimer = null;

// ---------- Load current break status ----------
function loadBreakStatus() {
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
                document.getElementById('breakStatus').textContent = 'Yes';
                startBreakTimer(data.start_time);
            } else {
                startBtn.style.display = 'inline-block';
                endBtn.style.display = 'none';
                document.getElementById('breakStatus').textContent = 'No';
                if (breakTimer) clearInterval(breakTimer);
            }
        })
        .catch(function () {
            document.getElementById('breakStatus').textContent = 'No';
        });
}

function startBreakTimer(startTime) {
    if (breakTimer) clearInterval(breakTimer);
    var start = new Date(startTime);
    var tick = function () {
        var diff = Math.floor((new Date() - start) / 1000);
        var m = String(Math.floor(diff / 60)).padStart(2, '0');
        var s = String(diff % 60).padStart(2, '0');
        var el = document.getElementById('liveBreakTimer');
        if (el) el.textContent = m + ':' + s;
    };
    tick();
    breakTimer = setInterval(tick, 1000);
}

// ---------- Load break history ----------
function loadHistory() {
    fetch('/api/breaks/history/', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var items = data.results || data || [];
            var tbody = document.getElementById('breakHistoryBody');
            var total = 0;

            var completed = items.filter(function (b) { return b.status === 'completed'; });
            document.getElementById('totalBreaks').textContent = completed.length;

            if (!items.length) {
                tbody.innerHTML =
                    '<tr><td colspan="5" class="empty-state">' +
                    '<i class="fas fa-mug-hot"></i>' +
                    '<p class="mb-0">No break history yet</p></td></tr>';
                return;
            }

            var html = '';
            items.forEach(function (b) {
                if (b.status === 'completed' && b.duration) {
                    var parts = b.duration.split(':');
                    total += parseInt(parts[0], 10) * 3600
                          + parseInt(parts[1], 10) * 60
                          + parseInt(parts[2] || 0, 10);
                }
                var badge = b.status === 'active' ? 'bg-warning'
                          : b.status === 'completed' ? 'bg-success'
                          : 'bg-secondary';
                html +=
                    '<tr>' +
                    '<td><span class="badge bg-secondary">' + (b.break_type_display || b.break_type) + '</span></td>' +
                    '<td>' + new Date(b.start_time).toLocaleTimeString() + '</td>' +
                    '<td>' + (b.end_time ? new Date(b.end_time).toLocaleTimeString() : '—') + '</td>' +
                    '<td>' + ((b.duration || '--:--').substring(0, 8)) + '</td>' +
                    '<td><span class="badge ' + badge + '">' + b.status + '</span></td>' +
                    '</tr>';
            });
            tbody.innerHTML = html;

            var h = String(Math.floor(total / 3600)).padStart(2, '0');
            var m = String(Math.floor((total % 3600) / 60)).padStart(2, '0');
            document.getElementById('totalBreakTime').textContent = h + ':' + m;
        })
        .catch(function () { /* silent */ });
}

// ---------- Start break (from modal) ----------
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
            loadBreakStatus();
            loadHistory();
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
            if (breakTimer) clearInterval(breakTimer);
            loadBreakStatus();
            loadHistory();
        })
        .catch(function () { showToast('error', 'Failed to end break.'); });
});

// ---------- Init ----------
loadBreakStatus();
loadHistory();