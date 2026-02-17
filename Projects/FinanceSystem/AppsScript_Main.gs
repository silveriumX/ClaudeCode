// Google Apps Script для фильтрации заявок по компании
// Добавьте этот код в Extensions → Apps Script главной таблицы

// Создание персонализированных представлений
function createCompanyFilters() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Заявки');

  if (!sheet) {
    SpreadsheetApp.getUi().alert('Лист "Заявки" не найден');
    return;
  }

  // Получаем уникальные компании
  const data = sheet.getRange(2, 4, sheet.getLastRow() - 1, 1).getValues(); // Колонка D (Компания)
  const companies = [...new Set(data.flat().filter(c => c))];

  SpreadsheetApp.getUi().alert(
    `Найдено компаний: ${companies.length}\n\n${companies.join('\n')}\n\n` +
    `Используйте встроенные фильтры Google Sheets для фильтрации по компании.`
  );
}

// Функция для автоматического применения фильтра по пользователю
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('🏢 Компании')
      .addItem('Показать список компаний', 'createCompanyFilters')
      .addItem('Сбросить фильтры', 'clearFilters')
      .addSeparator()
      .addItem('Мои заявки', 'filterMyRequests')
      .addToUi();
}

// Сброс всех фильтров
function clearFilters() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Заявки');

  if (!sheet) return;

  // Удаляем существующий фильтр
  const filter = sheet.getFilter();
  if (filter) {
    filter.remove();
  }

  SpreadsheetApp.getUi().alert('✅ Фильтры сброшены');
}

// Фильтр "Мои заявки"
function filterMyRequests() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Заявки');

  if (!sheet) return;

  const userEmail = Session.getActiveUser().getEmail();

  // Удаляем существующий фильтр
  let filter = sheet.getFilter();
  if (filter) {
    filter.remove();
  }

  // Создаем новый фильтр
  const dataRange = sheet.getDataRange();
  filter = dataRange.createFilter();

  // Применяем фильтр к колонке C (Автор)
  const criteria = SpreadsheetApp.newFilterCriteria()
    .whenTextContains(userEmail)
    .build();
  filter.setColumnFilterCriteria(3, criteria);

  SpreadsheetApp.getUi().alert(`✅ Показаны только ваши заявки (${userEmail})`);
}

// Функция для создания отчета по компании
function generateCompanyReport() {
  const ui = SpreadsheetApp.getUi();
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Заявки');

  if (!sheet) {
    ui.alert('Лист "Заявки" не найден');
    return;
  }

  // Запрашиваем название компании
  const response = ui.prompt(
    'Отчет по компании',
    'Введите название компании:',
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() !== ui.Button.OK) return;

  const companyName = response.getResponseText();

  // Получаем данные
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const rows = data.slice(1);

  // Фильтруем по компании
  const companyRows = rows.filter(row => row[3] === companyName);

  if (companyRows.length === 0) {
    ui.alert(`Заявок для компании "${companyName}" не найдено`);
    return;
  }

  // Подсчитываем статистику
  const totalAmount = companyRows.reduce((sum, row) => sum + (parseFloat(row[6]) || 0), 0);
  const createdCount = companyRows.filter(row => row[11] === 'Создана').length;
  const approvedCount = companyRows.filter(row => row[11] === 'Одобрена').length;
  const paidCount = companyRows.filter(row => row[11] === 'Оплачена').length;

  // Показываем отчет
  ui.alert(
    `📊 Отчет по ${companyName}\n\n` +
    `Всего заявок: ${companyRows.length}\n` +
    `Создано: ${createdCount}\n` +
    `Одобрено: ${approvedCount}\n` +
    `Оплачено: ${paidCount}\n\n` +
    `Общая сумма: ${totalAmount.toFixed(2)} ₽`
  );
}

// Функция защиты данных от случайного удаления
function protectCriticalColumns() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Заявки');

  if (!sheet) return;

  // Защищаем колонки A, B, C (ID, Дата создания, Автор)
  const range1 = sheet.getRange('A2:C1000');
  const protection1 = range1.protect().setDescription('Системные данные');
  protection1.setWarningOnly(false);

  // Защищаем колонки L-S (Статусы и результаты)
  const range2 = sheet.getRange('L2:S1000');
  const protection2 = range2.protect().setDescription('Данные заполняются системой');
  protection2.setWarningOnly(false);

  // Даем доступ только владельцу
  const me = Session.getEffectiveUser();
  [protection1, protection2].forEach(p => {
    p.addEditor(me);
    p.removeEditors(p.getEditors());
    if (p.canDomainEdit()) {
      p.setDomainEdit(false);
    }
  });
}
