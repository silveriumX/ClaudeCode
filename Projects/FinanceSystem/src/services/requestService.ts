import { pool } from '../database';
import { PaymentRequest, RequestStatus, Category, PaymentMethod, Urgency } from '../types';
import { GoogleSheetsService } from '../integrations/googleSheets';
import { config } from '../config';

const sheetsService = new GoogleSheetsService();

export class RequestService {
  async createRequest(data: {
    authorId: number;
    company: string;
    category: Category;
    recipient: string;
    amountRub: number;
    paymentMethod: PaymentMethod;
    paymentDetails: string;
    purpose: string;
    urgency: Urgency;
    authorUsername: string;
  }): Promise<PaymentRequest> {
    // Генерируем ID заявки
    const externalId = `REQ-${Date.now()}`;
    const now = new Date();

    // Сохраняем в БД
    const result = await pool.query(
      `INSERT INTO requests
       (external_id, author_id, company, category, recipient, amount_rub,
        payment_method, payment_details, purpose, status, urgency, created_at, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
       RETURNING *`,
      [
        externalId,
        data.authorId,
        data.company,
        data.category,
        data.recipient,
        data.amountRub,
        data.paymentMethod,
        data.paymentDetails,
        data.purpose,
        RequestStatus.CREATED,
        data.urgency,
        now,
        now,
      ]
    );

    // Записываем в Google Sheets
    await this.addToSheets(externalId, data, now);

    return this.mapRow(result.rows[0]);
  }

  private async addToSheets(
    externalId: string,
    data: any,
    createdAt: Date
  ): Promise<void> {
    const row = [
      externalId,
      createdAt.toLocaleString('ru-RU'),
      data.authorUsername,
      data.company,
      data.category,
      data.recipient,
      data.amountRub,
      data.paymentMethod,
      data.paymentDetails,
      data.purpose,
      '', // Кошелек списания (заполнит Owner при одобрении)
      RequestStatus.CREATED,
      data.urgency,
      '', // Одобрил
      '', // Дата одобрения
      '', // Оплатил
      '', // Дата оплаты
      '', // Курс
      '', // Сумма USDT (формула)
      '', // Комментарии
    ];

    await sheetsService.appendRow(
      config.google.mainSpreadsheetId,
      'Заявки!A:T',
      row
    );
  }

  async getRequestById(requestId: string): Promise<PaymentRequest | null> {
    const result = await pool.query(
      'SELECT * FROM requests WHERE external_id = $1',
      [requestId]
    );

    if (result.rows.length === 0) return null;

    return this.mapRow(result.rows[0]);
  }

  async getRequestsByAuthor(authorId: number): Promise<PaymentRequest[]> {
    const result = await pool.query(
      'SELECT * FROM requests WHERE author_id = $1 ORDER BY created_at DESC LIMIT 20',
      [authorId]
    );

    return result.rows.map(row => this.mapRow(row));
  }

  async getPendingApprovals(): Promise<PaymentRequest[]> {
    const result = await pool.query(
      `SELECT * FROM requests
       WHERE status = $1
       ORDER BY urgency DESC, created_at ASC`,
      [RequestStatus.CREATED]
    );

    return result.rows.map(row => this.mapRow(row));
  }

  async approveRequest(
    requestId: string,
    approvedBy: number,
    wallet: string,
    approverUsername: string
  ): Promise<void> {
    const now = new Date();

    // Обновляем в БД
    await pool.query(
      `UPDATE requests
       SET status = $1, approved_by = $2, approved_at = $3, wallet = $4, updated_at = $5
       WHERE external_id = $6`,
      [RequestStatus.APPROVED, approvedBy, now, wallet, now, requestId]
    );

    // Обновляем в Google Sheets
    await this.updateInSheets(requestId, {
      status: RequestStatus.APPROVED,
      wallet,
      approvedBy: approverUsername,
      approvedAt: now.toLocaleString('ru-RU'),
    });
  }

  async rejectRequest(
    requestId: string,
    rejectedBy: number,
    reason: string
  ): Promise<void> {
    const now = new Date();

    // Обновляем в БД
    await pool.query(
      `UPDATE requests
       SET status = $1, comments = $2, updated_at = $3
       WHERE external_id = $4`,
      [RequestStatus.REJECTED, reason, now, requestId]
    );

    // Обновляем в Google Sheets
    await this.updateInSheets(requestId, {
      status: RequestStatus.REJECTED,
      comments: reason,
    });
  }

