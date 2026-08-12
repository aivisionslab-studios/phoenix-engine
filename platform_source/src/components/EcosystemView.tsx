import React, { useState } from 'react';
import { 
  Cpu, 
  Server, 
  Globe, 
  Monitor, 
  Bot, 
  Terminal, 
  ExternalLink, 
  CheckCircle2, 
  Sparkles, 
  Search, 
  ShieldCheck, 
  Zap,
  Layers,
  Activity,
  ArrowUpRight,
  Code2,
  Workflow,
  Laptop,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Check,
  AlertCircle,
  XCircle,
  Settings,
  Volume2,
  AudioWaveform
} from 'lucide-react';
import { ProviderConfig, ProviderType } from '../types';
import { synthesizeAndPlayPiper, stopPiperSpeech, DEFAULT_PIPER_VOICES } from '../services/piperTtsService';
import { BenchmarkSection } from './BenchmarkSection';

interface EcosystemViewProps {
  providers: ProviderConfig[];
  onOpenSettings: () => void;
  onUpdateProvider?: (updated: ProviderConfig) => void;
  onTestProvider?: (providerId: string) => Promise<void>;
  hasGeminiKey?: boolean;
}

export interface EcosystemTool {
  id: string;
  name: string;
  category: 'runtime' | 'server' | 'webui' | 'desktop' | 'agent' | 'aios';
  categoryLabel: string;
  description: string;
  url: string;
  phoenixStatus: 'Orquestrado Nativamente' | 'Endpoint Conectado' | 'Provedor Suportado' | 'Integração Via API';
  endpointDefault?: string;
  popularModels?: string[];
  tags: string[];
}

