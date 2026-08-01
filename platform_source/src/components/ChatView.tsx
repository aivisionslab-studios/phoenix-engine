import React, { useState, useRef, useEffect } from 'react';
import { 
  Plus, 
  Send, 
  Bot, 
  User, 
  Paperclip, 
  Image as ImageIcon, 
  Volume2, 
  Copy, 
  Check, 
  RotateCcw, 
  BrainCircuit, 
  ChevronDown, 
  ChevronUp, 
  Trash2, 
  Edit3, 
  MessageSquare, 
  Sparkles, 
  FileText, 
  X,
  Sliders,
  Terminal,
  Cpu,
  Globe,
  Zap
} from 'lucide-react';
import { Conversation, ChatMessage, ProviderConfig, ChatParameters, AttachedFile, ModelInfo } from '../types';

interface ChatViewProps {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: string) => void;
  onSendMessage: (text: string, files: AttachedFile[], searchContext?: string) => Promise<void>;
  onRegenerateMessage: () => Promise<void>;
  isLoading: boolean;
  providers: ProviderConfig[];
  availableModels: ModelInfo[];
  selectedModelId: string;
  onSelectModel: (modelId: string) => void;
  parameters: ChatParameters;
  onToggleParameters: () => void;
}

export const ChatView: React.FC<ChatViewProps> = ({
  conversations,
  activeConversation,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onSendMessage,
  onRegenerateMessage,
  isLoading,
  providers,
  availableModels,
  selectedModelId,
  onSelectModel,
  parameters,
  onToggleParameters,
}) => {
  const [inputText, setInputText] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [expandedThinking, setExpandedThinking] = useState<Record<string, boolean>>({});
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [webSearchOn, setWebSearchOn] = useState(false);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConversation?.messages, isLoading]);

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if ((!inputText.trim() && attachedFiles.length === 0) || isLoading || isSearching) return;

    const currentText = inputText;
    const currentFiles = [...attachedFiles];

    setInputText('');
    setAttachedFiles([]);

    let searchContext: string | undefined;
    if (webSearchOn && currentText.trim()) {
      setIsSearching(true);
      try {
        const res = await fetch('/api/websearch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: currentText }),
        });
        const data = await res.json();
        if (data.error) {
          searchContext = `(Busca na web falhou: ${data.error})`;
        } else if (data.results?.length) {
          searchContext = data.results
            .map((r: { title: string; url: string; content: string }, i: number) => `${i + 1}. ${r.title}\n${r.url}\n${r.content}`)
            .join('\n\n');
        }
      } catch (err: any) {
        searchContext = `(Busca na web falhou: ${err.message || 'erro de rede'})`;
      } finally {
        setIsSearching(false);
      }
    }

    await onSendMessage(currentText, currentFiles, searchContext);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    Array.from(files).forEach((file: File) => {
      const reader = new FileReader();
      const isImg = file.type.startsWith('image/');

      reader.onload = (event) => {
        const content = event.target?.result as string;
        setAttachedFiles((prev) => [
          ...prev,
          {
            id: Math.random().toString(),
            name: file.name,
            size: file.size,
            type: file.type,
            content,
            isImage: isImg,
          },
        ]);
      };

      if (isImg) {
        reader.readAsDataURL(file);
      } else {
        reader.readAsText(file);
      }
    });

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachedFile = (fileId: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const copyToClipboard = (text: string, msgId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(msgId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const speakText = (text: string, msgId: string) => {
    if ('speechSynthesis' in window) {
      if (speakingId === msgId) {
        window.speechSynthesis.cancel();
        setSpeakingId(null);
        return;
      }
      window.speechSynthesis.cancel();
      // Remove think blocks or markdown tags for cleaner speech
      const cleanText = text.replace(/<think>[\s\S]*?<\/think>/gi, '').replace(/[*#`_]/g, '');
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = 'pt-BR';
      utterance.onend = () => setSpeakingId(null);
      utterance.onerror = () => setSpeakingId(null);
      setSpeakingId(msgId);
      window.speechSynthesis.speak(utterance);
    }
  };

  const toggleThinking = (msgId: string) => {
    setExpandedThinking((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const selectedModelObj = availableModels.find((m) => m.id === selectedModelId);

  return (
    <div id="chat-view-container" className="flex-1 flex overflow-hidden bg-slate-950 text-slate-100 min-h-0">
      
      {/* Sidebar - Chat History */}
      <aside id="chat-sidebar" className="w-64 border-r border-slate-800/80 bg-slate-900/80 flex flex-col hidden md:flex shrink-0">
        
        {/* New Chat Button */}
        <div className="p-3 border-b border-slate-800/80">
          <button
            id="new-chat-btn"
            onClick={onNewConversation}
            className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-indigo-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Nova Conversa</span>
          </button>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 ? (
            <div className="text-center p-4 text-xs text-slate-500">
              Nenhuma conversa salva ainda.
            </div>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                onClick={() => onSelectConversation(c.id)}
                className={`group flex items-center justify-between p-2.5 rounded-xl text-xs font-medium cursor-pointer transition-all ${
                  activeConversation?.id === c.id
                    ? 'bg-indigo-600/20 text-indigo-200 border border-indigo-500/30'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200 border border-transparent'
                }`}
              >
                <div className="flex items-center space-x-2.5 truncate">
                  <MessageSquare className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                  <span className="truncate">{c.title || 'Conversa sem título'}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(c.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-400 rounded transition-opacity"
                  title="Excluir"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center justify-between">
          <span>Phoenix Aviary Platform</span>
          <span className="font-mono text-[10px] text-indigo-400">v2.5</span>
        </div>
      </aside>

      {/* Main Chat Workspace */}
      <main id="chat-main-area" className="flex-1 flex flex-col h-full overflow-hidden bg-slate-950">
        
        {/* Top Chat Bar: Model Selector */}
        <div className="p-3 border-b border-slate-800/80 bg-slate-900/60 flex items-center justify-between px-4 sm:px-6">
          
          <div className="flex items-center space-x-3">
            <span className="text-xs font-medium text-slate-400 hidden sm:inline">Modelo Ativo:</span>
            
            {/* Model Dropdown */}
            <div className="relative">
              <select
                id="active-model-select"
                value={selectedModelId}
                onChange={(e) => onSelectModel(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white font-semibold focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 appearance-none pr-8 cursor-pointer shadow-sm"
              >
                {availableModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    [{m.providerType.toUpperCase()}] {m.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
            </div>

            {selectedModelObj?.supportsThinking && (
              <span className="hidden sm:flex items-center space-x-1 text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded-full font-mono">
                <BrainCircuit className="w-3 h-3" />
                <span>Raciocínio &lt;think&gt;</span>
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onToggleParameters}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 flex items-center space-x-1.5 transition-colors"
            >
              <Sliders className="w-3.5 h-3.5 text-indigo-400" />
              <span className="hidden sm:inline">Temp: {parameters.temperature.toFixed(1)}</span>
            </button>
          </div>

        </div>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {!activeConversation || activeConversation.messages.length === 0 ? (
            
            /* Welcome Empty Screen */
            <div className="max-w-2xl mx-auto my-auto text-center py-12 px-4">
              <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 mx-auto flex items-center justify-center mb-4 shadow-xl">
                <Bot className="w-8 h-8 text-indigo-400" />
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">
                O que gostaria de criar hoje?
              </h1>
              <p className="text-slate-400 text-xs sm:text-sm max-w-md mx-auto mb-8">
                Conecte-se a modelos locais via <strong>Ollama</strong> ou <strong>LM Studio</strong>, ou utilize o <strong>Gemini 3.6</strong> na nuvem.
              </p>

              {/* Quick Prompt Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                <button
                  onClick={() => setInputText("Explique como funciona o modelo de raciocínio DeepSeek-R1 e suas vantagens.")}
                  className="p-3 bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-indigo-500/50 rounded-xl transition-all group"
                >
                  <div className="flex items-center space-x-2 mb-1">
                    <BrainCircuit className="w-4 h-4 text-purple-400 group-hover:scale-110 transition-transform" />
                    <span className="text-xs font-bold text-slate-200">Explorar DeepSeek-R1</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Entenda o raciocínio em etapas e a arquitetura de RL.</p>
                </button>

                <button
                  onClick={() => setInputText("Crie um componente React com Tailwind CSS para exibir métricas de hardware de servidor.")}
                  className="p-3 bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-indigo-500/50 rounded-xl transition-all group"
                >
                  <div className="flex items-center space-x-2 mb-1">
                    <Terminal className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                    <span className="text-xs font-bold text-slate-200">Gerar Código Frontend</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Código React limpo, tipado e responsivo em TypeScript.</p>
                </button>

                <button
                  onClick={() => setInputText("Quais as diferenças de desempenho entre quantizações GGUF Q4_K_M e Q8_0?")}
                  className="p-3 bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-indigo-500/50 rounded-xl transition-all group"
                >
                  <div className="flex items-center space-x-2 mb-1">
                    <Cpu className="w-4 h-4 text-cyan-400 group-hover:scale-110 transition-transform" />
                    <span className="text-xs font-bold text-slate-200">Benchmark de Modelos Locais</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Compare VRAM, perda de perplexidade e tokens/segundo.</p>
                </button>

                <button
                  onClick={() => setInputText("Escreva um e-mail corporativo em Português para alinhar migração para LLMs privados.")}
                  className="p-3 bg-slate-900/80 hover:bg-slate-800/90 border border-slate-800 hover:border-indigo-500/50 rounded-xl transition-all group"
                >
                  <div className="flex items-center space-x-2 mb-1">
                    <FileText className="w-4 h-4 text-amber-400 group-hover:scale-110 transition-transform" />
                    <span className="text-xs font-bold text-slate-200">Comunicação Executiva</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Texto persuasivo sobre privacidade de dados e IA local.</p>
                </button>
              </div>

            </div>

          ) : (

            /* Message Thread */
            activeConversation.messages.map((msg) => {
              const isUser = msg.role === 'user';
              const isThinkingExpanded = expandedThinking[msg.id];

              return (
                <div
                  key={msg.id}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-4xl mx-auto`}
                >
                  
                  {/* Sender Name & Model Badge */}
                  <div className="flex items-center space-x-2 mb-1 px-1">
                    {!isUser && (
                      <div className="w-5 h-5 rounded-md bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center">
                        <Bot className="w-3 h-3 text-indigo-400" />
                      </div>
                    )}
                    <span className="text-[11px] font-semibold text-slate-400">
                      {isUser ? 'Você' : msg.modelId || 'Assistente IA'}
                    </span>
                    {msg.timestamp && (
                      <span className="text-[10px] font-mono text-slate-600">{msg.timestamp}</span>
                    )}
                  </div>

                  {/* Message Card */}
                  <div
                    className={`rounded-2xl p-4 text-xs sm:text-sm leading-relaxed max-w-full shadow-lg ${
                      isUser
                        ? 'bg-indigo-600 text-white rounded-tr-none'
                        : 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-none'
                    }`}
                  >
                    
                    {/* Attached Image Preview */}
                    {msg.image && (
                      <div className="mb-3">
                        <img
                          src={msg.image}
                          alt="Anexo de Imagem"
                          className="max-h-60 rounded-lg object-contain border border-slate-700/80"
                        />
                      </div>
                    )}

                    {/* Attached Files Preview */}
                    {msg.files && msg.files.length > 0 && (
                      <div className="mb-3 space-y-1.5">
                        {msg.files.map((f) => (
                          <div
                            key={f.id}
                            className="flex items-center space-x-2 bg-slate-950/60 p-2 rounded-lg border border-slate-800 text-xs font-mono"
                          >
                            <FileText className="w-4 h-4 text-indigo-400" />
                            <span className="truncate">{f.name}</span>
                            <span className="text-[10px] text-slate-500">({(f.size / 1024).toFixed(1)} KB)</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Reasoning Think Block (For DeepSeek-R1 / Thinking models) */}
                    {msg.thinking && (
                      <div className="mb-3 bg-purple-950/30 border border-purple-800/40 rounded-xl overflow-hidden">
                        <button
                          onClick={() => toggleThinking(msg.id)}
                          className="w-full flex items-center justify-between p-2.5 bg-purple-900/20 text-purple-300 font-mono text-[11px] font-semibold hover:bg-purple-900/30 transition-colors"
                        >
                          <div className="flex items-center space-x-2">
                            <BrainCircuit className="w-3.5 h-3.5 text-purple-400" />
                            <span>Processo de Raciocínio (&lt;think&gt;)</span>
                          </div>
                          {isThinkingExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5" />
                          )}
                        </button>
                        {isThinkingExpanded && (
                          <div className="p-3 text-[11px] font-mono text-purple-200/80 bg-purple-950/40 border-t border-purple-800/30 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
                            {msg.thinking}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Main Content Body */}
                    <div className="whitespace-pre-wrap font-sans">
                      {msg.content}
                    </div>

                    {/* Error Message if any */}
                    {msg.error && (
                      <div className="mt-2 p-2.5 bg-rose-950/50 border border-rose-800/50 rounded-lg text-rose-300 text-xs">
                        ⚠️ {msg.error}
                      </div>
                    )}

                    {/* Assistant Message Footer: Metrics & Actions */}
                    {!isUser && (
                      <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
                        
                        {/* Token Speed & Metrics */}
                        {msg.metrics && (
                          <div className="flex items-center space-x-3 font-mono text-[10px]">
                            {msg.metrics.tokensPerSec !== undefined && (
                              <span className="text-emerald-400 font-semibold flex items-center space-x-1">
                                <Zap className="w-3 h-3" />
                                <span>{msg.metrics.tokensPerSec} tok/s</span>
                              </span>
                            )}
                            {msg.metrics.durationMs && (
                              <span>{(msg.metrics.durationMs / 1000).toFixed(2)}s</span>
                            )}
                            {msg.metrics.completionTokens && (
                              <span>{msg.metrics.completionTokens} tokens</span>
                            )}
                          </div>
                        )}

                        {/* Action Buttons */}
                        <div className="flex items-center space-x-1 ml-auto">
                          <button
                            onClick={() => speakText(msg.content, msg.id)}
                            className={`p-1.5 rounded hover:bg-slate-800 transition-colors ${
                              speakingId === msg.id ? 'text-indigo-400 animate-pulse' : 'text-slate-400 hover:text-slate-200'
                            }`}
                            title="Ouvir Resposta (Voz)"
                          >
                            <Volume2 className="w-3.5 h-3.5" />
                          </button>
                          
                          <button
                            onClick={() => copyToClipboard(msg.content, msg.id)}
                            className="p-1.5 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition-colors"
                            title="Copiar Texto"
                          >
                            {copiedId === msg.id ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>

                      </div>
                    )}

                  </div>

                </div>
              );
            })
          )}

          {isLoading && (
            <div className="flex items-center space-x-3 max-w-4xl mx-auto p-4 bg-slate-900/60 border border-slate-800 rounded-2xl">
              <Bot className="w-5 h-5 text-indigo-400 animate-bounce" />
              <div className="space-y-1">
                <span className="text-xs font-semibold text-slate-300">Processando resposta...</span>
                <p className="text-[11px] text-slate-500 font-mono">Gerando tokens a partir do modelo selecionado</p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Input Area */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/80">
          <div className="max-w-4xl mx-auto">
            
            {/* Display Attached Files List */}
            {attachedFiles.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2 p-2 bg-slate-950 border border-slate-800 rounded-xl">
                {attachedFiles.map((f) => (
                  <div
                    key={f.id}
                    className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-900 border border-slate-700/80 rounded-lg text-xs font-mono text-slate-300"
                  >
                    {f.isImage ? <ImageIcon className="w-3.5 h-3.5 text-cyan-400" /> : <FileText className="w-3.5 h-3.5 text-indigo-400" />}
                    <span className="truncate max-w-[120px]">{f.name}</span>
                    <button
                      onClick={() => removeAttachedFile(f.id)}
                      className="text-slate-500 hover:text-rose-400"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Form Input */}
            <form onSubmit={handleSend} className="relative flex items-center bg-slate-950 border border-slate-800 focus-within:border-indigo-500 rounded-2xl shadow-xl transition-all">
              
              {/* Hidden File Input */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                multiple
                className="hidden"
                accept="image/*,.txt,.md,.json,.js,.ts,.py,.cpp,.java,.pdf"
              />

              {/* Attach File Button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="p-3 text-slate-400 hover:text-indigo-300 transition-colors"
                title="Anexar arquivo ou imagem"
              >
                <Paperclip className="w-5 h-5" />
              </button>

              {/* Web Search Toggle (SearXNG — searxng-phoenix, porta 8080) */}
              <button
                type="button"
                onClick={() => setWebSearchOn((prev) => !prev)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 mr-1 rounded-lg text-xs font-semibold transition-colors ${
                  webSearchOn
                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
                    : 'text-slate-400 border border-transparent hover:text-slate-200 hover:bg-slate-800/60'
                }`}
                title="Buscar na web antes de responder (SearXNG)"
              >
                <Globe className="w-4 h-4" />
                <span className="hidden sm:inline">{isSearching ? 'Buscando...' : 'Web'}</span>
              </button>

              {/* Textarea Input */}
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Digite sua mensagem para o modelo de IA..."
                disabled={isLoading}
                className="flex-1 bg-transparent py-3 px-2 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
              />

              {/* Submit / Send Button */}
              <button
                type="submit"
                disabled={(!inputText.trim() && attachedFiles.length === 0) || isLoading}
                className="m-1.5 p-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white rounded-xl shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
              >
                <Send className="w-4 h-4" />
              </button>

            </form>

            <div className="flex items-center justify-between mt-2 text-[10px] text-slate-500 px-1 font-mono">
              <span>Shift + Enter para nova linha</span>
              <span>Suporta Markdown e código tipado</span>
            </div>

          </div>
        </div>

      </main>

    </div>
  );
};
