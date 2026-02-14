/**
 * In-memory task data store with JSON file persistence.
 * All mutations auto-save to disk so data survives restarts.
 */

import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { getSeedTasks } from './seed.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DATA_FILE = path.join(__dirname, 'data.json');

class TaskStore {
  constructor() {
    this.tasks = [];
    this._load();
  }

  /**
   * Load tasks from the JSON file on disk.
   * Falls back to seed data if the file doesn't exist or is corrupt.
   */
  _load() {
    try {
      if (fs.existsSync(DATA_FILE)) {
        const raw = fs.readFileSync(DATA_FILE, 'utf-8');
        const parsed = JSON.parse(raw);

        if (Array.isArray(parsed) && parsed.length > 0) {
          this.tasks = parsed;
          return;
        }
      }
    } catch (err) {
      console.warn(`[TaskStore] Could not read ${DATA_FILE}, seeding fresh data:`, err.message);
    }

    // No valid persisted data found -- seed defaults
    this.tasks = getSeedTasks();
    this.save();
  }

  // ---------------------------------------------------------------------------
  // Queries
  // ---------------------------------------------------------------------------

  /**
   * Return all tasks, optionally filtered by status and/or priority.
   * @param {{ status?: string, priority?: string }} [filters]
   * @returns {Array} Matching tasks (shallow copies).
   */
  getAll(filters = {}) {
    let results = [...this.tasks];

    if (filters.status) {
      results = results.filter((t) => t.status === filters.status);
    }

    if (filters.priority) {
      results = results.filter((t) => t.priority === filters.priority);
    }

    return results;
  }

  /**
   * Return a single task by its id, or null if not found.
   * @param {string} id
   * @returns {object|null}
   */
  getById(id) {
    const task = this.tasks.find((t) => t.id === id);
    return task ? { ...task } : null;
  }

  /**
   * Return aggregate counts grouped by status.
   * @returns {{ total: number, todo: number, inProgress: number, done: number }}
   */
  getStats() {
    return {
      total: this.tasks.length,
      todo: this.tasks.filter((t) => t.status === 'todo').length,
      inProgress: this.tasks.filter((t) => t.status === 'in-progress').length,
      done: this.tasks.filter((t) => t.status === 'done').length,
    };
  }

  // ---------------------------------------------------------------------------
  // Mutations (all auto-save)
  // ---------------------------------------------------------------------------

  /**
   * Create a new task. Auto-generates id, createdAt, and defaults status to 'todo'.
   * @param {{ title: string, description?: string, priority?: string }} taskData
   * @returns {object} The newly created task.
   */
  create(taskData) {
    const task = {
      id: crypto.randomUUID(),
      title: taskData.title,
      description: taskData.description || '',
      status: 'todo',
      priority: taskData.priority || 'medium',
      createdAt: new Date().toISOString(),
    };

    this.tasks.push(task);
    this.save();
    return { ...task };
  }

  /**
   * Update an existing task's fields. Sets updatedAt automatically.
   * @param {string} id
   * @param {object} updates - Fields to merge into the task.
   * @returns {object|null} The updated task, or null if not found.
   */
  update(id, updates) {
    const index = this.tasks.findIndex((t) => t.id === id);

    if (index === -1) {
      return null;
    }

    // Prevent callers from overwriting the id or createdAt
    const { id: _id, createdAt: _createdAt, ...safeUpdates } = updates;

    this.tasks[index] = {
      ...this.tasks[index],
      ...safeUpdates,
      updatedAt: new Date().toISOString(),
    };

    this.save();
    return { ...this.tasks[index] };
  }

  /**
   * Delete a task by id.
   * @param {string} id
   * @returns {boolean} True if the task was found and removed.
   */
  delete(id) {
    const lengthBefore = this.tasks.length;
    this.tasks = this.tasks.filter((t) => t.id !== id);

    if (this.tasks.length < lengthBefore) {
      this.save();
      return true;
    }

    return false;
  }

  // ---------------------------------------------------------------------------
  // Persistence
  // ---------------------------------------------------------------------------

  /**
   * Write the current tasks array to data.json.
   */
  save() {
    try {
      fs.writeFileSync(DATA_FILE, JSON.stringify(this.tasks, null, 2), 'utf-8');
    } catch (err) {
      console.error('[TaskStore] Failed to persist data:', err.message);
    }
  }
}

// Export a singleton so every module shares the same in-memory state
const store = new TaskStore();
export { TaskStore };
export default store;
