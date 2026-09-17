# Lumina - Section Extractor (Laboratório Experimental)

Este repositório funciona como um **laboratório experimental** para o ecossistema do projeto **Lumina**. 

Seu propósito central é pesquisar, prototipar e validar abordagens de alto desempenho e baixo custo para **ler documentos PDF complexos** (como editais de licitação, contratos públicos e artigos científicos) e **extrair seções estruturadas e chunks enriquecidos com papéis semânticos**, sem depender de chamadas custosas e lentas a LLMs no processo inicial de ingestão.

---

## 🏛️ Arquitetura em Três Estágios Desacoplados

O pipeline adota uma **arquitetura orientada a estágios independentes**, implementada sob um paradigma **estritamente funcional** (funções puras, composições e pipelines de callables, utilizando classes apenas em `dataclass` e `Enum` para modelagem de dados):

```
PDF 
 │
 ├──▶ [Estágio 1: Extração Bruta (pymupdf4llm)]
 │     └─▶ Gera Markdown consolidado (.md) + Mapeamento de Páginas (_pages.json)
 │
 ├──▶ [Estágio 2: Limpeza Estrutural, Árvore e Classificação Semântica]
 │     ├─▶ Pipeline de 5 Cleaners Funcionais (Markup, Repetição, Merge, Numeração, Órfãos)
 │     ├─▶ Montagem da Árvore de Seções (Hierarquia e Delimitação de Texto)
 │     └─▶ SectionRoleClassifier (AliasRoleClassifier + PositionalAbstractFallbackClassifier)
 │     └─▶ Gera Árvores em JSON (_sections.json) e Relatórios (_sections.md)
 │
 └──▶ [Estágio 3: Chunking Inteligente e Enriquecimento Semântico]
       ├─▶ Fatiamento com RecursiveCharacterTextSplitter (somente seções longas)
       ├─▶ Injeção de Prefixo Contextual Leve [Título Imediato]
       ├─▶ Metadados Ricos (section_role, role_confidence, hierarchy_confidence, page_number)
       └─▶ Gera Chunks Prontos para Vetorização (_chunks.json e _chunks.md)
```

---

## 🔬 O que Utilizamos para Identificar Seções

Para alcançar alta fidelidade sem recorrer a LLMs para ler o documento inteiro a cada ingestão, combinamos técnicas determinísticas complementares:

1. **Extração de Layout e Markdown (`pymupdf4llm`)**:
   - Conversão de alta velocidade preservando marcadores de título (`#`, `##`, `###`), tabelas formatadas em texto e metadados por página (`page_chunks=True`).
2. **Fusão de Cabeçalhos Quebrados (`AdjacentHeadingMerger`)**:
   - Em PDFs, títulos longos frequentemente são quebrados em linhas consecutivas (ex.: `#### 1.0. DO OBJETO:` seguido imediatamente de `#### CONTRATAÇÃO DE EMPRESA...`).
   - Quando o texto entre dois títulos consecutivos tem $\le 5$ caracteres, eles são **fundidos em um único título lógico**.
3. **Reclassificação por Numeração Explícita (`NumberingLevelReclassifier`)**:
   - Como os conversores de PDF baseiam o nível do `#` no tamanho visual da fonte (e não na semântica), títulos como `1.0` frequentemente viravam `H4` ou `H6`.
   - O classificador analisa padrões de numeração e convenções formais (`1.0`, `1.1`, `1.1.1`, `CLÁUSULA II`, `ANEXO IV`) e reatribui o nível semântico real, marcando `hierarchy_confidence = "numbered"`.
4. **Classificador de Papéis Semânticos (`SectionRoleClassifier`)**:
   - **Camada 1 (`AliasRoleClassifier`)**: Reconhece seções explícitas via expressões regulares em português e inglês (`ABSTRACT`, `INTRODUCTION`, `METHODOLOGY`, `RESULTS`, `DISCUSSION`, `CONCLUSION`, `REFERENCES`).
   - **Camada 2 (`PositionalAbstractFallbackClassifier`)**: Caso o artigo científico não possua cabeçalho explícito para o Resumo/Abstract (o texto existe implicitamente entre os autores e a introdução), o nó precedente a `INTRODUCTION` é automaticamente delimitado e classificado como `ABSTRACT` com `role_confidence = "positional_fallback"`.

---

## 💡 O que Deu Certo nos Experimentos

- **Desacoplamento Completo**: Cada estágio pode evoluir e ser testado isoladamente. Mexer nos cleaners de cabeçalho não quebra o chunking; alterar o tamanho de chunk não afeta a árvore.
- **Detecção de Ruídos Repetitivos**: O cleaner de repetição eliminou com precisão dezenas de cabeçalhos institucionais e rodapés repetidos por página (como `Secretaria Municipal de Saúde...` repetindo 15 vezes).
- **Fusão em vez de Deleção**: Tratar títulos adjacentes sem corpo como *merge* (e não como erro) preservou integralmente o conteúdo e os metadados das seções contratuais.
- **Fallback Posicional de Custo Zero**: Conseguimos identificar com precisão o Abstract em artigos sem cabeçalho sem fazer uma única chamada a modelos de linguagem, economizando custo e reduzindo a latência para milissegundos.
- **Chunking Cirúrgico**: Seções menores que o limite de chunk permanecem 100% íntegras; seções longas são fatiadas preservando o prefixo do título da seção para enriquecer o embedding.

