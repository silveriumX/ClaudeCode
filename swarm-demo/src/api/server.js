/**
 * Task Manager — HTTP API Server
 *
 * A lightweight REST server built on Node.js's built-in `http` module.
 * No external dependencies required.
 *
 * Routes:
 *   GET    /              -> Serve the main HTML page
 *   GET    /api/tasks     -> List tasks (supports ?status= and ?priority= filters)
 *   GET    /api/tasks/:id -> Get a single task by ID
 *   POST   /api/tasks     -> Create a new task
 *   PUT    /api/tasks/:id -> Update an existing task
 *   DELETE /api/tasks/:id -> Delete a task
 */

import http from 'node:http';
import { Router } from './router.js';
import { TaskStore } from '../db/store.js';

// -- Initialise core objects ---------------------------------------------------

const router = new Router();
const store = new TaskStore();
const PORT = process.env.PORT || 3000;

// -- Middleware-style helpers ---------------------------------------------------

/**
 * Read the full request body and parse it as JSON.
 * Attaches the result to `req.body`.  If the body is empty or
 * invalid JSON the promise resolves with an empty object.
 *
 * @param {import('http').IncomingMessage} req
 * @returns {Promise<object>}
 */
function parseJsonBody(req) {
  return new Promise((resolve) => {
    const chunks = [];
    req.on('data', (chunk) => chunks.push(chunk));
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf-8');
      if (!raw || raw.trim().length === 0) {
        req.body = {};
        return resolve(req.body);
      }
      try {
        req.body = JSON.parse(raw);
      } catch {
        req.body = {};
      }
      resolve(req.body);
    });
    req.on('error', () => {
      req.body = {};
      resolve(req.body);
    });
  });
}

/**
 * Set common CORS headers so the API can be consumed from any origin.
 * @param {import('http').ServerResponse} res
 */
function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

/**
 * Send a JSON response.
 * @param {import('http').ServerResponse} res
 * @param {number} statusCode
 * @param {*} data
 */
function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

/**
 * Send an HTML response.
 * @param {import('http').ServerResponse} res
 * @param {number} statusCode
 * @param {string} html
 */
function sendHtml(res, statusCode, html) {
  res.writeHead(statusCode, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(html);
}

/**
 * Log every incoming request to stdout in a concise format.
 * @param {import('http').IncomingMessage} req
 */
function logRequest(req) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${req.method} ${req.url}`);
}

// -- Route handlers ------------------------------------------------------------

// GET / -- Serve the main HTML page
router.get('/', (_req, res) => {
  // Dynamically import the App renderer (provided by the frontend agent).
  // If it isn't available yet we send a basic fallback page.
  import('../components/App.js')
    .then((mod) => {
      const renderApp = mod.renderApp || mod.default;
      if (typeof renderApp === 'function') {
        const html = renderApp();
        sendHtml(res, 200, html);
      } else {
        sendHtml(res, 200, getFallbackHtml());
      }
    })
    .catch(() => {
      sendHtml(res, 200, getFallbackHtml());
    });
});

/**
 * Return a minimal fallback HTML page when the frontend component
 * is not yet available.
 */
function getFallbackHtml() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Task Manager</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 640px; margin: 4rem auto; padding: 0 1rem; color: #1a1a2e; }
    h1 { color: #16213e; }
  </style>
</head>
<body>
  <h1>Task Manager</h1>
  <p>The frontend is not available yet. Use the <code>/api/tasks</code> endpoints directly.</p>
</body>
</html>`;
}

// GET /api/tasks -- List all tasks (optional ?status= and ?priority= filters)
router.get('/api/tasks', (req, res) => {
  try {
    let tasks = store.getAll();

    // Apply query-string filters when provided
    const { status, priority } = req.query || {};

    if (status) {
      tasks = tasks.filter((t) => t.status === status);
    }
    if (priority) {
      tasks = tasks.filter((t) => t.priority === priority);
    }

    sendJson(res, 200, { success: true, data: tasks });
  } catch (err) {
    console.error('Error listing tasks:', err);
    sendJson(res, 500, { success: false, error: 'Internal server error' });
  }
});

