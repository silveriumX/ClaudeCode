import { Context, Markup } from 'telegraf';
import { RequestService } from '../services/requestService';
import { UserService } from '../services/userService';
import { Category, PaymentMethod, Urgency, UserRole } from '../types';

const requestService = new RequestService();
const userService = new UserService();

// Хранилище состояний создания заявки (в продакшене использовать Redis)
const requestStates = new Map<number, any>();

export function registerRequestCommands(bot: any) {
  // Команда создания заявки
  bot.command('new_request', async (ctx: Context) => {
    const user = (ctx as any).user;

    // Проверяем роль
    if (![UserRole.MANAGER, UserRole.MANAGER_PLUS, UserRole.BUYER].includes(user.role)) {
      await ctx.reply('⛔ У вас нет прав на создание заявок');
      return;
    }

    // Инициализируем состояние
    requestStates.set(ctx.from!.id, { step: 'company' });

    await ctx.reply(
      '📝 Создание новой заявки\n\nВыберите компанию:',
      Markup.inlineKeyboard([
        [Markup.button.callback('ООО Альфа', 'company_alfa')],
        [Markup.button.callback('ООО Бета', 'company_beta')],
        [Markup.button.callback('ИП Иванов', 'company_ivanov')],
        [Markup.button.callback('❌ Отменить', 'cancel_request')],
      ])
    );
  });

  // Обработка выбора компании
  bot.action(/^company_(.+)$/, async (ctx: Context) => {
    const company = (ctx as any).match[1];
    const state = requestStates.get(ctx.from!.id);

    if (!state) return;

    const companyNames: Record<string, string> = {
      alfa: 'ООО Альфа',
      beta: 'ООО Бета',
      ivanov: 'ИП Иванов',
    };

    state.company = companyNames[company];
    state.step = 'category';

    await ctx.editMessageText(
      `Компания: ${state.company}\n\nВыберите категорию платежа:`,
      Markup.inlineKeyboard([
        [Markup.button.callback('💰 Зарплата', 'category_salary')],
        [Markup.button.callback('📦 Поставщик', 'category_supplier')],
        [Markup.button.callback('📢 Маркетинг', 'category_marketing')],
        [Markup.button.callback('🚚 Логистика', 'category_logistics')],
        [Markup.button.callback('🏢 Офис', 'category_office')],
        [Markup.button.callback('📋 Прочее', 'category_other')],
        [Markup.button.callback('« Назад', 'back_to_company')],
      ])
    );
  });

  // Обработка выбора категории
  bot.action(/^category_(.+)$/, async (ctx: Context) => {
    const category = (ctx as any).match[1];
    const state = requestStates.get(ctx.from!.id);

    if (!state) return;

    const categoryNames: Record<string, Category> = {
      salary: Category.SALARY,
      supplier: Category.SUPPLIER,
      marketing: Category.MARKETING,
      logistics: Category.LOGISTICS,
      office: Category.OFFICE,
      other: Category.OTHER,
    };

    state.category = categoryNames[category];
    state.step = 'recipient';

    await ctx.editMessageText(
      `Компания: ${state.company}\nКатегория: ${state.category}\n\nУкажите получателя (ФИО или название):`
    );
  });

  // Обработка текстового ввода
  bot.on('text', async (ctx: Context) => {
    const state = requestStates.get(ctx.from!.id);
    if (!state) return;

    const text = (ctx as any).message.text;

    switch (state.step) {
      case 'recipient':
        state.recipient = text;
        state.step = 'amount';
        await ctx.reply(
          `Получатель: ${state.recipient}\n\nУкажите сумму в рублях (только число):`,
          Markup.inlineKeyboard([[Markup.button.callback('❌ Отменить', 'cancel_request')]])
        );
        break;

      case 'amount':
        const amount = parseFloat(text);
        if (isNaN(amount) || amount <= 0) {
          await ctx.reply('❌ Неверная сумма. Введите число больше 0:');
          return;
        }
        state.amountRub = amount;
        state.step = 'payment_method';
        await ctx.reply(
          `Сумма: ${amount} ₽\n\nВыберите способ оплаты:`,
          Markup.inlineKeyboard([
            [Markup.button.callback('💳 Карта', 'payment_card')],
            [Markup.button.callback('📱 СБП (QR)', 'payment_sbp')],
            [Markup.button.callback('☎️ Телефон', 'payment_phone')],
            [Markup.button.callback('💵 Наличные', 'payment_cash')],
            [Markup.button.callback('₿ Крипта', 'payment_crypto')],
            [Markup.button.callback('🇧🇾 BYN', 'payment_byn')],
            [Markup.button.callback('❌ Отменить', 'cancel_request')],
          ])
        );
        break;

      case 'payment_details':
        state.paymentDetails = text;
        state.step = 'purpose';
        await ctx.reply(
          `Реквизиты: ${text}\n\nУкажите назначение платежа:`,
          Markup.inlineKeyboard([[Markup.button.callback('❌ Отменить', 'cancel_request')]])
        );
        break;

      case 'purpose':
        state.purpose = text;
        state.step = 'urgency';
        await ctx.reply(
          `Назначение: ${text}\n\nВыберите срочность:`,
          Markup.inlineKeyboard([
            [Markup.button.callback('📅 Обычная', 'urgency_normal')],
            [Markup.button.callback('⚡ Срочная', 'urgency_urgent')],
            [Markup.button.callback('❌ Отменить', 'cancel_request')],
          ])
        );
        break;
    }
  });

  // Обработка выбора способа оплаты
  bot.action(/^payment_(.+)$/, async (ctx: Context) => {
    const method = (ctx as any).match[1];
    const state = requestStates.get(ctx.from!.id);

    if (!state) return;

    const methodNames: Record<string, PaymentMethod> = {
      card: PaymentMethod.CARD,
      sbp: PaymentMethod.SBP,
      phone: PaymentMethod.PHONE,
      cash: PaymentMethod.CASH,
      crypto: PaymentMethod.CRYPTO,
      byn: PaymentMethod.BYN,
    };

    state.paymentMethod = methodNames[method];
    state.step = 'payment_details';

    await ctx.editMessageText(
      `Способ оплаты: ${state.paymentMethod}\n\nУкажите реквизиты (номер карты/телефона/кошелька):`
    );
  });

  // Обработка выбора срочности
  bot.action(/^urgency_(.+)$/, async (ctx: Context) => {
    const urgency = (ctx as any).match[1];
    const state = requestStates.get(ctx.from!.id);

    if (!state) return;

    state.urgency = urgency === 'urgent' ? Urgency.URGENT : Urgency.NORMAL;

    // Показываем итоговую заявку
    const summary = `
📄 Проверьте данные заявки:

Компания: ${state.company}
Категория: ${state.category}
Получатель: ${state.recipient}
Сумма: ${state.amountRub} ₽
Способ оплаты: ${state.paymentMethod}
Реквизиты: ${state.paymentDetails}
Назначение: ${state.purpose}
Срочность: ${state.urgency === Urgency.URGENT ? '⚡ Срочная' : '📅 Обычная'}
    `.trim();

    await ctx.editMessageText(
      summary,
      Markup.inlineKeyboard([
        [Markup.button.callback('✅ Создать заявку', 'confirm_request')],
        [Markup.button.callback('✏️ Изменить', 'edit_request')],
        [Markup.button.callback('❌ Отменить', 'cancel_request')],
      ])
    );
  });

  // Подтверждение создания заявки
  bot.action('confirm_request', async (ctx: Context) => {
    const state = requestStates.get(ctx.from!.id);
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
        category: state.category,
        recipient: state.recipient,
        amountRub: state.amountRub,
        paymentMethod: state.paymentMethod,
        paymentDetails: state.paymentDetails,
        purpose: state.purpose,
        urgency: state.urgency,
      });

      // Логируем действие
      await userService.logAction(
        user.id,
        'create_request',
        'request',
        request.id,
        { requestId: request.externalId }
      );

      // Очищаем состояние
      requestStates.delete(ctx.from!.id);

      await ctx.editMessageText(
        `✅ Заявка создана!\n\n` +
        `ID: ${request.externalId}\n` +
        `Сумма: ${request.amountRub} ₽\n` +
        `Статус: Ожидает одобрения\n\n` +
        `Владелец получил уведомление.`
      );

      // Уведомляем владельца
      await notifyOwnerNewRequest(ctx, request, user);

    } catch (error) {
      console.error('Error creating request:', error);
      await ctx.answer('❌ Ошибка при создании заявки');
    }
  });

  // Отмена создания заявки
  bot.action('cancel_request', async (ctx: Context) => {
    requestStates.delete(ctx.from!.id);
    await ctx.editMessageText('❌ Создание заявки отменено');
  });

  // Команда просмотра своих заявок
  bot.command('my_requests', async (ctx: Context) => {
    const user = (ctx as any).user;

    const requests = await requestService.getRequestsByAuthor(user.id);

    if (requests.length === 0) {
      await ctx.reply('У вас пока нет заявок');
      return;
    }

    let message = '📋 Ваши заявки:\n\n';

    for (const req of requests) {
      const statusEmoji = getStatusEmoji(req.status);
      message += `${statusEmoji} ${req.externalId}\n`;
      message += `${req.category} - ${req.amountRub} ₽\n`;
      message += `Создана: ${req.createdAt.toLocaleDateString('ru-RU')}\n`;
      message += `Статус: ${req.status}\n\n`;
    }

    await ctx.reply(message.trim());
  });

  // Команда редактирования заявки
  bot.command('edit_request', async (ctx: Context) => {
    const user = (ctx as any).user;
    const args = (ctx as any).message.text.split(' ');

    if (args.length < 2) {
      await ctx.reply('Использование: /edit_request [ID заявки]\n\nПример: /edit_request REQ-1234567890');
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
      await ctx.reply('❌ Вы можете редактировать только свои заявки');
      return;
    }

    // Проверяем статус
    if (request.status !== RequestStatus.CREATED) {
      await ctx.reply('❌ Можно редактировать только заявки со статусом "Создана"');
      return;
    }

    // Показываем меню редактирования
    await ctx.reply(
      `📝 Редактирование заявки #${requestId}\n\n` +
      `Текущие данные:\n` +
      `Компания: ${request.company}\n` +
      `Категория: ${request.category}\n` +
      `Получатель: ${request.recipient}\n` +
      `Сумма: ${request.amountRub} ₽\n` +
      `Способ оплаты: ${request.paymentMethod}\n` +
      `Реквизиты: ${request.paymentDetails}\n` +
      `Назначение: ${request.purpose}\n\n` +
      `Что хотите изменить?`,
      Markup.inlineKeyboard([
        [Markup.button.callback('Получателя', `edit_recipient_${requestId}`)],
        [Markup.button.callback('Сумму', `edit_amount_${requestId}`)],
        [Markup.button.callback('Реквизиты', `edit_details_${requestId}`)],
        [Markup.button.callback('Назначение', `edit_purpose_${requestId}`)],
        [Markup.button.callback('🗑️ Отменить заявку', `cancel_req_${requestId}`)],
        [Markup.button.callback('« Закрыть', 'close_edit')],
      ])
    );
  });

  // Обработчики редактирования полей
  const editStates = new Map<number, any>();

  bot.action(/^edit_recipient_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    editStates.set(ctx.from!.id, { requestId, field: 'recipient' });
    await ctx.editMessageText(`Введите нового получателя:`);
  });

  bot.action(/^edit_amount_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    editStates.set(ctx.from!.id, { requestId, field: 'amount' });
    await ctx.editMessageText(`Введите новую сумму в рублях:`);
  });

  bot.action(/^edit_details_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    editStates.set(ctx.from!.id, { requestId, field: 'details' });
    await ctx.editMessageText(`Введите новые реквизиты:`);
  });

  bot.action(/^edit_purpose_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    editStates.set(ctx.from!.id, { requestId, field: 'purpose' });
    await ctx.editMessageText(`Введите новое назначение платежа:`);
  });

  // Обработка ввода при редактировании
  bot.on('text', async (ctx: Context, next: any) => {
    const editState = editStates.get(ctx.from!.id);

    if (editState) {
      const text = (ctx as any).message.text;
      const user = (ctx as any).user;

      try {
        let updateData: any = {};

        switch (editState.field) {
          case 'recipient':
            updateData.recipient = text;
            break;
          case 'amount':
            const amount = parseFloat(text);
            if (isNaN(amount) || amount <= 0) {
              await ctx.reply('❌ Неверная сумма. Введите число больше 0:');
              return;
            }
            updateData.amountRub = amount;
            break;
          case 'details':
            updateData.paymentDetails = text;
            break;
          case 'purpose':
            updateData.purpose = text;
            break;
        }

        await requestService.updateRequest(editState.requestId, updateData);

        // Логируем изменение
        await userService.logAction(
          user.id,
          'edit_request',
          'request',
          null,
          { requestId: editState.requestId, field: editState.field, newValue: text }
        );

        editStates.delete(ctx.from!.id);

        await ctx.reply(
          `✅ Заявка #${editState.requestId} обновлена!\n\n` +
          `Используйте /edit_request ${editState.requestId} для дальнейшего редактирования.`
        );
      } catch (error) {
        console.error('Error updating request:', error);
        await ctx.reply('❌ Ошибка при обновлении заявки');
      }

      return; // Прерываем обработку, чтобы не передавать в другие обработчики
    }

    return next();
  });

  // Отмена заявки
  bot.action(/^cancel_req_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    const user = (ctx as any).user;

    try {
      await requestService.rejectRequest(requestId, user.id, 'Отменена автором');

      await userService.logAction(
        user.id,
        'cancel_request',
        'request',
        null,
        { requestId }
      );

      await ctx.editMessageText(`🗑️ Заявка #${requestId} отменена`);
    } catch (error) {
      console.error('Error canceling request:', error);
      await ctx.answer('❌ Ошибка при отмене заявки');
    }
  });

  bot.action('close_edit', async (ctx: Context) => {
    await ctx.editMessageText('Редактирование завершено');
  });

  // Ответ на вопрос по заявке
  bot.action(/^reply_(.+)$/, async (ctx: Context) => {
    const requestId = (ctx as any).match[1];
    const replyStates = new Map<number, any>();
    replyStates.set(ctx.from!.id, { requestId, action: 'reply' });

    await ctx.editMessageText('Напишите ваш ответ:');
  });
}

