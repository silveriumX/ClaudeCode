/** ===================== КОНФИГ ===================== */
const SHEET_NUMBERS = 'Номера';      // список номеров
const SHEET_LOG     = 'Журнал СМС';  // журнал входящих (4 колонки)
const LOG_HEADERS = ['Дата/время получения','Номер-получатель','Отправитель','Текст СМС'];

/** ===================== МЕНЮ ===================== */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📲 СМС')
    .addItem('🔁 Получить список номеров (МТТ)', 'fetchNumbersFromMTT')
    .addItem('🧩 Подключить уведомления на номерах (MTT)', 'configureEventWebhookForAllNumbers')
    .addItem('▶️ Продолжить подключение уведомлений', 'continueWebhookSetup')
    .addSeparator()
    .addItem('⬇ Загрузить историю (МТТ)', 'backfillHistoryMTT')
    .addSeparator()
    .addItem('🔗 Показать URL веб-хука (Web App)', 'showWebAppUrl')
    .addItem('🔍 Диагностика веб-хука', 'diagnoseWebhook')
    .addItem('🧪 Тестовая запись в журнал', 'testAppend')
    .addToUi();
  ensureSheets_();
}

/** ===================== ИНИЦИАЛИЗАЦИЯ ЛИСТОВ ===================== */
function ensureSheets_() {
  const ss = SpreadsheetApp.getActive();
  if (!ss.getSheetByName(SHEET_NUMBERS)) ss.insertSheet(SHEET_NUMBERS);
  let log = ss.getSheetByName(SHEET_LOG);
  if (!log) log = ss.insertSheet(SHEET_LOG);
  const firstRow = log.getRange(1, 1, 1, LOG_HEADERS.length).getValues()[0];
  if (firstRow.join('') === '') {
    log.getRange(1, 1, 1, LOG_HEADERS.length).setValues([LOG_HEADERS]);
    log.setFrozenRows(1);
    log.getRange('A:A').setNumberFormat('yyyy-mm-dd HH:mm:ss');
    log.autoResizeColumns(1, LOG_HEADERS.length);
  }
}

/** ===================== ПОЛУЧИТЬ НОМЕРА (МТТ /v1/GetNumbers) ===================== */
function fetchNumbersFromMTT() {
  ensureSheets_();
  const props = PropertiesService.getScriptProperties();
  const API_TOKEN = props.getProperty('MSAPI_TOKEN');
  const CUSTOMER_NAME = props.getProperty('CUSTOMER_NAME'); // опционально
  const MTT_BASE  = (props.getProperty('MTT_BASE') || 'https://api.mtt.ru/ms-customer-gateway').replace(/\/+$/,'');

  if (!API_TOKEN) throw new Error('Не задан MSAPI_TOKEN в Script Properties.');

  const url = `${MTT_BASE}/v1/GetNumbers`;
  const LIMIT = 10000;
  let offset = 0, total = null;
  const all = [];

  while (true) {
    const body = { limit: LIMIT, offset };
    if (CUSTOMER_NAME) body.customer_name = CUSTOMER_NAME;

    const resp = UrlFetchApp.fetch(url, {
      method: 'post',
      contentType: 'application/json',
      headers: { 'Authorization': `Bearer ${API_TOKEN}` },
      muteHttpExceptions: true,
      payload: JSON.stringify(body),
    });
    if (resp.getResponseCode() !== 200) {
      throw new Error(`GetNumbers HTTP ${resp.getResponseCode()}: ${resp.getContentText()}`);
    }
    const data = safeJson_(resp.getContentText());
    const batch = Array.isArray(data.numbers) ? data.numbers : [];
    total = total == null ? (data.total || batch.length) : total;
    all.push(...batch);
    if (batch.length < LIMIT || all.length >= total) break;
    offset += LIMIT;
    Utilities.sleep(150);
  }

  writeNumbersSheetFromGetNumbers_(all);
  SpreadsheetApp.getUi().alert(`Загружено номеров: ${all.length}${total ? ` (из ${total})` : ''}`);
}

