/**
 * =============================================================================
 * SERVER MONITORING SYSTEM - Google Apps Script v4.2
 * =============================================================================
 * С логированием сессий (занят/свободен, IP клиента, город клиента)
 * Дата: 19.01.2026
 * =============================================================================
 */

var VPS_WEBHOOK_URL = "http://151.241.154.57:8080/execute_command";
var SHEET_NAME = "Сервера";
var LOG_SHEET_NAME = "Логи";
var SESSION_LOG_SHEET_NAME = "Логи сессий";
var MAX_LOG_ROWS = 1000;

const COLUMNS = {
  STORE: null,
  RDP: null,
  TARGET_CITY: null,
  STATUS_MACHINE: null,
  STATUS_PROXY: null,
  CURRENT_IP: null,
  CURRENT_CITY: null,
  ANYDESK: null,
  RUSTDESK: null,
  DATETIME: null,
  COMMAND: null,
  CHECK_SERVER_RESULT: null,
  CHECK_PROXY_RESULT: null,
  COMMAND_RESULT: null,
  PROXY_PROVIDER: null,
  PROXY_KEY: null,
  PROXYMA_API_KEY: null,
  PROXY_NAME: null,
  PROXY_LIMIT: null,
  PROXY_USED: null,
  PROXY_LEFT: null,
  PROXY_EXPIRES: null,
  PROXY_PRICE: null,
  PROXY_BALANCE: null,
  PROXY_CHECK_TIME: null,
  PROXY_CREDENTIALS: null,
  VYDATY: null,
  BUSY_STATUS: null,
  CLIENT_IP: null,
  CLIENT_CITY: null
};

function findColumnIndexes(headers) {
  var indexes = Object.assign({}, COLUMNS);

  for (var i = 0; i < headers.length; i++) {
    var h = headers[i].toString().toLowerCase();

    if (h.indexOf('магазин') >= 0) indexes.STORE = i;
    if (h.indexOf('rdp') >= 0 || (h.indexOf('ip') >= 0 && h.indexOf('username') >= 0 && h.indexOf('password') >= 0)) indexes.RDP = i;
    if (h.indexOf('город прокси который нужен') >= 0) indexes.TARGET_CITY = i;
    if (h.indexOf('статус машины') >= 0) indexes.STATUS_MACHINE = i;
    if (h.indexOf('статус прокси') >= 0) indexes.STATUS_PROXY = i;
    if (h === 'текущий ip' || h.indexOf('текущий ip') >= 0) indexes.CURRENT_IP = i;
    if (h.indexOf('текущий город') >= 0) indexes.CURRENT_CITY = i;
    if (h.indexOf('запущен anydesk') >= 0 || h.indexOf('anydesk') >= 0) indexes.ANYDESK = i;
    if (h.indexOf('запущен rustdesk') >= 0 || h.indexOf('rustdesk') >= 0) indexes.RUSTDESK = i;
    if (h.indexOf('дата и время проверки') >= 0 && h.indexOf('прокси') < 0) indexes.DATETIME = i;
    if (h.indexOf('команда') >= 0 && h.indexOf('результат') < 0) indexes.COMMAND = i;
    if (h.indexOf('результат проверки сервера') >= 0 || h.indexOf('результат check') >= 0) indexes.CHECK_SERVER_RESULT = i;
    if (h.indexOf('результат проверки прокси') >= 0 || h.indexOf('результат proxyma') >= 0) indexes.CHECK_PROXY_RESULT = i;
    if ((h.indexOf('результат команды') >= 0 || h.indexOf('результат последней команды') >= 0) && h.indexOf('проверки') < 0) indexes.COMMAND_RESULT = i;
    if (h.indexOf('провайдер') >= 0 && h.indexOf('api') < 0) indexes.PROXY_PROVIDER = i;
    if (h.indexOf('package key') >= 0 || h.indexOf('package key / id') >= 0) indexes.PROXY_KEY = i;
    if (h.indexOf('proxyma api key') >= 0 || (h.indexOf('api key') >= 0 && h.indexOf('proxyma') >= 0)) indexes.PROXYMA_API_KEY = i;
    if (h.indexOf('название пакета прокси') >= 0 || (h.indexOf('название') >= 0 && h.indexOf('пакета') >= 0)) indexes.PROXY_NAME = i;
    if (h.indexOf('лимит трафика') >= 0) indexes.PROXY_LIMIT = i;
    if (h.indexOf('использовано') >= 0 && h.indexOf('gb') >= 0) indexes.PROXY_USED = i;
    if (h.indexOf('осталось') >= 0 && h.indexOf('gb') >= 0) indexes.PROXY_LEFT = i;
    if (h.indexOf('дата истечения прокси') >= 0) indexes.PROXY_EXPIRES = i;
    if (h === 'цена тарифа') indexes.PROXY_PRICE = i;
    if (h === 'баланс кабинета') indexes.PROXY_BALANCE = i;
    if (h.indexOf('дата и время') >= 0 && h.indexOf('проверки прокси') >= 0) indexes.PROXY_CHECK_TIME = i;
    if (h.indexOf('прокси реквизиты') >= 0 || h.indexOf('реквизиты прокси') >= 0 || h.indexOf('proxy credentials') >= 0 || (h.indexOf('прокси') >= 0 && h.indexOf('реквизиты') >= 0)) indexes.PROXY_CREDENTIALS = i;
    if (h.indexOf('выдать') >= 0) indexes.VYDATY = i;
    if (h.indexOf('занят') >= 0 || h.indexOf('свободен') >= 0) indexes.BUSY_STATUS = i;
    if (h.indexOf('откуда') >= 0 && h.indexOf('ip') >= 0) indexes.CLIENT_IP = i;
    if (h.indexOf('город клиента') >= 0 || h.indexOf('город подключения') >= 0 || (h.indexOf('город') >= 0 && h.indexOf('подключ') >= 0)) indexes.CLIENT_CITY = i;
  }

  return indexes;
}

