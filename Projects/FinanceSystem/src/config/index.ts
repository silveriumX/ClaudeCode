import dotenv from 'dotenv';

dotenv.config();

export const config = {
  telegram: {
    botToken: process.env.TELEGRAM_BOT_TOKEN || '',
    ownerTelegramId: parseInt(process.env.OWNER_TELEGRAM_ID || '0'),
  },
  google: {
    serviceAccountEmail: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL || '',
    privateKey: (process.env.GOOGLE_PRIVATE_KEY || '').replace(/\\n/g, '\n'),
    mainSpreadsheetId: process.env.MAIN_SPREADSHEET_ID || '',
    payrollSpreadsheetId: process.env.PAYROLL_SPREADSHEET_ID || '',
  },
  database: {
    url: process.env.DATABASE_URL || '',
  },
  limits: {
    managerPlusLimit: parseInt(process.env.MANAGER_PLUS_LIMIT || '10000'),
  },
};
