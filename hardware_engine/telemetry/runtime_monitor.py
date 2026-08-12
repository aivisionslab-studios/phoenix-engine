"""
telemetry/runtime_monitor.py
=============================
Runtime Monitor (especificação "Hardware Telemetry Core v2.0").

Observa o que acontece com a máquina durante uma tarefa específica da
Phoenix (ex.: uma inferência de LLM, uma geração de imagem). Registra
o estado antes, durante (amostras periódicas) e depois - não decide se
o resultado foi "bom" ou "ruim", nem interpreta os números.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class RuntimeTaskRecord:
    """Contexto observado de uma tarefa: amostras de hardware coletadas
    antes de começar, durante a execução e logo após terminar. Os
    valores em si (tokens/s, tempo de carga) são Performance Monitor;
    aqui o foco é o *contexto de hardware* ao redor da tarefa."""

    task_name: str
    started_at: float
    finished_at: Optional[float] = None
    samples_during: list[dict[str, Any]] = field(default_factory=list)
    sample_before: Optional[dict[str, Any]] = None
    sample_after: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": (
                (self.finished_at - self.started_at) if self.finished_at else None
            ),
            "sample_before": self.sample_before,
            "sample_after": self.sample_after,
            "samples_during_count": len(self.samples_during),
        }


class RuntimeMonitor:
    """Acompanha o ciclo de vida de tarefas da Phoenix (ex.: uma
    inferência) e registra o contexto de hardware ao redor delas. Não
    decide se a tarefa deveria ter sido executada, nem se os números
    observados são aceitáveis - isso é Rules Engine/Decision Engine."""

    def __init__(self, sample_fn: Callable[[], dict[str, Any]]):
        """`sample_fn` é a função que retorna uma amostra factual do
        estado atual da máquina (tipicamente
        `HardwareTelemetryCore._collect_sample().to_dict()`), injetada
        por fora para não duplicar a lógica de coleta aqui."""
        self._sample_fn = sample_fn
        self._active: dict[str, RuntimeTaskRecord] = {}
        self._completed: list[RuntimeTaskRecord] = []

    def start_task(self, task_name: str) -> None:
        """Chamado pela Phoenix quando uma tarefa começa (ex.: início
        de uma inferência)."""
        record = RuntimeTaskRecord(
            task_name=task_name,
            started_at=time.time(),
            sample_before=self._sample_fn(),
        )
        self._active[task_name] = record

    def sample_during(self, task_name: str) -> None:
        """Chamado periodicamente pela Phoenix enquanto a tarefa roda,
        para capturar o comportamento do hardware em andamento (ex.:
        GPU subindo para 98% de uso)."""
        record = self._active.get(task_name)
        if record is not None:
            record.samples_during.append(self._sample_fn())

    def end_task(self, task_name: str) -> Optional[dict[str, Any]]:
        """Chamado quando a tarefa termina. Move o registro para o
        histórico de tarefas completadas e retorna o resumo factual
        (sem nenhuma conclusão sobre se foi rápido/lento/bom/ruim)."""
        record = self._active.pop(task_name, None)
        if record is None:
            return None
        record.finished_at = time.time()
        record.sample_after = self._sample_fn()
        self._completed.append(record)
        return record.to_dict()

    def get_task_history(self, task_name: Optional[str] = None) -> list[dict[str, Any]]:
        records = self._completed
        if task_name is not None:
            records = [r for r in records if r.task_name == task_name]
        return [r.to_dict() for r in records]
