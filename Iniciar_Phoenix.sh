#!/usr/bin/env bash
# Iniciar_Phoenix.sh
# Launcher de USO DIARIO da Phoenix Engine (Linux) - depois que a instalacao
# ja foi feita uma vez com "sudo pwsh ./install_phoenix.ps1". Nao reinstala
# nada, so ativa o venv ja criado e sobe o api_server.py (porta 8000).
# E o alvo do atalho .desktop criado pelo linux.ps1.

cd "$(dirname "$0")" || exit 1

if [ ! -f ".venv/bin/python" ]; then
    echo ""
    echo "[X] Ambiente virtual nao encontrado (.venv/bin/python)."
    echo "    Rode 'sudo pwsh ./install_phoenix.ps1' primeiro para provisionar a Phoenix."
    echo ""
    read -rp "Pressione Enter para sair..."
    exit 1
fi

.venv/bin/python api_server.py
status=$?

if [ $status -ne 0 ]; then
    echo ""
    echo "[X] A Phoenix encerrou com erro (codigo $status). Veja as mensagens acima."
    read -rp "Pressione Enter para sair..."
fi
