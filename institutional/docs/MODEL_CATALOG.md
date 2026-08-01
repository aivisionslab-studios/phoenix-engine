# Catálogo de Modelos — AIVisions Phoenix Engine

## Como funciona

O catálogo completo (regras de classificação, VRAM mínima, política de roteamento) vive em [`catalog/`](../../catalog) no repositório. A Phoenix classifica o hardware detectado (GPU Score + Machine Class) e recomenda modelos compatíveis — sem tentativa e erro.

## Exemplo de recomendação (hardware de referência: RX 580, 8GB VRAM)

```
VRAM detectada: 8192 MB
Machine Class: MEDIUM
GPU Score: 94%

Modelos recomendados:
★★★★★ qwen3:8b           — assistente geral, cabe 100% em VRAM
★★★★★ gemma3:4b          — muito rápido, baixo consumo
★★★★☆ qwen2.5-coder:7b   — programação
★★★★☆ llama3.2:3b        — uso geral / português

Modelos híbridos (VRAM + RAM):
★★★☆☆ deepseek-r1:14b    — raciocínio, offload parcial necessário

Não recomendado para este hardware:
✗ qwen3:30b
✗ llama3.3:70b
✗ deepseek-r1:671b
```

## Formatos suportados

- **GGUF** — modelos de linguagem quantizados, compatíveis com llama.cpp
- **Safetensors** — modelos de difusão de imagem, compatíveis com stable-diffusion.cpp/ComfyUI

## Licenciamento

Cada modelo listado no catálogo mantém sua **licença original**, definida pelo respectivo criador. A Phoenix apenas detecta, recomenda, baixa e organiza esses modelos localmente — nunca os redistribui sob licença própria (ver [Third Party Licenses](../legal/THIRD_PARTY_LICENSES.md)).
