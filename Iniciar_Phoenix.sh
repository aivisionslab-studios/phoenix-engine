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

# PHX-FIX: o arquivo pode existir e mesmo assim nao funcionar - por exemplo
# se o Python-base usado para criar o venv foi removido/atualizado depois
# (o venv guarda o caminho original em .venv/pyvenv.cfg e falha ao rodar
# se ele nao existir mais). Valida de verdade antes de seguir.
if ! .venv/bin/python --version >/dev/null 2>&1; then
    echo ""
    echo "[X] O ambiente virtual existe, mas o Python dele nao roda"
    echo "    (provavelmente o Python-base usado para cria-lo foi removido ou"
    echo "    atualizado depois). Apague a pasta .venv e rode"
    echo "    'sudo pwsh ./install_phoenix.ps1' de novo para recria-lo."
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
