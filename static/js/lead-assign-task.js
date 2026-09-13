// ---------- CSRF helper ----------
function getCookie(name) {
    const value = '; ' + document.cookie;
    const parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}

const preselectedIntern = new URLSearchParams(window.location.search).get('intern');

// ---------- Load interns for dropdown ----------
function loadInterns() {
    fetch('/api/reports/current-status/', {
        credentials: 'same-origin',
    })
        .then(r => r.json())
        .then(data => {
            document.getElementById('totalInterns').textContent = data.total_interns || 0;
            document.getElementById('onlineInterns').textContent = data.online_interns || 0;
            document.getElementById('breakInterns').textContent = data.on_break_interns || 0;
            document.getElementById('offlineInterns').textContent = data.offline_interns || 0;

            const interns = data.interns || [];
            let opts = '<option value="">Select an intern by username...</option>';
            interns.forEach(i => {
                const isSelected = String(preselectedIntern) === String(i.id);
                const username = i.username || i.email || i.name || 'unknown';
                const fullName = i.name && i.name !== username ? ` — ${i.name}` : '';
                opts += `<option value="${i.id}" ${isSelected ? 'selected' : ''}>${username}${fullName}</option>`;
            });

            document.getElementById('assignedTo').innerHTML = opts;
        })
        .catch(err => {
            document.getElementById('assignedTo').innerHTML =
                '<option value="">Failed to load interns</option>';
            console.error(err);
        });
}

// ---------- Submit task ----------
document.getElementById('taskForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const btn = document.getElementById('submitBtn');
    const original = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Assigning...';
    btn.disabled = true;
    document.getElementById('messageContainer').innerHTML = '';

    const payload = {
        assigned_to: document.getElementById('assignedTo').value,
        title: document.getElementById('title').value.trim(),
        description: document.getElementById('description').value.trim(),
        priority: document.getElementById('priority').value,
        deadline: document.getElementById('deadline').value || null,
    };

    if (!payload.assigned_to) {
        showToast('error', 'Please select an intern.');
        btn.innerHTML = original;
        btn.disabled = false;
        return;
    }

    fetch('/api/tasks/create/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
    })
        .then(r => r.json().then(body => ({ ok: r.ok, body })))
        .then(({ ok, body }) => {
            if (!ok) {
                let msg = '';
                if (typeof body === 'object') {
                    msg = Object.entries(body)
                        .map(([k, v]) => `<strong>${k}:</strong> ${Array.isArray(v) ? v.join(', ') : v}`)
                        .join('<br>');
                } else {
                    msg = body;
                }
                throw new Error(msg);
            }

            document.getElementById('messageContainer').innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i>
                    Task assigned successfully!
                </div>`;
            document.getElementById('taskForm').reset();
            window.history.replaceState({}, '', '/lead/assign-task/');
        })
        .catch(err => {
            document.getElementById('messageContainer').innerHTML = `
                <div class="alert alert-danger">${err.message}</div>`;
        })
        .finally(() => {
            btn.innerHTML = original;
            btn.disabled = false;
        });
});

// ---------- Init ----------
loadInterns();