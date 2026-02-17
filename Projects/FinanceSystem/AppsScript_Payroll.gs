// Google Apps Script для таблицы "Зарплаты - Реестр"
// Этот скрипт добавляется в Extensions → Apps Script

// ID главной таблицы (вставьте свой)
const MAIN_SPREADSHEET_ID = 'YOUR_MAIN_SPREADSHEET_ID';

// Функция создания заявки на зарплату
function createPayrollRequest() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Начисления сотрудников');

  if (!sheet) {
    SpreadsheetApp.getUi().alert('Лист "Начисления сотрудников" не найден');
    return;
  }

  // Получаем данные (начиная со 2 строки, пропускаем заголовок)
  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, 11).getValues();

  // Фильтруем пустые строки
  const employees = data.filter(row => row[0] && row[8] > 0); // ФИО и ИТОГО > 0

  if (employees.length === 0) {
    SpreadsheetApp.getUi().alert('Нет сотрудников с начислениями');
    return;
  }

  // Подсчитываем общую сумму
  const totalAmount = employees.reduce((sum, row) => sum + parseFloat(row[8]), 0);

  // Создаем ID заявки
  const requestId = 'PAYROLL-' + Date.now();

  // Формируем назначение
  const period = employees[0][2] || 'Текущий период';
  const purpose = `Зарплата ${employees.length} сотрудникам за ${period}`;

  // Получаем текущего пользователя
  const userEmail = Session.getActiveUser().getEmail();

  // Записываем в главную таблицу
  try {
    const mainSs = SpreadsheetApp.openById(MAIN_SPREADSHEET_ID);
    const mainSheet = mainSs.getSheetByName('Заявки');

    if (!mainSheet) {
      SpreadsheetApp.getUi().alert('Лист "Заявки" не найден в главной таблице');
      return;
    }

    // Добавляем строку
    const timestamp = new Date().toLocaleString('ru-RU');
    const row = [
      requestId,                    // ID
      timestamp,                    // Дата создания
      userEmail,                    // Автор
      'ООО Альфа',                 // Компания (или выбирать)
      'Зарплата',                  // Категория
      `${employees.length} сотрудников`, // Получатель
      totalAmount,                  // Сумма RUB
      'Карта',                      // Способ оплаты
      'Реестр в таблице зарплат',   // Реквизиты
      purpose,                      // Назначение
      '',                           // Кошелек списания
      'Создана',                    // Статус
      'Обычная',                    // Срочность
      '',                           // Одобрил
      '',                           // Дата одобрения
      '',                           // Оплатил
      '',                           // Дата оплаты
      '',                           // Курс
      '',                           // Сумма USDT
      `Ссылка на реестр: ${ss.getUrl()}` // Комментарии
    ];

    mainSheet.appendRow(row);

    SpreadsheetApp.getUi().alert(
      `✅ Заявка создана!\n\n` +
      `ID: ${requestId}\n` +
      `Сотрудников: ${employees.length}\n` +
      `Сумма: ${totalAmount} ₽\n\n` +
      `Заявка добавлена в главную таблицу и ожидает одобрения владельца.`
    );

  } catch (error) {
    SpreadsheetApp.getUi().alert('❌ Ошибка: ' + error.toString());
  }
}

// Функция добавления кнопки в меню
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('💰 Зарплаты')
      .addItem('Создать заявку на выплату', 'createPayrollRequest')
      .addItem('Обновить ИТОГО', 'recalculateTotal')
      .addToUi();
}

// Функция пересчета итоговых сумм
function recalculateTotal() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Начисления сотрудников');

  if (!sheet) {
    SpreadsheetApp.getUi().alert('Лист не найден');
    return;
  }

  const lastRow = sheet.getLastRow();

  // Обновляем формулы в колонке I (ИТОГО)
  for (let i = 2; i <= lastRow; i++) {
    const formula = `=SUM(D${i}:G${i})-H${i}`;
    sheet.getRange(i, 9).setFormula(formula);
  }

  SpreadsheetApp.getUi().alert('✅ Формулы обновлены');
}

// Функция защиты колонки ИТОГО
function protectTotalColumn() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Начисления сотрудников');

  if (!sheet) return;

  // Защищаем колонку I (ИТОГО к выплате)
  const range = sheet.getRange('I2:I1000');
  const protection = range.protect().setDescription('Формула ИТОГО');

  // Разрешаем редактирование только владельцу
  const me = Session.getEffectiveUser();
  protection.addEditor(me);
  protection.removeEditors(protection.getEditors());

  if (protection.canDomainEdit()) {
    protection.setDomainEdit(false);
  }
}
