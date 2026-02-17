/** ===================== КОНФИГ ===================== */
const SHEET_NUMBERS = 'Номера';      // список арендованных номеров
const SHEET_LOG     = 'Журнал СМС';  // журнал входящих СМС
const LOG_HEADERS = ['Дата/время получения', 'Номер', 'Сервис', 'Код', 'Текст СМС', 'ID активации'];

/**
 * ===================== НАСТРОЙКА =====================
 * Откройте: Project Settings → Script properties
 * Добавьте:
 *   API_KEY         = ваш ключ
 *   API_BASE_URL    = http://65.109.64.76:8011/stubs/handler_api.php
 *   DEFAULT_SERVICE = oz
 *   DEFAULT_COUNTRY = 0
 *
 * ===================== ДОСТУПНЫЕ МЕТОДЫ API =====================
 *   getNumber, getStatus, setStatus, getBalance, getCountries, getServiceName
 */

/** ===================== МЕНЮ ===================== */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📲 СМС')
    .addItem('📞 Получить новый номер', 'getNewNumber')
    .addItem('📞 Получить номер (выбор сервиса)', 'getNumberCustom')
    .addSeparator()
    .addItem('📥 Проверить СМС (все номера)', 'checkAllSms')
    .addSeparator()
    .addItem('✅ Подтвердить активацию', 'confirmActivation')
    .addItem('❌ Отменить активацию', 'cancelActivation')
    .addItem('🔁 Запросить ещё СМС', 'requestAnotherSms')
    .addSeparator()
    .addItem('💰 Баланс', 'showBalance')
    .addItem('🌍 Список стран', 'loadCountries')
    .addSeparator()
    .addItem('⏱️ Автопроверка ВКЛ', 'enableAutoCheck')
    .addItem('⏹️ Автопроверка ВЫКЛ', 'disableAutoCheck')
    .addSeparator()
    .addItem('⚙️ Настройки', 'showSettings')
    .addSeparator()
    .addItem('🧪 Тест API', 'testApiConnection')
    .addItem('🔍 Диагностика (лог запросов)', 'diagnoseApi')
    .addItem('🔎 Проверить по ID активации', 'checkSingleNumber')
    .addItem('📱 Проверить по номеру телефона', 'checkByPhoneNumber')
    .addToUi();
  ensureSheets_();
}

/** ===================== ИНИЦИАЛИЗАЦИЯ ЛИСТОВ ===================== */
function ensureSheets_() {
  const ss = SpreadsheetApp.getActive();

  // Лист номеров
  let nums = ss.getSheetByName(SHEET_NUMBERS);
  if (!nums) {
    nums = ss.insertSheet(SHEET_NUMBERS);
  }
  const numHeaders = ['ID активации', 'Номер', 'Сервис', 'Статус', 'Код', 'Текст СМС', 'Время аренды', 'Цена'];
  const firstRowNums = nums.getRange(1, 1, 1, numHeaders.length).getValues()[0];
  if (firstRowNums.join('') === '') {
    nums.getRange(1, 1, 1, numHeaders.length).setValues([numHeaders]);
    nums.setFrozenRows(1);
    nums.autoResizeColumns(1, numHeaders.length);
  }

  // Лист журнала СМС
  let log = ss.getSheetByName(SHEET_LOG);
  if (!log) log = ss.insertSheet(SHEET_LOG);
  const firstRowLog = log.getRange(1, 1, 1, LOG_HEADERS.length).getValues()[0];
  if (firstRowLog.join('') === '') {
    log.getRange(1, 1, 1, LOG_HEADERS.length).setValues([LOG_HEADERS]);
    log.setFrozenRows(1);
    log.getRange('A:A').setNumberFormat('yyyy-mm-dd HH:mm:ss');
    log.autoResizeColumns(1, LOG_HEADERS.length);
  }
}

