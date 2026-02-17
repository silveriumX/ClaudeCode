import { config } from './config';
import { initDatabase } from './database';
import { startBot } from './bot';

async function main() {
  console.log('🚀 Starting Finance Management System...\n');

  // Проверяем конфигурацию
  if (!config.telegram.botToken) {
    console.error('❌ TELEGRAM_BOT_TOKEN is not set');
    process.exit(1);
  }

  if (!config.google.privateKey) {
    console.error('❌ GOOGLE_PRIVATE_KEY is not set');
    process.exit(1);
  }

  if (!config.database.url) {
    console.error('❌ DATABASE_URL is not set');
    process.exit(1);
  }

  try {
    // Инициализируем базу данных
    console.log('📦 Initializing database...');
    await initDatabase();

    // Запускаем Telegram бота
    console.log('🤖 Starting Telegram bot...');
    await startBot();

    console.log('\n✅ System started successfully!');
    console.log('📊 Bot is running and ready to accept requests\n');
  } catch (error) {
    console.error('❌ Failed to start system:', error);
    process.exit(1);
  }
}

main();
