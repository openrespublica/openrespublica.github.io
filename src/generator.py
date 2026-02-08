from flask import Flask, request, jsonify
import os, hashlib
from ledger_client import Ledger

app = Flask(__name__)
ledger = Ledger()

BASE_DIR = "/root/openrespublica/orp"
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

@app.route('/api/generate', methods=['POST'])
@app.route('/generate', methods=['POST']) # Add this line as a backup!
def generate():
    data = request.json
    control_no = data.get("control_no", "UNKNOWN")
    content = data.get("content", "")

    file_path = os.path.join(OUTPUT_DIR, f"{control_no}.txt")
    with open(file_path, "w") as f:
        f.write(f"CONTROL NO: {control_no}\nCONTENT: {content}")

    with open(file_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    chain_link = ledger.record_document(control_no, file_hash)

    return jsonify({
        "status": "Success",
        "hash": file_hash,
        "chain_link": chain_link,
        "url": f"/outputs/{control_no}.txt"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