// =============================================================================
// ЛОГИРОВАНИЕ (с поддержкой сессий)
// =============================================================================

function getOrCreateLogSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var logSheet = ss.getSheetByName(LOG_SHEET_NAME);

  if (!logSheet) {
    logSheet = ss.insertSheet(LOG_SHEET_NAME);

    var headers = [
      'Дата/Время',
      'Магазин',
      'IP сервера',
      'Статус машины',
      'Статус прокси',
      'Текущий IP',
      'Город',
      'Занят/Свободен',
      'IP клиента',
      'Город клиента',
      'Событие'
    ];

    logSheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    logSheet.getRange(1, 1, 1, headers.length)
      .setFontWeight('bold')
      .setBackground('#4a86e8')
      .setFontColor('white')
      .setHorizontalAlignment('center');

    logSheet.setFrozenRows(1);
    logSheet.setColumnWidth(1, 150);
    logSheet.setColumnWidth(2, 100);
    logSheet.setColumnWidth(3, 120);
    logSheet.setColumnWidth(4, 100);
    logSheet.setColumnWidth(5, 120);
    logSheet.setColumnWidth(6, 130);
    logSheet.setColumnWidth(7, 120);
    logSheet.setColumnWidth(8, 140);
    logSheet.setColumnWidth(9, 130);
    logSheet.setColumnWidth(10, 120);
    logSheet.setColumnWidth(11, 150);
  }

  return logSheet;
}

function writeLog(params, eventType, storeName) {
  try {
    var logSheet = getOrCreateLogSheet();

    var serverIp = 'N/A';
    if (params.rdp) {
      var parts = params.rdp.toString().split(':');
      if (parts.length > 0) {
        serverIp = parts[0];
      }
    }

    var logRow = [
      new Date(),
      storeName || 'N/A',
      serverIp,
      params.statusMachine || '',
      params.statusProxy || '',
      params.currentIp || '',
      params.currentCity || '',
      params.busyStatus || '',
      params.clientIp || '',
      params.clientCity || '',
      eventType || 'check'
    ];

    logSheet.insertRowAfter(1);
    logSheet.getRange(2, 1, 1, logRow.length).setValues([logRow]);
    logSheet.getRange(2, 1).setNumberFormat('dd.MM.yyyy HH:mm:ss');

    // Подсветка статуса машины
    if (params.statusMachine) {
      var statusCell = logSheet.getRange(2, 4);
      if (params.statusMachine.toString().indexOf('Online') >= 0) {
        statusCell.setBackground('#d9ead3');
      } else if (params.statusMachine.toString().indexOf('ERROR') >= 0) {
        statusCell.setBackground('#f4cccc');
      }
    }

    // Подсветка занятости
    if (params.busyStatus) {
      var busyCell = logSheet.getRange(2, 8);
      if (params.busyStatus === 'Свободен') {
        busyCell.setBackground('#d9ead3');
      } else if (params.busyStatus.indexOf('Занят') >= 0) {
        busyCell.setBackground('#f4cccc');
      }
    }

    var lastRow = logSheet.getLastRow();
    if (lastRow > MAX_LOG_ROWS + 1) {
      logSheet.deleteRows(MAX_LOG_ROWS + 2, lastRow - MAX_LOG_ROWS - 1);
    }

  } catch (error) {
    Logger.log('Ошибка записи лога: ' + error.toString());
  }
}