function writeNumbersSheetFromGetNumbers_(items) {
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NUMBERS);
  sh.clear();
  const header = ['Номер','Альфа-имя?','Event URL','Шлюз','Направление','Лицевой счёт'];
  sh.getRange(1,1,1,header.length).setValues([header]);
  const rows = (items||[]).map(x => [
    sanitizeNumber_(String(x.number || '')),
    x.is_alpha_name ? 'да' : 'нет',
    x.event_url || '',
    x.allowed_gateway || '',
    x.direction || '',
    x.customer_name || ''
  ]);
  if (rows.length) sh.getRange(2,1,rows.length,header.length).setValues(rows);
  sh.setFrozenRows(1);
  sh.autoResizeColumns(1, header.length);
}

/** ===================== ВКЛЮЧИТЬ ВЕБ-ХУКИ (МТТ /v1/SetNumberSettings) ===================== */
function configureEventWebhookForAllNumbers() {
  ensureSheets_();
  const props = PropertiesService.getScriptProperties();
  const API_TOKEN = props.getProperty('MSAPI_TOKEN');
  const WEBHOOK_SECRET = props.getProperty('WEBHOOK_SECRET');
  const MTT_BASE = (props.getProperty('MTT_BASE') || 'https://api.mtt.ru/ms-customer-gateway').replace(/\/+$/,'');
  const webAppUrl = ScriptApp.getService().getUrl();

  if (!API_TOKEN) throw new Error('Не задан MSAPI_TOKEN.');
  if (!WEBHOOK_SECRET) throw new Error('Не задан WEBHOOK_SECRET.');
  if (!webAppUrl) throw new Error('Web App ещё не опубликован. Deploy → Web app.');

  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NUMBERS);
  const last = sh.getLastRow();
  if (last < 2) {
    SpreadsheetApp.getUi().alert('В листе «Номера» нет данных. Сначала загрузите их.');
    return;
  }

  const range = sh.getRange(2,1,last-1,2).getValues(); // A: номер, B: альфа?
  const statusCol = ensureWebhookStatusColumn_(sh);
  const eventUrl = `${webAppUrl}?key=${encodeURIComponent(WEBHOOK_SECRET)}`;

  let ok = 0, fail = 0;
  for (let i = 0; i < range.length; i++) {
    const row = 2 + i;
    const num = sanitizeNumber_(String(range[i][0] || ''));
    const isAlpha = (String(range[i][1] || '').toLowerCase() === 'да');
    if (!num || isAlpha) {
      sh.getRange(row, statusCol).setValue(isAlpha ? 'пропущен (альфа-имя)' : 'нет номера');
      continue;
    }
    sh.getRange(row, statusCol).setValue('▶ подключаю…'); SpreadsheetApp.flush();
    try {
      setNumberSettings_(MTT_BASE, API_TOKEN, { number: num, event_url: eventUrl });
      sh.getRange(row, statusCol).setValue('OK'); ok++;
    } catch (e) {
      sh.getRange(row, statusCol).setValue(`ERR: ${String(e).slice(0,120)}`); fail++;
    }
    Utilities.sleep(200);
  }
  SpreadsheetApp.getUi().alert(`ГОТОВО:\nПодключено: ${ok}\nОшибок: ${fail}`);
}

/** ===================== ПРОДОЛЖИТЬ ПОДКЛЮЧЕНИЕ ВЕБ-ХУКОВ ===================== */
/**
 * Продолжает подключение веб-хуков с того места, где остановились.
 * Пропускает строки, где статус уже "OK" или "пропущен (альфа-имя)".
 */
