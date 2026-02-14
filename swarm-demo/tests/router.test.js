import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert';
import { Router } from '../src/api/router.js';

describe('Router', () => {
  let router;

  beforeEach(() => {
    router = new Router();
  });

  describe('route registration', () => {
    it('should register GET routes', () => {
      // Should not throw when registering a GET route
      assert.doesNotThrow(() => {
        router.get('/tasks', (req, res) => {
          res.end('ok');
        });
      }, 'Registering a GET route should not throw');
    });

    it('should register POST routes', () => {
      // Should not throw when registering a POST route
      assert.doesNotThrow(() => {
        router.post('/tasks', (req, res) => {
          res.end('ok');
        });
      }, 'Registering a POST route should not throw');
    });
  });

  describe('route matching', () => {
    it('should match exact paths and call the correct handler', () => {
      let handlerCalled = false;

      router.get('/tasks', (req, res) => {
        handlerCalled = true;
      });

      const { handler, params } = router.match('GET', '/tasks');

      assert.ok(handler, 'Should find a handler for GET /tasks');
      assert.deepStrictEqual(params, {}, 'Params should be empty for exact match');

      // Invoke the handler to verify it is the right one
      handler({}, {});
      assert.ok(handlerCalled, 'The correct handler should have been called');
    });

    it('should extract path parameters from :id segments', () => {
      let capturedParams = null;

      router.get('/tasks/:id', (req, res) => {
        capturedParams = req.params;
      });

      const { handler, params } = router.match('GET', '/tasks/abc-123');

      assert.ok(handler, 'Should find a handler for GET /tasks/:id');
      assert.strictEqual(params.id, 'abc-123', 'Should extract id parameter from path');

      // Invoke the handler with params attached to req
      handler({ params }, {});
      assert.deepStrictEqual(capturedParams, { id: 'abc-123' }, 'Handler should receive extracted params');
    });

    it('should return null handler for unmatched routes', () => {
      router.get('/tasks', (req, res) => {
        res.end('ok');
      });

      const result = router.match('GET', '/unknown');

      // The router should indicate no match was found
      assert.ok(
        result === null || result.handler === null || result.handler === undefined,
        'Should return null or no handler for unmatched route'
      );
    });

    it('should handle different HTTP methods on the same path', () => {
      let getHandlerCalled = false;
      let postHandlerCalled = false;

      router.get('/tasks', (req, res) => {
        getHandlerCalled = true;
      });

      router.post('/tasks', (req, res) => {
        postHandlerCalled = true;
      });

      // Match GET
      const getResult = router.match('GET', '/tasks');
      assert.ok(getResult && getResult.handler, 'Should match GET /tasks');
      getResult.handler({}, {});
      assert.ok(getHandlerCalled, 'GET handler should be called');
      assert.ok(!postHandlerCalled, 'POST handler should NOT be called for GET request');

      // Reset
      getHandlerCalled = false;

      // Match POST
      const postResult = router.match('POST', '/tasks');
      assert.ok(postResult && postResult.handler, 'Should match POST /tasks');
      postResult.handler({}, {});
      assert.ok(postHandlerCalled, 'POST handler should be called');
      assert.ok(!getHandlerCalled, 'GET handler should NOT be called for POST request');
    });
  });

  describe('404 handling', () => {
    it('should return no match for a path with no registered routes', () => {
      const result = router.match('GET', '/nonexistent');

      assert.ok(
        result === null || result.handler === null || result.handler === undefined,
        'Unregistered path should not match any handler'
      );
    });

    it('should not match GET route when POST is requested', () => {
      router.get('/tasks', (req, res) => {
        res.end('ok');
      });

      const result = router.match('POST', '/tasks');

      assert.ok(
        result === null || result.handler === null || result.handler === undefined,
        'GET route should not match a POST request'
      );
    });
  });
});
