# autobuild.ps1 → Build siêu nhẹ chỉ với Nuitka + UPX

Write-Host "=== CCDLASER - BUILD USING NUITKA ===" -ForegroundColor Cyan
Write-Host "Building... please wait!" -ForegroundColor Yellow

# Tạo thư mục dist nếu chưa có
if (!(Test-Path "dist")) { New-Item -ItemType Directory -Path "dist" | Out-Null }
# --mingw64 ` 
# --lto=yes `
# Lệnh build Nuitka
& python -m nuitka `
  --standalone `
  --onefile `
  --enable-plugin=pyside6 `
  --windows-disable-console `
  --windows-icon-from-ico=icon.ico `
  --assume-yes-for-downloads `
  --jobs=0 `
  --windows-product-name="CCDLaser" `
  --windows-file-description="CCDLaser - Camera Control Software by SWE Team - Ryder" `
  --windows-company-name="SWE Team - Ryder" `
  --windows-product-version=1.1.1.0 `
  --output-dir=dist `
  --output-filename=CCDLaser.exe `
  main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nBuild successfully!" -ForegroundColor Green

    # Nén UPX nếu có
    if (Test-Path "upx.exe") {
        Write-Host "Compressing UPX..." -ForegroundColor Yellow
        .\upx.exe --best --lzma dist/CCDLaser.exe
    } else {
        Write-Host "upx.exe not found → skipping compression." -ForegroundColor DarkYellow
    }

    $size = "{0:N2}" -f ((Get-Item "dist/CCDLaser.exe").Length / 1MB)
    Write-Host "`nCompleted!" -ForegroundColor Cyan
    Write-Host "File output: dist\CCDLaser.exe   |   Size: $size MB" -ForegroundColor Green
    Invoke-Item dist
} else {
    Write-Host "`nBuild failed! Check the error above." -ForegroundColor Red
}

Read-Host "Press Enter to exit"
