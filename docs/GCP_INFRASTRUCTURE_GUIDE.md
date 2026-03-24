# GCP Infrastructure Guide — Sage 200 VM al Cloud

> Guia per reproduir l'entorn Sage 200 al cloud des de zero.
> Última actualització: 24 Mar 2026

## Prerequisits

1. **gcloud CLI** instal·lat i autenticat
2. **Compte GCP** amb facturació activa
3. **VMSage200.zip** (19GB) — la VM VMware amb Sage 200 preinstal·lat
4. **VMware Player installer** (opcional, si vas per nested virt)

## Arquitectura

```
┌─────────────────────────────────────────────┐
│  GCP (europe-southwest1-a)                  │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │  sage-vm (Windows Server 2022)      │    │
│  │  n2-standard-8 · 32GB RAM · 200GB   │    │
│  │  Nested Virt enabled (VMX license)  │    │
│  │                                     │    │
│  │  ┌───────────────────────────┐      │    │
│  │  │  VMware Player 17        │      │    │
│  │  │  ┌─────────────────────┐ │      │    │
│  │  │  │ Sage 200 VM         │ │      │    │
│  │  │  │ Win Server 2019     │ │      │    │
│  │  │  │ 4 vCPU · 6GB RAM   │ │      │    │
│  │  │  │ SQL Server + Sage   │ │      │    │
│  │  │  └─────────────────────┘ │      │    │
│  │  └───────────────────────────┘      │    │
│  └────────────────┬────────────────────┘    │
│                   │ RDP :3389               │
│  ┌────────────────┴────────────────────┐    │
│  │  Firewall: 3389, 22, 5900, 3390    │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  gs://sage-vm-transfer-tmp (bucket)         │
│  sage200-image (GCE image, backup)          │
└─────────────────────────────────────────────┘
```

## Pas 1: Crear projecte i configurar gcloud

```bash
# Si no tens gcloud:
curl https://sdk.cloud.google.com | bash
gcloud init
gcloud auth login

# Usar projecte existent o crear-ne un
gcloud config set project illuminator-optimai
# O: gcloud projects create sage200-audit --name="Sage 200 Audit"
```

## Pas 2: Crear bucket i pujar fitxers

```bash
# Crear bucket temporal
gcloud storage buckets create gs://sage-vm-transfer-tmp \
  --location=europe-southwest1 \
  --uniform-bucket-level-access

# Pujar la VM (19GB, triga ~30min)
gcloud storage cp VMSage200.zip gs://sage-vm-transfer-tmp/

# Pujar VMware Player installer
gcloud storage cp VMware-player-full-17.0.0-20800274.exe gs://sage-vm-transfer-tmp/

# Fer el bucket llegible (perquè la VM Windows pugui descarregar)
gcloud storage buckets add-iam-policy-binding gs://sage-vm-transfer-tmp \
  --member=allUsers --role=roles/storage.objectViewer
```

## Pas 3: Crear firewall rules

```bash
# RDP (accés al servidor Windows)
gcloud compute firewall-rules create allow-rdp \
  --allow=tcp:3389 --direction=INGRESS \
  --source-ranges=0.0.0.0/0 --priority=1000

# SSH
gcloud compute firewall-rules create allow-ssh \
  --allow=tcp:22 --direction=INGRESS \
  --source-ranges=0.0.0.0/0 --priority=1000

# VNC (per computer-use headless)
gcloud compute firewall-rules create allow-vnc \
  --allow=tcp:5900 --direction=INGRESS \
  --source-ranges=0.0.0.0/0 --priority=1000

# RDP forwarding a VM interna (port 3390 → 3389 de la VM Sage)
gcloud compute firewall-rules create allow-rdp-sage \
  --allow=tcp:3390 --direction=INGRESS \
  --source-ranges=0.0.0.0/0 --priority=1000
```

## Pas 4: Crear la VM Windows amb nested virtualization

```bash
# IMPORTANT: Nested virt requereix llicència VMX
gcloud compute instances create sage-vm \
  --zone=europe-southwest1-a \
  --machine-type=n2-standard-8 \
  --image-family=windows-2022 \
  --image-project=windows-cloud \
  --boot-disk-size=200GB \
  --boot-disk-type=pd-ssd \
  --metadata=enable-nested-virtualization=true \
  --min-cpu-platform="Intel Haswell" \
  --licenses="https://www.googleapis.com/compute/v1/projects/vm-options/global/licenses/enable-vmx" \
  --scopes=storage-ro

# Esperar ~5min a que arrenqui
# Obtenir IP
gcloud compute instances describe sage-vm \
  --zone=europe-southwest1-a \
  --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
```

## Pas 5: Configurar Windows (via PowerShell remot o RDP)

### Opció A: Reset password i RDP manual
```bash
# Crear/reset password per RDP
gcloud compute reset-windows-password sage-vm \
  --zone=europe-southwest1-a --user=albert
```

### Opció B: Startup script (automatitzat)
Afegir startup script a la VM que:
1. Instal·li OpenSSH
2. Configuri auto-login
3. Descarregui fitxers del bucket
4. Instal·li VMware Player

```bash
gcloud compute instances add-metadata sage-vm \
  --zone=europe-southwest1-a \
  --metadata-from-file=windows-startup-script-ps1=scripts/setup_windows_vm.ps1
```

