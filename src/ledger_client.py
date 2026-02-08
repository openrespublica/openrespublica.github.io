import hashlib
from immudb import ImmudbClient
import json
import os

class Ledger:
    def __init__(self, host="127.0.0.1", port=3322):
        self.client = ImmudbClient(f"{host}:{port}")
        self.client.login("immudb", "immudb")
        # Absolute path to ensure consistency
        self.manifest_path = "/root/openrespublica/orp/docs/manifest.json"

    def get_last_hash(self):
        try:
            last_id = self.client.get(b"last_registered_id").value.decode()
            return self.client.get(last_id.encode()).value.decode()
        except:
            return "00000000000000000000000000000000"

    def record_document(self, control_no, doc_hash):
        prev_hash = self.get_last_hash()
        chain_link = hashlib.sha256(f"{doc_hash}{prev_hash}".encode()).hexdigest()

        # Commit to immudb
        self.client.set(control_no.encode(), doc_hash.encode())
        self.client.set(f"link_{control_no}".encode(), chain_link.encode())
        self.client.set(b"last_registered_id", control_no.encode())

        self.update_public_manifest(control_no, doc_hash, chain_link)
        return chain_link

    def update_public_manifest(self, control_no, doc_hash, chain_link):
        # Ensure file exists and is a valid list
        if not os.path.exists(self.manifest_path) or os.stat(self.manifest_path).st_size == 0:
            data = []
        else:
            with open(self.manifest_path, 'r') as f:
                try:
                    data = json.load(f)
                except:
                    data = []

        data.append({
            "id": control_no,
            "hash": doc_hash,
            "chain_link": chain_link,
            "verified": "immudb-v1.2"
        })

        with open(self.manifest_path, 'w') as f:
            json.dump(data, f, indent=2)

