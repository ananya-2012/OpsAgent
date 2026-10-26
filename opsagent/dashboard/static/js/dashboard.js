/* OpsAgent Dashboard JavaScript */

const API_BASE = '';
let activeTaskId = null;
let eventSource = null;

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
    loadTasks();
    loadApprovals();
    loadMemory();
    loadPolicy();
    setupEventListeners();
    // Auto-refresh
    setInterval(loadTasks, 5000);
    setInterval(loadApprovals, 3000);
});

function setupEventListeners() {
    document.getElementById('submit-task').addEventListener('click', submitTask);
    document.getElementById('refresh-tasks').addEventListener('click', loadTasks);
    document.getElementById('refresh-approvals').addEventListener('click', loadApprovals);

    document.getElementById('task-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            submitTask();
        }
    });

    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
        });
    });
}

// ---- Tasks ----
async function submitTask() {
    const input = document.getElementById('task-input');
    const desc = input.value.trim();
    if (!desc) return;

    const btn = document.getElementById('submit-task');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Submitting...';

    try {
        const resp = await fetch(`${API_BASE}/api/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description: desc })
        });
        const data = await resp.json();
        if (resp.ok) {
            input.value = '';
            selectTask(data.task_id);
            loadTasks();
        } else {
            alert(`Error: ${data.detail || 'Unknown error'}`);
        }
    } catch (e) {
        alert(`Network error: ${e.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🚀</span> Submit Task';
    }
}

async function loadTasks() {
    try {
        const resp = await fetch(`${API_BASE}/api/tasks`);
        const data = await resp.json();
        renderTasks(data.tasks || []);
    } catch (e) {
        console.error('Failed to load tasks:', e);
    }
}

function renderTasks(tasks) {
    const container = document.getElementById('tasks-list');
    if (tasks.length === 0) {
        container.innerHTML = '<div class="empty-state">No tasks yet. Submit one above!</div>';
        return;
    }

    container.innerHTML = tasks.map(task => `
        <div class="task-item ${task.id === activeTaskId ? 'active' : ''}"
             onclick="selectTask('${task.id}')">
            <div class="task-status ${task.status}"></div>
            <div class="task-info">
                <div class="task-desc">${escapeHtml(task.description)}</div>
                <div class="task-meta">${task.id} · Step ${task.steps_taken || 0} · ${timeAgo(task.created_at)}</div>
            </div>
            <span class="task-badge ${task.status}">${task.status}</span>
        </div>
    `).join('');
}

async function selectTask(taskId) {
    activeTaskId = taskId;
    loadTasks(); // Re-render to highlight active

    // Show trace section
    document.getElementById('trace-section').style.display = 'block';
    document.getElementById('details-section').style.display = 'block';

    // Start SSE stream
    startStream(taskId);

    // Load details
    loadTaskDetails(taskId);
    loadAuditLog(taskId);
    loadMemory();
}

async function loadTaskDetails(taskId) {
    try {
        const resp = await fetch(`${API_BASE}/api/tasks/${taskId}`);
        const task = await resp.json();

        const evidenceEl = document.getElementById('evidence-content');

        let html = `
            <div class="evidence-item">
                <strong>Status:</strong> <span class="task-badge ${task.status}">${task.status}</span>
            </div>
        `;

        if (task.result) {
            html += `<div class="evidence-item"><strong>Result:</strong><br>${escapeHtml(task.result)}</div>`;
        }
        if (task.error) {
            html += `<div class="evidence-item" style="border-color:var(--error)"><strong>Error:</strong><br>${escapeHtml(task.error)}</div>`;
        }

        if (task.evidence && task.evidence.length > 0) {
            html += '<h4 style="margin:12px 0 8px;color:var(--accent-light)">Evidence</h4>';
            task.evidence.forEach((ev, i) => {
                html += `<div class="evidence-item"><pre>${escapeHtml(JSON.stringify(ev, null, 2))}</pre></div>`;
            });
        }

        // Verify button
        if (task.status === 'completed') {
            html += `<button class="btn btn-primary" style="margin-top:12px" onclick="verifyTask('${taskId}')">
                🔍 Verify & Compare
            </button>`;
        }

        html += `<div id="verify-report-${taskId}"></div>`;
        evidenceEl.innerHTML = html;
    } catch (e) {
        console.error('Failed to load task details:', e);
    }
}

async function verifyTask(taskId) {
    const reportEl = document.getElementById(`verify-report-${taskId}`);
    reportEl.innerHTML = '<div class="spinner"></div> Verifying...';

    try {
        const resp = await fetch(`${API_BASE}/api/tasks/${taskId}/verify`);
        const report = await resp.json();

        let html = '<div class="verify-report">';
        html += `<h4>${report.verified ? '✅ Verified' : '❌ Verification Failed'}</h4>`;

        if (report.checks) {
            report.checks.forEach(check => {
                html += `<div class="check-item ${check.passed ? 'check-pass' : 'check-fail'}">
                    ${check.passed ? '✓' : '✗'} ${escapeHtml(check.message)}
                </div>`;
            });
        }

        if (report.discrepancies && report.discrepancies.length > 0) {
            html += '<h4 style="color:var(--error);margin-top:8px">Discrepancies:</h4>';
            report.discrepancies.forEach(d => {
                html += `<div class="check-item check-fail">
                    ${d.field}: bill="${d.bill_value}" vs invoice="${d.invoice_value}"
                </div>`;
            });
        }

        if (report.error) {
            html += `<div class="check-item check-fail">Error: ${escapeHtml(report.error)}</div>`;
        }

        html += '</div>';
        reportEl.innerHTML = html;
    } catch (e) {
        reportEl.innerHTML = `<div class="check-item check-fail">Verification error: ${e.message}</div>`;
    }
}

// ---- SSE Streaming ----
function startStream(taskId) {
    if (eventSource) {
        eventSource.close();
    }

    const traceLog = document.getElementById('trace-log');
    traceLog.innerHTML = '';

    eventSource = new EventSource(`${API_BASE}/api/tasks/${taskId}/stream`);

    const eventTypes = ['status', 'step', 'tool_call', 'reasoning', 'policy_block',
                        'approval_needed', 'approval_response', 'waiting',
                        'completed', 'failed', 'error', 'loop_detected',
                        'verification_failed'];

    eventTypes.forEach(type => {
        eventSource.addEventListener(type, (e) => {
            const data = JSON.parse(e.data);
            addTraceEntry(type, data);

            if (type === 'completed' || type === 'failed') {
                loadTaskDetails(taskId);
                loadTasks();
                loadApprovals();
            }
            if (type === 'approval_needed' || type === 'waiting') {
                loadApprovals();
            }
        });
    });

    eventSource.addEventListener('heartbeat', () => {});
    eventSource.onerror = () => {
        document.getElementById('trace-status').textContent = 'Disconnected';
        document.getElementById('trace-status').className = 'badge';
    };
}

function addTraceEntry(type, data) {
    const traceLog = document.getElementById('trace-log');
    const entry = document.createElement('div');
    entry.className = `trace-entry ${type}`;

    const time = new Date().toLocaleTimeString();
    let content = '';

    switch (type) {
        case 'step':
            content = `Step ${data.step}/${data.max_steps}`;
            break;
        case 'tool_call':
            content = `${data.tool}(${Object.entries(data.args || {}).map(([k,v]) => `${k}="${v}"`).join(', ')})`;
            break;
        case 'reasoning':
            content = data.text || '';
            break;
        case 'policy_block':
            content = `🚫 BLOCKED: ${data.reason}`;
            break;
        case 'approval_needed':
            content = `⏳ Approval needed: ${data.reason}`;
            break;
        case 'completed':
            content = `✅ ${data.summary || data.status || 'Done'}`;
            break;
        case 'failed':
            content = `❌ ${data.message || data.error || 'Failed'}`;
            break;
        case 'error':
            content = `⚠️ ${data.error || data.message}`;
            break;
        default:
            content = JSON.stringify(data);
    }

    entry.innerHTML = `
        <span class="trace-time">${time}</span>
        <span class="trace-type ${type}">${type}</span>
        ${escapeHtml(content)}
    `;
    traceLog.appendChild(entry);
    traceLog.scrollTop = traceLog.scrollHeight;
}

// ---- Approvals ----
async function loadApprovals() {
    try {
        const resp = await fetch(`${API_BASE}/api/approvals`);
        const data = await resp.json();
        renderApprovals(data.approvals || []);
    } catch (e) {
        console.error('Failed to load approvals:', e);
    }
}

function renderApprovals(approvals) {
    const container = document.getElementById('approvals-list');
    if (approvals.length === 0) {
        container.innerHTML = '<div class="empty-state">No pending approvals</div>';
        return;
    }

    container.innerHTML = approvals.map(a => `
        <div class="approval-item">
            <div class="approval-question">${escapeHtml(a.question)}</div>
            ${a.context ? `<div class="approval-context">${escapeHtml(a.context)}</div>` : ''}
            <div class="approval-actions">
                <input type="text" class="approval-input" id="approval-input-${a.id}"
                       placeholder="${a.request_type === 'approval' ? 'approve / deny' : 'Your response...'}">
                <button class="btn btn-success btn-sm" onclick="respondApproval(${a.id}, 'approve')">✓ Approve</button>
                <button class="btn btn-danger btn-sm" onclick="respondApproval(${a.id}, 'deny')">✗ Deny</button>
                <button class="btn btn-ghost btn-sm" onclick="respondApprovalCustom(${a.id})">Send</button>
            </div>
        </div>
    `).join('');
}

async function respondApproval(approvalId, response) {
    try {
        await fetch(`${API_BASE}/api/approvals/${approvalId}/respond`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ response })
        });
        loadApprovals();
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

async function respondApprovalCustom(approvalId) {
    const input = document.getElementById(`approval-input-${approvalId}`);
    const response = input.value.trim();
    if (!response) return;
    await respondApproval(approvalId, response);
}

// ---- Audit Log ----
async function loadAuditLog(taskId) {
    try {
        const resp = await fetch(`${API_BASE}/api/tasks/${taskId}/audit`);
        const data = await resp.json();
        const container = document.getElementById('audit-content');

        if (!data.audit_log || data.audit_log.length === 0) {
            container.innerHTML = '<div class="empty-state">No audit entries yet</div>';
            return;
        }

        container.innerHTML = data.audit_log.map(entry => `
            <div class="audit-entry">
                <span class="audit-time">${formatTime(entry.timestamp)}</span>
                <span class="audit-type">${entry.event_type}</span>
                ${entry.tool_name ? `<strong>${entry.tool_name}</strong>` : ''}
                ${entry.policy_decision ? `<br><small style="color:var(--warning)">${escapeHtml(entry.policy_decision).substring(0, 200)}</small>` : ''}
                ${entry.output_data ? `<br><small style="color:var(--text-muted)">${escapeHtml(String(entry.output_data)).substring(0, 200)}</small>` : ''}
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load audit log:', e);
    }
}

// ---- Memory ----
async function loadMemory() {
    try {
        const resp = await fetch(`${API_BASE}/api/memory`);
        const data = await resp.json();
        const container = document.getElementById('memory-content');

        if (!data.facts || data.facts.length === 0) {
            container.innerHTML = '<div class="empty-state">No persistent facts stored yet</div>';
            return;
        }

        container.innerHTML = data.facts.map(f => `
            <div class="fact-item">
                <span class="fact-key">${escapeHtml(f.key)}</span>
                <span class="fact-value">${escapeHtml(f.value)}</span>
            </div>
        `).join('');
    } catch (e) {
        console.error('Failed to load memory:', e);
    }
}

// ---- Policy ----
async function loadPolicy() {
    try {
        const resp = await fetch(`${API_BASE}/api/policy`);
        const data = await resp.json();
        const container = document.getElementById('policy-content');

        container.innerHTML = `
            <div class="policy-section">
                <h4>🌐 Allowed Domains</h4>
                <p>${(data.allowed_domains || []).join(', ')}</p>
            </div>
            <div class="policy-section">
                <h4>⚡ Risk Levels</h4>
                ${Object.entries(data.risk_levels || {}).map(([level, config]) =>
                    `<p><strong>${level}:</strong> ${config.allowed ? '✅ Allowed' : '❌ Blocked'}
                    ${config.requires_approval ? '(needs approval)' : ''}</p>`
                ).join('')}
            </div>
            <div class="policy-section">
                <h4>💰 Approval Threshold</h4>
                <p>Rs ${(data.approval_threshold || 50000).toLocaleString()}</p>
            </div>
            <div class="policy-section">
                <h4>🛡️ Content Safety</h4>
                <p>${data.injection_patterns_count || 0} injection patterns monitored</p>
            </div>
            <div class="policy-section">
                <h4>🔧 Tools Registered</h4>
                <p>${data.tools_registered || 0} tools available</p>
            </div>
        `;
    } catch (e) {
        console.error('Failed to load policy:', e);
    }
}

// ---- Utilities ----
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

function formatTime(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleTimeString();
}
