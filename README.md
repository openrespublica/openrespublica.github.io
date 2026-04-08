# 🏛️ OpenResPublica TruthChain — Container Setup Guide

**Barangay Buñao, Dumaguete City · Cryptographic Document Integrity System**

> A production-grade immutable ledger running on Podman, Fedora Linux, immudb, Flask/Gunicorn, and Nginx — anchoring barangay documents to a public GitHub Pages portal.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Directory Structure](#directory-structure)
4. [Environment Configuration](#environment-configuration)
5. [Building the Flask Image](#building-the-flask-image)
6. [Pod & Container Setup (Quadlets)](#pod--container-setup-quadlets)
7. [immudb Persistence & Password Setup](#immudb-persistence--password-setup)
8. [Systemd Autostart on Boot](#systemd-autostart-on-boot)
9. [GitHub Pages Configuration](#github-pages-configuration)
10. [Daily Operations](#daily-operations)
11. [Troubleshooting](#troubleshooting)
12. [Full Stack Checklist](#full-stack-checklist)

---

### 1. Set Pages to serve from `/docs`

```
GitHub → Repository Settings → Pages → Build and deployment
  Source:  Deploy from a branch
  Branch:  main
  Folder:  /docs
```

### 2. Verify SSH remote

```bash
cd ~/immudb/openrespublica.github.io
git remote -v
# Must show: git@github.com:openrespublica/openrespublica.github.io.git

# If it shows https://, switch to SSH:
git remote set-url origin git@github.com:openrespublica/openrespublica.github.io.git
```

### 3. Initialize docs structure

```bash
cd ~/immudb/openrespublica.github.io
mkdir -p docs/records docs/assets

touch docs/records/.gitkeep

git add -A
git commit -m "Init: docs/ structure for GitHub Pages"
git push origin main
```

### 4. main.py path configuration

```python
REPO_PATH    = "/app/repo"
RECORDS_DIR  = os.path.join(REPO_PATH, "docs", "records")
CONTROL_FILE = os.path.join(REPO_PATH, "docs", "control_number.txt")
```

### 5. Propagation timeline

```
Flask stamps PDF       →  ~1 second
git commit + push      →  ~5 seconds
GitHub Pages rebuild   →  ~30–60 seconds
Public ledger live     →  ~60–90 seconds total
```
---

# 🏛️ OpenResPublica: Sovereign Node (Fedora Edition)

This repository contains the core logic, document engine, and immutable ledger for the **TruthChain** project. It is designed to run locally on an Android device via **Termux** and **PRoot-Distro (Fedora 43)**, providing a mobile-first, GPG-signed, and decentralized government service platform.

## 📱 Phase 1: Android Environment (Termux)

Before entering the Linux container, we must prepare the Android "Host" to ensure the process isn't killed in the background.

1.  **Install Termux:** [F-Droid Version](https://f-droid.org/en/packages/com.termux/) is required.
2.  **Enable Wake Lock:** Open Termux and pull down the notification bar. Select **"Acquire Wake Lock"** to prevent the OS from sleeping.
3.  **Prepare Storage & Packages:**
    ```bash
    termux-setup-storage
    pkg update && pkg upgrade -y
    pkg install proot-distro git openssh -y
    ```

---

## 🏗️ Phase 2: The Fedora "Sovereign" Container

We use **Fedora 43 (Rawhide/ARM64)** to access modern cryptographic libraries and the latest `immudb` builds.

1.  **Installation & Entry:**
    ```bash
    proot-distro install fedora
    proot-distro login fedora
    ```

2.  **System Prerequisites:**
    ```bash
    dnf update -y
    dnf install -y python3-pip python3-devel git gpg libreoffice-writer \
        libreoffice-headless java-latest-openjdk-headless gcc
    ```

---

## 💎 Phase 3: The Ledger & Identity (immudb + GPG)

### 1. immudb Binary
We use the ARM64 optimized binary for low-power high-speed immutability.
```bash
mkdir -p /root/bin
cd /root/bin
# Download immudb (Ensure version matches 1.10.0 or higher)
wget https://github.com/codenotary/immudb/releases/download/v1.10.0/immudb-v1.10.0-linux-arm64
mv immudb-v1.10.0-linux-arm64 immudb
chmod +x immudb
```

### 2. GPG Identity
Import your master sovereign key for document signing.
```bash
# Import your secret key
gpg --import /path/to/your/private-key.asc
# Verify identity
gpg --list-secret-keys --keyid-format LONG
```

---

## 🐍 Phase 4: Python Environment Setup

Isolate the TruthChain engine using a virtual environment to avoid system-level conflicts.

```bash
cd /root/openrespublica.github.io
python3 -m venv ~/truthchain-env
source ~/truthchain-env/bin/activate
pip install flask python-gnupg gunicorn immudb-py gitpython
```

---

## 🔑 Phase 5: SSH & Git Handshake

To enable the "Cloud Anchor," your Fedora container must be authorized with GitHub.

1.  **Generate/Identify Key:**
    ```bash
    ssh-keygen -t ed25519 -C "your-email@example.com"
    cat ~/.ssh/id_ed25519.pub # Paste this into GitHub Settings
    ```

2.  **Configure SSH Persistence:**
    Create `/root/.ssh/config`:
    ```text
    Host github.com
      IdentityFile ~/.ssh/id_ed25519
      StrictHostKeyChecking no
    ```

---

## 🚀 Phase 6: Operational Commands

### 🚦 Ignition (`wake-node`)
Use the built-in automation script to start the stack:
```bash
/root/bin/wake-node
```

### 🧪 Genesis Test (Mock Ingest)
Send a test payload to verify the chain:
```bash
curl -X POST http://127.0.0.1:5000/ingest \
-H "Content-Type: application/json" \
-d '{"purok": "Purok 1", "purpose": "VERIFICATION", "payload": "{...}"}'
```

---

## 📊 Infrastructure Layout
* **`/root/bin/immudb`**: The Immutability Engine.
* **`/root/openrespublica.github.io/main.py`**: The Flask/Python Logic.
* **`/root/openrespublica.github.io/docs/records/`**: The Public Audit Trail.
* **`/root/identity.sh`**: Environment variables for keys.

**Sovereignty Status:** 🟢 **Active** **Location:** Barangay Buñao, Dumaguete City  

---

### `invalid user name or password` on Flask startup

immudb password does not match `.env`. Causes: fresh `immudb_data` volume (resets to default), or wrong value in `.env`.

```bash
# Fix: change password via immuclient
immuclient login immudb --address localhost --port 3322
immuclient user changepassword immudb --address localhost --port 3322
systemctl --user restart flask_app.service
```

### `not logged in` on document upload

immudb restarted and the gRPC session token expired. Ensure `main.py` has auto-reconnect logic:

```python
def get_client():
    c = ImmudbClient("localhost:3322")
    c.login(os.environ["IMMUDB_USER"], os.environ["IMMUDB_PASS"], database=b"defaultdb")
    return c

client = get_client()

@app.route("/upload", methods=["POST"])
def upload_pdf():
    global client          # required — prevents UnboundLocalError
    ...
    try:
        tx = client.set(sha256_hash.encode(), b"VERIFIED_BY_ORP_ENGINE")
    except Exception:
        print("⚠️ [immudb] Session expired, reconnecting...")
        client = get_client()
        tx = client.set(sha256_hash.encode(), b"VERIFIED_BY_ORP_ENGINE")
```

### Git push fails — `Author identity unknown`

Git identity not configured in the container. Verify `Containerfile` has:

```dockerfile
RUN git config --global user.email "truthchain@barangaybunao.gov.ph"
RUN git config --global user.name "TruthChain ORP Engine"
```

Rebuild the image after adding these lines.

### Git push fails — SSH authentication error

```bash
# Test SSH from the host
ssh -T git@github.com

# Verify the remote is SSH not HTTPS
cd ~/immudb/openrespublica.github.io
git remote -v
git remote set-url origin git@github.com:openrespublica/openrespublica.github.io.git
```
      --format '{{.State.Health.Status}}' — healthy 
[ ] immuclient login ... (if fresh volume) — change 
default password [ ] systemctl --user start 
flask_app.service [ ] systemctl --user start 
nginx_proxy.service [ ] podman ps --pod — all 4 
containers Up [ ] curl http://0.0.0.0:5000 — returns 
ORP Engine form [ ] End-to-end stamp test — 📜 + 🚀 
in logs [ ] loginctl show-user openrespublica | grep 
Linger — Linger=yes ```

--- 

