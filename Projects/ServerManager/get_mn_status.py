#!/usr/bin/env python3
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys

# Encoding fix for Windows
sys.stdout.reconfigure(encoding='utf-8')

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('servermanagment.json', scope)
client = gspread.authorize(creds)

sheet = client.open_by_key('1wIS9hjLSbIU4PSjXbXyIoh3_KHVBRaX2jDQVj4o51V8').get_worksheet(0)
data = sheet.get_all_values()

# Row 3 = MN 194.59.31.156
row = data[2]

print("=" * 60)
print("MN (194.59.31.156) - CURRENT STATUS IN GOOGLE SHEET")
print("=" * 60)
print(f"Row 3 columns:")
print(f"  [0]  Magazin:          {row[0]}")
print(f"  [6]  RDP:              {row[6][:30]}...")
print(f"  [28] Status Machine:   {row[28] if len(row) > 28 else 'N/A'}")
print(f"  [29] Status Proxy:     {row[29] if len(row) > 29 else 'N/A'}")
print(f"  [30] Current IP:       {row[30] if len(row) > 30 else 'N/A'}")
print(f"  [31] City (2ip):       {row[31] if len(row) > 31 else 'N/A'}")
print(f"  [34] Date/Time Check:  {row[34] if len(row) > 34 else 'N/A'}")
print(f"  [36] Check Result:     {row[36] if len(row) > 36 else 'N/A'}")