### Script PowerShell per setup (executar dins la VM):
```powershell
# 1. Instal·lar OpenSSH
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

# 2. Descarregar VM des de GCS
mkdir C:\VMs\Sage200 -Force
cd C:\VMs\Sage200
Invoke-WebRequest -Uri "https://storage.googleapis.com/sage-vm-transfer-tmp/VMSage200.zip" -OutFile "VMSage200.zip"
Expand-Archive -Path VMSage200.zip -DestinationPath . -Force

# 3. Instal·lar VMware Player
Invoke-WebRequest -Uri "https://storage.googleapis.com/sage-vm-transfer-tmp/VMware-player-full-17.0.0-20800274.exe" -OutFile "vmware.exe"
Start-Process -FilePath "vmware.exe" -ArgumentList "/s /v`"/qn EULAS_AGREED=1 AUTOSOFTWAREUPDATE=0`"" -Wait

# 4. Instal·lar TightVNC (per computer-use headless)
# Descarregar des de tightvnc.com o usar chocolatey:
choco install tightvnc -y --params "/SET_PASSWORD=sage2026 /SET_USEVNCAUTH=1"

# 5. Engegar la VM Sage
$vmxPath = Get-ChildItem -Path "C:\VMs\Sage200" -Recurse -Filter "*.vmx" | Select-Object -First 1
& "C:\Program Files (x86)\VMware\VMware Player\vmrun.exe" start $vmxPath.FullName nogui
```

## Pas 6: Engegar la VM Sage dins VMware

```powershell
# Trobar el .vmx
$vmx = "C:\VMs\Sage200\VMSage200\Sage 200.vmx"

# Engegar (nogui = sense finestra)
& "C:\Program Files (x86)\VMware\VMware Player\vmrun.exe" start "$vmx" nogui

# Verificar que corre
& "C:\Program Files (x86)\VMware\VMware Player\vmrun.exe" list
```

**IMPORTANT:** VMware Player necessita sessió de desktop activa. Si no tens RDP obert, la VM no persisteix. Solucions:
- Mantenir sessió RDP oberta (o usar `tscon` per desconnectar sense tancar sessió)
- Usar VMware Workstation (que sí pot córrer com a servei)

## Pas 7: Accés per computer-use

### Via VNC (recomanat per computer-use)
```bash
# Des de la teva màquina, connecta via VNC al servidor Windows
# El servidor Windows mostra el seu desktop (incloent VMware amb Sage)
# Port: 5900, Password: sage2026
```

### Via RDP forwarding
```bash
# Si la VM Sage té IP interna (ex: 192.168.x.x), configurar port forwarding:
# Al servidor Windows, PowerShell:
netsh interface portproxy add v4tov4 listenport=3390 listenaddress=0.0.0.0 connectport=3389 connectaddress=192.168.x.x
```

## Gestió de costos

```bash
# ATURAR quan no s'usa (~€0.40/hora!)
gcloud compute instances stop sage-vm --zone=europe-southwest1-a

# ENGEGAR quan es necessita
gcloud compute instances start sage-vm --zone=europe-southwest1-a

# ESBORRAR quan s'acabi l'audit
gcloud compute instances delete sage-vm --zone=europe-southwest1-a
gcloud compute instances delete vmdk-converter --zone=europe-southwest1-a
gcloud compute instances delete sage200-direct --zone=europe-southwest1-a
gcloud storage rm -r gs://sage-vm-transfer-tmp
gcloud compute images delete sage200-image
gcloud compute firewall-rules delete allow-rdp allow-ssh allow-vnc allow-rdp-sage
```

## Recursos actuals (24 Mar 2026)

| Recurs | Estat | Notes |
|--------|-------|-------|
| `sage-vm` | RUNNING | Windows Server 2022, VMware + Sage VM instal·lats |
| `vmdk-converter` | TERMINATED | Ubuntu, ja no cal (esborrar) |
| `sage200-direct` | TERMINATED | Intent de boot directe VMDK, va fallar (drivers) |
| `sage200-image` | READY | Imatge GCE del VMDK (backup, no funcional sense drivers) |
| `gs://sage-vm-transfer-tmp` | Actiu | 19GB zip + 36GB vmdk + installer |
| IP sage-vm | 34.175.136.176 | Canvia si es para/engega la VM |

## Lliçons apreses

1. **Nested virtualization a GCP funciona** però requereix llicència VMX explícita
2. **VMware Player** (vs Workstation) no pot córrer VMs sense sessió de desktop — és una limitació important
3. **Convertir VMDK → GCE image** no funciona si la VM original no té drivers VirtIO/GCE
4. **TightVNC** mostra pantalla negra a Windows Server sense sessió RDP activa (no té GPU virtual)
5. **La VM Sage és Windows Server 2019**, 4 vCPU, 6GB RAM, EFI firmware
6. **El bucket ha de ser públic** (o la VM ha de tenir service account amb permisos) per descarregar fitxers
7. **SSH a Windows Server** funciona amb OpenSSH, útil per automatització

## Alternativa provada: Boot directe del VMDK

Va fallar perquè la VM original no té:
- Drivers VirtIO (xarxa/disc GCE)
- GCE guest agent
- Configuració de boot compatible amb hardware GCE

Per fer-ho funcionar caldria:
1. Muntar el VMDK offline
2. Injectar drivers VirtIO
3. Reconfigurar el boot loader
→ Massa complex per l'scope de l'audit.
