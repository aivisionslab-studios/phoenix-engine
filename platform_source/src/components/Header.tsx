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
  Layers
} from 'lucide-react';
import { ProviderConfig } from '../types';

interface HeaderProps {
  activeTab: 'chat' | 'arena' | 'hub' | 'vram' | 'stack' | 'settings';
  setActiveTab: (tab: 'chat' | 'arena' | 'hub' | 'vram' | 'stack' | 'settings') => void;
  providers: ProviderConfig[];
  onOpenSettings: () => void;
  onToggleParameters: () => void;
  hasGeminiKey: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  providers,
  onOpenSettings,
  onToggleParameters,
  hasGeminiKey,
}) => {
  const activeProvidersCount = providers.filter((p) => p.enabled && p.status === 'connected').length;
  const totalEnabled = providers.filter((p) => p.enabled).length;

  return (
    <header id="main-header" className="bg-slate-900 border-b border-slate-800 text-slate-100 sticky top-0 z-30 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('chat')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-cyan-500 p-0.5 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Bot className="w-6 h-6 text-indigo-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-indigo-200 bg-clip-text text-transparent whitespace-nowrap">
                  Phoenix Aviary
                </span>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 whitespace-nowrap">
                  Platform
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block whitespace-nowrap">
                AIVisionsLab Studio Group
              </p>
            </div>
          </div>

          {/* Center Navigation Tabs */}
          <nav id="header-nav-tabs" className="flex items-center space-x-1 sm:space-x-2 bg-slate-950/70 p-1 rounded-xl border border-slate-800/80 flex-shrink-0 whitespace-nowrap overflow-x-auto">
            <button
              id="tab-chat-btn"
              onClick={() => setActiveTab('chat')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'chat'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Bot className="w-4 h-4" />
              <span className="hidden md:inline">Chat WebUI</span>
            </button>

            <button
              id="tab-arena-btn"
              onClick={() => setActiveTab('arena')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'arena'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Columns3 className="w-4 h-4" />
              <span className="hidden md:inline">Model Arena</span>
              <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded border border-amber-500/30 font-mono hidden sm:inline">
                Compare
              </span>
            </button>

            <button
              id="tab-hub-btn"
              onClick={() => setActiveTab('hub')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'hub'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Download className="w-4 h-4" />
              <span className="hidden md:inline">Model Hub</span>
            </button>

            <button
              id="tab-vram-btn"
              onClick={() => setActiveTab('vram')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'vram'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Cpu className="w-4 h-4" />
              <span className="hidden md:inline">Hardware & VRAM</span>
            </button>

            <button
              id="tab-stack-btn"
              onClick={() => setActiveTab('stack')}
              className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                activeTab === 'stack'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span className="hidden md:inline">Stack & Ecossistema</span>
            </button>
          </nav>

          {/* Right Action Tools & Provider Badges */}
          <div className="flex items-center space-x-2">
            
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