---

## ⚠️ O que Deu Errado e Lições Aprendidas

### 1. O Bug do `OrphanCleaner` (Deleção Indevida do Objeto)
- **O que aconteceu:** A seção essencial `#### 1.0. DO OBJETO:` simplesmente desapareceu da árvore do documento `ext_section_document_g`.
- **Causa Raiz:** O cleaner de seções órfãs possuía a heurística de descartar títulos cujo conteúdo subsequente tivesse menos de 20 caracteres. Como o subtítulo descritivo (`CONTRATAÇÃO DE EMPRESA...`) vinha na linha seguinte como outro heading `####`, a distância entre eles era de **0 caracteres**. O cleaner interpretou o título do objeto como um ruído vazio e o deletou!
- **Lição Aprendida:** Títulos colados com zero texto no meio **nunca são lixo — são quase sempre o mesmo título quebrado em duas linhas pelo conversor**. A solução foi criar um passo de fusão (`AdjacentHeadingMerger`) e executá-lo *antes* de qualquer descarte.

### 2. A Ilusão da Hierarquia por Tamanho de Fonte
- **O que aconteceu:** Editais públicos frequentemente usam a mesma fonte (mesmo tamanho e peso) para títulos de primeiro nível (`1.0`), segundo nível (`1.1`) e até para cláusulas contratuais.
- **Causa Raiz:** O `pymupdf4llm` atribui os hashes `#` estritamente pelo tamanho da fonte. Isso gerava árvores com distorções absurdas (ex.: `CLÁUSULA I` aparecendo como filha de um detalhe qualquer só porque a fonte era ligeiramente menor).
- **Lição Aprendida:** A numeração explícita (`1.0`, `CLÁUSULA II`) é a **única fonte primária da verdade**. A tipografia visual deve ser usada apenas como fallback secundário.

### 3. A Poluição por Breadcrumb no Texto dos Chunks
- **O que aconteceu:** Inicialmente, inserimos a cadeia hierárquica inteira no texto do chunk (ex.: `[TERMO DE REFERÊNCIA > 9. CONDIÇÕES > Habilitação Jurídica]`).
- **Causa Raiz:** Como a hierarquia do documento original nem sempre é perfeita, forçar um caminho longo inseria ruído e palavras irrelevantes dentro da janela de contexto do embedding vetorial.
- **Lição Aprendida:** No texto que vai para embedding, injeta-se apenas o **título imediato** `[Habilitação Jurídica]`. O caminho completo (`breadcrumb`) pertence estritamente aos **metadados** para rastreabilidade e filtros.

---

## 🚫 O que Esquecemos no Início que Quase Travou o Projeto

1. **A Ordem Estrita dos Cleaners:** Descobrimos que a ordem dos filtros altera radicalmente o resultado. Rodar remoção de órfãos antes da fusão deleta títulos válidos; rodar fusão antes da remoção de repetidos impede que títulos idênticos coincidam. A ordem precisa ser documentada e blindada por testes:
   $$\text{Markup} \longrightarrow \text{Repetidos} \longrightarrow \text{Merge Adjacente} \longrightarrow \text{Reclassificação} \longrightarrow \text{Órfãos}$$
2. **Gravação Acidental de Dados no Git:** Ao rodar os primeiros testes com PDFs reais, os arquivos gerados em `data/` quase foram versionados. Criamos e reforçamos o `.gitignore` com a regra `data/**/*` (preservando apenas os `README.md` estruturais das pastas).

---

## 📂 Estrutura de Pastas de Dados

A separação física das etapas permite inspecionar cada fase do pipeline:

- **`data/00_input_pdfs/`**: Onde você deposita seus PDFs brutos.
- **`data/01_raw_markdown/`**: Markdowns puros (`.md`) e mapas de páginas com intervalos de linhas (`_pages.json`).
- **`data/02_sections_tree/`**: Árvores hierárquicas de seções (`_sections.json`) e relatórios legíveis (`_sections.md`).
- **`data/03_chunks/`**: Chunks semânticos enriquecidos prontos para vector stores (`_chunks.json` e `_chunks.md`).

---

## 🚀 Como Executar o Projeto

### 1. Pré-requisitos
- Python `>= 3.13, < 4.0`
- [Poetry](https://python-poetry.org/)

### 2. Instalação
```bash
poetry install
```

### 3. Execução do Pipeline Completo
Para processar todos os PDFs presentes em `data/00_input_pdfs/` executando os 3 estágios de ponta a ponta:
```bash
poetry run run-pipeline
```

### 4. Execução Estágio por Estágio (Modo Experimental)

- **Estágio 1 — Extração Bruta:**
  ```bash
  poetry run extract-raw
  ```
- **Estágio 2 — Limpeza, Árvore e Classificação de Roles:**
  ```bash
  poetry run extract-sections
  ```
- **Estágio 3 — Chunking e Enriquecimento:**
  ```bash
  poetry run extract-chunks
  ```
  *(Parâmetros opcionais: `--chunk-size 1000 --chunk-overlap 150`)*

### 5. Executando a Suíte de Testes Automatizados
O projeto conta com 21 testes unitários cobrindo todos os cenários críticos e prevenindo regressões:
```bash
poetry run python -m unittest discover tests
```
