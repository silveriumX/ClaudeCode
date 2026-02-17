import { Context, Markup } from 'telegraf';
import { RequestService } from '../services/requestService';
import { UserService } from '../services/userService';
import { UserRole, RequestStatus } from '../types';
import { GoogleSheetsService } from '../integrations/googleSheets';

const requestService = new RequestService();
const userService = new UserService();
const sheetsService = new GoogleSheetsService();

// Хранилище состояний одобрения (в продакшене использовать Redis)
const approvalStates = new Map<number, any>();

export function registerOwnerCommands(bot: any) {
  // Команда просмотра заявок на одобрение
  bot.command('pending_approvals', async (ctx: Context) => {
    const user = (ctx as any).user;

    if (user.role !== UserRole.OWNER) {
      await ctx.reply('⛔ Эта команда доступна только владельцу');
      return;
    }

    const requests = await requestService.getPendingApprovals();

    if (requests.length === 0) {
      await ctx.reply('Нет заявок, ожидающих одобрения');
      return;
    }

    let message = '📋 Заявки на одобрение:\n\n';

    for (const req of requests) {
      const urgencyEmoji = req.urgency === 'Срочная' ? '⚡ ' : '';
      message += `${urgencyEmoji}#${req.externalId}\n`;
      message += `${req.category} - ${req.amountRub} ₽\n`;
      message += `Получатель: ${req.recipient}\n`;
      message += `Назначение: ${req.purpose}\n\n`;
    }

    await ctx.reply(
      message.trim(),
      Markup.inlineKeyboard(
        requests.slice(0, 10).map((req) => [
          Markup.button.callback(
            `${req.urgency === 'Срочная' ? '⚡' : '📄'} ${req.externalId}`,
            `view_request_${req.externalId}`
          ),
        ])
      )
    );
  });

  // Просмотр заявки
  bot.action(/^view_request_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    const request = await requestService.getRequestById(requestId);

    if (!request) {
      await ctx.answer('❌ Заявка не найдена');
      return;
    }

    const urgencyEmoji = request.urgency === 'Срочная' ? '⚡ ' : '';

    const message = `
${urgencyEmoji}📄 Заявка #${request.externalId}

Компания: ${request.company}
Категория: ${request.category}
Получатель: ${request.recipient}
Сумма: ${request.amountRub} ₽
Способ оплаты: ${request.paymentMethod}
Реквизиты: ${request.paymentDetails}
Назначение: ${request.purpose}
Статус: ${request.status}
    `.trim();

    const buttons = [];

    if (request.status === RequestStatus.CREATED) {
      buttons.push([Markup.button.callback('✅ Одобрить', `approve_${request.externalId}`)]);
      buttons.push([Markup.button.callback('❌ Отклонить', `reject_${request.externalId}`)]);
      buttons.push([Markup.button.callback('💬 Уточнить', `ask_${request.externalId}`)]);
    }

    buttons.push([Markup.button.callback('« Назад к списку', 'back_to_approvals')]);

    await ctx.editMessageText(message, Markup.inlineKeyboard(buttons));
  });

  // Одобрение заявки
  bot.action(/^approve_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    const user = (ctx as any).user;

    if (user.role !== UserRole.OWNER) {
      await ctx.answer('⛔ Только владелец может одобрять заявки');
      return;
    }

    // Получаем список кошельков
    const wallets = await sheetsService.getWalletBalances();

    if (wallets.length === 0) {
      await ctx.answer('❌ Нет доступных кошельков');
      return;
    }

    // Сохраняем состояние
    approvalStates.set(ctx.from!.id, { requestId, action: 'approve' });

    const message = `Выберите кошелек для списания:`;

    const buttons = wallets.map((wallet) => [
      Markup.button.callback(
        `${wallet.name} (${wallet.balanceUsdt.toFixed(2)} USDT)`,
        `select_wallet_${wallet.name}`
      ),
    ]);

    buttons.push([Markup.button.callback('❌ Отменить', 'cancel_approval')]);

    await ctx.editMessageText(message, Markup.inlineKeyboard(buttons));
  });

  // Выбор кошелька
  bot.action(/^select_wallet_(.+)$/, async (ctx: Context) => {
    const walletName = (ctx as any).match[1];
    const state = approvalStates.get(ctx.from!.id);
    const user = (ctx as any).user;

    if (!state) {
      await ctx.answer('❌ Данные не найдены');
      return;
    }

    try {
      // Одобряем заявку
      await requestService.approveRequest(
        state.requestId,
        user.id,
        walletName,
        `@${ctx.from!.username || ctx.from!.id}`
      );

      // Логируем действие
      await userService.logAction(
        user.id,
        'approve_request',
        'request',
        null,
        { requestId: state.requestId, wallet: walletName }
      );

      // Очищаем состояние
      approvalStates.delete(ctx.from!.id);

      // Получаем данные заявки для уведомления
      const request = await requestService.getRequestById(state.requestId);

      await ctx.editMessageText(
        `✅ Заявка #${state.requestId} одобрена!\n\n` +
        `Кошелек: ${walletName}\n` +
        `Сумма: ${request?.amountRub} ₽\n\n` +
        `Оплатители получили уведомление.`
      );

      // Уведомляем оплатителей
      await notifyExecutors(ctx, request!);

      // Уведомляем автора заявки
      if (request) {
        const author = await userService.getUserByTelegramId(request.authorId);
        if (author) {
          await bot.telegram.sendMessage(
            author.telegramId,
            `✅ Ваша заявка #${request.externalId} одобрена!\n\n` +
            `Кошелек: ${walletName}\n` +
            `Статус: Ожидает оплаты`
          );
        }
      }
    } catch (error) {
      console.error('Error approving request:', error);
      await ctx.answer('❌ Ошибка при одобрении заявки');
    }
  });

  // Отклонение заявки
  bot.action(/^reject_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    const user = (ctx as any).user;

    if (user.role !== UserRole.OWNER) {
      await ctx.answer('⛔ Только владелец может отклонять заявки');
      return;
    }

    // Сохраняем состояние
    approvalStates.set(ctx.from!.id, { requestId, action: 'reject' });

    await ctx.editMessageText('Укажите причину отклонения:');
  });

  // Обработка причины отклонения
  bot.on('text', async (ctx: Context) => {
    const state = approvalStates.get(ctx.from!.id);

    if (state && state.action === 'reject') {
      const reason = (ctx as any).message.text;
      const user = (ctx as any).user;

      try {
        await requestService.rejectRequest(state.requestId, user.id, reason);

        // Логируем действие
        await userService.logAction(
          user.id,
          'reject_request',
          'request',
          null,
          { requestId: state.requestId, reason }
        );

        // Очищаем состояние
        approvalStates.delete(ctx.from!.id);

        // Получаем данные заявки
        const request = await requestService.getRequestById(state.requestId);

        await ctx.reply(
          `❌ Заявка #${state.requestId} отклонена.\n\nПричина: ${reason}`
        );

        // Уведомляем автора
        if (request) {
          const author = await userService.getUserByTelegramId(request.authorId);
          if (author) {
            await bot.telegram.sendMessage(
              author.telegramId,
              `❌ Ваша заявка #${request.externalId} отклонена.\n\n` +
              `Причина: ${reason}`
            );
          }
        }
      } catch (error) {
        console.error('Error rejecting request:', error);
        await ctx.reply('❌ Ошибка при отклонении заявки');
      }
    }
  });

  // Уточнение по заявке
  bot.action(/^ask_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    const user = (ctx as any).user;

    if (user.role !== UserRole.OWNER) {
      await ctx.answer('⛔ Только владелец может задавать вопросы');
      return;
    }

    // Сохраняем состояние
    approvalStates.set(ctx.from!.id, { requestId, action: 'ask' });

    await ctx.editMessageText('Напишите вопрос автору заявки:');
  });

  // Обработка вопроса
  bot.on('text', async (ctx: Context) => {
    const state = approvalStates.get(ctx.from!.id);

    if (state && state.action === 'ask') {
      const question = (ctx as any).message.text;
      const user = (ctx as any).user;

      try {
        // Получаем данные заявки
        const request = await requestService.getRequestById(state.requestId);

        if (!request) {
          await ctx.reply('❌ Заявка не найдена');
          return;
        }

        // Очищаем состояние
        approvalStates.delete(ctx.from!.id);

        await ctx.reply(`💬 Вопрос отправлен автору заявки #${state.requestId}`);

        // Отправляем вопрос автору
        const author = await userService.getUserByTelegramId(request.authorId);
        if (author) {
          await bot.telegram.sendMessage(
            author.telegramId,
            `💬 Вопрос по заявке #${request.externalId} (${request.category}, ${request.amountRub}₽):\n\n` +
            `${question}\n\n` +
            `Ответьте на это сообщение для отправки ответа.`,
            Markup.inlineKeyboard([
              [Markup.button.callback('Ответить', `reply_${request.externalId}`)],
            ])
          );
        }
      } catch (error) {
        console.error('Error asking question:', error);
        await ctx.reply('❌ Ошибка при отправке вопроса');
      }
    }
  });

  // Отмена действия
  bot.action('cancel_approval', async (ctx: Context) => {
    approvalStates.delete(ctx.from!.id);
    await ctx.editMessageText('❌ Действие отменено');
  });

  // Возврат к списку заявок
  bot.action('back_to_approvals', async (ctx: Context) => {
    // Перезапускаем команду
    (ctx as any).command = { command: 'pending_approvals' };
    bot.command('pending_approvals')(ctx);
  });

  // Команда просмотра балансов
  bot.command('balance', async (ctx: Context) => {
    const user = (ctx as any).user;

    if (![UserRole.OWNER, UserRole.EXECUTOR].includes(user.role)) {
      await ctx.reply('⛔ У вас нет доступа к балансам кошельков');
      return;
    }

    const wallets = await sheetsService.getWalletBalances();

    if (wallets.length === 0) {
      await ctx.reply('Нет данных о кошельках');
      return;
    }

    let message = '💰 Балансы кошельков:\n\n';

    const companies: Record<string, any[]> = {};

    wallets.forEach((wallet) => {
      if (!companies[wallet.company]) {
        companies[wallet.company] = [];
      }
      companies[wallet.company].push(wallet);
    });

    for (const [company, companyWallets] of Object.entries(companies)) {
      message += `📊 ${company}\n`;

      let totalUsdt = 0;

      for (const wallet of companyWallets) {
        message += `  ${wallet.name}: ${wallet.balanceUsdt.toFixed(2)} USDT\n`;
        totalUsdt += wallet.balanceUsdt;
      }

      message += `  ───────\n`;
      message += `  Итого: ${totalUsdt.toFixed(2)} USDT\n\n`;
    }

    // Общий баланс
    const totalUsdt = wallets.reduce((sum, w) => sum + w.balanceUsdt, 0);
    message += `💼 ОБЩИЙ БАЛАНС: ${totalUsdt.toFixed(2)} USDT\n`;
    message += `≈ ${(totalUsdt * 73.5).toFixed(0)} ₽ (курс 73.5)`;

    await ctx.reply(message.trim());
  });
}

// Уведомление оплатителей о новой одобренной заявке
async function notifyExecutors(ctx: Context, request: any) {
  const { bot } = await import('./index');
  const executors = await userService.getAllUsers();

  const executorUsers = executors.filter((u) => u.role === UserRole.EXECUTOR);

  for (const executor of executorUsers) {
    try {
      await bot.telegram.sendMessage(
        executor.telegramId,
        `🔔 Новая заявка на оплату #${request.externalId}\n\n` +
        `Компания: ${request.company}\n` +
        `Категория: ${request.category}\n` +
        `Получатель: ${request.recipient}\n` +
        `Сумма: ${request.amountRub} ₽\n` +
        `Способ оплаты: ${request.paymentMethod}\n` +
        `Кошелек: ${request.wallet}\n\n` +
        `Используйте /pending_payments для просмотра`
      );
    } catch (error) {
      console.error(`Error notifying executor ${executor.telegramId}:`, error);
    }
  }
}
