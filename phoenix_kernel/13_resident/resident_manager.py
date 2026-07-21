    async def analyze_machine(self) -> str:
        """Primeiro teste: coleta dados do State e pede ao Planner para sugerir um plano."""
        state_data = await self.state.get_state()
        
        if "error" in state_data:
            return "Sistema ainda inicializando. Aguarde o Discovery concluir."
            
        hw = state_data.get("hardware", {})
        budget = state_data.get("budget", {})
        
        # Pede ao Planner (RAG) para sugerir um plano baseado no hardware
        query = f"Melhor configuração LLM para {hw.get('gpu', 'CPU')} com {hw.get('vram_mb', 0)}MB VRAM"
        recommendation = await self.planner.knowledge.query_knowledge(query)
        
        report = f"🔍 PHOENIX RESIDENT MANAGER - ANÁLISE DE HARDWARE 🔍\n\n"
        report += f"CPU: {hw.get('cpu', 'N/A')}\n"
        report += f"RAM: {hw.get('ram_mb', 0)} MB\n"
        report += f"GPU: {hw.get('gpu', 'N/A')} ({hw.get('vram_mb', 0)} MB VRAM)\n"
        report += f"Backends: {', '.join(hw.get('backends', []))}\n"
        report += f"Classe da Máquina: {budget.get('class', 'Unknown')} (Score: {budget.get('score', 0)}%)\n\n"
        
        report += "💡 SUGESTÃO DE PLANO (Baseado no histórico RAG):\n"
        if recommendation:
            report += f"Baseado em testes anteriores, recomenda-se:\n"
            report += f"- {recommendation.get('name', 'N/A')}\n"
            report += f"- Notas: {recommendation.get('notes', 'N/A')}\n"
        else:
            report += "Nenhuma recomendação histórica exata encontrada. Plano padrão: Instalar Ollama e OpenWebUI.\n"
            
        report += "\n⚠️ Nenhuma ação de execução foi tomada. A Phoenix apenas pensou."
        return report