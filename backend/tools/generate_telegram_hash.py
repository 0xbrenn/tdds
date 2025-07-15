import hashlib
import hmac

data = {
    "id": "123456",
    "username": "yerba",
    "first_name": "Yerba",
    "last_name": "M",
    "auth_date": "1720000000"
}

bot_token = "750165999lBo"  

# Step 1: Build the data_check_string
pairs = [f"{k}={v}" for k, v in sorted(data.items())]
data_check_string = "\n".join(pairs)

# Step 2: Compute HMAC SHA-256 hash
secret_key = hashlib.sha256(bot_token.encode()).digest()
hash_ = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

print("\n📤 Post this JSON payload to /auth/telegram:\n")
print({
    **data,
    "hash": hash_
})