// =============================================================================
// ЛОГИРОВАНИЕ СЕССИЙ (отдельный лист)
// =============================================================================

function getOrCreateSessionLogSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var logSheet = ss.getSheetByName(SESSION_LOG_SHEET_NAME);

  if (!logSheet) {
    logSheet = ss.insertSheet(SESSION_LOG_SHEET_NAME);

    var headers = [
      'Дата/Время',
      'Магазин',
      'IP сервера',
      'Статус',
      'Тип подключения',
      'Пользователь',
      'IP клиента',
      'Город клиента',
      'Событие'
    ];

    logSheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    logSheet.getRange(1, 1, 1, headers.length)
      .setFontWeight('bold')
      .setBackground('#9900ff')
      .setFontColor('white')
      .setHorizontalAlignment('center');

    logSheet.setFrozenRows(1);
    logSheet.setColumnWidth(1, 150);
    logSheet.setColumnWidth(2, 100);
    logSheet.setColumnWidth(3, 120);
    logSheet.setColumnWidth(4, 120);
    logSheet.setColumnWidth(5, 100);
    logSheet.setColumnWidth(6, 120);
    logSheet.setColumnWidth(7, 130);
    logSheet.setColumnWidth(8, 120);
    logSheet.setColumnWidth(9, 100);
  }

  return logSheet;
}

function writeSessionLog(params, storeName) {
  try {
    // Записываем только если есть данные о сессии
    if (!params.busyStatus) return;

    var logSheet = getOrCreateSessionLogSheet();

    var serverIp = 'N/A';
    if (params.rdp) {
      var parts = params.rdp.toString().split(':');
      if (parts.length > 0) {
        serverIp = parts[0];
      }
    }

    // Парсим статус для получения типа и пользователя
    var busyType = '';
    var busyUser = '';
    var busyStatus = params.busyStatus || '';

    if (busyStatus.indexOf('RDP') >= 0) busyType = 'RDP';
    if (busyStatus.indexOf('AD') >= 0 || busyStatus.indexOf('AnyDesk') >= 0) {
      busyType = busyType ? busyType + '+AnyDesk' : 'AnyDesk';
    }

    var userMatch = busyStatus.match(/:\s*(\S+)\)/);
    if (userMatch) busyUser = userMatch[1];

    var eventType = params.eventSource || (busyStatus.indexOf('Занят') >= 0 ? 'Подключение' : 'Свободен');

    // Улучшаем отображение для real-time событий
    if (eventType === 'realtime-connect') eventType = '🔴 Подключение (live)';
    if (eventType === 'realtime-disconnect') eventType = '🟢 Отключение (live)';

    var logRow = [
      new Date(),
      storeName || 'N/A',
      serverIp,
      busyStatus,
      busyType,
      busyUser,
      params.clientIp || '',
      params.clientCity || '',
      eventType
    ];

    logSheet.insertRowAfter(1);
    logSheet.getRange(2, 1, 1, logRow.length).setValues([logRow]);
    logSheet.getRange(2, 1).setNumberFormat('dd.MM.yyyy HH:mm:ss');

    // Подсветка статуса
    var statusCell = logSheet.getRange(2, 4);
    if (busyStatus === 'Свободен') {
      statusCell.setBackground('#d9ead3');
    } else if (busyStatus.indexOf('Занят') >= 0) {
      statusCell.setBackground('#f4cccc');
    }

    // Лимит строк
    var lastRow = logSheet.getLastRow();
    if (lastRow > MAX_LOG_ROWS + 1) {
      logSheet.deleteRows(MAX_LOG_ROWS + 2, lastRow - MAX_LOG_ROWS - 1);
    }

  } catch (error) {
    Logger.log('Ошибка записи лога сессий: ' + error.toString());
  }
}

