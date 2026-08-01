import React, { useState } from 'react';
import { 
  Download, 
  Search, 
  Copy, 
  Check, 
  ExternalLink, 
  Cpu, 
  Sparkles, 
  ShieldCheck, 
  Terminal, 
  BrainCircuit, 
  Play
} from 'lucide-react';
import { OPEN_SOURCE_MODELS } from '../data/modelsData';

interface ModelHubViewProps {
  onSelectModelForChat: (modelName: string) => void;
}

export const ModelHubView: React.FC<ModelHubViewProps> = ({ onSelectModelForChat }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTag, setSelectedTag] = useState<string>('All');
  const [copiedCommand, setCopiedCommand] = useState<string | null>(null);

  const tags = ['All', 'Reasoning', 'Coding', 'General', 'Vision', 'Compact', 'Enterprise', 'Multi-Language'];

  const filteredModels = OPEN_SOURCE_MODELS.filter((model) => {
    const matchesSearch = 
      model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      model.org.toLowerCase().includes(searchTerm.toLowerCase()) ||
      model.description.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesTag = selectedTag === 'All' || model.tags.includes(selectedTag);

    return matchesSearch && matchesTag;
  });

  const copyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedCommand(cmd);
    setTimeout(() => setCopiedCommand(null), 2000);
  };

  return (
    <div id="model-hub-view" className="flex-1 overflow-y-auto bg-slate-950 text-slate-100 p-4 sm:p-6 lg:p-8">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950/60 to-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
          <div className="relative z-10 max-w-2xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold mb-3">
              <Download className="w-3.5 h-3.5 text-indigo-400" />
              <span>GGUF & Open Weights Explorer</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight mb-2">
              Hub de Modelos Open-Source
            </h1>
            <p className="text-slate-300 text-xs sm:text-sm leading-relaxed">
              Explore os principais modelos da comunidade (DeepSeek R1, Llama 3.3, Qwen 2.5, Phi-4). Verifique exigências de RAM/VRAM para quantizações GGUF e copie comandos do Ollama com 1 clique.
            </p>
          </div>
        </div>

        {/* Filters & Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          
          {/* Search Box */}
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar modelos, organizações..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          {/* Tag Pills */}
          <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
            {tags.map((tag) => (
              <button
                key={tag}
                onClick={() => setSelectedTag(tag)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  selectedTag === tag
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>

        </div>

        {/* Models List Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredModels.map((model) => (
            <div
              key={model.id}
              id={`hub-model-card-${model.id}`}
              className="bg-slate-900/80 border border-slate-800 hover:border-indigo-500/40 rounded-2xl p-5 shadow-xl transition-all flex flex-col justify-between"
            >
              <div>
                
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                        {model.org}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {model.params} • Contexto: {model.context}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-white mt-1">{model.name}</h3>
                  </div>

                  {model.supportsReasoning && (
                    <span className="p-1.5 bg-purple-500/10 border border-purple-500/20 text-purple-300 rounded-lg text-[10px] font-mono flex items-center space-x-1 shrink-0">
                      <BrainCircuit className="w-3.5 h-3.5" />
                      <span>Raciocínio</span>
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-300 leading-relaxed mb-4">
                  {model.description}
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 mb-4">
                  {model.tags.map((t) => (
                    <span
                      key={t}
                      className="text-[10px] bg-slate-950 text-slate-400 border border-slate-800 px-2 py-0.5 rounded-md"
                    >
                      #{t}
                    </span>
                  ))}
                </div>

                {/* GGUF Sizes Table */}
                <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 mb-4 space-y-2">
                  <span className="text-[11px] font-bold text-slate-300 block">
                    Formatos GGUF & Requisito de RAM:
                  </span>
                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                    {model.ggufSizes.map((g, idx) => (
                      <div key={idx} className="bg-slate-900/60 p-1.5 rounded border border-slate-800/60 flex items-center justify-between">
                        <span className="text-indigo-300 font-semibold">{g.quant}</span>
                        <span className="text-slate-400">{g.sizeGb}GB (~{g.ramRecommendedGb}GB RAM)</span>
                      </div>
                    ))}
                  </div>
                </div>

              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                
                {/* Terminal Ollama Copy Command */}
                <button
                  onClick={() => copyCommand(model.ollamaCommand)}
                  className="flex-1 flex items-center justify-center space-x-2 bg-slate-950 hover:bg-slate-800 text-slate-200 text-xs font-mono py-2 px-3 rounded-xl border border-slate-800 transition-colors"
                  title="Copiar comando do Ollama"
                >
                  <Terminal className="w-3.5 h-3.5 text-amber-400" />
                  <span className="truncate">{model.ollamaCommand}</span>
                  {copiedCommand === model.ollamaCommand ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <Copy className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  )}
                </button>

                {/* HuggingFace External Link */}
                <a
                  href={model.huggingFaceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="p-2 bg-slate-950 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 rounded-xl transition-colors"
                  title="Ver no HuggingFace"
                >
                  <ExternalLink className="w-4 h-4" />
                </a>

              </div>

            </div>
          ))}
        </div>

      </div>
    </div>
  );
};
