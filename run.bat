@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title 简历工坊 - 环境检查
pushd "%~dp0"

set "ROOT=%CD%"
set "RUNTIME=%ROOT%\.runtime"
set "VENV=%ROOT%\.venv"
set "PY=%VENV%\Scripts\python.exe"
set "LOG=%RUNTIME%\logs\bootstrap.log"
set "MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple"
set "PY_MIRROR=https://registry.npmmirror.com/-/binary/python/3.12.10/python-3.12.10-amd64.exe"
set "PY_OFFICIAL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
set "PLAYWRIGHT_MIRROR=https://registry.npmmirror.com/-/binary/playwright"
set "PORT=8765"

if not exist "%RUNTIME%" mkdir "%RUNTIME%"
if not exist "%RUNTIME%\logs" mkdir "%RUNTIME%\logs"
if not exist "%RUNTIME%\temp" mkdir "%RUNTIME%\temp"
if not exist "%RUNTIME%\pip-cache" mkdir "%RUNTIME%\pip-cache"
if not exist "%RUNTIME%\ms-playwright" mkdir "%RUNTIME%\ms-playwright"

set "TEMP=%RUNTIME%\temp"
set "TMP=%RUNTIME%\temp"
set "PIP_CACHE_DIR=%RUNTIME%\pip-cache"
set "PLAYWRIGHT_BROWSERS_PATH=%RUNTIME%\ms-playwright"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONNOUSERSITE=1"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PIP_NO_INPUT=1"

echo ============================================
echo   简历工坊 Resume Studio
echo   首次启动需要安装依赖，请保持网络连接
echo ============================================
echo.

echo [1/5] 检查运行环境...
call :ensure_python
if errorlevel 1 goto :fail

echo [2/5] 检查 Python 依赖...
call :ensure_deps
if errorlevel 1 goto :fail

echo [3/5] 检查浏览器内核...
call :ensure_chromium
if errorlevel 1 goto :fail

echo [4/5] 检查前端资源...
if not exist "%ROOT%\frontend\dist\index.html" (
  echo    [错误] 缺少前端构建产物 frontend\dist\index.html
  echo    请使用完整发布包，或由开发者执行 build_frontend.bat
  goto :fail
)

echo [5/5] 启动本地服务...
call :pick_port
>"%RUNTIME%\runtime.json" echo {"port": %PORT%}
set "RESUME_PORT=%PORT%"
start "简历工坊 - 请勿关闭此窗口" cmd /k ""%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port %PORT%"

echo    等待服务就绪...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='http://127.0.0.1:%PORT%/api/health'; for($i=0;$i -lt 60;$i++){ try { $r=Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){ exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1"
if errorlevel 1 (
  echo    [错误] 服务启动超时，请查看控制台窗口与日志：
  echo    %LOG%
  goto :fail
)

start "" "http://127.0.0.1:%PORT%"
echo.
echo 启动成功，浏览器已打开：http://127.0.0.1:%PORT%
echo 本窗口可以关闭，请勿关闭标题为“简历工坊”的服务窗口。
timeout /t 4 >nul
popd
exit /b 0

:ensure_python
set "VENV_OK="
if exist "%PY%" (
  "%PY%" -c "import sys,pathlib; sys.exit(0 if sys.version_info[:2]==(3,12) and pathlib.Path(sys.prefix).resolve()==pathlib.Path(r'%VENV%').resolve() else 1)" >nul 2>&1
  if not errorlevel 1 set "VENV_OK=1"
)
if defined VENV_OK goto :python_ready
if exist "%PY%" (
  echo    检测到虚拟环境版本不兼容或已损坏，正在自动重建...
  echo    [%date% %time%] venv invalid, rebuild >>"%LOG%"
  call :rebuild_venv
  if errorlevel 1 exit /b 1
)
set "SYSPY="
if exist "%RUNTIME%\python\python.exe" (
  "%RUNTIME%\python\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "SYSPY="%RUNTIME%\python\python.exe""
  ) else (
    echo    项目内置 Python 版本不兼容，正在重新安装...
    rd /s /q "%RUNTIME%\python" >nul 2>&1
  )
)
if not defined SYSPY (
  py -3.12 -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "SYSPY=py -3.12"
    echo    使用系统 Python 3.12
  )
)
if not defined SYSPY (
  python -c "import sys; sys.exit(0 if sys.version_info[:2]==(3,12) else 1)" >nul 2>&1
  if not errorlevel 1 (
    set "SYSPY=python"
    echo    使用系统 Python 3.12
  ) else (
    where python >nul 2>&1 && echo    检测到系统 Python 版本不符合要求（需要 3.12），已忽略
  )
)
if not defined SYSPY (
  echo    未找到兼容的 Python 3.12，正在下载并安装到本目录 .runtime\python ...
  echo    [%date% %time%] download python >>"%LOG%"
  set "INSTALLER=%RUNTIME%\python-installer.exe"
  if exist "!INSTALLER!" del /f /q "!INSTALLER!"
  echo    正在从国内镜像下载 Python 安装包...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '!PY_MIRROR!' -OutFile '!INSTALLER!' -UseBasicParsing -TimeoutSec 300 } catch { exit 1 }"
  set "INSTALLER_OK="
  if exist "!INSTALLER!" for %%A in ("!INSTALLER!") do if %%~zA GEQ 20000000 set "INSTALLER_OK=1"
  if not defined INSTALLER_OK (
    if exist "!INSTALLER!" del /f /q "!INSTALLER!"
    echo    镜像下载失败或文件不完整，切换官方源重试...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '!PY_OFFICIAL!' -OutFile '!INSTALLER!' -UseBasicParsing -TimeoutSec 300 } catch { exit 1 }"
    if exist "!INSTALLER!" for %%A in ("!INSTALLER!") do if %%~zA GEQ 20000000 set "INSTALLER_OK=1"
  )
  if not defined INSTALLER_OK (
    if exist "!INSTALLER!" del /f /q "!INSTALLER!"
    echo    [错误] Python 安装包下载失败或文件不完整，请检查网络连接。
    exit /b 1
  )
  "!INSTALLER!" /quiet InstallAllUsers=0 TargetDir="%RUNTIME%\python" Include_pip=1 Include_launcher=0 PrependPath=0 Shortcuts=0 Include_test=0
  if not exist "%RUNTIME%\python\python.exe" (
    echo    [错误] Python 静默安装失败，可能被杀毒软件拦截。
    exit /b 1
  )
  set "SYSPY="%RUNTIME%\python\python.exe""
)
if not exist "%PY%" (
  echo    正在创建虚拟环境 .venv ...
  echo    [%date% %time%] create venv >>"%LOG%"
  %SYSPY% -m venv "%VENV%" >>"%LOG%" 2>&1
  if errorlevel 1 (
    echo    [错误] 虚拟环境创建失败，请查看日志。
    exit /b 1
  )
  if exist "%RUNTIME%\deps.sha256" del /f /q "%RUNTIME%\deps.sha256"
  if exist "%RUNTIME%\playwright.ok" del /f /q "%RUNTIME%\playwright.ok"
)
:python_ready
"%PY%" -m ensurepip --upgrade >nul 2>&1
exit /b 0

