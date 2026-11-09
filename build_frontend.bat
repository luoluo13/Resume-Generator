@echo off
setlocal EnableExtensions
chcp 65001 >nul
title 简历工坊 - 前端构建
pushd "%~dp0"

where node >nul 2>&1
if errorlevel 1 (
  echo [错误] 未检测到 Node.js，仅开发者需要构建前端。
  goto :fail
)

pushd frontend
if exist package-lock.json (
  call npm ci
) else (
  call npm install
)
if errorlevel 1 goto :fail

call npm run build
if errorlevel 1 goto :fail
popd

echo.
echo 构建完成：frontend\dist
popd
exit /b 0

:fail
echo.
echo 构建失败，请查看上方日志。
popd
pause
exit /b 1
