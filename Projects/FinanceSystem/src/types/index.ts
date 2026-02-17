export enum UserRole {
  OWNER = 'owner',
  MANAGER = 'manager',
  MANAGER_PLUS = 'manager_plus',
  EXECUTOR = 'executor',
  PAYROLL = 'payroll',
  BUYER = 'buyer',
}

export enum RequestStatus {
  CREATED = 'Создана',
  APPROVED = 'Одобрена',
  IN_PROGRESS = 'В работе',
  PAID = 'Оплачена',
  REJECTED = 'Отклонена',
}

export enum PaymentMethod {
  CARD = 'Карта',
  SBP = 'СБП',
  PHONE = 'Телефон',
  CASH = 'Наличные',
  CRYPTO = 'Крипта',
  BYN = 'BYN',
}

export enum Category {
  SALARY = 'Зарплата',
  SUPPLIER = 'Поставщик',
  MARKETING = 'Маркетинг',
  LOGISTICS = 'Логистика',
  OFFICE = 'Офис',
  OTHER = 'Прочее',
}

export enum Urgency {
  NORMAL = 'Обычная',
  URGENT = 'Срочная',
}

export interface User {
  id: number;
  telegramId: number;
  username: string;
  fullName?: string;
  role: UserRole;
  company?: string;
  createdAt: Date;
}

export interface PaymentRequest {
  id: number;
  externalId: string;
  authorId: number;
  company: string;
  category: Category;
  subcategory?: string;
  recipient: string;
  amountRub: number;
  paymentMethod: PaymentMethod;
  paymentDetails: string;
  purpose: string;
  wallet?: string;
  status: RequestStatus;
  urgency: Urgency;
  approvedBy?: number;
  approvedAt?: Date;
  paidBy?: number;
  paidAt?: Date;
  exchangeRate?: number;
  amountUsdt?: number;
  comments?: string;
  createdAt: Date;
  updatedAt: Date;
}
