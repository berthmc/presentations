# Verify available operating system memory
$SysInfo = Get-CimInstance Win32_ComputerSystem
$TotalRAM = [math]::Round($SysInfo.TotalPhysicalMemory / 1GB, 2)
Write-Output "Visible Operating System RAM: $TotalRAM GB"

# Verify active integrated Radeon graphics reservation thresholds
$GPUInfo = Get-CimInstance Win32_VideoController | Where-Object Name -like "*Radeon*"
if ($GPUInfo) {
    $VRAM = [math]::Round($GPUInfo.AdapterRAM / 1GB, 2)
    Write-Output "AMD Radeon 780M VRAM Allocation: $VRAM GB"
    if ($VRAM -lt 8.0) {
        Write-Warning "System VRAM is set below 8.00 GB. Adjust your BIOS settings to avoid local LLM execution failures."
    } else {
        Write-Output "VRAM Allocation is optimal for local 3B/8B execution loops."
    }
} else {
    Write-Output "Physical Integrated Radeon 780M was not discovered on host."
}

$Nvidia = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match 'NVIDIA|RTX' }
if ($Nvidia) {
    Write-Output "Discrete NVIDIA GPU detected: $($Nvidia.Name -join ', ')"
}
