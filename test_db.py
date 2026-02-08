from immudb import ImmudbClient

try:
    # Note: default credentials from your log are immudb/immudb
    client = ImmudbClient("127.0.0.1:3322")
    client.login("immudb", "immudb")
    client.set(b"status", b"Tesla-Model-S3-CUTIE")
    val = client.get(b"status")
    print(f"\n✅ Connection Successful!")
    print(f"Decoded value from Ledger: {val.value.decode()}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