/** ===================== КОНФИГУРАЦИЯ ===================== */
function getConfig_() {
  const p = PropertiesService.getScriptProperties();
  return {
    apiKey: p.getProperty('API_KEY') || '',
    baseUrl: (p.getProperty('API_BASE_URL') || 'http://65.109.64.76:8011/stubs/handler_api.php').replace(/\/+$/, ''),
    service: p.getProperty('DEFAULT_SERVICE') || 'oz',
    country: p.getProperty('DEFAULT_COUNTRY') || '0',
    pollMin: parseInt(p.getProperty('POLL_MINUTES') || '1', 10)
  };
}

/** ===================== API ЗАПРОС ===================== */
function apiCall_(action, params) {
  const cfg = getConfig_();
  if (!cfg.apiKey) throw new Error('Не задан API_KEY в Script Properties!');

  let url = `${cfg.baseUrl}?api_key=${encodeURIComponent(cfg.apiKey)}&action=${action}`;
  for (const [k, v] of Object.entries(params || {})) {
    if (v !== undefined && v !== null && v !== '') {
      url += `&${encodeURIComponent(k)}=${encodeURIComponent(v)}`;
    }
  }

  const resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  const text = resp.getContentText().trim();
  const code = resp.getResponseCode();

  if (code !== 200) throw new Error(`HTTP ${code}: ${text}`);

  // Проверяем на известные ошибки
  const errors = {
    'Access denied': 'Доступ запрещён (проверьте API ключ)',
    'BAD_KEY': 'Неверный API ключ',
    'NO_KEY': 'API ключ не указан',
    'BAD_ACTION': 'Неверное действие',
    'NO_NUMBERS': 'Нет свободных номеров',
    'NO_BALANCE': 'Недостаточно средств',
    'NO_ACTIVATION': 'Активация не найдена',
    'BANNED': 'Аккаунт заблокирован',
    'ERROR_SQL': 'Ошибка сервера'
  };

  if (errors[text]) throw new Error(errors[text]);

  return text;
}

/** ===================== ПАРСИНГ ОТВЕТА ===================== */
function parseResp_(text) {
  // Пробуем JSON
  try {
    return { json: true, data: JSON.parse(text) };
  } catch (_) {}

  // ACCESS_BALANCE:123.45
  if (text.startsWith('ACCESS_BALANCE:')) {
    return { balance: text.split(':')[1] };
  }

  // ACCESS_NUMBER:ID:NUMBER
  if (text.startsWith('ACCESS_NUMBER:')) {
    const p = text.split(':');
    return { id: p[1], number: p[2] };
  }

  // STATUS_OK:CODE или STATUS_WAIT_CODE и т.д.
  if (text.startsWith('STATUS_')) {
    const p = text.split(':');
    return { status: p[0], code: p.slice(1).join(':') };
  }

  // ACCESS_READY, ACCESS_CANCEL, ACCESS_ACTIVATION и т.д.
  if (text.startsWith('ACCESS_')) {
    const p = text.split(':');
    return { access: p[0], value: p.slice(1).join(':') };
  }

  return { raw: text };
}

/** ===================== БАЛАНС ===================== */
function showBalance() {
  try {
    const r = parseResp_(apiCall_('getBalance', {}));
    const bal = r.balance || (r.data && r.data.balance) || r.raw || '?';
    SpreadsheetApp.getUi().alert(`💰 Баланс: ${bal}`);
  } catch (e) {
    SpreadsheetApp.getUi().alert(`❌ Ошибка: ${e.message}`);
  }
}

/** ===================== ПОЛУЧИТЬ НОМЕР ===================== */
function getNewNumber() {
  const cfg = getConfig_();
  getNumber_(cfg.service, cfg.country);
}

