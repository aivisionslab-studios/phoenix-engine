import React, { useState, useEffect } from 'react';
import { BookOpen, Globe, Download, CheckCircle2, ArrowRight, ExternalLink, ShieldCheck, Cpu, Volume2, HardDrive } from 'lucide-react';

export const ManualModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  const [lang, setLang] = useState<'pt' | 'en'>('pt');
  const [manualText, setManualText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetch('/MANUAL.md')
      .then((res) => (res.ok ? res.text() : 'Manual em carregamento...'))
      .then((text) => setManualText(text))
      .catch(() => setManualText('Falha ao carregar o arquivo MANUAL.md'))
      .finally(() => setLoading(false));
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        
        {/* Header Modal */}
        <div className="p-4 sm:p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                <span>Manual & Documentação Técnica</span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  v3.0
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Phoenix Aviary Platform & Phoenix Engine | Português (BR) & English (US)
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* Language Selector */}
            <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-mono">
              <button
                onClick={() => setLang('pt')}
                className={`px-3 py-1 rounded-lg font-bold transition-all ${
                  lang === 'pt' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                🇧🇷 PT-BR
              </button>
              <button
                onClick={() => setLang('en')}
                className={`px-3 py-1 rounded-lg font-bold transition-all ${
                  lang === 'en' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                🇺🇸 EN-US
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="p-5 overflow-y-auto space-y-6 text-slate-200 text-sm leading-relaxed font-sans">
          
          {/* Quick Direct Actions Box */}
          <div className="bg-gradient-to-r from-amber-950/40 via-slate-900 to-indigo-950/40 border border-amber-500/30 rounded-xl p-4 space-y-3">
            <div className="flex items-center space-x-2">
              <Volume2 className="w-5 h-5 text-amber-400" />
              <h3 className="font-bold text-amber-300 text-sm">
                {lang === 'pt' ? 'Solução Rápida do Erro de Voz Piper TTS (eSpeak-NG no Windows)' : 'Quick Fix for Piper TTS Voice Error (eSpeak-NG on Windows)'}
              </h3>
            </div>
            <p className="text-xs text-slate-300">
              {lang === 'pt'
                ? 'Se o Piper TTS apresentar erro ao sintetizar voz no Windows por falta da pasta espeak-ng-data, baixe e instale o pacote oficial de 64 bits:'
                : 'If Piper TTS returns an error due to missing espeak-ng-data on Windows, download and run the official 64-bit installer:'}
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              <a
                href="https://github.com/espeak-ng/espeak-ng/releases/download/1.51/espeak-ng-X64.msi"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-2 px-3.5 py-1.5 bg-amber-600/30 hover:bg-amber-600/50 text-amber-200 border border-amber-500/40 rounded-lg text-xs font-semibold transition-all"
              >
                <span>{lang === 'pt' ? 'Baixar Instalador eSpeak-NG (MSI)' : 'Download eSpeak-NG Installer (MSI)'}</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
              <a
                href="https://github.com/espeak-ng/espeak-ng/releases"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-700 rounded-lg text-xs transition-all"
              >
                <span>{lang === 'pt' ? 'Releases eSpeak-NG GitHub' : 'GitHub eSpeak-NG Releases'}</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* Render Manual Content by Selected Language */}
          {lang === 'pt' ? (
            <div className="space-y-5">
              <section className="space-y-2">
                <h3 className="text-lg font-bold text-indigo-300 border-b border-slate-800 pb-1 flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-indigo-400" />
                  1. Visão Geral da Plataforma
                </h3>
                <p>
                  A <strong>Phoenix Aviary Platform v3.0</strong> e o <strong>Phoenix Engine 5.0</strong> integram orquestração de Inteligência Artificial Local e Nuvem. O projeto oferece suporte completo a provedores de LLM, visão computacional e síntese de voz neural.
                </p>
              </section>

              <section className="space-y-2">
                <h3 className="text-lg font-bold text-indigo-300 border-b border-slate-800 pb-1 flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-indigo-400" />
                  2. Arquitetura de Comunicação
                </h3>
                <div className="bg-slate-950 p-4 rounded-xl font-mono text-xs text-slate-300 space-y-1 border border-slate-800">
                  <p className="text-indigo-400">● Frontend (React 19 / Vite): http://localhost:3000</p>
                  <p className="text-emerald-400">● Servidor Node.js Proxy (server.ts): http://localhost:3000</p>
                  <p className="text-cyan-400">● Phoenix Python Engine Core (api_server.py): http://localhost:8000</p>
                  <p className="text-amber-400">● Servidor LLM Nativo (llama-server / Vulkan): http://localhost:8081</p>
                  <p className="text-purple-400">● Ollama Local Engine: http://localhost:11434</p>
                </div>
              </section>

              <section className="space-y-2">
                <h3 className="text-lg font-bold text-indigo-300 border-b border-slate-800 pb-1 flex items-center gap-2">
                  <HardDrive className="w-5 h-5 text-indigo-400" />
                  3. Estrutura de Pastas e Modelos
                </h3>
                <p>
                  Os modelos recomendados residem em unidade NVMe de alta velocidade:
                </p>
                <ul className="list-disc list-inside space-y-1 font-mono text-xs text-slate-300 pl-2">
                  <li><code className="text-amber-300">R:\Phoenix\Workstations\Models\Chat\GGUF\</code> — Arquivos de LLM GGUF.</li>
                  <li><code className="text-amber-300">R:\Phoenix\Workstations\Models\Vision\</code> — Modelos multimodais de visão.</li>
                  <li><code className="text-amber-300">R:\Phoenix\Workstations\Models\Voice\Piper\</code> — Vozes neurais ONNX e dados do eSpeak-NG.</li>
                </ul>
              </section>

              <section className="space-y-2">
                <h3 className="text-lg font-bold text-indigo-300 border-b border-slate-800 pb-1 flex items-center gap-2">
                  <Volume2 className="w-5 h-5 text-indigo-400" />
                  4. Guia Detalhado do Piper TTS & eSpeak-NG
                </h3>
                <p>
                  O Piper gera voz neural a partir de modelos ONNX. No Windows, ele necessita do diretório de fonemas <code className="text-amber-300 font-mono">espeak-ng-data</code> na pasta do Piper ou instalado no sistema.
                </p>
                <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 text-xs space-y-1">
                  <p className="font-bold text-slate-200">Fallback Automático:</p>
                  <p className="text-slate-400">
                    Se o Phoenix Engine estiver indisponível ou o eSpeak-NG não estiver instalado, a plataforma utiliza automaticamente a síntese nativa do navegador (Web Speech API) garantindo leitura perfeita de mensagens.
                  </p>
                </div>
              </section>
            </div>
          ) : (
            <div className="space-y-5">
              <section className="space-y-2">
                <h3 className="text-lg font-bold text-indigo-300 border-b border-slate-800 pb-1 flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-indigo-400" />
                  1. Platform Overview
                </h3>
                <p>
                  <strong>Phoenix Aviary Platform v3.0</strong> and <strong>Phoenix Engine 5.0</strong> deliver unified orchestration for Local and Cloud AI models, vision capabilities, and neural voice synthesis.
                </p>
              </section>

              <section className="space-y-2">
                <h3 className="text-lg font-bold text-indigo-300 border-b border-slate-800 pb-1 flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-indigo-400" />
                  2. Network & Engine Stack
                </h3>
                <div className="bg-slate-950 p-4 rounded-xl font-mono text-xs text-slate-300 space-y-1 border border-slate-800">
                  <p className="text-indigo-400">● Frontend (React 19 / Vite): http://localhost:3000</p>
                  <p className="text-emerald-400">● Node.js Server Proxy (server.ts): http://localhost:3000</p>
                  <p className="text-cyan-400">● Phoenix Python Engine Core (api_server.py): http://localhost:8000</p>
                  <p className="text-amber-400">● llama-server Native Engine (Vulkan): http://localhost:8081</p>
                  <p className="text-purple-400">● Ollama Engine: http://localhost:11434</p>
                </div>
              </section>

              <section className="space-y-2">
                <h3 className="text-lg font-bold text-indigo-300 border-b border-slate-800 pb-1 flex items-center gap-2">
                  <Volume2 className="w-5 h-5 text-indigo-400" />
                  3. Piper TTS & eSpeak-NG
                </h3>
                <p>
                  Piper TTS uses ONNX models for neural voice output. On Windows, ensure <code className="text-amber-300 font-mono">espeak-ng-data</code> is present or install the official 64-bit eSpeak-NG MSI package.
                </p>
              </section>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <span className="text-xs text-slate-400 font-mono">
            Arquivo <code className="text-amber-300">MANUAL.md</code> salvo no projeto.
          </span>
          <button
            onClick={onClose}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl transition-all shadow-md shadow-indigo-600/30"
          >
            Fechar Manual
          </button>
        </div>

      </div>
    </div>
  );
};
