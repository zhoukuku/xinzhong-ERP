param(
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$secureCode = Read-Host "Enter Xinzhong ERP access code" -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureCode)

try {
    $accessCode = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    if ([string]::IsNullOrWhiteSpace($accessCode)) {
        throw "Access code cannot be empty"
    }

    $env:XINZHONG_ERP_HOST = $BindHost
    $env:XINZHONG_ERP_PORT = [string]$Port
    $env:XINZHONG_ERP_ACCESS_CODE = $accessCode
    Set-Location -LiteralPath $PSScriptRoot
    python server.py
}
finally {
    if ($pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
    Remove-Item Env:XINZHONG_ERP_ACCESS_CODE -ErrorAction SilentlyContinue
}
