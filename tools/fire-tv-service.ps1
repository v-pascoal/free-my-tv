param(
    [Parameter(Mandatory = $true)][string]$DeviceAddress,
    [string]$Adb = 'adb',
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'
function Invoke-Adb([string[]]$Arguments) {
    $result = & $Adb -s $DeviceAddress @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'ADB command failed; no further commands were run.' }
    return $result
}
$serviceName = 'io.freemytv/io.freemytv.FireTvHomeService'
$raw = (Invoke-Adb -Arguments @('shell', 'settings', 'get', 'secure', 'enabled_accessibility_services') | Out-String).Trim()
$entries = @($raw -split ':' | Where-Object { $_ -and $_ -ne 'null' })
foreach ($entry in $entries) {
    if ($entry -notmatch '^[\w.]+/[\w.$]+$') { throw 'Unexpected component name. Settings left unchanged.' }
}
$updated = @($entries | Where-Object { $_ -ne $serviceName -and $_ -ne 'io.freemytv/.FireTvHomeService' })
if (-not $Remove) { $updated += $serviceName }
if ($updated.Count -eq 0) {
    Invoke-Adb -Arguments @('shell', 'settings', 'delete', 'secure', 'enabled_accessibility_services')
} else {
    Invoke-Adb -Arguments @('shell', 'settings', 'put', 'secure', 'enabled_accessibility_services', ($updated -join ':'))
}
if (-not $Remove) { Invoke-Adb -Arguments @('shell', 'settings', 'put', 'secure', 'accessibility_enabled', '1') }
'Home service list updated. Other accessibility services were preserved.'
