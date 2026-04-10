#!/bin/bash
# run_orp-gum.sh — Sovereign UI Edition
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_orp_core.sh
source "$SCRIPT_DIR/_orp_core.sh"

ACCENT="#004a99"
GOLD="#FFD700"
WARN="#ff4d4d"
SUCCESS="#2ecc71"

# Override cleanup to add gum styling
cleanup() {
    echo ""
    gum style --foreground "$WARN" " [!] Locking vault & wiping volatile memory..."
    orp_cleanup
    gum style --foreground "$SUCCESS" " [*] Session terminated securely."
}
trap cleanup EXIT INT TERM

gum spin --spinner dot --title "Loading sovereign environment..." -- bash -c true
orp_load_env

gum spin --spinner pulse \
    --title "Forging session keys for $LGU_SIGNER_NAME..." \
    -- bash -c "source '$SCRIPT_DIR/_orp_core.sh' && \
                orp_load_env && orp_forge_identity"
# Note: orp_forge_identity must run in THIS shell to export vars
orp_forge_identity

if nc -z 127.0.0.1 3322 2>/dev/null; then
    gum style --foreground "$SUCCESS" " [✔] immudb vault detected."
    IMMUDB_PID=$(pgrep -f "immudb" | head -n1 || true)
    export IMMUDB_PID
else
    gum spin --spinner line \
        --title "Igniting hardened immudb vault..." \
        -- bash -c "
        ~/bin/immudb \
            --dir '$HOME/.orp_vault/data' \
            --address 127.0.0.1 \
            --port 3322 \
            --pidfile '$HOME/.orp_vault/immudb.pid' \
            --auth=true --maintenance=false \
            >> '$HOME/.orp_vault/immudb.log' 2>&1 &
        echo \$! > /tmp/orp_immudb.pid
        sleep 2
    "
    IMMUDB_PID=$(cat /tmp/orp_immudb.pid 2>/dev/null || true)
    rm -f /tmp/orp_immudb.pid
    export IMMUDB_PID
fi

orp_configure_git

clear
gum style \
    --border double \
    --margin "1" --padding "1 2" \
    --border-foreground "$ACCENT" --align center \
    "OPENRESPUBLICA" "INFORMATION TECHNOLOGY SOLUTIONS"

echo "$(gum style --foreground "$GOLD" --align center "★ ★ ★")"
gum style --bold " Sovereign node:  " "$LGU_NAME"
gum style        " Operator:        " "$LGU_SIGNER_NAME ($KEY_ID)"
echo ""
gum style --bold "📋 Session SSH key (Authentication):"
gum style --faint -- "$(cat "$ORP_IDENTITY_DIR/session.pub")"
echo ""
gum style --bold "🔐 Session GPG key (Commit Verification):"
gum style --faint -- "$(cat "$ORP_IDENTITY_DIR/session.gpg")"
echo ""

if gum confirm "Keys synced to GitHub Settings?"; then
    clear
    gum style --border normal --padding "1 2" \
        --border-foreground "$SUCCESS" \
        "VAULT UNLOCKED · ENGINE START"
    orp_launch_engine
else
    gum style --foreground "$WARN" "Launch aborted. Cleaning up..."
    exit 0
fi
