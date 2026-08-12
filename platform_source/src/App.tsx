import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { ProviderSettingsModal } from './components/ProviderSettingsModal';
import { ParametersDrawer } from './components/ParametersDrawer';
import { ChatView } from './components/ChatView';
import { ArenaView } from './components/ArenaView';
import { ModelHubView } from './components/ModelHubView';
import { VramCalculatorView } from './components/VramCalculatorView';
import { EcosystemView } from './components/EcosystemView';
import { ManualModal } from './components/ManualModal';

import { 
  ProviderConfig, 
  Conversation, 
  ChatMessage, 
  ChatParameters, 
  ModelInfo, 
  ArenaSlot,
  AttachedFile 
} from './types';
import { SYSTEM_PROMPT_PRESETS } from './data/systemPrompts';

// Initial default providers configuration across the full AI Stack
const DEFAULT_PROVIDERS: ProviderConfig[] = [
  {
    id: 'gemini-main',
    name: 'Google Gemini Cloud API',
    type: 'gemini',
    baseUrl: 'https://generativelanguage.googleapis.com',
    enabled: true,
    status: 'connected',
    latencyMs: 120,
    models: ['gemini-3.6-flash', 'gemini-3.1-pro-preview', 'gemini-3.1-flash-lite'],
  },
  {
    id: 'piper-tts-local',
    name: 'Piper TTS Neural (Local / CPU)',
    type: 'piper-tts',
    baseUrl: '/api/tts/piper',
    enabled: true,
    status: 'connected',
    latencyMs: 15,
    models: ['pt_BR-faber-medium', 'pt_BR-cadu-medium', 'pt_BR-edresson-low', 'en_US-lessac-high', 'en_US-ryan-medium'],
  },
  {
    id: 'ollama-local',
    name: 'Ollama (Servidor Local)',
    type: 'ollama',
    baseUrl: 'http://localhost:11434',
    enabled: true,
    status: 'disconnected',
    models: [
      'deepseek-r1:8b', 
      'llama3.3:70b', 
      'llama3.1:8b', 
      'qwen2.5-coder:32b', 
      'qwen2.5:72b', 
      'phi4', 
      'mistral-nemo', 
      'codestral', 
      'command-r-plus', 
      'llama3.2-vision', 
      'smollm2:1.7b',
      'granite3.1-dense:8b'
    ],
  },
  {
    id: 'lmstudio-local',
    name: 'LM Studio (Servidor Local)',
    type: 'lmstudio',
    baseUrl: 'http://localhost:1234/v1',
    enabled: true,
    status: 'disconnected',
    models: [
      'deepseek-r1-distill-qwen-8b', 
      'qwen2.5-coder-32b-gguf', 
      'phi-4-gguf', 
      'llama-3.3-70b-gguf',
      'mistral-nemo-12b-gguf',
      'gemma-2-9b-it'
    ],
  },
  {
    id: 'llama-server-local',
    name: 'llama-server / llama.cpp',
    type: 'llama-server',
    baseUrl: 'http://localhost:8081/v1',
    enabled: true,
    status: 'disconnected',
    models: ['mistral-7b-instruct-v0.2.Q4_K_M', 'qwen2.5-7b-instruct-q4'],
  },
  {
    id: 'vllm-local',
    name: 'vLLM Server (PagedAttention)',
    type: 'vllm',
    baseUrl: 'http://localhost:8000/v1',
    enabled: false,
    status: 'disconnected',
    models: ['meta-llama/Llama-3.1-8B-Instruct', 'Qwen/Qwen2.5-72B-Instruct'],
  },
  {
    id: 'localai-server',
    name: 'LocalAI Server',
    type: 'localai',
    baseUrl: 'http://localhost:8080/v1',
    enabled: false,
    status: 'disconnected',
    models: ['gpt-3.5-turbo', 'whisper-1'],
  },
  {
    id: 'koboldcpp-server',
    name: 'KoboldCpp Server',
    type: 'koboldcpp',
    baseUrl: 'http://localhost:5001/v1',
    enabled: false,
    status: 'disconnected',
    models: ['kobold-model-gguf'],
  },
  {
    id: 'jan-server',
    name: 'Jan Local Engine Server',
    type: 'jan',
    baseUrl: 'http://localhost:1337/v1',
    enabled: false,
    status: 'disconnected',
    models: ['mistral-ins-7b-q4'],
  },
  {
    id: 'openwebui-gateway',
    name: 'Open WebUI Gateway Proxy',
    type: 'open-webui',
    baseUrl: 'http://localhost:8010/api',
    enabled: false,
    status: 'disconnected',
    models: ['openwebui-pipeline-model'],
  },
  {
    id: 'anythingllm-server',
    name: 'AnythingLLM Enterprise RAG',
    type: 'anythingllm',
    baseUrl: 'http://localhost:3001/api/v1',
    enabled: false,
    status: 'disconnected',
    models: ['anythingllm-workspace-agent'],
  },
  {
    id: 'openai-cloud',
    name: 'OpenAI API Cloud',
    type: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    enabled: false,
    status: 'disconnected',
    models: ['gpt-4o', 'gpt-4o-mini', 'o1-preview'],
  },
  {
    id: 'anthropic-cloud',
    name: 'Anthropic Claude Cloud',
    type: 'anthropic',
    baseUrl: 'https://api.anthropic.com',
    enabled: false,
    status: 'disconnected',
    models: ['claude-3-5-sonnet', 'claude-3-haiku'],
  },
];

