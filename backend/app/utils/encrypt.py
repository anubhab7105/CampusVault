from cryptography.fernet import Fernet
import json
import os

# ===============================
# Generate or load encryption key
# ===============================
def load_or_create_key():
    key_file = "secret.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as keyfile:
            key = keyfile.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, "wb") as keyfile:
            keyfile.write(key)
    return key


# ===============================
# Encrypt data (dict or string)
# ===============================
def encrypt_data(data, key):
    fernet = Fernet(key)
    if isinstance(data, dict):
        data = json.dumps(data)
    encrypted = fernet.encrypt(data.encode())
    return encrypted




# ===============================
# Example usage
# ===============================
if __name__ == "__main__":
    key = load_or_create_key()

    # Example: User info
    user_data = {
        "username": input("Enter your user name: "),
        "password": input("Enter your password: "),
        "email": input("Enter your email Id: "),
    }

    print("\n🔹 Original Data:")
    print(user_data)

    encrypted = encrypt_data(user_data, key)
    print("\n🔒 Encrypted Data:")
    print(encrypted)

   