export const ECOSYSTEM_TOOLS: EcosystemTool[] = [
  // 1. Runtimes de Inferência
  {
    id: 'piper-tts',
    name: 'Piper TTS (OHF-Voice / piper1-gpl)',
    category: 'runtime',
    categoryLabel: 'Síntese Neural de Voz (TTS)',
    description: 'Motor neural local e gratuito de conversão de texto em fala. Roda em CPU com latência em tempo real e vozes PT-BR reais (pt_BR-faber-medium, cadu, edresson).',
    url: 'https://github.com/OHF-Voice/piper1-gpl',
    phoenixStatus: 'Orquestrado Nativamente',
    endpointDefault: '/api/tts/piper',
    tags: ['piper1-gpl', 'Neural TTS', 'GPL-3.0', 'CPU Fast', 'PT-BR Faber'],
  },
  {
    id: 'llama-cpp',
    name: 'llama.cpp',
    category: 'runtime',
    categoryLabel: 'Runtime de Inferência',
    description: 'Motor C/C++ ultra eficiente para inferência LLM com aceleração Vulkan, ROCm, Metal e CUDA.',
    url: 'https://github.com/ggml-org/llama.cpp',
    phoenixStatus: 'Orquestrado Nativamente',
    endpointDefault: 'http://localhost:8081/v1',
    tags: ['C++', 'Vulkan', 'GGUF', 'Multi-Platform'],
  },
  {
    id: 'vllm',
    name: 'vLLM',
    category: 'runtime',
    categoryLabel: 'Runtime de Inferência',
    description: 'Biblioteca de alto throughput com PagedAttention para gerenciamento eficiente de KV-cache.',
    url: 'https://github.com/vllm-project/vllm',
    phoenixStatus: 'Provedor Suportado',
    endpointDefault: 'http://localhost:8000/v1',
    tags: ['PagedAttention', 'Production', 'High Throughput'],
  },
  {
    id: 'tensorrt-llm',
    name: 'TensorRT-LLM',
    category: 'runtime',
    categoryLabel: 'Runtime de Inferência',
    description: 'Acelerador de inferência da NVIDIA otimizado para Tensor Cores em GPUs RTX/Enterprise.',
    url: 'https://github.com/NVIDIA/TensorRT-LLM',
    phoenixStatus: 'Integração Via API',
    tags: ['NVIDIA', 'Tensor Cores', 'FP8', 'FP16'],
  },
  {
    id: 'mlc-llm',
    name: 'MLC LLM',
    category: 'runtime',
    categoryLabel: 'Runtime de Inferência',
    description: 'Compilador e runtime universal para rodar LLMs via WebGPU e Vulkan em navegadores e edge.',
    url: 'https://github.com/mlc-ai/mlc-llm',
    phoenixStatus: 'Provedor Suportado',
    tags: ['WebGPU', 'Vulkan', 'Cross-Platform'],
  },
  {
    id: 'exllamav2',
    name: 'ExLlamaV2',
    category: 'runtime',
    categoryLabel: 'Runtime de Inferência',
    description: 'Motor EXL2 de alta velocidade projetado para quantização variável rápida em GPUs NVIDIA.',
    url: 'https://github.com/turboderp-org/exllamav2',
    phoenixStatus: 'Provedor Suportado',
    tags: ['EXL2', 'Fast Inference', 'CUDA'],
  },
  {
    id: 'koboldcpp',
    name: 'KoboldCpp',
    category: 'runtime',
    categoryLabel: 'Runtime de Inferência',
    description: 'Fork otimizado do llama.cpp com servidor HTTP OpenAI-compatible e UI de escrita integrada.',
    url: 'https://github.com/LostRuins/koboldcpp',
    phoenixStatus: 'Provedor Suportado',
    endpointDefault: 'http://localhost:5001/v1',
    tags: ['GGUF', 'OpenAI API', 'Standalone'],
  },
  {
    id: 'jan-nano',
    name: 'Jan Nano Engine',
    category: 'runtime',
    categoryLabel: 'Runtime de Inferência',
    description: 'Motor C++ embarcado privativo desenvolvido pela equipe do Jan para dispositivos locais.',
    url: 'https://jan.ai',
    phoenixStatus: 'Provedor Suportado',
    tags: ['Embedded', 'Private', 'Cross-Platform'],
  },
  {
    id: 'apple-mlx',
    name: 'Apple MLX',
    category: 'runtime',
    categoryLabel: 'Runtime de Inferência',
    description: 'Framework de aprendizado profundo otimizado para a arquitetura de memória unificada Apple Silicon.',
    url: 'https://github.com/ml-explore/mlx',
    phoenixStatus: 'Integração Via API',
    tags: ['Apple Silicon', 'Metal', 'Unified Memory'],
  },

  // 2. Servidores de Modelos
  {
    id: 'ollama',
    name: 'Ollama',
    category: 'server',
    categoryLabel: 'Servidor de Modelos',
    description: 'Gerenciador de modelos em background com download automático (Mxf/GGUF) e REST API.',
    url: 'https://ollama.com',
    phoenixStatus: 'Orquestrado Nativamente',
    endpointDefault: 'http://localhost:11434',
    tags: ['CLI', 'REST API', 'GGUF Manager', 'Docker'],
  },
  {
    id: 'localai',
    name: 'LocalAI',
    category: 'server',
    categoryLabel: 'Servidor de Modelos',
    description: 'Substituto drop-in da API da OpenAI rodando 100% local (LLMs, Whisper, SD, Embeddings).',
    url: 'https://localai.io',
    phoenixStatus: 'Provedor Suportado',
    endpointDefault: 'http://localhost:8080/v1',
    tags: ['Drop-in OpenAI', 'Multi-Modal', 'Audio & Text'],
  },
  {
    id: 'llama-server',
    name: 'llama-server (llama.cpp)',
    category: 'server',
    categoryLabel: 'Servidor de Modelos',
    description: 'Servidor C++ nativo do llama.cpp com suporte a streaming, slot allocation e Vulkan offload.',
    url: 'https://github.com/ggml-org/llama.cpp',
    phoenixStatus: 'Orquestrado Nativamente',
    endpointDefault: 'http://localhost:8081/v1',
    tags: ['Native C++', 'Vulkan Split', 'High Performance'],
  },
  {
    id: 'vllm-server',
    name: 'vLLM Server',
    category: 'server',
    categoryLabel: 'Servidor de Modelos',
    description: 'Endpoint de inferência em escala para servidores de produção com suporte a LoRA e multi-GPU.',
    url: 'https://github.com/vllm-project/vllm',
    phoenixStatus: 'Provedor Suportado',
    endpointDefault: 'http://localhost:8000/v1',
    tags: ['OpenAI Endpoint', 'Multi-GPU', 'Enterprise'],
  },
  {
    id: 'tgi',
    name: 'Text Generation Inference (TGI)',
    category: 'server',
    categoryLabel: 'Servidor de Modelos',
    description: 'Servidor de produção da HuggingFace para implantar e servir os maiores LLMs open-source.',
    url: 'https://github.com/huggingface/text-generation-inference',
    phoenixStatus: 'Provedor Suportado',
    endpointDefault: 'http://localhost:8080/v1',
    tags: ['HuggingFace', 'Production', 'FlashAttention'],
  },
  {
    id: 'sglang',
    name: 'SGLang Server',
    category: 'server',
    categoryLabel: 'Servidor de Modelos',
    description: 'Servidor de inferência rápida estruturada com suporte avançado a chamadas de função e JSON.',
    url: 'https://github.com/sgl-project/sglang',
    phoenixStatus: 'Provedor Suportado',
    endpointDefault: 'http://localhost:30000/v1',
    tags: ['Structured Output', 'RadixAttention', 'Fast'],
  },
  {
    id: 'nvidia-nim',
    name: 'NVIDIA NIM',
    category: 'server',
    categoryLabel: 'Servidor de Modelos',
    description: 'Microserviços otimizados em containers para inferência acelerada em nuvem e edge.',
    url: 'https://build.nvidia.com',
    phoenixStatus: 'Integração Via API',
    tags: ['Microservices', 'Enterprise', 'NVIDIA Cloud'],
  },

  // 3. Interfaces Web
  {
    id: 'open-webui',
    name: 'Open WebUI',
    category: 'webui',
    categoryLabel: 'Interface Web',
    description: 'Interface web estilo ChatGPT auto-hospedada com RAG, pesquisa Web SearXNG e suporte multi-usuário.',
    url: 'https://github.com/open-webui/open-webui',
    phoenixStatus: 'Orquestrado Nativamente',
    endpointDefault: 'http://localhost:8010/api',
    tags: ['Docker', 'RAG', 'SearXNG', 'Multi-User'],
  },
  {
    id: 'librechat',
    name: 'LibreChat',
    category: 'webui',
    categoryLabel: 'Interface Web',
    description: 'Clone open-source avançado do ChatGPT integrando múltiplos provedores e suporte a plugins.',
    url: 'https://github.com/danny-avila/LibreChat',
    phoenixStatus: 'Provedor Suportado',
    tags: ['Open Source', 'Plugins', 'Multi-Provider'],
  },
  {
    id: 'anythingllm',
    name: 'AnythingLLM',
    category: 'webui',
    categoryLabel: 'Interface Web',
    description: 'Interface e aplicação focada em RAG enterprise para documentos, PDFs e agentes corporativos.',
    url: 'https://anythingllm.com',
    phoenixStatus: 'Endpoint Conectado',
    endpointDefault: 'http://localhost:3001/api/v1',
    tags: ['RAG Enterprise', 'Documents', 'Agent Hub'],
  },
  {
    id: 'lobechat',
    name: 'LobeChat',
    category: 'webui',
    categoryLabel: 'Interface Web',
    description: 'Interface de chat ultramoderna com mercado de agentes, TTS e suporte a plugins estendidos.',
    url: 'https://lobehub.com',
    phoenixStatus: 'Provedor Suportado',
    tags: ['Agent Market', 'Plugins', 'TTS Voice'],
  },
  {
    id: 'flowise',
    name: 'Flowise AI',
    category: 'webui',
    categoryLabel: 'Interface Web',
    description: 'Construtor visual drag-and-drop no-code para fluxos LangChain e agentes autônomos.',
    url: 'https://flowiseai.com',
    phoenixStatus: 'Integração Via API',
    tags: ['No-Code', 'LangChain', 'Visual Workflows'],
  },
  {
    id: 'big-agi',
    name: 'Big-AGI',
    category: 'webui',
    categoryLabel: 'Interface Web',
    description: 'Plataforma web para engenharia de prompts avançada, enxame de modelos e análise sintética.',
    url: 'https://github.com/enricoros/big-AGI',
    phoenixStatus: 'Provedor Suportado',
    tags: ['Model Swarm', 'Prompt Engineering', 'Web App'],
  },
  {
    id: 'sillytavern',
    name: 'SillyTavern',
    category: 'webui',
    categoryLabel: 'Interface Web',
    description: 'Interface de alta personalização para RPG, personas detalhadas e gerenciamento de mundo.',
    url: 'https://github.com/SillyTavern/SillyTavern',
    phoenixStatus: 'Provedor Suportado',
    tags: ['RP & Personas', 'World Info', 'Granular Control'],
  },
  {
    id: 'chatbox',
    name: 'Chatbox AI',
    category: 'webui',
    categoryLabel: 'Interface Web',
    description: 'Cliente leve e responsivo para desktop e web compatível com múltiplos provedores.',
    url: 'https://chatboxai.app',
    phoenixStatus: 'Provedor Suportado',
    tags: ['Lightweight', 'Cross-Platform', 'Clean UI'],
  },

  // 4. Aplicações Desktop
  {
    id: 'lmstudio',
    name: 'LM Studio',
    category: 'desktop',
    categoryLabel: 'App Desktop',
    description: 'GUI para desktop para descobrir, baixar e executar modelos GGUF locais na GPU com servidor local.',
    url: 'https://lmstudio.ai',
    phoenixStatus: 'Endpoint Conectado',
    endpointDefault: 'http://localhost:1234/v1',
    tags: ['GUI Desktop', 'GGUF Catalog', 'Local Server'],
  },
  {
    id: 'jan',
    name: 'Jan',
    category: 'desktop',
    categoryLabel: 'App Desktop',
    description: 'Alternativa 100% open-source e privada ao LM Studio com motor C++ embarcado e extensões.',
    url: 'https://jan.ai',
    phoenixStatus: 'Endpoint Conectado',
    endpointDefault: 'http://localhost:1337/v1',
    tags: ['100% Open Source', 'Privacy First', 'Extension Support'],
  },
  {
    id: 'gpt4all',
    name: 'GPT4All',
    category: 'desktop',
    categoryLabel: 'App Desktop',
    description: 'Ecossistema desktop para rodar LLMs locais com busca privativa em documentos do computador.',
    url: 'https://gpt4all.io',
    phoenixStatus: 'Provedor Suportado',
    tags: ['Local Docs', 'Privacy', 'Nomic Engine'],
  },
  {
    id: 'msty',
    name: 'Msty',
    category: 'desktop',
    categoryLabel: 'App Desktop',
    description: 'Aplicativo desktop elegante focado em conversas comparativas lado-a-lado e gestão de conhecimento.',
    url: 'https://msty.app',
    phoenixStatus: 'Provedor Suportado',
    tags: ['Side-by-Side', 'Knowledge Base', 'Sleek UI'],
  },
  {
    id: 'cherry-studio',
    name: 'Cherry Studio',
    category: 'desktop',
    categoryLabel: 'App Desktop',
    description: 'Cliente desktop completo projetado para gerenciar múltiplos provedores e modelos simultâneos.',
    url: 'https://github.com/CherryHQ/cherry-studio',
    phoenixStatus: 'Provedor Suportado',
    tags: ['Multi-LLM', 'Desktop App', 'Custom Prompts'],
  },
  {
    id: 'enchanted',
    name: 'Enchanted LLM',
    category: 'desktop',
    categoryLabel: 'App Desktop',
    description: 'Cliente nativo macOS, iOS e iPadOS elegante projetado especificamente para conectar ao Ollama.',
    url: 'https://github.com/AugustDev/enchanted',
    phoenixStatus: 'Provedor Suportado',
    tags: ['Native Apple', 'Ollama Client', 'Swift'],
  },

  // 5. Frameworks de Agentes
  {
    id: 'openai-agents',
    name: 'OpenAI Agents SDK',
    category: 'agent',
    categoryLabel: 'Framework de Agente',
    description: 'SDK oficial da OpenAI para construir agentes autônomos com orquestração de ferramentas e loops.',
    url: 'https://openai.github.io/openai-agents-python/',
    phoenixStatus: 'Integração Via API',
    tags: ['Python SDK', 'Multi-Agent', 'Tools'],
  },
  {
    id: 'langgraph',
    name: 'LangGraph',
    category: 'agent',
    categoryLabel: 'Framework de Agente',
    description: 'Biblioteca para construção de fluxos de agentes cíclicos orientados a grafo de estados.',
    url: 'https://langchain-ai.github.io/langgraph/',
    phoenixStatus: 'Integração Via API',
    tags: ['State Graphs', 'Cyclic Agents', 'Persistence'],
  },
  {
    id: 'crewai',
    name: 'CrewAI',
    category: 'agent',
    categoryLabel: 'Framework de Agente',
    description: 'Framework para criar equipes de agentes com papéis, metas e colaboração autônoma.',
    url: 'https://www.crewai.com',
    phoenixStatus: 'Integração Via API',
    tags: ['Role-Playing', 'Multi-Agent Teams', 'Automation'],
  },
  {
    id: 'autogen',
    name: 'Microsoft AutoGen',
    category: 'agent',
    categoryLabel: 'Framework de Agente',
    description: 'Framework da Microsoft para desenvolvimento de conversas multi-agentes e automação de código.',
    url: 'https://github.com/microsoft/autogen',
    phoenixStatus: 'Integração Via API',
    tags: ['Microsoft', 'Group Chat', 'Code Execution'],
  },
  {
    id: 'semantic-kernel',
    name: 'Semantic Kernel',
    category: 'agent',
    categoryLabel: 'Framework de Agente',
    description: 'SDK da Microsoft para integrar facilmente modelos de linguagem em C#, Python e Java.',
    url: 'https://github.com/microsoft/semantic-kernel',
    phoenixStatus: 'Integração Via API',
    tags: ['Enterprise', 'C# / Python', 'Memory & Plugins'],
  },

  // 6. Plataformas AI OS
  {
    id: 'open-interpreter',
    name: 'Open Interpreter',
    category: 'aios',
    categoryLabel: 'Plataforma AI OS',
    description: 'Interface de linguagem natural que executa código diretamente no terminal e sistema operacional.',
    url: 'https://github.com/OpenInterpreter/open-interpreter',
    phoenixStatus: 'Orquestrado Nativamente',
    tags: ['Terminal OS', 'Code Execution', 'Local Control'],
  },
  {
    id: 'openhands',
    name: 'OpenHands (OpenDevin)',
    category: 'aios',
    categoryLabel: 'Plataforma AI OS',
    description: 'Engenheiro de software autônomo e plataforma de agentes operando em containers isolados.',
    url: 'https://github.com/All-Hands-AI/OpenHands',
    phoenixStatus: 'Orquestrado Nativamente',
    tags: ['Software Engineer', 'Sandbox Docker', 'Autonomous'],
  },
  {
    id: 'devika',
    name: 'Devika AI',
    category: 'aios',
    categoryLabel: 'Plataforma AI OS',
    description: 'Agente de IA open-source capaz de entender instruções de alto nível e criar projetos completos.',
    url: 'https://github.com/stitionai/devika',
    phoenixStatus: 'Integração Via API',
    tags: ['Web Dev', 'Autonomous', 'Planning'],
  },
  {
    id: 'bolt-diy',
    name: 'Bolt.diy',
    category: 'aios',
    categoryLabel: 'Plataforma AI OS',
    description: 'Desenvolvedor web autônomo executado no navegador/container para prototipação instantânea.',
    url: 'https://github.com/stackblitz-labs/bolt.diy',
    phoenixStatus: 'Integração Via API',
    tags: ['Web Builder', 'Container', 'Full-Stack'],
  },
  {
    id: 'continue',
    name: 'Continue.dev',
    category: 'aios',
    categoryLabel: 'Plataforma AI OS',
    description: 'Assistente e autocompletar de código autônomo para VS Code e JetBrains conectado a LLMs locais.',
    url: 'https://www.continue.dev',
    phoenixStatus: 'Provedor Suportado',
    tags: ['VS Code', 'Autocomplete', 'Local LLM'],
  },
];

