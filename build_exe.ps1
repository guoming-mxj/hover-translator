# 打包脚本：双击或在本目录执行 .\build_exe.ps1
python -m PyInstaller --noconfirm --clean --windowed --name HoverTranslator `
  --collect-all rapidocr_onnxruntime `
  --collect-all pystray `
  --collect-all PIL `
  --hidden-import pynput.keyboard._win32 `
  --hidden-import pynput.mouse._win32 `
  main.py

Write-Host "完成，产物位于 dist\HoverTranslator\HoverTranslator.exe"
