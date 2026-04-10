#!/bin/bash
# run_orp.sh
set -e

# --- 1. Load Configuration ---
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "CRITICAL: .env file missing."
    exit 1
fi

# --- 2. Setup Cleanup Trap ---
cleanup() {
    echo -e "\n[!] Shutting down ORP Engine..."
    # Use || true to prevent the trap itself from failing
    [ -n "$IMMUDB_PID" ] && kill "$IMMUDB_PID" 2>/dev/null || true
    if [ -n "$GNUPGHOME" ]; then
        echo "[*] Wiping ephemeral RAM directory..."
        gpgconf --kill all 2>/dev/null || true
        rm -rf "$GNUPGHOME" 2>/dev/null || true
        [ -d "/dev/shm/orp_identity" ] && rm -rf "/dev/shm/orp_identity" || true
    fi
    echo "[*] Session terminated securely."
}
trap cleanup EXIT INT TERM

# --- 3. Create Ephemeral RAM Disk ---
export GNUPGHOME=$(mktemp -d -p /dev/shm .orp-gpg-XXXXXX)
chmod 700 "$GNUPGHOME"

echo "enable-ssh-support" > "$GNUPGHOME/gpg-agent.conf"
echo "default-cache-ttl 86400" >> "$GNUPGHOME/gpg-agent.conf"
export SSH_AUTH_SOCK=$(gpgconf --list-dirs agent-ssh-socket)

# --- 4. JIT Database Startup ---
echo "[*] Starting immudb..."
immudb --dir "$IMMUDB_DATA_DIR" > /dev/null 2>&1 &
IMMUDB_PID=$!

echo "[*] Waiting for immudb (Port 3322)..."
for i in {1..10}; do
    if nc -z localhost 3322; then break; fi
    if [ $i -eq 10 ]; then echo "immudb failed to start"; exit 1; fi
    sleep 1
done

# --- 5. Key Generation ---
echo "[*] Generating ED25519 identity for $OPERATOR_GPG_EMAIL..."
cat > "$GNUPGHOME/gpg-gen-spec" <<EOF
Key-Type: EDDSA
Key-Curve: ed25519
Key-Usage: auth,sign
Name-Real: $LGU_SIGNER_NAME
Name-Email: $OPERATOR_GPG_EMAIL
Expire-Date: 1d
%no-protection
%commit
EOF

gpg --batch --generate-key "$GNUPGHOME/gpg-gen-spec" > /dev/null 2>&1

# --- 6. Bridge to SSH (With error handling) ---
# We wait a split second for the agent to register the key
sleep 1
KEYGRIP=$(gpg --with-keygrip -K "$OPERATOR_GPG_EMAIL" | grep "Keygrip" | head -n 1 | awk '{print $3}')

if [ -z "$KEYGRIP" ]; then
    echo "CRITICAL: Could not find Keygrip for generated key."
    exit 1
fi

echo "$KEYGRIP 0" > "$GNUPGHOME/sshcontrol"
gpg-connect-agent updatestartuptty /bye > /dev/null 2>&1

# --- 7. Export Public Fragments ---
export ORP_IDENTITY_DIR="/dev/shm/orp_identity"
mkdir -p "$ORP_IDENTITY_DIR"
gpg --export-ssh-key "$OPERATOR_GPG_EMAIL" > "$ORP_IDENTITY_DIR/session.pub"
gpg --export --armor "$OPERATOR_GPG_EMAIL" > "$ORP_IDENTITY_DIR/session.gpg"

# --- 8. Git Config ---
KEY_ID=$(gpg --list-secret-keys --with-colons "$OPERATOR_GPG_EMAIL" | grep "^sec" | awk -F: '{print $5}')
cd "$GITHUB_REPO_PATH"
git config --local user.name "$LGU_SIGNER_NAME"
git config --local user.email "$OPERATOR_GPG_EMAIL"
git config --local user.signingkey "$KEY_ID"
git config --local commit.gpgsign true

# --- 9. THE FLASH & WAIT ---
clear
echo "======================================================"
echo "          ORP SESSION CHECK-IN COMPLETE               "
echo "======================================================"
echo "Identity:   $LGU_SIGNER_NAME"
echo "GPG ID:     $KEY_ID"
echo "SSH Socket: $SSH_AUTH_SOCK"
echo "======================================================"
echo ""
echo "--- BEGIN SSH PUBLIC KEY ---"
cat "$ORP_IDENTITY_DIR/session.pub"
echo "--- END SSH PUBLIC KEY ---"
echo ""
echo "--- BEGIN GPG PUBLIC KEY ---"
cat "$ORP_IDENTITY_DIR/session.gpg"
echo "--- END GPG PUBLIC KEY ---"
echo ""
echo "======================================================"
echo "[!] ACTION: Paste the SSH key to GitHub Settings now."
echo "======================================================"
read -p "Press [ENTER] after pasting to start Flask... " confirm

# --- 10. Launch ---
# Make sure we use the venv python if applicable
#/home/orp/bin/immudb &
/home/orp/bin/immudb --dir "$IMMUDB_DATA_DIR" > /dev/null 2>&1 &
./venv/bin/python3 main.py