// =============================================================================
// GET запросы
// =============================================================================

function doGet(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var cols = findColumnIndexes(headers);
  var servers = [];

  for (var i = 1; i < data.length; i++) {
    var row = data[i];
    if (!row[cols.RDP]) continue;

    servers.push({
      rdp: row[cols.RDP],
      store: cols.STORE >= 0 ? row[cols.STORE] : 'N/A',
      targetCity: cols.TARGET_CITY >= 0 ? row[cols.TARGET_CITY] : 'N/A',
      vydaty: cols.VYDATY >= 0 ? row[cols.VYDATY] : 'Да',
      proxyProvider: cols.PROXY_PROVIDER >= 0 ? row[cols.PROXY_PROVIDER] : '',
      proxyKey: cols.PROXY_KEY >= 0 ? row[cols.PROXY_KEY] : '',
      proxymaApiKey: cols.PROXYMA_API_KEY >= 0 ? row[cols.PROXYMA_API_KEY] : '',
      rowIndex: i + 1
    });
  }

  return ContentService
    .createTextOutput(JSON.stringify({success: true, count: servers.length, data: servers}))
    .setMimeType(ContentService.MimeType.JSON);
}

// =============================================================================
// POST запросы
// =============================================================================

function doPost(e) {
  try {
    var params = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
    var data = sheet.getDataRange().getValues();
    var headers = data[0];
    var cols = findColumnIndexes(headers);

    for (var i = 1; i < data.length; i++) {
      if (data[i][cols.RDP] === params.rdp) {

        var storeName = cols.STORE >= 0 ? data[i][cols.STORE] : '';

        var eventType = 'auto-check';
        if (params.commandResult) {
          var cmdPreview = params.commandResult.toString().substring(0, 50);
          eventType = 'command: ' + cmdPreview;
        } else if (params.checkProxyResult) {
          eventType = 'proxy-check';
        }

        // Записываем лог проверки сервера (только если не real-time событие)
        if ((params.currentIp || params.statusMachine) && !params.realtimeEvent) {
          writeLog(params, eventType, storeName);
        }

        // Записываем лог сессий (всегда при наличии busyStatus)
        if (params.busyStatus) {
          // Для real-time событий добавляем специальную метку
          if (params.realtimeEvent) {
            params.eventSource = 'realtime-' + params.realtimeEvent;
          }
          writeSessionLog(params, storeName);
        }

        // Обновляем данные в таблице
        if (cols.STATUS_MACHINE >= 0 && params.statusMachine) sheet.getRange(i+1, cols.STATUS_MACHINE+1).setValue(params.statusMachine);
        if (cols.STATUS_PROXY >= 0 && params.statusProxy) sheet.getRange(i+1, cols.STATUS_PROXY+1).setValue(params.statusProxy);
        if (cols.CURRENT_IP >= 0 && params.currentIp) sheet.getRange(i+1, cols.CURRENT_IP+1).setValue(params.currentIp);
        if (cols.CURRENT_CITY >= 0 && params.currentCity) sheet.getRange(i+1, cols.CURRENT_CITY+1).setValue(params.currentCity);
        if (cols.ANYDESK >= 0 && params.anydesk !== undefined) sheet.getRange(i+1, cols.ANYDESK+1).setValue(params.anydesk ? "✅" : "❌");
        if (cols.RUSTDESK >= 0 && params.rustdesk !== undefined) sheet.getRange(i+1, cols.RUSTDESK+1).setValue(params.rustdesk ? "✅" : "❌");
        if (cols.DATETIME >= 0 && params.datetime) sheet.getRange(i+1, cols.DATETIME+1).setValue(params.datetime);
        if (cols.COMMAND >= 0 && params.clearCommand) sheet.getRange(i+1, cols.COMMAND+1).setValue('');
        if (cols.CHECK_SERVER_RESULT >= 0 && params.checkServerResult) sheet.getRange(i+1, cols.CHECK_SERVER_RESULT+1).setValue(params.checkServerResult);
        if (cols.CHECK_PROXY_RESULT >= 0 && params.checkProxyResult) sheet.getRange(i+1, cols.CHECK_PROXY_RESULT+1).setValue(params.checkProxyResult);
        if (cols.COMMAND_RESULT >= 0 && params.commandResult) sheet.getRange(i+1, cols.COMMAND_RESULT+1).setValue(params.commandResult);
        if (cols.PROXY_NAME >= 0 && params.proxyName) sheet.getRange(i+1, cols.PROXY_NAME+1).setValue(params.proxyName);
        if (cols.PROXY_LIMIT >= 0 && params.proxyLimit !== undefined) sheet.getRange(i+1, cols.PROXY_LIMIT+1).setValue(params.proxyLimit);
        if (cols.PROXY_USED >= 0 && params.proxyUsed !== undefined) sheet.getRange(i+1, cols.PROXY_USED+1).setValue(params.proxyUsed);
        if (cols.PROXY_LEFT >= 0 && params.proxyLeft !== undefined) sheet.getRange(i+1, cols.PROXY_LEFT+1).setValue(params.proxyLeft);
        if (cols.PROXY_EXPIRES >= 0 && params.proxyExpires) sheet.getRange(i+1, cols.PROXY_EXPIRES+1).setValue(params.proxyExpires);
        if (cols.PROXY_CHECK_TIME >= 0 && params.proxyCheckTime) sheet.getRange(i+1, cols.PROXY_CHECK_TIME+1).setValue(params.proxyCheckTime);
        if (cols.PROXY_BALANCE >= 0 && params.proxyBalance) sheet.getRange(i+1, cols.PROXY_BALANCE+1).setValue(params.proxyBalance);
        if (cols.PROXY_PRICE >= 0 && params.proxyPrice) sheet.getRange(i+1, cols.PROXY_PRICE+1).setValue(params.proxyPrice);

        // Session monitoring
        if (cols.BUSY_STATUS >= 0 && params.busyStatus !== undefined) {
          var busyCell = sheet.getRange(i+1, cols.BUSY_STATUS+1);
          busyCell.setValue(params.busyStatus);
          if (params.busyStatus === 'Свободен' || params.busyStatus === '') {
            busyCell.setBackground('#d9ead3');
          } else if (params.busyStatus.indexOf('Занят') >= 0) {
            busyCell.setBackground('#f4cccc');
          }
        }
        if (cols.CLIENT_IP >= 0 && params.clientIp !== undefined) {
          sheet.getRange(i+1, cols.CLIENT_IP+1).setValue(params.clientIp);
        }
        if (cols.CLIENT_CITY >= 0 && params.clientCity !== undefined) {
          sheet.getRange(i+1, cols.CLIENT_CITY+1).setValue(params.clientCity);
        }

        return ContentService.createTextOutput(JSON.stringify({success: true})).setMimeType(ContentService.MimeType.JSON);
      }
    }

    return ContentService.createTextOutput(JSON.stringify({success: false, error: 'Server not found'})).setMimeType(ContentService.MimeType.JSON);

  } catch(err) {
    Logger.log('Ошибка doPost: ' + err.toString());
    return ContentService.createTextOutput(JSON.stringify({success: false, error: err.toString()})).setMimeType(ContentService.MimeType.JSON);
  }
}

