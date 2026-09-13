const token = localStorage.getItem('access_token');

function loadTasks() {
    const params = new URLSearchParams();
    const s = document.getElementById('statusFilter').value;
    const p = document.getElementById('priorityFilter').value;
    if (s) params.append('status', s);
    if (p) params.append('priority', p);

    fetch('/api/tasks/?' + params.toString(), {
        headers: { 'Authorization': 'Bearer ' + token },
    })
        .then(r => r.json())
        .then(data => {
            const items = data.results || data || [];
            const tbody = document.getElementById('tasksBody');

            if (!items.length) {
                tbody.innerHTML =
                    '<tr><td colspan="6" class="empty-state"><i class="fas fa-clipboard-list"></i><p class="mb-0">No tasks found</p></td></tr>';
                return;
            }

            let html = '';
            items.forEach(t => {
                const overdue = t.is_overdue
                    ? ' <span class="badge bg-danger">Overdue</span>'
                    : '';
                html += `
                    <tr>
                        <td><strong>${t.title}</strong></td>
                        <td>
                            <span class="badge bg-secondary">${t.assigned_to_name || '—'}</span>
                        </td>
                        <td><span class="priority-badge ${t.priority}">${t.priority}</span></td>
                        <td><span class="task-status ${t.status}">${t.status.replace('_', ' ')}</span></td>
                        <td>
                            ${t.deadline ? new Date(t.deadline).toLocaleDateString() : '—'}
                            ${overdue}
                        </td>
                        <td>${new Date(t.created_at).toLocaleDateString()}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        })
        .catch(err => {
            document.getElementById('tasksBody').innerHTML =
                '<tr><td colspan="6" class="text-center text-danger py-4">Failed to load tasks</td></tr>';
            console.error(err);
        });
}

document.getElementById('statusFilter').addEventListener('change', loadTasks);
document.getElementById('priorityFilter').addEventListener('change', loadTasks);

loadTasks();