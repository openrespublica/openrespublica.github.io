---

# 🔐 USB Encryption Documentation (Fedora Workstation, LUKS + ext4)

## 1️⃣ Purpose

This guide explains how to securely encrypt a USB 3.0 flash drive using **LUKS + ext4**.

* Protects sensitive data with strong encryption
* Works as a **cold storage vault** for keys or code
* Ensures that if the drive is lost, stolen, or accessed without authorization, the data remains secure

---

## 2️⃣ Advantages of USB Encryption

* **Data Confidentiality**: AES-based encryption prevents unauthorized access
* **Portability**: Carry your encrypted vault anywhere
* **Compatibility**: Works across Linux systems that support LUKS and ext4
* **Reduced Attack Surface**: Offline storage minimizes exposure to network attacks

---

## 3️⃣ Tools Used

| Tool           | Purpose                             | Version                 |
| -------------- | ----------------------------------- | ----------------------- |
| `parted`       | Partitioning and GPT label          | 3.6                     |
| `lsblk`        | Listing devices and partitions      | 2.41.3                  |
| `cryptsetup`   | LUKS encryption management          | 2.8.4                   |
| `mkfs.ext4`    | Filesystem creation                 | 1.47.3                  |
| `wipefs`       | Wipe existing signatures/metadata   | bundled with util-linux |
| `mount/umount` | Mounting and unmounting filesystems | system utilities        |

---

## 4️⃣ Current Environment (Precise)

### OS / Distribution

```text
Fedora Linux 43 (Workstation Edition)
Release type: stable
CPE Name: cpe:/o:fedoraproject:fedora:43
Support End: 2026-12-02
```

### Kernel

```text
Linux 192.168.1.16 6.18.16-200.fc43.x86_64 SMP PREEMPT_DYNAMIC Wed Mar 4 19:13:32 UTC 2026 x86_64 GNU/Linux
```

### CPU

```text
Architecture: x86_64
CPU(s): 2
Model: AMD A4-9120e RADEON R3, 4 COMPUTE CORES 2C+2G
Virtualization: AMD-V
Caches: L1d 64 KiB, L1i 192 KiB, L2 2 MiB
```

### Memory

```text
RAM: 3.7 GiB (used: 2.8 GiB, free: 298 MiB)
Swap: 3.7 GiB (used: 1.8 GiB, free: 1.9 GiB)
```

### Block Devices

```text
sda: internal drive
├─ sda1: FAT32 /boot/efi
├─ sda2: ext4 /boot
└─ sda3: LUKS + Btrfs /home

sdc: USB 3.0 flash drive
└─ sdc1: LUKS (not mounted)
zram0: swap
```

### Filesystem Usage (root & mounted devices)

```text
Filesystem      Size  Used Avail Use% Mounted on
/dev/dm-0        56G   14G   42G  26% /
/dev/sda2       2.0G  566M  1.3G  31% /boot
/dev/sda1       599M   20M  580M   4% /boot/efi
```

### Shell & Environment

```text
Shell: /bin/bash
Terminal: $TERM
Environment variables: captured with `env | sort`
```

### Tool Versions

```text
parted: 3.6
lsblk: 2.41.3
cryptsetup: 2.8.4 (flags: UDEV BLKID KEYRING FIPS KERNEL_CAPI PWQUALITY HW_OPAL)
mkfs.ext4: 1.47.3
```

---

## 5️⃣ Step-by-Step Procedure

### Step 1 — Wipe the USB

```bash
sudo wipefs -a /dev/sdc
sudo parted /dev/sdc -- mklabel gpt
```

* Purpose: Remove old partition tables, signatures, and metadata

### Step 2 — Create a Partition

```bash
sudo parted /dev/sdc -- mkpart primary 0% 100%
```

* Creates a single partition covering the whole disk

### Step 3 — Encrypt with LUKS

```bash
sudo cryptsetup luksFormat /dev/sdc1
sudo cryptsetup open /dev/sdc1 orp_vault
```

* Creates a **secure encrypted container**
* `orp_vault` is the mapper name

### Step 4 — Format with ext4

```bash
sudo mkfs.ext4 -L orp-vault /dev/mapper/orp_vault
```

* ext4 chosen for stability, journaling, and Linux compatibility

### Step 5 — Mounting

```bash
sudo mkdir -p /vault/orp-vault
sudo mount /dev/mapper/orp_vault /vault/orp-vault
```

* Mount to a directory to read/write files

### Step 6 — Test

```bash
echo "vault working" | sudo tee /vault/orp-vault/test.txt
ls /vault/orp-vault
```

### Step 7 — Unmount and Close LUKS

```bash
sudo umount /vault/orp-vault
sudo cryptsetup close orp_vault
```

---

## 6️⃣ Concepts Explained

| Term                    | Purpose / Background                                                        |
| ----------------------- | --------------------------------------------------------------------------- |
| `wipefs`                | Removes filesystem signatures to allow clean setup                          |
| `LUKS`                  | Linux Unified Key Setup — standard for disk encryption                      |
| `ext4`                  | Journaled filesystem used for Linux storage                                 |
| `GPT`                   | GUID Partition Table — modern partitioning for drives >2TB and UEFI support |
| `lsblk`                 | Lists devices, partitions, and mountpoints                                  |
| `mount/umount`          | Attach/detach filesystems to the directory tree                             |
| `cryptsetup open/close` | Unlock or lock an encrypted LUKS container                                  |

---

## 7️⃣ Importance of Encryption

* Prevents unauthorized access if USB is lost
* Protects sensitive data even against **offline attacks**
* Enables **air-gapped identity management** for code, keys, or passwords

---

## 8️⃣ Emergency Recovery / Backup

* Keep a backup of your **LUKS header**:

```bash
sudo cryptsetup luksHeaderBackup /dev/sdc1 --header-backup-file ~/orp_vault_header.bkp
```

* Losing the header means **data is unrecoverable**
* Regularly backup critical files from inside the encrypted vault

---

✅ **Result**: You now have a **reproducible, secure USB vault** for storing sensitive data, fully documented with precise environment info, tools, and procedure.

---