function getNumberCustom() {
  const ui = SpreadsheetApp.getUi();
  const cfg = getConfig_();

  const s = ui.prompt('Сервис', `Код сервиса (по умолчанию: ${cfg.service}):`, ui.ButtonSet.OK_CANCEL);
  if (s.getSelectedButton() !== ui.Button.OK) return;
  const service = s.getResponseText().trim() || cfg.service;

  const c = ui.prompt('Страна', `Код страны (по умолчанию: ${cfg.country}, 0=Россия):`, ui.ButtonSet.OK_CANCEL);
  if (c.getSelectedButton() !== ui.Button.OK) return;
  const country = c.getResponseText().trim() || cfg.country;

  getNumber_(service, country);
}

function getNumber_(service, country) {
  ensureSheets_();
  try {
    const resp = apiCall_('getNumber', { service, country });
    const r = parseResp_(resp);

    let id, num, cost = '';

    if (r.id && r.number) {
      // Формат ACCESS_NUMBER:ID:NUMBER
      id = r.id;
      num = r.number;
    } else if (r.json && r.data) {
      // JSON формат
      id = r.data.activationId || r.data.id;
      num = r.data.phoneNumber || r.data.number;
      cost = r.data.activationCost || r.data.cost || '';
    } else {
      throw new Error(`Неожиданный ответ: ${resp}`);
    }

    // Записываем в лист номеров
    const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NUMBERS);
    sh.appendRow([id, num, service, 'Ожидание СМС', '', '', new Date(), cost]);
    sh.autoResizeColumns(1, 8);

    SpreadsheetApp.getUi().alert(`✅ Номер получен!\n\n📞 ${num}\n🆔 ID: ${id}\n💵 Цена: ${cost || 'н/д'}\n\nНомер добавлен в список «Номера».`);
  } catch (e) {
    SpreadsheetApp.getUi().alert(`❌ Ошибка: ${e.message}`);
  }
}

/** ===================== ПРОВЕРИТЬ СМС (ВСЕ НОМЕРА ИЗ СПИСКА) ===================== */
function checkAllSms() {
  ensureSheets_();
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NUMBERS);
  const lastRow = sh.getLastRow();

  if (lastRow < 2) {
    SpreadsheetApp.getUi().alert('Список номеров пуст.\nСначала получите номер через меню.');
    return;
  }

  const data = sh.getRange(2, 1, lastRow - 1, 8).getValues();
  let checked = 0, updated = 0;
  const newCodes = [];

  for (let i = 0; i < data.length; i++) {
    const row = i + 2;
    const [id, num, svc, status, oldCode, oldText] = data[i];

    // Пропускаем завершённые/отменённые
    if (['Завершено', 'Отменено', 'Не найдено'].includes(status)) continue;
    if (!id) continue;

    checked++;
    sh.getRange(row, 4).setValue('⏳ проверка...');
    SpreadsheetApp.flush();

    try {
      const resp = apiCall_('getStatus', { id });
      const r = parseResp_(resp);

      let newStatus = status;
      let code = oldCode || '';
      let smsText = oldText || '';

      if (r.status) {
        // Текстовый формат STATUS_XXX:CODE
        switch (r.status) {
          case 'STATUS_WAIT_CODE':
            newStatus = 'Ожидание СМС';
            break;
          case 'STATUS_WAIT_RETRY':
            newStatus = 'Ожидание повторной СМС';
            break;
          case 'STATUS_WAIT_RESEND':
            newStatus = 'Ожидание переотправки';
            break;
          case 'STATUS_OK':
            newStatus = 'Код получен';
            code = r.code || code;
            break;
          case 'STATUS_CANCEL':
            newStatus = 'Отменено';
            break;
        }
      } else if (r.json && r.data) {
        // JSON формат
        if (r.data.smsCode) {
          code = Array.isArray(r.data.smsCode) ? r.data.smsCode.join(', ') : r.data.smsCode;
          newStatus = 'Код получен';
        }
        if (r.data.smsText) {
          smsText = r.data.smsText;
        }
        if (r.data.status) {
          const st = String(r.data.status);
          if (st === '6') newStatus = 'Завершено';
          else if (st === '8') newStatus = 'Отменено';
        }
      } else if (r.raw === 'NO_ACTIVATION') {
        newStatus = 'Не найдено';
      }

      // Обновляем ячейки
      sh.getRange(row, 4).setValue(newStatus);
      sh.getRange(row, 5).setValue(code);
      sh.getRange(row, 6).setValue(smsText);

      // Если появился новый код — записываем в журнал
      if (code && code !== oldCode) {
        updated++;
        newCodes.push({ num, code });
        appendToLogNoDup_([{
          received_at: new Date(),
          number: num,
          service: svc,
          code: code,
          text: smsText,
          activation_id: id
        }]);
      }

    } catch (e) {
      sh.getRange(row, 4).setValue(`Ошибка: ${e.message.slice(0, 50)}`);
      console.log(`Ошибка проверки ${id}: ${e.message}`);
    }

    Utilities.sleep(300); // Пауза между запросами
  }

  let msg = `✅ Проверено номеров: ${checked}\nПолучено новых кодов: ${updated}`;
  if (newCodes.length > 0) {
    msg += '\n\n📩 Новые коды:';
    newCodes.forEach(x => msg += `\n• ${x.num}: ${x.code}`);
  }

  SpreadsheetApp.getUi().alert(msg);
}

