// ============================================================
//  intern-tasks.js — session-cookie authentication
// ============================================================

// ---------- CSRF helper ----------
function getCookie(name) {
    const value = '; ' + document.cookie;
    const parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

// ---------- Task loading ----------
function loadTasks() {
    const params = new URLSearchParams();
    const s = document.getElementById('statusFilter').value;
    const p = document.getElementById('priorityFilter').value;
    if (s) params.append('status', s);
    if (p) params.append('priority', p);

    const url = '/api/tasks/my-tasks/' + (params.toString() ? '?' + params.toString() : '');

    fetch(url, {
        credentials: 'same-origin',
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            const tasks = data.results || data || [];
            const grid = document.getElementById('tasksGrid');

            if (!tasks.length) {
                grid.innerHTML =
                    '<div class="col-12">' +
                    '<div class="card"><div class="card-body empty-state">' +
                    '<i class="fas fa-clipboard-list"></i>' +
                    '<h5>No tasks found</h5>' +
                    '<p class="mb-0">You have no tasks matching your filters.</p>' +
                    '</div></div></div>';
                return;
            }

            let html = '';
            tasks.forEach(function (t) {
                const isDone = t.status === 'completed';
                const isCancelled = t.status === 'cancelled';
                const overdue = t.deadline && new Date(t.deadline) < new Date() && !isDone && !isCancelled;

                html += '<div class="col-md-6 col-lg-4">';
                html += '<div class="card h-100"><div class="card-body d-flex flex-column">';

                html += '<div class="d-flex justify-content-between align-items-start mb-2">';
                html += '<span class="priority-badge ' + t.priority + '">' + t.priority + '</span>';
                html += '<span class="task-status ' + t.status + '">' + t.status.replace('_', ' ') + '</span>';
                html += '</div>';

                html += '<h6 class="fw-bold">' + t.title + '</h6>';
                html += '<p class="text-muted small mb-3 flex-grow-1">' +
                    (t.description || '').substring(0, 90) +
                    (t.description && t.description.length > 90 ? '...' : '') +
                    '</p>';

                html += '<div class="d-flex justify-content-between small text-muted mb-3">';
                html += '<span><i class="fas fa-user"></i> ' + (t.assigned_by_name || 'Lead') + '</span>';
                html += '<span class="' + (overdue ? 'text-danger fw-bold' : '') + '">' +
                    '<i class="fas fa-calendar"></i> ' +
                    (t.deadline ? new Date(t.deadline).toLocaleDateString() : 'No deadline') +
                    '</span>';
                html += '</div>';

                if (!isDone && !isCancelled) {
                    html += '<div class="d-flex gap-2">';
                    if (t.status !== 'in_progress') {
                        html += '<button class="btn btn-sm btn-outline-warning flex-grow-1" ' +
                            'data-action="start" data-id="' + t.id + '">' +
                            '<i class="fas fa-play"></i> Start</button>';
                    }
                    html += '<button class="btn btn-sm btn-outline-success flex-grow-1" ' +
                        'data-action="done" data-id="' + t.id + '">' +
                        '<i class="fas fa-check"></i> Done</button>';
                    html += '</div>';
                } else if (isDone) {
                    html += '<div class="text-center text-success small fw-semibold">' +
                        '<i class="fas fa-check-circle"></i> Completed</div>';
                } else {
                    html += '<div class="text-center text-muted small">' +
                        '<i class="fas fa-ban"></i> Cancelled</div>';
                }

                html += '</div></div></div>';
            });

            grid.innerHTML = html;

            // Attach click listeners programmatically (no inline onclick)
            grid.querySelectorAll('button[data-action]').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    const action = this.getAttribute('data-action');
                    const id = this.getAttribute('data-id');
                    const status = action === 'done' ? 'completed' : 'in_progress';
                    updateTask(id, status);
                });
            });
        })
        .catch(function (err) {
            console.error('loadTasks failed:', err);
        });
}

// ---------- Update a task ----------
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
        .then(function (r) {
            return r.json().then(function (body) {
                return { ok: r.ok, status: r.status, body: body };
            });
        })
        .then(function (res) {
            if (!res.ok) {
                const msg = (res.body && (res.body.detail || res.body.status)) || 'Failed to update';
                if (typeof showToast === 'function') showToast('error', msg);
                else alert(msg);
                return;
            }
            if (typeof showToast === 'function') showToast('success', 'Task updated!');
            loadTasks();
        })
        .catch(function (err) {
            console.error('updateTask failed:', err);
            if (typeof showToast === 'function') showToast('error', 'Network error');
        });
}

// Make it globally accessible (in case inline onclick is still somewhere)
window.updateTask = updateTask;

// ---------- Init ----------
document.getElementById('statusFilter').addEventListener('change', loadTasks);
document.getElementById('priorityFilter').addEventListener('change', loadTasks);
loadTasks();