function continueWebhookSetup() {
  ensureSheets_();
  const props = PropertiesService.getScriptProperties();
  const API_TOKEN = props.getProperty('MSAPI_TOKEN');
  const WEBHOOK_SECRET = props.getProperty('WEBHOOK_SECRET');
  const MTT_BASE = (props.getProperty('MTT_BASE') || 'https://api.mtt.ru/ms-customer-gateway').replace(/\/+$/,'');
  const webAppUrl = ScriptApp.getService().getUrl();

  if (!API_TOKEN) throw new Error('Не задан MSAPI_TOKEN.');
  if (!WEBHOOK_SECRET) throw new Error('Не задан WEBHOOK_SECRET.');
  if (!webAppUrl) throw new Error('Web App ещё не опубликован.');

  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NUMBERS);
  const last = sh.getLastRow();
  if (last < 2) {
    SpreadsheetApp.getUi().alert('В листе «Номера» нет данных.');
    return;
  }

  // Находим колонку статуса
  const header = sh.getRange(1,1,1,Math.max(1, sh.getLastColumn())).getValues()[0];
  let statusCol = header.findIndex(h => String(h).trim().toLowerCase() === 'webhook статус') + 1;
  if (!statusCol) {
    statusCol = header.length + 1;
    sh.getRange(1, statusCol).setValue('Webhook статус');
  }

  // Читаем данные: номер, альфа?, статус
  const dataRange = sh.getRange(2, 1, last - 1, Math.max(statusCol, 2));
  const data = dataRange.getValues();

  const eventUrl = `${webAppUrl}?key=${encodeURIComponent(WEBHOOK_SECRET)}`;

  // Статусы, которые считаем "уже обработано"
  const skipStatuses = ['ok', 'пропущен (альфа-имя)', 'нет номера'];

  let ok = 0, fail = 0, skipped = 0;
  const startTime = Date.now();
  const TIME_LIMIT = 5 * 60 * 1000; // 5 минут (с запасом до 6)

  for (let i = 0; i < data.length; i++) {
    // Проверяем таймаут
    if (Date.now() - startTime > TIME_LIMIT) {
      SpreadsheetApp.getUi().alert(
        `⏱ Таймаут! Обработано: ${ok + fail + skipped} из ${data.length}\n` +
        `✅ Подключено: ${ok}\n❌ Ошибок: ${fail}\n⏭ Пропущено: ${skipped}\n\n` +
        `Нажмите «Продолжить подключение» ещё раз.`
      );
      return;
    }

    const row = 2 + i;
    const num = sanitizeNumber_(String(data[i][0] || ''));
    const isAlpha = (String(data[i][1] || '').toLowerCase() === 'да');
    const currentStatus = String(data[i][statusCol - 1] || '').toLowerCase().trim();

    // Пропускаем уже обработанные
    if (skipStatuses.includes(currentStatus)) {
      skipped++;
      continue;
    }

    // Пропускаем альфа-имена и пустые
    if (!num) {
      sh.getRange(row, statusCol).setValue('нет номера');
      skipped++;
      continue;
    }
    if (isAlpha) {
      sh.getRange(row, statusCol).setValue('пропущен (альфа-имя)');
      skipped++;
      continue;
    }

    // Подключаем веб-хук
    sh.getRange(row, statusCol).setValue('▶ подключаю…');
    SpreadsheetApp.flush();

    try {
      setNumberSettings_(MTT_BASE, API_TOKEN, { number: num, event_url: eventUrl });
      sh.getRange(row, statusCol).setValue('OK');
      ok++;
    } catch (e) {
      sh.getRange(row, statusCol).setValue(`ERR: ${String(e).slice(0,120)}`);
      fail++;
    }

    Utilities.sleep(200);
  }

  SpreadsheetApp.getUi().alert(
    `✅ ГОТОВО!\n\nПодключено: ${ok}\nОшибок: ${fail}\nПропущено (уже было): ${skipped}`
  );
}

function ensureWebhookStatusColumn_(sh) {
  const header = sh.getRange(1,1,1,Math.max(1, sh.getLastColumn())).getValues()[0];
  let col = header.findIndex(h => String(h).trim().toLowerCase() === 'webhook статус') + 1;
  if (!col) {
    col = header.length + 1;
    sh.getRange(1,col).setValue('Webhook статус');
    sh.setFrozenRows(1);
  }
  return col;
}

function setNumberSettings_(base, token, payload) {
  const resp = UrlFetchApp.fetch(`${base}/v1/SetNumberSettings`, {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': `Bearer ${token}` },
    muteHttpExceptions: true,
    payload: JSON.stringify(payload),
  });
  const code = resp.getResponseCode();
  if (code < 200 || code >= 300) throw new Error(`HTTP ${code}: ${resp.getContentText()}`);
}

