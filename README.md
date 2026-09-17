# Lumina - Section Extractor

Este repositório é um **laboratório experimental** para o ecossistema do projeto Lumina.

## 🎯 Objetivo

O foco deste projeto é realizar a leitura de arquivos PDF e extrair suas seções de forma estruturada e inteligente, combinando:
- **Modelos de Linguagem (LLMs)** para interpretação e estruturação semântica.
- **Representações em Markdown** (preservando cabeçalhos, tabelas, hierarquia e formatação).
- **Abordagens híbridas** combinando ferramentas de parsing rápido de PDFs e orquestração de LLMs.

---

## 🛠️ Tecnologias e Ferramentas

- **Linguagem**: Python 3.13+
- **Gerenciador de Dependências**: [Poetry](https://python-poetry.org/)
- **Orquestração de IA / LLMs**:
  - `langchain`: Framework principal para orquestração de prompts e fluxos RAG/extração.
  - `langchain-openai`: Integração com modelos da OpenAI.
  - `langchain-pymupdf4llm` / `pymupdf4llm`: Extração otimizada de PDFs convertendo conteúdo diretamente para Markdown estruturado para consumo por LLMs.

---

## 🚀 Primeiros Passos

### 1. Pré-requisitos
- Python `>= 3.13, < 4.0`
- Poetry instalado

### 2. Instalação das Dependências

Instale as dependências do projeto através do Poetry:

```bash
poetry install
```

### 3. Ambiente Virtual

Para ativar o ambiente virtual:

```bash
poetry shell
```

Ou execute comandos diretamente via `poetry run`:

```bash
poetry run python -c "import pymupdf4llm; print('Ambiente pronto!')"
```

---

## 📂 Fluxo de Extração por Etapas

O pipeline é estruturado em **três estágios desacoplados**, utilizando uma **abordagem puramente funcional** com cleaners plugáveis e dataclasses apenas para modelagem de dados:

```
PDF → [Estágio 1: Extração Bruta] → Markdown + Páginas
    → [Estágio 2: Limpeza Funcional + Árvore de Headings] → Árvore de Seções (Breadcrumbs)
    → [Estágio 3: Chunking Intra-seção + Limpeza de Documentos] → Chunks Enriquecidos
```

### 📁 Estrutura de Diretórios

- **`data/00_input_pdfs/`**: PDFs originais adicionados manualmente.
- **`data/01_raw_markdown/`**: Markdowns crus (`.md`) e mapas de páginas (`_pages.json`).
- **`data/02_sections_tree/`**: Árvores hierárquicas de seções (`_sections.json` e `_sections.md`).
- **`data/03_chunks/`**: Chunks semânticos enriquecidos (`_chunks.json` e `_chunks.md`).
- *(Opcional: `data/02_extracted_titles/`: Títulos brutos extraídos via `extract-titles`)*

---

### 🚀 Comandos do Pipeline

#### 1. Executar o Pipeline Completo (Recomendado)
Executa os três estágios em sequência de ponta a ponta:

```bash
poetry run run-pipeline
```

#### 2. Executar Estágio por Estágio

- **Estágio 1 — Extração Bruta:**
  ```bash
  poetry run extract-raw
  ```
  *(Extrai o Markdown completo e gera o mapa de páginas com `pymupdf4llm`)*

- **Estágio 2 — Limpeza de Cabeçalhos e Árvore de Seções:**
  ```bash
  poetry run extract-sections
  ```
  *(Aplica cleaners funcionais: remoção de markup, cabeçalhos/rodapés repetidos e títulos órfãos; constrói relações parent/children e breadcrumbs)*

- **Estágio 3 — Chunking Intra-seção e Enriquecimento:**
  ```bash
  poetry run extract-chunks
  ```
  *(Fatia seções longas com `RecursiveCharacterTextSplitter`, injeta prefixo semântico `[Título]`, anexa metadados completos e executa cleaners de whitespace)*

---

### 🧪 Executando os Testes

```bash
poetry run python -m unittest discover tests
```