// Initial default parameters
const DEFAULT_PARAMETERS: ChatParameters = {
  temperature: 0.7,
  topP: 0.95,
  topK: 40,
  maxTokens: 4096,
  contextWindow: 16384,
  repeatPenalty: 1.1,
  systemInstruction: SYSTEM_PROMPT_PRESETS[0].prompt,
  showThinking: true,
};

// PHX-FIX: Helper seguro de persistência de conversas no localStorage.
// Evita o estouro de cota (QuotaExceededError) quando há imagens base64 ou
// histórico extenso de mensagens na memória.
function safeSaveConversations(convs: Conversation[]) {
  try {
    localStorage.setItem('app_conversations', JSON.stringify(convs));
  } catch (err) {
    console.warn('localStorage quota excedido. Omitindo imagens/arquivos base64 do cache local:', err);
    try {
      // 1ª Tentativa: Omitir imagens base64 pesadas e anexos extensos do cache do localStorage
      const prunedConvs = convs.map((c) => ({
        ...c,
        messages: c.messages.map((m) => ({
          ...m,
          image: m.image && m.image.length > 1000 ? undefined : m.image,
          files: m.files?.map((f) => ({
            ...f,
            content: f.content && f.content.length > 1000 ? '[Conteúdo omitido no cache local]' : f.content,
          })),
        })),
      }));
      localStorage.setItem('app_conversations', JSON.stringify(prunedConvs));
    } catch {
      try {
        // 2ª Tentativa: Manter apenas as últimas 5 conversas e últimas 20 mensagens em texto
        const recentConvs = convs.slice(0, 5).map((c) => ({
          ...c,
          messages: c.messages.slice(-20).map((m) => ({
            ...m,
            image: undefined,
            files: undefined,
          })),
        }));
        localStorage.setItem('app_conversations', JSON.stringify(recentConvs));
      } catch {
        // Falha silenciosa se o armazenamento do navegador estiver completamente bloqueado
      }
    }
  }
}

// PHX-NEW: id fixo da thread onde as respostas do Resident (Phoenix Engine, porta 8000)
// aparecem quando ele decide responder direto (ex: "diga oi!") em vez de rodar
// uma missão de provisionamento.
const RESIDENT_CONVERSATION_ID = 'resident-thread';