/** ===================== ИСТОРИЯ СМС (МТТ /v1/GetMessagesHistoryList) ===================== */
/**
 * Script Properties (минимум):
 *  - MSAPI_TOKEN      — Bearer токен
 *  - CUSTOMER_NAME    — наименование лицевого счёта (обязателен для этого метода)
 * Необязательные фильтры (если нужно):
 *  - HISTORY_PAGE_SIZE  (1..10000, по умолчанию 1000)
 *  - HISTORY_SINCE      -> event_date_gt (ISO 8601, напр. 2024-01-01T00:00:00Z)
 *  - HISTORY_UNTIL      -> event_date_lt (ISO 8601)
 *  - HISTORY_NUMBER     -> number (конкретный номер/альфа-имя)
 *  - HISTORY_DIRECTION  -> direction (incoming|outgoing)
 *  - HISTORY_DELIVERY   -> delivery_status (queued|transmitted|delivered|failed)
 *  - HISTORY_BILLING    -> billing_status (prebilled|billed|underfunded|failed|authorized)
 */
function backfillHistoryMTT() {
  ensureSheets_();
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty('MSAPI_TOKEN');
  const customer = props.getProperty('CUSTOMER_NAME');
  const MTT_BASE = (props.getProperty('MTT_BASE') || 'https://api.mtt.ru/ms-customer-gateway').replace(/\/+$/,'');
  const pageSize = Math.min(10000, Math.max(1, parseInt(props.getProperty('HISTORY_PAGE_SIZE') || '1000', 10)));

  if (!token)   throw new Error('Нет MSAPI_TOKEN.');
  if (!customer) throw new Error('Нет CUSTOMER_NAME (обязателен для истории).');

  const url = `${MTT_BASE}/v1/GetMessagesHistoryList`;
  let offset = 0, addedTotal = 0;

  while (true) {
    const body = {
      customer_name: customer,
      limit: pageSize,
      offset: offset
    };

    // Необязательные фильтры
    const since = props.getProperty('HISTORY_SINCE');
    const until = props.getProperty('HISTORY_UNTIL');
    const number = props.getProperty('HISTORY_NUMBER');
    const direction = props.getProperty('HISTORY_DIRECTION');
    const delivery = props.getProperty('HISTORY_DELIVERY');
    const billing = props.getProperty('HISTORY_BILLING');

    if (since) body.event_date_gt = since;
    if (until) body.event_date_lt = until;
    if (number) body.number = number;
    if (direction) body.direction = direction;
    if (delivery) body.delivery_status = delivery;
    if (billing) body.billing_status = billing;

    const resp = UrlFetchApp.fetch(url, {
      method: 'post', contentType: 'application/json', muteHttpExceptions: true,
      headers: { 'Authorization': `Bearer ${token}` },
      payload: JSON.stringify(body),
    });

    if (resp.getResponseCode() !== 200) {
      throw new Error(`GetMessagesHistoryList HTTP ${resp.getResponseCode()}:\n${resp.getContentText()}`);
    }

    const data = safeJson_(resp.getContentText());
    const list = Array.isArray(data.list) ? data.list : [];
    if (!list.length) break;

    // Мэппинг под наш журнал: ts, to, from, text
    const prepared = list.map(m => {
      const dir = (m.direction || '').toLowerCase();
      let to = '', from = '';
      if (dir === 'incoming') {
        to   = sanitizeNumber_(m.number || m.receiver || '');
        from = sanitizeNumber_(m.sender || '');
      } else {
        to   = sanitizeNumber_(m.receiver || '');
        from = sanitizeNumber_(m.number || m.sender || '');
      }
      return {
        received_at: normalizeTime_(m.event_date),
        to, from,
        text: String(m.text || '')
      };
    }).filter(x => x.to || x.from || x.text);

    const added = appendToLogNoDup_(prepared);
    addedTotal += added;

    if (list.length < pageSize) break;
    offset += pageSize;
    Utilities.sleep(150);
  }

  SpreadsheetApp.getUi().alert(`Готово. Добавлено в «Журнал СМС»: ${addedTotal} записей.`);
}

