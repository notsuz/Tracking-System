/* ============================================================
   intern-tasks.js — session-cookie auth + clickable task cards
   ============================================================ */

function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

// ---------------- Load tasks ----------------
function loadTasks() {
    var params = new URLSearchParams();
    var s = document.getElementById('statusFilter').value;
    var p = document.getElementById('priorityFilter').value;
    if (s) params.append('status', s);
    if (p) params.append('priority', p);

    var url = '/api/tasks/my-tasks/' + (params.toString() ? '?' + params.toString() : '');

    fetch(url, { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            var tasks = data.results || data || [];
            var grid = document.getElementById('tasksGrid');

            if (!tasks.length) {
                grid.innerHTML =
                    '<div class="col-12"><div class="card"><div class="card-body empty-state">' +
                    '<i class="fas fa-clipboard-list"></i>' +
                    '<h5>No tasks found</h5>' +
                    '<p class="mb-0">You have no tasks matching your filters.</p>' +
                    '</div></div></div>';
                return;
            }

            var html = '';
            tasks.forEach(function (t) {
                var isDone = t.status === 'completed';
                var isCancelled = t.status === 'cancelled';
                var overdue = t.deadline && new Date(t.deadline) < new Date() && !isDone && !isCancelled;

                html += '<div class="col-md-6 col-lg-4">';
                html += '<div class="card h-100 task-card" data-task-id="' + t.id + '">';
                html += '<div class="card-body d-flex flex-column">';

                html += '<div class="d-flex justify-content-between align-items-start mb-2">';
                html += '<span class="priority-badge ' + t.priority + '">' + t.priority + '</span>';
                html += '<span class="task-status ' + t.status + '">' + t.status.replace('_', ' ') + '</span>';
                html += '</div>';

                html += '<h6 class="fw-bold mb-2">' + t.title + '</h6>';
                html += '<p class="text-muted small mb-3 flex-grow-1">' +
                    (t.description || '').substring(0, 80) +
                    (t.description && t.description.length > 80 ? '...' : '') +
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

            // Click on card body → open detail modal
            grid.querySelectorAll('.task-card').forEach(function (card) {
                card.addEventListener('click', function (e) {
                    // If they clicked a Start/Done button, let that handle it
                    if (e.target.closest('button[data-action]')) return;
                    var taskId = this.getAttribute('data-task-id');
                    openTaskDetail(taskId);
                });
            });

            // Wire Start / Done buttons on the cards
            grid.querySelectorAll('button[data-action]').forEach(function (btn) {
                btn.addEventListener('click', function (e) {
                    e.stopPropagation();
                    var action = this.getAttribute('data-action');
                    var id = this.getAttribute('data-id');
                    var status = action === 'done' ? 'completed' : 'in_progress';
                    updateTask(id, status);
                });
            });
        })
        .catch(function (err) { console.error('loadTasks failed:', err); });
}

// ---------------- Open detail modal ----------------
function openTaskDetail(taskId) {
    fetch('/api/tasks/' + taskId + '/', { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (t) {
            document.getElementById('detailTitle').textContent = t.title || '—';
            document.getElementById('detailDescription').textContent = t.description || '—';

            var prio = document.getElementById('detailPriority');
            prio.className = 'priority-badge ' + t.priority;
            prio.textContent = t.priority;

            var status = document.getElementById('detailStatus');
            status.className = 'task-status ' + t.status;
            status.textContent = (t.status || '').replace('_', ' ');

            var assignedBy = document.getElementById('detailAssignedBy');
            assignedBy.textContent = (t.assigned_by_name || 'Lead')
                + (t.assigned_by_email ? ' (' + t.assigned_by_email + ')' : '');

            document.getElementById('detailDeadline').textContent =
                t.deadline ? new Date(t.deadline).toLocaleString() : 'No deadline';

            document.getElementById('detailCreated').textContent =
                t.created_at ? new Date(t.created_at).toLocaleString() : '—';

            document.getElementById('detailCompleted').textContent =
                t.completed_at ? new Date(t.completed_at).toLocaleString() : 'Not yet';

            if (t.notes) {
                document.getElementById('detailNotesSection').style.display = 'block';
                document.getElementById('detailNotes').textContent = t.notes;
            } else {
                document.getElementById('detailNotesSection').style.display = 'none';
            }

            // Buttons
            var startBtn = document.getElementById('detailStartBtn');
            var doneBtn = document.getElementById('detailDoneBtn');

            if (t.status === 'completed' || t.status === 'cancelled') {
                startBtn.style.display = 'none';
                doneBtn.style.display = 'none';
            } else {
                startBtn.style.display = (t.status !== 'in_progress') ? 'inline-block' : 'none';
                doneBtn.style.display = 'inline-block';

                startBtn.onclick = function () { updateTask(t.id, 'in_progress'); };
                doneBtn.onclick = function () { updateTask(t.id, 'completed'); };
            }

            var modalEl = document.getElementById('taskDetailModal');
            var modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            modal.show();
        })
        .catch(function (err) { console.error('openTaskDetail failed:', err); });
}

// ---------------- Update task ----------------
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
            return r.json().then(function (b) { return { ok: r.ok, status: r.status, body: b }; });
        })
        .then(function (res) {
            if (!res.ok) {
                var msg = (res.body && (res.body.error || res.body.detail)) || 'Failed to update task';
                showToast('error', msg);
                return;
            }
            showToast('success', 'Task updated.');
            loadTasks();
            if (typeof updateSidebarTaskCount === 'function') updateSidebarTaskCount();

            // Close modal if open
            var modalEl = document.getElementById('taskDetailModal');
            if (modalEl) {
                var modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();
            }
        })
        .catch(function () { showToast('error', 'Network error.'); });
}

// ---------------- Init ----------------
document.getElementById('statusFilter').addEventListener('change', loadTasks);
document.getElementById('priorityFilter').addEventListener('change', loadTasks);
document.getElementById('refreshBtn')?.addEventListener('click', loadTasks);

loadTasks();