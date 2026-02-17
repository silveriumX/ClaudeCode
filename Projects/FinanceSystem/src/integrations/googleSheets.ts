import { google, sheets_v4 } from 'googleapis';
import { config } from '../config';

export class GoogleSheetsService {
  private sheets: sheets_v4.Sheets;

  constructor() {
    const auth = new google.auth.JWT({
      email: config.google.serviceAccountEmail,
      key: config.google.privateKey,
      scopes: ['https://www.googleapis.com/auth/spreadsheets'],
    });

    this.sheets = google.sheets({ version: 'v4', auth });
  }

  // Добавить строку в таблицу
  async appendRow(spreadsheetId: string, range: string, values: any[]): Promise<void> {
    try {
      await this.sheets.spreadsheets.values.append({
        spreadsheetId,
        range,
        valueInputOption: 'USER_ENTERED',
        requestBody: {
          values: [values],
        },
      });
    } catch (error) {
      console.error('Error appending row to sheet:', error);
      throw error;
    }
  }

  // Получить все данные из диапазона
  async getValues(spreadsheetId: string, range: string): Promise<any[][]> {
    try {
      const response = await this.sheets.spreadsheets.values.get({
        spreadsheetId,
        range,
      });

      return response.data.values || [];
    } catch (error) {
      console.error('Error getting values from sheet:', error);
      throw error;
    }
  }

  // Обновить строку
  async updateRow(spreadsheetId: string, range: string, values: any[]): Promise<void> {
    try {
      await this.sheets.spreadsheets.values.update({
        spreadsheetId,
        range,
        valueInputOption: 'USER_ENTERED',
        requestBody: {
          values: [values],
        },
      });
    } catch (error) {
      console.error('Error updating row in sheet:', error);
      throw error;
    }
  }

  // Найти строку по ID заявки
  async findRequestRow(requestId: string): Promise<number | null> {
    try {
      const values = await this.getValues(
        config.google.mainSpreadsheetId,
        'Заявки!A:A'
      );

      for (let i = 0; i < values.length; i++) {
        if (values[i][0] === requestId) {
          return i + 1; // +1 потому что нумерация строк с 1
        }
      }

      return null;
    } catch (error) {
      console.error('Error finding request row:', error);
      return null;
    }
  }

  // Получить балансы кошельков
  async getWalletBalances(): Promise<any[]> {
    try {
      const values = await this.getValues(
        config.google.mainSpreadsheetId,
        'Балансы кошельков!A2:G100'
      );

      return values.map(row => ({
        company: row[0] || '',
        name: row[1] || '',
        type: row[2] || '',
        balanceUsdt: parseFloat(row[3]) || 0,
        lastUpdated: row[4] || '',
        responsible: row[5] || '',
        note: row[6] || '',
      }));
    } catch (error) {
      console.error('Error getting wallet balances:', error);
      return [];
    }
  }

  // Обновить баланс кошелька
  async updateWalletBalance(walletName: string, newBalance: number): Promise<void> {
    try {
      const values = await this.getValues(
        config.google.mainSpreadsheetId,
        'Балансы кошельков!A2:G100'
      );

      for (let i = 0; i < values.length; i++) {
        if (values[i][1] === walletName) {
          const rowNumber = i + 2; // +2 потому что строки с 1 и первая строка заголовок
          const now = new Date().toLocaleString('ru-RU');

          await this.updateRow(
            config.google.mainSpreadsheetId,
            `Балансы кошельков!D${rowNumber}:E${rowNumber}`,
            [newBalance, now]
          );

          return;
        }
      }

      console.warn(`Wallet ${walletName} not found in spreadsheet`);
    } catch (error) {
      console.error('Error updating wallet balance:', error);
      throw error;
    }
  }
}
