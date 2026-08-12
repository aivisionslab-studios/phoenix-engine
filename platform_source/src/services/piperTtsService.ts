import { PiperVoice } from '../types';

export const DEFAULT_PIPER_VOICES: PiperVoice[] = [
  // Português (Brasil & Portugal)
  {
    id: 'pt_BR-faber-medium',
    name: 'Faber (Brasil PT-BR)',
    language: 'pt-BR',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz neural masculina padrão para português do Brasil (OHF-Voice / Piper ONNX)',
    onnxModel: 'pt_BR-faber-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx',
  },
  {
    id: 'pt_BR-cadu-medium',
    name: 'Cadu (Brasil PT-BR)',
    language: 'pt-BR',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina clara e pausada para leitura de textos longos e narração',
    onnxModel: 'pt_BR-cadu-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/cadu/medium/pt_BR-cadu-medium.onnx',
  },
  {
    id: 'pt_BR-edresson-low',
    name: 'Edresson (Brasil PT-BR)',
    language: 'pt-BR',
    quality: 'low',
    sampleRate: 16000,
    gender: 'male',
    description: 'Modelo ultra-leve otimizado para baixa utilização de CPU e latência mínima',
    onnxModel: 'pt_BR-edresson-low.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/edresson/low/pt_BR-edresson-low.onnx',
  },
  {
    id: 'pt_BR-jeff-medium',
    name: 'Jeff (Brasil PT-BR)',
    language: 'pt-BR',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina conversacional para assistentes autônomos e podcasts',
    onnxModel: 'pt_BR-jeff-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/jeff/medium/pt_BR-jeff-medium.onnx',
  },
  {
    id: 'pt_PT-tugão-medium',
    name: 'Tugão (Portugal PT-PT)',
    language: 'pt-PT',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina neural em português de Portugal',
    onnxModel: 'pt_PT-tugão-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_PT/tug%C3%A3o/medium/pt_PT-tug%C3%A3o-medium.onnx',
  },

  // English (United States & Great Britain)
  {
    id: 'en_US-lessac-high',
    name: 'Lessac (EUA EN-US High)',
    language: 'en-US',
    quality: 'high',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina neural de alta fidelidade sintética e entonação natural',
    onnxModel: 'en_US-lessac-high.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/high/en_US-lessac-high.onnx',
  },
  {
    id: 'en_US-lessac-medium',
    name: 'Lessac (EUA EN-US Medium)',
    language: 'en-US',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Versão balanceada da voz feminina Lessac para síntese rápida',
    onnxModel: 'en_US-lessac-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx',
  },
  {
    id: 'en_US-ryan-high',
    name: 'Ryan (EUA EN-US High)',
    language: 'en-US',
    quality: 'high',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em alta definição para narração de áudio e tutoriais',
    onnxModel: 'en_US-ryan-high.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx',
  },
  {
    id: 'en_US-ryan-medium',
    name: 'Ryan (EUA EN-US Medium)',
    language: 'en-US',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina fluida e moderna para assistentes e leitura de notícias',
    onnxModel: 'en_US-ryan-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx',
  },
  {
    id: 'en_US-amy-medium',
    name: 'Amy (EUA EN-US)',
    language: 'en-US',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina expressiva ideal para resumos de documentos e artigos',
    onnxModel: 'en_US-amy-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx',
  },
  {
    id: 'en_US-danny-low',
    name: 'Danny (EUA EN-US)',
    language: 'en-US',
    quality: 'low',
    sampleRate: 16000,
    gender: 'male',
    description: 'Voz masculina rápida e leve para ambientes com recursos limitados',
    onnxModel: 'en_US-danny-low.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/danny/low/en_US-danny-low.onnx',
  },
  {
    id: 'en_US-ljspeech-high',
    name: 'LJSpeech (EUA EN-US High)',
    language: 'en-US',
    quality: 'high',
    sampleRate: 22050,
    gender: 'female',
    description: 'Dataset clássico de audiolivro com pronúncia cristalina e ritmo firme',
    onnxModel: 'en_US-ljspeech-high.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ljspeech/high/en_US-ljspeech-high.onnx',
  },
  {
    id: 'en_US-bryce-medium',
    name: 'Bryce (EUA EN-US)',
    language: 'en-US',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina natural para agentes de diálogo e e-learning',
    onnxModel: 'en_US-bryce-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/bryce/medium/en_US-bryce-medium.onnx',
  },
  {
    id: 'en_GB-alan-medium',
    name: 'Alan (Grã-Bretanha EN-GB)',
    language: 'en-GB',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina com sotaque britânico clássico',
    onnxModel: 'en_GB-alan-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx',
  },
  {
    id: 'en_GB-alba-medium',
    name: 'Alba (Grã-Bretanha EN-GB)',
    language: 'en-GB',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina britânica clara para apresentações e relatórios',
    onnxModel: 'en_GB-alba-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx',
  },
  {
    id: 'en_GB-cori-high',
    name: 'Cori (Grã-Bretanha EN-GB High)',
    language: 'en-GB',
    quality: 'high',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina britânica em alta definição sintética',
    onnxModel: 'en_GB-cori-high.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/cori/high/en_GB-cori-high.onnx',
  },

  // Español
  {
    id: 'es_ES-davefx-medium',
    name: 'Davefx (Espanha ES-ES)',
    language: 'es-ES',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em espanhol europeu para leitura e assistentes',
    onnxModel: 'es_ES-davefx-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx',
  },
  {
    id: 'es_ES-carlfm-x_low',
    name: 'Carlfm (Espanha ES-ES)',
    language: 'es-ES',
    quality: 'low',
    sampleRate: 16000,
    gender: 'male',
    description: 'Voz masculina leve em espanhol europeu para resposta ultra-rápida',
    onnxModel: 'es_ES-carlfm-x_low.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/carlfm/x_low/es_ES-carlfm-x_low.onnx',
  },
  {
    id: 'es_MX-ald-medium',
    name: 'Ald (México ES-MX)',
    language: 'es-MX',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina neutra em espanhol latino-americano',
    onnxModel: 'es_MX-ald-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx',
  },
  {
    id: 'es_AR-daniela-high',
    name: 'Daniela (Argentina ES-AR)',
    language: 'es-AR',
    quality: 'high',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina em alta definição com sotaque rioplatense',
    onnxModel: 'es_AR-daniela-high.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/es_AR-daniela-high.onnx',
  },

  // Deutsch & Français & Italiano
  {
    id: 'de_DE-thorsten-high',
    name: 'Thorsten (Alemanha DE-DE High)',
    language: 'de-DE',
    quality: 'high',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina alemã em alta definição da comunidade Thorsten-Voice',
    onnxModel: 'de_DE-thorsten-high.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/high/de_DE-thorsten-high.onnx',
  },
  {
    id: 'de_DE-thorsten-medium',
    name: 'Thorsten (Alemanha DE-DE)',
    language: 'de-DE',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina alemã neural desenvolvida para narração',
    onnxModel: 'de_DE-thorsten-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx',
  },
  {
    id: 'de_DE-eva_k-x_low',
    name: 'Eva K (Alemanha DE-DE)',
    language: 'de-DE',
    quality: 'low',
    sampleRate: 16000,
    gender: 'female',
    description: 'Voz feminina alemã leve e ágil',
    onnxModel: 'de_DE-eva_k-x_low.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/eva_k/x_low/de_DE-eva_k-x_low.onnx',
  },
  {
    id: 'de_DE-karlsson-low',
    name: 'Karlsson (Alemanha DE-DE)',
    language: 'de-DE',
    quality: 'low',
    sampleRate: 16000,
    gender: 'male',
    description: 'Voz masculina alemã compacta',
    onnxModel: 'de_DE-karlsson-low.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/karlsson/low/de_DE-karlsson-low.onnx',
  },
  {
    id: 'fr_FR-siwis-medium',
    name: 'Siwis (França FR-FR)',
    language: 'fr-FR',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina francesa de alta precisão fonética',
    onnxModel: 'fr_FR-siwis-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx',
  },
  {
    id: 'fr_FR-gilles-low',
    name: 'Gilles (França FR-FR)',
    language: 'fr-FR',
    quality: 'low',
    sampleRate: 16000,
    gender: 'male',
    description: 'Voz masculina francesa leve para síntese rápida',
    onnxModel: 'fr_FR-gilles-low.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/gilles/low/fr_FR-gilles-low.onnx',
  },
  {
    id: 'fr_FR-tom-medium',
    name: 'Tom (França FR-FR)',
    language: 'fr-FR',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina francesa natural e moderna',
    onnxModel: 'fr_FR-tom-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/tom/medium/fr_FR-tom-medium.onnx',
  },
  {
    id: 'it_IT-paola-medium',
    name: 'Paola (Itália IT-IT)',
    language: 'it-IT',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina italiana expressiva e melódica',
    onnxModel: 'it_IT-paola-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx',
  },
  {
    id: 'it_IT-riccardo-x_low',
    name: 'Riccardo (Itália IT-IT)',
    language: 'it-IT',
    quality: 'low',
    sampleRate: 16000,
    gender: 'male',
    description: 'Voz masculina italiana compacta',
    onnxModel: 'it_IT-riccardo-x_low.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/riccardo/x_low/it_IT-riccardo-x_low.onnx',
  },

  // Русский & Українська
  {
    id: 'ru_RU-dmitri-medium',
    name: 'Dmitri (Rússia RU-RU)',
    language: 'ru-RU',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina russa neural com excelente dicção',
    onnxModel: 'ru_RU-dmitri-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx',
  },
  {
    id: 'ru_RU-irina-medium',
    name: 'Irina (Rússia RU-RU)',
    language: 'ru-RU',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina russa fluida para narração',
    onnxModel: 'ru_RU-irina-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx',
  },
  {
    id: 'ru_RU-denis-medium',
    name: 'Denis (Rússia RU-RU)',
    language: 'ru-RU',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina russa clara para leitura de notícias',
    onnxModel: 'ru_RU-denis-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/denis/medium/ru_RU-denis-medium.onnx',
  },
  {
    id: 'uk_UA-mykyta-high',
    name: 'Mykyta (Ucrânia UK-UA High)',
    language: 'uk-UA',
    quality: 'high',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina ucraniana em alta definição',
    onnxModel: 'uk_UA-mykyta-high.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/mykyta/high/uk_UA-mykyta-high.onnx',
  },
  {
    id: 'uk_UA-oleksa-high',
    name: 'Oleksa (Ucrânia UK-UA High)',
    language: 'uk-UA',
    quality: 'high',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina ucraniana expressiva para áudio',
    onnxModel: 'uk_UA-oleksa-high.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/oleksa/high/uk_UA-oleksa-high.onnx',
  },

  // Nederlands & Polski & Čeština & Magyar & Română
  {
    id: 'nl_NL-rdh-medium',
    name: 'Rdh (Holanda NL-NL)',
    language: 'nl-NL',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em holandês padrão',
    onnxModel: 'nl_NL-rdh-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/nl/nl_NL/rdh/medium/nl_NL-rdh-medium.onnx',
  },
  {
    id: 'nl_BE-nathalie-medium',
    name: 'Nathalie (Bélgica NL-BE)',
    language: 'nl-BE',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina em holandês belga (Flamengo)',
    onnxModel: 'nl_BE-nathalie-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/nl/nl_BE/nathalie/medium/nl_BE-nathalie-medium.onnx',
  },
  {
    id: 'pl_PL-darkman-medium',
    name: 'Darkman (Polônia PL-PL)',
    language: 'pl-PL',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em polonês para assistentes de voz',
    onnxModel: 'pl_PL-darkman-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/pl/pl_PL/darkman/medium/pl_PL-darkman-medium.onnx',
  },
  {
    id: 'pl_PL-gosia-medium',
    name: 'Gosia (Polônia PL-PL)',
    language: 'pl-PL',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina polonesa fluida',
    onnxModel: 'pl_PL-gosia-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/pl/pl_PL/gosia/medium/pl_PL-gosia-medium.onnx',
  },
  {
    id: 'cs_CZ-jirka-medium',
    name: 'Jirka (República Tcheca CS-CZ)',
    language: 'cs-CZ',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em tcheco',
    onnxModel: 'cs_CZ-jirka-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/cs/cs_CZ/jirka/medium/cs_CZ-jirka-medium.onnx',
  },
  {
    id: 'hu_HU-anna-medium',
    name: 'Anna (Hungria HU-HU)',
    language: 'hu-HU',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina em húngaro',
    onnxModel: 'hu_HU-anna-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/hu/hu_HU/anna/medium/hu_HU-anna-medium.onnx',
  },
  {
    id: 'ro_RO-mihai-medium',
    name: 'Mihai (Romênia RO-RO)',
    language: 'ro-RO',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em romeno',
    onnxModel: 'ro_RO-mihai-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/ro/ro_RO/mihai/medium/ro_RO-mihai-medium.onnx',
  },

  // Nordics (Suomi, Svenska, Dansk, Norsk, Íslenska)
  {
    id: 'fi_FI-harri-medium',
    name: 'Harri (Finlândia FI-FI)',
    language: 'fi-FI',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina finlandesa neural',
    onnxModel: 'fi_FI-harri-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/fi/fi_FI/harri/medium/fi_FI-harri-medium.onnx',
  },
  {
    id: 'sv_SE-lisa-medium',
    name: 'Lisa (Suécia SV-SE)',
    language: 'sv-SE',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina em sueco',
    onnxModel: 'sv_SE-lisa-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/sv/sv_SE/lisa/medium/sv_SE-lisa-medium.onnx',
  },
  {
    id: 'da_DK-talesyntese-medium',
    name: 'Talesyntese (Dinamarca DA-DK)',
    language: 'da-DK',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz dinamarquesa padrão',
    onnxModel: 'da_DK-talesyntese-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/da/da_DK/talesyntese/medium/da_DK-talesyntese-medium.onnx',
  },
  {
    id: 'no_NO-talesyntese-medium',
    name: 'Talesyntese (Noruega NO-NO)',
    language: 'no-NO',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz norueguesa neural',
    onnxModel: 'no_NO-talesyntese-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/no/no_NO/talesyntese/medium/no_NO-talesyntese-medium.onnx',
  },
  {
    id: 'is_IS-bui-medium',
    name: 'Búi (Islândia IS-IS)',
    language: 'is-IS',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina islandesa',
    onnxModel: 'is_IS-bui-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/is/is_IS/bui/medium/is_IS-bui-medium.onnx',
  },

  // Asia & Middle East & Other Global
  {
    id: 'zh_CN-huayan-medium',
    name: 'Huayan (China ZH-CN)',
    language: 'zh-CN',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina em chinês mandarim',
    onnxModel: 'zh_CN-huayan-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx',
  },
  {
    id: 'zh_CN-chaowen-medium',
    name: 'Chaowen (China ZH-CN)',
    language: 'zh-CN',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em chinês mandarim',
    onnxModel: 'zh_CN-chaowen-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/chaowen/medium/zh_CN-chaowen-medium.onnx',
  },
  {
    id: 'ko_KR-kss-medium',
    name: 'KSS (Coréia do Sul KO-KR)',
    language: 'ko-KR',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina coreana neural',
    onnxModel: 'ko_KR-kss-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/ko/ko_KR/kss/medium/ko_KR-kss-medium.onnx',
  },
  {
    id: 'hi_IN-pratham-medium',
    name: 'Pratham (Índia HI-IN)',
    language: 'hi-IN',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em híndi',
    onnxModel: 'hi_IN-pratham-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx',
  },
  {
    id: 'ar_JO-kareem-medium',
    name: 'Kareem (Jordânia AR-JO)',
    language: 'ar-JO',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em árabe',
    onnxModel: 'ar_JO-kareem-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/ar/ar_JO/kareem/medium/ar_JO-kareem-medium.onnx',
  },
  {
    id: 'vi_VN-vais1000-medium',
    name: 'VAIS1000 (Vietnã VI-VN)',
    language: 'vi-VN',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina em vietnamita',
    onnxModel: 'vi_VN-vais1000-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx',
  },
  {
    id: 'id_ID-news_tts-medium',
    name: 'News TTS (Indonésia ID-ID)',
    language: 'id-ID',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'female',
    description: 'Voz feminina em indonésio para leitura de notícias',
    onnxModel: 'id_ID-news_tts-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/id/id_ID/news_tts/medium/id_ID-news_tts-medium.onnx',
  },
  {
    id: 'tr_TR-dfki-medium',
    name: 'DFKI (Turquia TR-TR)',
    language: 'tr-TR',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em turco',
    onnxModel: 'tr_TR-dfki-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium/tr_TR-dfki-medium.onnx',
  },
  {
    id: 'he_IL-saspeech-medium',
    name: 'SASpeech (Israel HE-IL)',
    language: 'he-IL',
    quality: 'medium',
    sampleRate: 22050,
    gender: 'male',
    description: 'Voz masculina em hebraico',
    onnxModel: 'he_IL-saspeech-medium.onnx',
    downloadUrl: 'https://huggingface.co/rhasspy/piper-voices/resolve/main/he/he_IL/saspeech/medium/he_IL-saspeech-medium.onnx',
  },
];

