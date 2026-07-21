# AIVisions Phoenix Engine 3.0 — Licença

**Copyright © 2026 AIVisionsLab Studio Group — Creative & Tech Solutions**

Este projeto (código-fonte, arquitetura de orquestração, documentação e
ativos associados) é distribuído sob a licença:

**Creative Commons Atribuição-NãoComercial 4.0 Internacional (CC BY-NC 4.0)**

Texto completo da licença: https://creativecommons.org/licenses/by-nc/4.0/deed.pt-BR

## Resumo em linguagem simples

Você tem permissão para:
- ✅ Usar este projeto livremente, para fins pessoais ou educacionais
- ✅ Copiar, modificar e redistribuir o código
- ✅ Compartilhar suas próprias versões/modificações

Desde que:
- 📌 **Atribuição** — dê crédito ao AIVisionsLab Studio Group como autor original, com link para o repositório oficial
- 🚫 **Não-Comercial** — não venda, revenda ou monetize este projeto (ou versões modificadas dele) sem autorização expressa e por escrito do AIVisionsLab Studio Group

## Sobre softwares e componentes de terceiros

A Phoenix Engine 3.0 **não distribui nem embute** nenhum software de
terceiros — ela orquestra, decide e executa ferramentas que permanecem
instaladas de forma independente, incluindo (mas não se limitando a):
- Docker / Docker Desktop
- Ollama
- llama.cpp
- stable-diffusion.cpp
- Open WebUI
- ChromaDB
- Vulkan SDK
- Visual Studio Build Tools
- Git

A Phoenix apenas detecta, decide, orienta e automatiza o download, a
compilação e a configuração dessas ferramentas diretamente de suas
fontes oficiais. Cada uma delas permanece sob sua **própria licença
original**, definida por seus respectivos autores/mantenedores. Ao
utilizar a Phoenix Engine, você concorda em também respeitar os termos
de licença de cada ferramenta de terceiro que ela instalar ou
orquestrar em seu nome.

Esta licença cobre exclusivamente:
- O código-fonte deste repositório (kernel, engines, event bus, contratos, terminal web/CLI)
- A arquitetura de decisão e orquestração (Knowledge Engine/RAG, Rules Engine, Runtime Engine, Mission Planner)
- A documentação e os ativos (textos, manifesto, templates, interface visual) originais deste projeto

## Sobre os módulos irmãos do ecossistema AIVisions

A Phoenix Engine consome, via SDK/contrato público, dados fornecidos
por módulos irmãos do ecossistema AIVisions — como o **AIVisions
Hardware Discovery Core** (descoberta de hardware) e o **AIVisions
Hardware Telemetry Core** (observação contínua de estado da máquina).
Esses módulos são projetos próprios, com suas próprias licenças e
ciclos de distribuição — esta licença **não** cobre o código-fonte
deles, apenas a forma como a Phoenix os consome através do seu SDK
público.

## Licenciamento comercial

O AIVisionsLab Studio Group reserva-se o direito de oferecer, em
paralelo, licenças comerciais específicas (com termos de suporte, uso
empresarial ou distribuição comercial) mediante acordo separado. A
disponibilização deste projeto sob CC BY-NC 4.0 não impede o titular
original dos direitos autorais de licenciar a mesma obra sob termos
adicionais para terceiros interessados em uso comercial.

Para consultas sobre licenciamento comercial, entre em contato através
dos canais oficiais do AIVisionsLab.

---

*Este documento é uma licença de código aberto e não constitui
aconselhamento jurídico. Para questões contratuais específicas
(especialmente relacionadas a licenciamento comercial futuro),
recomenda-se consultoria jurídica especializada.*
