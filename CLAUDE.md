# Sage 200 AI Audit - Code Repository

## Project
AI audit for Grupo Solitium testing if AI can replace/assist Sage 200 development workflows.
- **Client:** Grupo Solitium
- **Timeline:** 23 Mar 2026 → 13-14 April 2026
- **GCP Project:** illuminator-optimai
- **GCP Auth User:** albert@altan.ai

## GCP Infrastructure

### VM: sage-vm
- **Zone:** europe-southwest1-a
- **Machine Type:** n2-standard-8 (8 vCPU, 32GB RAM)
- **OS:** Windows Server 2022 Datacenter
- **Disc:** 200GB SSD
- **Nested Virtualization:** Enabled (VMX license)
- **Cost:** ~€0.40/hour — STOP WHEN NOT IN USE
- **IP:** Dynamic — check with command below
- **Software installed:** VMware Player 17, OpenSSH, TightVNC (port 5900)
- **VM Sage inside VMware:** Windows Server 2019, 4 vCPU, 6GB RAM, SQL Server + Sage 200

### Get VM IP
```bash
export PATH="$PATH:$HOME/google-cloud-sdk/bin"
gcloud compute instances describe sage-vm \
  --zone=europe-southwest1-a \
  --project=illuminator-optimai \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
```

### Start/Stop VM
```bash
gcloud compute instances start sage-vm --zone=europe-southwest1-a --project=illuminator-optimai
gcloud compute instances stop sage-vm --zone=europe-southwest1-a --project=illuminator-optimai
```

### Other Resources
- **GCS Bucket:** gs://sage-vm-transfer-tmp (VMSage200.zip, VMware Player, VMDK, tar.gz)
- **GCE Image:** sage200-image (backup — not bootable without VirtIO drivers)
- **VMs to delete:** vmdk-converter (TERMINATED), sage200-direct (TERMINATED)
- **Firewall:** allow-rdp (3389), allow-ssh (22), allow-vnc (5900), allow-rdp-sage (3390)

### Cleanup (when audit is done)
```bash
gcloud compute instances delete sage-vm vmdk-converter sage200-direct --zone=europe-southwest1-a --project=illuminator-optimai
gcloud storage rm -r gs://sage-vm-transfer-tmp
gcloud compute images delete sage200-image --project=illuminator-optimai
gcloud compute firewall-rules delete allow-rdp allow-ssh allow-vnc allow-rdp-sage --project=illuminator-optimai
```

## Architecture

```
Python script (local)
  │
  ├── VNC (port 5900) ──→ GCP Windows Server (sage-vm)
  │                          │
  │                          └── VMware Player 17
  │                               └── Sage 200 VM (Win Server 2019)
  │                                    ├── SQL Server
  │                                    └── Sage 200 Cloud
  │
  └── Anthropic API (computer-use)
       └── Claude analyzes screenshots → returns mouse/keyboard actions
```

## Running Computer-Use

```bash
# 1. Start the VM
gcloud compute instances start sage-vm --zone=europe-southwest1-a --project=illuminator-optimai

# 2. Get IP
export SAGE_VM_IP=$(gcloud compute instances describe sage-vm --zone=europe-southwest1-a --project=illuminator-optimai --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

# 3. Ensure VNC is running (SSH in)
ssh albert@$SAGE_VM_IP  # then check TightVNC service

# 4. Run computer-use
export ANTHROPIC_API_KEY=your_key
pip install anthropic vncdotool Pillow
python scripts/computer_use_sage.py              # Navigate admin
python scripts/computer_use_sage.py --create-table  # Create table
python scripts/computer_use_sage.py --custom "..."  # Custom task
```

## Key Files

| File | Purpose |
|------|---------|
| `scripts/computer_use_sage.py` | Main computer-use script (headless VNC, no RDP client needed) |
| `scripts/setup_windows_vm.ps1` | PowerShell setup for the Windows server |
| `scripts/vnc_screenshot.py` | VNC screenshot utility |
| `scripts/rdp_screenshot.py` | RDP screenshot utility (paramiko + PowerShell) |
| `docs/GCP_INFRASTRUCTURE_GUIDE.md` | Full guide to reproduce the GCP setup from scratch |
| `results/EXPERIMENT2_PROGRESS.md` | Detailed progress log |

## Known Issues

1. **VMware Player needs desktop session** — VM doesn't persist without active RDP/console session
2. **VNC shows black screen** — Windows Server without RDP session has no display buffer
3. **VMDK→GCE image failed** — Missing VirtIO drivers, can't boot natively
4. **VM Sage has no DHCP IP** — Internal VMware network not configured for external access

## Next Steps (Experiment 2)
1. RDP into sage-vm, start VMware Player with Sage VM
2. Ensure VNC captures the desktop (with RDP session active)
3. Run computer_use_sage.py to test AI controlling Sage GUI
4. If VNC doesn't work: use SSH+PowerShell screenshot approach as fallback
