# Política de Privacidade — AIVisions Phoenix Engine

A Phoenix Engine nasce com uma premissa central: **privacy first, local first**. Este documento explica exatamente o que acontece com seus dados.

## 1. Princípio geral

Por padrão, a Phoenix:

- ✅ Roda inteiramente local no seu hardware
- ✅ Prioriza processamento offline
- ✅ **Não** envia prompts para servidores da AIVisionsLab
- ✅ **Não** coleta conversas, documentos ou arquivos gerados
- ✅ **Não** envia imagens, áudios ou vídeos processados localmente
- ✅ **Não** exige cadastro ou conta para uso básico

## 2. Quando há comunicação externa

Comunicação com a internet ocorre apenas em ações explícitas, como:

- Download de modelos de IA (Hugging Face, catálogos AIVisionsLab, etc.);
- Verificação e instalação de atualizações;
- Acesso a repositórios GitHub (código, catálogos JSON de missões e conectores);
- Buscas web via SearXNG, quando o usuário solicita uma pesquisa;
- Sincronização com o Firestore da AIVisionsLab — **somente se o usuário habilitar explicitamente** essa opção.

Nenhuma dessas comunicações inclui o conteúdo dos seus prompts, documentos ou arquivos pessoais.

## 3. Firestore (opcional)

Caso o usuário autorize, dados de telemetria de hardware e uso agregado podem ser enviados ao Firestore da AIVisionsLab, com a finalidade de aprimorar versões futuras da Phoenix. Isso é **desativado por padrão** e detalhado na [Política de Telemetria](./TELEMETRY_POLICY.md).

## 4. Dados armazenados localmente

Toda a operação normal da Phoenix — logs, missões, histórico de aprovações, configurações — é armazenada localmente no seu próprio sistema, sob seu controle total. Você pode inspecionar, exportar ou apagar esses dados a qualquer momento.

## 5. Seus direitos

Como titular dos dados eventualmente compartilhados via telemetria opt-in, você pode:

- Desativar o envio de telemetria a qualquer momento;
- Solicitar informações sobre dados agregados associados ao seu uso, quando aplicável;
- Solicitar exclusão de dados enviados ao Firestore, dentro dos limites técnicos do serviço.

## 6. Menores de idade

A Phoenix não é direcionada a menores de idade e não coleta intencionalmente dados de menores.

## 7. Alterações nesta política

Mudanças relevantes nesta política serão comunicadas via `CHANGELOG.md` no repositório oficial.

## 8. Contato

Dúvidas sobre privacidade podem ser encaminhadas pelos canais oficiais da AIVisionsLab (ver `LEGAL_NOTICE.md`).
