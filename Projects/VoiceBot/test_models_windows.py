#!/usr/bin/env python3
"""Test Z.AI models directly from Windows."""
import json, urllib.request

ZAI_KEY = "525b2fbc0b954a6bb9aac9394789e349.vCDOfBTV1q1rmzv8"

models = ["glm-4-plus", "glm-4-0520", "glm-4-air", "glm-4-flash", "glm-4-airx", "glm-4", "glm-4-long"]

print("=== TESTING Z.AI MODELS ===\n")

for model in models:
    try:
        req = urllib.request.Request(
            "https://api.z.ai/api/paas/v4/chat/completions",
            data=json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "Say hello in 3 words"}],
                "max_tokens": 100
            }).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ZAI_KEY}"
            },
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content", "")
        finish = choice.get("finish_reason", "?")

        result = f"OK | content='{content[:50]}' | finish={finish} | reasoning={bool(reasoning)}"
        print(f"{model:20} : {result}")
    except urllib.error.HTTPError as err:
        body = err.read().decode()[:100]
        print(f"{model:20} : HTTP {err.code} | {body}")
    except Exception as ex:
        print(f"{model:20} : ERROR | {str(ex)[:100]}")

print("\n=== РЕКОМЕНДАЦИЯ ===")
print("Нужна модель с:")
print("  - content != empty")
print("  - reasoning = False (не reasoning модель)")
print("  - finish = stop (не length)")