// GET /api/tasks/:id -- Get a single task
router.get('/api/tasks/:id', (req, res) => {
  try {
    const task = store.getById(req.params.id);
    if (!task) {
      return sendJson(res, 404, { success: false, error: 'Task not found' });
    }
    sendJson(res, 200, { success: true, data: task });
  } catch (err) {
    console.error('Error fetching task:', err);
    sendJson(res, 500, { success: false, error: 'Internal server error' });
  }
});

// POST /api/tasks -- Create a new task
router.post('/api/tasks', (req, res) => {
  try {
    const body = req.body || {};

    // Validate required field: title
    if (!body.title || typeof body.title !== 'string' || body.title.trim().length === 0) {
      return sendJson(res, 400, {
        success: false,
        error: 'Validation failed: "title" is required and must be a non-empty string',
      });
    }

    // Validate priority (if provided) must be one of the allowed values
    const allowedPriorities = ['low', 'medium', 'high'];
    if (body.priority && !allowedPriorities.includes(body.priority)) {
      return sendJson(res, 400, {
        success: false,
        error: `Validation failed: "priority" must be one of: ${allowedPriorities.join(', ')}`,
      });
    }

    const task = store.create({
      title: body.title.trim(),
      description: body.description || '',
      priority: body.priority || 'medium',
      status: body.status || 'todo',
    });

    sendJson(res, 201, { success: true, data: task });
  } catch (err) {
    console.error('Error creating task:', err);
    sendJson(res, 500, { success: false, error: 'Internal server error' });
  }
});

// PUT /api/tasks/:id -- Update an existing task
router.put('/api/tasks/:id', (req, res) => {
  try {
    const existing = store.getById(req.params.id);
    if (!existing) {
      return sendJson(res, 404, { success: false, error: 'Task not found' });
    }

    const body = req.body || {};

    // Validate title if being updated
    if (body.title !== undefined) {
      if (typeof body.title !== 'string' || body.title.trim().length === 0) {
        return sendJson(res, 400, {
          success: false,
          error: 'Validation failed: "title" must be a non-empty string',
        });
      }
    }

    // Validate priority if being updated
    const allowedPriorities = ['low', 'medium', 'high'];
    if (body.priority !== undefined && !allowedPriorities.includes(body.priority)) {
      return sendJson(res, 400, {
        success: false,
        error: `Validation failed: "priority" must be one of: ${allowedPriorities.join(', ')}`,
      });
    }

    // Validate status if being updated
    const allowedStatuses = ['todo', 'in-progress', 'done'];
    if (body.status !== undefined && !allowedStatuses.includes(body.status)) {
      return sendJson(res, 400, {
        success: false,
        error: `Validation failed: "status" must be one of: ${allowedStatuses.join(', ')}`,
      });
    }

    const updates = {};
    if (body.title !== undefined) updates.title = body.title.trim();
    if (body.description !== undefined) updates.description = body.description;
    if (body.priority !== undefined) updates.priority = body.priority;
    if (body.status !== undefined) updates.status = body.status;

    const updated = store.update(req.params.id, updates);
    sendJson(res, 200, { success: true, data: updated });
  } catch (err) {
    console.error('Error updating task:', err);
    sendJson(res, 500, { success: false, error: 'Internal server error' });
  }
});

// DELETE /api/tasks/:id -- Delete a task
router.delete('/api/tasks/:id', (req, res) => {
  try {
    const existing = store.getById(req.params.id);
    if (!existing) {
      return sendJson(res, 404, { success: false, error: 'Task not found' });
    }

    store.delete(req.params.id);
    sendJson(res, 200, { success: true, message: 'Task deleted successfully' });
  } catch (err) {
    console.error('Error deleting task:', err);
    sendJson(res, 500, { success: false, error: 'Internal server error' });
  }
});

// -- HTTP server ---------------------------------------------------------------

const server = http.createServer(async (req, res) => {
  // Log every request
  logRequest(req);

  // Set CORS headers on every response
  setCorsHeaders(res);

  // Handle CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // Parse JSON body for methods that typically carry a payload
  if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
    await parseJsonBody(req);
  }

  // Attempt to match a registered route
  const matched = router.handle(req, res);

  if (!matched) {
    sendJson(res, 404, { success: false, error: 'Not found' });
  }
});

server.listen(PORT, () => {
  console.log(`\n  Task Manager API server running at http://localhost:${PORT}`);
  console.log(`  Press Ctrl+C to stop.\n`);
});

export { server, router };
