# Setup — Why It's Like This and How It Works

## The Short Version

```
Your Mac
  │
  ├── Python script (VNC client)
  │       │
  │       └── VNC :5900 ──────────────────────┐
  │                                            ▼
  │                              ┌──────────────────────────┐
  │                              │  GCP VM "sage-vm"        │
  │                              │  Windows Server 2022     │
  │                              │  (the "host")            │
  │                              │                          │
  │                              │  ┌────────────────────┐  │
  │                              │  │  VMware Player 17  │  │
  │                              │  │                    │  │
  │                              │  │  ┌──────────────┐  │  │
  │                              │  │  │ Sage 200 VM  │  │  │
  │                              │  │  │ Win Srv 2019 │  │  │
  │                              │  │  │ SQL Server   │  │  │
  │                              │  │  │ Sage 200     │  │  │
  │                              │  │  └──────────────┘  │  │
  │                              │  └────────────────────┘  │
  │                              └──────────────────────────┘
  │
  └── Anthropic API (Claude computer-use)
        Claude sees screenshots → decides mouse/keyboard actions
```

## Why Windows on GCP? Why not Linux?

**Sage 200 only runs on Windows.** It needs:
- Windows Server (for the OS)
- SQL Server (for the database)
- .NET Framework (for the application)

There is no Linux version. So we need Windows somewhere.

## Why a VM inside a VM? (Nested Virtualization)

Robert gave us a **VMware virtual machine file** (`.vmdk`) with Sage 200 pre-installed and configured. This is the standard way Solitium distributes their dev environments.

We had two options:

| Option | Approach | Result |
|--------|----------|--------|
| **A. Boot the VMDK directly on GCP** | Convert VMDK → GCE image, boot as native GCP VM | Failed. GCE needs VirtIO drivers which the VMDK doesn't have. Would need to inject drivers into an offline Windows disk — complex and risky. |
| **B. Run VMware inside a Windows host** | Create a Windows Server VM on GCP with nested virtualization, install VMware Player, run the Sage VMDK inside it | Works! This is what we did. |

So we ended up with **2 layers of Windows**:
1. **Host:** Windows Server 2022 on GCP (the outer VM)
2. **Guest:** Windows Server 2019 inside VMware Player (the Sage 200 VM)

## How We Control It

### VNC (TightVNC)
- Installed on the **host** (Windows Server 2022)
- Port 5900, password: `sage2026`
- Shows the host's desktop, where VMware Player runs
- Through VMware's window, we can see and interact with the Sage VM inside

### SSH (OpenSSH)
- Also on the **host**
- Used for admin tasks (restart services, check processes)
- Access: `gcloud compute ssh albert@sage-vm --tunnel-through-iap`

### RDP (Remote Desktop)
- Port 3389 on the host
- Needed to keep the display "alive" for VNC (Windows Server quirk)
- Without an active RDP session, VNC sometimes shows a black screen

## How the Computer-Use Agent Works

1. **Python script** connects to VNC on the GCP host
2. Takes a **screenshot** (1920x1080) of the host desktop
3. Sends it to **Claude Opus** via the Anthropic API with the `computer_20251124` tool
4. Claude analyzes the screenshot and returns an action (click, type, key press)
5. Script executes the action via VNC
6. Loop back to step 2

The agent sees VMware Player's window on the host desktop, and interacts with Sage 200 through it — just like a human would via Remote Desktop.

## Current State

| Component | Status |
|-----------|--------|
| GCP VM (sage-vm) | Running, Windows Server 2022 |
| VMware Player | Running, Sage 200 VM loaded |
| TightVNC | Running on port 5900 |
| VNC connection | Working (agent can see desktop) |
| Sage 200 VM | At login screen (Administrador) |
| Sage 200 VM password | **Unknown — need from Robert** |
| Computer-use agent | Validated — navigates VMware, sends Ctrl+Alt+Del, types passwords |

## Credentials

| What | User | Password | Notes |
|------|------|----------|-------|
| GCP Host (RDP/SSH) | albert | Reset via `gcloud compute reset-windows-password` | Changes each time |
| GCP Host (VNC) | — | sage2026 | TightVNC password |
| Sage VM (inside VMware) | Administrador | **???** | Need from Robert |

## Quick Start

```bash
# 1. Start the GCP VM
export PATH="$PATH:$HOME/google-cloud-sdk/bin"
gcloud compute instances start sage-vm --zone=europe-southwest1-a --project=illuminator-optimai

# 2. Get current IP
export SAGE_VM_IP=$(gcloud compute instances describe sage-vm \
  --zone=europe-southwest1-a --project=illuminator-optimai \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
echo "IP: $SAGE_VM_IP"

# 3. Run the computer-use agent
export ANTHROPIC_API_KEY=sk-ant-...
cd sage/
/tmp/sage_venv/bin/python scripts/test_computer_use_thinking.py --custom "Your task here"

# 4. STOP the VM when done (costs ~€0.40/hour!)
gcloud compute instances stop sage-vm --zone=europe-southwest1-a --project=illuminator-optimai
```

## Known Issues

1. **VNC black screen** — If no one is connected via RDP, the Windows host doesn't render its desktop. Fix: connect via RDP first (even briefly), or the agent's mouse clicks eventually wake it.
2. **Key combos fail via VNC** — vncdotool can't reliably send Ctrl+Alt+Insert. Workaround: use VMware Player's menu → "Send Ctrl+Alt+Del".
3. **Spanish keyboard layout** — The Sage VM has a Spanish keyboard. Special characters like `+` may get remapped when typed via VNC. May need to use key codes instead of text.
4. **Cost** — The GCP VM costs ~€0.40/hour. Always stop it when not in use.

## Why Not Just Use Linux + API?

That's **Plan B** of the audit. Instead of controlling the Sage GUI with computer-use:
- Build a modern API layer on top of Sage 200's REST API
- AI generates web/mobile apps that talk to Sage via API
- No need to touch the legacy GUI at all

Plan B avoids all the VNC/VMware complexity but doesn't validate whether AI can replace the *development* workflow inside Sage's IDE.
