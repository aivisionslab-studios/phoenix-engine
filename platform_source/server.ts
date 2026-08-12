import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json({ limit: "25mb" }));

// Enable CORS for all ports and origins
app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS");
  res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept, Authorization, x-api-key");
  if (req.method === "OPTIONS") {
    res.sendStatus(200);
    return;
  }
  next();
});

// Helper to get Gemini Client safely
function getGeminiClient() {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error("GEMINI_API_KEY environment variable is not defined");
  }
  return new GoogleGenAI({
    apiKey,
    httpOptions: {
      headers: {
        "User-Agent": "aistudio-build",
      },
    },
  });
}

// 0. Phoenix Engine Configuration & Base URL
const PHOENIX_ENGINE_URL = (process.env.PHOENIX_ENGINE_URL || "http://localhost:8000").replace(/\/$/, "");

// 1. Health check
app.get("/api/health", async (_req, res) => {
  let engineOnline = false;
  let engineData: any = null;

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 2000);
    const r = await fetch(`${PHOENIX_ENGINE_URL}/health`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (r.ok) {
      engineOnline = true;
      engineData = await r.json();
    }
  } catch {
    // Engine offline or booting
  }

  res.json({
    status: "ok",
    hasGeminiKey: Boolean(process.env.GEMINI_API_KEY),
    phoenixEngineUrl: PHOENIX_ENGINE_URL,
    engineOnline,
    engineData,
    timestamp: new Date().toISOString(),
  });
});

// 1b. Phoenix Engine State Proxy
app.get("/api/engine/state", async (_req, res) => {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 3000);
    const r = await fetch(`${PHOENIX_ENGINE_URL}/api/state`, { signal: ctrl.signal });
    clearTimeout(timer);

    if (!r.ok) {
      res.status(r.status).json({ error: `Phoenix Engine retornou HTTP ${r.status}` });
      return;
    }
    const data = await r.json();
    res.json(data);
  } catch (err: any) {
    res.status(503).json({
      error: `Phoenix Engine (${PHOENIX_ENGINE_URL}) offline ou inicializando: ${err.message || 'erro de rede'}`,
      online: false,
    });
  }
});

// 1c. Resident Message Queue Proxy
// PHX-NEW: Fila de mensagens pendentes do Resident (Phoenix Engine, porta 8000)
app.get("/api/chat/pending", async (_req, res) => {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 2000);
    const r = await fetch(`${PHOENIX_ENGINE_URL}/api/chat/pending`, { signal: ctrl.signal });
    clearTimeout(timer);

    if (!r.ok) {
      res.json({ messages: [] });
      return;
    }
    const data = await r.json();
    res.json({ messages: Array.isArray(data.messages) ? data.messages : [] });
  } catch {
    res.json({ messages: [] });
  }
});

// 1d. Phoenix Engine & Local Runtimes Tracked Models Scanner
app.get("/api/engine/models", async (_req, res) => {
  const tracked = {
    phoenixModels: [] as string[],
    ollamaModels: [] as string[],
    lmstudioModels: [] as string[],
    llamaServerModels: [] as string[],
    allDownloadedModels: [] as string[],
  };

  // 1. Check Phoenix Engine (port 8000)
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 2000);
    const r = await fetch(`${PHOENIX_ENGINE_URL}/api/models`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (r.ok) {
      const data: any = await r.json();
      if (Array.isArray(data.models)) {
        tracked.phoenixModels = data.models.map((m: any) => typeof m === "string" ? m : m.id || m.name);
      } else if (Array.isArray(data.data)) {
        tracked.phoenixModels = data.data.map((m: any) => typeof m === "string" ? m : m.id || m.name);
      }
    }
  } catch {
    // Engine offline or no /api/models
  }

  // 2. Check Ollama tags (port 11434)
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 2000);
    const r = await fetch("http://localhost:11434/api/tags", { signal: ctrl.signal });
    clearTimeout(timer);
    if (r.ok) {
      const data: any = await r.json();
      if (Array.isArray(data.models)) {
        tracked.ollamaModels = data.models.map((m: any) => m.name || m.model);
      }
    }
  } catch {
    // Ollama offline
  }

  // 3. Check LM Studio (port 1234)
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 2000);
    const r = await fetch("http://localhost:1234/v1/models", { signal: ctrl.signal });
    clearTimeout(timer);
    if (r.ok) {
      const data: any = await r.json();
      if (Array.isArray(data.data)) {
        tracked.lmstudioModels = data.data.map((m: any) => m.id || m.name);
      }
    }
  } catch {
    // LM Studio offline
  }

  // 4. Check llama-server (port 8081)
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 2000);
    const r = await fetch("http://localhost:8081/v1/models", { signal: ctrl.signal });
    clearTimeout(timer);
    if (r.ok) {
      const data: any = await r.json();
      if (Array.isArray(data.data)) {
        tracked.llamaServerModels = data.data.map((m: any) => m.id || m.name);
      }
    }
  } catch {
    // llama-server offline
  }

  // Combine unique downloaded models
  const uniqueSet = new Set([
    ...tracked.phoenixModels,
    ...tracked.ollamaModels,
    ...tracked.lmstudioModels,
    ...tracked.llamaServerModels,
  ]);
  tracked.allDownloadedModels = Array.from(uniqueSet);

  res.json(tracked);
});