/** ===================== ЖУРНАЛ СМС БЕЗ ДУБЛЕЙ ===================== */
function appendToLogNoDup_(messages) {
  if (!messages.length) return 0;
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_LOG);

  // Собираем ключи существующих записей
  const lastRow = sh.getLastRow();
  const existingKeys = new Set();
  if (lastRow >= 2) {
    const existed = sh.getRange(2, 1, lastRow - 1, LOG_HEADERS.length).getValues();
    for (const r of existed) {
      // Ключ: номер + код + ID активации
      const key = `${r[1]}•${r[3]}•${r[5]}`;
      existingKeys.add(key);
    }
  }

  // Добавляем только новые
  const toAppend = [];
  for (const m of messages) {
    const key = `${m.number}•${m.code}•${m.activation_id}`;
    if (existingKeys.has(key)) continue;
    existingKeys.add(key);
    toAppend.push([
      m.received_at instanceof Date ? m.received_at : new Date(),
      m.number,
      m.service,
      m.code,
      m.text,
      m.activation_id
    ]);
  }

  if (!toAppend.length) return 0;
  sh.getRange(sh.getLastRow() + 1, 1, toAppend.length, LOG_HEADERS.length).setValues(toAppend);
  return toAppend.length;
}

/** ===================== УПРАВЛЕНИЕ СТАТУСОМ ===================== */
function setStatus_(statusCode, statusName) {
  const ui = SpreadsheetApp.getUi();
  const resp = ui.prompt(statusName, 'Введите ID активации:', ui.ButtonSet.OK_CANCEL);
  if (resp.getSelectedButton() !== ui.Button.OK) return;

  const id = resp.getResponseText().trim();
  if (!id) { ui.alert('ID не указан!'); return; }

  try {
    const result = apiCall_('setStatus', { id, status: statusCode });

    // Обновляем в таблице номеров
    const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NUMBERS);
    const data = sh.getDataRange().getValues();
    for (let i = 1; i < data.length; i++) {
      if (String(data[i][0]) === id) {
        sh.getRange(i + 1, 4).setValue(statusName);
        break;
      }
    }

    ui.alert(`✅ Статус изменён: ${result}`);
  } catch (e) {
    ui.alert(`❌ Ошибка: ${e.message}`);
  }
}

function confirmActivation() { setStatus_(6, 'Завершено'); }
function cancelActivation() { setStatus_(-1, 'Отменено'); }
function requestAnotherSms() { setStatus_(3, 'Ожидание повторной СМС'); }

