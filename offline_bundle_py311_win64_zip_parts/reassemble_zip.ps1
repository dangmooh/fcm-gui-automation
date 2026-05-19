param(
    [string]$OutputZip = "offline_bundle_py311_win64.zip"
)

$ErrorActionPreference = "Stop"

$PartDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($PartDir -eq "") {
    $PartDir = Get-Location
}

$Parts = Get-ChildItem -LiteralPath $PartDir -Filter "offline_bundle_py311_win64.zip.part*" |
    Sort-Object Name

if ($Parts.Count -eq 0) {
    throw "No split archive parts found."
}

$OutputPath = Join-Path $PartDir $OutputZip
if (Test-Path $OutputPath) {
    Remove-Item -LiteralPath $OutputPath -Force
}

$OutputStream = [System.IO.File]::Create($OutputPath)
try {
    foreach ($Part in $Parts) {
        Write-Host "Appending $($Part.Name)"
        $InputStream = [System.IO.File]::OpenRead($Part.FullName)
        try {
            $InputStream.CopyTo($OutputStream)
        } finally {
            $InputStream.Dispose()
        }
    }
} finally {
    $OutputStream.Dispose()
}

Write-Host "Created $OutputPath"
Get-FileHash -Algorithm SHA256 -LiteralPath $OutputPath
