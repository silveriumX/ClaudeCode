import { Context, Markup } from 'telegraf';
import { RequestService } from '../services/requestService';
import { UserService } from '../services/userService';
import { UserRole, Category, PaymentMethod, Urgency } from '../types';
import { config } from '../config';

const requestService = new RequestService();
const userService = new UserService();

// Хранилище состояний для групповых заявок
const bulkRequestStates = new Map<number, any>();

export function registerSpecialRoleCommands(bot: any) {
  // Команда Manager+: оплатить свою заявку
  bot.command('pay_my_request', async (ctx: Context) => {
    const user = (ctx as any).user;

    if (user.role !== UserRole.MANAGER_PLUS) {
      await ctx.reply('⛔ Эта команда доступна только для роли Менеджер+');
      return;
    }

    const args = (ctx as any).message.text.split(' ');

    if (args.length < 2) {
      await ctx.reply('Использование: /pay_my_request [ID заявки]\n\nПример: /pay_my_request REQ-1234567890');
      return;
    }

    const requestId = args[1];
    const request = await requestService.getRequestById(requestId);

    if (!request) {
      await ctx.reply('❌ Заявка не найдена');
      return;
    }

    // Проверяем, что это заявка пользователя
    if (request.authorId !== user.id) {
      await ctx.reply('❌ Вы можете оплачивать только свои заявки');
      return;
    }

    // Проверяем статус
    if (request.status !== 'Одобрена') {
      await ctx.reply('❌ Заявка должна быть одобрена владельцем');
      return;
    }

    // Проверяем лимит
    if (request.amountRub > config.limits.managerPlusLimit) {
      await ctx.reply(
        `❌ Сумма заявки (${request.amountRub}₽) превышает ваш лимит (${config.limits.managerPlusLimit}₽).\n\n` +
        `Эту заявку должен оплатить оплатитель.`
      );
      return;
    }

    await ctx.reply(
      `💰 Оплата заявки #${requestId}\n\n` +
      `Сумма: ${request.amountRub} ₽\n` +
      `Получатель: ${request.recipient}\n` +
      `Способ: ${request.paymentMethod}\n` +
      `Реквизиты: ${request.paymentDetails}\n` +
      `Кошелек: ${request.wallet}\n\n` +
      `После проведения оплаты введите курс USDT/RUB:`,
      Markup.inlineKeyboard([[Markup.button.callback('❌ Отменить', 'cancel_manager_payment')]])
    );

    // Сохраняем состояние (используем тот же механизм что и у Executor)
    const paymentStates = new Map<number, any>();
    paymentStates.set(ctx.from!.id, { requestId, request });
  });

  // Команда Buyer: создать групповую заявку
  bot.command('new_bulk_request', async (ctx: Context) => {
    const user = (ctx as any).user;

    if (user.role !== UserRole.BUYER) {
      await ctx.reply('⛔ Эта команда доступна только для выкупщиков');
      return;
    }

    // Инициализируем состояние
    bulkRequestStates.set(ctx.from!.id, { step: 'company' });

    await ctx.reply(
      '📦 Создание групповой заявки на выкуп\n\nВыберите компанию:',
      Markup.inlineKeyboard([
        [Markup.button.callback('ООО Альфа', 'bulk_company_alfa')],
        [Markup.button.callback('ООО Бета', 'bulk_company_beta')],
        [Markup.button.callback('ИП Иванов', 'bulk_company_ivanov')],
        [Markup.button.callback('❌ Отменить', 'cancel_bulk_request')],
      ])
    );
  });

  // Обработка выбора компании для групповой заявки
  bot.action(/^bulk_company_(.+)$/, async (ctx: Context) => {
    const company = (ctx as any).match[1];
    const state = bulkRequestStates.get(ctx.from!.id);

    if (!state) return;

    const companyNames: Record<string, string> = {
      alfa: 'ООО Альфа',
      beta: 'ООО Бета',
      ivanov: 'ИП Иванов',
    };

    state.company = companyNames[company];
    state.step = 'marketplace';

    await ctx.editMessageText(
      `Компания: ${state.company}\n\nВыберите маркетплейс:`,
      Markup.inlineKeyboard([
        [Markup.button.callback('Wildberries', 'bulk_mp_wb')],
        [Markup.button.callback('Ozon', 'bulk_mp_ozon')],
        [Markup.button.callback('Яндекс.Маркет', 'bulk_mp_yandex')],
        [Markup.button.callback('Другой', 'bulk_mp_other')],
        [Markup.button.callback('« Назад', 'back_to_bulk_company')],
      ])
    );
  });

  // Обработка выбора маркетплейса
  bot.action(/^bulk_mp_(.+)$/, async (ctx: Context) => {
    const marketplace = (ctx as any).match[1];
    const state = bulkRequestStates.get(ctx.from!.id);

    if (!state) return;

    const marketplaceNames: Record<string, string> = {
      wb: 'Wildberries',
      ozon: 'Ozon',
      yandex: 'Яндекс.Маркет',
      other: 'Другой',
    };

    state.marketplace = marketplaceNames[marketplace];
    state.step = 'order_count';

    await ctx.editMessageText(
      `Маркетплейс: ${state.marketplace}\n\nУкажите количество выкупленных заказов:`
    );
  });

  // Обработка текстового ввода для групповой заявки
  bot.on('text', async (ctx: Context, next: any) => {
    const state = bulkRequestStates.get(ctx.from!.id);
    if (!state) return next();

    const text = (ctx as any).message.text;

    switch (state.step) {
      case 'order_count':
        const count = parseInt(text);
        if (isNaN(count) || count <= 0) {
          await ctx.reply('❌ Неверное количество. Введите число больше 0:');
          return;
        }
        state.orderCount = count;
        state.step = 'total_amount';
        await ctx.reply(
          `Количество заказов: ${count}\n\nУкажите общую сумму в рублях:`,
          Markup.inlineKeyboard([[Markup.button.callback('❌ Отменить', 'cancel_bulk_request')]])
        );
        break;

      case 'total_amount':
        const amount = parseFloat(text);
        if (isNaN(amount) || amount <= 0) {
          await ctx.reply('❌ Неверная сумма. Введите число больше 0:');
          return;
        }
        state.totalAmount = amount;
        state.step = 'payment_method';
        await ctx.reply(
          `Общая сумма: ${amount} ₽\n\nВыберите способ компенсации:`,
          Markup.inlineKeyboard([
            [Markup.button.callback('💳 Карта', 'bulk_payment_card')],
            [Markup.button.callback('💵 Наличные', 'bulk_payment_cash')],
            [Markup.button.callback('₿ Крипта', 'bulk_payment_crypto')],
            [Markup.button.callback('❌ Отменить', 'cancel_bulk_request')],
          ])
        );
        break;

      case 'payment_details':
        state.paymentDetails = text;
        state.step = 'confirmation';

        // Показываем итоговую заявку
        const summary = `
📦 Проверьте данные групповой заявки:

Компания: ${state.company}
Маркетплейс: ${state.marketplace}
Количество заказов: ${state.orderCount}
Общая сумма: ${state.totalAmount} ₽
Средняя сумма заказа: ${(state.totalAmount / state.orderCount).toFixed(2)} ₽
Способ компенсации: ${state.paymentMethod}
Реквизиты: ${state.paymentDetails}
        `.trim();

        await ctx.reply(
          summary,
          Markup.inlineKeyboard([
            [Markup.button.callback('✅ Создать заявку', 'confirm_bulk_request')],
            [Markup.button.callback('❌ Отменить', 'cancel_bulk_request')],
          ])
        );
        break;
    }
  });

  // Обработка выбора способа оплаты для групповой заявки
  bot.action(/^bulk_payment_(.+)$/, async (ctx: Context) => {
    const method = (ctx as any).match[1];
    const state = bulkRequestStates.get(ctx.from!.id);

    if (!state) return;

    const methodNames: Record<string, PaymentMethod> = {
      card: PaymentMethod.CARD,
      cash: PaymentMethod.CASH,
      crypto: PaymentMethod.CRYPTO,
    };

    state.paymentMethod = methodNames[method];
    state.step = 'payment_details';

    await ctx.editMessageText(
      `Способ компенсации: ${state.paymentMethod}\n\nУкажите реквизиты (номер карты/кошелька):`
    );
  });

  // Подтверждение создания групповой заявки
  bot.action('confirm_bulk_request', async (ctx: Context) => {
    const state = bulkRequestStates.get(ctx.from!.id);
    const user = (ctx as any).user;

    if (!state) {
      await ctx.answer('❌ Данные заявки не найдены');
      return;
    }

    try {
      // Создаем заявку
      const request = await requestService.createRequest({
        authorId: user.id,
        authorUsername: `@${ctx.from!.username || ctx.from!.id}`,
        company: state.company,
        category: Category.OTHER,
        recipient: `@${ctx.from!.username || ctx.from!.id}`,
        amountRub: state.totalAmount,
        paymentMethod: state.paymentMethod,
        paymentDetails: state.paymentDetails,
        purpose: `Выкуп ${state.orderCount} заказов на ${state.marketplace}`,
        urgency: Urgency.NORMAL,
      });

      // Логируем действие
      await userService.logAction(
        user.id,
        'create_bulk_request',
        'request',
        request.id,
        {
          requestId: request.externalId,
          marketplace: state.marketplace,
          orderCount: state.orderCount
        }
      );

      // Очищаем состояние
      bulkRequestStates.delete(ctx.from!.id);

      await ctx.editMessageText(
        `✅ Групповая заявка создана!\n\n` +
        `ID: ${request.externalId}\n` +
        `Заказов: ${state.orderCount}\n` +
        `Сумма: ${request.amountRub} ₽\n` +
        `Статус: Ожидает одобрения\n\n` +
        `Владелец получил уведомление.`
      );

    } catch (error) {
      console.error('Error creating bulk request:', error);
      await ctx.answer('❌ Ошибка при создании заявки');
    }
  });

  // Отмена создания групповой заявки
  bot.action('cancel_bulk_request', async (ctx: Context) => {
    bulkRequestStates.delete(ctx.from!.id);
    await ctx.editMessageText('❌ Создание групповой заявки отменено');
  });

  // Команда Payroll: статус зарплат
  bot.command('payroll_status', async (ctx: Context) => {
    const user = (ctx as any).user;

    if (user.role !== UserRole.PAYROLL) {
      await ctx.reply('⛔ Эта команда доступна только для зарплатного специалиста');
      return;
    }

    // Получаем заявки категории "Зарплата"
    const requests = await requestService.getPendingApprovals();
    const payrollRequests = requests.filter(r => r.category === Category.SALARY);

    if (payrollRequests.length === 0) {
      await ctx.reply('Нет зарплатных заявок, ожидающих одобрения');
      return;
    }

    let message = '💰 Зарплатные заявки:\n\n';

    for (const req of payrollRequests) {
      message += `#${req.externalId}\n`;
      message += `Сумма: ${req.amountRub} ₽\n`;
      message += `Назначение: ${req.purpose}\n`;
      message += `Статус: ${req.status}\n\n`;
    }

    await ctx.reply(message.trim());
  });
}