// 2. Gemini API Chat Endpoint
app.post("/api/gemini/chat", async (req, res) => {
  try {
    const { model, messages, systemInstruction, temperature, topP, topK, maxTokens } = req.body;
    const ai = getGeminiClient();

    const selectedModel = model || "gemini-3.6-flash";

    // Date Context Injection
    const currentDateStr = new Date().toLocaleDateString("pt-BR", {
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: "long"
    });
    const currentYear = new Date().getFullYear();
    const systemDateContext = `[Informação do Sistema: A data atual do sistema é ${currentDateStr} (Ano Atual: ${currentYear}). Considere o ano de ${currentYear} como o ano corrente.]`;

    const effectiveSystemInstruction = systemInstruction
      ? `${systemDateContext}\n\n${systemInstruction}`
      : systemDateContext;

    // Format chat messages for Gemini SDK
    // Convert previous user/assistant messages into contents history
    const contents: Array<{ role: string; parts: Array<{ text?: string; inlineData?: { mimeType: string; data: string } }> }> = [];

    const searchResults = await performWebSearchIfRequested(messages);

    if (Array.isArray(messages)) {
      for (let i = 0; i < messages.length; i++) {
        const msg = messages[i];
        const parts: Array<{ text?: string; inlineData?: { mimeType: string; data: string } }> = [];
        
        let textStr = msg.text || msg.content || "";
        if (i === messages.length - 1 && searchResults) {
          textStr += searchResults;
        }

        if (textStr) {
          parts.push({ text: textStr });
        }
        if (msg.image) {
          // base64 image data
          const matches = msg.image.match(/^data:(image\/[a-zA-Z]+);base64,(.+)$/);
          if (matches) {
            parts.push({
              inlineData: {
                mimeType: matches[1],
                data: matches[2],
              },
            });
          }
        }
        
        if (parts.length > 0) {
          contents.push({
            role: msg.role === "assistant" || msg.role === "model" ? "model" : "user",
            parts,
          });
        }
      }
    }

    if (contents.length === 0) {
      contents.push({
        role: "user",
        parts: [{ text: "Hello" }],
      });
    }

    const config: any = {
      systemInstruction: effectiveSystemInstruction,
    };
    if (typeof temperature === "number") config.temperature = temperature;
    if (typeof topP === "number") config.topP = topP;
    if (typeof topK === "number") config.topK = topK;
    if (typeof maxTokens === "number" && maxTokens > 0) config.maxOutputTokens = maxTokens;

    const startTime = Date.now();
    const response = await ai.models.generateContent({
      model: selectedModel,
      contents,
      config,
    });
    const endTime = Date.now();

    const outputText = response.text || "";
    const promptTokensEst = Math.ceil((JSON.stringify(contents).length) / 4);
    const completionTokensEst = Math.ceil(outputText.length / 4);
    const durationMs = endTime - startTime;
    const tokensPerSec = durationMs > 0 ? ((completionTokensEst / durationMs) * 1000).toFixed(1) : "0";

    res.json({
      text: outputText,
      usage: {
        promptTokens: promptTokensEst,
        completionTokens: completionTokensEst,
        durationMs,
        tokensPerSec: parseFloat(tokensPerSec),
      },
    });
  } catch (error: any) {
    console.error("Gemini API Error:", error);
    res.status(500).json({
      error: error.message || "Failed to generate response from Gemini API",
    });
  }
});

// 3b. Universal HTTP Proxy (Forward requests to any local or internet port/URL)
app.all("/api/proxy/universal", async (req, res) => {
  const targetUrl = (req.query.url as string) || (req.body && req.body.targetUrl);
  if (!targetUrl) {
    res.status(400).json({ error: "Parâmetro 'url' ou 'targetUrl' é obrigatório." });
    return;
  }

  try {
    const headers: Record<string, string> = {};
    if (req.headers["content-type"]) {
      headers["Content-Type"] = req.headers["content-type"] as string;
    }
    if (req.headers["authorization"]) {
      headers["Authorization"] = req.headers["authorization"] as string;
    }

    const options: RequestInit = {
      method: req.method,
      headers,
    };

    if (req.method !== "GET" && req.method !== "HEAD" && req.body) {
      delete req.body.targetUrl;
      options.body = typeof req.body === "string" ? req.body : JSON.stringify(req.body);
    }

    const response = await fetch(targetUrl, options);
    const contentType = response.headers.get("content-type") || "";

    res.status(response.status);
    if (contentType.includes("application/json")) {
      const json = await response.json();
      res.json(json);
    } else {
      const text = await response.text();
      res.send(text);
    }
  } catch (err: any) {
    res.status(502).json({
      error: `Falha ao conectar no destino (${targetUrl}): ${err.message || 'Erro de rede'}`,
    });
  }
});

