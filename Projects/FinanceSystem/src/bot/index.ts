import { Telegraf, Context } from 'telegraf';
import { config } from '../config';
import { UserService } from '../services/userService';
import { UserRole } from '../types';
import { registerRequestCommands } from './requestCommands';
import { registerOwnerCommands } from './ownerCommands';
import { registerPaymentCommands } from './paymentCommands';
import { registerSpecialRoleCommands } from './specialRoleCommands';

const userService = new UserService();

export const bot = new Telegraf(config.telegram.botToken);

// Middleware для проверки авторизации
bot.use(async (ctx, next) => {
  if (!ctx.from) return;

  const user = await userService.getUserByTelegramId(ctx.from.id);

  if (!user) {
    await ctx.reply(
      '⛔ Вы не зарегистрированы в системе.\n\n' +
      'Для получения доступа обратитесь к администратору.'
    );
    return;
  }

  (ctx as any).user = user;
  return next();
});

// Команда /start
bot.command('start', async (ctx) => {
  const user = (ctx as any).user;

  await ctx.reply(
    `👋 Добро пожаловать в систему управления финансами!\n\n` +
    `Ваша роль: ${getRoleName(user.role)}\n\n` +
    `Используйте /help для просмотра доступных команд.`
  );
});

// Команда /help
bot.command('help', async (ctx) => {
  const user = (ctx as any).user;
  const commands = getCommandsForRole(user.role);

  await ctx.reply(
    `📚 Доступные команды:\n\n${commands.join('\n')}\n\n` +
    `Ваша роль: ${getRoleName(user.role)}`
  );
});

// Регистрируем команды
registerRequestCommands(bot);
registerOwnerCommands(bot);
registerPaymentCommands(bot);
registerSpecialRoleCommands(bot);

// Вспомогательные функции
function getRoleName(role: UserRole): string {
  const roleNames = {
    [UserRole.OWNER]: 'Владелец',
    [UserRole.MANAGER]: 'Менеджер',
    [UserRole.MANAGER_PLUS]: 'Менеджер+',
    [UserRole.EXECUTOR]: 'Оплатитель',
    [UserRole.PAYROLL]: 'Зарплатный специалист',
    [UserRole.BUYER]: 'Выкупщик',
  };

  return roleNames[role] || role;
}

function getCommandsForRole(role: UserRole): string[] {
  const commonCommands = [
    '/help - Справка по командам',
    '/my_requests - Мои заявки',
  ];

  const roleCommands: Record<UserRole, string[]> = {
    [UserRole.OWNER]: [
      ...commonCommands,
      '/pending_approvals - Заявки на одобрение',
      '/pending_payments - Одобренные заявки',
      '/balance - Балансы кошельков',
    ],
    [UserRole.MANAGER]: [
      ...commonCommands,
      '/new_request - Создать заявку',
      '/edit_request [ID] - Редактировать заявку',
    ],
    [UserRole.MANAGER_PLUS]: [
      ...commonCommands,
      '/new_request - Создать заявку',
      '/edit_request [ID] - Редактировать заявку',
      '/pay_my_request [ID] - Оплатить свою заявку',
    ],
    [UserRole.EXECUTOR]: [
      ...commonCommands,
      '/pending_payments - Заявки на оплату',
      '/take_request [ID] - Взять заявку',
      '/confirm_payment [ID] - Подтвердить оплату',
      '/balance - Балансы кошельков',
    ],
    [UserRole.PAYROLL]: [
      ...commonCommands,
      '/payroll_status - Статус зарплат',
    ],
    [UserRole.BUYER]: [
      ...commonCommands,
      '/new_bulk_request - Групповая заявка',
    ],
  };

  return roleCommands[role] || commonCommands;
}

export async function startBot() {
  try {
    await bot.launch();
    console.log('✅ Telegram bot started successfully');
  } catch (error) {
    console.error('❌ Failed to start bot:', error);
    throw error;
  }
}

// Graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
