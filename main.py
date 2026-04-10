# main.py
import hashlib, io, os, json, subprocess, datetime, qrcode, threading, pytz
import gnupg
from flask import Flask, request, send_file, send_from_directory, jsonify, render_template, redirect, url_for
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from immudb.client import ImmudbClient
from dotenv import load_dotenv
from docxtpl import DocxTemplate
import getpass
from argon2 import PasswordHasher
import signal

load_dotenv()

# --- 1. CONFIGURATION & FAIL-FAST SECURITY ---
# --- 1. CONFIGURATION & FAIL-FAST SECURITY ---
GPG_HOME = os.getenv("GNUPGHOME")
GPG_EMAIL = os.getenv("OPERATOR_GPG_EMAIL")
SSH_AUTH_SOCK = os.getenv("SSH_AUTH_SOCK") # The new heartbeat

# SECURITY HALT: The "Triple Check"
if not all([GPG_HOME, GPG_EMAIL, SSH_AUTH_SOCK]):
    print("\n" + "!"*50)
    print(" CRITICAL SECURITY FAILURE: ENVIRONMENT INCOMPLETE")
    print(" - GPG_HOME: ", "✅" if GPG_HOME else "❌ MISSING")
    print(" - GPG_EMAIL:", "✅" if GPG_EMAIL else "❌ MISSING")
    print(" - SSH_SOCK: ", "✅" if SSH_AUTH_SOCK else "❌ MISSING")
    print("!"*50)
    raise RuntimeError("Engine must be launched via _orp_core.sh sequence.")

# Verify GPG_HOME is actually in RAM (/dev/shm)
if not GPG_HOME.startswith("/dev/shm/"):
    raise RuntimeError("VULNERABILITY DETECTED: GPG Home must reside in RAM disk (/dev/shm).")
if not GPG_HOME or not GPG_EMAIL:
    raise RuntimeError("SECURITY HALT: GNUPGHOME or OPERATOR_GPG_EMAIL is missing. Ephemeral RAM environment not detected!")

gpg = gnupg.GPG(gnupghome=GPG_HOME)
gpg.decode_errors = 'replace' # Ensures smooth passwordless operation

IMMUDB_HOST = os.getenv("IMMUDB_HOST", "localhost:3322")
IMMUDB_USER = os.getenv("IMMUDB_USER", "immudb")
IMMUDB_DB = os.getenv("IMMUDB_DB", "defaultdb") # Note: keep as string to avoid gRPC errors
IMMUDB_HASHED_PASSWORD = os.getenv("IMMUDB_HASHED_PASSWORD")

LGU_NAME = os.getenv("LGU_NAME", "Local Government Unit")
SIGNER_NAME = os.getenv("LGU_SIGNER_NAME", "Authorized Signatory")
SIGNER_POS = os.getenv("LGU_SIGNER_POSITION", "Official")
TZ_NAME = os.getenv("LGU_TIMEZONE", "Asia/Manila")

REPO_PATH = os.getenv("GITHUB_REPO_PATH", "/home/orp/openrespublica.github.io")
GITHUB_PORTAL = os.getenv("GITHUB_PORTAL_URL", "https://openrespublica.github.io/verify.html")
TEMPLATE_PATH = os.getenv("TEMPLATE_DOCX_PATH", "templates/barangay_template.docx")
RECORDS_DIR = os.path.join(REPO_PATH, "docs", "records")
CONTROL_FILE = os.path.join(REPO_PATH, "docs", "control_number.txt")

# --- 2. INITIALIZATION ---
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

ctrl_lock = threading.Lock()
git_lock = threading.Lock()
os.makedirs(RECORDS_DIR, exist_ok=True)

def get_client():
    """Direct Vault Authentication with Explicit Port Mapping."""
    print("\n" + "="*40)
    print("      ORP VAULT: DIRECT ACCESS        ")
    print("="*40)
    
    # Ensure we are pulling the right host/port
    host_raw = os.getenv("IMMUDB_HOST", "127.0.0.1:3322")
    
    # Split host and port to avoid gRPC defaulting to 443
    if ":" in host_raw:
        host, port = host_raw.split(":")
        port = int(port)
    else:
        host = host_raw
        port = 3322

    input_pw = getpass.getpass(f"Enter password for vault user [{IMMUDB_USER}]: ")

    try:
        # Explicitly pass rs=False if you aren't using immudb's built-in TLS 
        # (Since Nginx handles the TLS layer, the internal connection is plain gRPC)
        c = ImmudbClient(f"{host}:{port}") 
        c.login(IMMUDB_USER, input_pw, database=IMMUDB_DB)
        
        print(f"✅ Vault Unlocked. Connected to: {host}:{port}/{IMMUDB_DB}")
        return c
    except Exception as e:
        # If it still fails, let's see exactly what the client tried to do
        print(f"\n[!] ACCESS DENIED. Target: {host}:{port}")
        print(f"Error Details: {e}")
        exit(1)