/** ===================== СПИСОК СТРАН ===================== */
function loadCountries() {
  const ss = SpreadsheetApp.getActive();

  let sh = ss.getSheetByName('Страны');
  if (!sh) sh = ss.insertSheet('Страны');

  try {
    const resp = apiCall_('getCountries', {});
    const r = parseResp_(resp);

    sh.clear();
    sh.getRange(1, 1, 1, 3).setValues([['Код', 'Страна', 'Доступно']]);

    const rows = [];

    if (r.json && r.data) {
      // JSON формат
      if (Array.isArray(r.data)) {
        r.data.forEach(c => {
          rows.push([c.id || c.code, c.name || c.country, c.count || '']);
        });
      } else {
        // Объект {code: name} или {code: {name, count}}
        for (const [k, v] of Object.entries(r.data)) {
          if (typeof v === 'object') {
            rows.push([k, v.name || v.country || '', v.count || '']);
          } else {
            rows.push([k, v, '']);
          }
        }
      }
    } else if (r.raw) {
      // Текстовый формат - попробуем распарсить
      rows.push(['', r.raw, '']);
    }

    if (rows.length) {
      sh.getRange(2, 1, rows.length, 3).setValues(rows);
    }
    sh.setFrozenRows(1);
    sh.autoResizeColumns(1, 3);

    SpreadsheetApp.getUi().alert(`✅ Загружено стран: ${rows.length}`);
  } catch (e) {
    SpreadsheetApp.getUi().alert(`❌ Ошибка: ${e.message}`);
  }
}

/** ===================== АВТОПРОВЕРКА ===================== */
function enableAutoCheck() {
  disableAutoCheck();
  const cfg = getConfig_();
  ScriptApp.newTrigger('autoCheckSms_').timeBased().everyMinutes(cfg.pollMin).create();
  SpreadsheetApp.getUi().alert(`✅ Автопроверка включена!\nИнтервал: каждые ${cfg.pollMin} мин.\n\nНовые СМС будут автоматически появляться в «Журнал СМС».`);
}

function disableAutoCheck() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'autoCheckSms_')
    .forEach(t => ScriptApp.deleteTrigger(t));
  SpreadsheetApp.getUi().alert('⏹️ Автопроверка выключена');
}

// Тихая проверка для триггера (без UI)
function autoCheckSms_() {
  ensureSheets_();
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NUMBERS);
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return;

  const data = sh.getRange(2, 1, lastRow - 1, 8).getValues();

  for (let i = 0; i < data.length; i++) {
    const row = i + 2;
    const [id, num, svc, status, oldCode, oldText] = data[i];

    if (['Завершено', 'Отменено', 'Не найдено'].includes(status) || !id) continue;

    try {
      const resp = apiCall_('getStatus', { id });
      const r = parseResp_(resp);

      let newStatus = status;
      let code = oldCode || '';
      let smsText = oldText || '';

      if (r.status === 'STATUS_OK') {
        newStatus = 'Код получен';
        code = r.code || code;
      } else if (r.status === 'STATUS_CANCEL') {
        newStatus = 'Отменено';
      } else if (r.status === 'STATUS_WAIT_CODE') {
        newStatus = 'Ожидание СМС';
      } else if (r.json && r.data && r.data.smsCode) {
        code = Array.isArray(r.data.smsCode) ? r.data.smsCode.join(', ') : r.data.smsCode;
        smsText = r.data.smsText || '';
        newStatus = 'Код получен';
      } else if (r.raw === 'NO_ACTIVATION') {
        newStatus = 'Не найдено';
      }

      if (newStatus !== status || code !== oldCode) {
        sh.getRange(row, 4).setValue(newStatus);
        sh.getRange(row, 5).setValue(code);
        sh.getRange(row, 6).setValue(smsText);

        if (code && code !== oldCode) {
          appendToLogNoDup_([{
            received_at: new Date(),
            number: num,
            service: svc,
            code: code,
            text: smsText,
            activation_id: id
          }]);
        }
      }
    } catch (e) {
      console.log(`Автопроверка ${id}: ${e.message}`);
    }

    Utilities.sleep(300);
  }
}

