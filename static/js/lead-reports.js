/* ============================================================
   lead-reports.js — session-cookie authentication
   ============================================================ */

// Set default date to today
document.getElementById('reportDate').valueAsDate = new Date();

function loadReport() {
    var date = document.getElementById('reportDate').value;
    if (!date) {
        showToast('error', 'Please select a date.');
        return;
    }

    fetch('/api/reports/daily/?date=' + date, {
        credentials: 'same-origin',
    })
        .then(function (r) {
            if (!r.ok) throw new Error('Failed to load report');
            return r.json();
        })
        .then(function (d) {
            var html = '';

            // ---------- Stat cards ----------
            html += '<div class="row g-3 mb-4">';
            html +=
                '<div class="col-md-3">' +
                '<div class="stat-card primary">' +
                '<div class="stat-label">Total Interns</div>' +
                '<div class="stat-number">' + (d.attendance.total_interns || 0) + '</div>' +
                '</div></div>';
            html +=
                '<div class="col-md-3">' +
                '<div class="stat-card success">' +
                '<div class="stat-label">Completed Sessions</div>' +
                '<div class="stat-number">' + (d.attendance.completed_sessions || 0) + '</div>' +
                '</div></div>';
            html +=
                '<div class="col-md-3">' +
                '<div class="stat-card warning">' +
                '<div class="stat-label">Tasks Assigned</div>' +
                '<div class="stat-number">' + (d.tasks.assigned || 0) + '</div>' +
                '</div></div>';
            html +=
                '<div class="col-md-3">' +
                '<div class="stat-card info">' +
                '<div class="stat-label">Tasks Completed</div>' +
                '<div class="stat-number">' + (d.tasks.completed || 0) + '</div>' +
                '</div></div>';
            html += '</div>';

            // ---------- Summary cards ----------
            html += '<div class="row g-3">';
            html +=
                '<div class="col-md-6">' +
                '<div class="card"><div class="card-header"><h6 class="mb-0">Attendance Summary</h6></div>' +
                '<div class="card-body">' +
                '<div class="d-flex justify-content-between mb-2"><span>Total Duration</span><strong>' + d.attendance.total_duration + '</strong></div>' +
                '<div class="d-flex justify-content-between mb-2"><span>Total Break Time</span><strong>' + d.attendance.total_break_time + '</strong></div>' +
                '<div class="d-flex justify-content-between"><span>Total Working Time</span><strong class="text-success">' + d.attendance.total_working_time + '</strong></div>' +
                '</div></div></div>';
            html +=
                '<div class="col-md-6">' +
                '<div class="card"><div class="card-header"><h6 class="mb-0">Availability Summary</h6></div>' +
                '<div class="card-body">' +
                '<div class="d-flex justify-content-between mb-2"><span>Total Checks</span><strong>' + (d.availability.total_checks || 0) + '</strong></div>' +
                '<div class="d-flex justify-content-between mb-2"><span>Responded</span><strong class="text-success">' + (d.availability.responded || 0) + '</strong></div>' +
                '<div class="d-flex justify-content-between"><span>Missed</span><strong class="text-danger">' + (d.availability.missed || 0) + '</strong></div>' +
                '</div></div></div>';
            html += '</div>';

            // ---------- Per-intern breakdown ----------
            var breakdown = d.intern_breakdown || [];
            html +=
                '<div class="card mt-3">' +
                '<div class="card-header"><h6 class="mb-0">Per-Intern Breakdown</h6></div>' +
                '<div class="card-body p-0"><div class="table-responsive">' +
                '<table class="table mb-0">' +
                '<thead><tr>' +
                '<th>Intern</th>' +
                '<th>Login</th>' +
                '<th>Logout</th>' +
                '<th>Duration</th>' +
                '<th>Break</th>' +
                '<th>Working</th>' +
                '<th>Logins</th>' +
                '<th>Tasks</th>' +
                '<th>Status</th>' +
                '</tr></thead><tbody id="breakdownBody">';

            if (!breakdown.length) {
                html += '<tr><td colspan="9" class="text-center text-muted py-4">No sessions for this date</td></tr>';
            } else {
                breakdown.forEach(function (row) {
                    var badge = row.status === 'active' ? 'bg-success'
                              : row.status === 'completed' ? 'bg-secondary'
                              : 'bg-danger';
                    html +=
                        '<tr>' +
                        '<td><strong>' + row.username + '</strong><br><small class="text-muted">' + row.full_name + '</small></td>' +
                        '<td>' + row.login_time + '</td>' +
                        '<td>' + row.logout_time + '</td>' +
                        '<td>' + row.duration + '</td>' +
                        '<td>' + row.break_time + '</td>' +
                        '<td>' + row.working_time + '</td>' +
                        '<td><span class="badge bg-info">' + row.login_count + '</span></td>' +
                        '<td>' + row.tasks_completed + ' / ' + row.tasks_assigned + '</td>' +
                        '<td><span class="badge ' + badge + '">' + row.status + '</span></td>' +
                        '</tr>';
                });
            }
            html += '</tbody></table></div></div></div>';

            document.getElementById('reportContent').innerHTML = html;
        })
        .catch(function (err) {
            console.error(err);
            showToast('error', 'Failed to load report.');
        });
}

// Auto-load today's report
loadReport();