client = get_client()

def gracefull_shutdown(signum, frame):
    print("\n[!] EMERGENCY SCRAM: Purging Session...")
    # Add any specific internal cleanup here (e.g., closing immudb client)
    try:
        client.logout()
    except:
        pass
    os._exit(0) # Forced exit to ensure the shell trap catches it

# Register the signals
signal.signal(signal.SIGINT, gracefull_shutdown)
signal.signal(signal.SIGTERM, gracefull_shutdown)

# --- 3. CRYPTO & DATA UTILITIES ---
def sign_json_data(record_dict):
    """Signs the JSON payload securely using the passwordless ephemeral key."""
    data_str = json.dumps(record_dict, sort_keys=True)
    gpg_sig = gpg.sign(data_str, keyid=GPG_EMAIL)
    
    if not gpg_sig.status == "signature created":
        print(f"❌ GPG Signing Error: {gpg_sig.stderr}")
        return None

    return {
        "gpg_signature": str(gpg_sig),
        "hash_anchor": hashlib.sha256(data_str.encode()).hexdigest(),
        "integrity_scope": "EPHEMERAL_RAM_LEGAL_SIGNATURE"
    }

def next_control_number():
    with ctrl_lock:
        local_tz = pytz.timezone(TZ_NAME)
        current_year = str(datetime.datetime.now(local_tz).year)
        if not os.path.exists(CONTROL_FILE):
            with open(CONTROL_FILE, "w") as f: f.write(f"{current_year}-0000")
        with open(CONTROL_FILE, "r+") as f:
            val = f.read().strip().split("-")
            year, num = val[0], int(val[1])
            if year != current_year: year, num = current_year, 0
            new_ctrl = f"{year}-{(num + 1):04d}"
            f.seek(0); f.write(new_ctrl); f.truncate()
        return new_ctrl

def generate_qr(sha256_hash):
    qr_url = f"{GITHUB_PORTAL}?hash={sha256_hash}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(qr_url)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)
    return buf, qr_url

def add_footer(original_pdf, sha256_hash, signature, qr_buf, timestamp, control_number):
    reader = PdfReader(io.BytesIO(original_pdf))
    writer = PdfWriter()
    qr_image = ImageReader(qr_buf)
    for page in reader.pages:
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=A4)
        c.setLineWidth(0.5)
        c.line(25*mm, 22*mm, 185*mm, 22*mm)
        items = [("TIMESTAMP", timestamp), ("CTRL NO", control_number), ("HASH", sha256_hash[:32]+"...")]
        y = 18*mm
        for label, val in items:
            c.setFont("Helvetica-Bold", 7); c.drawString(30*mm, y, f"{label}:")
            c.setFont("Helvetica", 7); c.drawString(55*mm, y, str(val))
            y -= 3.5*mm
        c.drawImage(qr_image, 165*mm, 5*mm, width=15*mm, height=15*mm)
        c.save(); packet.seek(0)
        page.merge_page(PdfReader(packet).pages[0])
        writer.add_page(page)
    out = io.BytesIO(); writer.write(out); out.seek(0)
    return out

def update_manifest(record):
    manifest_path = os.path.join(RECORDS_DIR, "manifest.json")
    records = []
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r") as f:
                records = json.load(f)
        except Exception:
            records = []
    
    records.insert(0, record) # Newest first
    if len(records) > 1000:
        records = records[:1000]
        
    with open(manifest_path, "w") as f:
        json.dump(records, f, indent=4)

def sync_to_github(json_path, record):
    with git_lock:
        update_manifest(record)
        
        repo_path = REPO_PATH
        anchor_hash = os.path.basename(json_path).replace(".json", "")
        
        git_env = os.environ.copy()
        # The engine now trusts the shell's exported socket
        git_env["SSH_AUTH_SOCK"] = SSH_AUTH_SOCK 
        git_env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"

        try:
            subprocess.run(['git', '-C', repo_path, 'add', '.'], check=True, env=git_env)
            subprocess.run(['git', '-C', repo_path, 'commit', '-m', f"Audit: Anchor {anchor_hash}"], 
                           check=False, env=git_env)
            subprocess.run(['git', '-C', repo_path, 'fetch', 'origin'], check=True, env=git_env)
            subprocess.run(['git', '-C', repo_path, 'pull', '--rebase', '-X', 'ours', 'origin', 'main'], 
                           check=True, env=git_env)
            subprocess.run(['git', '-C', repo_path, 'push', 'origin', 'main'], check=True, env=git_env)
            print(f"✅ TruthChain Synchronized: {anchor_hash}")
        except subprocess.CalledProcessError as e:
            print(f"❌ [Git Sync Error] {e}")

