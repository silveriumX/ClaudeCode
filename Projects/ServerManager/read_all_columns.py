#!/usr/bin/env python3
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('servermanagment.json', scope)
client = gspread.authorize(creds)

spreadsheet = client.open_by_key('1wIS9hjLSbIU4PSjXbXyIoh3_KHVBRaX2jDQVj4o51V8')
sheet = spreadsheet.get_worksheet(0)
data = sheet.get_all_values()

# Show all headers with indices
print("HEADERS:")
print("-" * 80)
headers = data[0]
for i, h in enumerate(headers):
    print(f"  [{i}] = {h[:40]}")

# Show row 3 (MN - 194.59.31.156)
print("\n" + "=" * 80)
print("ROW 3 (MN - 194.59.31.156) - ALL VALUES:")
print("=" * 80)
row3 = data[2]  # index 2 = row 3
for i, val in enumerate(row3):
    header = headers[i] if i < len(headers) else f'col_{i}'
    if val:  # only show non-empty
        print(f"  [{i}] {header[:30]:<30} = {val[:50]}")