export default function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'arena' | 'hub' | 'vram' | 'stack' | 'settings'>('chat');
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isParamsOpen, setIsParamsOpen] = useState<boolean>(false);
  const [isManualOpen, setIsManualOpen] = useState<boolean>(false);
  
  const [providers, setProviders] = useState<ProviderConfig[]>(() => {
    try {
      const saved = localStorage.getItem('app_providers');
      return saved ? JSON.parse(saved) : DEFAULT_PROVIDERS;
    } catch {
      return DEFAULT_PROVIDERS;
    }
  });

  const [parameters, setParameters] = useState<ChatParameters>(() => {
    try {
      const saved = localStorage.getItem('app_parameters');
      return saved ? JSON.parse(saved) : DEFAULT_PARAMETERS;
    } catch {
      return DEFAULT_PARAMETERS;
    }
  });

  const [conversations, setConversations] = useState<Conversation[]>(() => {
    try {
      const saved = localStorage.getItem('app_conversations');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => {
    try {
      const savedConvs = localStorage.getItem('app_conversations');
      if (savedConvs) {
        const parsed: Conversation[] = JSON.parse(savedConvs);
        return parsed[0]?.id || null;
      }
    } catch {
      // ignore parse error
    }
    return null;
  });

  const [selectedModelId, setSelectedModelId] = useState<string>('gemini-3.6-flash');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [hasGeminiKey, setHasGeminiKey] = useState<boolean>(true);
  const [engineOnline, setEngineOnline] = useState<boolean>(false);
  const [telemetry, setTelemetry] = useState<{
    gpuTempC?: number;
    vramUsedGb?: number;
    vramTotalGb?: number;
    cpuLoadPct?: number;
  }>({
    gpuTempC: 52,
    vramUsedGb: 4.8,
    vramTotalGb: 8.0,
    cpuLoadPct: 18,
  });

  // Save state to localStorage safely
  useEffect(() => {
    try {
      localStorage.setItem('app_providers', JSON.stringify(providers));
    } catch {
      // Ignore quota error for providers
    }
  }, [providers]);

  useEffect(() => {
    try {
      localStorage.setItem('app_parameters', JSON.stringify(parameters));
    } catch {
      // Ignore quota error for parameters
    }
  }, [parameters]);

  useEffect(() => {
    safeSaveConversations(conversations);
  }, [conversations]);

  // Aggregate available models from enabled providers
  const availableModels: ModelInfo[] = React.useMemo(() => {
    const list: ModelInfo[] = [];

    providers.forEach((p) => {
      if (!p.enabled) return;

      p.models.forEach((m) => {
        list.push({
          id: m,
          name: m,
          providerType: p.type,
          providerId: p.id,
          contextWindow: p.type === 'gemini' ? 1000000 : 128000,
          supportsThinking: m.includes('deepseek-r1') || m.includes('r1') || m.includes('reasoner'),
        });
      });
    });

    // Fallback if empty
    if (list.length === 0) {
      list.push({
        id: 'gemini-3.6-flash',
        name: 'gemini-3.6-flash',
        providerType: 'gemini',
        providerId: 'gemini-main',
        contextWindow: 1000000,
      });
    }

    return list;
  }, [providers]);

  // Check health & live telemetry on initial load & polling
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/api/health');
        const data = await res.json();
        if (data.hasGeminiKey !== undefined) {
          setHasGeminiKey(data.hasGeminiKey);
        }
        if (data.engineOnline !== undefined) {
          const isOnline = Boolean(data.engineOnline);
          setEngineOnline(isOnline);
          
          if (isOnline) {
            try {
              const stateRes = await fetch('/api/engine/state');
              if (stateRes.ok) {
                const stateData = await stateRes.json();
                if (stateData) {
                  const t = stateData.telemetry || stateData.metrics || stateData || {};
                  const hw = stateData.hardware || stateData || {};

                  const isNum = (v: unknown): v is number => typeof v === 'number' && !Number.isNaN(v);

                  const rawGpuTemp = t.gpu_temp ?? t.gpu_temperature_celsius ?? t.gpuTempC ?? t.gpuTemp ?? t.temperature ?? stateData.gpuTemp;
                  const rawCpuLoad = t.cpu_usage ?? t.cpu_load_pct ?? t.cpuLoadPct ?? stateData.cpuLoadPct;

                  let rawVramUsed = t.gpu_vram_used ?? t.vram_used_mb ?? t.vramUsedGb ?? t.vram_used ?? stateData.vramUsedGb;
                  if (isNum(rawVramUsed) && rawVramUsed > 128) {
                    rawVramUsed = rawVramUsed / 1024;
                  }

                  let rawVramTotal = hw.vram_mb ?? hw.vram_total_mb ?? t.vramTotalGb ?? t.vram_total ?? stateData.vramTotalGb;
                  if (isNum(rawVramTotal) && rawVramTotal > 128) {
                    rawVramTotal = rawVramTotal / 1024;
                  }

                  const gpuTempC = isNum(rawGpuTemp) ? rawGpuTemp : undefined;
                  const cpuLoadPct = isNum(rawCpuLoad) ? rawCpuLoad : undefined;
                  const vramUsedGb = isNum(rawVramUsed) ? rawVramUsed : undefined;
                  const vramTotalGb = isNum(rawVramTotal) ? rawVramTotal : undefined;

                  if (gpuTempC !== undefined || cpuLoadPct !== undefined || vramUsedGb !== undefined) {
                    setTelemetry({ gpuTempC, vramUsedGb, vramTotalGb, cpuLoadPct });
                  } else {
                    setTelemetry(null);
                  }
                }
              } else {
                setTelemetry(null);
              }
            } catch {
              setTelemetry(null);
            }
          }
        }
      } catch {
        setEngineOnline(false);
      }
    };
    checkHealth();
    const timer = setInterval(checkHealth, 4000);
    return () => clearInterval(timer);
  }, []);

  // PHX-NEW: poll de mensagens que o Resident (Phoenix Engine, porta 8000)
  // decidiu enviar direto pro chat (ex: o usuário executou um comando de conversa no terminal)
  useEffect(() => {
    const pollResidentMessages = () => {
      fetch('/api/chat/pending')
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (!data || !Array.isArray(data.messages) || data.messages.length === 0) return;

          setConversations((prev) => {
            const existing = prev.find((c) => c.id === RESIDENT_CONVERSATION_ID);
            const newMessages: ChatMessage[] = data.messages.map((m: any) => ({
              id: Math.random().toString(36).substring(2, 9),
              role: 'assistant',
              content: m.content || '',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              modelId: m.model || 'phoenix-resident',
              providerType: 'custom',
            }));

            if (existing) {
              return prev.map((c) =>
                c.id === RESIDENT_CONVERSATION_ID
                  ? { ...c, messages: [...c.messages, ...newMessages], updatedAt: new Date().toLocaleTimeString() }
                  : c
              );
            }

            const residentConv: Conversation = {
              id: RESIDENT_CONVERSATION_ID,
              title: 'Resident',
              modelId: 'phoenix-resident',
              providerType: 'custom',
              createdAt: new Date().toLocaleDateString(),
              updatedAt: new Date().toLocaleTimeString(),
              messages: newMessages,
              parameters: { ...parameters },
            };
            return [residentConv, ...prev];
          });
        })
        .catch(() => {});
    };
    pollResidentMessages();
    const timer = setInterval(pollResidentMessages, 7000);
    return () => clearInterval(timer);
  }, [parameters]);

  // Handler to update a provider's configuration
  const handleUpdateProvider = (updated: ProviderConfig) => {
    setProviders((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  // Handler to test provider ping
  const handleTestProvider = async (providerId: string) => {
    const provider = providers.find((p) => p.id === providerId);
    if (!provider) return;

    try {
      const response = await fetch('/api/proxy/ping', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          providerType: provider.type,
          baseUrl: provider.baseUrl,
          apiKey: provider.apiKey,
        }),
      });

      const data = await response.json();

      setProviders((prev) =>
        prev.map((p) => {
          if (p.id === providerId) {
            return {
              ...p,
              status: data.online ? 'connected' : 'disconnected',
              latencyMs: data.latencyMs || 0,
              models: data.models && data.models.length > 0 ? data.models : p.models,
              lastChecked: new Date().toLocaleTimeString(),
            };
          }
          return p;
        })
      );
    } catch {
      setProviders((prev) =>
        prev.map((p) => (p.id === providerId ? { ...p, status: 'error' } : p))
      );
    }
  };

  // Scan all enabled providers for active models automatically
  const handleScanAllProviders = async () => {
    setIsScanning(true);
    try {
      // 1. Query Phoenix Engine & Local Runtimes model scanner endpoint
      const engineRes = await fetch('/api/engine/models').catch(() => null);
      if (engineRes && engineRes.ok) {
        const trackedData = await engineRes.json().catch(() => null);
        if (trackedData && trackedData.allDownloadedModels && trackedData.allDownloadedModels.length > 0) {
          setProviders((prev) =>
            prev.map((p) => {
              if (p.type === 'ollama' && trackedData.ollamaModels?.length > 0) {
                const merged = Array.from(new Set([...p.models, ...trackedData.ollamaModels]));
                return { ...p, models: merged, status: 'connected' };
              }
              if (p.type === 'lmstudio' && trackedData.lmstudioModels?.length > 0) {
                const merged = Array.from(new Set([...p.models, ...trackedData.lmstudioModels]));
                return { ...p, models: merged, status: 'connected' };
              }
              if (p.type === 'llama-server' && trackedData.llamaServerModels?.length > 0) {
                const merged = Array.from(new Set([...p.models, ...trackedData.llamaServerModels]));
                return { ...p, models: merged, status: 'connected' };
              }
              return p;
            })
          );
        }
      }

      // 2. Ping enabled providers to verify connections
      await Promise.all(
        providers.filter((p) => p.enabled).map((p) => handleTestProvider(p.id))
      );
    } catch {
      // ignore scan error
    } finally {
      setIsScanning(false);
    }
  };

  // Run initial auto-detection scan on mount
  useEffect(() => {
    handleScanAllProviders();
  }, []);

  // Create new conversation
  const handleNewConversation = () => {
    const newConv: Conversation = {
      id: Math.random().toString(36).substring(2, 9),
      title: 'Nova Conversa IA',
      modelId: selectedModelId,
      providerType: availableModels.find((m) => m.id === selectedModelId)?.providerType || 'gemini',
      createdAt: new Date().toLocaleDateString(),
      updatedAt: new Date().toLocaleTimeString(),
      messages: [],
      parameters: { ...parameters },
    };

    setConversations((prev) => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
  };

  // Delete conversation
  const handleDeleteConversation = (id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeConversationId === id) {
      setActiveConversationId(null);
    }
  };

  // Active conversation object
  const activeConversation = conversations.find((c) => c.id === activeConversationId) || null;

  // Send message
  const handleSendMessage = async (text: string, files: AttachedFile[]) => {
    let convId = activeConversationId;
    let convList = [...conversations];

    if (!convId || !activeConversation) {
      const newConv: Conversation = {
        id: Math.random().toString(36).substring(2, 9),
        title: text.slice(0, 30) || 'Nova Conversa IA',
        modelId: selectedModelId,
        providerType: availableModels.find((m) => m.id === selectedModelId)?.providerType || 'gemini',
        createdAt: new Date().toLocaleDateString(),
        updatedAt: new Date().toLocaleTimeString(),
        messages: [],
        parameters: { ...parameters },
      };
      convList = [newConv, ...convList];
      convId = newConv.id;
      setActiveConversationId(newConv.id);
    }

    const userMsg: ChatMessage = {
      id: Math.random().toString(36).substring(2, 9),
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      files,
      image: files.find((f) => f.isImage)?.content,
    };

    const targetConv = convList.find((c) => c.id === convId)!;
    const updatedMessages = [...targetConv.messages, userMsg];

    setConversations(
      convList.map((c) => (c.id === convId ? { ...c, messages: updatedMessages, title: c.title === 'Nova Conversa IA' ? text.slice(0, 30) : c.title } : c))
    );

    setIsLoading(true);

    // PHX-NEW: Check if user prompt requests image generation
    const isImageIntent = (
      /\b(cria|crie|gerar|gera|desenha|desenhe|make|create|generate|draw)\b.*\b(imagem|foto|arte|desenho|ilusalcao|ilustração|image|picture|photo|avatar|logo)\b/i.test(text) ||
      /\b(imagem|foto|arte|desenho)\s+(de|da|do|cyberpunk|cyberpink|phoenix)\b/i.test(text) ||
      text.toLowerCase().startsWith('cria uma imagem') ||
      text.toLowerCase().startsWith('crie uma imagem') ||
      text.toLowerCase().startsWith('gerar imagem') ||
      text.toLowerCase().startsWith('gera uma imagem') ||
      text.toLowerCase().startsWith('desenhe ')
    );

    if (isImageIntent) {
      try {
        const imgRes = await fetch('/api/engine/generate-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: text }),
        });
        const imgData = await imgRes.json();
        if (imgRes.ok && imgData.imageUrl) {
          const assistantMsg: ChatMessage = {
            id: Math.random().toString(36).substring(2, 9),
            role: 'assistant',
            content: `🎨 **Imagem renderizada com sucesso!**\n\n**Prompt:** *"${imgData.prompt || text}"*\n\n**Motor de Renderização:** \`${imgData.engine || 'Phoenix Visual Engine (SD/FLUX)'}\``,
            image: imgData.imageUrl,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            modelId: 'Phoenix Visual Engine (Diffusers / FLUX)',
            providerType: 'llama-server',
          };

          setConversations((prev) =>
            prev.map((c) =>
              c.id === convId ? { ...c, messages: [...updatedMessages, assistantMsg] } : c
            )
          );
          setIsLoading(false);
          return;
        }
      } catch (imgErr) {
        console.warn('Fallback para LLM de texto pois a geração visual falhou:', imgErr);
      }
    }

    const activeModelObj = availableModels.find((m) => m.id === selectedModelId);
    const providerObj = providers.find((p) => p.id === activeModelObj?.providerId) || providers[0];

    try {
      let endpoint = '/api/gemini/chat';
      let requestPayload: any = {
        model: selectedModelId,
        messages: updatedMessages,
        systemInstruction: parameters.systemInstruction,
        temperature: parameters.temperature,
        topP: parameters.topP,
        topK: parameters.topK,
        maxTokens: parameters.maxTokens,
      };

      if (providerObj.type !== 'gemini') {
        endpoint = '/api/proxy/chat';
        requestPayload = {
          providerType: providerObj.type,
          baseUrl: providerObj.baseUrl,
          apiKey: providerObj.apiKey,
          model: selectedModelId,
          messages: updatedMessages,
          systemInstruction: parameters.systemInstruction,
          temperature: parameters.temperature,
          maxTokens: parameters.maxTokens,
        };
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload),
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(data.error || 'Erro ao comunicar com o provedor');
      }

      let responseText = data.text || '';
      let thinkingText = '';

      // Extract <think> reasoning if model is DeepSeek-R1 style
      const thinkMatch = responseText.match(/<think>([\s\S]*?)<\/think>/i);
      if (thinkMatch) {
        thinkingText = thinkMatch[1].trim();
        responseText = responseText.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
      }

      const assistantMsg: ChatMessage = {
        id: Math.random().toString(36).substring(2, 9),
        role: 'assistant',
        content: responseText,
        thinking: thinkingText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        modelId: selectedModelId,
        providerType: providerObj.type,
        metrics: data.usage,
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId ? { ...c, messages: [...updatedMessages, assistantMsg] } : c
        )
      );
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: Math.random().toString(36).substring(2, 9),
        role: 'assistant',
        content: 'Falha ao obter resposta do modelo.',
        error: err.message || 'Verifique se o servidor local (Ollama / LM Studio) está rodando.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        modelId: selectedModelId,
      };

      setConversations((prev) =>
        prev.map((c) =>
          c.id === convId ? { ...c, messages: [...updatedMessages, errorMsg] } : c
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Regenerate last response
  const handleRegenerate = async () => {
    if (!activeConversation || activeConversation.messages.length === 0) return;
    const lastUserMsgIndex = [...activeConversation.messages].reverse().findIndex((m) => m.role === 'user');
    if (lastUserMsgIndex === -1) return;

    const actualUserIndex = activeConversation.messages.length - 1 - lastUserMsgIndex;
    const trimmedMsgs = activeConversation.messages.slice(0, actualUserIndex + 1);

    setConversations((prev) =>
      prev.map((c) => (c.id === activeConversation.id ? { ...c, messages: trimmedMsgs } : c))
    );

    const lastUserMsg = trimmedMsgs[trimmedMsgs.length - 1];
    await handleSendMessage(lastUserMsg.content, lastUserMsg.files || []);
  };

  // Execute Arena comparison
  const handleExecuteArena = async (
    arenaSlots: ArenaSlot[],
    prompt: string,
    onUpdateSlots: (updatedSlots: ArenaSlot[]) => void
  ) => {
    setIsLoading(true);

    // Set all slots to loading first
    onUpdateSlots(
      arenaSlots.map((s) => ({
        ...s,
        isLoading: true,
        currentResponse: '',
        thinking: undefined,
        error: undefined,
        metrics: undefined,
      }))
    );

    const updatedSlotsPromises = arenaSlots.map(async (slot) => {
      const modelObj = availableModels.find((m) => m.id === slot.modelId);
      const providerObj = providers.find((p) => p.id === modelObj?.providerId) || providers[0];

      try {
        let endpoint = '/api/gemini/chat';
        let payload: any = {
          model: slot.modelId,
          messages: [{ role: 'user', text: prompt }],
          systemInstruction: parameters.systemInstruction,
          temperature: parameters.temperature,
        };

        if (providerObj.type !== 'gemini') {
          endpoint = '/api/proxy/chat';
          payload = {
            providerType: providerObj.type,
            baseUrl: providerObj.baseUrl,
            apiKey: providerObj.apiKey,
            model: slot.modelId,
            messages: [{ role: 'user', text: prompt }],
            systemInstruction: parameters.systemInstruction,
            temperature: parameters.temperature,
          };
        }

        const res = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const data = await res.json();
        if (!res.ok || data.error) {
          throw new Error(data.error || 'Erro no provedor');
        }

        let respText = data.text || '';
        let thinkingText = '';
        const thinkMatch = respText.match(/<think>([\s\S]*?)<\/think>/i);
        if (thinkMatch) {
          thinkingText = thinkMatch[1].trim();
          respText = respText.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
        }

        return {
          ...slot,
          isLoading: false,
          currentResponse: respText,
          thinking: thinkingText,
          metrics: data.usage,
          error: undefined,
        };
      } catch (err: any) {
        return {
          ...slot,
          isLoading: false,
          currentResponse: '',
          error: err.message || 'Falha ao conectar com o modelo',
        };
      }
    });

    const finalSlots = await Promise.all(updatedSlotsPromises);
    onUpdateSlots(finalSlots);
    setIsLoading(false);
  };

  return (
    <div id="app-root" className="h-screen max-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased overflow-hidden">
      
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        providers={providers}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onToggleParameters={() => setIsParamsOpen(!isParamsOpen)}
        onOpenManual={() => setIsManualOpen(true)}
        hasGeminiKey={hasGeminiKey}
        engineOnline={engineOnline}
        telemetry={telemetry}
      />

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden relative">
        
        {/* Active Tab View */}
        {activeTab === 'chat' && (
          <ChatView
            conversations={conversations}
            activeConversation={activeConversation}
            onSelectConversation={(id) => setActiveConversationId(id)}
            onNewConversation={handleNewConversation}
            onDeleteConversation={handleDeleteConversation}
            onSendMessage={handleSendMessage}
            onRegenerateMessage={handleRegenerate}
            isLoading={isLoading}
            providers={providers}
            availableModels={availableModels}
            selectedModelId={selectedModelId}
            onSelectModel={(modelId) => setSelectedModelId(modelId)}
            parameters={parameters}
            onToggleParameters={() => setIsParamsOpen(!isParamsOpen)}
            onScanProviders={handleScanAllProviders}
            isScanning={isScanning}
          />
        )}

        {activeTab === 'arena' && (
          <ArenaView
            availableModels={availableModels}
            providers={providers}
            onExecuteArena={handleExecuteArena}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'hub' && (
          <ModelHubView
            onSelectModelForChat={(modelName) => {
              setSelectedModelId(modelName);
              setActiveTab('chat');
            }}
          />
        )}

        {activeTab === 'vram' && <VramCalculatorView />}

        {activeTab === 'stack' && (
          <EcosystemView 
            providers={providers} 
            onOpenSettings={() => setIsSettingsOpen(true)}
            onUpdateProvider={handleUpdateProvider}
            onTestProvider={handleTestProvider}
            hasGeminiKey={hasGeminiKey}
          />
        )}

        {/* Parameters Sidebar Drawer (Collapsible) */}
        <ParametersDrawer
          isOpen={isParamsOpen && activeTab === 'chat'}
          onClose={() => setIsParamsOpen(false)}
          parameters={parameters}
          onChangeParameters={(updated) => setParameters(updated)}
        />

      </div>

      {/* Provider Settings Modal */}
      <ProviderSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        providers={providers}
        onUpdateProvider={handleUpdateProvider}
        onTestProvider={handleTestProvider}
        hasGeminiKey={hasGeminiKey}
      />

      {/* Manual & Documentation Modal */}
      <ManualModal
        isOpen={isManualOpen}
        onClose={() => setIsManualOpen(false)}
      />

    </div>
  );
}