// Уведомление владельца о новой заявке
async function notifyOwnerNewRequest(ctx: Context, request: any, author: any) {
  const { config } = await import('../config');
  const { bot } = await import('./index');

  const urgencyEmoji = request.urgency === Urgency.URGENT ? '⚡ ' : '';

  const message = `
${urgencyEmoji}🔔 Новая заявка #${request.externalId}

Автор: @${ctx.from!.username || ctx.from!.id}
Компания: ${request.company}
Категория: ${request.category}
Получатель: ${request.recipient}
Сумма: ${request.amountRub} ₽
Способ оплаты: ${request.paymentMethod}
Реквизиты: ${request.paymentDetails}
Назначение: ${request.purpose}
${request.urgency === Urgency.URGENT ? '⚡ СРОЧНАЯ' : ''}
  `.trim();

  await bot.telegram.sendMessage(
    config.telegram.ownerTelegramId,
    message,
    Markup.inlineKeyboard([
      [Markup.button.callback('✅ Одобрить', `approve_${request.externalId}`)],
      [Markup.button.callback('❌ Отклонить', `reject_${request.externalId}`)],
      [Markup.button.callback('💬 Уточнить', `ask_${request.externalId}`)],
    ])
  );
}

function getStatusEmoji(status: string): string {
  const emojis: Record<string, string> = {
    [String(RequestStatus.CREATED)]: '🟡',
    [String(RequestStatus.APPROVED)]: '🔵',
    [String(RequestStatus.PAID)]: '🟢',
    [String(RequestStatus.REJECTED)]: '🔴',
  };
  return emojis[status] || '⚪';
}
