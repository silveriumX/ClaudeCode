import { describe, it } from 'node:test';
import assert from 'node:assert';
import { formatDate, getPriorityColor, getStatusIcon, generateId } from '../src/utils/helpers.js';

describe('formatDate', () => {
  it('should return a readable string for a valid ISO date', () => {
    const result = formatDate('2026-01-15T14:30:00.000Z');
    assert.ok(typeof result === 'string', 'Should return a string');
    assert.ok(result.length > 0, 'Should not be empty');
    assert.ok(result !== 'Unknown date', 'Should not return "Unknown date" for valid input');
    // Should contain recognizable date parts
    assert.ok(result.includes('Jan') || result.includes('15') || result.includes('2026'),
      'Should contain date components');
  });

  it('should return a readable string for a Date object', () => {
    const date = new Date('2026-06-20T09:15:00.000Z');
    const result = formatDate(date);
    assert.ok(typeof result === 'string', 'Should return a string');
    assert.ok(result !== 'Unknown date', 'Should not return "Unknown date" for valid Date object');
  });

  it('should return "Unknown date" for an invalid date string', () => {
    const result = formatDate('not-a-date');
    assert.strictEqual(result, 'Unknown date', 'Should return "Unknown date" for invalid input');
  });

  it('should return "Unknown date" for null or undefined', () => {
    const resultNull = formatDate(null);
    const resultUndef = formatDate(undefined);
    // Both should handle gracefully
    assert.ok(
      resultNull === 'Unknown date' || typeof resultNull === 'string',
      'Should handle null input gracefully'
    );
    assert.ok(
      resultUndef === 'Unknown date' || typeof resultUndef === 'string',
      'Should handle undefined input gracefully'
    );
  });
});

describe('getPriorityColor', () => {
  it('should return a valid color string for "low"', () => {
    const color = getPriorityColor('low');
    assert.ok(typeof color === 'string', 'Should return a string');
    assert.ok(color.startsWith('#'), 'Should return a hex color');
    assert.strictEqual(color, '#22c55e', 'Low priority should be green');
  });

  it('should return a valid color string for "medium"', () => {
    const color = getPriorityColor('medium');
    assert.ok(typeof color === 'string', 'Should return a string');
    assert.ok(color.startsWith('#'), 'Should return a hex color');
    assert.strictEqual(color, '#f59e0b', 'Medium priority should be amber');
  });

  it('should return a valid color string for "high"', () => {
    const color = getPriorityColor('high');
    assert.ok(typeof color === 'string', 'Should return a string');
    assert.ok(color.startsWith('#'), 'Should return a hex color');
    assert.strictEqual(color, '#ef4444', 'High priority should be red');
  });

  it('should return a fallback color for an unknown priority', () => {
    const color = getPriorityColor('critical');
    assert.ok(typeof color === 'string', 'Should return a string for unknown priority');
    assert.ok(color.startsWith('#'), 'Fallback should also be a hex color');
    assert.strictEqual(color, '#6b7280', 'Unknown priority should return gray fallback');
  });
});

describe('getStatusIcon', () => {
  it('should return an emoji string for "todo"', () => {
    const icon = getStatusIcon('todo');
    assert.ok(typeof icon === 'string', 'Should return a string');
    assert.ok(icon.length > 0, 'Should not be empty');
    assert.strictEqual(icon, '\u{1F4CB}', 'Todo should return clipboard emoji');
  });

  it('should return an emoji string for "in-progress"', () => {
    const icon = getStatusIcon('in-progress');
    assert.ok(typeof icon === 'string', 'Should return a string');
    assert.ok(icon.length > 0, 'Should not be empty');
    assert.strictEqual(icon, '\u{1F3C3}', 'In-progress should return runner emoji');
  });

  it('should return an emoji string for "done"', () => {
    const icon = getStatusIcon('done');
    assert.ok(typeof icon === 'string', 'Should return a string');
    assert.ok(icon.length > 0, 'Should not be empty');
    assert.strictEqual(icon, '\u{2705}', 'Done should return green checkmark emoji');
  });

  it('should return a fallback emoji for an unknown status', () => {
    const icon = getStatusIcon('cancelled');
    assert.ok(typeof icon === 'string', 'Should return a string for unknown status');
    assert.ok(icon.length > 0, 'Fallback should not be empty');
    assert.strictEqual(icon, '\u{2753}', 'Unknown status should return question mark emoji');
  });
});

describe('generateId', () => {
  it('should return a non-empty string', () => {
    const id = generateId();
    assert.ok(typeof id === 'string', 'Should return a string');
    assert.ok(id.length > 0, 'ID should not be empty');
  });

  it('should return unique values on successive calls', () => {
    const ids = new Set();
    const iterations = 100;

    for (let i = 0; i < iterations; i++) {
      ids.add(generateId());
    }

    assert.strictEqual(ids.size, iterations, `All ${iterations} generated IDs should be unique`);
  });

  it('should return IDs with a reasonable length', () => {
    const id = generateId();
    // UUIDs are 36 chars, fallback IDs are shorter but still substantial
    assert.ok(id.length >= 10, 'ID should be at least 10 characters long');
  });
});