// 3c. Dynamic Local Port Proxy (Forward requests to any local port e.g. /api/proxy/port/8000/api/state)
app.all(["/api/proxy/port/:port", "/api/proxy/port/:port/*"], async (req, res) => {
  const targetPort = req.params.port;
  const subPath = (req.params as any)[0] ? `/${(req.params as any)[0]}` : "";
  const queryStr = req.url.includes("?") ? req.url.substring(req.url.indexOf("?")) : "";
  const targetUrl = `http://127.0.0.1:${targetPort}${subPath}${queryStr}`;

  try {
    const headers: Record<string, string> = {};
    for (const [key, val] of Object.entries(req.headers)) {
      if (key !== "host" && key !== "content-length" && typeof val === "string") {
        headers[key] = val;
      }
    }

    const options: RequestInit = {
      method: req.method,
      headers,
    };

    if (req.method !== "GET" && req.method !== "HEAD" && req.body) {
      options.body = typeof req.body === "string" ? req.body : JSON.stringify(req.body);
    }

    const response = await fetch(targetUrl, options);
    res.status(response.status);

    response.headers.forEach((val, key) => {
      if (key !== "content-encoding" && key !== "content-length") {
        res.setHeader(key, val);
      }
    });

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const json = await response.json();
      res.json(json);
    } else {
      const buffer = await response.arrayBuffer();
      res.send(Buffer.from(buffer));
    }
  } catch (err: any) {
    res.status(502).json({
      error: `Falha ao conectar na porta local ${targetPort}: ${err.message || 'Erro de conexão'}`,
      targetUrl,
    });
  }
});

// 4. Provider Connection Ping / Discovery Proxy
app.post("/api/proxy/ping", async (req, res) => {
  const { providerType, baseUrl, apiKey } = req.body;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 4000);

  try {
    let testUrl = baseUrl || "";
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }

    if (providerType === "ollama") {
      testUrl = `${baseUrl.replace(/\/$/, "")}/api/tags`;
    } else if (providerType === "anthropic") {
      testUrl = `${baseUrl.replace(/\/$/, "")}/v1/models`;
      headers["x-api-key"] = apiKey || "";
      headers["anthropic-version"] = "2023-06-01";
    } else {
      // OpenAI-compatible / llama-server / LM Studio / vLLM / LocalAI / KoboldCpp / Jan / Custom
      const cleanBase = (baseUrl || "").replace(/\/$/, "");
      if (cleanBase.endsWith("/v1")) {
        testUrl = `${cleanBase}/models`;
      } else {
        testUrl = `${cleanBase}/v1/models`;
      }
    }

    if (!testUrl.startsWith("http")) {
      testUrl = `http://${testUrl}`;
    }

    const startTime = Date.now();
    let response = await fetch(testUrl, {
      method: "GET",
      headers,
      signal: controller.signal,
    });

    // Fallback check for llama-server props or health endpoint if /v1/models returns 404
    if (!response.ok && (providerType === "llama-server" || providerType === "koboldcpp")) {
      const altUrl = testUrl.replace(/\/v1\/models|\/models/, "/props");
      try {
        const altResponse = await fetch(altUrl, { method: "GET", headers, signal: controller.signal });
        if (altResponse.ok) {
          response = altResponse;
        }
      } catch {
        // ignore fallback error
      }
    }

    clearTimeout(timeoutId);

    const latencyMs = Date.now() - startTime;

    if (!response.ok && response.status !== 401 && response.status !== 403) {
      res.json({
        online: false,
        status: response.status,
        latencyMs,
        message: `HTTP ${response.status}: ${response.statusText}`,
        models: [],
      });
      return;
    }

    let modelsList: string[] = [];
    try {
      const data: any = await response.json();
      if (providerType === "ollama" && Array.isArray(data.models)) {
        modelsList = data.models.map((m: any) => m.name || m.model);
      } else if (Array.isArray(data.data)) {
        modelsList = data.data.map((m: any) => m.id || m.name || m.model);
      } else if (Array.isArray(data.models)) {
        modelsList = data.models.map((m: any) => m.id || m.name || m.model);
      } else if (data.id) {
        modelsList = [data.id];
      } else if (data.default_generation_settings?.model) {
        const fullPath = data.default_generation_settings.model;
        const fileName = fullPath.split(/[\/\\]/).pop() || fullPath;
        modelsList = [fileName];
      }
    } catch {
      // JSON parse fallback
    }

    res.json({
      online: true,
      latencyMs,
      status: response.status,
      models: modelsList,
    });
  } catch (err: any) {
    clearTimeout(timeoutId);
    res.json({
      online: false,
      latencyMs: 0,
      message: err.name === "AbortError" ? "Connection timed out (is local server running?)" : err.message || "Failed to reach endpoint",
      models: [],
    });
  }
});

// Helper to extract clean query without conversational command prefixes
function extractCleanSearchQuery(text: string): string {
  let cleaned = text.trim();
  cleaned = cleaned.replace(/^(por favor,?\s*)?(pesquisar|pesquise|buscar|busque|procure|procurar|pesquisa|busca|search|google)\s+(na internet|na web|no google|em linha|online|sobre|por|about|for)?\s*(sobre|about|por|for)?\s*/i, "");
  cleaned = cleaned.replace(/^(na internet|na web|no google|em linha|online)\s+(sobre|por|about|for)?\s*/i, "");
  cleaned = cleaned.replace(/^(sobre|about|por|for)\s+/i, "");
  return cleaned.trim() || text.trim();
}

