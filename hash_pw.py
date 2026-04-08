from argon2 import PasswordHasher
import getpass
ph = PasswordHasher()

# Prompt user securely (no echo)
pw = getpass.getpass("Enter immudb password: ")
# Hash with Argon2id

hashed = ph.hash(pw)

print("\n=== Sovereignty Checkpoint ===")
print("Argon2id hash:\n")
print(hashed)
print("\nCopy this into your .env as IMMUDb_HASHED_PASSWORD")
