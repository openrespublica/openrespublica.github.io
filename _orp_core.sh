#!/bin/bash
# _orp_core.sh — Shared core for ORP Engine boot sequence
# Source this file; do not execute directly.

# ── 1. Environment ───────────────────────────────────────────────
orp_load_env() {
    if [ -f .env ]; then
        set -a; source .env; set +a
    else
        orp_die "CRITICAL: .env file missing."
    fi

    if [ -f "$HOME/.identity/db_secrets.env" ]; then
        set -a; source "$HOME/.identity/db_secrets.env"; set +a
    else
        orp_die "CRITICAL: RAM secrets not found at ~/.identity/db_secrets.env"
    fi
}

orp_die() {
    echo "ERROR: $*" >&2
    exit 1
}

# ── 2. Cleanup trap ──────────────────────────────────────────────
orp_cleanup() {
    echo -e "\n[!] Shutting down ORP Engine..."
    if [ -n "$IMMUDB_PID" ] && kill -0 "$IMMUDB_PID" 2>/dev/null; then
        kill "$IMMUDB_PID" 2>/dev/null || true
    fi
    if [ -n "$GNUPGHOME" ] && [ -d "$GNUPGHOME" ]; then
        echo "[*] Wiping ephemeral RAM disk..."
        gpgconf --kill all 2>/dev/null || true
        rm -rf "$GNUPGHOME"
    fi
    [ -d "/dev/shm/orp_identity" ] && rm -rf "/dev/shm/orp_identity"
    echo "[*] Session terminated securely."
}

# ── 3. RAM disk + GPG identity ───────────────────────────────────
orp_forge_identity() {
    export GNUPGHOME
    GNUPGHOME=$(mktemp -d -p /dev/shm .orp-gpg-XXXXXX)
    chmod 700 "$GNUPGHOME"

    cat > "$GNUPGHOME/gpg-agent.conf" <<EOF
enable-ssh-support
allow-loopback-pinentry
default-cache-ttl 86400
EOF

    gpg-connect-agent reloadagent /bye > /dev/null 2>&1
    export SSH_AUTH_SOCK
    SSH_AUTH_SOCK=$(gpgconf --list-dirs agent-ssh-socket)

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

    sleep 1
    KEYGRIP=$(gpg --with-keygrip -K "$OPERATOR_GPG_EMAIL" \
        | grep "Keygrip" | head -n1 | awk '{print $3}')
    [ -z "$KEYGRIP" ] && orp_die "Could not find Keygrip for generated key."

    echo "$KEYGRIP 0" > "$GNUPGHOME/sshcontrol"
    gpg-connect-agent updatestartuptty /bye > /dev/null 2>&1

    export ORP_IDENTITY_DIR="/dev/shm/orp_identity"
    mkdir -p "$ORP_IDENTITY_DIR"
    gpg --export-ssh-key "$OPERATOR_GPG_EMAIL" > "$ORP_IDENTITY_DIR/session.pub"
    gpg --export --armor "$OPERATOR_GPG_EMAIL" > "$ORP_IDENTITY_DIR/session.gpg"

    KEY_ID=$(gpg --list-secret-keys --with-colons "$OPERATOR_GPG_EMAIL" \
        | awk -F: '/^sec/{print $5; exit}')
    export KEY_ID
}

# ── 4. immudb vault ──────────────────────────────────────────────
orp_start_vault() {
    echo "[*] Checking for immudb vault on :3322..."
    if nc -z 127.0.0.1 3322 2>/dev/null; then
        echo "[!] Vault already running. Connecting."
        # Use pgrep carefully; don't fail if not found
        IMMUDB_PID=$(pgrep -f "immudb" | head -n1 || true)
    else
        echo "[*] Starting hardened immudb instance..."
        ~/bin/immudb \
            --dir "$HOME/.orp_vault/data" \
            --address 127.0.0.1 \
            --port 3322 \
            --pidfile "$HOME/.orp_vault/immudb.pid" \
            --auth=true \
            --maintenance=false \
            >> "$HOME/.orp_vault/immudb.log" 2>&1 &
        IMMUDB_PID=$!

        # Wait with a timeout instead of a blind sleep
        local i=0
        while ! nc -z 127.0.0.1 3322 2>/dev/null; do
            sleep 0.5; i=$((i+1))
            [ $i -ge 20 ] && orp_die "immudb failed to start after 10s."
        done
        echo "[*] Vault ready."
    fi
    export IMMUDB_PID
}

# ── 5. Git config ────────────────────────────────────────────────
orp_configure_git() {
    cd "$GITHUB_REPO_PATH" || orp_die "Cannot cd to GITHUB_REPO_PATH: $GITHUB_REPO_PATH"
    git config --local user.name "$LGU_SIGNER_NAME"
    git config --local user.email "$OPERATOR_GPG_EMAIL"
    git config --local user.signingkey "$KEY_ID"
    git config --local commit.gpgsign true
}

# ── 6. Engine launch ─────────────────────────────────────────────
orp_launch_engine() {
    # Re-export the agent socket in case it drifted
    export SSH_AUTH_SOCK
    SSH_AUTH_SOCK=$(gpgconf --list-dirs agent-ssh-socket)
    export GNUPGHOME

    echo "[*] Launching ORP Engine..."
    exec ./.venv/bin/python3 main.py
}
