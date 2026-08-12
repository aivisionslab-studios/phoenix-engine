import React from 'react';
import { 
  Bot, 
  Columns3, 
  Download, 
  Cpu, 
  Settings, 
  Zap, 
  CheckCircle2, 
  XCircle, 
  Activity,
  Sliders,
  Sparkles,
  Layers,
  BookOpen
} from 'lucide-react';
import { ProviderConfig } from '../types';

interface HeaderProps {
  activeTab: 'chat' | 'arena' | 'hub' | 'vram' | 'stack' | 'settings';
  setActiveTab: (tab: 'chat' | 'arena' | 'hub' | 'vram' | 'stack' | 'settings') => void;
  providers: ProviderConfig[];
  onOpenSettings: () => void;
  onToggleParameters: () => void;
  onOpenManual?: () => void;
  hasGeminiKey: boolean;
  engineOnline?: boolean;
  telemetry?: {
    gpuTempC?: number;
    vramUsedGb?: number;
    vramTotalGb?: number;
    cpuLoadPct?: number;
  };
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  providers,
  onOpenSettings,
  onToggleParameters,
  onOpenManual,
  hasGeminiKey,
  engineOnline = false,
  telemetry,
}) => {
  const activeProvidersCount = providers.filter((p) => p.enabled && p.status === 'connected').length;
  const totalEnabled = providers.filter((p) => p.enabled).length;

  return (
    <header id="main-header" className="bg-slate-900 border-b border-slate-800 text-slate-100 sticky top-0 z-30 shadow-md">
      <div className="w-full px-3 sm:px-5 lg:px-6">
        <div className="flex items-center justify-between h-16 gap-3">
          
          {/* Left Container: Logo & Brand + Navigation Tabs */}
          <div className="flex items-center space-x-3 lg:space-x-5 min-w-0">
            {/* Logo & Brand */}
            <div className="flex items-center space-x-2.5 cursor-pointer shrink-0" onClick={() => setActiveTab('chat')}>
              {/* Brazilian Flag Badge */}
              <div className="flex items-center space-x-1 px-1.5 py-1 rounded-lg bg-emerald-950/40 border border-emerald-500/30 shadow-sm shrink-0" title="Phoenix Aviary Engine (Brasil) - Soberania & Local AI Stack">
                <svg viewBox="0 0 720 504" className="w-5 h-3.5 rounded-[2px] shrink-0 shadow-sm">
                  <rect width="720" height="504" fill="#009b3a"/>
                  <polygon points="360,42 678,252 360,462 42,252" fill="#fedf00"/>
                  <circle cx="360" cy="252" r="126" fill="#002776"/>
                  <path d="M 238,272 A 150,150 0 0,1 482,232" fill="none" stroke="#ffffff" strokeWidth="14"/>
                </svg>
                <span className="text-[10px] font-extrabold text-emerald-400 font-mono tracking-wider">BR</span>
              </div>

              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-cyan-500 p-0.5 flex items-center justify-center shadow-lg shadow-indigo-500/20 shrink-0">
                <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                  <Bot className="w-5 h-5 text-indigo-400" />
                </div>
              </div>
              <div className="shrink-0">
                <div className="flex items-center space-x-1.5">
                  <span className="font-bold text-base sm:text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-200 bg-clip-text text-transparent whitespace-nowrap">
                    Phoenix Aviary
                  </span>
                  <span className="text-[9px] sm:text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 whitespace-nowrap hidden sm:inline-block">
                    Platform
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 hidden md:block whitespace-nowrap">
                  AIVisionsLab Studio Group
                </p>
              </div>
            </div>

            {/* Navigation Tabs Shifted Left */}
            <nav id="header-nav-tabs" className="flex items-center space-x-1 bg-slate-950/70 p-1 rounded-xl border border-slate-800/80 shrink-0 whitespace-nowrap overflow-x-auto max-w-full">
              <button
                id="tab-chat-btn"
                onClick={() => setActiveTab('chat')}
                className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                  activeTab === 'chat'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Bot className="w-4 h-4" />
                <span className="hidden sm:inline">Chat WebUI</span>
              </button>

              <button
                id="tab-arena-btn"
                onClick={() => setActiveTab('arena')}
                className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                  activeTab === 'arena'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Columns3 className="w-4 h-4" />
                <span className="hidden sm:inline">Model Arena</span>
                <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1 py-0.5 rounded border border-amber-500/30 font-mono hidden md:inline">
                  Compare
                </span>
              </button>

              <button
                id="tab-hub-btn"
                onClick={() => setActiveTab('hub')}
                className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                  activeTab === 'hub'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Download className="w-4 h-4" />
                <span className="hidden sm:inline">Model Hub</span>
              </button>

              <button
                id="tab-vram-btn"
                onClick={() => setActiveTab('vram')}
                className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                  activeTab === 'vram'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Cpu className="w-4 h-4" />
                <span className="hidden sm:inline">Hardware & VRAM</span>
              </button>

              <button
                id="tab-stack-btn"
                onClick={() => setActiveTab('stack')}
                className={`flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                  activeTab === 'stack'
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Layers className="w-4 h-4" />
                <span className="hidden sm:inline">Stack & Ecossistema</span>
              </button>
            </nav>
          </div>

          {/* Right Action Tools & Telemetry */}
          <div className="flex items-center space-x-2 shrink-0">
            
            {/* Phoenix Engine Status Badge & Live Telemetry */}
            <div className="flex items-center space-x-1.5">
              <div
                className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-[10px] font-mono border font-semibold ${
                  engineOnline
                    ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                    : 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                }`}
                title={engineOnline ? "Phoenix Engine ativo em http://localhost:8000 (polling contínuo a cada 4s)" : "Phoenix Engine desconectado ou inicializando na porta 8000"}
              >
                <Zap className={`w-3 h-3 ${engineOnline ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
                <span>Engine: {engineOnline ? '8000 [ON]' : '8000 [STANDBY]'}</span>
              </div>

              {engineOnline && telemetry && (
                <div className="hidden md:flex items-center space-x-1.5 text-[10px] font-mono">
                  {typeof telemetry.gpuTempC === 'number' && !Number.isNaN(telemetry.gpuTempC) && (
                    <span className="px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/80 text-amber-300 flex items-center gap-1" title="Temperatura GPU">
                      🔥 {telemetry.gpuTempC.toFixed(0)}°C
                    </span>
                  )}
                  {(typeof telemetry.vramUsedGb === 'number' || typeof telemetry.vramTotalGb === 'number') && (
                    <span className="px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/80 text-cyan-300 flex items-center gap-1" title="Uso de VRAM">
                      <Cpu className="w-2.5 h-2.5" />
                      VRAM: {typeof telemetry.vramUsedGb === 'number' ? telemetry.vramUsedGb.toFixed(1) : "?"}/{typeof telemetry.vramTotalGb === 'number' ? telemetry.vramTotalGb.toFixed(1) : "?"} GB
                    </span>
                  )}
                  {typeof telemetry.cpuLoadPct === 'number' && !Number.isNaN(telemetry.cpuLoadPct) && (
                    <span className="px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/80 text-indigo-300 flex items-center gap-1" title="Carga de CPU">
                      <Activity className="w-2.5 h-2.5" />
                      CPU: {telemetry.cpuLoadPct.toFixed(0)}%
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Parameters Quick Drawer Toggle */}
            {activeTab === 'chat' && (
              <button
                id="toggle-params-btn"
                onClick={onToggleParameters}
                className="p-2 rounded-lg text-slate-400 hover:text-indigo-300 hover:bg-slate-800 transition-colors border border-slate-800 relative"
                title="Ajustar Parâmetros de Temperatura e Sistema"
              >
                <Sliders className="w-4 h-4" />
              </button>
            )}

            {/* Provider Status Pill */}
            <button
              id="provider-status-badge"
              onClick={onOpenSettings}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-800 border border-slate-700/80 text-xs text-slate-300 transition-all cursor-pointer"
            >
              <Activity className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
              <span className="hidden sm:inline font-mono text-[11px]">
                {activeProvidersCount}/{totalEnabled} Provedores On
              </span>
              <div className="flex items-center space-x-1">
                {activeProvidersCount > 0 ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <XCircle className="w-3.5 h-3.5 text-amber-400" />
                )}
              </div>
            </button>

            {/* Manual & Documentation Button */}
            {onOpenManual && (
              <button
                id="open-manual-btn"
                onClick={onOpenManual}
                className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-indigo-950/60 hover:bg-indigo-900/60 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition-all cursor-pointer"
                title="Abrir Manual & Documentação Técnica Completa (PT-BR / EN-US)"
              >
                <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                <span className="hidden lg:inline">Manual</span>
              </button>
            )}

            {/* Settings Modal Button */}
            <button
              id="open-settings-modal-btn"
              onClick={onOpenSettings}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors border border-slate-800"
              title="Configurar Provedores de LLM"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>

        </div>
      </div>
    </header>
  );
};
