export type ProviderType = 
  | 'gemini' 
  | 'ollama' 
  | 'lmstudio' 
  | 'llama-server' 
  | 'stable-diffusion-cpp'
  | 'vllm' 
  | 'localai' 
  | 'koboldcpp' 
  | 'tgi' 
  | 'jan' 
  | 'sglang' 
  | 'open-webui' 
  | 'anythingllm' 
  | 'openai' 
  | 'anthropic' 
  | 'custom';

export interface ProviderConfig {
  id: string;
  name: string;
  type: ProviderType;
  baseUrl: string;
  apiKey?: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'testing' | 'error';
  latencyMs?: number;
  models: string[];
  lastChecked?: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  providerType: ProviderType;
  providerId: string;
  contextWindow: number;
  parameterSize?: string; // e.g. "8B", "70B"
  description?: string;
  supportsVision?: boolean;
  supportsThinking?: boolean; // e.g. DeepSeek-R1
}

export interface SystemPromptPreset {
  id: string;
  title: string;
  category: 'General' | 'Coding' | 'Reasoning' | 'Creative' | 'Productivity';
  prompt: string;
  description: string;
}

export interface ChatParameters {
  temperature: number;
  topP: number;
  topK: number;
  maxTokens: number;
  contextWindow: number;
  repeatPenalty: number;
  systemInstruction: string;
  showThinking: boolean;
}

export interface AttachedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  content: string; // text or base64
  isImage: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking?: string; // For models like DeepSeek-R1
  timestamp: string;
  modelId?: string;
  providerType?: ProviderType;
  image?: string;
  files?: AttachedFile[];
  metrics?: {
    promptTokens?: number;
    completionTokens?: number;
    durationMs?: number;
    tokensPerSec?: number;
  };
  error?: string;
}

export interface Conversation {
  id: string;
  title: string;
  modelId: string;
  providerType: ProviderType;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
  parameters: ChatParameters;
}

export interface ArenaSlot {
  id: string;
  modelId: string;
  providerType: ProviderType;
  providerId: string;
  isLoading: boolean;
  currentResponse: string;
  thinking?: string;
  metrics?: {
    durationMs?: number;
    tokensPerSec?: number;
    promptTokens?: number;
    completionTokens?: number;
  };
  error?: string;
}

export interface HubModel {
  id: string;
  name: string;
  org: string;
  params: string;
  tags: string[];
  description: string;
  context: string;
  license: string;
  ollamaCommand: string;
  huggingFaceUrl: string;
  ggufSizes: {
    quant: string;
    sizeGb: number;
    ramRecommendedGb: number;
    qualityRating: number;
  }[];
  supportsVision?: boolean;
  supportsReasoning?: boolean;
}