/** ===================== ДОБАВЛЕНИЕ В ЖУРНАЛ БЕЗ ДУБЛЕЙ ===================== */
function appendToLogNoDup_(messages) {
  if (!messages.length) return 0;
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_LOG);

  // Собираем ключи уже существующих сообщений (на основе 4 полей журнала)
  const last = sh.getLastRow();
  const existingKeys = new Set();
  if (last >= 2) {
    const existed = sh.getRange(2,1,last-1,4).getValues();
    for (const r of existed) {
      const key = makeKey_(r[0], r[1], r[2], r[3]);
      existingKeys.add(key);
    }
  }

  // Готовим строки, фильтруя дубли
  const toAppend = [];
  for (const m of messages) {
    const ts = m.received_at instanceof Date ? m.received_at : normalizeTime_(m.received_at);
    const key = makeKey_(ts, m.to, m.from, m.text);
    if (existingKeys.has(key)) continue;
    existingKeys.add(key);
    toAppend.push([ts, m.to, m.from, m.text]);
  }

  if (!toAppend.length) return 0;
  sh.getRange(sh.getLastRow()+1, 1, toAppend.length, 4).setValues(toAppend);
  return toAppend.length;
}

function makeKey_(ts, to, from, text) {
  const d = (ts instanceof Date) ? ts.toISOString() : String(ts || '');
  return [d, String(to||''), String(from||''), String(text||'')].join('•');
}

/** ===================== ВЕБ-ХУК (ПРИЁМ ВХОДЯЩИХ) ===================== */
function doPost(e) {
  try {
    ensureSheets_();
    const props = PropertiesService.getScriptProperties();
    const WEBHOOK_SECRET = props.getProperty('WEBHOOK_SECRET');
    const key = e && e.parameter ? e.parameter.key : '';
    if (!WEBHOOK_SECRET || key !== WEBHOOK_SECRET) return json_({ ok:false, error:'unauthorized' });

    const payload = parseIncoming_(e);
    const received = normalizeTime_(
      payload.received_at || payload.timestamp || payload.time || payload.date
      || (payload.event && (payload.event.received_at || payload.event.timestamp))
      || (payload.message && payload.message.timestamp)
    );
    const to = sanitizeNumber_(payload.to || payload.destination || (payload.event && payload.event.to) || (payload.message && payload.message.to) || '');
    const from = sanitizeNumber_(payload.from || payload.sender || (payload.event && payload.event.from) || (payload.message && payload.message.from) || '');
    const text = payload.text || (payload.message && (payload.message.text || payload.message.body)) || JSON.stringify(payload);

    appendToLogNoDup_([{ received_at: received, to, from, text }]);
    return json_({ ok:true });
  } catch (err) {
    return json_({ ok:false, error:String(err) });
  }
}

/** ===================== УТИЛИТЫ ===================== */
function sanitizeNumber_(val) {
  const digits = String(val||'').replace(/\D+/g,'');
  if (!digits) return '';
  if (digits.length === 11 && digits.startsWith('8')) return '7' + digits.slice(1);
  return digits;
}
function parseIncoming_(e) {
  if (e && e.postData && e.postData.contents) {
    try { return JSON.parse(e.postData.contents); }
    catch (_) {
      const params = e.parameter || {}; const obj = {};
      Object.keys(params).forEach(k => obj[k] = params[k]); return obj;
    }
  }
  return e && e.parameter ? e.parameter : {};
}
function normalizeTime_(val) {
  if (!val) return new Date();
  if (val instanceof Date) return val;
  if (typeof val === 'number') return new Date(val < 2e10 ? val*1000 : val);
  const d = new Date(val); return isNaN(d.getTime()) ? new Date() : d;
}
function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
function showWebAppUrl() {
  const url = ScriptApp.getService().getUrl();
  SpreadsheetApp.getUi().alert(
    url ? `URL вашего веб-хука:\n\n${url}\n\nПередайте его провайдеру.` :
          'Скрипт ещё не опубликован как Web App. Deploy → Manage deployments.'
  );
}
function testAppend() {
  appendToLogNoDup_([{ received_at: new Date(), to: '79991234567', from: '71112223344', text: 'Тестовое сообщение' }]);
  SpreadsheetApp.getUi().alert('Тестовая запись добавлена.');
}
function safeJson_(t){ try { return JSON.parse(t); } catch(e){ return {}; } }

