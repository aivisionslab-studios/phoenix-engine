import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json({ limit: "25mb" }));

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

// 1. Health check
app.get("/api/health", (_req, res) => {
  res.json({
    status: "ok",
    hasGeminiKey: Boolean(process.env.GEMINI_API_KEY),
    timestamp: new Date().toISOString(),
  });
});

// 2. Gemini API Chat Endpoint
app.post("/api/gemini/chat", async (req, res) => {
  try {
    const { model, messages, systemInstruction, temperature, topP, topK, maxTokens } = req.body;
    const ai = getGeminiClient();

    const selectedModel = model || "gemini-3.6-flash";

    // Format chat messages for Gemini SDK
    // Convert previous user/assistant messages into contents history
    const contents: Array<{ role: string; parts: Array<{ text?: string; inlineData?: { mimeType: string; data: string } }> }> = [];

    if (Array.isArray(messages)) {
      for (const msg of messages) {
        const parts: Array<{ text?: string; inlineData?: { mimeType: string; data: string } }> = [];
        
        if (msg.text) {
          parts.push({ text: msg.text });
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

    const config: any = {};
    if (systemInstruction) config.systemInstruction = systemInstruction;
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

// 3. Provider Connection Ping / Discovery Proxy
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
    } else if (providerType === "lmstudio" || providerType === "openai" || providerType === "llama-server") {
      testUrl = `${baseUrl.replace(/\/$/, "")}/models`;
      if (!testUrl.startsWith("http")) testUrl = `http://${testUrl}`;
    } else if (providerType === "anthropic") {
      testUrl = `${baseUrl.replace(/\/$/, "")}/v1/models`;
      headers["x-api-key"] = apiKey || "";
      headers["anthropic-version"] = "2023-06-01";
    } else if (providerType === "stable-diffusion-cpp") {
      // sd-server não expõe /models nem /health — não é chat, é geração de
      // imagem (API estilo A1111). Aqui só confirmamos que a raiz responde.
      testUrl = baseUrl || "";
      if (!testUrl.startsWith("http")) testUrl = `http://${testUrl}`;
    }

    const startTime = Date.now();
    const response = await fetch(testUrl, {
      method: "GET",
      headers,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    const latencyMs = Date.now() - startTime;

    // sd-server (stable-diffusion.cpp) não tem endpoint GET padrão — qualquer
    // resposta HTTP (mesmo 404) já prova que o processo está de pé escutando
    // na porta. É bem diferente de chat providers, onde status ruim = offline.
    if (providerType === "stable-diffusion-cpp") {
      res.json({ online: true, latencyMs, status: response.status, models: [] });
      return;
    }

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
        modelsList = data.data.map((m: any) => m.id);
      } else if (Array.isArray(data.models)) {
        modelsList = data.models.map((m: any) => m.id || m.name);
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

    if (providerType === "ollama") {
      endpointUrl = `${baseUrl.replace(/\/$/, "")}/api/chat`;
      const formattedMsgs = [];
      if (systemInstruction) {
        formattedMsgs.push({ role: "system", content: systemInstruction });
      }
      if (Array.isArray(messages)) {
        messages.forEach((m: any) => {
          formattedMsgs.push({
            role: m.role === "assistant" ? "assistant" : "user",
            content: m.text || m.content || "",
          });
        });
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
      if (systemInstruction) {
        formattedMsgs.push({ role: "system", content: systemInstruction });
      }
      if (Array.isArray(messages)) {
        messages.forEach((m: any) => {
          formattedMsgs.push({
            role: m.role === "assistant" ? "assistant" : "user",
            content: m.text || m.content || "",
          });
        });
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

    // Modelo REAL que o servidor confirmou ter usado (ex: llama-server pode
    // ignorar o "model" pedido no request e sempre responder com o GGUF que
    // está de fato carregado). Cai pro nome pedido só se o servidor não
    // informar nada — nunca inventa um nome que não veio de algum lugar real.
    const confirmedModel = data.model || data.message?.model || model || null;

    res.json({
      text: textResult,
      model: confirmedModel,
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

// --- Busca na web via SearXNG (container "searxng-phoenix", porta 8080) ---
// Requer o formato JSON habilitado no settings.yml do SearXNG (ver guia:
// "Full Instructions (manual install).txt" — Passo 4, seção "formats:").
// Sem isso, o SearXNG devolve 403 Forbidden em vez de JSON.
app.post("/api/websearch", async (req, res) => {
  const { query, baseUrl } = req.body as { query?: string; baseUrl?: string };
  if (!query || !query.trim()) {
    res.status(400).json({ error: "Parâmetro 'query' vazio." });
    return;
  }
  const searxUrl = (baseUrl || "http://localhost:8080").replace(/\/$/, "");
  const searchUrl = `${searxUrl}/search?q=${encodeURIComponent(query)}&format=json`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);
    const response = await fetch(searchUrl, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (response.status === 403) {
      res.status(502).json({
        error: "SearXNG devolveu 403 Forbidden — o formato JSON provavelmente não está habilitado. " +
               "Verifique 'formats: [html, json]' em searxng/settings.yml e reinicie o container (ver guia, Passo 4).",
      });
      return;
    }
    if (!response.ok) {
      res.status(502).json({ error: `SearXNG devolveu status ${response.status}.` });
      return;
    }

    const data = await response.json();
    const results = Array.isArray(data.results)
      ? data.results.slice(0, 5).map((r: any) => ({
          title: r.title || "",
          url: r.url || "",
          content: r.content || "",
        }))
      : [];

    res.json({ query, results, count: results.length });
  } catch (err: any) {
    res.status(500).json({
      error: `Falha ao alcançar o SearXNG em ${searxUrl}: ${err.message || "erro de rede"}. ` +
             `Confirme que o container "searxng-phoenix" está rodando (docker ps).`,
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
    console.log(`Phoenix Aviary Platform server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
