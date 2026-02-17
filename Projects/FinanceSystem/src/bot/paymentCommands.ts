import { Context, Markup } from 'telegraf';
import { RequestService } from '../services/requestService';
import { UserService } from '../services/userService';
import { GoogleSheetsService } from '../integrations/googleSheets';
import { UserRole, RequestStatus } from '../types';

const requestService = new RequestService();
const userService = new UserService();
const sheetsService = new GoogleSheetsService();

// Хранилище состояний оплаты
const paymentStates = new Map<number, any>();

export function registerPaymentCommands(bot: any) {
  // Команда просмотра заявок на оплату
  bot.command('pending_payments', async (ctx: Context) => {
    const user = (ctx as any).user;

    if (![UserRole.EXECUTOR, UserRole.OWNER].includes(user.role)) {
      await ctx.reply('⛔ У вас нет доступа к оплате заявок');
      return;
    }

    const requests = await requestService.getPendingPayments();

    if (requests.length === 0) {
      await ctx.reply('Нет заявок, ожидающих оплаты');
      return;
    }

    let message = '💰 Заявки на оплату:\n\n';

    for (const req of requests) {
      const statusEmoji = req.status === RequestStatus.IN_PROGRESS ? '⏳' : '🔵';
      message += `${statusEmoji} #${req.externalId}\n`;
      message += `${req.category} - ${req.amountRub} ₽\n`;
      message += `Получатель: ${req.recipient}\n`;
      message += `Кошелек: ${req.wallet}\n`;
      if (req.status === RequestStatus.IN_PROGRESS) {
        message += `В работе у другого оплатителя\n`;
      }
      message += `\n`;
    }

    const availableRequests = requests.filter(r => r.status !== RequestStatus.IN_PROGRESS);

    await ctx.reply(
      message.trim(),
      availableRequests.length > 0 ? Markup.inlineKeyboard(
        availableRequests.slice(0, 10).map((req) => [
          Markup.button.callback(
            `💰 ${req.externalId} (${req.amountRub}₽)`,
            `take_request_${req.externalId}`
          ),
        ])
      ) : undefined
    );
  });

  // Взять заявку в работу
  bot.action(/^take_request_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    const user = (ctx as any).user;

    if (![UserRole.EXECUTOR, UserRole.OWNER].includes(user.role)) {
      await ctx.answer('⛔ У вас нет доступа к оплате заявок');
      return;
    }

    const request = await requestService.getRequestById(requestId);

    if (!request) {
      await ctx.answer('❌ Заявка не найдена');
      return;
    }

    if (request.status !== RequestStatus.APPROVED) {
      await ctx.answer('❌ Эта заявка уже в работе или оплачена');
      return;
    }

    try {
      // Обновляем статус на "В работе"
      await requestService.updateRequestStatus(
        requestId,
        RequestStatus.IN_PROGRESS,
        user.id
      );

      // Сохраняем состояние
      paymentStates.set(ctx.from!.id, { requestId, request });

      await ctx.editMessageText(
        `⏳ Заявка #${requestId} взята в работу\n\n` +
        `Детали оплаты:\n` +
        `Сумма: ${request.amountRub} ₽\n` +
        `Получатель: ${request.recipient}\n` +
        `Способ: ${request.paymentMethod}\n` +
        `Реквизиты: ${request.paymentDetails}\n` +
        `Кошелек: ${request.wallet}\n` +
        `Назначение: ${request.purpose}\n\n` +
        `📝 После проведения реальной оплаты введите курс USDT/RUB (например: 73.5):`
      );

      // Логируем действие
      await userService.logAction(
        user.id,
        'take_request',
        'request',
        request.id,
        { requestId }
      );
    } catch (error) {
      console.error('Error taking request:', error);
      await ctx.answer('❌ Ошибка при взятии заявки');
    }
  });

  // Обработка ввода курса
  bot.on('text', async (ctx: Context) => {
    const state = paymentStates.get(ctx.from!.id);

    if (state && state.request && !state.exchangeRate) {
      const text = (ctx as any).message.text;
      const rate = parseFloat(text);

      if (isNaN(rate) || rate <= 0) {
        await ctx.reply('❌ Неверный курс. Введите число больше 0 (например: 73.5):');
        return;
      }

      state.exchangeRate = rate;
      const amountUsdt = state.request.amountRub / rate;

      await ctx.reply(
        `📊 Расчет:\n\n` +
        `Сумма: ${state.request.amountRub} ₽\n` +
        `Курс: ${rate}\n` +
        `Списано USDT: ${amountUsdt.toFixed(2)}\n\n` +
        `Подтвердите оплату:`,
        Markup.inlineKeyboard([
          [Markup.button.callback('✅ Подтвердить оплату', 'confirm_payment')],
          [Markup.button.callback('❌ Отменить', 'cancel_payment')],
        ])
      );
    }
  });

  // Подтверждение оплаты
  bot.action('confirm_payment', async (ctx: Context) => {
    const state = paymentStates.get(ctx.from!.id);
    const user = (ctx as any).user;

    if (!state) {
      await ctx.answer('❌ Данные оплаты не найдены');
      return;
    }

    try {
      const amountUsdt = state.request.amountRub / state.exchangeRate;

      // Обновляем заявку
      await requestService.confirmPayment(
        state.requestId,
        user.id,
        state.exchangeRate,
        amountUsdt,
        `@${ctx.from!.username || ctx.from!.id}`
      );

      // Обновляем баланс кошелька
      const wallets = await sheetsService.getWalletBalances();
      const wallet = wallets.find(w => w.name === state.request.wallet);

      if (wallet) {
        const newBalance = wallet.balanceUsdt - amountUsdt;
        await sheetsService.updateWalletBalance(wallet.name, newBalance);
      }

      // Логируем действие
      await userService.logAction(
        user.id,
        'confirm_payment',
        'request',
        state.request.id,
        {
          requestId: state.requestId,
          exchangeRate: state.exchangeRate,
          amountUsdt
        }
      );

      // Очищаем состояние
      paymentStates.delete(ctx.from!.id);

      await ctx.editMessageText(
        `✅ Оплата подтверждена!\n\n` +
        `Заявка #${state.requestId} оплачена.\n` +
        `Списано: ${amountUsdt.toFixed(2)} USDT\n` +
        `Баланс кошелька обновлен.`
      );

      // Уведомляем владельца и автора
      await notifyPaymentCompleted(ctx, state.request, user, state.exchangeRate, amountUsdt);

    } catch (error) {
      console.error('Error confirming payment:', error);
      await ctx.answer('❌ Ошибка при подтверждении оплаты');
    }
  });

  // Отмена оплаты
  bot.action('cancel_payment', async (ctx: Context) => {
    const state = paymentStates.get(ctx.from!.id);

    if (state) {
      // Возвращаем статус заявки обратно в "Одобрена"
      await requestService.updateRequestStatus(
        state.requestId,
        RequestStatus.APPROVED,
        null
      );

      paymentStates.delete(ctx.from!.id);
    }

    await ctx.editMessageText('❌ Оплата отменена. Заявка возвращена в список на оплату.');
  });
}

