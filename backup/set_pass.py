# set_pass.py
import pexpect
import getpass

hex_pass = getpass.getpass("Enter your ESP32 hex: ")

child = pexpect.spawn(
    'gpg --homedir /run/user/1001/hsm-pki/gnupg '
    '--pinentry-mode loopback '
    '--batch '
    '--passwd 39D9792E855B6B89756679B4E796111950B68F3B'
)
child.sendline('')          # current passphrase (empty)
child.sendline(hex_pass)    # new passphrase
child.sendline(hex_pass)    # confirm
child.expect(pexpect.EOF)
print("Done!")
