import React, { useState } from 'react';
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Cpu, 
  Zap, 
  Terminal, 
  Copy, 
  Check, 
  Search, 
  HelpCircle, 
  Sparkles, 
  Database, 
  Layers, 
  Monitor, 
  Clock, 
  Flame, 
  HardDrive,
  Info
} from 'lucide-react';

export interface BenchmarkItem {
  id: string;
  name: string;
  category: 'llm' | 'image' | 'audio' | 'moe';
  categoryLabel: string;
  status: 'success' | 'failed' | 'oom' | 'path_error' | 'vae_error';
  statusLabel: string;
  hardware: string;
  resolutionOrContext?: string;
  steps?: number;
  timeTaken?: string;
  vramUsed: string;
  ramUsed: string;
  tpsOrSpeed?: string;
  command?: string;
  prompt?: string;
  notes: string;
  qualityRating?: string;
}

export const BENCHMARK_ITEMS: BenchmarkItem[] = [
  // --- LLM Benchmarks ---
  {
    id: 'mistral-7b-vulkan',
    name: 'Mistral 7B Q4_K_M',
    category: 'llm',
    categoryLabel: 'LLM (Incap. Textual)',
    status: 'success',
    statusLabel: '✅ Sucesso Absoluto',
    hardware: 'RX 580 8GB (Vulkan) + Xeon E5-2690 v3',
    resolutionOrContext: '2048 ctx',
    vramUsed: '4.8 GB',
    ramUsed: '1.2 GB',
    tpsOrSpeed: '17.77 - 18.54 tok/s',
    command: 'llama-cli -m mistral-7b-instruct-v0.2.Q4_K_M.gguf -ngl 99 -c 2048',
    notes: 'Desempenho máximo no Polaris gfx803. 100% das camadas carregadas na GPU via Vulkan.',
    qualityRating: '⭐⭐⭐⭐⭐ (18 tok/s)',
  },
  {
    id: 'qwen3-4b-polaris',
    name: 'Qwen3-4B Q4_K_M',
    category: 'llm',
    categoryLabel: 'LLM (Incap. Textual)',
    status: 'success',
    statusLabel: '✅ Sucesso Absoluto',
    hardware: 'RX 580 8GB (Vulkan Mesa RADV) + 32GB RAM',
    resolutionOrContext: '2048 ctx',
    vramUsed: '2.5 GB',
    ramUsed: '1.1 GB',
    tpsOrSpeed: '16.20 - 18.00 tok/s',
    command: 'llama-cli -m Qwen3-4B-Instruct-Q4_K_M.gguf -ngl 99 -c 2048 --flash-attn',
    notes: 'Teto físico absoluto do Polaris gfx803 sem núcleos de matriz dedicados (fp16=0, int dot=0).',
    qualityRating: '⭐⭐⭐⭐⭐ (Teto Shaders)',
  },
  {
    id: 'qwen3-8b-polaris',
    name: 'Qwen3-8B Q4_K_M',
    category: 'llm',
    categoryLabel: 'LLM (Incap. Textual)',
    status: 'success',
    statusLabel: '✅ Sucesso Absoluto',
    hardware: 'RX 580 8GB (Vulkan) + Xeon E5-2690 v3',
    resolutionOrContext: '2048 ctx',
    vramUsed: '5.2 GB',
    ramUsed: '1.5 GB',
    tpsOrSpeed: '8.50 - 9.10 tok/s',
    command: 'llama-cli -m Qwen3-8B-Instruct-Q4_K_M.gguf -ngl 99 -c 2048',
    notes: 'Escalamento linear limitado pela largura de banda de memória física do Polaris.',
    qualityRating: '⭐⭐⭐⭐ (8.5 tok/s)',
  },
  {
    id: 'qwen35-35b-moe',
    name: 'Qwen3.5-35B A3B Q4_K_M (MoE)',
    category: 'moe',
    categoryLabel: 'MoE (Mixture of Experts)',
    status: 'success',
    statusLabel: '✅ Sucesso Híbrido',
    hardware: 'RX 580 8GB (Vulkan) + Xeon 12-Core + 32GB RAM',
    resolutionOrContext: '2048 ctx (35B total / 3B ativo)',
    vramUsed: '7.2 GB (GPU)',
    ramUsed: '18.4 GB (RAM)',
    tpsOrSpeed: '7.62 tok/s',
    command: 'llama-cli -m Qwen3.5-35B-A3B-Q4_K_M.gguf -ngl 24 -c 2048',
    notes: 'Sucesso histórico! Modelo MoE de 35B rodando em hardware de 2017 via split dinâmico de especialistas.',
    qualityRating: '⭐⭐⭐⭐⭐ (7.6 tok/s MoE)',
  },
  {
    id: 'qwen36-35b-moe-override',
    name: 'Qwen3.6-35B A3B Q4_K_M (Override)',
    category: 'moe',
    categoryLabel: 'MoE (Mixture of Experts)',
    status: 'success',
    statusLabel: '✅ Sucesso Híbrido',
    hardware: 'RX 580 8GB (Vulkan) + Xeon 12-Core + 32GB RAM',
    resolutionOrContext: '2048 ctx',
    vramUsed: '6.8 GB',
    ramUsed: '19.1 GB',
    tpsOrSpeed: '6.92 tok/s',
    command: 'llama-cli -m Qwen3.6-35B-A3B-Q4_K_M.gguf -ngl 20 --override-tensor exps=CPU',
    notes: 'Encaminhamento forçado dos especialistas para a RAM do Xeon mantendo o attention na GPU.',
    qualityRating: '⭐⭐⭐⭐ (6.9 tok/s)',
  },
  {
    id: 'whisper-large-v3-turbo',
    name: 'Whisper Large-v3-Turbo',
    category: 'audio',
    categoryLabel: 'Áudio & Transcrição',
    status: 'success',
    statusLabel: '✅ Sucesso Absoluto',
    hardware: 'RX 580 8GB (Vulkan) / Xeon CPU',
    vramUsed: '1.8 GB',
    ramUsed: '800 MB',
    tpsOrSpeed: '150x Speedup',
    notes: 'Transcrição ultra rápida de arquivos de áudio longos em tempo real.',
    qualityRating: '⭐⭐⭐⭐⭐ (150x Realtime)',
  },
  {
    id: 'applio-rvc-voice-clone',
    name: 'Applio RVC Voice Clone (Yuri)',
    category: 'audio',
    categoryLabel: 'Áudio & Voz Neural',
    status: 'success',
    statusLabel: '✅ Sucesso em CPU',
    hardware: 'Xeon E5-2690 v3 (12 Cores / 24 Threads)',
    vramUsed: '0 MB (100% CPU)',
    ramUsed: '3.2 GB',
    tpsOrSpeed: '2.4x Speedup',
    notes: 'Clonagem e inferência de voz neural RVC/Applio rodando em CPU sem gastar VRAM da GPU.',
    qualityRating: '⭐⭐⭐⭐⭐ (Xeon CPU Mode)',
  },

  // --- Image Benchmarks (SDXL, SD 3.5, FLUX) ---
  {
    id: 'sdxl-1024-base',
    name: 'SDXL 1.0 Base (1024x1024)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'success',
    statusLabel: '✅ Sucesso Absoluto',
    hardware: 'RX 580 8GB (Vulkan) + Xeon E5-2690 v3',
    resolutionOrContext: '1024 x 1024',
    steps: 20,
    timeTaken: '357s (~6 min)',
    vramUsed: '6.4 GB',
    ramUsed: '94 MB',
    tpsOrSpeed: '13.33s / step',
    command: 'sd-cli.exe -m sd_xl_base_1.0.safetensors --vae sdxl_vae-fp16-fix.safetensors --vae-on-cpu -W 1024 -H 1024 --steps 20 -p "a futuristic Sao Paulo cityscape at night..." -o output.png',
    prompt: 'a futuristic Sao Paulo cityscape at night, neon lights, cinematic, 8k',
    notes: 'Exige obrigatoriamente sdxl_vae-fp16-fix.safetensors (335MB) para evitar imagem preta. Estilo fotorrealista com bokeh dramático.',
    qualityRating: '⭐⭐⭐⭐ (Baseline 6min)',
  },
  {
    id: 'sd35-medium-512-clip',
    name: 'SD 3.5 Medium (512x512 - Clip Only)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'success',
    statusLabel: '✅ Sucesso Absoluto',
    hardware: 'RX 580 8GB (Vulkan)',
    resolutionOrContext: '512 x 512',
    steps: 20,
    timeTaken: '110s (~1.8 min)',
    vramUsed: '6.7 GB',
    ramUsed: '120 MB',
    tpsOrSpeed: '5.50s / step',
    command: 'sd-cli.exe -m sd3.5_medium.safetensors --clip_l clip_l.safetensors --clip_g clip_g.safetensors --vae-on-cpu -W 512 -H 512 --steps 20 -p "a futuristic Sao Paulo..."',
    prompt: 'a futuristic Sao Paulo cityscape at night, neon lights, cinematic, 8k',
    notes: '3x mais rápido que SDXL! Imagem fotorrealista e nítida sem estourar VRAM.',
    qualityRating: '⭐⭐⭐⭐⭐ (110s Rápido)',
  },
  {
    id: 'sd35-medium-512-t5xxl-offload',
    name: 'SD 3.5 Medium (512x512 - t5xxl CPU Offload)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'success',
    statusLabel: '✅ Sucesso em RAM (0MB VRAM)',
    hardware: 'Xeon 12-Core + 32GB RAM DDR4 (0MB VRAM)',
    resolutionOrContext: '512 x 512',
    steps: 20,
    timeTaken: '123s (~2 min)',
    vramUsed: '0 MB (100% RAM)',
    ramUsed: '15.9 GB',
    tpsOrSpeed: '6.15s / step',
    command: 'sd-cli.exe -m sd3.5_medium.safetensors --clip_l clip_l.safetensors --clip_g clip_g.safetensors --t5xxl t5xxl_fp8_e4m3fn.safetensors --vae-on-cpu --clip-on-cpu --offload-to-cpu -W 512 -H 512 --steps 20',
    prompt: 'a futuristic Sao Paulo cityscape at night, neon lights, cinematic, 8k',
    notes: 'Feito histórico! O modelo rodou 100% na RAM DDR4 do Xeon liberando totalmente a VRAM da GPU com interpretação perfeita do prompt.',
    qualityRating: '⭐⭐⭐⭐⭐ (Zero VRAM)',
  },
  {
    id: 'sd35-medium-1024-split',
    name: 'SD 3.5 Medium (1024x1024 - Split Híbrido)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'success',
    statusLabel: '✅ Sucesso Híbrido Ultra',
    hardware: 'RX 580 8GB (Vulkan) + Xeon RAM (32GB)',
    resolutionOrContext: '1024 x 1024',
    steps: 20,
    timeTaken: '1332s (~22 min)',
    vramUsed: '7.4 GB (GPU)',
    ramUsed: '15.9 GB (RAM)',
    tpsOrSpeed: '61.66s / step',
    command: 'sd-cli.exe -m sd3.5_medium.safetensors --clip_l clip_l.safetensors --clip_g clip_g.safetensors --t5xxl t5xxl_fp8_e4m3fn.safetensors --vae-on-cpu --clip-on-cpu --offload-to-cpu -W 1024 -H 1024 --steps 20',
    prompt: 'a lovely cat, detailed fur, studio lighting',
    notes: 'Qualidade fotográfica de estúdio impecável (gato Maine Coon e cidade de SP). Denoising na GPU e encoders na RAM.',
    qualityRating: '⭐⭐⭐⭐⭐ (Foto Estúdio)',
  },
  {
    id: 'flux1-q4-512-20steps',
    name: 'FLUX.1 [dev] Q4_K_S (512x512 - 20 Steps)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'success',
    statusLabel: '✅ Sucesso GGUF',
    hardware: 'RX 580 8GB (Vulkan) + Xeon RAM',
    resolutionOrContext: '512 x 512',
    steps: 20,
    timeTaken: '705s (~11.7 min)',
    vramUsed: '7.5 GB',
    ramUsed: '12.5 GB',
    tpsOrSpeed: '32.99s / step',
    command: 'sd-cli.exe --diffusion-model flux1-dev-Q4_K_S.gguf --vae ae.safetensors --clip_l clip_l.safetensors --t5xxl t5xxl_fp8.safetensors --vae-on-cpu --clip-on-cpu --offload-to-cpu -W 512 -H 512 --steps 20',
    prompt: 'a lovely cat, detailed fur, studio lighting',
    notes: 'Executado via parâmetro --diffusion-model. Imagem em estilo ilustração suave.',
    qualityRating: '⭐⭐⭐ (Ilustração 20s)',
  },
  {
    id: 'flux1-q4-512-50steps',
    name: 'FLUX.1 [dev] Q4_K_S (512x512 - 50 Steps)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'success',
    statusLabel: '✅ Sucesso GGUF',
    hardware: 'RX 580 8GB (Vulkan) + Xeon RAM',
    resolutionOrContext: '512 x 512',
    steps: 50,
    timeTaken: '1660s (~27.6 min)',
    vramUsed: '7.5 GB',
    ramUsed: '17.1 GB',
    tpsOrSpeed: '32.16s / step',
    command: 'sd-cli.exe --diffusion-model flux1-dev-Q4_K_S.gguf --vae ae.safetensors --clip_l clip_l.safetensors --t5xxl t5xxl_fp8.safetensors --vae-on-cpu --clip-on-cpu --offload-to-cpu -W 512 -H 512 --steps 50',
    prompt: 'a lovely cat, detailed fur, studio lighting',
    notes: '50 passos resolveram detalhes de pelagem e iluminação digital refinada.',
    qualityRating: '⭐⭐⭐⭐ (50 Steps Refinado)',
  },
  {
    id: 'flux1-q3-768-28steps',
    name: 'FLUX.1 [dev] Q3_K_S (768x768 - 28 Steps)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'success',
    statusLabel: '✅ Sucesso Absoluto (Teto FLUX)',
    hardware: 'RX 580 8GB (Vulkan) + Xeon RAM',
    resolutionOrContext: '768 x 768',
    steps: 28,
    timeTaken: '2253s (~37.5 min)',
    vramUsed: '6.4 GB (Modelo 5.0GB na GPU)',
    ramUsed: '16.7 GB',
    tpsOrSpeed: '77.43s / step',
    command: 'sd-cli.exe --diffusion-model flux1-dev-Q3_K_S.gguf --vae ae.safetensors --clip_l clip_l.safetensors --t5xxl t5xxl_fp8.safetensors --vae-on-cpu --clip-on-cpu --offload-to-cpu --cfg-scale 3.5 -W 768 -H 768 --steps 28',
    prompt: 'a lovely cat, detailed fur, studio lighting',
    notes: 'TETO MÁXIMO DO FLUX EM 8GB VRAM! O modelo de 5.0GB respeitou a Regra dos 6.3GB e permitiu o buffer de computação em 768x768.',
    qualityRating: '⭐⭐⭐⭐⭐ (Teto 768x768)',
  },

  // --- Failures, OOMs & Execution Errors ---
  {
    id: 'flux1-q4-768-oom',
    name: 'FLUX.1 [dev] Q4_K_S (768x768 / 1024x1024)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'oom',
    statusLabel: '❌ OOM (Compute Buffer)',
    hardware: 'RX 580 8GB VRAM',
    resolutionOrContext: '768x768 / 1024x1024',
    vramUsed: 'Estourou 8.0 GB',
    ramUsed: '16.0 GB',
    notes: 'Falha de alocação de buffer de computação (`failed to allocate compute buffer of size 4124314640 bytes`). Exige ~4GB só de buffer mais 6.8GB do modelo (>10GB VRAM).',
  },
  {
    id: 'flux1-q8-oom',
    name: 'FLUX.1 [dev] Q8_0 (12.7 GB)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'oom',
    statusLabel: '❌ OOM (Modelo Físico)',
    hardware: 'RX 580 8GB VRAM',
    resolutionOrContext: '512 x 512',
    vramUsed: '12.7 GB (> 8GB)',
    ramUsed: '16.0 GB',
    notes: 'O tamanho dos pesos quantizados Q8 (12.7GB) excede fisicamente a VRAM da GPU (`1063888896 bytes allocation failure`).',
  },
  {
    id: 'flux2-q4-vae-error',
    name: 'FLUX.2 [dev] Q4_K_S (19.3 GB)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'vae_error',
    statusLabel: '❌ Incompatibilidade VAE',
    hardware: 'RX 580 8GB / Xeon RAM',
    resolutionOrContext: '512 x 512',
    vramUsed: 'N/A',
    ramUsed: '19.3 GB',
    notes: 'Incompatibilidade de dimensões no encoder de VAE (`got shape [3,3,16,512], expected [3,3,32,512]`). Exige o VAE nativo do FLUX.2.',
  },
  {
    id: 'sd35-large-system-freeze',
    name: 'SD 3.5 Large (16.5 GB)',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'failed',
    statusLabel: '❌ Congelamento de Sistema',
    hardware: 'RX 580 8GB + 32GB RAM DDR4',
    resolutionOrContext: '512 x 512',
    vramUsed: '8.0 GB (100%)',
    ramUsed: '31.8 GB (100%)',
    notes: 'Esgotou a VRAM e toda a RAM DDR4 do sistema, travando o ponteiro do mouse e gerando tela preta no driver. Requer margem de RAM > 32GB.',
  },
  {
    id: 'flux-kontext-path-error',
    name: 'FLUX Kontext Q4 / Juggernaut XL',
    category: 'image',
    categoryLabel: 'Geração de Imagem',
    status: 'path_error',
    statusLabel: '❌ Erro de Caminho CLI',
    hardware: 'Windows 10 PowerShell',
    vramUsed: 'N/A',
    ramUsed: 'N/A',
    notes: 'Erro de sintaxe de caminho no script CLI (`file not found: Juggernaut-XL-v9-RunDiffusionPhoto-v2.safetensors`). O modelo existe mas o caminho do diretório estava incorreto.',
  },
];

