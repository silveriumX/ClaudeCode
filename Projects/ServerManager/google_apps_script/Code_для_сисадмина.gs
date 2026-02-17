/**
 * =============================================================================
 * SERVER MONITORING SYSTEM - Версия для системного администратора
 * =============================================================================
 * Упрощённая версия с ограниченным доступом
 * Дата: 24.01.2026
 * =============================================================================
 */

var VPS_WEBHOOK_URL = "http://151.241.154.57:8080/execute_command";
var SHEET_NAME = "Сервера";

// =============================================================================
// МЕНЮ
// =============================================================================

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🔧 Управление')
      .addItem('⚡ Выполнить команды', 'executeCommands')
      .addItem('🔍 Проверить сервера', 'checkAllServers')
      .addSeparator()
      .addItem('📊 Статистика', 'showStatistics')
      .addItem('🗑️ Очистить результаты', 'clearResults')
      .addSeparator()
      .addItem('📖 Справка по командам', 'showCommandsHelp')
      .addToUi();
}

// =============================================================================
// ВЫПОЛНЕНИЕ КОМАНД
// =============================================================================

function executeCommands() {
  var ui = SpreadsheetApp.getUi();
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  var data = sheet.getDataRange().getValues();

  // Индексы колонок (могут отличаться в зависимости от структуры)
  var rdpCol = 1;  // Колонка B (RDP IP:Username:Password)
  var cmdCol = 10; // Колонка K (Команда)

  var commandsToExecute = [];

  for (var i = 1; i < data.length; i++) {
    var command = data[i][cmdCol];
    var rdp = data[i][rdpCol];

    if (command && command.toString().trim() !== '' && rdp) {
      commandsToExecute.push({
        rdp: rdp.toString().trim(),
        command: command.toString().trim(),
        rowIndex: i + 1
      });
    }
  }

  if (commandsToExecute.length === 0) {
    ui.alert('Нет команд для выполнения!', 'Заполните колонку "Команда" для нужных серверов', ui.ButtonSet.OK);
    return;
  }

  var successCount = 0;
  var errorCount = 0;

  for (var i = 0; i < commandsToExecute.length; i++) {
    var cmd = commandsToExecute[i];

    // Очищаем команду после отправки
    sheet.getRange(cmd.rowIndex, cmdCol + 1).setValue('');

    try {
      var payload = {
        rdp: cmd.rdp,
        command: cmd.command
      };

      var options = {
        method: 'post',
        contentType: 'application/json',
        payload: JSON.stringify(payload),
        muteHttpExceptions: true
      };

      var response = UrlFetchApp.fetch(VPS_WEBHOOK_URL, options);

      if (response.getResponseCode() === 200) {
        successCount++;
      } else {
        errorCount++;
      }
    } catch(err) {
      Logger.log('Ошибка выполнения команды: ' + err);
      errorCount++;
    }

    // Пауза между запросами
    Utilities.sleep(500);
  }

  ui.alert('✅ Готово!',
           'Выполнено: ' + successCount + '\n' +
           'Ошибок: ' + errorCount + '\n\n' +
           'Результаты появятся через 10-30 секунд в колонке "Результат"',
           ui.ButtonSet.OK);
}

// =============================================================================
// ПРОВЕРКА ВСЕХ СЕРВЕРОВ
// =============================================================================

function checkAllServers() {
  var ui = SpreadsheetApp.getUi();
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  var data = sheet.getDataRange().getValues();

  var rdpCol = 1; // Колонка B (RDP)
  var count = 0;

  for (var i = 1; i < data.length; i++) {
    var rdp = data[i][rdpCol];

    if (rdp && rdp.toString().trim() !== '') {
      try {
        var payload = {
          rdp: rdp.toString().trim(),
          command: 'check'
        };

        var options = {
          method: 'post',
          contentType: 'application/json',
          payload: JSON.stringify(payload),
          muteHttpExceptions: true
        };

        UrlFetchApp.fetch(VPS_WEBHOOK_URL, options);
        count++;

      } catch (error) {
        Logger.log('Ошибка проверки сервера: ' + error);
      }
    }
  }

  if (count === 0) {
    ui.alert('Нет серверов для проверки', ui.ButtonSet.OK);
  } else {
    ui.alert('✅ Проверка запущена',
             'Проверка запущена для ' + count + ' серверов.\n\n' +
             'Результаты появятся через 1-2 минуты в колонках со статусами.',
             ui.ButtonSet.OK);
  }
}

// =============================================================================
// СТАТИСТИКА
// =============================================================================

