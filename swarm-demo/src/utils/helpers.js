/**
 * Utility functions for the Task Manager app.
 */

/**
 * Format an ISO date string into a human-readable format.
 * Example: "Feb 12, 2026 at 3:45 PM"
 * @param {string|Date} date - ISO date string or Date object
 * @returns {string} Formatted date string
 */
export function formatDate(date) {
  try {
    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) {
      return 'Unknown date';
    }
    const options = {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    };
    return d.toLocaleDateString('en-US', options);
  } catch {
    return 'Unknown date';
  }
}

/**
 * Return a CSS color value for a given priority level.
 * @param {'low'|'medium'|'high'} priority
 * @returns {string} CSS color string
 */
export function getPriorityColor(priority) {
  const colors = {
    low: '#22c55e',
    medium: '#f59e0b',
    high: '#ef4444',
  };
  return colors[priority] || '#6b7280';
}

/**
 * Return an emoji icon representing the given task status.
 * @param {'todo'|'in-progress'|'done'} status
 * @returns {string} Emoji string
 */
export function getStatusIcon(status) {
  const icons = {
    'todo': '\u{1F4CB}',        // clipboard
    'in-progress': '\u{1F3C3}', // runner
    'done': '\u{2705}',         // green checkmark
  };
  return icons[status] || '\u{2753}';
}

/**
 * Escape HTML special characters to prevent XSS.
 * @param {string} text - Raw text to escape
 * @returns {string} Escaped HTML string
 */
export function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, (char) => map[char]);
}

/**
 * Generate a unique identifier string.
 * Uses crypto.randomUUID when available, falls back to a timestamp + random combo.
 * @returns {string} Unique ID
 */
export function generateId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // Fallback: timestamp + random hex
  const timestamp = Date.now().toString(36);
  const randomPart = Math.random().toString(36).substring(2, 10);
  const extraRandom = Math.random().toString(36).substring(2, 6);
  return `${timestamp}-${randomPart}-${extraRandom}`;
}
