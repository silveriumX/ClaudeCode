import { formatDate, getPriorityColor, getStatusIcon } from '../utils/helpers.js';

/**
 * Render an HTML string for a single task card.
 *
 * @param {object} task
 * @param {string} task.id
 * @param {string} task.title
 * @param {string} task.description
 * @param {'low'|'medium'|'high'} task.priority
 * @param {'todo'|'in-progress'|'done'} task.status
 * @param {string} task.createdAt - ISO date string
 * @returns {string} HTML string
 */
export function renderTaskCard(task) {
  const priorityColor = getPriorityColor(task.priority);
  const statusIcon = getStatusIcon(task.status);
  const created = formatDate(task.createdAt);

  // Determine which status transitions are available
  const statusTransitions = buildStatusButtons(task);

  // Escape HTML entities in user-provided text
  const safeTitle = escapeHtml(task.title);
  const safeDescription = escapeHtml(task.description || '');

  const priorityLabel = task.priority.charAt(0).toUpperCase() + task.priority.slice(1);
  const statusLabel = formatStatusLabel(task.status);

  const doneClass = task.status === 'done' ? ' task-card--done' : '';

  return `
    <div class="task-card${doneClass}" data-id="${task.id}" data-status="${task.status}" data-priority="${task.priority}">
      <div class="task-card__header">
        <h3 class="task-card__title">${safeTitle}</h3>
        <button class="task-card__delete-btn" onclick="deleteTask('${task.id}')" title="Delete task">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"></path>
            <path d="M10 11v6"></path>
            <path d="M14 11v6"></path>
            <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"></path>
          </svg>
        </button>
      </div>

      ${safeDescription ? `<p class="task-card__description">${safeDescription}</p>` : ''}

      <div class="task-card__meta">
        <span class="task-card__badge task-card__badge--priority" style="--priority-color: ${priorityColor}">
          ${priorityLabel}
        </span>
        <span class="task-card__badge task-card__badge--status" data-status="${task.status}">
          ${statusIcon} ${statusLabel}
        </span>
      </div>

      <div class="task-card__footer">
        <span class="task-card__date">Created ${created}</span>
        <div class="task-card__actions">
          ${statusTransitions}
        </div>
      </div>
    </div>
  `;
}

/**
 * Build the status transition buttons HTML based on current status.
 */
function buildStatusButtons(task) {
  const buttons = [];

  if (task.status === 'todo') {
    buttons.push(
      `<button class="task-card__action-btn task-card__action-btn--progress" onclick="updateTaskStatus('${task.id}', 'in-progress')" title="Start working">
        Start
      </button>`
    );
  }

  if (task.status === 'in-progress') {
    buttons.push(
      `<button class="task-card__action-btn task-card__action-btn--todo" onclick="updateTaskStatus('${task.id}', 'todo')" title="Move back to Todo">
        Back
      </button>`
    );
    buttons.push(
      `<button class="task-card__action-btn task-card__action-btn--done" onclick="updateTaskStatus('${task.id}', 'done')" title="Mark as done">
        Done
      </button>`
    );
  }

  if (task.status === 'done') {
    buttons.push(
      `<button class="task-card__action-btn task-card__action-btn--reopen" onclick="updateTaskStatus('${task.id}', 'todo')" title="Reopen task">
        Reopen
      </button>`
    );
  }

  return buttons.join('\n');
}

/**
 * Format a status string into a display label.
 */
function formatStatusLabel(status) {
  const labels = {
    'todo': 'To Do',
    'in-progress': 'In Progress',
    'done': 'Done',
  };
  return labels[status] || status;
}

/**
 * Escape HTML special characters to prevent XSS.
 */
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return String(text).replace(/[&<>"']/g, (char) => map[char]);
}