function showStatistics() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  var data = sheet.getDataRange().getValues();

  var total = 0;
  var online = 0;
  var offline = 0;
  var unknown = 0;

  // Колонка D - Статус машины
  var statusCol = 3;

  for (var i = 1; i < data.length; i++) {
    if (data[i][1]) { // Если есть RDP
      total++;

      var status = data[i][statusCol] ? data[i][statusCol].toString() : '';

      if (status.indexOf('Online') >= 0) {
        online++;
      } else if (status.indexOf('ERROR') >= 0 || status.indexOf('Offline') >= 0) {
        offline++;
      } else {
        unknown++;
      }
    }
  }

  var ui = SpreadsheetApp.getUi();
  ui.alert('📊 Статистика серверов',
           '━━━━━━━━━━━━━━━━━━━\n' +
           'Всего серверов: ' + total + '\n' +
           '━━━━━━━━━━━━━━━━━━━\n' +
           '✅ Онлайн: ' + online + ' (' + Math.round(online/total*100) + '%)\n' +
           '❌ Оффлайн/Проблемы: ' + offline + '\n' +
           '❓ Не проверялись: ' + unknown + '\n' +
           '━━━━━━━━━━━━━━━━━━━\n\n' +
           'Используй "Проверить сервера" для обновления статусов',
           ui.ButtonSet.OK);
}

// =============================================================================
// ОЧИСТКА РЕЗУЛЬТАТОВ
// =============================================================================

function clearResults() {
  var ui = SpreadsheetApp.getUi();
  var result = ui.alert('🗑️ Очистить все результаты?',
                        'Будут очищены колонки со статусами, IP, результатами команд.\n\nПродолжить?',
                        ui.ButtonSet.YES_NO);

  if (result == ui.Button.YES) {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
    var lastRow = sheet.getLastRow();

    if (lastRow > 1) {
      // Очищаем колонки D-M (Статусы, IP, Результаты)
      // Не трогаем колонки A-C (Магазин, RDP, AnyDesk)
      sheet.getRange(2, 4, lastRow-1, 10).clearContent().clearFormat();

      // Восстанавливаем условное форматирование для статусов (если было)
      var statusRange = sheet.getRange(2, 4, lastRow-1, 1);

      var onlineRule = SpreadsheetApp.newConditionalFormatRule()
        .whenTextContains('Online')
        .setBackground('#d9ead3')
        .setRanges([statusRange])
        .build();

      var errorRule = SpreadsheetApp.newConditionalFormatRule()
        .whenTextContains('ERROR')
        .setBackground('#f4cccc')
        .setRanges([statusRange])
        .build();

      var rules = sheet.getConditionalFormatRules();
      rules.push(onlineRule);
      rules.push(errorRule);
      sheet.setConditionalFormatRules(rules);
    }

    ui.alert('✅ Результаты очищены!',
             'Запусти "Проверить сервера" для получения новых данных',
             ui.ButtonSet.OK);
  }
}

// =============================================================================
// СПРАВКА ПО КОМАНДАМ
// =============================================================================

function showCommandsHelp() {
  var ui = SpreadsheetApp.getUi();

  var helpText = '📖 ДОСТУПНЫЕ КОМАНДЫ\n\n' +
    '━━━━ Мониторинг ━━━━\n' +
    '• check - Полная проверка сервера\n\n' +

    '━━━━ Программы ━━━━\n' +
    '• start_proxifier - Запустить Proxifier\n' +
    '• stop_proxifier - Остановить Proxifier\n' +
    '• restart_proxifier - Перезапустить Proxifier\n' +
    '• start_anydesk - Запустить AnyDesk\n\n' +

    '━━━━ Таймзона ━━━━\n' +
    '• get_timezone - Показать текущую таймзону\n' +
    '• set_timezone_msk - Установить MSK (UTC+3)\n' +
    '• set_timezone_ekt - Установить EKT (UTC+5)\n\n' +

    '━━━━ Языки ━━━━\n' +
    '• get_languages - Показать установленные языки\n' +
    '• set_lang_russian - Установить русский\n' +
    '• set_lang_english - Установить английский\n\n' +

    '━━━━ Система ━━━━\n' +
    '• reboot - Перезагрузить сервер (ОСТОРОЖНО!)\n\n' +

    '━━━━━━━━━━━━━━━━━━━━\n\n' +
    'КАК ИСПОЛЬЗОВАТЬ:\n' +
    '1. Введи команду в колонку "Команда"\n' +
    '2. Нажми "Управление → Выполнить команды"\n' +
    '3. Результат появится в колонке "Результат"\n\n' +
    'ВАЖНО:\n' +
    '- Команды выполняются удалённо через WinRM\n' +
    '- Результат появляется через 10-30 секунд\n' +
    '- Не используй reboot без необходимости';

  ui.alert(helpText, ui.ButtonSet.OK);
}

// =============================================================================
// АВТОМАТИЧЕСКАЯ ИНИЦИАЛИЗАЦИЯ
// =============================================================================

// Эта функция вызывается автоматически при открытии таблицы
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🔧 Управление')
      .addItem('⚡ Выполнить команды', 'executeCommands')
      .addItem('🔍 Проверить сервера', 'checkAllServers')
      .addSeparator()
      .addItem('📊 Статистика', 'showStatistics')
      .addItem('🗑️ Очистить результаты', 'clearResults')
      .addSeparator()
      .addItem('📖 Справка по командам', 'showCommandsHelp')
      .addToUi();
}