  async getPendingPayments(): Promise<PaymentRequest[]> {
    const result = await pool.query(
      `SELECT * FROM requests
       WHERE status IN ($1, $2)
       ORDER BY urgency DESC, approved_at ASC`,
      [RequestStatus.APPROVED, RequestStatus.IN_PROGRESS]
    );

    return result.rows.map(row => this.mapRow(row));
  }

  async updateRequestStatus(
    requestId: string,
    status: RequestStatus,
    userId: number | null
  ): Promise<void> {
    const now = new Date();

    await pool.query(
      `UPDATE requests
       SET status = $1, updated_at = $2
       WHERE external_id = $3`,
      [status, now, requestId]
    );

    // Обновляем в Google Sheets
    await this.updateInSheets(requestId, { status });
  }

  async confirmPayment(
    requestId: string,
    paidBy: number,
    exchangeRate: number,
    amountUsdt: number,
    paidByUsername: string
  ): Promise<void> {
    const now = new Date();

    // Обновляем в БД
    await pool.query(
      `UPDATE requests
       SET status = $1, paid_by = $2, paid_at = $3,
           exchange_rate = $4, amount_usdt = $5, updated_at = $6
       WHERE external_id = $7`,
      [RequestStatus.PAID, paidBy, now, exchangeRate, amountUsdt, now, requestId]
    );

    // Обновляем в Google Sheets
    await this.updateInSheets(requestId, {
      status: RequestStatus.PAID,
      paidBy: paidByUsername,
      paidAt: now.toLocaleString('ru-RU'),
      exchangeRate,
    });
  }

  async updateRequest(requestId: string, updates: any): Promise<void> {
    const now = new Date();
    const fields = [];
    const values = [];
    let index = 1;

    if (updates.recipient !== undefined) {
      fields.push(`recipient = $${index++}`);
      values.push(updates.recipient);
    }

    if (updates.amountRub !== undefined) {
      fields.push(`amount_rub = $${index++}`);
      values.push(updates.amountRub);
    }

    if (updates.paymentDetails !== undefined) {
      fields.push(`payment_details = $${index++}`);
      values.push(updates.paymentDetails);
    }

    if (updates.purpose !== undefined) {
      fields.push(`purpose = $${index++}`);
      values.push(updates.purpose);
    }

    if (fields.length === 0) return;

    fields.push(`updated_at = $${index++}`);
    values.push(now);
    values.push(requestId);

    await pool.query(
      `UPDATE requests SET ${fields.join(', ')} WHERE external_id = $${index}`,
      values
    );

    // Обновляем в Google Sheets
    await this.updateInSheets(requestId, updates);
  }

  private async updateInSheets(requestId: string, updates: any): Promise<void> {
    const rowNumber = await sheetsService.findRequestRow(requestId);
    if (!rowNumber) return;

    // Получаем текущие данные строки
    const currentRow = await sheetsService.getValues(
      config.google.mainSpreadsheetId,
      `Заявки!A${rowNumber}:T${rowNumber}`
    );

    if (currentRow.length === 0) return;

    const row = currentRow[0];

    // Обновляем только измененные поля
    if (updates.wallet !== undefined) row[10] = updates.wallet;
    if (updates.status !== undefined) row[11] = updates.status;
    if (updates.approvedBy !== undefined) row[13] = updates.approvedBy;
    if (updates.approvedAt !== undefined) row[14] = updates.approvedAt;
    if (updates.paidBy !== undefined) row[15] = updates.paidBy;
    if (updates.paidAt !== undefined) row[16] = updates.paidAt;
    if (updates.exchangeRate !== undefined) row[17] = updates.exchangeRate;
    if (updates.comments !== undefined) row[19] = updates.comments;

    await sheetsService.updateRow(
      config.google.mainSpreadsheetId,
      `Заявки!A${rowNumber}:T${rowNumber}`,
      row
    );
  }

  private mapRow(row: any): PaymentRequest {
    return {
      id: row.id,
      externalId: row.external_id,
      authorId: row.author_id,
      company: row.company,
      category: row.category as Category,
      subcategory: row.subcategory,
      recipient: row.recipient,
      amountRub: parseFloat(row.amount_rub),
      paymentMethod: row.payment_method as PaymentMethod,
      paymentDetails: row.payment_details,
      purpose: row.purpose,
      wallet: row.wallet,
      status: row.status as RequestStatus,
      urgency: row.urgency as Urgency,
      approvedBy: row.approved_by,
      approvedAt: row.approved_at,
      paidBy: row.paid_by,
      paidAt: row.paid_at,
      exchangeRate: row.exchange_rate ? parseFloat(row.exchange_rate) : undefined,
      amountUsdt: row.amount_usdt ? parseFloat(row.amount_usdt) : undefined,
      comments: row.comments,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}