let currentAudio: HTMLAudioElement | null = null;

export interface SpeakOptions {
  voiceId?: string;
  speed?: number;
  pitch?: number;
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (err: any) => void;
}

export const stopPiperSpeech = () => {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
};

export const cleanTextForSpeech = (text: string): string => {
  return text
    .replace(/<think>[\s\S]*?<\/think>/gi, '') // Remove DeepSeek/LLM think blocks
    .replace(/```[\s\S]*?```/g, ' Código omitido na leitura. ') // Replace code blocks
    .replace(/`([^`]+)`/g, '$1') // Remove inline code formatting
    .replace(/[*#_~]/g, '') // Remove markdown symbols
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Convert markdown links
    .replace(/\n+/g, '. ') // Replace linebreaks with pause
    .trim();
};

export const synthesizeAndPlayPiper = async (
  text: string,
  options: SpeakOptions = {}
): Promise<{ success: boolean; engine: string }> => {
  stopPiperSpeech();

  const clean = cleanTextForSpeech(text);
  if (!clean) {
    options.onEnd?.();
    return { success: false, engine: 'empty_text' };
  }

  const voiceId = options.voiceId || 'pt_BR-faber-medium';
  const speed = options.speed || 1.0;

  options.onStart?.();

  try {
    const response = await fetch('/api/tts/piper', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: clean,
        voice: voiceId,
        speed,
        pitch: options.pitch || 1.0,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      if (data.audioUrl) {
        const audio = new Audio(data.audioUrl);
        currentAudio = audio;
        audio.playbackRate = speed;

        audio.onended = () => {
          currentAudio = null;
          options.onEnd?.();
        };

        audio.onerror = (e) => {
          console.warn('Piper Audio playback error, falling back to WebSpeech:', e);
          currentAudio = null;
          fallbackToWebSpeech(clean, options);
        };

        await audio.play();
        return { success: true, engine: data.engine || 'Piper TTS (Local)' };
      }
    }
    
    // Server endpoint didn't yield audioUrl, fallback
    fallbackToWebSpeech(clean, options);
    return { success: true, engine: 'Web Speech API (Fallback)' };
  } catch (err) {
    console.warn('Piper API fetch error, falling back to Web Speech:', err);
    fallbackToWebSpeech(clean, options);
    return { success: true, engine: 'Web Speech API (Fallback)' };
  }
};

const getBestNaturalVoice = (isEn: boolean): SpeechSynthesisVoice | null => {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) return null;

  let voices = window.speechSynthesis.getVoices();
  if (!voices || voices.length === 0) return null;

  const langPrefix = isEn ? 'en' : 'pt';

  // Filter voices matching language
  const langVoices = voices.filter((v) => v.lang.toLowerCase().startsWith(langPrefix));

  if (langVoices.length === 0) {
    return voices.find((v) => v.lang.toLowerCase().startsWith('pt') || v.lang.toLowerCase().startsWith('en')) || null;
  }

  // Priority 1: Online / Natural / Neural voices (Edge/Chrome Microsoft Natural or Google Neural)
  const naturalVoice = langVoices.find((v) => {
    const name = v.name.toLowerCase();
    return name.includes('natural') || name.includes('online') || name.includes('neural') || name.includes('google');
  });
  if (naturalVoice) return naturalVoice;

  // Priority 2: Preferred Portuguese/English localized voices
  const preferredVoice = langVoices.find((v) => {
    const name = v.name.toLowerCase();
    return (
      name.includes('francisca') ||
      name.includes('antonio') ||
      name.includes('faber') ||
      name.includes('cadu') ||
      name.includes('daniel') ||
      name.includes('luciana') ||
      name.includes('maria') ||
      name.includes('amy') ||
      name.includes('ryan') ||
      name.includes('guy') ||
      name.includes('aria')
    );
  });
  if (preferredVoice) return preferredVoice;

  // Priority 3: Any voice matching language
  return langVoices[0] || null;
};

const fallbackToWebSpeech = (text: string, options: SpeakOptions) => {
  if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
    options.onError?.('Síntese de voz não suportada neste navegador.');
    options.onEnd?.();
    return;
  }

  window.speechSynthesis.cancel();

  const isEn = options.voiceId?.startsWith('en_') || false;

  const executeSpeak = () => {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = isEn ? 'en-US' : 'pt-BR';
    utterance.rate = options.speed || 1.0;
    utterance.pitch = options.pitch || 1.0;

    const matchedVoice = getBestNaturalVoice(isEn);
    if (matchedVoice) {
      utterance.voice = matchedVoice;
    }

    utterance.onend = () => options.onEnd?.();
    utterance.onerror = (e) => {
      options.onError?.(e);
      options.onEnd?.();
    };

    window.speechSynthesis.speak(utterance);
  };

  // Check if voices are loaded or need onvoiceschanged event
  const currentVoices = window.speechSynthesis.getVoices();
  if (currentVoices && currentVoices.length > 0) {
    executeSpeak();
  } else {
    let fired = false;
    window.speechSynthesis.onvoiceschanged = () => {
      if (!fired) {
        fired = true;
        executeSpeak();
      }
    };
    // Fallback trigger if event doesn't fire immediately
    setTimeout(() => {
      if (!fired) {
        fired = true;
        executeSpeak();
      }
    }, 200);
  }
};