// Helper to perform live web search directly for a query string
async function performWebSearchDirect(rawQuery: string): Promise<string | null> {
  const query = extractCleanSearchQuery(rawQuery);
  if (!query || query.length < 2) return null;

  console.log(`[WebSearch] Pesquisando: "${query}" (Original: "${rawQuery}")`);

  const localSearchEndpoints = [
    `http://127.0.0.1:8080/search?q=${encodeURIComponent(query)}&format=json`,
    `http://127.0.0.1:8088/search?q=${encodeURIComponent(query)}&format=json`,
    `http://localhost:8080/search?q=${encodeURIComponent(query)}&format=json`,
    `http://localhost:8088/search?q=${encodeURIComponent(query)}&format=json`,
  ];

  const browserHeaders = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
  };

  // 1. SearXNG Local Endpoints
  for (const url of localSearchEndpoints) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 3000);
      const res = await fetch(url, {
        headers: browserHeaders,
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (res.ok) {
        const data: any = await res.json();
        const results = data.results || data.data || [];
        if (Array.isArray(results) && results.length > 0) {
          const topResults = results.slice(0, 5).map((r: any, idx: number) => 
            `${idx + 1}. [${r.title || 'Sem título'}](${r.url || '#'}) - ${r.content || r.snippet || r.abstract || ''}`
          ).join("\n");

          return `\n\n[Resultados da Busca na Web em Tempo Real (Pesquisa: "${query}" - Data: ${new Date().toLocaleDateString("pt-BR")})]:\n${topResults}`;
        }
      }
    } catch {
      // try next
    }
  }

  // 2. Fallback: DuckDuckGo Instant Answer API & HTML Search
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3500);
    const ddgRes = await fetch(`https://api.duckduckgo.com/?q=${encodeURIComponent(query)}&format=json&no_html=1&skip_disambig=1`, {
      headers: browserHeaders,
      signal: controller.signal,
    });
    clearTimeout(timer);

    if (ddgRes.ok) {
      const ddgData: any = await ddgRes.json();
      const results: string[] = [];

      if (ddgData.AbstractText) {
        results.push(`• **${ddgData.Heading || query}**: ${ddgData.AbstractText} (Fonte: ${ddgData.AbstractURL || 'DuckDuckGo'})`);
      }
      if (Array.isArray(ddgData.RelatedTopics)) {
        for (const topic of ddgData.RelatedTopics.slice(0, 4)) {
          if (topic.Text && topic.FirstURL) {
            results.push(`• ${topic.Text} - ${topic.FirstURL}`);
          }
        }
      }

      if (results.length > 0) {
        return `\n\n[Resultados da Busca Web via DuckDuckGo (Pesquisa: "${query}")]:\n${results.join('\n')}`;
      }
    }
  } catch {
    // try next fallback
  }

  // 3. Fallback: Wikipedia PT API
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 3500);
    const wikiRes = await fetch(`https://pt.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(query)}&utf8=&format=json&origin=*`, { signal: controller.signal });
    clearTimeout(timer);

    if (wikiRes.ok) {
      const wikiData: any = await wikiRes.json();
      const items = wikiData?.query?.search || [];
      if (Array.isArray(items) && items.length > 0) {
        const formatted = items.slice(0, 3).map((item: any, idx: number) => {
          const cleanSnippet = (item.snippet || '').replace(/<[^>]*>/g, '');
          return `${idx + 1}. **${item.title}**: ${cleanSnippet} (https://pt.wikipedia.org/wiki/${encodeURIComponent(item.title)})`;
        }).join('\n');

        return `\n\n[Resultados da Busca Web via Wikipédia (Pesquisa: "${query}")]:\n${formatted}`;
      }
    }
  } catch {
    // ignore
  }

  return null;
}

// Helper to perform live web search if user query expresses search intent
async function performWebSearchIfRequested(msgs: any[]): Promise<string | null> {
  if (!Array.isArray(msgs) || msgs.length === 0) return null;
  const lastMsg = msgs[msgs.length - 1];
  const lastText = (lastMsg?.text || lastMsg?.content || "").toString().trim();

  if (!lastText) return null;

  const isSearchIntent = /\b(pesquisar|pesquise|busca|buscar|busque|procure|procurar|search|google|notícias|noticias|acidente|aconteceu|quem é|o que é|quem foi|sobre|aivisionslab|site|web|internet)\b/i.test(lastText);
  if (!isSearchIntent) return null;

  return performWebSearchDirect(lastText);
}

// Helper to process images attached in chat for local providers via Phoenix Engine vision
async function processMessageImages(msgs: any[]): Promise<any[]> {
  const formattedMsgs = [];
  const searchResults = await performWebSearchIfRequested(msgs);

  for (let i = 0; i < msgs.length; i++) {
    const m = msgs[i];
    let textContent = m.text || m.content || "";
    
    // Attach web search results to the latest user prompt if search was executed
    if (i === msgs.length - 1 && searchResults) {
      textContent += searchResults;
    }

    // If there's an image attached, process it via Phoenix Engine vision
    if (m.image) {
      try {
        const match = m.image.match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,(.+)$/);
        if (match) {
          const imageBuffer = Buffer.from(match[2], "base64");
          const formData = new FormData();
          formData.append("file", new Blob([imageBuffer], { type: match[1] }), "attachment.png");
          formData.append("prompt", "Descreva esta imagem em detalhes em Português.");
          
          const descRes = await fetch(`${PHOENIX_ENGINE_URL}/api/describe-image`, {
            method: "POST",
            body: formData
          });
          if (descRes.ok) {
            const descData: any = await descRes.json();
            if (descData && descData.text) {
              textContent += `\n\n[Contexto e Análise da Imagem Anexada via MiniCPM-V 2.6]:\n${descData.text}`;
            }
          }
        }
      } catch (e) {
        console.error("Failed to process image for chat via MiniCPM-V:", e);
      }
    }
    
    formattedMsgs.push({
      role: m.role === "assistant" ? "assistant" : "user",
      content: textContent,
    });
  }
  return formattedMsgs;
}

