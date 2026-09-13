/* ============================================================
   lead-attendance.js — daily attendance summary
   ============================================================ */

// Set default date to today
document.getElementById('dateFilter').valueAsDate = new Date();

function loadSummary() {
    var date = document.getElementById('dateFilter').value;
    var statusFilter = document.getElementById('statusFilter').value;

    var url = '/api/attendance/daily-summary/';
    if (date) url += '?date=' + date;

    fetch(url, { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var rows = data.rows || [];
            if (statusFilter) {
                rows = rows.filter(function (r) { return r.status === statusFilter; });
            }

            document.getElementById('rowCount').textContent =
                rows.length + ' row' + (rows.length === 1 ? '' : 's');

            var tbody = document.getElementById('summaryBody');
            if (!rows.length) {
                tbody.innerHTML =
                    '<tr><td colspan="8" class="empty-state">' +
                    '<i class="fas fa-calendar"></i>' +
                    '<p class="mb-0">No records for this date</p></td></tr>';
                return;
            }

            var html = '';
            rows.forEach(function (r) {
                var badgeClass = 'bg-secondary';
                var label = r.status;

                if (r.status === 'active') {
                    badgeClass = 'bg-success';
                    label = 'Active';
                } else if (r.status === 'completed') {
                    badgeClass = 'bg-primary';
                    label = 'Completed';
                } else if (r.status === 'force_logged_out') {
                    badgeClass = 'bg-danger';
                    label = 'Force Logged Out';
                } else if (r.status === 'no_activity') {
                    badgeClass = 'bg-light text-muted';
                    label = 'No Activity';
                }

                var loginCell = r.login || '—';
                var logoutCell = r.logout || '—';
                var durationCell = r.total_duration || '00:00:00';
                var breakCell = r.total_break || '00:00:00';
                var loginsCell = r.total_logins || 0;

                html +=
                    '<tr>' +
                    '<td>' +
                    '<strong>' + (r.full_name || r.username) + '</strong><br>' +
                    '<small class="text-muted">' + r.username + '</small>' +
                    '</td>' +
                    '<td>' + r.date + '</td>' +
                    '<td>' + loginCell + '</td>' +
                    '<td>' + logoutCell + '</td>' +
                    '<td><strong>' + durationCell + '</strong></td>' +
                    '<td>' + breakCell + '</td>' +
                    '<td><span class="badge bg-info">' + loginsCell + '</span></td>' +
                    '<td><span class="badge ' + badgeClass + '">' + label + '</span></td>' +
                    '</tr>';
            });
            tbody.innerHTML = html;
        })
        .catch(function (err) {
            console.error('Failed to load summary:', err);
            document.getElementById('summaryBody').innerHTML =
                '<tr><td colspan="8" class="text-center text-danger py-4">' +
                'Failed to load summary</td></tr>';
        });
}

// Auto-load on open
loadSummary();

// Reload when filters change
document.getElementById('dateFilter').addEventListener('change', loadSummary);
document.getElementById('statusFilter').addEventListener('change', loadSummary);