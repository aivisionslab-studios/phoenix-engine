import React, { useState } from 'react';
import { 
  X, 
  Check, 
  RefreshCw, 
  Server, 
  Key, 
  Globe, 
  Terminal, 
  Cpu, 
  ExternalLink,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Zap,
  AudioWaveform
} from 'lucide-react';
import { ProviderConfig, ProviderType } from '../types';

interface ProviderSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  providers: ProviderConfig[];
  onUpdateProvider: (updated: ProviderConfig) => void;
  onTestProvider: (providerId: string) => Promise<void>;
  hasGeminiKey: boolean;
}

export const ProviderSettingsModal: React.FC<ProviderSettingsModalProps> = ({
  isOpen,
  onClose,
  providers,
  onUpdateProvider,
  onTestProvider,
  hasGeminiKey,
}) => {
  const [testingId, setTestingId] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleTest = async (providerId: string) => {
    setTestingId(providerId);
    await onTestProvider(providerId);
    setTestingId(null);
  };

  const getProviderIcon = (type: ProviderType) => {
    switch (type) {
      case 'ollama':
        return <Terminal className="w-5 h-5 text-amber-400" />;
      case 'lmstudio':
        return <Cpu className="w-5 h-5 text-cyan-400" />;
      case 'gemini':
        return <Sparkles className="w-5 h-5 text-purple-400" />;
      case 'llama-server':
        return <Cpu className="w-5 h-5 text-emerald-400" />;
      case 'vllm':
        return <Zap className="w-5 h-5 text-blue-400" />;
      case 'localai':
        return <Server className="w-5 h-5 text-indigo-400" />;
      case 'koboldcpp':
        return <Terminal className="w-5 h-5 text-rose-400" />;
      case 'tgi':
        return <Globe className="w-5 h-5 text-amber-500" />;
      case 'jan':
        return <Cpu className="w-5 h-5 text-teal-400" />;
      case 'sglang':
        return <Zap className="w-5 h-5 text-cyan-300" />;
      case 'open-webui':
        return <Globe className="w-5 h-5 text-purple-300" />;
      case 'anythingllm':
        return <Server className="w-5 h-5 text-blue-300" />;
      case 'openai':
        return <Globe className="w-5 h-5 text-emerald-400" />;
      case 'anthropic':
        return <Server className="w-5 h-5 text-indigo-400" />;
      case 'piper-tts':
        return <AudioWaveform className="w-5 h-5 text-indigo-400" />;
      default:
        return <Globe className="w-5 h-5 text-slate-400" />;
    }
  };

  return (
    <div id="provider-settings-modal" className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
              <Server className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Provedores de LLM & Endpoints</h2>
              <p className="text-xs text-slate-400">
                Gerencie conexões locais (Ollama, LM Studio) e APIs de nuvem (Gemini, OpenAI, Custom)
              </p>
            </div>
          </div>
          <button
            id="close-settings-modal-btn"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          
          {/* Quick Notice Banner */}
          <div className="bg-indigo-950/40 border border-indigo-800/50 rounded-xl p-4 flex items-start space-x-3 text-xs text-indigo-200">
            <Sparkles className="w-4 h-4 text-indigo-400 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold text-indigo-100 mb-0.5">Suporte a Servidores Locais & CORS Proxy</p>
              <p className="text-indigo-300/80 leading-relaxed">
                Nossa plataforma executa verificações de ping no lado do servidor para acessar diretamente suas instâncias locais do <strong>Ollama</strong> (<code className="bg-slate-900 px-1 py-0.5 rounded text-amber-300">http://localhost:11434</code>) e <strong>LM Studio</strong> (<code className="bg-slate-900 px-1 py-0.5 rounded text-cyan-300">http://localhost:1234/v1</code>) sem problemas de CORS no navegador.
              </p>
            </div>
          </div>

          {/* Providers List */}
          <div className="space-y-4">
            {providers.map((p) => (
              <div
                key={p.id}
                id={`provider-card-${p.id}`}
                className={`border rounded-xl p-4 transition-all ${
                  p.enabled
                    ? 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                    : 'bg-slate-950/30 border-slate-800/50 opacity-60'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  
                  {/* Left Title & Status */}
                  <div className="flex items-center space-x-3">
                    <div className="p-2 rounded-xl bg-slate-900 border border-slate-800">
                      {getProviderIcon(p.type)}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="font-semibold text-sm text-white">{p.name}</h3>
                        {p.status === 'connected' && (
                          <span className="flex items-center space-x-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Conectado ({p.latencyMs || 0}ms)</span>
                          </span>
                        )}
                        {p.status === 'disconnected' && (
                          <span className="flex items-center space-x-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                            <XCircle className="w-3 h-3" />
                            <span>Offline / Não Encontrado</span>
                          </span>
                        )}
                        {p.status === 'error' && (
                          <span className="flex items-center space-x-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                            <AlertCircle className="w-3 h-3" />
                            <span>Erro de Conexão</span>
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {p.models.length > 0 
                          ? `${p.models.length} modelos detectados (${p.models.slice(0, 3).join(', ')}${p.models.length > 3 ? '...' : ''})`
                          : 'Nenhum modelo carregado'}
                      </p>
                    </div>
                  </div>

                  {/* Right Action Controls */}
                  <div className="flex items-center space-x-3 self-end md:self-center">
                    
                    {/* Enable Toggle */}
                    <label className="flex items-center space-x-2 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={p.enabled}
                        onChange={(e) => onUpdateProvider({ ...p, enabled: e.target.checked })}
                        className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-900 w-4 h-4 cursor-pointer"
                      />
                      <span>Ativo</span>
                    </label>

                    {/* Test Ping Button */}
                    <button
                      id={`test-provider-${p.id}-btn`}
                      onClick={() => handleTest(p.id)}
                      disabled={!p.enabled || testingId === p.id}
                      className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition-colors disabled:opacity-40"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${testingId === p.id ? 'animate-spin text-indigo-400' : ''}`} />
                      <span>{testingId === p.id ? 'Testando...' : 'Testar Ping'}</span>
                    </button>
                  </div>

                </div>

                {/* Configuration Inputs */}
                {p.enabled && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80 grid grid-cols-1 md:grid-cols-2 gap-3">
                    
                    {/* Base URL Input */}
                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1">
                        URL Base do Endpoint
                      </label>
                      <input
                        type="text"
                        value={p.baseUrl}
                        onChange={(e) => onUpdateProvider({ ...p, baseUrl: e.target.value })}
                        disabled={p.type === 'gemini'}
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 font-mono"
                        placeholder={p.type === 'ollama' ? 'http://localhost:11434' : 'http://localhost:1234/v1'}
                      />
                    </div>

                    {/* API Key Input (if applicable) */}
                    <div>
                      <label className="block text-[11px] font-medium text-slate-400 mb-1">
                        {p.type === 'gemini' ? 'Chave Gemini (Injetada automaticamente)' : 'Chave API (Opcional para locais)'}
                      </label>
                      {p.type === 'gemini' ? (
                        <div className="flex items-center justify-between bg-purple-950/30 border border-purple-800/40 rounded-lg px-3 py-1.5 text-xs text-purple-300 font-mono">
                          <span>{hasGeminiKey ? '••••••••••••••••' : 'Configurada via Secrets do AI Studio'}</span>
                          <Check className="w-3 h-3 text-purple-400" />
                        </div>
                      ) : (
                        <input
                          type="password"
                          value={p.apiKey || ''}
                          onChange={(e) => onUpdateProvider({ ...p, apiKey: e.target.value })}
                          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 font-mono"
                          placeholder="sk-..."
                        />
                      )}
                    </div>

                  </div>
                )}

              </div>
            ))}
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            Dica: Para o Ollama, certifique-se de executar <code className="bg-slate-900 text-amber-300 px-1 rounded">OLLAMA_ORIGINS="*" ollama serve</code> se acessar via rede.
          </p>
          <button
            id="save-settings-btn"
            onClick={onClose}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/30 transition-all"
          >
            Concluído
          </button>
        </div>

      </div>
    </div>
  );
};
