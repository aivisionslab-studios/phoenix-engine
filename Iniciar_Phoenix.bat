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

if not exist ".venv\Scripts\python.exe" goto :install

REM PHX-FIX: "if exist" so confere que o ARQUIVO existe - um venv cujo
REM pyvenv.cfg aponta pra um Python que foi desinstalado/movido (ex: apos
REM o instalador reinstalar/reparar o Python numa execucao posterior)
REM ainda passa nesse teste e so quebra depois, na cara do usuario, com a
REM mensagem confusa "No Python at ...". Valida de verdade rodando
REM --version antes de decidir pular a instalacao.
".venv\Scripts\python.exe" --version >nul 2>&1
if %ERRORLEVEL% equ 0 goto :check_storage

echo.
echo [!] Ambiente virtual encontrado, mas o Python dele nao responde
echo     (provavelmente o Python original foi movido/reinstalado depois
echo     que o venv foi criado). Recriando o ambiente virtual...
echo.
rmdir /s /q ".venv" >nul 2>&1
goto :install

:check_storage
REM PHX-FIX (auditoria 2026-08-04): mesmo problema do venv, mas pro
REM storage.json (workspace no disco NVMe/SSD/HDD mais rapido, escolhido
REM por install/storage_scanner.ps1). Uma vez gravado, nada revalidava se
REM aquele caminho ainda existe - se a letra do drive mudar (disco
REM removido/remapeado, unidade de rede desconectada) entre uma execucao
REM e outra, a Phoenix continuaria confiando cegamente num caminho morto.
REM Revalida de verdade a cada inicializacao, sem custo perceptivel
REM (checagem de arquivo, nao um scan de disco completo).
powershell -NoProfile -Command "$p = Join-Path $env:ProgramData 'Phoenix\storage.json'; if (-not (Test-Path $p)) { exit 1 }; try { $j = Get-Content $p -Raw | ConvertFrom-Json } catch { exit 1 }; if (-not $j.workspace -or -not (Test-Path $j.workspace)) { exit 1 } else { exit 0 }" >nul 2>&1
if %ERRORLEVEL% equ 0 goto :start

REM Trava de seguranca: nunca reinstala mais de uma vez por causa disso -
REM se falhar de novo logo apos reinstalar, e um problema persistente
REM (ex: permissao negada em ProgramData), nao uma unidade que sumiu.
if defined PHX_STORAGE_RETRY (
    echo.
    echo [X] storage.json continua invalido mesmo apos reinstalar. Confira
    echo     permissoes de %ProgramData%\Phoenix\ ou rode
    echo     install\storage_scanner.ps1 manualmente para ver o erro.
    pause
    exit /b 1
)
set PHX_STORAGE_RETRY=1

echo.
echo [!] storage.json ausente, corrompido, ou aponta para um disco que nao
echo     existe mais (ex: unidade removida/remapeada). Rodando o instalador
echo     de novo para redetectar o melhor disco (NVMe/SSD/HDD)...
echo.
goto :install

:install

echo.
echo [i] Rodando o instalador da Phoenix Engine...
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

goto :check_storage

:start
".venv\Scripts\python.exe" api_server.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [X] A Phoenix encerrou com erro. Veja as mensagens acima.
    pause
)