// =============================================================================
// МЕНЮ
// =============================================================================

function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('🔧 Управление серверами')
      .addItem('⚡ Выполнить команды', 'executeCommands')
      .addItem('🔍 Проверить все сервера', 'checkAllServers')
      .addItem('📊 Проверить все прокси', 'checkAllProxyma')
      .addSeparator()
      .addItem('📊 Показать статистику', 'showStatistics')
      .addItem('🗑️ Очистить результаты', 'clearResults')
      .addItem('🗑️ Очистить логи', 'clearLogs')
      .addItem('🗑️ Очистить логи сессий', 'clearSessionLogs')
      .addToUi();
}

function executeCommands() {
  var ui = SpreadsheetApp.getUi();
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var cols = findColumnIndexes(headers);

  if (cols.RDP < 0 || cols.COMMAND < 0) {
    ui.alert('Ошибка', 'Не найдены необходимые колонки!', ui.ButtonSet.OK);
    return;
  }

  var commandsToExecute = [];

  for (var i = 1; i < data.length; i++) {
    var command = data[i][cols.COMMAND];
    var rdp = data[i][cols.RDP];
    var proxyKey = cols.PROXY_KEY >= 0 ? data[i][cols.PROXY_KEY] : '';
    var proxymaApiKey = cols.PROXYMA_API_KEY >= 0 ? data[i][cols.PROXYMA_API_KEY] : '';
    var proxyCredentials = cols.PROXY_CREDENTIALS >= 0 ? data[i][cols.PROXY_CREDENTIALS] : '';

    if (command && command.toString().trim() !== '') {
      commandsToExecute.push({
        rdp: rdp,
        command: command.toString().trim(),
        proxyKey: proxyKey,
        proxymaApiKey: proxymaApiKey,
        proxyCredentials: proxyCredentials,
        rowIndex: i + 1
      });
    }
  }

  if (commandsToExecute.length === 0) {
    ui.alert('Нет команд для выполнения!', ui.ButtonSet.OK);
    return;
  }

  var successCount = 0;
  var errorCount = 0;

  for (var i = 0; i < commandsToExecute.length; i++) {
    var cmd = commandsToExecute[i];
    sheet.getRange(cmd.rowIndex, cols.COMMAND + 1).setValue('');

    try {
      var payload = {
        rdp: cmd.rdp,
        command: cmd.command,
        proxyKey: cmd.proxyKey,
        proxymaApiKey: cmd.proxymaApiKey,
        proxyCredentials: cmd.proxyCredentials
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
      errorCount++;
    }

    Utilities.sleep(500);
  }

  ui.alert('✅ Готово!', 'Выполнено: ' + successCount + '\nОшибок: ' + errorCount, ui.ButtonSet.OK);
}

function checkAllServers() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  var lastRow = sheet.getLastRow();

  if (lastRow < 2) {
    SpreadsheetApp.getUi().alert('Нет серверов для проверки');
    return;
  }

  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var cols = findColumnIndexes(headers);

  var rdpRange = sheet.getRange(2, cols.RDP + 1, lastRow - 1, 1).getValues();
  var count = 0;

  for (var i = 0; i < rdpRange.length; i++) {
    var rdp = rdpRange[i][0];
    if (rdp && rdp.toString().trim()) {
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
        Logger.log('Error: ' + error);
      }
    }
  }

  SpreadsheetApp.getUi().alert('✅ Проверка запущена для ' + count + ' серверов.\n\nРезультаты появятся через 1-2 минуты.');
}

