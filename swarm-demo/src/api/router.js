/**
 * Simple HTTP router utility.
 *
 * Provides Express-like route registration with support for
 * path parameters (e.g. /api/tasks/:id).  Uses only Node.js
 * built-in modules — no external dependencies.
 */

/**
 * Convert a route pattern like "/api/tasks/:id" into a RegExp
 * and extract the parameter names.
 *
 * @param {string} pattern - Route pattern with optional :param segments
 * @returns {{ regex: RegExp, paramNames: string[] }}
 */
function compilePath(pattern) {
  const paramNames = [];

  // Escape special regex chars except for : which marks params
  const regexStr = pattern
    .replace(/[-\\^$+?.()|[\]{}]/g, '\\$&')
    .replace(/:([a-zA-Z_][a-zA-Z0-9_]*)/g, (_match, name) => {
      paramNames.push(name);
      // Match one or more characters that are not a slash
      return '([^/]+)';
    });

  // Anchor the pattern so it matches the full path
  const regex = new RegExp(`^${regexStr}$`);

  return { regex, paramNames };
}

/**
 * Router — a lightweight HTTP router.
 *
 * Usage:
 *   const router = new Router();
 *   router.get('/api/items',      listHandler);
 *   router.get('/api/items/:id',  getHandler);
 *   router.post('/api/items',     createHandler);
 *
 *   // Inside the http request listener:
 *   const handled = router.handle(req, res);
 *   if (!handled) { ... send 404 ... }
 */
export class Router {
  constructor() {
    /** @type {Array<{ method: string, pattern: string, regex: RegExp, paramNames: string[], handler: Function }>} */
    this.routes = [];
  }

  // ── Route registration helpers ──────────────────────────────

  /**
   * Register a GET route.
   * @param {string} pattern - URL pattern (e.g. "/api/tasks/:id")
   * @param {Function} handler - (req, res) => void
   */
  get(pattern, handler) {
    this._addRoute('GET', pattern, handler);
  }

  /**
   * Register a POST route.
   * @param {string} pattern
   * @param {Function} handler
   */
  post(pattern, handler) {
    this._addRoute('POST', pattern, handler);
  }

  /**
   * Register a PUT route.
   * @param {string} pattern
   * @param {Function} handler
   */
  put(pattern, handler) {
    this._addRoute('PUT', pattern, handler);
  }

  /**
   * Register a DELETE route.
   * @param {string} pattern
   * @param {Function} handler
   */
  delete(pattern, handler) {
    this._addRoute('DELETE', pattern, handler);
  }

  // ── Internal route storage ──────────────────────────────────

  /**
   * Add a route definition to the internal list.
   * @param {string} method - HTTP method (uppercase)
   * @param {string} pattern - URL pattern
   * @param {Function} handler - Request handler
   * @private
   */
  _addRoute(method, pattern, handler) {
    const { regex, paramNames } = compilePath(pattern);
    this.routes.push({ method, pattern, regex, paramNames, handler });
  }

  // ── Request matching ────────────────────────────────────────

  /**
   * Attempt to match an incoming request to a registered route and invoke
   * the corresponding handler.
   *
   * When a match is found the handler receives `req` and `res` with an
   * additional `req.params` object containing any extracted path parameters.
   *
   * @param {import('http').IncomingMessage} req
   * @param {import('http').ServerResponse} res
   * @returns {boolean} `true` if a matching route was found and the handler
   *   was called; `false` otherwise (caller should send 404).
   */
  handle(req, res) {
    // Strip query string so we only match the path portion
    const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    const pathname = url.pathname;
    const method = req.method.toUpperCase();

    for (const route of this.routes) {
      if (route.method !== method) continue;

      const match = pathname.match(route.regex);
      if (!match) continue;

      // Build params object from captured groups
      const params = {};
      route.paramNames.forEach((name, index) => {
        params[name] = decodeURIComponent(match[index + 1]);
      });

      // Attach params and parsed query to the request for convenience
      req.params = params;
      req.query = Object.fromEntries(url.searchParams.entries());

      // Invoke the handler
      route.handler(req, res);
      return true;
    }

    // No route matched
    return false;
  }
}
