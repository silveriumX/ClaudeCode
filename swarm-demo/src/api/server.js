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
 *   PATCH  /api/tasks/:id -> Partially update an existing task
 *   DELETE /api/tasks/:id -> Delete a task
 */

import http from 'node:http';
import { Router } from './router.js';
import store from '../db/store.js';
import { renderApp } from '../components/App.js';

// -- Initialise core objects ---------------------------------------------------

const router = new Router();
const PORT = process.env.PORT || 3000;

// -- Validation constants ------------------------------------------------------

const ALLOWED_PRIORITIES = ['low', 'medium', 'high'];
const ALLOWED_STATUSES = ['todo', 'in-progress', 'done'];
const MAX_TITLE_LENGTH = 200;
const MAX_DESCRIPTION_LENGTH = 2000;

// -- Body size limit -----------------------------------------------------------

const MAX_BODY_SIZE = 1024 * 100; // 100 KB

// -- Rate limiting -------------------------------------------------------------

const rateLimitMap = new Map();
const RATE_LIMIT_WINDOW_MS = 60 * 1000;
const RATE_LIMIT_MAX = 100;

/**
 * Simple in-memory rate limiter based on client IP.
 * Returns true if the request is allowed, false if rate-limited.
 *
 * @param {import('http').IncomingMessage} req
 * @param {import('http').ServerResponse} res
 * @returns {boolean}
 */
function rateLimit(req, res) {
  const ip = req.socket.remoteAddress || 'unknown';
  const now = Date.now();
  const entry = rateLimitMap.get(ip) || { count: 0, resetAt: now + RATE_LIMIT_WINDOW_MS };

  if (now > entry.resetAt) {
    entry.count = 0;
    entry.resetAt = now + RATE_LIMIT_WINDOW_MS;
  }

  entry.count++;
  rateLimitMap.set(ip, entry);

  if (entry.count > RATE_LIMIT_MAX) {
    sendJson(res, 429, { success: false, error: 'Too many requests' });
    return false;
  }
  return true;
}

// -- Middleware-style helpers ---------------------------------------------------

/**
 * Read the full request body and parse it as JSON.
 * Attaches the result to `req.body`.  If the body is empty or
 * invalid JSON the promise resolves with an empty object.
 * Enforces a maximum body size to prevent abuse.
 *
 * @param {import('http').IncomingMessage} req
 * @returns {Promise<void>}
 */
function parseJsonBody(req) {
  return new Promise((resolve) => {
    const chunks = [];
    let totalSize = 0;

    req.on('data', (chunk) => {
      totalSize += chunk.length;
      if (totalSize > MAX_BODY_SIZE) {
        req.destroy();
        req.body = {};
        req.bodyTooLarge = true;
        return resolve();
      }
      chunks.push(chunk);
    });

    req.on('end', () => {
      if (req.bodyTooLarge) return;
      const raw = Buffer.concat(chunks).toString('utf-8');
      if (!raw || raw.trim().length === 0) {
        req.body = {};
        return resolve();
      }
      try {
        req.body = JSON.parse(raw);
      } catch {
        req.body = {};
        req.jsonParseError = true;
      }
      resolve();
    });

    req.on('error', () => {
      req.body = {};
      resolve();
    });
  });
}

/**
 * Set common CORS headers so the API can be consumed from any origin.
 * @param {import('http').ServerResponse} res
 */
function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
}

/**
 * Set HTTP security headers to harden the response.
 * @param {import('http').ServerResponse} res
 */
function setSecurityHeaders(res) {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
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
  try {
    const tasks = store.getAll();
    const html = renderApp(tasks);
    sendHtml(res, 200, html);
  } catch (err) {
    console.error('Error rendering page:', err);
    sendHtml(res, 200, getFallbackHtml());
  }
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

    // Validate title length
    if (body.title.trim().length > MAX_TITLE_LENGTH) {
      return sendJson(res, 400, {
        success: false,
        error: `Validation failed: "title" must be at most ${MAX_TITLE_LENGTH} characters`,
      });
    }

    // Validate description length (if provided)
    if (body.description && body.description.length > MAX_DESCRIPTION_LENGTH) {
      return sendJson(res, 400, {
        success: false,
        error: `Validation failed: "description" must be at most ${MAX_DESCRIPTION_LENGTH} characters`,
      });
    }

    // Validate priority (if provided) must be one of the allowed values
    if (body.priority && !ALLOWED_PRIORITIES.includes(body.priority)) {
      return sendJson(res, 400, {
        success: false,
        error: `Validation failed: "priority" must be one of: ${ALLOWED_PRIORITIES.join(', ')}`,
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
// PATCH /api/tasks/:id -- Partially update an existing task
const updateTaskHandler = (req, res) => {
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
      if (body.title.trim().length > MAX_TITLE_LENGTH) {
        return sendJson(res, 400, {
          success: false,
          error: `Validation failed: "title" must be at most ${MAX_TITLE_LENGTH} characters`,
        });
      }
    }

    // Validate description length if being updated
    if (body.description !== undefined && body.description.length > MAX_DESCRIPTION_LENGTH) {
      return sendJson(res, 400, {
        success: false,
        error: `Validation failed: "description" must be at most ${MAX_DESCRIPTION_LENGTH} characters`,
      });
    }

    // Validate priority if being updated
    if (body.priority !== undefined && !ALLOWED_PRIORITIES.includes(body.priority)) {
      return sendJson(res, 400, {
        success: false,
        error: `Validation failed: "priority" must be one of: ${ALLOWED_PRIORITIES.join(', ')}`,
      });
    }

    // Validate status if being updated
    if (body.status !== undefined && !ALLOWED_STATUSES.includes(body.status)) {
      return sendJson(res, 400, {
        success: false,
        error: `Validation failed: "status" must be one of: ${ALLOWED_STATUSES.join(', ')}`,
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
};

router.put('/api/tasks/:id', updateTaskHandler);
router._addRoute('PATCH', '/api/tasks/:id', updateTaskHandler);

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

  // Set security headers on every response
  setSecurityHeaders(res);

  // Set CORS headers on every response
  setCorsHeaders(res);

  // Rate limiting -- reject if too many requests from this IP
  if (!rateLimit(req, res)) {
    return;
  }

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

  // Check for body parsing errors before routing
  if (req.bodyTooLarge) {
    return sendJson(res, 413, { success: false, error: 'Request body too large' });
  }
  if (req.jsonParseError) {
    return sendJson(res, 400, { success: false, error: 'Invalid JSON in request body' });
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

// Server timeouts for security and performance
server.keepAliveTimeout = 65000;
server.headersTimeout = 66000;
server.timeout = 120000;

export { server, router };
