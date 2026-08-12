import React from 'react';
import { Sliders, X, Sparkles, BookOpen, RotateCcw } from 'lucide-react';
import { ChatParameters, SystemPromptPreset } from '../types';
import { SYSTEM_PROMPT_PRESETS } from '../data/systemPrompts';

interface ParametersDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  parameters: ChatParameters;
  onChangeParameters: (updated: ChatParameters) => void;
}

export const ParametersDrawer: React.FC<ParametersDrawerProps> = ({
  isOpen,
  onClose,
  parameters,
  onChangeParameters,
}) => {
  if (!isOpen) return null;

  const handlePresetSelect = (preset: SystemPromptPreset) => {
    onChangeParameters({
      ...parameters,
      systemInstruction: preset.prompt,
    });
  };

  const handleReset = () => {
    onChangeParameters({
      temperature: 0.7,
      topP: 0.95,
      topK: 40,
      maxTokens: 4096,
      contextWindow: 16384,
      repeatPenalty: 1.1,
      systemInstruction: SYSTEM_PROMPT_PRESETS[0].prompt,
      showThinking: true,
    });
  };

  return (
    <aside id="parameters-drawer" className="w-80 border-l border-slate-800 bg-slate-900 text-slate-100 flex flex-col h-full shadow-2xl z-20 shrink-0">
      
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
        <div className="flex items-center space-x-2">
          <Sliders className="w-4 h-4 text-indigo-400" />
          <h3 className="font-bold text-sm text-white">Parâmetros do Modelo</h3>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={handleReset}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors text-xs flex items-center space-x-1"
            title="Resetar para Padrão"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Controls Container */}
      <div className="p-4 overflow-y-auto space-y-5 flex-1 text-xs">
        
        {/* System Prompt Presets */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="font-semibold text-slate-300 flex items-center space-x-1">
              <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
              <span>Instrução de Sistema (System Prompt)</span>
            </label>
          </div>

          <div className="space-y-1.5 mb-2 max-h-36 overflow-y-auto pr-1">
            {SYSTEM_PROMPT_PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => handlePresetSelect(preset)}
                className={`w-full text-left p-2 rounded-lg border text-[11px] transition-all ${
                  parameters.systemInstruction === preset.prompt
                    ? 'bg-indigo-600/20 border-indigo-500/50 text-indigo-200'
                    : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <span className="font-medium block text-slate-200">{preset.title}</span>
                <span className="text-[10px] text-slate-400 line-clamp-1">{preset.description}</span>
              </button>
            ))}
          </div>

          <textarea
            value={parameters.systemInstruction}
            onChange={(e) => onChangeParameters({ ...parameters, systemInstruction: e.target.value })}
            rows={3}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 font-sans text-xs"
            placeholder="Digite aqui as instruções do sistema..."
          />
        </div>

        {/* Temperature */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300">Temperatura</label>
            <span className="font-mono text-indigo-400 font-bold">{parameters.temperature.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="2"
            step="0.05"
            value={parameters.temperature}
            onChange={(e) => onChangeParameters({ ...parameters, temperature: parseFloat(e.target.value) })}
            className="w-full accent-indigo-500 cursor-pointer bg-slate-950 rounded-lg"
          />
          <div className="flex justify-between text-[10px] text-slate-500">
            <span>0.0 (Preciso / Lógico)</span>
            <span>1.0 (Equilibrado)</span>
            <span>2.0 (Criativo)</span>
          </div>
        </div>

        {/* Thinking Block Toggle */}
        <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl flex items-center justify-between">
          <div>
            <span className="font-semibold text-slate-200 block text-[11px]">Exibir Bloco de Raciocínio (&lt;think&gt;)</span>
            <span className="text-[10px] text-slate-400">Para modelos como DeepSeek-R1</span>
          </div>
          <input
            type="checkbox"
            checked={parameters.showThinking}
            onChange={(e) => onChangeParameters({ ...parameters, showThinking: e.target.checked })}
            className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-900 w-4 h-4 cursor-pointer"
          />
        </div>

        {/* Top-P */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300">Top P (Nucleus Sampling)</label>
            <span className="font-mono text-indigo-400 font-bold">{parameters.topP.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={parameters.topP}
            onChange={(e) => onChangeParameters({ ...parameters, topP: parseFloat(e.target.value) })}
            className="w-full accent-indigo-500 cursor-pointer bg-slate-950 rounded-lg"
          />
        </div>

        {/* Max Output Tokens */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300">Máximo de Tokens de Saída</label>
            <span className="font-mono text-indigo-400 font-bold">{parameters.maxTokens}</span>
          </div>
          <input
            type="range"
            min="256"
            max="16384"
            step="256"
            value={parameters.maxTokens}
            onChange={(e) => onChangeParameters({ ...parameters, maxTokens: parseInt(e.target.value) })}
            className="w-full accent-indigo-500 cursor-pointer bg-slate-950 rounded-lg"
          />
        </div>

        {/* Context Window Length */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300">Janela de Contexto (Tokens)</label>
            <span className="font-mono text-indigo-400 font-bold">{(parameters.contextWindow / 1024).toFixed(0)}K</span>
          </div>
          <input
            type="range"
            min="2048"
            max="131072"
            step="2048"
            value={parameters.contextWindow}
            onChange={(e) => onChangeParameters({ ...parameters, contextWindow: parseInt(e.target.value) })}
            className="w-full accent-indigo-500 cursor-pointer bg-slate-950 rounded-lg"
          />
        </div>

        {/* Repeat Penalty */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="font-semibold text-slate-300">Penalidade de Repetição</label>
            <span className="font-mono text-indigo-400 font-bold">{parameters.repeatPenalty.toFixed(2)}</span>
          </div>
          <input
            type="range"
            min="1.0"
            max="2.0"
            step="0.05"
            value={parameters.repeatPenalty}
            onChange={(e) => onChangeParameters({ ...parameters, repeatPenalty: parseFloat(e.target.value) })}
            className="w-full accent-indigo-500 cursor-pointer bg-slate-950 rounded-lg"
          />
        </div>

      </div>

    </aside>
  );
};