// 4. Provider Chat Completion Proxy
app.post("/api/proxy/chat", async (req, res) => {
  const { providerType, baseUrl, apiKey, model, messages, temperature, maxTokens, systemInstruction } = req.body;

  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (apiKey) {
      headers["Authorization"] = `Bearer ${apiKey}`;
    }

    let endpointUrl = "";
    let payload: any = {};

    // Date Context Injection
    const currentDateStr = new Date().toLocaleDateString("pt-BR", {
      year: "numeric",
      month: "long",
      day: "numeric",
      weekday: "long"
    });
    const currentYear = new Date().getFullYear();
    const systemDateContext = `[Informação do Sistema: A data atual do sistema é ${currentDateStr} (Ano Atual: ${currentYear}). Considere o ano de ${currentYear} como o ano corrente em todas as análises e respostas.]`;

    const effectiveSystemInstruction = systemInstruction
      ? `${systemDateContext}\n\n${systemInstruction}`
      : systemDateContext;

    if (providerType === "ollama") {
      endpointUrl = `${baseUrl.replace(/\/$/, "")}/api/chat`;
      const formattedMsgs = [];
      formattedMsgs.push({ role: "system", content: effectiveSystemInstruction });
      if (Array.isArray(messages)) {
        const processedMsgs = await processMessageImages(messages);
        formattedMsgs.push(...processedMsgs);
      }
      payload = {
        model,
        messages: formattedMsgs,
        stream: false,
        options: {
          temperature: typeof temperature === "number" ? temperature : 0.7,
          num_predict: typeof maxTokens === "number" ? maxTokens : 2048,
        },
      };
    } else {
      // OpenAI / LM Studio / vLLM compatible format
      endpointUrl = `${baseUrl.replace(/\/$/, "")}/chat/completions`;
      if (!endpointUrl.includes("/v1/")) {
        endpointUrl = `${baseUrl.replace(/\/$/, "")}/v1/chat/completions`;
      }
      const formattedMsgs = [];
      formattedMsgs.push({ role: "system", content: effectiveSystemInstruction });
      if (Array.isArray(messages)) {
        const processedMsgs = await processMessageImages(messages);
        formattedMsgs.push(...processedMsgs);
      }
      payload = {
        model,
        messages: formattedMsgs,
        temperature: typeof temperature === "number" ? temperature : 0.7,
        max_tokens: typeof maxTokens === "number" ? maxTokens : 2048,
        stream: false,
      };
    }

    const startTime = Date.now();
    const response = await fetch(endpointUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });

    const endTime = Date.now();
    const durationMs = endTime - startTime;

    if (!response.ok) {
      const errText = await response.text();
      res.status(response.status).json({
        error: `Endpoint returned error (${response.status}): ${errText.slice(0, 300)}`,
      });
      return;
    }

    const data: any = await response.json();
    let textResult = "";
    if (providerType === "ollama") {
      textResult = data.message?.content || "";
    } else {
      textResult = data.choices?.[0]?.message?.content || "";
    }

    const completionTokensEst = Math.ceil(textResult.length / 4);
    const tokensPerSec = durationMs > 0 ? ((completionTokensEst / durationMs) * 1000).toFixed(1) : "0";

    res.json({
      text: textResult,
      usage: {
        promptTokens: data.usage?.prompt_tokens || 0,
        completionTokens: data.usage?.completion_tokens || completionTokensEst,
        durationMs,
        tokensPerSec: parseFloat(tokensPerSec),
      },
    });
  } catch (err: any) {
    res.status(500).json({
      error: `Proxy request failed: ${err.message || "Network error"}`,
    });
  }
});

