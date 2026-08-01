import React, { useState } from 'react';
import { 
  Cpu, 
  Zap, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Info, 
  Sliders, 
  Database,
  Layers,
  Sparkles
} from 'lucide-react';

export const VramCalculatorView: React.FC = () => {
  const [gpuName, setGpuName] = useState<string>('rtx4090');
  const [customVramGb, setCustomVramGb] = useState<number>(24);
  const [customBandwidth, setCustomBandwidth] = useState<number>(1008);
  
  const [paramSizeNum, setParamSizeNum] = useState<number>(8); // e.g. 8B
  const [quantType, setQuantType] = useState<string>('Q4_K_M');
  const [contextTokens, setContextTokens] = useState<number>(16384);
  const [kvCacheQuant, setKvCacheQuant] = useState<string>('FP16');

  // Pre-defined GPU profiles
  const gpuProfiles: Record<string, { name: string; vramGb: number; bandwidthGbs: number }> = {
    rx580: { name: 'AMD Radeon RX 580 2048SP (8 GB)', vramGb: 8, bandwidthGbs: 224 },
    rx6600: { name: 'AMD Radeon RX 6600 (8 GB)', vramGb: 8, bandwidthGbs: 224 },
    rx6700xt: { name: 'AMD Radeon RX 6700 XT (12 GB)', vramGb: 12, bandwidthGbs: 384 },
    rx7800xt: { name: 'AMD Radeon RX 7800 XT (16 GB)', vramGb: 16, bandwidthGbs: 624 },
    rx7900xtx: { name: 'AMD Radeon RX 7900 XTX (24 GB)', vramGb: 24, bandwidthGbs: 960 },
    rtx3060: { name: 'NVIDIA RTX 3060 (12 GB)', vramGb: 12, bandwidthGbs: 360 },
    rtx4070: { name: 'NVIDIA RTX 4070 (12 GB)', vramGb: 12, bandwidthGbs: 504 },
    rtx3080: { name: 'NVIDIA RTX 3080 (10 GB)', vramGb: 10, bandwidthGbs: 760 },
    rtx4080: { name: 'NVIDIA RTX 4080 (16 GB)', vramGb: 16, bandwidthGbs: 716 },
    rtx4090: { name: 'NVIDIA RTX 4090 (24 GB)', vramGb: 24, bandwidthGbs: 1008 },
    m3max36: { name: 'Apple M3/M4 Max (36 GB)', vramGb: 36, bandwidthGbs: 300 },
    m2max64: { name: 'Apple M2/M3 Max (64 GB)', vramGb: 64, bandwidthGbs: 400 },
    m2ultra128: { name: 'Apple M2/M3 Ultra (128 GB)', vramGb: 128, bandwidthGbs: 800 },
    a100: { name: 'NVIDIA A100 SXM4 (80 GB)', vramGb: 80, bandwidthGbs: 2039 },
    custom: { name: 'GPU Personalizada', vramGb: customVramGb, bandwidthGbs: customBandwidth },
  };

  const currentGpu = gpuProfiles[gpuName] || gpuProfiles.rtx4090;

  // Bits per weight for quantizations
  const quantBits: Record<string, number> = {
    Q2_K: 2.5,
    Q3_K_M: 3.4,
    Q4_K_M: 4.5,
    Q5_K_M: 5.5,
    Q8_0: 8.5,
    FP16: 16.0,
  };

  const bitsPerWeight = quantBits[quantType] || 4.5;

  // Model Weights VRAM Calculation (GB)
  // Formula: (Params * BitsPerWeight) / 8 / 1024 + 10% overhead for activation tensors
  const modelWeightsGb = (paramSizeNum * 1e9 * bitsPerWeight) / (8 * 1024 * 1024 * 1024);

  // KV Cache VRAM Calculation (GB)
  // Approx KV cache size per token per billion params = 0.5 MB / token / B-param for FP16
  let kvMultiplier = 1.0;
  if (kvCacheQuant === 'Q8') kvMultiplier = 0.5;
  if (kvCacheQuant === 'Q4') kvMultiplier = 0.25;

  const kvCacheGb = ((paramSizeNum * contextTokens * 500000) / (1024 * 1024 * 1024)) * kvMultiplier;

  // CUDA / PyTorch Framework Overhead
  const overheadGb = 1.2;

  // Total VRAM
  const totalVramNeeded = parseFloat((modelWeightsGb + kvCacheGb + overheadGb).toFixed(2));
  const availableVram = currentGpu.vramGb;

  // Offload feasibility percentage
  const offloadPercentage = Math.min(100, Math.round((availableVram / totalVramNeeded) * 100));

  // Total layers estimation (e.g. 8B has ~32 layers, 70B has ~80 layers)
  const totalLayers = paramSizeNum <= 8 ? 32 : paramSizeNum <= 14 ? 48 : paramSizeNum <= 32 ? 64 : 80;
  const offloadedLayers = Math.min(totalLayers, Math.floor((availableVram / totalVramNeeded) * totalLayers));

  // Estimated Tokens Per Second
  // Memory Bandwidth / Model Size in GB = tok/s theoretical upper limit
  const theoreticalTokSec = Math.round(currentGpu.bandwidthGbs / Math.max(1, totalVramNeeded));

  return (
    <div id="vram-calculator-view" className="flex-1 overflow-y-auto bg-slate-950 text-slate-100 p-4 sm:p-6 lg:p-8">
      <div className="max-w-5xl mx-auto space-y-6">
        
        {/* Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex items-start space-x-4">
          <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl shrink-0">
            <Cpu className="w-8 h-8 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-white mb-1">
              Calculadora de VRAM & Desempenho de Hardware
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
              Estime com precisão a memória VRAM necessária para rodar modelos GGUF locais no Ollama ou LM Studio, considerando tamanho de parâmetros, quantização e tamanho do contexto.
            </p>
          </div>
        </div>

        {/* Form Inputs Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Left Column: Hardware & Model Config */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-5 shadow-xl">
            <h2 className="text-sm font-bold text-white flex items-center space-x-2 border-b border-slate-800 pb-3">
              <Sliders className="w-4 h-4 text-indigo-400" />
              <span>Configuração de Hardware & Modelo</span>
            </h2>

            {/* GPU Profile */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Placa de Vídeo / Hardware
              </label>
              <select
                value={gpuName}
                onChange={(e) => setGpuName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:ring-1 focus:ring-indigo-500 font-semibold"
              >
                {Object.entries(gpuProfiles).map(([key, gpu]) => (
                  <option key={key} value={key}>
                    {gpu.name} ({gpu.vramGb} GB VRAM • {gpu.bandwidthGbs} GB/s)
                  </option>
                ))}
              </select>
            </div>

            {/* Custom VRAM if Custom selected */}
            {gpuName === 'custom' && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">VRAM (GB)</label>
                  <input
                    type="number"
                    value={customVramGb}
                    onChange={(e) => setCustomVramGb(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Largura de Banda (GB/s)</label>
                  <input
                    type="number"
                    value={customBandwidth}
                    onChange={(e) => setCustomBandwidth(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-white"
                  />
                </div>
              </div>
            )}

            {/* Model Size */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-xs font-semibold text-slate-300">Tamanho dos Parâmetros</label>
                <span className="font-mono text-xs font-bold text-indigo-400">{paramSizeNum}B Parâmetros</span>
              </div>
              <div className="grid grid-cols-4 gap-2">
                {[3, 8, 14, 32, 70, 405].map((size) => (
                  <button
                    key={size}
                    onClick={() => setParamSizeNum(size)}
                    className={`py-1.5 px-2 rounded-lg text-xs font-mono font-bold transition-all ${
                      paramSizeNum === size
                        ? 'bg-indigo-600 text-white shadow-md'
                        : 'bg-slate-950 text-slate-400 border border-slate-800 hover:bg-slate-800'
                    }`}
                  >
                    {size}B
                  </button>
                ))}
              </div>
            </div>

            {/* Quantization Format */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Formato de Quantização GGUF
              </label>
              <div className="grid grid-cols-3 gap-2">
                {Object.keys(quantBits).map((q) => (
                  <button
                    key={q}
                    onClick={() => setQuantType(q)}
                    className={`py-1.5 px-2 rounded-lg text-xs font-mono font-medium transition-all ${
                      quantType === q
                        ? 'bg-indigo-600 text-white shadow-md'
                        : 'bg-slate-950 text-slate-400 border border-slate-800 hover:bg-slate-800'
                    }`}
                  >
                    {q} ({quantBits[q]} bits)
                  </button>
                ))}
              </div>
            </div>

            {/* Context Window Slider */}
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-xs font-semibold text-slate-300">Tamanho do Contexto</label>
                <span className="font-mono text-xs font-bold text-indigo-400">{(contextTokens / 1024).toFixed(0)}K Tokens</span>
              </div>
              <input
                type="range"
                min="2048"
                max="131072"
                step="2048"
                value={contextTokens}
                onChange={(e) => setContextTokens(Number(e.target.value))}
                className="w-full accent-indigo-500 cursor-pointer"
              />
            </div>

          </div>

          {/* Right Column: Output & Calculations */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-5 shadow-xl flex flex-col justify-between">
            <div>
              <h2 className="text-sm font-bold text-white flex items-center space-x-2 border-b border-slate-800 pb-3">
                <Database className="w-4 h-4 text-indigo-400" />
                <span>Estimativa de Memória VRAM & Status</span>
              </h2>

              {/* Status Badge */}
              <div className="my-4">
                {totalVramNeeded <= availableVram ? (
                  <div className="p-3 bg-emerald-950/40 border border-emerald-800/50 rounded-xl flex items-center space-x-3 text-emerald-300">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    <div>
                      <span className="font-bold text-xs block">Offload 100% na GPU Suportado</span>
                      <span className="text-[11px] text-emerald-400/80">O modelo cabe totalmente na VRAM para velocidade máxima.</span>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 bg-amber-950/40 border border-amber-800/50 rounded-xl flex items-center space-x-3 text-amber-300">
                    <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
                    <div>
                      <span className="font-bold text-xs block">Offload Parcial (Spillover na RAM)</span>
                      <span className="text-[11px] text-amber-400/80">
                        {offloadedLayers} de {totalLayers} camadas rodarão na VRAM. O restante na RAM do sistema.
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* VRAM Breakdown Bars */}
              <div className="space-y-3 font-mono text-xs">
                
                {/* Weights */}
                <div>
                  <div className="flex justify-between text-slate-300 mb-1">
                    <span>Pesos do Modelo ({quantType}):</span>
                    <span className="text-indigo-400 font-bold">{modelWeightsGb.toFixed(2)} GB</span>
                  </div>
                  <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-indigo-500 h-full rounded-full"
                      style={{ width: `${Math.min(100, (modelWeightsGb / availableVram) * 100)}%` }}
                    />
                  </div>
                </div>

                {/* KV Cache */}
                <div>
                  <div className="flex justify-between text-slate-300 mb-1">
                    <span>KV Cache (Contexto {(contextTokens / 1024).toFixed(0)}K):</span>
                    <span className="text-cyan-400 font-bold">{kvCacheGb.toFixed(2)} GB</span>
                  </div>
                  <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-cyan-500 h-full rounded-full"
                      style={{ width: `${Math.min(100, (kvCacheGb / availableVram) * 100)}%` }}
                    />
                  </div>
                </div>

                {/* Overhead */}
                <div>
                  <div className="flex justify-between text-slate-300 mb-1">
                    <span>Overhead do Driver / CUDA:</span>
                    <span className="text-slate-400">{overheadGb.toFixed(2)} GB</span>
                  </div>
                  <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-slate-600 h-full rounded-full"
                      style={{ width: `${Math.min(100, (overheadGb / availableVram) * 100)}%` }}
                    />
                  </div>
                </div>

              </div>
            </div>

            {/* Total VRAM & Theoretical tok/s */}
            <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3">
              <div className="flex justify-between items-center text-sm font-bold text-white border-b border-slate-800/80 pb-2">
                <span>VRAM Total Necessária:</span>
                <span className="text-indigo-300 font-mono text-base">{totalVramNeeded} GB</span>
              </div>

              <div className="flex justify-between items-center text-xs text-slate-300">
                <span className="flex items-center space-x-1">
                  <Zap className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Velocidade Teórica Estimada:</span>
                </span>
                <span className="font-mono font-bold text-emerald-400">~{theoreticalTokSec} tok/s</span>
              </div>
            </div>

          </div>

        </div>

        {/* Real RX 580 8GB + Xeon Benchmark Card */}
        <div className="bg-slate-900/90 border border-indigo-500/30 rounded-2xl p-6 shadow-2xl space-y-5 relative overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-extrabold text-white">
                  Laboratório RX 580 2048SP (8 GB VRAM) & Xeon Benchmark Real
                </h2>
                <p className="text-xs text-slate-400">
                  Resultados validados na prática com aceleração Vulkan, WSL2 e arquitetura de carregamento híbrido.
                </p>
              </div>
            </div>
            <span className="text-[11px] font-mono font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20 px-3 py-1 rounded-full">
              AMD Vulkan Acelerado
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            
            {/* Test 1: LLM Mistral 7B */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>Mistral 7B Q4_K_M (Llama.cpp)</span>
                <span className="text-emerald-400 font-mono">17.77 tok/s</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Rodando 100% offload na RX 580 com a flag <code className="text-indigo-300 font-mono">-DGGML_VULKAN=ON --device Vulkan0</code>.
              </p>
            </div>

            {/* Test 2: Polaris Vulkan Teto LLM */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>Qwen 3.5 4B / Qwen 3 8B (Llama.cpp)</span>
                <span className="text-emerald-400 font-mono">~16-18 tok/s Teto</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Teto físico do chip Polaris (gfx803) via Vulkan RADV. Sem núcleos de matriz em hardware (operações em FP32 shader fallback).
              </p>
            </div>

            {/* Test 3: SDXL 1.0 Baseline */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>SDXL 1.0 Base (1024x1024)</span>
                <span className="text-indigo-400 font-mono">357s (~6 min) • 6.4GB VRAM</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Baseline de referência (20 steps, seed 42). Exige <code className="text-indigo-300 font-mono">sdxl_vae-fp16-fix.safetensors</code> para evitar tela preta.
              </p>
            </div>

            {/* Test 4: DreamShaper 8 GGUF */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>DreamShaper 8 GGUF (SD.cpp)</span>
                <span className="text-cyan-400 font-mono">Geração Vulkan</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Compilado nativamente com C++ e Vulkan na porta 7860. Renderiza imagens SD1.5/GGUF sem estouro de VRAM.
              </p>
            </div>

            {/* Test 5: SD 3.5 Medium vs SDXL */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>SD 3.5 Medium (512x512 MMDiT)</span>
                <span className="text-emerald-400 font-mono">110s (6.7GB VRAM)</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                3x mais rápido que SDXL 1.0 (357s). Fotorrealismo impressionante em cenas urbanas e retratos em estúdio.
              </p>
            </div>

            {/* Test 6: SD 3.5 Medium 100% CPU Offload */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>SD 3.5 Medium (t5xxl Offload)</span>
                <span className="text-cyan-400 font-mono">0MB VRAM • 15.9GB RAM</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Executado 100% na RAM DDR4 do Xeon em 123s (512px) e 22 min (1024px) com a flag <code className="text-indigo-300 font-mono">--offload-to-cpu</code>.
              </p>
            </div>

            {/* Test 7: FLUX.1 Schnell (16GB) */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>FLUX.1 Schnell (16GB Híbrido)</span>
                <span className="text-amber-400 font-mono">~14 min/img</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Modo híbrido VRAM + RAM com <code className="text-indigo-300 font-mono">--vae-on-cpu --vae-tiling</code> e 4 steps de difusão rápida.
              </p>
            </div>

            {/* Test 8: FLUX.1 Q3 768x768 */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>FLUX.1 [dev] Q3_K_S (768x768)</span>
                <span className="text-amber-400 font-mono">2253s (~37 min)</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Regra dos 6.3GB VRAM: Modelo Q3 (5.0GB) coube em 768x768 via <code className="text-indigo-300 font-mono">--diffusion-model</code> do city96 GGUF.
              </p>
            </div>

            {/* Test 9: FLUX.1 Q4 512x512 */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>FLUX.1 [dev] Q4 (512x512)</span>
                <span className="text-indigo-400 font-mono">705s (20s) • 1660s (50s)</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Offload dinâmico na RX 580 (6.8GB) + Xeon. Resoluções &ge;768px no Q4 resultam em OOM no compute buffer (~4GB requeridos).
              </p>
            </div>

            {/* Test 10: FLUX Q8 OOM Documentado */}
            <div className="bg-slate-950 p-4 rounded-xl border border-rose-900/50 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-rose-300">
                <span>FLUX.1 Q8 (12.7 GB) [OOM]</span>
                <span className="text-rose-400 font-mono">Buffer Failure</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Falha ao alocar buffer Vulkan0 de 1.06 GB. Excede a VRAM física da RX 580 mesmo em 512x512.
              </p>
            </div>

            {/* Test 11: FLUX.2 Dev VAE Incompatibility */}
            <div className="bg-slate-950 p-4 rounded-xl border border-rose-900/50 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-rose-300">
                <span>FLUX.2 dev Q4 (19.3 GB) [Erro VAE]</span>
                <span className="text-rose-400 font-mono">Shape Mismatch</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Incompatibilidade de VAE: recebido tensor <code className="text-indigo-300 font-mono">[3,3,16,512]</code> vs esperado <code className="text-indigo-300 font-mono">[3,3,32,512]</code>. Requer VAE nativo FLUX.2.
              </p>
            </div>

            {/* Test 12: SD 3.5 Large Freeze */}
            <div className="bg-slate-950 p-4 rounded-xl border border-rose-900/50 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-rose-300">
                <span>SD 3.5 Large (16.5 GB) [Saturação]</span>
                <span className="text-rose-400 font-mono">System Freeze</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Consumiu 100% da RAM e causou tela preta no Windows por exaustão de Swap/Pagefile.
              </p>
            </div>

            {/* Test 13: Regra dos 6.3GB VRAM */}
            <div className="bg-slate-950 p-4 rounded-xl border border-amber-500/30 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-amber-300">
                <span>Regra Mágica dos 6.3GB VRAM</span>
                <span className="text-amber-400 font-mono">Fórmula Prática</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                <code className="text-indigo-300 font-mono">8GB - 1.2GB (Buffer) - 0.5GB (Margem) = ~6.3GB</code> máx. Modelo de difusão não deve passar de 6.3GB na VRAM.
              </p>
            </div>

            {/* Test 14: Whisper Transcription */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>Whisper Large-v3-Turbo</span>
                <span className="text-emerald-400 font-mono">150x Speedup</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Transcreve áudio/vídeo MP4 de 15 minutos em apenas ~5 minutos usando aceleração Vulkan.
              </p>
            </div>

            {/* Test 15: Applio RVC Voice Clone */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>Applio RVC Voice Clone</span>
                <span className="text-purple-400 font-mono">Xeon CPU Mode</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Executado no processador Xeon com Python 3.11 para evitar travamentos do DirectML no Windows.
              </p>
            </div>

            {/* Test 16: ComfyUI WSL2 */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>ComfyUI no WSL2 (Ubuntu)</span>
                <span className="text-indigo-400 font-mono">Link Simbólico</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Espelhamento de modelos <code className="text-indigo-300 font-mono">ln -s /mnt/e/models</code> permitindo carregar modelos gigantes de 16GB.
              </p>
            </div>

            {/* Test 17: Errata city96 GGUF */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-white">
                <span>Erratas & Descobertas GGUF</span>
                <span className="text-emerald-400 font-mono">--diffusion-model</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Revisão: city96 GGUF é 100% compatível com <code className="text-indigo-300 font-mono">sd-cli</code> usando a flag <code className="text-indigo-300 font-mono">--diffusion-model</code> (Método DadHacks).
              </p>
            </div>

            {/* Test 18: Path & File Errors */}
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-bold text-slate-300">
                <span>Erros de Caminho (Kontext/Juggernaut)</span>
                <span className="text-slate-400 font-mono">Path Mismatch</span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Documentado: Erros "File not found" ocorrem devido a hífens vs underscores nos repositórios HuggingFace.
              </p>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
};
