# Experiment 2: VM Sage 200 al Cloud + Computer-Use

## Objectiu
Muntar una VM amb Sage 200 al cloud (GCP) i provar computer-use per controlar la GUI de Sage amb IA.

## Estat: EN CURS — Infraestructura muntada, pendent testar computer-use

## Infraestructura Creada

### Servidor Windows GCP (sage-vm)
- **Machine type:** n2-standard-8 (8 vCPU, 32GB RAM)
- **Zone:** europe-southwest1-a
- **OS:** Windows Server 2022 Datacenter
- **Disc:** 200GB SSD
- **Nested virtualization:** Habilitada (llicència VMX)
- **Cost estimat:** ~€0.40/hora (~€10/dia si 24h)

### GCS Bucket (sage-vm-transfer-tmp)
- Bucket temporal per transferir fitxers
- Conté: VMSage200.zip (19GB), VMware Player installer, sage200.vmdk (36GB), sage200.tar.gz (18GB)

### Firewall Rules
- allow-rdp: TCP 3389
- allow-ssh: TCP 22
- allow-vnc: TCP 5900
- allow-rdp-sage: TCP 3390

## Passos Completats

### 1. gcloud CLI instal·lat i autenticat ✅
- Projecte: illuminator-optimai
- Usuari: albert@altan.ai

### 2. Servidor Windows creat a GCP ✅
- Auto-login configurat
- OpenSSH instal·lat (accés remot via SSH)
- TightVNC instal·lat (port 5900)

### 3. VMware Player instal·lat + VM Sage descomprimida ✅
- VMware Player 17 instal·lat silenciosament
- VM extreta a C:\VMs\Sage200\VMSage200\
- Fitxers: Sage 200.vmdk (36GB), Sage 200.vmx, etc.

### 4. VM Sage identificada ✅
- Guest OS: Windows Server 2019 (Build 17763.379)
- Firmware: EFI
- 4 vCPU, 6GB RAM
- VMware Tools instal·lats
- SQL Server + Sage 200 preinstal·lats

### 5. VM Sage engegada dins VMware ✅
- `vmrun start "C:\VMs\Sage200\VMSage200\Sage 200.vmx" nogui`
- La VM arrenca correctament

### 6. VMDK pujat a GCS i imatge creada ✅
- VMDK convertit a RAW, comprimit, pujat com tar.gz (18GB)
- Imatge GCE `sage200-image` creada (READY)
- **Resultat:** No funcional per boot directe (falta VirtIO drivers)
- Guardat com backup per si es necessita en el futur

## Problemes Trobats i Solucions

### VMware Player no manté VM sense sessió de desktop
- **Problema:** `vmrun start` funciona però la VM no persisteix sense sessió interactiva
- **Causa:** VMware Player (vs Workstation) necessita sessió de consola activa
- **Solució:** Mantenir sessió RDP oberta o usar `tscon` per desconnectar sense tancar

### VNC mostra pantalla negra
- **Problema:** TightVNC funciona (port obert, auth correcta) però pantalla negra
- **Causa:** Windows Server sense sessió RDP activa no renderitza display buffer
- **Solució:** Cal obrir una sessió RDP primer (encara que sigui disconnected)

### Boot directe VMDK no funciona
- **Problema:** sage200-direct entra en loop "Automatic Repair"
- **Causa:** La VM original no té drivers VirtIO/GCE
- **Solució:** Caldria injectar drivers offline — fora de scope

### VM Sage no obté IP per DHCP
- **Problema:** La VM Sage dins VMware no rep IP per DHCP
- **Causa:** Adaptador de xarxa intern no configurat
- **Solució:** Configurar IP estàtica dins la VM o usar NAT de VMware

## Enfocament per Computer-Use

L'script `scripts/computer_use_sage.py` funciona completament headless:

1. **VNC** (preferit): Connecta via `vncdotool` al port 5900 del servidor Windows
2. **SSH+PowerShell** (fallback): Captura screenshots via PowerShell remotament
3. **FreeRDP** (alternatiu): Per entorns Linux amb Xvfb

### Prerequisits per funcionar
1. La VM `sage-vm` ha d'estar engegada
2. Cal una sessió RDP activa (perquè VNC pugui capturar el desktop)
3. VMware Player ha d'estar obert amb la VM Sage corrent
4. TightVNC ha d'estar escoltant al port 5900

### Flow
```
computer_use_sage.py → VNC screenshot → Anthropic API → Claude analitza →
acció (click/type/key) → VNC envia acció → espera → VNC screenshot → repeat
```

## Dates
- **23 Mar 2026 ~17:00** — VM sage-vm creada
- **23 Mar 2026 ~17:23** — VM Sage descomprimida i engegada dins VMware
- **23 Mar 2026 ~19:05** — VMDK pujat a GCS (36GB)
- **23 Mar 2026 ~20:00** — Imatge GCE sage200-image creada
- **23 Mar 2026 ~20:10** — sage200-direct creat → falla (Automatic Repair loop)
- **24 Mar 2026** — Documentació i script computer-use actualitzats

## Pròxims Passos
1. [ ] Connectar per RDP al servidor Windows (sage-vm)
2. [ ] Verificar que VMware Player + VM Sage estan corrent
3. [ ] Confirmar que VNC captura el desktop correctament
4. [ ] Executar `computer_use_sage.py` — test de navegació
5. [ ] Si funciona: test complet amb creació de taules i scripts 4GL
6. [ ] Documentar resultats a EXPERIMENT2_RESULTS.md
