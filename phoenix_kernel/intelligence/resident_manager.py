import asyncio
import logging
import importlib
import re
from datetime import datetime, timezone

from .interfaces import IResidentManager

logger = logging.getLogger(__name__)

# core.py mora em phoenix_kernel/06_telemetry/core.py. "06_telemetry" começa
# com dígito, então não dá pra fazer "from phoenix_kernel.06_telemetry import
# core" direto (SyntaxError) — daqui de dentro de outro pacote (intelligence),
# nem dá pra usar import relativo. Por isso importlib.
_hardware_core = importlib.import_module("phoenix_kernel.06_telemetry.core")

# Limites simples pra sinalizar sensor fora do normal em QUALQUER dispositivo
# (não só GPU). Primeiro corte — ajusta se gerar alerta demais/de menos.
HOT_TEMP_C = 80.0
HIGH_LOAD_PCT = 90.0


def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:60]


class ResidentManager(IResidentManager):
    def __init__(self, state_engine, planner_engine):
        self.state = state_engine
        self.planner = planner_engine

    async def analyze_machine(self) -> str:
        """Coleta specs do State, faz a leitura completa de sensores (todos
        os dispositivos ativos — CPU, GPU, placa-mãe, SSD/HDD etc., não só
        a GPU que já vinha no state), pede ao Planner (RAG) uma sugestão de
        plano, e registra qualquer sensor fora do normal como conhecimento
        novo no próprio RAG (pra Phoenix ir 'aprendendo' com o scanner)."""
        logger.info("ResidentManager: Iniciando análise de máquina...")
        state_data = await self.state.get_state()

        if "error" in state_data:
            return "Sistema ainda inicializando. Aguarde o Discovery concluir."

        hw = state_data.get("hardware", {})
        budget = state_data.get("budget", {})

        # Leitura via pythonnet/HardwareMonitor é bloqueante — roda em
        # thread separada pra não travar o event loop do FastAPI.
        loop = asyncio.get_running_loop()
        try:
            devices = await loop.run_in_executor(None, _hardware_core.get_all_hardware_sensors)
        except Exception as e:
            logger.warning(f"ResidentManager: falha ao ler sensores completos - {e}")
            devices = []

        alerts = self._check_device_alerts(devices)
        new_knowledge_count = await self._record_alerts_as_knowledge(alerts, hw)

        # A query de RAG continua baseada só em specs (gpu/vram), que é o
        # sinal que os documentos da base de fato têm de forma consistente.
        # Misturar leituras ao vivo (temp/load) direto na query prejudicaria
        # o match semântico: a busca é top-1 com threshold apertado (0.45),
        # então texto extra e ruidoso tende a derrubar a similaridade em vez
        # de ajudar. Os sensores completos entram no relatório à parte — e
        # agora também viram conhecimento novo no RAG (ver abaixo), não só
        # texto solto no relatório.
        query = f"Melhor configuração LLM para {hw.get('gpu', 'CPU')} com {hw.get('vram_mb', 0)}MB VRAM"
        recommendation = await self.planner.knowledge.query_knowledge(query)

        report = "🔍 PHOENIX RESIDENT MANAGER - ANÁLISE DE HARDWARE 🔍\n\n"
        report += f"CPU: {hw.get('cpu', 'N/A')}\n"
        report += f"RAM: {hw.get('ram_mb', 0)} MB\n"
        report += f"GPU: {hw.get('gpu', 'N/A')} ({hw.get('vram_mb', 0)} MB VRAM)\n"
        report += f"Backends: {', '.join(hw.get('backends', []))}\n"
        report += f"Classe da Máquina: {budget.get('class', 'Unknown')} (Score: {budget.get('score', 0)}%)\n\n"

        report += f"📡 SCANNER COMPLETO: {len(devices)} dispositivo(s) ativo(s) lido(s)\n"
        if alerts:
            report += "⚠️ ALERTAS DE SENSOR:\n"
            for a in alerts:
                report += f"- {a['device']} / {a['sensor_name']}: {a['value']:.0f}{a['unit']} (acima de {a['threshold']:.0f}{a['unit']})\n"
        else:
            report += "Nenhum sensor fora da faixa normal no momento.\n"
        if new_knowledge_count:
            report += f"🧠 {new_knowledge_count} novo(s) registro(s) adicionado(s) ao RAG a partir dessa leitura.\n"
        report += "\n"

        report += "💡 SUGESTÃO DE PLANO (Baseado no histórico RAG):\n"
        if recommendation:
            report += "Baseado em testes anteriores, recomenda-se:\n"
            report += f"- {recommendation.get('name', 'N/A')}\n"
            report += f"- Notas: {recommendation.get('notes', 'N/A')}\n"
        else:
            report += "Nenhuma recomendação histórica exata encontrada. Plano padrão: Instalar Ollama e OpenWebUI.\n"

        report += "\n⚠️ Nenhuma ação de execução foi tomada. A Phoenix apenas pensou."
        return report

    @staticmethod
    def _check_device_alerts(devices: list) -> list:
        """Varre todos os dispositivos/sensores e sinaliza o que está acima
        dos limites de temperatura/load. Retorna dados estruturados (não só
        texto) porque tanto o relatório quanto o registro no RAG precisam
        dos campos separados."""
        alerts = []
        for dev in devices:
            for s in dev.get("sensors", []):
                if s["type"] == "Temperature" and s["value"] >= HOT_TEMP_C:
                    alerts.append({
                        "device": dev["name"], "sensor_name": s["name"], "sensor_type": s["type"],
                        "value": s["value"], "unit": "°C", "threshold": HOT_TEMP_C,
                    })
                elif s["type"] == "Load" and s["value"] >= HIGH_LOAD_PCT:
                    alerts.append({
                        "device": dev["name"], "sensor_name": s["name"], "sensor_type": s["type"],
                        "value": s["value"], "unit": "%", "threshold": HIGH_LOAD_PCT,
                    })
        return alerts

    async def _record_alerts_as_knowledge(self, alerts: list, hw: dict) -> int:
        """Pra cada alerta, registra (uma vez só — id determinístico por
        dispositivo+sensor, checado via has_document) um documento novo na
        categoria 'telemetry_event' do RAG. Passa pelo KnowledgeEngine, que
        usa o MESMO _build_doc_text do sync do knowledge_base.json — ou
        seja, isso vira embedding como frase natural, no mesmo padrão de
        qualquer outro documento da base, nunca texto cru."""
        created = 0
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        for alert in alerts:
            doc_id = f"telemetry_{_slugify(alert['device'])}_{_slugify(alert['sensor_name'])}"
            try:
                if await self.planner.knowledge.has_document(doc_id):
                    continue

                doc = {
                    "id": doc_id,
                    "category": "telemetry_event",
                    "title": f"{alert['device']} / {alert['sensor_name']} acima do normal",
                    "device": alert["device"],
                    "sensor_name": alert["sensor_name"],
                    "sensor_type": alert["sensor_type"],
                    "value": alert["value"],
                    "unit": alert["unit"],
                    "threshold": alert["threshold"],
                    "hardware_gpu": hw.get("gpu", ""),
                    "first_observed": now_iso,
                    "notes": "Gerado automaticamente pelo loop do ResidentManager a partir do scanner completo de sensores.",
                }
                if await self.planner.knowledge.add_document(doc):
                    created += 1
            except Exception as e:
                logger.warning(f"ResidentManager: falha ao registrar conhecimento pro alerta '{doc_id}': {e}")

        return created
