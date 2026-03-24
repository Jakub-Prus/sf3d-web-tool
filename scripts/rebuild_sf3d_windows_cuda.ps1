param(
    [string]$PythonExecutable = ".\.venv\Scripts\python.exe",
    [string]$CudaHome = "",
    [string]$VcVarsPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = if ([System.IO.Path]::IsPathRooted($PythonExecutable)) {
    $PythonExecutable
} else {
    Join-Path $repoRoot $PythonExecutable
}

$cudaCandidates = @(
    "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.0",
    "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.9",
    "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8",
    "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.7"
)
$vswhereCandidates = @(
    "C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe",
    "C:\Program Files\Microsoft Visual Studio\Installer\vswhere.exe"
)
$vcvarsSuffix = "VC\Auxiliary\Build\vcvars64.bat"

if (-not (Test-Path $pythonPath)) {
    throw "Python executable not found: $pythonPath"
}

if (-not $CudaHome) {
    foreach ($candidate in $cudaCandidates) {
        if (Test-Path (Join-Path $candidate "bin\nvcc.exe")) {
            $CudaHome = $candidate
            break
        }
    }
}
if (-not $CudaHome) {
    throw "CUDA toolkit not found. Install CUDA and pass -CudaHome explicitly."
}

if (-not $VcVarsPath) {
    foreach ($vswherePath in $vswhereCandidates) {
        if (-not (Test-Path $vswherePath)) {
            continue
        }
        $installPath = & $vswherePath -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
        if ($LASTEXITCODE -eq 0 -and $installPath) {
            $candidate = Join-Path $installPath $vcvarsSuffix
            if (Test-Path $candidate) {
                $VcVarsPath = $candidate
                break
            }
        }
    }
}
if (-not $VcVarsPath -or -not (Test-Path $VcVarsPath)) {
    throw "Visual Studio Build Tools vcvars64.bat not found. Install C++ Build Tools or pass -VcVarsPath explicitly."
}

$patchScript = Join-Path $repoRoot "scripts\patch_windows_torch_cuda_header.py"
& $pythonPath $patchScript
if ($LASTEXITCODE -ne 0) {
    throw "PyTorch Windows CUDA compatibility patch failed."
}

$textureBakerPath = Join-Path $repoRoot "models\stable-fast-3d\texture_baker"
$uvUnwrapperPath = Join-Path $repoRoot "models\stable-fast-3d\uv_unwrapper"
$buildCommand = @(
    "call `"$VcVarsPath`"",
    "set `"CUDA_HOME=$CudaHome`"",
    "set `"PATH=%CUDA_HOME%\bin;!PATH!`"",
    "set DISTUTILS_USE_SDK=1",
    "set MSSdk=1",
    "set CC=cl",
    "set CXX=cl",
    "`"$pythonPath`" -m pip install --force-reinstall --no-build-isolation `"$uvUnwrapperPath`" `"$textureBakerPath`""
) -join " && "

Push-Location $repoRoot
try {
    cmd /v:on /c $buildCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Native CUDA extension rebuild failed."
    }

    & $pythonPath -c "import torch, texture_baker, uv_unwrapper; print('texture_baker CUDA=', torch._C._dispatch_has_kernel_for_dispatch_key('texture_baker_cpp::rasterize', 'CUDA')); print('interpolate CUDA=', torch._C._dispatch_has_kernel_for_dispatch_key('texture_baker_cpp::interpolate', 'CUDA'))"
    if ($LASTEXITCODE -ne 0) {
        throw "CUDA extension verification failed."
    }
} finally {
    Pop-Location
}
