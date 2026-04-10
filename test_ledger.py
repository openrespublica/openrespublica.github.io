import os
from immudb import ImmudbClient

def test_connection():
    try:
        client = ImmudbClient(f"{os.getenv('IMMUDB_HOST')}:{os.getenv('IMMUDB_PORT')}")
        client.login(
            os.getenv('IMMUDB_USER'), 
            os.getenv('IMMUDB_PASS'), 
            database=os.getenv('IMMUDB_DB')
        )
        print("[-] Success: Cryptographic bridge established with brgy_bunaodb.")
        client.logout()
    except Exception as e:
        print(f"[!] Connection Failed: {e}")

if __name__ == "__main__":
    test_connection()
