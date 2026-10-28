@echo off
rem Abre o BrasBim. Na primeira vez, instala o Python e as bibliotecas (precisa de internet).
chcp 65001 >nul
setlocal
title BrasBim
cd /d "%~dp0"

set "PYVER=3.14.3"
rem Ambiente fora desta pasta, num caminho curto (limite de 260 caracteres do Windows)
set "VENV=%LOCALAPPDATA%\BrasBim\ambiente"
set "OK=%VENV%\pronto.txt"

if not exist "%OK%" goto preparar
"%VENV%\Scripts\python.exe" -c "import PySide6, ifcopenshell" >nul 2>&1 && goto abrir
rem A instalação estragou: prepara de novo.
rmdir /s /q "%VENV%"

:preparar
echo.
echo  ==========================================================
echo    BrasBim - preparando este computador (só na 1ª vez)
echo    Precisa de internet e leva de 5 a 10 minutos.
echo    Não feche esta janela.
echo  ==========================================================
echo.

rem --- 1. Python ------------------------------------------------
set "PY="
for %%V in (3.14 3.13 3.12) do (
    if not defined PY py -%%V -c "pass" >nul 2>&1 && set "PY=py -%%V"
)
if defined PY goto ambiente
set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if exist "%PYEXE%" goto achou

echo  [1/3] Baixando o Python %PYVER% (site oficial python.org)...
set "INST=%TEMP%\python-%PYVER%-amd64.exe"
curl -L --fail -o "%INST%" "https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-amd64.exe"
if errorlevel 1 goto erro_download
echo  [1/3] Instalando o Python (pode aparecer uma janela pedindo permissão)...
"%INST%" /quiet InstallAllUsers=0 InstallLauncherAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0
del "%INST%" >nul 2>&1
if not exist "%PYEXE%" goto erro_python

:achou
set PY="%PYEXE%"

:ambiente
rem --- 2. Ambiente próprio do BrasBim -------------------------
echo  [2/3] Criando o ambiente do BrasBim...
%PY% -m venv "%VENV%"
if errorlevel 1 goto erro_python

rem --- 3. Bibliotecas ------------------------------------------
echo  [3/3] Baixando as bibliotecas (a maior demora um pouco)...
"%VENV%\Scripts\python.exe" -m pip install --disable-pip-version-check -r "%~dp0requisitos.txt"
if errorlevel 1 goto erro_pip
echo ok> "%OK%"

rem Atalho na Área de Trabalho
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\BrasBim.lnk'); $s.TargetPath='%~f0'; $s.WorkingDirectory='%~dp0'; $s.WindowStyle=7; $s.Save()" >nul 2>&1

echo.
echo  Pronto! Criei um atalho "BrasBim" na Área de Trabalho.
echo  Das próximas vezes o BrasBim abre direto.
echo.
timeout /t 5 >nul

:abrir
start "" "%VENV%\Scripts\pythonw.exe" -m brasbim.ui.app %*
exit /b 0

:erro_download
echo.
echo  Não consegui baixar o Python. Confira a internet e tente de novo.
goto fim_erro
:erro_python
echo.
echo  Não consegui instalar o Python. Instale o Python 3.14 pelo site python.org
echo  (marque "Add python.exe to PATH") e abra este arquivo de novo.
goto fim_erro
:erro_pip
echo.
echo  Não consegui baixar as bibliotecas. Confira a internet e tente de novo.
if exist "%VENV%" rmdir /s /q "%VENV%"
:fim_erro
echo.
pause
exit /b 1