// 4.5 Multimodal Vision Bridge (MiniCPM-V + mmproj-model-f16.gguf + Gemini Fallback)
app.post("/api/describe-image", async (req, res) => {
  const { imageDataUrl, prompt } = req.body as { imageDataUrl?: string; prompt?: string };

  if (!imageDataUrl || typeof imageDataUrl !== "string") {
    res.status(400).json({ error: "Parâmetro 'imageDataUrl' ausente ou inválido." });
    return;
  }

  const match = imageDataUrl.match(/^data:(image\/[a-zA-Z0-9.+-]+);base64,(.*)$/);
  if (!match) {
    res.status(400).json({ error: "'imageDataUrl' não é uma data URL de imagem base64 válida." });
    return;
  }
  const [, mimeType, base64Payload] = match;

  // Try Phoenix Engine (Port 8000) first for local MiniCPM-V vision
  try {
    const imageBuffer = Buffer.from(base64Payload, "base64");
    const formData = new FormData();
    formData.append("file", new Blob([imageBuffer], { type: mimeType }), "attachment.png");
    if (prompt && prompt.trim()) {
      formData.append("prompt", prompt);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 90_000);

    const response = await fetch(`${PHOENIX_ENGINE_URL}/api/describe-image`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (response.ok) {
      const data: any = await response.json();
      if (!data.error && data.text) {
        res.json({
          text: data.text,
          engine: "MiniCPM-V 2.6 (Phoenix Engine / Vulkan)",
          mmprojRequired: "mmproj-model-f16.gguf",
        });
        return;
      }
    }
  } catch {
    // Phoenix Engine offline or booting
  }

  // Fallback: If Gemini API key is available, use Gemini 3.6 Flash for vision
  if (process.env.GEMINI_API_KEY) {
    try {
      const ai = getGeminiClient();
      const response = await ai.models.generateContent({
        model: "gemini-3.6-flash",
        contents: [
          {
            role: "user",
            parts: [
              { text: prompt || "Descreva esta imagem em detalhes em Português do Brasil para narração em áudio." },
              { inlineData: { mimeType, data: base64Payload } },
            ],
          },
        ],
      });

      res.json({
        text: response.text || "Análise de imagem concluída.",
        engine: "Gemini 3.6 Flash (Nuvem / Visão Multimodal)",
        notice: "MiniCPM-V local requer os arquivos mmproj-model-f16.gguf e ggml-model-Q6_K.gguf no Phoenix Engine.",
        downloadLinks: {
          projector: "https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf/resolve/main/mmproj-model-f16.gguf?download=true",
          modelWeights: "https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf/resolve/main/ggml-model-Q6_K.gguf?download=true",
        },
      });
      return;
    } catch (geminiErr: any) {
      console.error("Gemini Vision Fallback Error:", geminiErr);
    }
  }

  res.status(503).json({
    error: "MiniCPM-V 2.6 local necessita do projetor 'mmproj-model-f16.gguf' e do modelo de linguagem 'ggml-model-Q6_K.gguf' em Workstations/Models/Chat/GGUF/.",
    downloadLinks: {
      projector: "https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf/resolve/main/mmproj-model-f16.gguf?download=true",
      modelWeights: "https://huggingface.co/openbmb/MiniCPM-V-2_6-gguf/resolve/main/ggml-model-Q6_K.gguf?download=true",
    },
    instruction: "Baixe o mmproj-model-f16.gguf e salve na pasta Workstations/Models/Chat/GGUF/ da Phoenix Engine.",
  });
});

// Search Endpoint (SearXNG + DuckDuckGo + Wikipedia Fallback)
app.get("/api/search", async (req, res) => {
  const q = (req.query.q || req.query.query || "").toString().trim();
  if (!q) {
    res.status(400).json({ error: "Parâmetro 'q' ou 'query' na URL é obrigatório." });
    return;
  }

  const resultText = await performWebSearchDirect(q);
  res.json({
    ok: !!resultText,
    query: q,
    results: resultText || "Nenhum resultado encontrado na internet.",
  });
});

app.post("/api/search", async (req, res) => {
  const q = (req.body.q || req.body.query || "").toString().trim();
  if (!q) {
    res.status(400).json({ error: "Parâmetro 'q' ou 'query' no corpo é obrigatório." });
    return;
  }

  const resultText = await performWebSearchDirect(q);
  res.json({
    ok: !!resultText,
    query: q,
    results: resultText || "Nenhum resultado encontrado na internet.",
  });
});

// Proxy to Engine endpoints

app.post("/api/engine/generate-image", async (req, res) => {
  const { prompt } = req.body as { prompt?: string };

  if (!prompt || typeof prompt !== "string" || !prompt.trim()) {
    res.status(400).json({ error: "Parâmetro 'prompt' é obrigatório." });
    return;
  }

  const cleanPrompt = prompt
    .replace(/^(cria|crie|gerar|gera|desenha|desenhe|make|create|generate|draw)\s+(uma\s+|um\s+)?(imagem|foto|arte|desenho|ilusalcao|ilustração|image|picture|photo)?\s+(de|da|do|sobre|for|about)?\s*/i, "")
    .trim() || prompt;

  console.log(`[ImageGen] Gerando imagem para o prompt: "${cleanPrompt}" (Original: "${prompt}")`);

  // 1. Try local Phoenix Engine (Port 8000) SD / SDXL / FLUX pipeline
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 6000);
    const r = await fetch(`${PHOENIX_ENGINE_URL}/api/generate-image`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: cleanPrompt }),
      signal: controller.signal,
    });
    clearTimeout(timer);

    if (r.ok) {
      const data: any = await r.json();
      if (data && (data.imageUrl || data.image || data.url || data.base64)) {
        res.json({
          imageUrl: data.imageUrl || data.image || data.url || (data.base64 ? `data:image/png;base64,${data.base64}` : null),
          prompt: cleanPrompt,
          engine: data.engine || "Phoenix Engine (Diffusers SD/FLUX Local GPU)",
        });
        return;
      }
    }
  } catch {
    // Local Phoenix Engine SD offline or not running
  }

  // 2. Pollinations AI (FLUX / SDXL Cloud High-Res Neural Engine) Fallback
  try {
    const seed = Math.floor(Math.random() * 1000000);
    const pollinationsUrl = `https://image.pollinations.ai/prompt/${encodeURIComponent(cleanPrompt)}?width=1024&height=1024&seed=${seed}&nologo=true&model=flux`;

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 18000);
    const imgRes = await fetch(pollinationsUrl, { signal: controller.signal });
    clearTimeout(timer);

    if (imgRes.ok) {
      const buffer = await imgRes.arrayBuffer();
      const base64Img = Buffer.from(buffer).toString("base64");
      const dataUrl = `data:image/jpeg;base64,${base64Img}`;

      res.json({
        imageUrl: dataUrl,
        prompt: cleanPrompt,
        engine: "Phoenix Visual Engine (FLUX Neural Renderer)",
      });
      return;
    }
  } catch (err: any) {
    console.error("[ImageGen] Erro no fallback do motor visual:", err);
  }

  res.status(500).json({ error: "Não foi possível renderizar a imagem no momento. Verifique se a GPU local está ativa ou a conexão com a internet." });
});

