# Deploy the pinned Mesa 26.2.4 WGL llvmpipe runtime beside a Python
# executable. Hosted Windows runners have no GPU; an app-local
# opengl32.dll gives GTK a real OpenGL implementation for the GLArea smoke.
param(
  [Parameter(Mandatory = $true)][string]$PythonExe
)
$ErrorActionPreference = 'Stop'

$archive = Join-Path $env:RUNNER_TEMP 'mesa3d-26.2.4-release-msvc.7z'
$url = 'https://github.com/pal1000/mesa-dist-win/releases/download/26.2.4/mesa3d-26.2.4-release-msvc.7z'
$expectedSha256 = '351fc8c8b695878ffb3eaa044b3ead08672a48b1a045e3c3e3975811df0f6695'
Invoke-WebRequest -Uri $url -OutFile $archive
$actualSha256 = (Get-FileHash -Path $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualSha256 -ne $expectedSha256) {
  throw "Mesa archive SHA-256 mismatch: $actualSha256"
}

$sevenZip = (Get-Command 7z.exe -ErrorAction SilentlyContinue).Source
if (-not $sevenZip) {
  $sevenZip = Join-Path $env:ProgramFiles '7-Zip\7z.exe'
}
if (-not (Test-Path $sevenZip)) {
  throw '7-Zip is required to extract the pinned Mesa runtime.'
}
$extractDir = Join-Path $env:RUNNER_TEMP 'mesa3d-26.2.4'
& $sevenZip x $archive "-o$extractDir" -y
if ($LASTEXITCODE -ne 0) {
  throw "7-Zip extraction failed with exit code $LASTEXITCODE"
}

$mesaDir = Get-ChildItem -Path $extractDir -Directory -Filter x64 -Recurse |
  Select-Object -First 1 -ExpandProperty FullName
if (-not $mesaDir) {
  throw 'The pinned Mesa archive contains no x64 runtime directory.'
}
if (-not (Test-Path $PythonExe)) {
  throw "Python executable not found: $PythonExe"
}
$appDir = Split-Path -Parent $PythonExe
foreach ($dll in @('opengl32.dll', 'libgallium_wgl.dll')) {
  $source = Join-Path $mesaDir $dll
  if (-not (Test-Path $source)) {
    throw "Required Mesa WGL file is missing: $source"
  }
  Copy-Item -Path $source -Destination $appDir -Force
}
Write-Output "Pinned Mesa WGL llvmpipe runtime deployed beside $PythonExe"