/** ===================== НАСТРОЙКИ ===================== */
function showSettings() {
  const cfg = getConfig_();
  const html = HtmlService.createHtmlOutput(`
    <style>
      body{font-family:Arial,sans-serif;padding:15px}
      label{display:block;margin-top:12px;font-weight:bold}
      input{width:100%;padding:6px;margin-top:4px;box-sizing:border-box}
      button{margin-top:15px;padding:8px 16px;background:#4285f4;color:#fff;border:none;cursor:pointer;border-radius:4px}
      button:hover{background:#3367d6}
      .hint{font-size:11px;color:#666;margin-top:3px}
    </style>
    <h3>⚙️ Настройки API</h3>
    <label>API Ключ</label>
    <input id="k" value="${cfg.apiKey}">
    <label>URL API</label>
    <input id="u" value="${cfg.baseUrl}">
    <div class="hint">http://65.109.64.76:8011/stubs/handler_api.php</div>
    <label>Сервис по умолчанию</label>
    <input id="s" value="${cfg.service}">
    <label>Страна (0=Россия)</label>
    <input id="c" value="${cfg.country}">
    <label>Автопроверка (минуты)</label>
    <input id="p" type="number" value="${cfg.pollMin}" min="1" max="60">
    <button onclick="save()">💾 Сохранить</button>
    <script>
      function save(){
        google.script.run.withSuccessHandler(()=>{alert('✅ Сохранено');google.script.host.close()})
          .withFailureHandler(e=>alert('❌ '+e))
          .saveSettings_({
            apiKey:document.getElementById('k').value,
            baseUrl:document.getElementById('u').value,
            service:document.getElementById('s').value,
            country:document.getElementById('c').value,
            pollMin:document.getElementById('p').value
          });
      }
    </script>
  `).setWidth(380).setHeight(420);
  SpreadsheetApp.getUi().showModalDialog(html, 'Настройки');
}

function saveSettings_(s) {
  const p = PropertiesService.getScriptProperties();
  p.setProperty('API_KEY', s.apiKey || '');
  p.setProperty('API_BASE_URL', s.baseUrl || '');
  p.setProperty('DEFAULT_SERVICE', s.service || 'oz');
  p.setProperty('DEFAULT_COUNTRY', s.country || '0');
  p.setProperty('POLL_MINUTES', s.pollMin || '1');
}

/** ===================== ТЕСТ ===================== */
function testApiConnection() {
  const cfg = getConfig_();
  const ui = SpreadsheetApp.getUi();

  let msg = `🔧 Конфигурация:\n`;
  msg += `URL: ${cfg.baseUrl}\n`;
  msg += `Ключ: ${cfg.apiKey ? cfg.apiKey.slice(0, 8) + '...' : '(не задан)'}\n`;
  msg += `Сервис: ${cfg.service}\n`;
  msg += `Страна: ${cfg.country}\n\n`;

  msg += `📡 Доступные методы API:\n`;
  msg += `• getNumber - получить номер\n`;
  msg += `• getStatus - проверить СМС\n`;
  msg += `• setStatus - изменить статус\n`;
  msg += `• getBalance - баланс\n`;
  msg += `• getCountries - список стран\n`;
  msg += `• getServiceName - имя сервиса\n\n`;

  try {
    const resp = apiCall_('getBalance', {});
    msg += `✅ Баланс: ${resp}`;
  } catch (e) {
    msg += `❌ Ошибка: ${e.message}`;
  }

  ui.alert(msg);
}

