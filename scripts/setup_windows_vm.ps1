# PowerShell script to run on the GCP Windows VM
# Downloads files from GCS bucket and sets up VMware + Sage VM

# Install gcloud CLI on Windows
Write-Host "Installing Google Cloud SDK..."
$installerUrl = "https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe"
$installerPath = "$env:TEMP\GoogleCloudSDKInstaller.exe"
Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
Start-Process -FilePath $installerPath -ArgumentList "/S" -Wait
$env:Path += ";C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin"

# Authenticate (will need interactive login or service account)
Write-Host "Authenticate with: gcloud auth login"
Write-Host "Then run the download commands below:"

# Download files from GCS
Write-Host "`nDownloading VMware Player..."
gsutil cp gs://sage-vm-transfer-tmp/VMware-player-full-17.0.0-20800274.exe C:\Temp\
Write-Host "Downloading VMSage200.zip..."
gsutil cp gs://sage-vm-transfer-tmp/VMSage200.zip C:\Temp\

# Install VMware Player silently
Write-Host "`nInstalling VMware Player..."
Start-Process -FilePath "C:\Temp\VMware-player-full-17.0.0-20800274.exe" -ArgumentList "/s /v/qn EULAS_AGREED=1 AUTOSOFTWAREUPDATE=0" -Wait

# Extract VM
Write-Host "Extracting VMSage200.zip..."
Expand-Archive -Path "C:\Temp\VMSage200.zip" -DestinationPath "C:\VMs\Sage200" -Force

Write-Host "`nSetup complete!"
Write-Host "Next: Open VMware Player and add the VM from C:\VMs\Sage200"