export const EcosystemView: React.FC<EcosystemViewProps> = ({ 
  providers, 
  onOpenSettings,
  onUpdateProvider,
  onTestProvider,
  hasGeminiKey = true
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showEndpointsPanel, setShowEndpointsPanel] = useState<boolean>(true);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [voiceSearch, setVoiceSearch] = useState<string>('');
  const [voiceLangFilter, setVoiceLangFilter] = useState<string>('all');

  const handleTest = async (providerId: string) => {
    if (!onTestProvider) return;
    setTestingId(providerId);
    await onTestProvider(providerId);
    setTestingId(null);
  };

  const categories = [
    { id: 'all', label: 'Todas as Camadas', icon: <Layers className="w-4 h-4" /> },
    { id: 'runtime', label: '1. Runtimes (Inferência)', icon: <Cpu className="w-4 h-4" /> },
    { id: 'server', label: '2. Servidores de Modelos', icon: <Server className="w-4 h-4" /> },
    { id: 'webui', label: '3. Interfaces Web', icon: <Globe className="w-4 h-4" /> },
    { id: 'desktop', label: '4. Apps Desktop', icon: <Monitor className="w-4 h-4" /> },
    { id: 'agent', label: '5. Frameworks Agentes', icon: <Workflow className="w-4 h-4" /> },
    { id: 'aios', label: '6. Plataformas AI OS', icon: <Terminal className="w-4 h-4" /> },
  ];

  const filteredTools = ECOSYSTEM_TOOLS.filter((tool) => {
    const matchesCategory = selectedCategory === 'all' || tool.category === selectedCategory;
    const matchesSearch = 
      tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.tags.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  return (
    <div id="ecosystem-view-container" className="flex-1 bg-slate-950 text-slate-100 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Top Title Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950/60 to-slate-900 border border-indigo-500/30 rounded-3xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
            <Layers className="w-64 h-64 text-indigo-400" />
          </div>
          
          <div className="relative z-10 space-y-4 max-w-4xl">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Centro de Comando & Arquitetura Unificada 2026</span>
              </span>
              <span className="px-3 py-1 rounded-full text-xs font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                40+ Ferramentas + {providers.length} Endpoints
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-white">
              Arquitetura da Stack, Ecossistema & Gestão de Endpoints
            </h1>

            <p className="text-sm sm:text-base text-slate-300 leading-relaxed">
              Juntamos em um único lugar o <strong>mapeamento completo de ferramentas</strong> (runtimes, servidores, UIs, agentes), a <strong>matriz de benchmarks e testes de campo</strong> e o <strong>painel de controle de conexões ativas</strong>. Configure IP, portas, chaves e pings de qualquer provedor diretamente nesta aba!
            </p>
          </div>
        </div>

        {/* Complete Benchmark & Field Test Results Hub (Successes & Failures) */}
        <BenchmarkSection />

        {/* Unified Endpoint & Provider Control Panel */}
        <div className="bg-slate-900 border border-indigo-500/30 rounded-2xl p-6 shadow-xl space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 bg-indigo-600/20 border border-indigo-500/30 rounded-xl text-indigo-400">
                <Server className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                  <span>Provedores & Endpoints Configurados</span>
                  <span className="text-xs font-mono font-normal px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    {providers.filter(p => p.enabled).length}/{providers.length} Ativos
                  </span>
                </h2>
                <p className="text-xs text-slate-400">
                  Ajuste portas, URLs locais (Ollama, llama-server, LM Studio) e chaves de API com teste de latência em tempo real.
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2 shrink-0">
              <button
                onClick={() => setShowEndpointsPanel(!showEndpointsPanel)}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700 transition-colors"
              >
                {showEndpointsPanel ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                <span>{showEndpointsPanel ? 'Ocultar Painel' : 'Expandir Configurações'}</span>
              </button>
            </div>
          </div>

          {showEndpointsPanel && (
            <div className="space-y-4 pt-2">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {providers.map((p) => (
                  <div
                    key={p.id}
                    className={`border rounded-xl p-4 transition-all ${
                      p.enabled
                        ? 'bg-slate-950 border-slate-800 hover:border-slate-700'
                        : 'bg-slate-950/40 border-slate-800/40 opacity-60'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center space-x-2.5">
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-indigo-400">
                          <Cpu className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <h3 className="font-semibold text-xs text-white">{p.name}</h3>
                            {p.status === 'connected' && (
                              <span className="flex items-center space-x-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                <CheckCircle2 className="w-3 h-3" />
                                <span>{p.latencyMs || 0}ms</span>
                              </span>
                            )}
                            {p.status === 'disconnected' && (
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                Offline
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-slate-400 mt-0.5">
                            {p.models.length > 0 ? `${p.models.length} modelos` : 'Sem modelos'}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <label className="flex items-center space-x-1.5 text-xs text-slate-300 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={p.enabled}
                            onChange={(e) => onUpdateProvider && onUpdateProvider({ ...p, enabled: e.target.checked })}
                            className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-900 w-3.5 h-3.5 cursor-pointer"
                          />
                          <span className="text-[11px]">Ativo</span>
                        </label>

                        {onTestProvider && (
                          <button
                            onClick={() => handleTest(p.id)}
                            disabled={!p.enabled || testingId === p.id}
                            className="flex items-center space-x-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] rounded-lg border border-slate-700 transition-colors disabled:opacity-40 font-medium"
                          >
                            <RefreshCw className={`w-3 h-3 ${testingId === p.id ? 'animate-spin text-indigo-400' : ''}`} />
                            <span>{testingId === p.id ? 'Ping...' : 'Ping'}</span>
                          </button>
                        )}
                      </div>
                    </div>

                    {p.enabled && onUpdateProvider && (
                      <div className="mt-3 pt-3 border-t border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                        <div>
                          <label className="block text-[10px] text-slate-400 mb-1 font-mono">URL Endpoint</label>
                          <input
                            type="text"
                            value={p.baseUrl}
                            onChange={(e) => onUpdateProvider({ ...p, baseUrl: e.target.value })}
                            disabled={p.type === 'gemini'}
                            className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-[11px] text-slate-200 focus:ring-1 focus:ring-indigo-500 font-mono disabled:opacity-50"
                          />
                        </div>
                        <div>
                          <label className="block text-[10px] text-slate-400 mb-1 font-mono">Chave API / Token</label>
                          {p.type === 'gemini' ? (
                            <div className="bg-purple-950/30 border border-purple-800/40 rounded px-2.5 py-1 text-[11px] text-purple-300 font-mono flex items-center justify-between">
                              <span>{hasGeminiKey ? 'Injetada via Secrets' : 'Nenhuma chave'}</span>
                              <Check className="w-3 h-3 text-purple-400" />
                            </div>
                          ) : (
                            <input
                              type="password"
                              value={p.apiKey || ''}
                              onChange={(e) => onUpdateProvider({ ...p, apiKey: e.target.value })}
                              placeholder="sk-..."
                              className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-[11px] text-slate-200 focus:ring-1 focus:ring-indigo-500 font-mono"
                            />
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* MiniCPM-V 2.6 Multimodal Vision & Narration Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-purple-950/70 to-slate-900 border border-purple-500/40 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="p-3 bg-purple-600/30 border border-purple-500/40 rounded-xl text-purple-300">
                <Sparkles className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h2 className="text-base font-bold text-white">MiniCPM-V 2.6 — Visão & Narração Multimodal Nativa</h2>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    OpenBMB / llama-mtmd-cli
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Para o MiniCPM-V conseguir enxergar e narrar imagens em áudio, são necessários <strong>2 arquivos obrigatórios</strong> na pasta <code className="text-purple-300 font-mono">Workstations/Models/Chat/GGUF/</code>:
                </p>
              </div>
            </div>

            <a
              href="https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center space-x-1 text-xs text-purple-400 hover:text-purple-300 font-semibold underline shrink-0"
            >
              <span>Repositório HuggingFace</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
            {/* File 1: mmproj projector */}
            <div className="bg-slate-950/80 p-4 rounded-xl border border-purple-900/50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-purple-300">1. Projetor de Imagem (OBRIGATÓRIO)</span>
                <span className="text-[10px] font-mono bg-purple-950 px-2 py-0.5 rounded text-purple-300 border border-purple-800">
                  ~1.04 GB
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                <code className="text-purple-200 font-mono font-semibold">mmproj-model-f16.gguf</code>: Sem esse projetor o modelo não enxerga os pixels da imagem.
              </p>
              <a
                href="https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf/resolve/main/mmproj-model-f16.gguf?download=true"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center w-full space-x-2 px-3 py-1.5 bg-purple-600/30 hover:bg-purple-600/50 text-purple-200 border border-purple-500/40 rounded-lg text-xs font-semibold transition-all mt-1"
              >
                <span>Baixar mmproj-model-f16.gguf</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            {/* File 2: LLM Weights */}
            <div className="bg-slate-950/80 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-cyan-300">2. Pesos de Linguagem (Q6_K)</span>
                <span className="text-[10px] font-mono bg-slate-900 px-2 py-0.5 rounded text-slate-400 border border-slate-800">
                  ~6.25 GB
                </span>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                <code className="text-cyan-200 font-mono font-semibold">ggml-model-Q6_K.gguf</code> (ou MiniCPM-V-2_6-Q6_K_L.gguf): Pesos do modelo 8B.
              </p>
              <a
                href="https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf/resolve/main/ggml-model-Q6_K.gguf?download=true"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center w-full space-x-2 px-3 py-1.5 bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-200 border border-cyan-500/40 rounded-lg text-xs font-semibold transition-all mt-1"
              >
                <span>Baixar ggml-model-Q6_K.gguf</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </div>

        {/* Piper TTS Neural Voice Engine Banner */}
        <div className="bg-gradient-to-r from-slate-900 via-indigo-950/70 to-slate-900 border border-indigo-500/40 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="p-3 bg-indigo-600/30 border border-indigo-500/40 rounded-xl text-indigo-300">
                <AudioWaveform className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h2 className="text-base font-bold text-white">Piper TTS — Síntese Neural de Voz Gratuita & Local</h2>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    OHF-Voice / piper1-gpl
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Motor neural 100% gratuito executado em CPU local. Sem dependência de APIs pagas ou cotas de nuvem.
                </p>
              </div>
            </div>

            <a
              href="https://github.com/OHF-Voice/piper1-gpl"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300 font-semibold underline shrink-0"
            >
              <span>Repositório GitHub</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          {/* eSpeak-NG Direct Download Box for Windows */}
          <div className="bg-slate-950/90 border border-amber-500/30 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Dependência Obrigatória Windows
                </span>
                <span className="text-xs font-bold text-slate-200">eSpeak-NG (Dados Fonéticos para o Piper)</span>
              </div>
              <a
                href="https://github.com/espeak-ng/espeak-ng/releases"
                target="_blank"
                rel="noreferrer"
                className="text-xs text-amber-400 hover:text-amber-300 font-mono underline flex items-center space-x-1"
              >
                <span>Releases eSpeak-NG</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <p className="text-[11px] text-slate-300 leading-relaxed">
              O Piper precisa dos arquivos de fonemas do eSpeak-NG no Windows (<code className="text-amber-300 font-mono">espeak-ng-data\phontab</code>). Para resolver o erro do eSpeak-NG no Windows e ativar o Piper nativo, baixe e execute o instalador oficial de 64 bits ou copie a pasta <code className="text-amber-300 font-mono">espeak-ng-data</code> para <code className="text-amber-300 font-mono">R:\Phoenix\Workstations\Models\Voice\Piper\</code>.
            </p>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <a
                href="https://github.com/espeak-ng/espeak-ng/releases/download/1.51/espeak-ng-X64.msi"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-2 px-3.5 py-1.5 bg-amber-600/30 hover:bg-amber-600/50 text-amber-200 border border-amber-500/40 rounded-lg text-xs font-semibold transition-all"
              >
                <span>Baixar Instalador Oficial (espeak-ng-X64.msi)</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
              <a
                href="https://github.com/espeak-ng/espeak-ng/releases"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 rounded-lg text-xs transition-all"
              >
                <span>Página Oficial no GitHub</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* Voice Search & Language Filter Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 pb-1 border-t border-slate-800/80">
            <div className="flex flex-wrap items-center gap-1.5 w-full sm:w-auto">
              {[
                { id: 'all', label: 'Todas' },
                { id: 'pt', label: 'Português' },
                { id: 'en', label: 'Inglês' },
                { id: 'es', label: 'Espanhol' },
                { id: 'de', label: 'Alemão' },
                { id: 'fr', label: 'Francês' },
                { id: 'it', label: 'Italiano' },
                { id: 'ru', label: 'Russo' },
                { id: 'zh', label: 'Chinês' },
                { id: 'other', label: 'Outras' },
              ].map((lang) => (
                <button
                  key={lang.id}
                  onClick={() => setVoiceLangFilter(lang.id)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                    voiceLangFilter === lang.id
                      ? 'bg-indigo-600 text-white shadow-sm font-semibold'
                      : 'bg-slate-900/80 hover:bg-slate-800 text-slate-400 border border-slate-800'
                  }`}
                >
                  {lang.label}
                </button>
              ))}
            </div>

            <div className="relative w-full sm:w-64 shrink-0">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Buscar voz, idioma ou modelo..."
                value={voiceSearch}
                onChange={(e) => setVoiceSearch(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
              />
            </div>
          </div>

          {/* Voice Models Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
            {DEFAULT_PIPER_VOICES.filter((v) => {
              const matchesSearch =
                v.name.toLowerCase().includes(voiceSearch.toLowerCase()) ||
                v.language.toLowerCase().includes(voiceSearch.toLowerCase()) ||
                v.description.toLowerCase().includes(voiceSearch.toLowerCase()) ||
                v.onnxModel.toLowerCase().includes(voiceSearch.toLowerCase());

              const langCode = v.language.toLowerCase();
              let matchesLang = true;
              if (voiceLangFilter === 'pt') matchesLang = langCode.startsWith('pt');
              else if (voiceLangFilter === 'en') matchesLang = langCode.startsWith('en');
              else if (voiceLangFilter === 'es') matchesLang = langCode.startsWith('es');
              else if (voiceLangFilter === 'de') matchesLang = langCode.startsWith('de');
              else if (voiceLangFilter === 'fr') matchesLang = langCode.startsWith('fr');
              else if (voiceLangFilter === 'it') matchesLang = langCode.startsWith('it');
              else if (voiceLangFilter === 'ru') matchesLang = langCode.startsWith('ru') || langCode.startsWith('uk');
              else if (voiceLangFilter === 'zh') matchesLang = langCode.startsWith('zh') || langCode.startsWith('ko');
              else if (voiceLangFilter === 'other') {
                matchesLang = !['pt', 'en', 'es', 'de', 'fr', 'it', 'ru', 'uk', 'zh', 'ko'].some((prefix) => langCode.startsWith(prefix));
              }

              return matchesSearch && matchesLang;
            }).map((v) => (
              <div key={v.id} className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800 space-y-2 flex flex-col justify-between hover:border-indigo-500/30 transition-all">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-indigo-300">{v.name}</span>
                    <span className="text-[10px] font-mono bg-slate-900 px-1.5 py-0.5 rounded text-slate-400 border border-slate-800">
                      {v.quality} ({v.sampleRate}Hz)
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2 mt-1">{v.description}</p>
                </div>

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-1">
                  <span className="text-[10px] font-mono text-slate-500 truncate">{v.onnxModel}</span>
                  
                  <div className="flex items-center space-x-1.5 shrink-0">
                    {v.downloadUrl && (
                      <a
                        href={v.downloadUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1 text-slate-400 hover:text-white bg-slate-900 border border-slate-800 rounded text-[10px]"
                        title="Baixar Modelo ONNX no HuggingFace"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                    <button
                      onClick={() => synthesizeAndPlayPiper(`Testando voz neural ${v.name} com o Piper TTS local.`, { voiceId: v.id })}
                      className="flex items-center space-x-1 px-2 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-200 border border-indigo-500/40 rounded text-[10px] font-semibold transition-all"
                    >
                      <Volume2 className="w-3 h-3 text-indigo-400" />
                      <span>Testar Voz</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Phoenix Engine Bridge & Terminal Deck Panel */}
        <div className="bg-slate-900 border border-indigo-500/30 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center space-x-2.5">
              <Terminal className="w-5 h-5 text-emerald-400" />
              <div>
                <h2 className="text-base font-bold text-white">Terminal Bridge — Phoenix Aviary &lt;--&gt; Phoenix Engine</h2>
                <p className="text-xs text-slate-400">Comunicação bidirecional direta com o orquestrador local na porta 8000 (api_server.py)</p>
              </div>
            </div>

            <div className="flex items-center space-x-1.5 text-xs">
              <button
                onClick={() => {
                  fetch('/api/engine/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: 'status' }),
                  })
                  .then(r => r.json())
                  .then(d => alert(d.output || d.error || 'Resposta recebida.'));
                }}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-mono font-medium border border-slate-700"
              >
                Status
              </button>
              <button
                onClick={() => {
                  fetch('/api/engine/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: 'manager analyze' }),
                  })
                  .then(r => r.json())
                  .then(d => alert(d.output || d.error || 'Análise iniciada.'));
                }}
                className="px-2.5 py-1 bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 rounded-lg text-xs font-mono font-medium border border-indigo-500/40"
              >
                Analisar Maquina
              </button>
            </div>
          </div>

          <div className="bg-slate-950 rounded-xl p-4 border border-slate-800 font-mono text-xs space-y-2">
            <div className="text-slate-400 text-[11px] pb-2 border-b border-slate-800/80 flex items-center justify-between">
              <span>◆ Ponte Bidirecional Ativa (http://localhost:8000/api/command)</span>
              <span className="text-emerald-400 font-bold">● OK</span>
            </div>
            <p className="text-slate-300 leading-relaxed">
              Use comandos no Terminal Bridge: <code className="text-amber-300">status</code> (leitura de hardware), <code className="text-amber-300">models</code> (modelos locais), <code className="text-amber-300">manager analyze</code> (análise do Resident Manager), <code className="text-amber-300">validate</code> (verificação de ambiente).
            </p>
          </div>
        </div>

        {/* Strategic Distinction Card: Why Phoenix Engine is Different */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5">
          <div className="flex items-center space-x-3 border-b border-slate-800 pb-4">
            <div className="p-2.5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl text-white shadow-lg shadow-indigo-500/20">
              <Zap className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">O Papel Único da Phoenix Engine no Ecossistema</h2>
              <p className="text-xs text-slate-400">
                A Phoenix não compete como "mais um frontend" — ela atua como o **Orquestrador Residente** e **Provisionador Inteligente** da sua máquina.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1.5">
              <div className="flex items-center space-x-2 text-indigo-400 font-bold">
                <ShieldCheck className="w-4 h-4" />
                <span>1. Provisionador Inteligente</span>
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Detecta automaticamente GPU (RX 580 Vulkan, RTX CUDA, Apple Silicon), RAM, VRAM e caminhos do sistema para preparar o ambiente sem atrito.
              </p>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1.5">
              <div className="flex items-center space-x-2 text-purple-400 font-bold">
                <Workflow className="w-4 h-4" />
                <span>2. Orquestrador Multilayer</span>
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Subordina e gerencia Ollama, llama.cpp, ComfyUI, Whisper, SearXNG e Open WebUI como serviços residentes de segundo plano.
              </p>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1.5">
              <div className="flex items-center space-x-2 text-cyan-400 font-bold">
                <Code2 className="w-4 h-4" />
                <span>3. Mission Kernel</span>
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Trata prompts complexos como missões estruturadas com planejamento, validação de segurança, auditoria e execução isolada.
              </p>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-1.5">
              <div className="flex items-center space-x-2 text-emerald-400 font-bold">
                <Activity className="w-4 h-4" />
                <span>4. Camada Unificada</span>
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">
                Expõe todos os motores sob uma API unificada compatível com OpenAI, permitindo alternar entre nuvem e hardware local instantaneamente.
              </p>
            </div>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 bg-slate-900 p-4 rounded-2xl border border-slate-800">
          
          {/* Search Bar */}
          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar por nome, tag ou motor..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          {/* Quick Configure Endpoint Button */}
          <button
            onClick={onOpenSettings}
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/30 transition-all shrink-0 w-full md:w-auto justify-center"
          >
            <Server className="w-4 h-4" />
            <span>Gerenciar Conexões & Endpoints</span>
          </button>
        </div>

        {/* Category Tabs */}
        <div className="flex items-center space-x-2 overflow-x-auto pb-2 scrollbar-thin">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`flex items-center space-x-2 px-3.5 py-2 rounded-xl text-xs font-medium whitespace-nowrap transition-all ${
                selectedCategory === cat.id
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {cat.icon}
              <span>{cat.label}</span>
            </button>
          ))}
        </div>

        {/* Tool Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredTools.map((tool) => {
            const isEndpointProvider = providers.some(p => p.baseUrl === tool.endpointDefault || p.type.includes(tool.id));

            return (
              <div
                key={tool.id}
                id={`ecosystem-card-${tool.id}`}
                className="bg-slate-900 border border-slate-800/80 hover:border-slate-700 rounded-2xl p-5 shadow-lg flex flex-col justify-between space-y-4 group transition-all"
              >
                <div className="space-y-3">
                  
                  {/* Card Top Header */}
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-mono uppercase tracking-wider text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                        {tool.categoryLabel}
                      </span>
                      <h3 className="text-base font-bold text-white mt-1 group-hover:text-indigo-300 transition-colors">
                        {tool.name}
                      </h3>
                    </div>

                    <a
                      href={tool.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
                      title="Ver repositório/site oficial"
                    >
                      <ArrowUpRight className="w-4 h-4" />
                    </a>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-slate-400 leading-relaxed min-h-[48px]">
                    {tool.description}
                  </p>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {tool.tags.map((tag, i) => (
                      <span
                        key={i}
                        className="text-[10px] font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>

                </div>

                {/* Card Footer Info & Connect Action */}
                <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-1.5 text-[11px]">
                    <CheckCircle2 className={`w-3.5 h-3.5 ${
                      tool.phoenixStatus === 'Orquestrado Nativamente'
                        ? 'text-emerald-400'
                        : tool.phoenixStatus === 'Endpoint Conectado'
                        ? 'text-cyan-400'
                        : 'text-indigo-400'
                    }`} />
                    <span className="text-slate-300 font-medium">{tool.phoenixStatus}</span>
                  </div>

                  {tool.endpointDefault && (
                    <button
                      onClick={onOpenSettings}
                      className="text-[10px] font-mono text-indigo-300 hover:text-indigo-200 bg-indigo-950/50 hover:bg-indigo-900/60 border border-indigo-800/50 px-2.5 py-1 rounded-lg transition-colors"
                    >
                      Testar Ping
                    </button>
                  )}
                </div>

              </div>
            );
          })}
        </div>

      </div>
    </div>
  );
};
