import { pool } from '../database';
import { User, UserRole } from '../types';

export class UserService {
  async getUserByTelegramId(telegramId: number): Promise<User | null> {
    const result = await pool.query(
      'SELECT * FROM users WHERE telegram_id = $1',
      [telegramId]
    );

    if (result.rows.length === 0) return null;

    const row = result.rows[0];
    return {
      id: row.id,
      telegramId: row.telegram_id,
      username: row.username,
      fullName: row.full_name,
      role: row.role as UserRole,
      company: row.company,
      createdAt: row.created_at,
    };
  }

  async createUser(data: {
    telegramId: number;
    username: string;
    fullName?: string;
    role: UserRole;
    company?: string;
  }): Promise<User> {
    const result = await pool.query(
      `INSERT INTO users (telegram_id, username, full_name, role, company)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING *`,
      [data.telegramId, data.username, data.fullName, data.role, data.company]
    );

    const row = result.rows[0];
    return {
      id: row.id,
      telegramId: row.telegram_id,
      username: row.username,
      fullName: row.full_name,
      role: row.role as UserRole,
      company: row.company,
      createdAt: row.created_at,
    };
  }

  async updateUserRole(telegramId: number, role: UserRole): Promise<void> {
    await pool.query(
      'UPDATE users SET role = $1 WHERE telegram_id = $2',
      [role, telegramId]
    );
  }

  async getAllUsers(): Promise<User[]> {
    const result = await pool.query('SELECT * FROM users ORDER BY created_at DESC');

    return result.rows.map(row => ({
      id: row.id,
      telegramId: row.telegram_id,
      username: row.username,
      fullName: row.full_name,
      role: row.role as UserRole,
      company: row.company,
      createdAt: row.created_at,
    }));
  }

  async logAction(userId: number, action: string, entityType: string, entityId?: number, details?: any): Promise<void> {
    await pool.query(
      `INSERT INTO audit_log (user_id, action, entity_type, entity_id, details)
       VALUES ($1, $2, $3, $4, $5)`,
      [userId, action, entityType, entityId, details ? JSON.stringify(details) : null]
    );
  }
}
