import { Pool } from 'pg';
import { config } from '../config';

export const pool = new Pool({
  connectionString: config.database.url,
});

export async function initDatabase() {
  const client = await pool.connect();
  try {
    // Создаем таблицу пользователей
    await client.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        telegram_id BIGINT UNIQUE NOT NULL,
        username VARCHAR(255),
        full_name VARCHAR(255),
        role VARCHAR(50) NOT NULL,
        company VARCHAR(255),
        created_at TIMESTAMP DEFAULT NOW()
      );
    `);

    // Создаем таблицу заявок
    await client.query(`
      CREATE TABLE IF NOT EXISTS requests (
        id SERIAL PRIMARY KEY,
        external_id VARCHAR(50) UNIQUE NOT NULL,
        author_id INT REFERENCES users(id),
        company VARCHAR(255),
        category VARCHAR(100),
        subcategory VARCHAR(100),
        recipient VARCHAR(255),
        amount_rub DECIMAL(12,2),
        payment_method VARCHAR(50),
        payment_details TEXT,
        purpose TEXT,
        wallet VARCHAR(100),
        status VARCHAR(50),
        urgency VARCHAR(20),
        approved_by INT REFERENCES users(id),
        approved_at TIMESTAMP,
        paid_by INT REFERENCES users(id),
        paid_at TIMESTAMP,
        exchange_rate DECIMAL(10,4),
        amount_usdt DECIMAL(12,4),
        comments TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
      );
    `);

    // Создаем таблицу кошельков
    await client.query(`
      CREATE TABLE IF NOT EXISTS wallets (
        id SERIAL PRIMARY KEY,
        company VARCHAR(255),
        name VARCHAR(255) NOT NULL,
        type VARCHAR(50),
        balance_usdt DECIMAL(12,4),
        last_updated TIMESTAMP,
        responsible VARCHAR(255),
        note TEXT,
        created_at TIMESTAMP DEFAULT NOW()
      );
    `);

    // Создаем таблицу audit log
    await client.query(`
      CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        user_id INT REFERENCES users(id),
        action VARCHAR(255) NOT NULL,
        entity_type VARCHAR(50),
        entity_id INT,
        details JSONB,
        created_at TIMESTAMP DEFAULT NOW()
      );
    `);

    // Создаем индексы
    await client.query(`
      CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status);
      CREATE INDEX IF NOT EXISTS idx_requests_author ON requests(author_id);
      CREATE INDEX IF NOT EXISTS idx_requests_company ON requests(company);
    `);

    console.log('✅ Database initialized successfully');
  } catch (error) {
    console.error('❌ Database initialization error:', error);
    throw error;
  } finally {
    client.release();
  }
}