function checkAllProxyma() {
  var ui = SpreadsheetApp.getUi();
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var cols = findColumnIndexes(headers);

  var count = 0;

  for (var i = 1; i < data.length; i++) {
    var rdp = data[i][cols.RDP];
    var provider = data[i][cols.PROXY_PROVIDER];
    var proxyKey = cols.PROXY_KEY >= 0 ? data[i][cols.PROXY_KEY] : '';
    var proxymaApiKey = cols.PROXYMA_API_KEY >= 0 ? data[i][cols.PROXYMA_API_KEY] : '';

    if (rdp && provider && provider.toString().toLowerCase() === 'proxyma' && proxyKey && proxymaApiKey) {
      try {
        var payload = {
          rdp: rdp,
          command: 'check_proxyma',
          proxyKey: proxyKey,
          proxymaApiKey: proxymaApiKey
        };

        var options = {
          method: 'post',
          contentType: 'application/json',
          payload: JSON.stringify(payload),
          muteHttpExceptions: true
        };

        UrlFetchApp.fetch(VPS_WEBHOOK_URL, options);
        count++;
        Utilities.sleep(500);
      } catch(err) {}
    }
  }

  if (count === 0) {
    ui.alert('Не найдено серверов с Proxyma');
  } else {
    ui.alert('✅ Проверка Proxyma запущена для ' + count + ' серверов');
  }
}

