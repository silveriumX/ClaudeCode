from pathlib import Path
from dotenv import load_dotenv
import os

print("=" * 50)
print("Testing .env loading")
print("=" * 50)

env_path = Path("C:/EnglishTutorBot/.env")
print(f"Env file exists: {env_path.exists()}")

if env_path.exists():
    print(f"File size: {env_path.stat().st_size} bytes")
    print("\nFile content (first 200 chars):")
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read(200)
        print(repr(content))

print("\nLoading with load_dotenv()...")
result = load_dotenv(env_path)
print(f"load_dotenv() returned: {result}")

token = os.getenv("TELEGRAM_TOKEN")
api_key = os.getenv("OPENAI_API_KEY")

print("\nResults:")
print(f"Token loaded: {bool(token)}")
if token:
    print(f"Token length: {len(token)}")
    print(f"Token starts with: {token[:10]}")
else:
    print("Token is None or empty!")

print(f"API key loaded: {bool(api_key)}")
if api_key:
    print(f"API key length: {len(api_key)}")
    print(f"API key starts with: {api_key[:10]}")
else:
    print("API key is None or empty!")