/** ===================== ДИАГНОСТИКА ===================== */
function diagnoseApi() {
  const ui = SpreadsheetApp.getUi();
  const cfg = getConfig_();

  // Создаём лист для логов
  const ss = SpreadsheetApp.getActive();
  let logSheet = ss.getSheetByName('API Диагностика');
  if (!logSheet) {
    logSheet = ss.insertSheet('API Диагностика');
  }
  logSheet.clear();
  logSheet.getRange(1, 1, 1, 4).setValues([['Время', 'Запрос', 'HTTP код', 'Ответ (сырой)']]);
  logSheet.setFrozenRows(1);

  const log = (action, params, code, response) => {
    const url = `${cfg.baseUrl}?api_key=***&action=${action}&${Object.entries(params).map(([k,v])=>`${k}=${v}`).join('&')}`;
    logSheet.appendRow([new Date(), url, code, response.slice(0, 50000)]);
  };

  let row = 2;

  // 1. Тест getBalance
  try {
    const url = `${cfg.baseUrl}?api_key=${encodeURIComponent(cfg.apiKey)}&action=getBalance`;
    const resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    log('getBalance', {}, resp.getResponseCode(), resp.getContentText());
  } catch (e) {
    log('getBalance', {}, 'ERR', e.message);
  }

  // 2. Тест getCountries
  try {
    const url = `${cfg.baseUrl}?api_key=${encodeURIComponent(cfg.apiKey)}&action=getCountries`;
    const resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    log('getCountries', {}, resp.getResponseCode(), resp.getContentText());
  } catch (e) {
    log('getCountries', {}, 'ERR', e.message);
  }

  // 3. Тест getStatus для всех номеров из таблицы
  const numSheet = ss.getSheetByName(SHEET_NUMBERS);
  if (numSheet && numSheet.getLastRow() >= 2) {
    const ids = numSheet.getRange(2, 1, numSheet.getLastRow() - 1, 1).getValues().flat().filter(id => id);

    for (const id of ids.slice(0, 10)) { // Максимум 10 номеров
      try {
        const url = `${cfg.baseUrl}?api_key=${encodeURIComponent(cfg.apiKey)}&action=getStatus&id=${encodeURIComponent(id)}`;
        const resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
        log('getStatus', { id }, resp.getResponseCode(), resp.getContentText());
      } catch (e) {
        log('getStatus', { id }, 'ERR', e.message);
      }
      Utilities.sleep(300);
    }
  }

  logSheet.autoResizeColumns(1, 4);
  ss.setActiveSheet(logSheet);

  ui.alert(`✅ Диагностика завершена!\n\nРезультаты в листе «API Диагностика».\nПосмотрите колонку "Ответ (сырой)" — там видно что реально возвращает API.`);
}

/** ===================== ПРОВЕРИТЬ ОДИН НОМЕР (ручной ввод ID) ===================== */
function checkSingleNumber() {
  const ui = SpreadsheetApp.getUi();
  const cfg = getConfig_();

  const resp = ui.prompt('Проверка номера', 'Введите ID активации:', ui.ButtonSet.OK_CANCEL);
  if (resp.getSelectedButton() !== ui.Button.OK) return;

  const id = resp.getResponseText().trim();
  if (!id) { ui.alert('ID не указан!'); return; }

  try {
    const url = `${cfg.baseUrl}?api_key=${encodeURIComponent(cfg.apiKey)}&action=getStatus&id=${encodeURIComponent(id)}`;
    const httpResp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    const code = httpResp.getResponseCode();
    const text = httpResp.getContentText();

    ui.alert(`🔍 Результат проверки ID: ${id}\n\nHTTP код: ${code}\n\nОтвет API:\n${text}`);
  } catch (e) {
    ui.alert(`❌ Ошибка: ${e.message}`);
  }
}

