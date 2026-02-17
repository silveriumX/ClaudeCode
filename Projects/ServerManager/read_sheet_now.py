#!/usr/bin/env python3
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('servermanagment.json', scope)
client = gspread.authorize(creds)

spreadsheet = client.open_by_key('1wIS9hjLSbIU4PSjXbXyIoh3_KHVBRaX2jDQVj4o51V8')
sheet = spreadsheet.get_worksheet(0)
data = sheet.get_all_values()

print("=" * 90)
print("CURRENT DATA FROM GOOGLE SHEET")
print("=" * 90)
print()

# Headers are in row 0
headers = data[0]

# Find column indices
rdp_col = 6  # RDP IP:Username:Password
status_col = 7  # Status
current_ip_col = 11  # Current IP from check

print(f"{'ROW':<4} {'IP':<18} {'SHOP':<6} {'STATUS':<15} {'CURRENT IP':<20}")
print("-" * 90)

for i, row in enumerate(data[1:], 2):
    if len(row) > rdp_col:
        shop = row[0]
        rdp = row[rdp_col]
        status = row[status_col] if len(row) > status_col else ''
        current_ip = row[current_ip_col] if len(row) > current_ip_col else ''

        # Extract IP from RDP string
        ip = rdp.split(':')[0] if ':' in rdp else rdp

        if ip and ip != 'ERROR':
            marker = ''
            if 'ERROR' in status or 'Offline' in status:
                marker = ' [!]'
            print(f"{i:<4} {ip:<18} {shop:<6} {status:<15} {current_ip:<20}{marker}")