function showStatistics() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  var data = sheet.getDataRange().getValues();
  var headers = data[0];
  var cols = findColumnIndexes(headers);

  var total = 0, online = 0, proxyOk = 0, busy = 0, free = 0;

  for (var i = 1; i < data.length; i++) {
    if (data[i][cols.RDP]) {
      total++;
      if (cols.STATUS_MACHINE >= 0 && data[i][cols.STATUS_MACHINE].toString().indexOf('Online') >= 0) online++;
      if (cols.STATUS_PROXY >= 0 && data[i][cols.STATUS_PROXY] === 'OK') proxyOk++;
      if (cols.BUSY_STATUS >= 0) {
        var busyStatus = data[i][cols.BUSY_STATUS].toString();
        if (busyStatus.indexOf('Занят') >= 0) busy++;
        else if (busyStatus === 'Свободен') free++;
      }
    }
  }

  var logSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(LOG_SHEET_NAME);
  var logCount = logSheet ? Math.max(0, logSheet.getLastRow() - 1) : 0;

  var ui = SpreadsheetApp.getUi();
  ui.alert('📊 Статистика',
           'Всего серверов: ' + total + '\n' +
           '✅ Онлайн: ' + online + '\n' +
           '🔧 Прокси OK: ' + proxyOk + '\n' +
           '❌ Проблемы: ' + (total - online) + '\n' +
           '━━━━━━━━━━━━━━━━━━━\n' +
           '🟢 Свободно: ' + free + '\n' +
           '🔴 Занято: ' + busy + '\n' +
           '━━━━━━━━━━━━━━━━━━━\n' +
           '📝 Записей в логах: ' + logCount,
           ui.ButtonSet.OK);
}

function clearResults() {
  var ui = SpreadsheetApp.getUi();
  var result = ui.alert('🗑️ Очистить все результаты?', 'Продолжить?', ui.ButtonSet.YES_NO);

  if (result == ui.Button.YES) {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
    var data = sheet.getDataRange().getValues();
    var headers = data[0];
    var cols = findColumnIndexes(headers);

    var columnsToClear = [
      cols.STATUS_MACHINE, cols.STATUS_PROXY, cols.CURRENT_IP, cols.CURRENT_CITY,
      cols.ANYDESK, cols.RUSTDESK, cols.DATETIME, cols.COMMAND,
      cols.CHECK_SERVER_RESULT, cols.CHECK_PROXY_RESULT, cols.COMMAND_RESULT,
      cols.BUSY_STATUS, cols.CLIENT_IP, cols.CLIENT_CITY
    ];

    for (var i = 1; i < data.length; i++) {
      for (var j = 0; j < columnsToClear.length; j++) {
        if (columnsToClear[j] >= 0) {
          sheet.getRange(i + 1, columnsToClear[j] + 1).setValue('').setBackground(null);
        }
      }
    }

    ui.alert('✅ Результаты очищены!');
  }
}

function clearLogs() {
  var ui = SpreadsheetApp.getUi();
  var result = ui.alert('🗑️ Очистить логи проверок?', 'Продолжить?', ui.ButtonSet.YES_NO);

  if (result == ui.Button.YES) {
    var logSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(LOG_SHEET_NAME);

    if (logSheet) {
      var lastRow = logSheet.getLastRow();
      if (lastRow > 1) {
        logSheet.deleteRows(2, lastRow - 1);
      }
      ui.alert('✅ Логи проверок очищены!');
    }
  }
}

function clearSessionLogs() {
  var ui = SpreadsheetApp.getUi();
  var result = ui.alert('🗑️ Очистить логи сессий?', 'Будут удалены записи о подключениях.\nПродолжить?', ui.ButtonSet.YES_NO);

  if (result == ui.Button.YES) {
    var logSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SESSION_LOG_SHEET_NAME);

    if (logSheet) {
      var lastRow = logSheet.getLastRow();
      if (lastRow > 1) {
        logSheet.deleteRows(2, lastRow - 1);
      }
      ui.alert('✅ Логи сессий очищены!');
    } else {
      ui.alert('Лист "Логи сессий" не найден');
    }
  }
}
