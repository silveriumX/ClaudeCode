import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert';
import { TaskStore } from '../src/db/store.js';

describe('TaskStore', () => {
  let store;

  beforeEach(() => {
    store = new TaskStore();
  });

  describe('initialization', () => {
    it('should initialize with seed data', () => {
      const tasks = store.getAll();
      assert.ok(Array.isArray(tasks), 'getAll() should return an array');
      assert.ok(tasks.length > 0, 'Store should have seed data on init');
    });
  });

  describe('getAll()', () => {
    it('should return an array of tasks', () => {
      const tasks = store.getAll();
      assert.ok(Array.isArray(tasks), 'Result should be an array');
      for (const task of tasks) {
        assert.ok(task.id, 'Each task should have an id');
        assert.ok(task.title, 'Each task should have a title');
        assert.ok(task.status, 'Each task should have a status');
        assert.ok(task.priority, 'Each task should have a priority');
      }
    });

    it('should filter by status when {status: "todo"} is passed', () => {
      const todoTasks = store.getAll({ status: 'todo' });
      assert.ok(Array.isArray(todoTasks), 'Filtered result should be an array');
      for (const task of todoTasks) {
        assert.strictEqual(task.status, 'todo', `Expected status "todo" but got "${task.status}"`);
      }
    });

    it('should filter by priority when {priority: "high"} is passed', () => {
      // Add a known high-priority task to ensure at least one exists
      store.create({ title: 'Urgent fix', priority: 'high' });
      const highTasks = store.getAll({ priority: 'high' });
      assert.ok(Array.isArray(highTasks), 'Filtered result should be an array');
      assert.ok(highTasks.length > 0, 'Should have at least one high-priority task');
      for (const task of highTasks) {
        assert.strictEqual(task.priority, 'high', `Expected priority "high" but got "${task.priority}"`);
      }
    });
  });

  describe('getById()', () => {
    it('should return the correct task for a valid id', () => {
      const allTasks = store.getAll();
      const firstTask = allTasks[0];
      const found = store.getById(firstTask.id);
      assert.ok(found, 'getById should return a task');
      assert.strictEqual(found.id, firstTask.id, 'Returned task id should match');
      assert.strictEqual(found.title, firstTask.title, 'Returned task title should match');
    });

    it('should return null for a non-existent id', () => {
      const result = store.getById('non-existent-id-xyz-99999');
      assert.strictEqual(result, null, 'getById should return null for unknown id');
    });
  });

  describe('create()', () => {
    it('should add a new task with a generated id and createdAt', () => {
      const beforeCount = store.getAll().length;
      const newTask = store.create({
        title: 'Write unit tests',
        description: 'Cover all edge cases',
        priority: 'medium',
      });

      assert.ok(newTask, 'create() should return the new task');
      assert.ok(newTask.id, 'New task should have a generated id');
      assert.ok(newTask.createdAt, 'New task should have a createdAt timestamp');
      assert.strictEqual(newTask.title, 'Write unit tests', 'Title should match input');
      assert.strictEqual(newTask.description, 'Cover all edge cases', 'Description should match input');
      assert.strictEqual(newTask.priority, 'medium', 'Priority should match input');

      const afterCount = store.getAll().length;
      assert.strictEqual(afterCount, beforeCount + 1, 'Task count should increase by 1');
    });

    it('should set default status to "todo" when not specified', () => {
      const newTask = store.create({
        title: 'Default status test',
        priority: 'low',
      });

      assert.strictEqual(newTask.status, 'todo', 'Default status should be "todo"');
    });
  });

  describe('update()', () => {
    it('should modify task fields and return the updated task', () => {
      const allTasks = store.getAll();
      const target = allTasks[0];

      const updated = store.update(target.id, {
        title: 'Updated title',
        status: 'in-progress',
      });

      assert.ok(updated, 'update() should return the updated task');
      assert.strictEqual(updated.id, target.id, 'Task id should remain the same');
      assert.strictEqual(updated.title, 'Updated title', 'Title should be updated');
      assert.strictEqual(updated.status, 'in-progress', 'Status should be updated');

      // Verify the change persists in the store
      const fetched = store.getById(target.id);
      assert.strictEqual(fetched.title, 'Updated title', 'Updated title should persist');
    });

    it('should return null for a non-existent id', () => {
      const result = store.update('non-existent-id-xyz-99999', { title: 'Nope' });
      assert.strictEqual(result, null, 'update() should return null for unknown id');
    });
  });

  describe('delete()', () => {
    it('should remove the task and return true', () => {
      const allTasks = store.getAll();
      const target = allTasks[0];
      const beforeCount = allTasks.length;

      const result = store.delete(target.id);
      assert.strictEqual(result, true, 'delete() should return true on success');

      const afterCount = store.getAll().length;
      assert.strictEqual(afterCount, beforeCount - 1, 'Task count should decrease by 1');

      const found = store.getById(target.id);
      assert.strictEqual(found, null, 'Deleted task should no longer be found');
    });

    it('should return false for a non-existent id', () => {
      const result = store.delete('non-existent-id-xyz-99999');
      assert.strictEqual(result, false, 'delete() should return false for unknown id');
    });
  });

  describe('getStats()', () => {
    it('should return correct counts for each status', () => {
      // Reset store by creating a fresh instance
      const freshStore = new TaskStore();

      // Create tasks with known statuses
      freshStore.create({ title: 'Todo 1', priority: 'low' });
      freshStore.create({ title: 'Todo 2', priority: 'medium' });

      const inProgressTask = freshStore.create({ title: 'WIP', priority: 'high' });
      freshStore.update(inProgressTask.id, { status: 'in-progress' });

      const doneTask = freshStore.create({ title: 'Finished', priority: 'low' });
      freshStore.update(doneTask.id, { status: 'done' });

      const stats = freshStore.getStats();

      assert.ok(stats, 'getStats() should return an object');
      assert.ok(typeof stats.todo === 'number', 'stats.todo should be a number');
      assert.ok(typeof stats['in-progress'] === 'number', 'stats["in-progress"] should be a number');
      assert.ok(typeof stats.done === 'number', 'stats.done should be a number');
      assert.ok(typeof stats.total === 'number', 'stats.total should be a number');

      // Verify total is the sum of all statuses
      const sum = stats.todo + stats['in-progress'] + stats.done;
      assert.strictEqual(stats.total, sum, 'Total should equal sum of all status counts');

      // Verify counts are non-negative
      assert.ok(stats.todo >= 0, 'Todo count should be non-negative');
      assert.ok(stats['in-progress'] >= 0, 'In-progress count should be non-negative');
      assert.ok(stats.done >= 0, 'Done count should be non-negative');
      assert.ok(stats.total > 0, 'Total should be greater than 0');
    });
  });
});