// Уведомление о завершении оплаты
async function notifyPaymentCompleted(
  ctx: Context,
  request: any,
  executor: any,
  rate: number,
  amountUsdt: number
) {
  const { config } = await import('../config');
  const { bot } = await import('./index');

  // Уведомляем владельца
  await bot.telegram.sendMessage(
    config.telegram.ownerTelegramId,
    `✅ Заявка #${request.externalId} оплачена\n\n` +
    `Оплатил: @${ctx.from!.username || ctx.from!.id}\n` +
    `Сумма: ${request.amountRub} ₽\n` +
    `Курс: ${rate}\n` +
    `Списано: ${amountUsdt.toFixed(2)} USDT\n` +
    `Кошелек: ${request.wallet}`
  );

  // Уведомляем автора заявки
  const authorUser = await userService.getUserByTelegramId(request.authorId);
  if (authorUser) {
    await bot.telegram.sendMessage(
      authorUser.telegramId,
      `✅ Ваша заявка #${request.externalId} оплачена!\n\n` +
      `Сумма: ${request.amountRub} ₽\n` +
      `Получатель: ${request.recipient}\n` +
      `Способ: ${request.paymentMethod}`
    );
  }
}

// Дополнительный метод в RequestService
declare module '../services/requestService' {
  interface RequestService {
    getPendingPayments(): Promise<any[]>;
    updateRequestStatus(requestId: string, status: RequestStatus, userId: number | null): Promise<void>;
    confirmPayment(
      requestId: string,
      paidBy: number,
      exchangeRate: number,
      amountUsdt: number,
      paidByUsername: string
    ): Promise<void>;
  }
}
