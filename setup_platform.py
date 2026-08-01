"""
setup_platform.py
==================
Automatiza o BUILD da Phoenix Aviary Platform (app exportado do Google
AI Studio) para que o usuário final nunca precise rodar `npm` na mão.

IMPORTANTE (correção de arquitetura): essa Platform NÃO é um site
estático. Ela roda um servidor Node.js próprio (`dist/server.cjs`) que
faz o ping dos provedores (Ollama/LM Studio) do lado do servidor -
por isso ela evita CORS sem precisar mexer no Ollama. Isso significa
que o processo precisa ficar RODANDO, não só "compilado e servido como
arquivo estático". Quem sobe/vigia o processo é o platform_process.py,
chamado pelo kernel.py. Este arquivo aqui cuida só do build.

Fluxo:
  1. Verifica se já existe platform_source/dist/server.cjs -> se sim,
     não builda de novo (custo zero em boots subsequentes).
  2. Verifica/instala Node.js via winget (mesmo padrão do resto da
     Phoenix pra Git/Docker/Vulkan).
  3. Roda `npm install` + `npm run build` dentro de platform_source/.
  4. Confirma que o build gerou dist/server.cjs (se o projeto do AI
     Studio gerar noutro caminho, ajuste SERVER_ENTRY abaixo).
"""

from __future__ import annotations
import subprocess
import sys
from pathlib import Path

PLATFORM_SOURCE = Path("platform_source")
SERVER_ENTRY = PLATFORM_SOURCE / "dist" / "server.cjs"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    print(f"[setup_platform] Executando: {' '.join(cmd)} (em {cwd})")
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=(sys.platform == "win32"))


def is_platform_built() -> bool:
    # Não basta o server.cjs existir - se node_modules/express sumir
    # (ex: zip sem node_modules, ou npm install incompleto), o processo
    # crasha com "Cannot find module" mesmo com server.cjs presente.
    # Checar os dois evita a Phoenix achar que "já está pronto" quando
    # na real falta a dependência.
    node_modules_ok = (PLATFORM_SOURCE / "node_modules" / "express").exists()
    return SERVER_ENTRY.exists() and node_modules_ok


def is_node_installed() -> bool:
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, shell=(sys.platform == "win32"))
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_node_via_winget() -> bool:
    """Mesmo padrão já usado pela Phoenix pra Git/Docker/Vulkan SDK -
    winget silencioso, sem prompt pro usuário."""
    print("[setup_platform] Node.js não encontrado. Instalando via winget...")
    result = _run(
        ["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS",
         "--accept-package-agreements", "--accept-source-agreements", "--silent"],
        cwd=Path("."),
    )
    if result.returncode != 0:
        print(f"[setup_platform] FALHA ao instalar Node.js: {result.stderr}")
        return False
    print("[setup_platform] Node.js instalado com sucesso.")
    return True


def build_platform() -> tuple[bool, str]:
    """Retorna (sucesso, mensagem). Nunca levanta exceção - falhas aqui
    não devem derrubar o boot da Phoenix; a Platform só fica indisponível
    até alguém corrigir (platform_process.py trata isso avisando no log
    em vez de tentar subir um server.cjs que não existe)."""
    if is_platform_built():
        return True, "Platform já compilada (dist/server.cjs encontrado), nada a fazer."

    if not PLATFORM_SOURCE.exists():
        return False, (
            f"Pasta '{PLATFORM_SOURCE}' não encontrada. Exporte o projeto do "
            f"Google AI Studio (ZIP/GitHub) e extraia para essa pasta antes de "
            f"rodar o build."
        )

    if not is_node_installed():
        if not install_node_via_winget():
            return False, "Não foi possível instalar o Node.js automaticamente."

    result = _run(["npm", "install"], cwd=PLATFORM_SOURCE)
    if result.returncode != 0:
        return False, f"'npm install' falhou: {result.stderr[-500:]}"

    result = _run(["npm", "run", "build"], cwd=PLATFORM_SOURCE)
    if result.returncode != 0:
        return False, f"'npm run build' falhou: {result.stderr[-500:]}"

    if not SERVER_ENTRY.exists():
        return False, (
            f"Build rodou, mas '{SERVER_ENTRY}' não foi gerado. Verifique o "
            f"comando de build do projeto no AI Studio - pode gerar o server "
            f"noutro caminho, e nesse caso ajuste SERVER_ENTRY neste arquivo "
            f"e PLATFORM_SOURCE/SERVER_REL_PATH em platform_process.py."
        )

    return True, "Platform compilada com sucesso (dist/server.cjs pronto)."


if __name__ == "__main__":
    ok, message = build_platform()
    print(f"[setup_platform] {'OK' if ok else 'FALHA'}: {message}")