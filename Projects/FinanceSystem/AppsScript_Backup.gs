// Google Apps Script для автоматического backup
// Добавьте в Extensions → Apps Script главной таблицы

// Настройки
const BACKUP_FOLDER_ID = 'YOUR_BACKUP_FOLDER_ID'; // ID папки для бэкапов в Google Drive
const BACKUP_FREQUENCY = 'WEEKLY'; // DAILY или WEEKLY

// Функция создания бэкапа
function createBackup() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const backupFolder = DriveApp.getFolderById(BACKUP_FOLDER_ID);

    // Создаем копию таблицы
    const timestamp = Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd_HH-mm');
    const backupName = `Финансы_Backup_${timestamp}`;

    const file = DriveApp.getFileById(ss.getId());
    const backup = file.makeCopy(backupName, backupFolder);

    // Отправляем уведомление владельцу
    const ownerEmail = Session.getEffectiveUser().getEmail();
    MailApp.sendEmail({
      to: ownerEmail,
      subject: '✅ Backup финансовой системы создан',
      body: `Резервная копия таблицы создана успешно.\n\n` +
            `Название: ${backupName}\n` +
            `Ссылка: ${backup.getUrl()}\n` +
            `Дата: ${new Date().toLocaleString('ru-RU')}\n\n` +
            `Копия сохранена в папку Backup.`
    });

    Logger.log(`Backup created: ${backupName}`);

    // Очищаем старые бэкапы (старше 30 дней)
    cleanOldBackups();

  } catch (error) {
    Logger.log(`Error creating backup: ${error}`);

    // Отправляем уведомление об ошибке
    const ownerEmail = Session.getEffectiveUser().getEmail();
    MailApp.sendEmail({
      to: ownerEmail,
      subject: '❌ Ошибка создания backup финансовой системы',
      body: `Не удалось создать резервную копию.\n\n` +
            `Ошибка: ${error.toString()}\n` +
            `Дата: ${new Date().toLocaleString('ru-RU')}\n\n` +
            `Пожалуйста, проверьте настройки.`
    });
  }
}

// Функция очистки старых бэкапов
function cleanOldBackups() {
  try {
    const backupFolder = DriveApp.getFolderById(BACKUP_FOLDER_ID);
    const files = backupFolder.getFiles();
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

    let deletedCount = 0;

    while (files.hasNext()) {
      const file = files.next();
      const created = file.getDateCreated();

      if (created < thirtyDaysAgo) {
        file.setTrashed(true);
        deletedCount++;
      }
    }

    if (deletedCount > 0) {
      Logger.log(`Deleted ${deletedCount} old backups`);
    }

  } catch (error) {
    Logger.log(`Error cleaning old backups: ${error}`);
  }
}

// Функция настройки триггера
function setupBackupTrigger() {
  // Удаляем существующие триггеры
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'createBackup') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  // Создаем новый триггер
  if (BACKUP_FREQUENCY === 'DAILY') {
    // Ежедневно в 2:00 ночи
    ScriptApp.newTrigger('createBackup')
      .timeBased()
      .atHour(2)
      .everyDays(1)
      .create();
  } else if (BACKUP_FREQUENCY === 'WEEKLY') {
    // Каждое воскресенье в 2:00 ночи
    ScriptApp.newTrigger('createBackup')
      .timeBased()
      .onWeekDay(ScriptApp.WeekDay.SUNDAY)
      .atHour(2)
      .create();
  }

  SpreadsheetApp.getUi().alert(
    `✅ Триггер backup настроен!\n\n` +
    `Частота: ${BACKUP_FREQUENCY === 'DAILY' ? 'Ежедневно' : 'Еженедельно'}\n` +
    `Время: 02:00\n\n` +
    `Старые бэкапы (>30 дней) будут автоматически удаляться.`
  );
}

// Функция восстановления из бэкапа
function restoreFromBackup() {
  const ui = SpreadsheetApp.getUi();

  const response = ui.alert(
    'Восстановление из backup',
    '⚠️ ВНИМАНИЕ!\n\n' +
    'Восстановление из backup заменит текущие данные.\n' +
    'Текущая таблица будет сохранена как "Перед восстановлением".\n\n' +
    'Продолжить?',
    ui.ButtonSet.YES_NO
  );

  if (response !== ui.Button.YES) {
    ui.alert('Операция отменена');
    return;
  }

  // Создаем копию текущей таблицы
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const file = DriveApp.getFileById(ss.getId());
  const timestamp = Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd_HH-mm');
  file.makeCopy(`Финансы_Перед_Восстановлением_${timestamp}`);

  ui.alert(
    '✅ Текущая версия сохранена!\n\n' +
    `Название: Финансы_Перед_Восстановлением_${timestamp}\n\n` +
    'Теперь откройте нужный backup из папки Backup и скопируйте данные вручную.'
  );
}

// Функция экспорта данных в CSV
function exportToCSV() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Заявки');

  if (!sheet) {
    SpreadsheetApp.getUi().alert('Лист "Заявки" не найден');
    return;
  }

  // Получаем данные
  const data = sheet.getDataRange().getValues();
  let csv = '';

  data.forEach(row => {
    csv += row.map(cell => `"${cell}"`).join(',') + '\n';
  });

  // Создаем файл
  const timestamp = Utilities.formatDate(new Date(), 'Europe/Moscow', 'yyyy-MM-dd');
  const fileName = `Заявки_Экспорт_${timestamp}.csv`;

  const backupFolder = DriveApp.getFolderById(BACKUP_FOLDER_ID);
  const file = backupFolder.createFile(fileName, csv, MimeType.CSV);

  SpreadsheetApp.getUi().alert(
    `✅ Экспорт завершен!\n\n` +
    `Файл: ${fileName}\n` +
    `Ссылка: ${file.getUrl()}`
  );
}

// Меню
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('💾 Backup')
      .addItem('Создать backup сейчас', 'createBackup')
      .addItem('Настроить автоматический backup', 'setupBackupTrigger')
      .addItem('Восстановить из backup', 'restoreFromBackup')
      .addSeparator()
      .addItem('Экспорт в CSV', 'exportToCSV')
      .addToUi();
}

// Функция проверки целостности данных
function checkDataIntegrity() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('Заявки');

  if (!sheet) return;

  const data = sheet.getRange(2, 1, sheet.getLastRow() - 1, 20).getValues();

  let errors = [];

  data.forEach((row, index) => {
    const rowNum = index + 2;

    // Проверка ID
    if (!row[0]) {
      errors.push(`Строка ${rowNum}: Отсутствует ID`);
    }

    // Проверка суммы
    if (!row[6] || row[6] <= 0) {
      errors.push(`Строка ${rowNum}: Неверная сумма`);
    }

    // Проверка статуса
    const validStatuses = ['Создана', 'Одобрена', 'В работе', 'Оплачена', 'Отклонена'];
    if (!validStatuses.includes(row[11])) {
      errors.push(`Строка ${rowNum}: Неверный статус "${row[11]}"`);
    }

    // Проверка формулы USDT
    if (row[11] === 'Оплачена' && row[17] && !row[18]) {
      errors.push(`Строка ${rowNum}: Не рассчитана сумма USDT`);
    }
  });

  if (errors.length === 0) {
    SpreadsheetApp.getUi().alert('✅ Проверка целостности: ошибок не найдено');
  } else {
    SpreadsheetApp.getUi().alert(
      `⚠️ Найдено ошибок: ${errors.length}\n\n` +
      errors.slice(0, 10).join('\n') +
      (errors.length > 10 ? `\n\n... и еще ${errors.length - 10}` : '')
    );
  }
}
