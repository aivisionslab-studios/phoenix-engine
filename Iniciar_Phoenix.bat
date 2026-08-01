@echo off
REM Iniciar_Phoenix.bat
REM Launcher UNICO da Phoenix Engine: detecta se e a primeira execucao
REM (instala se precisar) e depois sempre sobe a API. Junta o que antes
REM era Instalar_Phoenix.bat + Iniciar_Phoenix.bat num arquivo so.
REM
REM Por que ainda precisa ser um .bat (e nao chamar o .ps1 direto):
REM arquivos .ps1 sao bloqueados pela Execution Policy do PowerShell
REM ANTES de qualquer linha do script rodar - ou seja, o proprio
REM install_phoenix.ps1 nao consegue se "auto-liberar", porque o Windows
REM PowerShell recusa carregar o arquivo. Um .bat nao sofre essa
REM restricao, entao ele e quem chama o powershell.exe ja com
REM -ExecutionPolicy Bypass.
REM
REM Nota tecnica sobre o "goto" abaixo (em vez de aninhar if dentro de if):
REM dentro de um bloco "if (...)" do batch, todas as variaveis %VAR% sao
REM expandidas de UMA VEZ SO, no momento em que o bloco inteiro e lido -
REM ou seja, se o "if %ERRORLEVEL%" do instalador estivesse aninhado
REM dentro do "if not exist (...)", ele checaria o ERRORLEVEL de ANTES do
REM PowerShell rodar, nao o resultado real da instalacao. Usar "goto"
REM mantem cada "if %ERRORLEVEL%" no nivel principal do script, onde a
REM expansao acontece na hora certa, linha por linha.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto :start

echo.
echo [i] Ambiente virtual nao encontrado - primeira execucao detectada.
echo     Rodando o instalador da Phoenix Engine...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_phoenix.ps1"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [X] O instalador terminou com erro. Veja as mensagens acima.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [X] O instalador terminou sem erro, mas o ambiente virtual ainda
    echo     nao existe em .venv\Scripts\python.exe. Alguma coisa no
    echo     install_phoenix.ps1 nao criou o venv onde este launcher espera
    echo     - confira o log da instalacao acima antes de tentar de novo.
    pause
    exit /b 1
)

:start
".venv\Scripts\python.exe" api_server.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [X] A Phoenix encerrou com erro. Veja as mensagens acima.
    pause
)