// 5. Piper TTS - List Available Local Neural Voices
app.get("/api/tts/voices", (_req, res) => {
  res.json({
    engine: "Piper TTS (OHF-Voice / piper1-gpl / ONNX)",
    license: "GPL-3.0 / MIT",
    status: "ready",
    availableVoices: [
      // Português (Brasil & Portugal)
      {
        id: "pt_BR-faber-medium",
        name: "Faber (Brasil PT-BR)",
        language: "pt-BR",
        quality: "medium",
        sampleRate: 22050,
        gender: "male",
        description: "Voz neural masculina padrão para português do Brasil (OHF-Voice / Piper ONNX)",
        onnxModel: "pt_BR-faber-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx",
      },
      {
        id: "pt_BR-cadu-medium",
        name: "Cadu (Brasil PT-BR)",
        language: "pt-BR",
        quality: "medium",
        sampleRate: 22050,
        gender: "male",
        description: "Voz masculina clara e pausada para leitura de textos longos e narração",
        onnxModel: "pt_BR-cadu-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/cadu/medium/pt_BR-cadu-medium.onnx",
      },
      {
        id: "pt_BR-edresson-low",
        name: "Edresson (Brasil PT-BR)",
        language: "pt-BR",
        quality: "low",
        sampleRate: 16000,
        gender: "male",
        description: "Modelo ultra-leve otimizado para baixa utilização de CPU e latência mínima",
        onnxModel: "pt_BR-edresson-low.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/edresson/low/pt_BR-edresson-low.onnx",
      },
      {
        id: "pt_BR-jeff-medium",
        name: "Jeff (Brasil PT-BR)",
        language: "pt-BR",
        quality: "medium",
        sampleRate: 22050,
        gender: "male",
        description: "Voz masculina conversacional para assistentes autônomos e podcasts",
        onnxModel: "pt_BR-jeff-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/jeff/medium/pt_BR-jeff-medium.onnx",
      },
      {
        id: "pt_PT-tugão-medium",
        name: "Tugão (Portugal PT-PT)",
        language: "pt-PT",
        quality: "medium",
        sampleRate: 22050,
        gender: "male",
        description: "Voz masculina neural em português de Portugal",
        onnxModel: "pt_PT-tugão-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_PT/tug%C3%A3o/medium/pt_PT-tug%C3%A3o-medium.onnx",
      },

      // English (United States & Great Britain)
      {
        id: "en_US-lessac-high",
        name: "Lessac (EUA EN-US High)",
        language: "en-US",
        quality: "high",
        sampleRate: 22050,
        gender: "female",
        description: "Voz feminina neural de alta fidelidade sintética e entonação natural",
        onnxModel: "en_US-lessac-high.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx",
      },
      {
        id: "en_US-lessac-medium",
        name: "Lessac (EUA EN-US Medium)",
        language: "en-US",
        quality: "medium",
        sampleRate: 22050,
        gender: "female",
        description: "Versão balanceada da voz feminina Lessac para síntese rápida",
        onnxModel: "en_US-lessac-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
      },
      {
        id: "en_US-ryan-high",
        name: "Ryan (EUA EN-US High)",
        language: "en-US",
        quality: "high",
        sampleRate: 22050,
        gender: "male",
        description: "Voz masculina em alta definição para narração de áudio e tutoriais",
        onnxModel: "en_US-ryan-high.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx",
      },
      {
        id: "en_US-ryan-medium",
        name: "Ryan (EUA EN-US Medium)",
        language: "en-US",
        quality: "medium",
        sampleRate: 22050,
        gender: "male",
        description: "Voz masculina fluida e moderna para assistentes e leitura de notícias",
        onnxModel: "en_US-ryan-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx",
      },
      {
        id: "en_US-amy-medium",
        name: "Amy (EUA EN-US)",
        language: "en-US",
        quality: "medium",
        sampleRate: 22050,
        gender: "female",
        description: "Voz feminina expressiva ideal para resumos de documentos e artigos",
        onnxModel: "en_US-amy-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
      },
      {
        id: "en_US-danny-low",
        name: "Danny (EUA EN-US)",
        language: "en-US",
        quality: "low",
        sampleRate: 16000,
        gender: "male",
        description: "Voz masculina rápida e leve para ambientes com recursos limitados",
        onnxModel: "en_US-danny-low.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/danny/low/en_US-danny-low.onnx",
      },
      {
        id: "en_US-ljspeech-high",
        name: "LJSpeech (EUA EN-US High)",
        language: "en-US",
        quality: "high",
        sampleRate: 22050,
        gender: "female",
        description: "Dataset clássico de audiolivro com pronúncia cristalina e ritmo firme",
        onnxModel: "en_US-ljspeech-high.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ljspeech/high/en_US-ljspeech-high.onnx",
      },
      {
        id: "en_GB-alan-medium",
        name: "Alan (Grã-Bretanha EN-GB)",
        language: "en-GB",
        quality: "medium",
        sampleRate: 22050,
        gender: "male",
        description: "Voz masculina com sotaque britânico clássico",
        onnxModel: "en_GB-alan-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx",
      },
      {
        id: "en_GB-alba-medium",
        name: "Alba (Grã-Bretanha EN-GB)",
        language: "en-GB",
        quality: "medium",
        sampleRate: 22050,
        gender: "female",
        description: "Voz feminina britânica clara para apresentações e relatórios",
        onnxModel: "en_GB-alba-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx",
      },

      // Español
      {
        id: "es_ES-davefx-medium",
        name: "Davefx (Espanha ES-ES)",
        language: "es-ES",
        quality: "medium",
        sampleRate: 22050,
        gender: "male",
        description: "Voz masculina em espanhol europeu para leitura e assistentes",
        onnxModel: "es_ES-davefx-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
      },
      {
        id: "es_MX-ald-medium",
        name: "Ald (México ES-MX)",
        language: "es-MX",
        quality: "medium",
        sampleRate: 22050,
        gender: "male",
        description: "Voz masculina neutra em espanhol latino-americano",
        onnxModel: "es_MX-ald-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx",
      },
      {
        id: "es_AR-daniela-high",
        name: "Daniela (Argentina ES-AR)",
        language: "es-AR",
        quality: "high",
        sampleRate: 22050,
        gender: "female",
        description: "Voz feminina em alta definição com sotaque rioplatense",
        onnxModel: "es_AR-daniela-high.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx",
      },

      // Deutsch & Français & Italiano & Nordics & Asia
      {
        id: "de_DE-thorsten-medium",
        name: "Thorsten (Alemanha DE-DE)",
        language: "de-DE",
        quality: "medium",
        sampleRate: 22050,
        gender: "male",
        description: "Voz masculina alemã neural desenvolvida pela comunidade Thorsten-Voice",
        onnxModel: "de_DE-thorsten-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx",
      },
      {
        id: "fr_FR-siwis-medium",
        name: "Siwis (França FR-FR)",
        language: "fr-FR",
        quality: "medium",
        sampleRate: 22050,
        gender: "female",
        description: "Voz feminina francesa de alta precisão fonética",
        onnxModel: "fr_FR-siwis-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx",
      },
      {
        id: "it_IT-paola-medium",
        name: "Paola (Itália IT-IT)",
        language: "it-IT",
        quality: "medium",
        sampleRate: 22050,
        gender: "female",
        description: "Voz feminina italiana expressiva e melódica",
        onnxModel: "it_IT-paola-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx",
      },
      {
        id: "zh_CN-huayan-medium",
        name: "Huayan (China ZH-CN)",
        language: "zh-CN",
        quality: "medium",
        sampleRate: 22050,
        gender: "female",
        description: "Voz feminina em chinês mandarim",
        onnxModel: "zh_CN-huayan-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
      },
      {
        id: "ko_KR-kss-medium",
        name: "KSS (Coréia do Sul KO-KR)",
        language: "ko-KR",
        quality: "medium",
        sampleRate: 22050,
        gender: "female",
        description: "Voz feminina coreana neural",
        onnxModel: "ko_KR-kss-medium.onnx",
        downloadUrl: "https://huggingface.co/rhasspy/piper-voices/resolve/main/ko/ko_KR/kss/medium/ko_KR-kss-medium.onnx",
      },
    ],
  });
});

