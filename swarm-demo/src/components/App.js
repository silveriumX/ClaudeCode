import { renderTaskCard } from './TaskCard.js';

/**
 * Render the full HTML page for the Task Manager application.
 *
 * @param {Array<object>} tasks - Array of task objects
 * @returns {string} Complete HTML document string
 */
export function renderApp(tasks = []) {
  const taskCards = tasks.map((task) => renderTaskCard(task)).join('\n');

  // Compute stats
  const total = tasks.length;
  const todoCount = tasks.filter((t) => t.status === 'todo').length;
  const progressCount = tasks.filter((t) => t.status === 'in-progress').length;
  const doneCount = tasks.filter((t) => t.status === 'done').length;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Task Manager</title>
  <style>
    /* ===== CSS Reset & Base ===== */
    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    :root {
      --bg-primary: #0f172a;
      --bg-secondary: #1e293b;
      --bg-card: #1e293b;
      --bg-card-hover: #263348;
      --bg-input: #0f172a;
      --border-color: #334155;
      --border-focus: #6366f1;
      --text-primary: #f1f5f9;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent: #6366f1;
      --accent-hover: #818cf8;
      --accent-glow: rgba(99, 102, 241, 0.3);
      --danger: #ef4444;
      --danger-hover: #f87171;
      --success: #22c55e;
      --warning: #f59e0b;
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 16px;
      --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.3);
      --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
      --shadow-lg: 0 8px 30px rgba(0, 0, 0, 0.5);
      --transition: 200ms ease;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.6;
      min-height: 100vh;
    }

    /* ===== Layout ===== */
    .app {
      max-width: 900px;
      margin: 0 auto;
      padding: 2rem 1.5rem 4rem;
    }

    /* ===== Header ===== */
    .header {
      text-align: center;
      margin-bottom: 2.5rem;
    }

    .header__title {
      font-size: 2.5rem;
      font-weight: 800;
      background: linear-gradient(135deg, #6366f1, #a78bfa, #6366f1);
      background-size: 200% auto;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      animation: gradientShift 4s ease infinite;
      letter-spacing: -0.02em;
    }

    .header__subtitle {
      color: var(--text-secondary);
      font-size: 1rem;
      margin-top: 0.25rem;
    }

    @keyframes gradientShift {
      0%, 100% { background-position: 0% center; }
      50% { background-position: 200% center; }
    }

    /* ===== Stats Bar ===== */
    .stats {
      display: flex;
      gap: 1rem;
      margin-bottom: 2rem;
      flex-wrap: wrap;
    }

    .stats__item {
      flex: 1;
      min-width: 120px;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 1rem 1.25rem;
      text-align: center;
      transition: transform var(--transition), box-shadow var(--transition);
    }

    .stats__item:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }

    .stats__number {
      font-size: 1.75rem;
      font-weight: 700;
      display: block;
    }

    .stats__label {
      font-size: 0.8rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .stats__item--total .stats__number { color: var(--accent); }
    .stats__item--todo .stats__number { color: var(--text-secondary); }
    .stats__item--progress .stats__number { color: var(--warning); }
    .stats__item--done .stats__number { color: var(--success); }

    /* ===== Add Task Form ===== */
    .form-section {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 1.75rem;
      margin-bottom: 2rem;
      box-shadow: var(--shadow-sm);
    }

    .form-section__heading {
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 1.25rem;
      color: var(--text-primary);
    }

    .form {
      display: grid;
      gap: 1rem;
    }

    .form__row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }

    .form__group {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }

    .form__label {
      font-size: 0.8rem;
      font-weight: 500;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .form__input,
    .form__textarea,
    .form__select {
      background: var(--bg-input);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
      padding: 0.7rem 0.85rem;
      color: var(--text-primary);
      font-size: 0.95rem;
      font-family: inherit;
      transition: border-color var(--transition), box-shadow var(--transition);
      outline: none;
    }

    .form__input:focus,
    .form__textarea:focus,
    .form__select:focus {
      border-color: var(--border-focus);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }

    .form__textarea {
      resize: vertical;
      min-height: 80px;
    }

    .form__select {
      cursor: pointer;
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 0.75rem center;
      padding-right: 2.25rem;
    }

    .form__submit {
      justify-self: start;
      background: linear-gradient(135deg, #6366f1, #7c3aed);
      color: #fff;
      border: none;
      border-radius: var(--radius-sm);
      padding: 0.7rem 2rem;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: transform var(--transition), box-shadow var(--transition), opacity var(--transition);
    }

    .form__submit:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
    }

    .form__submit:active {
      transform: translateY(0);
    }

    .form__submit:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
      box-shadow: none;
    }

    /* ===== Filters ===== */
    .filters {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
    }

    .filters__btn {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 99px;
      padding: 0.45rem 1.1rem;
      color: var(--text-secondary);
      font-size: 0.85rem;
      font-weight: 500;
      cursor: pointer;
      transition: all var(--transition);
    }

    .filters__btn:hover {
      color: var(--text-primary);
      border-color: var(--text-muted);
    }

    .filters__btn--active {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }

    .filters__btn--active:hover {
      background: var(--accent-hover);
      border-color: var(--accent-hover);
      color: #fff;
    }

    /* ===== Task List ===== */
    .task-list {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .task-list__empty {
      text-align: center;
      padding: 3rem 1rem;
      color: var(--text-muted);
      font-size: 1.05rem;
    }

    .task-list__empty-icon {
      font-size: 2.5rem;
      display: block;
      margin-bottom: 0.75rem;
    }

    /* ===== Task Card ===== */
    .task-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 1.25rem 1.5rem;
      transition: transform var(--transition), box-shadow var(--transition), border-color var(--transition);
      animation: fadeSlideIn 300ms ease forwards;
    }

    .task-card:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
      border-color: var(--text-muted);
    }

    .task-card--done {
      opacity: 0.65;
    }

    .task-card--done .task-card__title {
      text-decoration: line-through;
      color: var(--text-muted);
    }

    @keyframes fadeSlideIn {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .task-card__header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 0.75rem;
      margin-bottom: 0.5rem;
    }

    .task-card__title {
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--text-primary);
      line-height: 1.3;
    }

    .task-card__delete-btn {
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 0.3rem;
      border-radius: var(--radius-sm);
      transition: color var(--transition), background var(--transition);
      flex-shrink: 0;
    }

    .task-card__delete-btn:hover {
      color: var(--danger);
      background: rgba(239, 68, 68, 0.1);
    }

    .task-card__description {
      color: var(--text-secondary);
      font-size: 0.9rem;
      margin-bottom: 0.75rem;
      line-height: 1.5;
    }

    .task-card__meta {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 0.85rem;
      flex-wrap: wrap;
    }

    .task-card__badge {
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      padding: 0.2rem 0.65rem;
      border-radius: 99px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }

    .task-card__badge--priority {
      background: color-mix(in srgb, var(--priority-color) 15%, transparent);
      color: var(--priority-color);
      border: 1px solid color-mix(in srgb, var(--priority-color) 30%, transparent);
    }

    .task-card__badge--status[data-status="todo"] {
      background: rgba(148, 163, 184, 0.12);
      color: #94a3b8;
      border: 1px solid rgba(148, 163, 184, 0.25);
    }

    .task-card__badge--status[data-status="in-progress"] {
      background: rgba(245, 158, 11, 0.12);
      color: #f59e0b;
      border: 1px solid rgba(245, 158, 11, 0.25);
    }

    .task-card__badge--status[data-status="done"] {
      background: rgba(34, 197, 94, 0.12);
      color: #22c55e;
      border: 1px solid rgba(34, 197, 94, 0.25);
    }

    .task-card__footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .task-card__date {
      font-size: 0.78rem;
      color: var(--text-muted);
    }

    .task-card__actions {
      display: flex;
      gap: 0.4rem;
    }

    .task-card__action-btn {
      border: none;
      border-radius: var(--radius-sm);
      padding: 0.35rem 0.85rem;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all var(--transition);
    }

    .task-card__action-btn--progress {
      background: rgba(245, 158, 11, 0.15);
      color: #f59e0b;
    }
    .task-card__action-btn--progress:hover {
      background: rgba(245, 158, 11, 0.3);
    }

    .task-card__action-btn--done {
      background: rgba(34, 197, 94, 0.15);
      color: #22c55e;
    }
    .task-card__action-btn--done:hover {
      background: rgba(34, 197, 94, 0.3);
    }

    .task-card__action-btn--todo {
      background: rgba(148, 163, 184, 0.15);
      color: #94a3b8;
    }
    .task-card__action-btn--todo:hover {
      background: rgba(148, 163, 184, 0.3);
    }

    .task-card__action-btn--reopen {
      background: rgba(99, 102, 241, 0.15);
      color: #818cf8;
    }
    .task-card__action-btn--reopen:hover {
      background: rgba(99, 102, 241, 0.3);
    }

    /* ===== Toast Notification ===== */
    .toast {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      padding: 0.85rem 1.25rem;
      color: var(--text-primary);
      font-size: 0.9rem;
      box-shadow: var(--shadow-lg);
      opacity: 0;
      transform: translateY(20px);
      transition: opacity 300ms ease, transform 300ms ease;
      z-index: 1000;
      pointer-events: none;
    }

    .toast--visible {
      opacity: 1;
      transform: translateY(0);
    }

    .toast--error {
      border-color: var(--danger);
    }

    /* ===== Responsive ===== */
    @media (max-width: 640px) {
      .app {
        padding: 1.25rem 1rem 3rem;
      }

      .header__title {
        font-size: 1.75rem;
      }

      .stats {
        gap: 0.5rem;
      }

      .stats__item {
        min-width: 70px;
        padding: 0.75rem 0.5rem;
      }

      .stats__number {
        font-size: 1.35rem;
      }

      .form__row {
        grid-template-columns: 1fr;
      }

      .task-card__footer {
        flex-direction: column;
        align-items: flex-start;
      }
    }
  </style>
