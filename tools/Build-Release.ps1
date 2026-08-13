$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$buildEnvironment = Join-Path $projectRoot '.venv-build'
$releaseDirectory = Join-Path $projectRoot 'release'

Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath $buildEnvironment)) {
        python -m venv $buildEnvironment
    }

    $pythonExecutable = Join-Path $buildEnvironment 'Scripts\python.exe'
    function Invoke-CheckedNative {
        param(
            [Parameter(Mandatory = $true)][string]$Executable,
            [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
        )
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE`: $Executable $($Arguments -join ' ')"
        }
    }

    Invoke-CheckedNative -Executable $pythonExecutable -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
    Invoke-CheckedNative -Executable $pythonExecutable -Arguments @('-m', 'pip', 'install', '-e', "$projectRoot[dev]")
    Invoke-CheckedNative -Executable $pythonExecutable -Arguments @((Join-Path $projectRoot 'tools\build_assets.py'))
    Invoke-CheckedNative -Executable $pythonExecutable -Arguments @('-m', 'ruff', 'check', (Join-Path $projectRoot 'src'), (Join-Path $projectRoot 'tests'), (Join-Path $projectRoot 'tools'))
    Invoke-CheckedNative -Executable $pythonExecutable -Arguments @('-m', 'pytest', '-m', 'not live', (Join-Path $projectRoot 'tests'))
    Invoke-CheckedNative -Executable $pythonExecutable -Arguments @('-m', 'PyInstaller', '--clean', '--noconfirm', '--distpath', (Join-Path $projectRoot 'dist'), '--workpath', (Join-Path $projectRoot 'build'), (Join-Path $projectRoot 'packaging\wallpaper_changer.spec'))

    New-Item -ItemType Directory -Force -Path $releaseDirectory | Out-Null
    $executable = Join-Path $projectRoot 'dist\AutoWallpaperChanger.exe'
    $checksum = Get-FileHash -LiteralPath $executable -Algorithm SHA256
    $checksumLine = "$($checksum.Hash.ToLowerInvariant())  AutoWallpaperChanger.exe`r`n"
    [IO.File]::WriteAllText((Join-Path $releaseDirectory 'AutoWallpaperChanger.exe.sha256'), $checksumLine, (New-Object Text.UTF8Encoding($false)))
    Copy-Item -LiteralPath $executable -Destination (Join-Path $releaseDirectory 'AutoWallpaperChanger.exe') -Force

    $portableZip = Join-Path $releaseDirectory 'AutoWallpaperChanger-Portable-2.0.0.zip'
    $portableFiles = @(
        $executable,
        (Join-Path $projectRoot 'README.md'),
        (Join-Path $projectRoot 'LICENSE'),
        (Join-Path $projectRoot 'PRIVACY.md'),
        (Join-Path $projectRoot 'THIRD_PARTY_NOTICES.md')
    )
    Compress-Archive -LiteralPath $portableFiles -DestinationPath $portableZip -CompressionLevel Optimal -Force
    $zipChecksum = Get-FileHash -LiteralPath $portableZip -Algorithm SHA256
    $allChecksums = @(
        "$($checksum.Hash.ToLowerInvariant())  AutoWallpaperChanger.exe",
        "$($zipChecksum.Hash.ToLowerInvariant())  AutoWallpaperChanger-Portable-2.0.0.zip"
    ) -join "`r`n"
    [IO.File]::WriteAllText((Join-Path $releaseDirectory 'SHA256SUMS.txt'), "$allChecksums`r`n", (New-Object Text.UTF8Encoding($false)))

    $innoCompiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($innoCompiler) {
        & $innoCompiler.Source (Join-Path $projectRoot 'packaging\installer.iss')
    }

    Write-Output "Release created in $releaseDirectory"
}
finally {
    Pop-Location
}
