/* ============================================================
   lead-dashboard.js — read-only team snapshot
   ============================================================ */

function loadAll() {
    fetch('/api/reports/current-status/', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            document.getElementById('totalInterns').textContent = data.total_interns || 0;
            document.getElementById('onlineInterns').textContent = data.online_interns || 0;
            document.getElementById('onBreakInterns').textContent = data.on_break_interns || 0;
            document.getElementById('offlineInterns').textContent = data.offline_interns || 0;
            document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();

            var interns = data.interns || [];
            var tbody = document.getElementById('internsBody');

            if (!interns.length) {
                tbody.innerHTML =
                    '<tr><td colspan="6" class="empty-state">' +
                    '<i class="fas fa-users"></i><p class="mb-0">No interns found</p></td></tr>';
                return;
            }

            var html = '';
            interns.forEach(function (i) {
                var statusClass = 'offline', statusText = 'Offline';
                if (i.status === 'active') { statusClass = 'online'; statusText = 'Online'; }
                else if (i.status === 'on_break') { statusClass = 'on_break'; statusText = 'On Break'; }

                html +=
                    '<tr>' +
                    '<td><span class="badge bg-secondary">' + i.username + '</span></td>' +
                    '<td>' + i.name + '</td>' +
                    '<td><span class="status-indicator ' + statusClass + '"></span> ' + statusText + '</td>' +
                    '<td>' + (i.duration || '00:00:00') + '</td>' +
                    '<td>' + (i.break_duration || '00:00:00') + '</td>' +
                    '<td><span class="badge bg-info">' + (i.login_count || 1) + '</span></td>' +
                    '</tr>';
            });
            tbody.innerHTML = html;
        })
        .catch(function () {
            document.getElementById('internsBody').innerHTML =
                '<tr><td colspan="6" class="text-center text-danger py-4">Failed to load</td></tr>';
        });
}

loadAll();
setInterval(loadAll, 30000);