:rebuild_venv
set "BROKEN=%VENV%.broken"
if exist "%BROKEN%" rd /s /q "%BROKEN%" >nul 2>&1
move "%VENV%" "%BROKEN%" >nul 2>&1
if errorlevel 1 (
  echo    [错误] 无法重建虚拟环境，请先关闭正在运行的服务窗口后重试。
  exit /b 1
)
rd /s /q "%BROKEN%" >nul 2>&1
if exist "%RUNTIME%\deps.sha256" del /f /q "%RUNTIME%\deps.sha256"
if exist "%RUNTIME%\playwright.ok" del /f /q "%RUNTIME%\playwright.ok"
exit /b 0

:ensure_deps
"%PY%" -c "import hashlib,sys,pathlib; h=hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest(); t=sys.version.split()[0]+'|'+h; p=pathlib.Path(r'.runtime/deps.sha256'); sys.exit(0 if p.exists() and p.read_text().strip()==t else 1)"
if not errorlevel 1 exit /b 0
echo    正在安装依赖，首次可能需要几分钟...
echo    [%date% %time%] pip install >>"%LOG%"
"%PY%" -m pip install -r requirements.txt -i %MIRROR% >>"%LOG%" 2>&1
if errorlevel 1 (
  echo    镜像源安装失败，切换官方源重试...
  "%PY%" -m pip install -r requirements.txt >>"%LOG%" 2>&1
  if errorlevel 1 (
    echo    [错误] 依赖安装失败，日志最后 20 行：
    powershell -NoProfile -Command "Get-Content -Path '%LOG%' -Tail 20"
    exit /b 1
  )
)
"%PY%" -c "import hashlib,sys,pathlib; h=hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest(); pathlib.Path(r'.runtime/deps.sha256').write_text(sys.version.split()[0]+'|'+h)"
exit /b 0

:ensure_chromium
set "PW_VERSION="
"%PY%" -c "import importlib.metadata as m,pathlib; pathlib.Path(r'%RUNTIME%\pw.version').write_text(m.version('playwright'))" >nul 2>&1
if exist "%RUNTIME%\pw.version" (
  set /p PW_VERSION=<"%RUNTIME%\pw.version"
  del /f /q "%RUNTIME%\pw.version"
)
set "CHROME_FOUND="
for /d %%D in ("%PLAYWRIGHT_BROWSERS_PATH%\chromium-*") do set "CHROME_FOUND=1"
if defined CHROME_FOUND (
  if exist "%RUNTIME%\playwright.ok" (
    set /p PW_OK=<"%RUNTIME%\playwright.ok"
    if "!PW_OK!"=="!PW_VERSION!" exit /b 0
  )
)
echo    正在下载浏览器内核，首次可能需要几分钟...
echo    [%date% %time%] playwright install >>"%LOG%"
set "PLAYWRIGHT_DOWNLOAD_HOST=%PLAYWRIGHT_MIRROR%"
"%PY%" -m playwright install chromium >>"%LOG%" 2>&1
if errorlevel 1 (
  echo    部分内核镜像缺失，切换官方源补齐...
  set "PLAYWRIGHT_DOWNLOAD_HOST="
  "%PY%" -m playwright install chromium >>"%LOG%" 2>&1
  if errorlevel 1 (
    echo    [错误] 浏览器内核下载失败，请检查网络后重新双击 run.bat。
    exit /b 1
  )
)
if defined PW_VERSION >"%RUNTIME%\playwright.ok" echo !PW_VERSION!
exit /b 0

:pick_port
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul
if not errorlevel 1 (
  set /a PORT+=1
  if !PORT! GTR 8800 (
    echo    [错误] 8765-8800 端口均被占用，请关闭占用程序后重试。
    exit /b 1
  )
  goto :pick_port
)
exit /b 0

:fail
echo.
echo 启动失败。请查看日志：%LOG%
echo 可将本窗口截图发送给开发者。
pause
popd
exit /b 1
