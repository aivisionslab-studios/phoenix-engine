import React, { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { ProviderSettingsModal } from './components/ProviderSettingsModal';
import { ParametersDrawer } from './components/ParametersDrawer';
import { ChatView } from './components/ChatView';
import { ArenaView } from './components/ArenaView';
import { ModelHubView } from './components/ModelHubView';
import { VramCalculatorView } from './components/VramCalculatorView';
import { EcosystemView } from './components/EcosystemView';

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
    status: 'disconnected',
    models: [],
  },
  {
    id: 'llama-server-local',
    name: 'llama.cpp (Motor Nativo Vulkan — RX 580)',
    type: 'llama-server',
    baseUrl: 'http://localhost:8081/v1',
    enabled: true,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'stable-diffusion-cpp-local',
    name: 'stable-diffusion.cpp (Geração de Imagem — Vulkan)',
    type: 'stable-diffusion-cpp',
    baseUrl: 'http://localhost:7860',
    enabled: true,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'ollama-local',
    name: 'Ollama (Servidor Local)',
    type: 'ollama',
    baseUrl: 'http://localhost:11434',
    enabled: true,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'lmstudio-local',
    name: 'LM Studio (Servidor Local)',
    type: 'lmstudio',
    baseUrl: 'http://localhost:1234/v1',
    enabled: true,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'vllm-local',
    name: 'vLLM Server (PagedAttention)',
    type: 'vllm',
    baseUrl: 'http://localhost:8000/v1',
    enabled: false,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'localai-server',
    name: 'LocalAI Server',
    type: 'localai',
    baseUrl: 'http://localhost:8080/v1',
    enabled: false,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'koboldcpp-server',
    name: 'KoboldCpp Server',
    type: 'koboldcpp',
    baseUrl: 'http://localhost:5001/v1',
    enabled: true,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'jan-server',
    name: 'Jan Local Engine Server',
    type: 'jan',
    baseUrl: 'http://localhost:1337/v1',
    enabled: true,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'openwebui-gateway',
    name: 'Open WebUI Gateway Proxy',
    type: 'open-webui',
    baseUrl: 'http://localhost:8010/api',
    enabled: false,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'anythingllm-server',
    name: 'AnythingLLM Enterprise RAG',
    type: 'anythingllm',
    baseUrl: 'http://localhost:3001/api/v1',
    enabled: true,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'openai-cloud',
    name: 'OpenAI API Cloud',
    type: 'openai',
    baseUrl: 'https://api.openai.com/v1',
    enabled: false,
    status: 'disconnected',
    models: [],
  },
  {
    id: 'anthropic-cloud',
    name: 'Anthropic Claude Cloud',
    type: 'anthropic',
    baseUrl: 'https://api.anthropic.com',
    enabled: false,
    status: 'disconnected',
    models: [],
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

export default function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'arena' | 'hub' | 'vram' | 'stack' | 'settings'>('chat');
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isParamsOpen, setIsParamsOpen] = useState<boolean>(false);
  
  // Sobe esse número toda vez que DEFAULT_PROVIDERS muda de forma estrutural
  // (nome, baseUrl padrão, modelos placeholder, provedor novo/removido).
  // Sem isso, o merge por id só ADICIONA provedor novo mas nunca ATUALIZA um
  // que já existia no localStorage do navegador — então correções de código
  // (como remover nomes-placeholder fake) nunca chegavam em quem já tinha
  // usado o app antes, ficando pra sempre preso na versão salva antiga.
  const PROVIDERS_SCHEMA_VERSION = 2;

  const [providers, setProviders] = useState<ProviderConfig[]>(() => {
    const savedVersion = localStorage.getItem('app_providers_version');
    if (savedVersion !== String(PROVIDERS_SCHEMA_VERSION)) {
      // Schema mudou (ou é a primeira vez): descarta o save antigo e começa
      // limpo com os defaults atuais do código.
      return DEFAULT_PROVIDERS;
    }
    const saved = localStorage.getItem('app_providers');
    if (!saved) return DEFAULT_PROVIDERS;
    try {
      const savedList: ProviderConfig[] = JSON.parse(saved);
      const savedIds = new Set(savedList.map((p) => p.id));
      // Mantém as edições salvas do usuário (URL/chave/ativo) e acrescenta
      // qualquer provedor novo do código (ex: llama.cpp, stable-diffusion.cpp)
      // que ainda não existia quando o save antigo foi feito no navegador.
      const missingFromSaved = DEFAULT_PROVIDERS.filter((p) => !savedIds.has(p.id));
      return [...savedList, ...missingFromSaved];
    } catch {
      return DEFAULT_PROVIDERS;
    }
  });

  const [parameters, setParameters] = useState<ChatParameters>(() => {
    const saved = localStorage.getItem('app_parameters');
    return saved ? JSON.parse(saved) : DEFAULT_PARAMETERS;
  });

  const [conversations, setConversations] = useState<Conversation[]>(() => {
    const saved = localStorage.getItem('app_conversations');
    return saved ? JSON.parse(saved) : [];
  });

  const [activeConversationId, setActiveConversationId] = useState<string | null>(() => {
    const savedConvs = localStorage.getItem('app_conversations');
    if (savedConvs) {
      const parsed: Conversation[] = JSON.parse(savedConvs);
      return parsed[0]?.id || null;
    }
    return null;
  });

  const [selectedModelId, setSelectedModelId] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [hasGeminiKey, setHasGeminiKey] = useState<boolean>(true);

  // Save state to localStorage
  useEffect(() => {
    localStorage.setItem('app_providers', JSON.stringify(providers));
    localStorage.setItem('app_providers_version', String(PROVIDERS_SCHEMA_VERSION));
  }, [providers]);

  useEffect(() => {
    localStorage.setItem('app_parameters', JSON.stringify(parameters));
  }, [parameters]);

  useEffect(() => {
    localStorage.setItem('app_conversations', JSON.stringify(conversations));
  }, [conversations]);

  // Aggregate available models from enabled providers
  const availableModels: ModelInfo[] = React.useMemo(() => {
    const list: ModelInfo[] = [];

    providers.forEach((p) => {
      if (!p.enabled) return;
      // stable-diffusion.cpp não é um provedor de chat/texto — os "modelos" dele
      // são checkpoints de geração de imagem (.gguf/.safetensors), incompatíveis
      // com o endpoint de chat completions. Não faz sentido aparecer aqui.
      if (p.type === 'stable-diffusion-cpp') return;
      // Só considera modelo real depois de um ping bem-sucedido — enquanto o
      // provedor não foi confirmado online, não existe modelo "detectado" de
      // verdade pra oferecer no chat.
      if (p.status !== 'connected') return;

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

    return list;
  }, [providers]);

  // Escolhe o modelo ativo padrão assim que a lista estiver pronta, priorizando
  // motores LOCAIS (llama.cpp é o motor primordial do projeto) sobre nuvem —
  // evita começar toda conversa nova travada em "GEMINI_API_KEY is not defined"
  // quando o usuário nem configurou chave de nuvem nenhuma.
  useEffect(() => {
    if (availableModels.length === 0) return;
    // Só pula a escolha se o modelo atual ainda existir na lista. Se o ping
    // acabou de trocar um nome-placeholder ("qwen2.5-7b-instruct-q4") pelo
    // nome real do modelo carregado ("qwen3-8b-q4_k_m"), o id antigo fica
    // órfão — nesse caso escolhe de novo em vez de deixar o dropdown preso
    // apontando pra uma opção que não existe mais.
    if (selectedModelId && availableModels.some((m) => m.id === selectedModelId)) return;
    const priority: ModelInfo['providerType'][] = [
      'llama-server', 'ollama', 'lmstudio', 'vllm', 'localai', 'koboldcpp',
      'openai', 'anthropic', 'gemini',
    ];
    for (const type of priority) {
      const match = availableModels.find((m) => m.providerType === type);
      if (match) {
        setSelectedModelId(match.id);
        return;
      }
    }
    setSelectedModelId(availableModels[0].id);
  }, [availableModels, selectedModelId]);

  // Check health on initial load
  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => {
        if (data.hasGeminiKey !== undefined) {
          setHasGeminiKey(data.hasGeminiKey);
        }
      })
      .catch(() => {});
  }, []);

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

  // Auto-detecção: pinga todos os provedores locais/habilitados de forma
  // PERIÓDICA (não só uma vez), porque runtimes como llama-server/sd-server
  // costumam subir DEPOIS que o Aviary já carregou (carregar um GGUF grande
  // leva tempo) — um ping único na montagem ficava preso mostrando os nomes
  // placeholder pra sempre se o servidor ainda não estivesse de pé naquele
  // instante exato. Usa um ref pra sempre pingar a lista mais atual de
  // provedores, sem precisar recriar o interval a cada mudança de estado.
  const providersRef = useRef(providers);
  useEffect(() => {
    providersRef.current = providers;
  }, [providers]);

  useEffect(() => {
    const pingAllEnabled = () => {
      providersRef.current.forEach((p) => {
        if (p.enabled && p.type !== 'stable-diffusion-cpp') {
          handleTestProvider(p.id);
        }
      });
    };
    pingAllEnabled(); // primeira tentativa imediata ao abrir o app
    const intervalId = setInterval(pingAllEnabled, 20000); // depois, a cada 20s
    return () => clearInterval(intervalId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
  const handleSendMessage = async (text: string, files: AttachedFile[], searchContext?: string) => {
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

    // O contexto de busca só entra no que é ENVIADO pro modelo — a bolha
    // exibida na tela (updatedMessages/userMsg) fica limpa com a pergunta
    // original, sem o bloco de resultados poluindo visualmente o chat.
    const messagesForApi = searchContext
      ? updatedMessages.map((m, i) =>
          i === updatedMessages.length - 1
            ? { ...m, content: `${m.content}\n\n[Resultados de busca na web — SearXNG]\n${searchContext}\n\nResponda usando esses resultados quando forem relevantes, e cite que a informação veio de uma busca na web se usar algo de lá.` }
            : m
        )
      : updatedMessages;

    setConversations(
      convList.map((c) => (c.id === convId ? { ...c, messages: updatedMessages, title: c.title === 'Nova Conversa IA' ? text.slice(0, 30) : c.title } : c))
    );

    setIsLoading(true);

    const activeModelObj = availableModels.find((m) => m.id === selectedModelId);
    const providerObj = providers.find((p) => p.id === activeModelObj?.providerId) || providers[0];

    try {
      let endpoint = '/api/gemini/chat';
      let requestPayload: any = {
        model: selectedModelId,
        messages: messagesForApi,
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
          messages: messagesForApi,
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
        // Prefere o modelo que o SERVIDOR confirmou ter usado de verdade
        // (ex: llama-server pode ignorar o "model" pedido e sempre responder
        // com o GGUF que está de fato carregado, tipo qwen3-8b-q4_k_m mesmo
        // se a UI mandou outro nome). Só cai pro nome pedido se o servidor
        // não informar nada.
        modelId: data.model || selectedModelId,
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
  const handleExecuteArena = async (arenaSlots: ArenaSlot[], prompt: string) => {
    setIsLoading(true);

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

    await Promise.all(updatedSlotsPromises);
    setIsLoading(false);
  };

  return (
    <div id="app-root" className="h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased overflow-hidden">
      
      {/* Top Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        providers={providers}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onToggleParameters={() => setIsParamsOpen(!isParamsOpen)}
        hasGeminiKey={hasGeminiKey}
      />

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden relative min-h-0">
        
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

    </div>
  );
}
