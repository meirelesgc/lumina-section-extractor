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

Para permitir a análise comparativa e a tomada de decisões, o pipeline trabalha com pastas organizadas por fases:

- **`data/00_input_pdfs/`**: Coloque aqui os arquivos PDF originais para processamento.
- **`data/01_raw_markdown/`**: Onde os resultados em Markdown cru (sem pós-tratamento) são salvos após a conversão básica.

### Executando a Etapa 1: Markdown Cru

Após adicionar os PDFs em `data/00_input_pdfs/`, execute:

```bash
poetry run extract-raw
```

*(Ou alternativamente: `poetry run python -m lumina_section_extractor.extract_raw_markdown`)*

Para personalizar as pastas de entrada e saída:
```bash
poetry run extract-raw --input-dir data/00_input_pdfs --output-dir data/01_raw_markdown
```

---

- **`data/02_extracted_titles/`**: Onde os títulos extraídos (linhas com `#`) são salvos em formato `.md` e `.json`.

### Executando a Etapa 2: Extração de Títulos (`#`)

Após gerar os markdowns crus da Etapa 1, execute:

```bash
poetry run extract-titles
```

*(Ou alternativamente: `poetry run python -m lumina_section_extractor.extract_titles`)*

Você também pode especificar um arquivo `.md` pontual:
```bash
poetry run extract-titles --file data/01_raw_markdown/meu_arquivo.md
```