// 6. Piper TTS - Synthesize Audio Endpoint
app.post("/api/tts/piper", async (req, res) => {
  try {
    const { text, voice, speed } = req.body;

    if (!text || typeof text !== "string") {
      res.status(400).json({ error: "Campo 'text' é obrigatório." });
      return;
    }

    const selectedVoice = voice || "pt_BR-faber-medium";
    const numSpeed = typeof speed === "number" ? speed : 1.0;

    // Phoenix Engine TTS (Port 8000) native Piper TTS
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 10000);
      const engineRes = await fetch(`${PHOENIX_ENGINE_URL}/api/synthesize-speech`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          voice: selectedVoice,
          length_scale: 1.0 / Math.max(0.1, numSpeed),
        }),
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (engineRes.ok) {
        const engineData: any = await engineRes.json();
        if (engineData.audio_base64) {
          res.json({
            success: true,
            engine: `Piper TTS (${engineData.voice || selectedVoice} / Phoenix Engine)`,
            voice: engineData.voice || selectedVoice,
            format: "wav",
            audioUrl: `data:${engineData.mime_type || "audio/wav"};base64,${engineData.audio_base64}`,
          });
          return;
        }
      } else {
        const errData: any = await engineRes.json().catch(() => ({}));
        console.warn("[Piper Server Proxy] Phoenix Engine TTS returned error:", errData);
      }
    } catch (err: any) {
      console.warn("[Piper Server Proxy] Phoenix Engine offline or unreachable:", err.message);
    }

    // If Phoenix Engine is offline or failed, return 503 so frontend uses high-quality Web Speech API
    res.status(503).json({
      success: false,
      fallback: true,
      error: "Phoenix Engine Piper TTS indisponível. Utilizando síntese natural do navegador.",
    });
  } catch (err: any) {
    console.error("Piper TTS Error:", err);
    res.status(500).json({
      error: `Falha na síntese de voz Piper: ${err.message || "Erro interno"}`,
    });
  }
});

// Setup Vite development server or production static serving
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Local & Cloud AI Studio server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