/** ===================== ПРОВЕРИТЬ СМС ПО НОМЕРУ ТЕЛЕФОНА ===================== */
function checkByPhoneNumber() {
  const ui = SpreadsheetApp.getUi();
  const cfg = getConfig_();

  const resp = ui.prompt('Проверка по номеру телефона', 'Введите номер телефона:', ui.ButtonSet.OK_CANCEL);
  if (resp.getSelectedButton() !== ui.Button.OK) return;

  const phone = resp.getResponseText().trim().replace(/\D/g, ''); // Только цифры
  if (!phone) { ui.alert('Номер не указан!'); return; }

  // Ищем номер в таблице
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NUMBERS);
  if (!sh || sh.getLastRow() < 2) {
    ui.alert('Таблица номеров пуста!');
    return;
  }

  const data = sh.getRange(2, 1, sh.getLastRow() - 1, 6).getValues();
  let found = null;
  let foundRow = -1;

  for (let i = 0; i < data.length; i++) {
    const numInTable = String(data[i][1]).replace(/\D/g, '');
    if (numInTable === phone || numInTable.endsWith(phone) || phone.endsWith(numInTable)) {
      found = { id: data[i][0], number: data[i][1], service: data[i][2], status: data[i][3], code: data[i][4], text: data[i][5] };
      foundRow = i + 2;
      break;
    }
  }

  if (!found) {
    ui.alert(`❌ Номер ${phone} не найден в таблице «Номера».\n\nСначала получите этот номер через меню.`);
    return;
  }

  // Запрашиваем статус у API
  try {
    const url = `${cfg.baseUrl}?api_key=${encodeURIComponent(cfg.apiKey)}&action=getStatus&id=${encodeURIComponent(found.id)}`;
    const httpResp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    const httpCode = httpResp.getResponseCode();
    const text = httpResp.getContentText().trim();

    let msg = `🔍 Проверка номера: ${found.number}\n`;
    msg += `🆔 ID активации: ${found.id}\n`;
    msg += `📦 Сервис: ${found.service}\n`;
    msg += `📊 Статус в таблице: ${found.status}\n\n`;
    msg += `━━━━━━━━━━━━━━━━━━━━━\n`;
    msg += `📡 Ответ API (HTTP ${httpCode}):\n${text}\n`;
    msg += `━━━━━━━━━━━━━━━━━━━━━\n\n`;

    // Парсим ответ и обновляем таблицу
    const r = parseResp_(text);
    let newStatus = found.status;
    let newCode = found.code || '';
    let newText = found.text || '';

    if (r.status) {
      switch (r.status) {
        case 'STATUS_WAIT_CODE':
          newStatus = 'Ожидание СМС';
          msg += '⏳ СМС ещё не пришло';
          break;
        case 'STATUS_OK':
          newStatus = 'Код получен';
          newCode = r.code || '';
          msg += `✅ КОД ПОЛУЧЕН: ${newCode}`;
          break;
        case 'STATUS_CANCEL':
          newStatus = 'Отменено';
          msg += '❌ Активация отменена';
          break;
        default:
          msg += `ℹ️ Статус: ${r.status}`;
      }
    } else if (r.json && r.data) {
      if (r.data.smsCode) {
        newCode = Array.isArray(r.data.smsCode) ? r.data.smsCode.join(', ') : r.data.smsCode;
        newText = r.data.smsText || '';
        newStatus = 'Код получен';
        msg += `✅ КОД ПОЛУЧЕН: ${newCode}`;
        if (newText) msg += `\n📝 Текст: ${newText}`;
      } else {
        msg += '⏳ СМС ещё не пришло';
      }
    } else if (text === 'STATUS_WAIT_CODE') {
      newStatus = 'Ожидание СМС';
      msg += '⏳ СМС ещё не пришло';
    } else if (text === 'NO_ACTIVATION') {
      newStatus = 'Не найдено';
      msg += '❌ Активация не найдена на сервере';
    }

    // Обновляем таблицу
    if (foundRow > 0) {
      sh.getRange(foundRow, 4).setValue(newStatus);
      if (newCode) sh.getRange(foundRow, 5).setValue(newCode);
      if (newText) sh.getRange(foundRow, 6).setValue(newText);

      // Если новый код — пишем в журнал
      if (newCode && newCode !== found.code) {
        appendToLogNoDup_([{
          received_at: new Date(),
          number: found.number,
          service: found.service,
          code: newCode,
          text: newText,
          activation_id: found.id
        }]);
        msg += '\n\n📝 Код записан в журнал СМС';
      }
    }

    ui.alert(msg);

  } catch (e) {
    ui.alert(`❌ Ошибка запроса: ${e.message}`);
  }
}