/** ===================== ДИАГНОСТИКА ВЕБ-ХУКА ===================== */
function diagnoseWebhook() {
  ensureSheets_();
  const ui = SpreadsheetApp.getUi();

  const props = PropertiesService.getScriptProperties();
  const webAppUrl = ScriptApp.getService().getUrl();
  const secret = props.getProperty('WEBHOOK_SECRET') || '';
  if (!webAppUrl) { ui.alert('Web App не опубликован. Deploy → Web app.'); return; }
  if (!secret) { ui.alert('В Script Properties не задан WEBHOOK_SECRET.'); return; }

  const sh = SpreadsheetApp.getActive().getSheetByName(SHEET_NUMBERS);
  let eventUrlFromSheet = '';
  if (sh && sh.getLastRow() >= 2) {
    const header = sh.getRange(1,1,1,Math.max(1, sh.getLastColumn())).getValues()[0].map(String);
    let c = header.findIndex(h => h.toLowerCase().indexOf('event url') !== -1) + 1;
    if (c > 0) {
      const vals = sh.getRange(2,c,sh.getLastRow()-1,1).getValues().flat().map(v => String(v||'').trim());
      eventUrlFromSheet = vals.find(v => v) || '';
    }
  }
  const expectedUrl = `${webAppUrl}?key=${encodeURIComponent(secret)}`;

  let msg = `Текущий Web App URL:\n${webAppUrl}\n\nОжидаемый event_url:\n${expectedUrl}\n`;
  if (eventUrlFromSheet) msg += `\nEvent URL из листа «Номера»:\n${eventUrlFromSheet}\n`;
  else msg += `\nВ листе «Номера» не найден Event URL. Перепропишите кнопкой «Подключить уведомления…».`;

  let postResult = '';
  try {
    const target = eventUrlFromSheet || expectedUrl;
    const resp = UrlFetchApp.fetch(target, {
      method: 'post',
      contentType: 'application/json',
      muteHttpExceptions: true,
      payload: JSON.stringify({
        received_at: new Date().toISOString(),
        to: '79990000000',
        from: '79991111111',
        text: 'diag-ping'
      })
    });
    postResult = `POST ${target}\nHTTP ${resp.getResponseCode()}\n${resp.getContentText().slice(0,200)}…`;
  } catch (e) {
    postResult = `POST ошибка: ${String(e)}`;
  }

  ui.alert(`${msg}\n\nТест POST:\n${postResult}\n\nЕсли HTTP не 200, проверьте доступ Web App (Anyone/Anyone with the link) или секрет ?key=…`);
}

/** ===================== doGet для пингов/проверок ===================== */
function doGet(e) {
  try {
    if (shouldLogRaw_()) logRaw_(e, 'GET');
    return ContentService.createTextOutput(JSON.stringify({ok:true, method:'GET'}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok:false, error:String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/** ===================== Доп. логирование сырых запросов (для диагностики) ===================== */
function shouldLogRaw_() {
  const v = (PropertiesService.getScriptProperties().getProperty('LOG_WEBHOOK_RAW') || '').trim();
  return v === '1' || v.toLowerCase() === 'true';
}
function logRaw_(e, tag) {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName('Webhook RAW');
  if (!sh) {
    sh = ss.insertSheet('Webhook RAW');
    sh.getRange(1,1,1,5).setValues([['when','method','query.key','contentType','body']]);
    sh.setFrozenRows(1);
  }
  const when = new Date();
  const key = e && e.parameter ? (e.parameter.key || '') : '';
  const ct = e && e.postData ? (e.postData.type || '') : '';
  const body = e && e.postData ? (e.postData.contents || '') : JSON.stringify(e && e.parameter ? e.parameter : {});
  sh.appendRow([when, tag || 'POST', key, ct, body.slice(0, 50000)]);
}

/** ===================== АВТОМАТИЧЕСКИЙ ТРИГГЕР (опционально) ===================== */

/**
 * Запустите эту функцию ОДИН РАЗ вручную, чтобы создать триггер.
 * После этого скрипт будет сам проверять номера каждый час.
 */
function setupAutoRefreshTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'autoRefreshNumbersAndWebhooks') {
      ScriptApp.deleteTrigger(t);
    }
  });

  ScriptApp.newTrigger('autoRefreshNumbersAndWebhooks')
    .timeBased()
    .everyHours(1)
    .create();

  SpreadsheetApp.getUi().alert('✅ Триггер создан! Номера будут обновляться каждый час.');
}

