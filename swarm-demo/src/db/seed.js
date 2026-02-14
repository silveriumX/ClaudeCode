/**
 * Seed data for the Task Manager app.
 * Provides a set of realistic sample tasks for initial population.
 */

import crypto from 'node:crypto';

export function getSeedTasks() {
  const now = new Date();

  return [
    {
      id: crypto.randomUUID(),
      title: 'Set up CI/CD pipeline',
      description:
        'Configure GitHub Actions to run tests, lint, and deploy to staging on every push to the main branch.',
      status: 'todo',
      priority: 'high',
      createdAt: new Date(now.getTime() - 5 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: crypto.randomUUID(),
      title: 'Fix login page redirect bug',
      description:
        'Users are being redirected to a 404 page after successful login when they had a deep link saved. Investigate the auth callback flow.',
      status: 'in-progress',
      priority: 'high',
      createdAt: new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: crypto.randomUUID(),
      title: 'Write API documentation',
      description:
        'Document all REST endpoints including request/response schemas, authentication requirements, and example curl commands.',
      status: 'in-progress',
      priority: 'medium',
      createdAt: new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: crypto.randomUUID(),
      title: 'Add dark mode support',
      description:
        'Implement a theme toggle that switches between light and dark color schemes. Persist the user preference in localStorage.',
      status: 'todo',
      priority: 'low',
      createdAt: new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString(),
    },
    {
      id: crypto.randomUUID(),
      title: 'Optimize database queries',
      description:
        'Profile slow queries on the tasks listing endpoint and add appropriate indexes. Target response time under 200ms.',
      status: 'done',
      priority: 'medium',
      createdAt: new Date(now.getTime() - 10 * 24 * 60 * 60 * 1000).toISOString(),
    },
  ];
}
