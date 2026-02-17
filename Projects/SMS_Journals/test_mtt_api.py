#!/usr/bin/env python3
"""
Тест API МТТ: GetNumbers и GetMessagesHistoryList.
Проверяет, доходят ли запросы до оператора и что возвращает API.
Токен: из переменной MTT_MSAPI_TOKEN или аргумента --token.
CUSTOMER_NAME: из MTT_CUSTOMER_NAME или --customer (для истории обязателен).
"""
import os
import sys
import json
import argparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

MTT_BASE = "https://api.mtt.ru/ms-customer-gateway"


def request(path: str, token: str, body: dict) -> tuple[int, dict | str]:
    url = f"{MTT_BASE}{path}"
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8")
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, raw
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, body
    except URLError as e:
        return -1, str(e.reason)


def main():
    ap = argparse.ArgumentParser(description="Тест MTT API")
    ap.add_argument("--token", default=os.environ.get("MTT_MSAPI_TOKEN"), help="Bearer токен")
    ap.add_argument("--customer", default=os.environ.get("MTT_CUSTOMER_NAME"), help="Лицевой счёт (для истории)")
    ap.add_argument("--limit", type=int, default=10, help="Лимит сообщений в истории")
    args = ap.parse_args()

    if not args.token:
        print("Задайте токен: MTT_MSAPI_TOKEN или --token")
        sys.exit(1)

    print("=" * 60)
    print("1. GetNumbers (проверка токена и список номеров)")
    print("=" * 60)
    code, data = request("/v1/GetNumbers", args.token, {"limit": 100, "offset": 0})
    print(f"HTTP: {code}")
    if isinstance(data, dict):
        numbers = data.get("numbers") or []
        total = data.get("total")
        print(f"Номеров: {len(numbers)}" + (f" (всего {total})" if total is not None else ""))
        if numbers:
            n0 = numbers[0]
            print(f"Первый номер: {n0.get('number')}, customer_name: {n0.get('customer_name')}")
            # Для истории часто нужен customer_name с первого номера
            suggested = n0.get("customer_name") or ""
            if suggested and not args.customer:
                print(f"  → Рекомендуемый CUSTOMER_NAME для истории: {repr(suggested)}")
        else:
            print("Список номеров пуст.")
        if code != 200:
            print("Тело ответа:", json.dumps(data, ensure_ascii=False, indent=2)[:500])
    else:
        print("Ответ (не JSON):", str(data)[:400])

    customer = args.customer
    if not customer and isinstance(data, dict) and (data.get("numbers") or []):
        customer = (data["numbers"][0].get("customer_name") or "").strip()
    if not customer:
        print("\nCUSTOMER_NAME не задан. Для GetMessagesHistoryList укажите --customer или MTT_CUSTOMER_NAME.")
    else:
        print("\n" + "=" * 60)
        print("2. GetMessagesHistoryList (история SMS)")
        print("=" * 60)
        body = {
            "customer_name": customer,
            "limit": args.limit,
            "offset": 0,
            "direction": "incoming",
        }
        code2, data2 = request("/v1/GetMessagesHistoryList", args.token, body)
        print(f"HTTP: {code2}")
        if isinstance(data2, dict):
            lst = data2.get("list")
            if lst is None:
                print("В ответе нет поля 'list'. Ключи:", list(data2.keys()))
                print("Полный ответ:", json.dumps(data2, ensure_ascii=False, indent=2)[:1500])
            else:
                print(f"SMS в ответе: {len(lst)}")
                for i, m in enumerate(lst[:5]):
                    print(f"  [{i+1}] event_date={m.get('event_date')} number={m.get('number')} sender={m.get('sender')}")
                    print(f"       text={repr((m.get('text') or m.get('body') or m.get('message') or '')[:80])}")
                    print(f"       keys={list(m.keys())}")
                if len(lst) > 5:
                    print(f"  ... и ещё {len(lst) - 5}")
                if not lst:
                    print("История пуста. Возможные причины: неверный CUSTOMER_NAME, SMS не приходили или API не отдаёт.")
                else:
                    print(f"\n  OK: API отдаёт SMS. Для таблицы в Script Properties задайте CUSTOMER_NAME = {repr(customer)}")
        else:
            print("Ответ (не JSON):", str(data2)[:500])

    print("\n" + "=" * 60)
    print("Итог: проблема на стороне оператора (API) или нашей (таблица/скрипт)?")
    print("  - Если GetNumbers HTTP != 200 или GetMessagesHistoryList пустой/ошибка — проверьте токен и CUSTOMER_NAME.")
    print("  - Если API возвращает list с данными — скрипт в таблице должен их писать; проверьте Script Properties (MSAPI_TOKEN, CUSTOMER_NAME) и лист «Журнал СМС».")
    print("=" * 60)


if __name__ == "__main__":
    main()