export const BenchmarkSection: React.FC = () => {
  const [activeCategory, setActiveCategory] = useState<'all' | 'success' | 'failed' | 'llm' | 'image' | 'erratas'>('all');
  const [searchTerm, setSearchQuery] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const handleCopyCommand = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredItems = BENCHMARK_ITEMS.filter((item) => {
    let matchesCat = true;
    if (activeCategory === 'success') matchesCat = item.status === 'success';
    else if (activeCategory === 'failed') matchesCat = item.status !== 'success';
    else if (activeCategory === 'llm') matchesCat = item.category === 'llm' || item.category === 'moe' || item.category === 'audio';
    else if (activeCategory === 'image') matchesCat = item.category === 'image';
    
    const matchesSearch = 
      item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.notes.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.hardware.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (item.command && item.command.toLowerCase().includes(searchTerm.toLowerCase()));

    return matchesCat && matchesSearch;
  });

  const successCount = BENCHMARK_ITEMS.filter(i => i.status === 'success').length;
  const failureCount = BENCHMARK_ITEMS.filter(i => i.status !== 'success').length;

  return (
    <div id="benchmark-hub-container" className="bg-slate-900/90 border border-indigo-500/30 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-6">
      
      {/* Top Banner Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 border-b border-slate-800 pb-6">
        <div className="space-y-2 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-3 py-1 rounded-full text-[11px] font-extrabold uppercase font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Matriz de Conhecimento e Benchmarks Reais 2026</span>
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              RX 580 8GB Vulkan + Xeon E5-2690 v3
            </span>
          </div>

          <h2 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight flex items-center space-x-2">
            <Activity className="w-6 h-6 text-indigo-400" />
            <span>Resultados de Campo: Todos os Testes, Sucessos &amp; Fracassos</span>
          </h2>

          <p className="text-xs text-slate-300 leading-relaxed">
            Documentação rigorosa sem maquiagem: logs de terminal, tempos cronometrados, comandos CLI exatos, limites de VRAM/RAM e falhas documentadas para orientar o orquestrador Phoenix Engine.
          </p>
        </div>

        {/* Quick Metrics Summary */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 shrink-0">
          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-center">
            <span className="block text-[10px] text-slate-400 font-mono">Testes Registrados</span>
            <span className="text-lg font-bold text-white font-mono">{BENCHMARK_ITEMS.length}</span>
          </div>
          <div className="bg-slate-950 p-3 rounded-xl border border-emerald-500/30 text-center">
            <span className="block text-[10px] text-emerald-400 font-mono">Sucessos ✅</span>
            <span className="text-lg font-bold text-emerald-300 font-mono">{successCount}</span>
          </div>
          <div className="bg-slate-950 p-3 rounded-xl border border-rose-500/30 text-center">
            <span className="block text-[10px] text-rose-400 font-mono">Fracassos/OOMs ❌</span>
            <span className="text-lg font-bold text-rose-300 font-mono">{failureCount}</span>
          </div>
          <div className="bg-slate-950 p-3 rounded-xl border border-indigo-500/30 text-center">
            <span className="block text-[10px] text-indigo-400 font-mono">Teto VRAM FLUX</span>
            <span className="text-lg font-bold text-indigo-300 font-mono">≤ 6.3 GB</span>
          </div>
        </div>
      </div>

      {/* Regra Mágica dos 6.3GB VRAM Card */}
      <div className="bg-gradient-to-r from-slate-950 via-indigo-950/40 to-slate-950 border border-indigo-500/30 rounded-2xl p-5 space-y-3">
        <div className="flex items-center space-x-2 text-indigo-300 font-bold text-sm">
          <Zap className="w-4 h-4 text-amber-400" />
          <span>Fórmula da Regra dos 6.3GB VRAM (Vulkan / Polaris RX 580)</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          Para que modelos pesados de difusão (como o <strong>FLUX.1 [dev]</strong> e <strong>SD 3.5 Medium</strong>) rodem sem erro de alocação de buffer de computação no Vulkan, o tamanho do arquivo quantizado na VRAM não pode ultrapassar <strong>6.3 GB</strong>:
        </p>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 font-mono text-[11px] text-slate-300 flex flex-wrap items-center justify-between gap-2">
          <div>
            <span className="text-emerald-400">8.0 GB VRAM Total</span> - <span className="text-amber-400">1.2 GB Compute Buffer</span> - <span className="text-cyan-400">0.5 GB Folga de Sistema</span> = <strong className="text-indigo-300 text-xs">6.3 GB Peso Máximo na VRAM</strong>
          </div>
          <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[10px]">--offload-to-cpu ativado</span>
        </div>
      </div>

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          {[
            { id: 'all', label: 'Todos os Testes' },
            { id: 'success', label: '✅ Sucessos' },
            { id: 'failed', label: '❌ Fracassos & OOMs' },
            { id: 'llm', label: '📊 LLMs & Runtimes' },
            { id: 'image', label: '🎨 Geração de Imagem' },
            { id: 'erratas', label: '💡 Erratas & Evolução' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveCategory(tab.id as any)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                activeCategory === tab.id
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                  : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72 shrink-0">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar modelo, comando ou erro..."
            className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
          />
        </div>
      </div>

      {/* Erratas & Field Evolution Section */}
      {activeCategory === 'erratas' && (
        <div className="space-y-4 pt-2">
          <div className="bg-slate-950 border border-indigo-500/30 rounded-2xl p-5 space-y-4">
            <div className="flex items-center space-x-2 text-indigo-300 font-bold text-sm">
              <Info className="w-4 h-4 text-indigo-400" />
              <span>Erratas Evolutivas — Quando a Prática de Campo Supera a Teoria</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2">
                <span className="text-amber-400 font-bold block text-[11px]">1. Incompatibilidade GGUF do city96</span>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  <strong className="text-rose-400">Antes:</strong> Documentava-se que os modelos GGUF do repositório <code className="text-slate-300">city96</code> eram compatíveis exclusivamente com o ComfyUI.<br />
                  <strong className="text-emerald-400">Depois (Junho/2026):</strong> Descobriu-se a flag <code className="text-amber-300">--diffusion-model</code> no <code className="text-slate-300">sd-cli.exe</code> do <code className="text-slate-300">stable-diffusion.cpp</code>, permitindo rodar modelos GGUF nativamente no Vulkan!
                </p>
              </div>

              <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2">
                <span className="text-amber-400 font-bold block text-[11px]">2. Teto Shaders do Polaris RX 580</span>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  <strong className="text-rose-400">Antes:</strong> Acreditava-se que a largura de banda teórica de 256 GB/s entregaria ~100 tok/s em LLMs de 2.5GB.<br />
                  <strong className="text-emerald-400">Depois:</strong> Identificou-se que a arquitetura Polaris (gfx803) tem <code className="text-slate-300">fp16=0</code> e <code className="text-slate-300">int dot=0</code> (sem núcleos de matriz dedicados). O teto físico real no Vulkan RADV é ~16-18 tok/s.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Benchmark Items List */}
      <div className="space-y-3 pt-2">
        {filteredItems.map((item) => {
          const isSuccess = item.status === 'success';

          return (
            <div
              key={item.id}
              className={`border rounded-2xl p-4 sm:p-5 transition-all space-y-3 ${
                isSuccess
                  ? 'bg-slate-950/90 border-slate-800 hover:border-emerald-500/40'
                  : 'bg-rose-950/20 border-rose-900/40 hover:border-rose-700/60'
              }`}
            >
              {/* Item Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-xl border ${
                    isSuccess
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}>
                    {isSuccess ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                  </div>

                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-bold text-sm text-white">{item.name}</h3>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border font-semibold ${
                        isSuccess
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                      }`}>
                        {item.statusLabel}
                      </span>
                      <span className="text-[10px] font-mono bg-slate-900 text-indigo-300 border border-slate-800 px-2 py-0.5 rounded-full">
                        {item.categoryLabel}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-400 mt-0.5 font-mono">
                      Hardware: {item.hardware}
                    </p>
                  </div>
                </div>

                {/* Rating / Speed Badge */}
                {item.qualityRating && (
                  <span className="text-[11px] font-mono text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-lg self-start sm:self-auto font-semibold">
                    {item.qualityRating}
                  </span>
                )}
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
                <div>
                  <span className="text-slate-500 block text-[10px]">Resolução / Contexto</span>
                  <span className="text-slate-200 font-semibold">{item.resolutionOrContext || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">Tempo Total / Passos</span>
                  <span className="text-slate-200 font-semibold">{item.timeTaken || item.tpsOrSpeed || 'N/A'} {item.steps ? `(${item.steps} steps)` : ''}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">VRAM Utilizada</span>
                  <span className={`font-semibold ${item.vramUsed.includes('0 MB') ? 'text-emerald-400' : 'text-indigo-300'}`}>
                    {item.vramUsed}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px]">RAM do Sistema</span>
                  <span className="text-cyan-300 font-semibold">{item.ramUsed}</span>
                </div>
              </div>

              {/* Notes & Description */}
              <p className="text-xs text-slate-300 leading-relaxed font-sans">
                {item.notes}
              </p>

              {/* Command CLI Code Block */}
              {item.command && (
                <div className="bg-slate-950 rounded-xl p-3 border border-slate-800 font-mono text-[11px] space-y-1 relative group">
                  <div className="flex items-center justify-between text-[10px] text-slate-500 pb-1 border-b border-slate-900">
                    <span>Comando CLI Executado</span>
                    <button
                      onClick={() => handleCopyCommand(item.id, item.command!)}
                      className="flex items-center space-x-1 text-indigo-400 hover:text-indigo-300 font-sans text-[10px] transition-colors"
                    >
                      {copiedId === item.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedId === item.id ? 'Copiado!' : 'Copiar Comando'}</span>
                    </button>
                  </div>
                  <p className="text-slate-300 whitespace-pre-wrap break-all pt-1">
                    {item.command}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>

    </div>
  );
};