/**
 * Автоматически обновляет список номеров и подключает веб-хуки на новых.
 * Вызывается триггером.
 */
function autoRefreshNumbersAndWebhooks() {
  try {
    ensureSheets_();
    const props = PropertiesService.getScriptProperties();
    const API_TOKEN = props.getProperty('MSAPI_TOKEN');
    const WEBHOOK_SECRET = props.getProperty('WEBHOOK_SECRET');
    const MTT_BASE = (props.getProperty('MTT_BASE') || 'https://api.mtt.ru/ms-customer-gateway').replace(/\/+$/,'');
    const webAppUrl = ScriptApp.getService().getUrl();

    if (!API_TOKEN || !WEBHOOK_SECRET || !webAppUrl) {
      console.log('autoRefresh: не хватает настроек (TOKEN/SECRET/WebApp)');
      return;
    }

    const numbers = fetchNumbersFromMTT_silent_();
    if (!numbers.length) return;

    const expectedUrl = `${webAppUrl}?key=${encodeURIComponent(WEBHOOK_SECRET)}`;
    const toUpdate = numbers.filter(n => {
      if (n.is_alpha_name) return false;
      const currentUrl = (n.event_url || '').trim();
      return currentUrl !== expectedUrl;
    });

    let updated = 0;
    for (const n of toUpdate) {
      const num = sanitizeNumber_(String(n.number || ''));
      if (!num) continue;
      try {
        setNumberSettings_(MTT_BASE, API_TOKEN, { number: num, event_url: expectedUrl });
        updated++;
        Utilities.sleep(200);
      } catch (e) {
        console.log(`autoRefresh: ошибка для ${num}: ${e}`);
      }
    }

    writeNumbersSheetFromGetNumbers_(numbers);

    console.log(`autoRefresh: номеров ${numbers.length}, обновлено веб-хуков: ${updated}`);
  } catch (e) {
    console.log(`autoRefresh error: ${e}`);
  }
}

/**
 * Тихая версия fetchNumbersFromMTT — без alert, возвращает массив.
 */
function fetchNumbersFromMTT_silent_() {
  const props = PropertiesService.getScriptProperties();
  const API_TOKEN = props.getProperty('MSAPI_TOKEN');
  const CUSTOMER_NAME = props.getProperty('CUSTOMER_NAME');
  const MTT_BASE = (props.getProperty('MTT_BASE') || 'https://api.mtt.ru/ms-customer-gateway').replace(/\/+$/,'');

  if (!API_TOKEN) return [];

  const url = `${MTT_BASE}/v1/GetNumbers`;
  const LIMIT = 10000;
  let offset = 0;
  const all = [];

  while (true) {
    const body = { limit: LIMIT, offset };
    if (CUSTOMER_NAME) body.customer_name = CUSTOMER_NAME;

    const resp = UrlFetchApp.fetch(url, {
      method: 'post',
      contentType: 'application/json',
      headers: { 'Authorization': `Bearer ${API_TOKEN}` },
      muteHttpExceptions: true,
      payload: JSON.stringify(body),
    });

    if (resp.getResponseCode() !== 200) return all;

    const data = safeJson_(resp.getContentText());
    const batch = Array.isArray(data.numbers) ? data.numbers : [];
    all.push(...batch);

    if (batch.length < LIMIT) break;
    offset += LIMIT;
    Utilities.sleep(150);
  }

  return all;
}

/**
 * Удалить автоматический триггер
 */
function removeAutoRefreshTrigger() {
  let removed = 0;
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'autoRefreshNumbersAndWebhooks') {
      ScriptApp.deleteTrigger(t);
      removed++;
    }
  });
  SpreadsheetApp.getUi().alert(`Удалено триггеров: ${removed}`);
}
