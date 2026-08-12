"""
events.py
=========
Compara o estado anterior com o estado atual e produz uma lista de
eventos factuais (algo apareceu / desapareceu / mudou de status).
Isto NÃO é uma decisão — é só constatação de diferença. Interpretar
o que essa diferença significa é responsabilidade das Engines
(Phoenix, AI Doctor), nunca da Telemetria.
"""

from __future__ import annotations

from typing import Any, Optional


def _names(items: list[dict[str, Any]], key: str) -> set[str]:
    return {i.get(key) for i in items if i.get(key) is not None}


def diff_ai_environment(previous: Optional[list[dict[str, Any]]],
                         current: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if previous is None:
        return []
    prev_names = _names(previous, "name")
    curr_names = _names(current, "name")
    events = []
    for added in curr_names - prev_names:
        events.append({"category": "ai_environment", "event_type": "tool_detected",
                        "message": f"Ferramenta de IA detectada: {added}",
                        "payload": {"name": added}})
    for removed in prev_names - curr_names:
        events.append({"category": "ai_environment", "event_type": "tool_no_longer_detected",
                        "message": f"Ferramenta de IA não detectada mais: {removed}",
                        "payload": {"name": removed}})
    return events


def diff_models(previous_paths: set[str], current: list[dict[str, Any]]) -> list[dict[str, Any]]:
    curr_paths = {m["path"] for m in current}
    events = []
    for added in curr_paths - previous_paths:
        events.append({"category": "models", "event_type": "model_added",
                        "message": f"Modelo detectado em disco: {added}",
                        "payload": {"path": added}})
    for removed in previous_paths - curr_paths:
        events.append({"category": "models", "event_type": "model_removed",
                        "message": f"Modelo não encontrado mais: {removed}",
                        "payload": {"path": removed}})
    return events


def diff_inventory(previous: Optional[list[dict[str, Any]]],
                    current: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if previous is None:
        return []
    prev_names = _names(previous, "name")
    curr_names = _names(current, "name")
    events = []
    for added in curr_names - prev_names:
        events.append({"category": "inventory", "event_type": "program_installed",
                        "message": f"Programa detectado: {added}",
                        "payload": {"name": added}})
    for removed in prev_names - curr_names:
        events.append({"category": "inventory", "event_type": "program_removed",
                        "message": f"Programa não detectado mais: {removed}",
                        "payload": {"name": removed}})
    return events


def diff_services(previous: Optional[dict[str, Any]], current: dict[str, Any]) -> list[dict[str, Any]]:
    if previous is None:
        return []
    prev_containers = {c.get("Names") for c in previous.get("docker_containers", [])}
    curr_containers = {c.get("Names") for c in current.get("docker_containers", [])}
    events = []
    for added in curr_containers - prev_containers:
        if added:
            events.append({"category": "services", "event_type": "container_started",
                            "message": f"Container Docker observado: {added}",
                            "payload": {"name": added}})
    for removed in prev_containers - curr_containers:
        if removed:
            events.append({"category": "services", "event_type": "container_stopped",
                            "message": f"Container Docker não observado mais: {removed}",
                            "payload": {"name": removed}})
    return events
