import React, { useState } from 'react';
import { 
  Columns3, 
  Play, 
  Zap, 
  Bot, 
  ChevronDown, 
  Sparkles, 
  Copy, 
  Check, 
  Trophy, 
  RotateCcw,
  Clock,
  BrainCircuit
} from 'lucide-react';
import { ArenaSlot, ModelInfo, ProviderConfig } from '../types';

interface ArenaViewProps {
  availableModels: ModelInfo[];
  providers: ProviderConfig[];
  onExecuteArena: (
    slots: ArenaSlot[],
    prompt: string,
    onUpdateSlots: (updatedSlots: ArenaSlot[]) => void
  ) => Promise<void>;
  isLoading: boolean;
}

export const ArenaView: React.FC<ArenaViewProps> = ({
  availableModels,
  providers,
  onExecuteArena,
  isLoading,
}) => {
  const [promptText, setPromptText] = useState('Escreva uma função otimizada para encontrar números primos em um intervalo e analise a complexidade Big O.');
  const [copiedSlot, setCopiedSlot] = useState<string | null>(null);
  const [winnerId, setWinnerId] = useState<string | null>(null);

  const [slots, setSlots] = useState<ArenaSlot[]>([
    {
      id: 'slot-1',
      modelId: availableModels[0]?.id || 'gemini-3.6-flash',
      providerType: availableModels[0]?.providerType || 'gemini',
      providerId: availableModels[0]?.providerId || 'gemini-main',
      isLoading: false,
      currentResponse: '',
    },
    {
      id: 'slot-2',
      modelId: availableModels[1]?.id || 'deepseek-r1:8b',
      providerType: availableModels[1]?.providerType || 'ollama',
      providerId: availableModels[1]?.providerId || 'ollama-main',
      isLoading: false,
      currentResponse: '',
    },
  ]);

  const updateSlotModel = (slotId: string, modelId: string) => {
    const selectedModel = availableModels.find((m) => m.id === modelId);
    if (!selectedModel) return;

    setSlots((prev) =>
      prev.map((s) =>
        s.id === slotId
          ? {
              ...s,
              modelId: selectedModel.id,
              providerType: selectedModel.providerType,
              providerId: selectedModel.providerId,
            }
          : s
      )
    );
  };

  const addSlot = () => {
    if (slots.length >= 3) return;
    const thirdModel = availableModels[2] || availableModels[0];
    setSlots((prev) => [
      ...prev,
      {
        id: `slot-${prev.length + 1}`,
        modelId: thirdModel.id,
        providerType: thirdModel.providerType,
        providerId: thirdModel.providerId,
        isLoading: false,
        currentResponse: '',
      },
    ]);
  };

  const removeSlot = (slotId: string) => {
    if (slots.length <= 2) return;
    setSlots((prev) => prev.filter((s) => s.id !== slotId));
  };

  const handleRunArena = async () => {
    if (!promptText.trim() || isLoading) return;
    setWinnerId(null);
    await onExecuteArena(slots, promptText, (updatedSlots) => setSlots(updatedSlots));
  };

  const copyText = (text: string, slotId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSlot(slotId);
    setTimeout(() => setCopiedSlot(null), 2000);
  };

  return (
    <div id="arena-view-container" className="flex-1 flex flex-col bg-slate-950 text-slate-100 overflow-hidden">
      
      {/* Header Banner */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Columns3 className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">Arena de Comparação Lado a Lado</h2>
            <span className="text-[10px] bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full font-mono border border-amber-500/30">
              Benchmark em Tempo Real
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Compare latência, velocidade (tokens/segundo) e qualidade das respostas entre modelos locais e em nuvem simultaneamente.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {slots.length < 3 && (
            <button
              onClick={addSlot}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition-colors"
            >
              + Adicionar Modelo 3
            </button>
          )}
        </div>
      </div>

      {/* Arena Slots Grid */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className={`grid grid-cols-1 ${slots.length === 3 ? 'md:grid-cols-3' : 'md:grid-cols-2'} gap-4 h-full min-h-[400px]`}>
          {slots.map((slot, index) => {
            const modelObj = availableModels.find((m) => m.id === slot.modelId);
            const isWinner = winnerId === slot.id;

            return (
              <div
                key={slot.id}
                id={`arena-slot-card-${slot.id}`}
                className={`bg-slate-900/90 border rounded-2xl p-4 flex flex-col relative transition-all shadow-xl ${
                  isWinner
                    ? 'border-amber-500 ring-2 ring-amber-500/30 shadow-amber-500/10'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                
                {/* Slot Model Picker Header */}
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <div className="flex items-center space-x-2 flex-1 mr-2">
                    <div className="p-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-lg shrink-0">
                      <Bot className="w-4 h-4 text-indigo-400" />
                    </div>
                    
                    <select
                      value={slot.modelId}
                      onChange={(e) => updateSlotModel(slot.id, e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-white font-semibold focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      {availableModels.map((m) => (
                        <option key={m.id} value={m.id}>
                          [{m.providerType.toUpperCase()}] {m.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-center space-x-1">
                    {slots.length > 2 && (
                      <button
                        onClick={() => removeSlot(slot.id)}
                        className="p-1 text-slate-500 hover:text-rose-400 text-xs"
                        title="Remover Slot"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                </div>

                {/* Metrics Header Banner */}
                {slot.metrics && (
                  <div className="my-2 p-2 bg-slate-950/80 border border-slate-800 rounded-xl flex items-center justify-around text-[11px] font-mono">
                    <div className="flex items-center space-x-1 text-emerald-400 font-bold">
                      <Zap className="w-3.5 h-3.5" />
                      <span>{slot.metrics.tokensPerSec || 0} tok/s</span>
                    </div>
                    <div className="flex items-center space-x-1 text-slate-400">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{((slot.metrics.durationMs || 0) / 1000).toFixed(2)}s</span>
                    </div>
                    <div className="text-slate-500">
                      <span>{slot.metrics.completionTokens || 0} tok</span>
                    </div>
                  </div>
                )}

                {/* Response Content Body */}
                <div className="flex-1 overflow-y-auto my-3 text-xs leading-relaxed space-y-3 pr-1">
                  {slot.isLoading ? (
                    <div className="p-8 text-center text-slate-500 space-y-2">
                      <Zap className="w-6 h-6 text-indigo-400 animate-pulse mx-auto" />
                      <p className="font-mono text-[11px]">Gerando resposta no {slot.providerType}...</p>
                    </div>
                  ) : slot.error ? (
                    <div className="p-3 bg-rose-950/40 border border-rose-800/50 rounded-xl text-rose-300">
                      ⚠️ {slot.error}
                    </div>
                  ) : slot.currentResponse ? (
                    <>
                      {/* Thinking process if available */}
                      {slot.thinking && (
                        <div className="p-2.5 bg-purple-950/30 border border-purple-800/40 rounded-xl font-mono text-[10px] text-purple-200">
                          <div className="flex items-center space-x-1 font-semibold text-purple-400 mb-1">
                            <BrainCircuit className="w-3.5 h-3.5" />
                            <span>Raciocínio (&lt;think&gt;)</span>
                          </div>
                          <div className="line-clamp-4 hover:line-clamp-none transition-all">
                            {slot.thinking}
                          </div>
                        </div>
                      )}
                      
                      <div className="whitespace-pre-wrap font-sans text-slate-200">
                        {slot.currentResponse}
                      </div>
                    </>
                  ) : (
                    <div className="h-full flex items-center justify-center text-slate-600 text-[11px] italic">
                      Aguardando execução do benchmark...
                    </div>
                  )}
                </div>

                {/* Footer Controls & Winner Button */}
                {slot.currentResponse && !slot.isLoading && (
                  <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                    <button
                      onClick={() => setWinnerId(slot.id)}
                      className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                        isWinner
                          ? 'bg-amber-500 text-slate-950 shadow-md'
                          : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                      }`}
                    >
                      <Trophy className="w-3.5 h-3.5" />
                      <span>{isWinner ? 'Melhor Resposta!' : 'Marcar como Campeão'}</span>
                    </button>

                    <button
                      onClick={() => copyText(slot.currentResponse, slot.id)}
                      className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800"
                      title="Copiar Resposta"
                    >
                      {copiedSlot === slot.id ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                )}

              </div>
            );
          })}
        </div>
      </div>

      {/* Shared Prompt Bar */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/90">
        <div className="max-w-4xl mx-auto flex items-center space-x-3">
          <input
            type="text"
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            placeholder="Digite o prompt para comparar a execução nos modelos..."
            disabled={isLoading}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl py-3 px-4 text-xs sm:text-sm text-white focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
          />

          <button
            onClick={handleRunArena}
            disabled={!promptText.trim() || isLoading}
            className="flex items-center space-x-2 px-5 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs sm:text-sm font-bold rounded-xl shadow-lg shadow-indigo-600/30 transition-all shrink-0 cursor-pointer"
          >
            <Play className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>{isLoading ? 'Executando Arena...' : 'Executar Comparação'}</span>
          </button>
        </div>
      </div>

    </div>
  );
};