# --- 4. ROUTES ---
@app.route("/")
def home():
    return render_template("portal.html")

@app.route("/cert_error.html")
def cert_error():
    return "<h1>Sovereign Identity Required</h1><p>Please present your operator certificate.</p>", 403

@app.route('/lock_engine', methods=['POST'])
def lock_engine():
    """Trigger the cleanup trap by shutting down the Python process."""
    print("\n[!] LOCK SIGNAL RECEIVED: Initiating secure shutdown...")
    # Sending SIGINT to ourselves is like hitting CTRL+C
    os.kill(os.getpid(), signal.SIGINT)
    return "Engine Locked. RAM Disk Purged.", 200

@app.route('/ingest', methods=['POST'])
def sovereign_ingest():
    global client
    try:
        data = request.get_json(silent=True)
        payload = json.loads(data['payload'].strip())
        subject = payload.get('subject', {})

        # 1. GENERATE CONTROL DATA FIRST
        control_no = next_control_number()
        doc_type = data.get('purpose', 'BARANGAY-CERT')
        final_ctrl = f"Verified_{control_no}-{doc_type}"

        # 2. GENERATE PHILID INTEGRITY HASH (Audit Fingerprint)
        # We use final_ctrl to ensure this hash is unique to this specific issuance
        raw_str = f"{subject.get('PCN', '')}{subject.get('lName', '')}{subject.get('fName', '')}{final_ctrl}"
        integrity_hash = hashlib.sha256(raw_str.encode()).hexdigest().upper()

        # 3. RENDER THE DOCUMENT
        doc = DocxTemplate(TEMPLATE_PATH)
        context = {
            'fName':     subject.get('fName'),
            'lName':     subject.get('lName'),
            'PCN':        subject.get('PCN'),
            'Hash':      integrity_hash,
            'Day':       datetime.datetime.now().strftime("%d"),
            'MonthYear': datetime.datetime.now().strftime("%B %Y").upper(),
            'Purpose':   doc_type,
        }
        doc.render(context)

        # 4. CONVERT TO PDF (Headless LibreOffice)
        temp_docx = f"/tmp/tmp_{integrity_hash[:8]}.docx"
        doc.save(temp_docx)
        subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', '/tmp', temp_docx], check=True)

        pdf_path = f"/tmp/tmp_{integrity_hash[:8]}.pdf"
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        # Cleanup temp files immediately after reading
        if os.path.exists(temp_docx): os.remove(temp_docx)
        if os.path.exists(pdf_path): os.remove(pdf_path)

        # 5. GENERATE DOCUMENT HASH & IMMUDB ANCHOR
        sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()
        try:
            tx = client.set(sha256_hash.encode(), b"VERIFIED_BY_ORP_ENGINE")
        except Exception:
            client = get_client() # Reconnect on session timeout
            tx = client.set(sha256_hash.encode(), b"VERIFIED_BY_ORP_ENGINE")

        # 6. ASSEMBLE FINAL RECORD & PGP SIGN
        local_tz = pytz.timezone(TZ_NAME)
        timestamp_ph = datetime.datetime.now(local_tz).strftime("%Y-%m-%d %I:%M %p PHT")
        
        record = {
            "status": "VERIFIED ✅",
            "document_type": doc_type,
            "control_number": final_ctrl,
            "sha256_hash": sha256_hash,
            "timestamp": timestamp_ph,
            "immudb_transaction_id": tx.id,
            "philid_pcn": subject.get('PCN'),
            "philid_hash": integrity_hash
        }

        pgp_signature = sign_json_data(record)
        if pgp_signature:
            record["data_signature"] = pgp_signature

        # 7. SAVE LOCALLY & SYNC TO GITHUB
        json_path = os.path.join(RECORDS_DIR, f"{sha256_hash}.json")
        with open(json_path, 'w') as f:
            json.dump(record, f, indent=4)

        threading.Thread(target=sync_to_github, args=(json_path, record)).start()

        # 8. ADD SECURITY FOOTER & SEND TO USER
        qr_buf, _ = generate_qr(sha256_hash)
        stamped_pdf_buf = add_footer(pdf_bytes, sha256_hash, "ORP-IMMUTABLE-SIG", qr_buf, timestamp_ph, final_ctrl)

        return send_file(stamped_pdf_buf, as_attachment=True, download_name=f"{final_ctrl}.pdf")

    except Exception as e:
        print(f"❌ [Sovereign Error] {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    app.run(host="127.0.0.1", port=port)
