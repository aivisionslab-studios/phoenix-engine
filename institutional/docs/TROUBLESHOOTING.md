# Troubleshooting — AIVisions Phoenix Engine

**Dashboard não sobe em `localhost:8000`**
Confirme que `api_server.py` está rodando e que a porta não está em uso.

**"Sistema operacional não suportado" logo no início, no Windows**
Sintoma de o upgrade automático pro PowerShell 7 não ter completado (ex.: winget do PS7 falhou silenciosamente). O `install_phoenix.ps1` atual já trata esse caso — se ainda estiver no PS 5.1 depois da tentativa, segue em modo degradado em vez de travar. Se persistir: `winget install Microsoft.PowerShell` e rode `pwsh ./install_phoenix.ps1` direto.

**GPU não aparece no System Tuner (Windows)**
O processo precisa ser executado como Administrador — sensores de GPU via LibreHardwareMonitor exigem elevação. Rode `Iniciar_Phoenix.bat` como Admin. Se a instalação do LibreHardwareMonitor falhar, o instalador para com erro (componente primordial, não apenas aviso).

**GPU não aparece no System Tuner (Linux)**
Confirme que o driver Mesa RADV está instalado: `vulkaninfo --summary`. Para temperatura, verifique se `lm-sensors` está configurado: `sensors`.

**`ModuleNotFoundError: No module named 'phoenix_kernel.logs'` (ou qualquer outro submódulo)**
Confirme se essa pasta não está sendo capturada por engano pelo `.gitignore`. Um padrão como `logs/` (sem `/` na frente) ignora qualquer pasta chamada `logs` no repositório inteiro — inclusive `phoenix_kernel/logs/`. Rode `git check-ignore -v phoenix_kernel/logs/engine.py` para confirmar, e ancore o padrão com `/logs/` no `.gitignore` se for o caso.

**RAG mostrando 0 documentos**
O arquivo `data/knowledge_base.json` precisa existir. O índice vetorial (`data/chroma_db/`) é gerado localmente a partir dele e não vem no clone.

**Ícone de Desktop não aparece (Linux)**
O instalador roda como root via `sudo`, então precisa resolver o usuário real via `$SUDO_USER` — se você rodou como root "de verdade" (não via sudo), o instalador usa `$HOME` atual e avisa no log. Confirme rodando `sudo pwsh ./install_phoenix.ps1` como usuário normal, não logado direto como root.

**Docker não consegue alcançar llama-server ou sd-server**
Windows Defender bloqueia a subnet Docker (172.x.x.x) por padrão. O instalador já libera as portas oficiais da Phoenix automaticamente; se precisar liberar manualmente:

```powershell
New-NetFirewallRule -DisplayName "Phoenix AI Services" `
  -Direction Inbound -Protocol TCP -LocalPort 8081,7860 -Action Allow
```

## Onde buscar mais ajuda

Consulte os logs locais da Phoenix (comando `logs` no Terminal Deck) e, se necessário, abra uma issue no [repositório oficial](https://github.com/aivisionslab-studios/phoenix-engine) com os detalhes do ambiente (SO, hardware, versão da Phoenix).