</head>
<body>
  <div class="app">

    <!-- Header -->
    <header class="header">
      <h1 class="header__title">Task Manager</h1>
      <p class="header__subtitle">Stay organized, get things done.</p>
    </header>

    <!-- Stats -->
    <section class="stats" id="stats">
      <div class="stats__item stats__item--total">
        <span class="stats__number" id="stat-total">${total}</span>
        <span class="stats__label">Total</span>
      </div>
      <div class="stats__item stats__item--todo">
        <span class="stats__number" id="stat-todo">${todoCount}</span>
        <span class="stats__label">To Do</span>
      </div>
      <div class="stats__item stats__item--progress">
        <span class="stats__number" id="stat-progress">${progressCount}</span>
        <span class="stats__label">In Progress</span>
      </div>
      <div class="stats__item stats__item--done">
        <span class="stats__number" id="stat-done">${doneCount}</span>
        <span class="stats__label">Done</span>
      </div>
    </section>

    <!-- Add Task Form -->
    <section class="form-section">
      <h2 class="form-section__heading">Add New Task</h2>
      <form class="form" id="task-form" onsubmit="handleAddTask(event)">
        <div class="form__group">
          <label class="form__label" for="task-title">Title</label>
          <input
            class="form__input"
            type="text"
            id="task-title"
            name="title"
            placeholder="What needs to be done?"
            required
            maxlength="120"
          />
        </div>
        <div class="form__row">
          <div class="form__group">
            <label class="form__label" for="task-description">Description</label>
            <textarea
              class="form__textarea"
              id="task-description"
              name="description"
              placeholder="Add some details (optional)"
              maxlength="500"
            ></textarea>
          </div>
          <div class="form__group">
            <label class="form__label" for="task-priority">Priority</label>
            <select class="form__select" id="task-priority" name="priority">
              <option value="low">Low</option>
              <option value="medium" selected>Medium</option>
              <option value="high">High</option>
            </select>
          </div>
        </div>
        <button class="form__submit" type="submit" id="submit-btn">
          Add Task
        </button>
      </form>
    </section>

    <!-- Filters -->
    <section class="filters" id="filters">
      <button class="filters__btn filters__btn--active" data-filter="all" onclick="setFilter('all')">
        All (${total})
      </button>
      <button class="filters__btn" data-filter="todo" onclick="setFilter('todo')">
        To Do (${todoCount})
      </button>
      <button class="filters__btn" data-filter="in-progress" onclick="setFilter('in-progress')">
        In Progress (${progressCount})
      </button>
      <button class="filters__btn" data-filter="done" onclick="setFilter('done')">
        Done (${doneCount})
      </button>
    </section>

    <!-- Task List -->
    <section class="task-list" id="task-list">
      ${taskCards.length > 0 ? taskCards : `
        <div class="task-list__empty">
          <span class="task-list__empty-icon">\u{1F4ED}</span>
          No tasks yet. Add one above to get started!
        </div>
      `}
    </section>

    <!-- Toast -->
    <div class="toast" id="toast"></div>
  </div>

  <script>
    // ===== Client-Side JavaScript =====

    let currentFilter = 'all';

    /**
     * Show a toast notification.
     */
    function showToast(message, isError = false) {
      const toast = document.getElementById('toast');
      toast.textContent = message;
      toast.className = 'toast toast--visible' + (isError ? ' toast--error' : '');
      clearTimeout(toast._timeout);
      toast._timeout = setTimeout(() => {
        toast.className = 'toast';
      }, 3000);
    }

    /**
     * Reload the page to re-render with fresh data from the server.
     */
    function reloadPage() {
      window.location.reload();
    }

    /**
     * Handle the add-task form submission.
     */
    async function handleAddTask(event) {
      event.preventDefault();
      const form = event.target;
      const submitBtn = document.getElementById('submit-btn');

      const title = form.title.value.trim();
      const description = form.description.value.trim();
      const priority = form.priority.value;

      if (!title) {
        showToast('Please enter a task title.', true);
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Adding...';

      try {
        const res = await fetch('/api/tasks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, description, priority }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error || 'Failed to add task');
        }

        showToast('Task added successfully!');
        form.reset();
        // Short delay so the toast is visible before reload
        setTimeout(reloadPage, 400);
      } catch (err) {
        showToast(err.message, true);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Add Task';
      }
    }

    /**
     * Update a task's status via the API.
     */
    async function updateTaskStatus(taskId, newStatus) {
      try {
        const res = await fetch('/api/tasks/' + taskId, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus }),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error || 'Failed to update task');
        }

        showToast('Task updated!');
        setTimeout(reloadPage, 300);
      } catch (err) {
        showToast(err.message, true);
      }
    }

    /**
     * Delete a task via the API.
     */
    async function deleteTask(taskId) {
      if (!confirm('Are you sure you want to delete this task?')) return;

      try {
        const res = await fetch('/api/tasks/' + taskId, {
          method: 'DELETE',
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.error || 'Failed to delete task');
        }

        // Animate card removal
        const card = document.querySelector('[data-id="' + taskId + '"]');
        if (card) {
          card.style.transition = 'opacity 300ms ease, transform 300ms ease';
          card.style.opacity = '0';
          card.style.transform = 'translateX(30px)';
        }

        showToast('Task deleted.');
        setTimeout(reloadPage, 500);
      } catch (err) {
        showToast(err.message, true);
      }
    }

    /**
     * Set the active filter and show/hide task cards accordingly.
     */
    function setFilter(filter) {
      currentFilter = filter;

      // Update button states
      document.querySelectorAll('.filters__btn').forEach((btn) => {
        btn.classList.toggle('filters__btn--active', btn.dataset.filter === filter);
      });

      // Show/hide cards
      document.querySelectorAll('.task-card').forEach((card) => {
        const matches = filter === 'all' || card.dataset.status === filter;
        card.style.display = matches ? '' : 'none';
      });

      // Show empty state if no visible cards
      const visibleCards = document.querySelectorAll('.task-card[style=""], .task-card:not([style*="display: none"])');
      const taskList = document.getElementById('task-list');
      const existingEmpty = taskList.querySelector('.task-list__empty');

      if (visibleCards.length === 0 && !existingEmpty) {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'task-list__empty';
        emptyDiv.innerHTML = '<span class="task-list__empty-icon">\u{1F50D}</span>No tasks match this filter.';
        taskList.appendChild(emptyDiv);
      } else if (visibleCards.length > 0 && existingEmpty) {
        existingEmpty.remove();
      }
    }
  </script>
</body>
</html>`;
}
