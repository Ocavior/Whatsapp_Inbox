import secrets
token = secrets.token_urlsafe(32)
print(f"WEBHOOK_VERIFY_TOKEN={token}")