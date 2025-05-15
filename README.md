# Obsidian Suite

A collection of Python tools designed to enhance the Obsidian note-taking experience by leveraging Large Language Models (LLMs) like OpenAI and Perplexity.

## Features

*   **Template Manager:** ([src/tools/template_manager/](src/tools/template_manager/)) Automatically applies structured templates (frontmatter, sections) to markdown notes using an LLM based on a defined schema.
*   **Tag Manager:** ([src/tools/tag_manager/](src/tools/tag_manager/)) Scans the vault, identifies inconsistent tags (ignoring exempt ones), suggests standardized versions using an LLM, and updates notes accordingly.
*   **Researcher:** ([src/tools/researcher/](src/tools/researcher/)) Uses a powerful two-stage approach for comprehensive research:
    * **Stage 1 (OpenAI):** Generates a hierarchical plan with detailed instructions for each note
    * **Stage 2 (Perplexity AI):** Executes these instructions to generate in-depth content with sources
    * Creates a structured set of interconnected Obsidian notes organized hierarchically with proper linking
*   **Enricher:** ([src/tools/enricher/](src/tools/enricher/)) Analyzes existing notes and appends or updates an AI-generated section containing key concepts, related topics, and thought-provoking questions.
*   **Core Obsidian Utilities:** ([src/core/obsidian/](src/core/obsidian/)) Includes functions for parsing frontmatter ([`parse_frontmatter`](src/core/obsidian/parser.py)), extracting tags ([`extract_tags`](src/core/obsidian/parser.py)), and formatting Obsidian links/tags ([`format_obsidian_link`](src/core/obsidian/formatter.py), [`format_obsidian_tag`](src/core/obsidian/formatter.py)).
*   **LLM Integration:** ([src/core/llm/](src/core/llm/)) Provides clients for interacting with OpenAI ([`OpenAIClient`](src/core/llm/openai_client.py)) and Perplexity ([`PerplexityClient`](src/core/llm/perplexity_client.py)) APIs.
*   **Configuration:** ([src/core/config/loader.py](src/core/config/loader.py)) Centralized configuration via [`config/settings.yaml`](config/settings.yaml) and [`config/.env`](config/.env.example).
*   **Logging:** ([src/core/logging/setup.py](src/core/logging/setup.py)) Configurable logging setup.
*   **File Utilities:** ([src/core/file_io/utils.py](src/core/file_io/utils.py)) Helpers for scanning directories and reading/writing files.

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yavuztopsever/obsidian_llm_suite.git
    cd obsidian_llm_suite
    ```
2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    # venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **API Keys:**
    *   Copy the example environment file: `cp config/.env.example config/.env`
    *   Edit `config/.env` and add your actual `OPENAI_API_KEY` and `PERPLEXITY_API_KEY`.
    *   Ensure `.env` is listed in your [.gitignore](.gitignore) file to avoid committing secrets.
2.  **Settings:**
    *   Open [`config/settings.yaml`](config/settings.yaml).
    *   **Crucially, update `obsidian_vault_path`** to the absolute path of your Obsidian vault.
    *   Review and adjust other settings like default LLM models, tool-specific configurations (e.g., `exempt_tags`, `output_directory`), and logging preferences as needed.

## Usage

Run the tools from the root directory of the project (`obsidian_suite/`).

*   **Template Manager:**
    *   Process all notes in the vault:
        ```bash
        python -m obsidian_suite.src.tools.template_manager.main
        ```
    *   Process a single file:
        ```bash
        # Replace with the actual path to your note
        python -m obsidian_suite.src.tools.template_manager.main --file "/path/to/your/note.md"
        ```
*   **Tag Manager:**
    *   Perform a dry run (scan and show proposed changes without modifying files):
        ```bash
        python -m obsidian_suite.src.tools.tag_manager.main --dry-run
        ```
    *   Apply the standardization changes (creates `.bak` backups):
        ```bash
        python -m obsidian_suite.src.tools.tag_manager.main
        ```
*   **Researcher:**
    *   Conduct research using the two-stage process:
        ```bash
        # Replace with your research query
        python -m obsidian_suite.src.tools.researcher.main "What are the latest advancements in AI-assisted note-taking?"
        ```
    *   Customize the models in [`config/settings.yaml`](config/settings.yaml):
        * `researcher.openai_model`: Model for Stage 1 planning (default: "gpt-4o-mini")
        * `researcher.perplexity_model`: Model for Stage 2 content generation (default: "sonar-deep-research")
    *   Customize the prompts by setting file paths:
        * `researcher.planning_system_prompt_path`: Custom prompt for Stage 1
        * `researcher.system_prompt_path`: Custom prompt for Stage 2
    *   Notes are saved to the directory specified by `researcher.output_directory` (defaults to `research_output/`).
*   **Enricher:**
    *   The [`EnricherProcessor`](src/tools/enricher/processor.py) class provides the logic for enriching notes.
    *   Currently, there is no dedicated command-line script (`main.py`) for the enricher. It needs to be integrated into another workflow or run programmatically.

## Dependencies

All required Python packages are listed in [`requirements.txt`](requirements.txt). Key dependencies include:

*   `openai`
*   `requests`
*   `python-dotenv`
*   `PyYAML`
*   `python-frontmatter`
*   `jsonschema`

## Tests

The project includes a `tests/` directory ([tests/](tests/)) for unit and integration tests. Implementations are pending.