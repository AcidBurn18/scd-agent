# Create an Agent in Azure AI Foundry Using the Python SDK

> Draft article (ready to refine for publication). All examples derived from local project code patterns; proprietary domain logic & lengthy domain-specific instructions have been abstracted into neutral examples.

――――――――――――――――――――――――――――――

## 1. Why Another “Build an Agent” Guide?

You start with a simple goal: "Answer a user question." A week later product wants source-backed answers, structured summaries, guardrails, and a pathway to add more capabilities **without rewiring everything**. The early single-file prototype is now friction. This narrative begins intentionally *non-technical*—framing the pressure that pushes a team from a lone `agent.py` script toward a composable agent stack—then gradually dives deeper until we are reasoning about vector store reuse and connected-agent tool boundaries.

Most tutorials stop at a single hello-world agent. Real systems quickly need: multiple specialized agents, reusable tool wiring, vector-backed file search, and safe lifecycle management. This guide walks you through those layers incrementally—using the Azure AI Foundry Python SDK—grounded in a modular pattern distilled from the referenced codebase (with domain specifics removed).

We’ll build a small *Agent Stack* composed of:

- **Core Retrieval Agent** (focuses on gathering domain material via web + file search)
- **Composer Agent** (turns gathered context into structured output)
- **Validator Agent** (spot-checks and applies rule-based validation)
- **Tool Layer** (Bing custom search, file search, optional connected agents)
- **Factory + ToolManager** abstractions for reproducibility

You can keep just the first agent if you’re starting simple, or extend toward multi-agent collaboration.

――――――――――――――――――――――――――――――

## 2. Prerequisites

- Python 3.10+
- Azure subscription + Azure AI Foundry Project
- Deployed model (e.g., `gpt-4o` family or similar) in the project
- Environment variables (choose either connection string style or endpoint style—this draft uses a project endpoint style variable renamed for clarity):
- `PROJECT_CONNECTION_STRING` (in original code; treat as project endpoint)
- `AZURE_OPENAI_CHAT_COMPLETION_MODEL` (model deployment name)
- Bing / search related: `DATA_COLLECTION_BING_CONNECTION_NAME`, `DATA_COLLECTION_BING_INSTANCE_NAME`, `VALIDATION_BING_CONNECTION_NAME`, `VALIDATION_BING_INSTANCE_NAME`

Minimal install (adapt to your lock file):

pip install azure-ai-projects azure-ai-agents azure-identity python-dotenv

――――――――――――――――――――――――――――――

## 3. High-Level Architecture

┌────────────────────────────────┐

│  Client / Trigger (CLI, HTTP)  │

└───────────────┬────────────────┘

│

┌───────▼────────┐

│  AgentFactory  │  (creates specialized agents)

└───────┬────────┘

│ wires

┌───────▼──────────────┐

│     ToolManager      │  (search + file index + connected agent tools)

└───────┬──────────────┘

uses         │ tool defs + resources

┌───────▼──────────────┐

│  Azure AI Agents API │

└──────────────────────┘

Key design ideas:

- **Factory** centralizes agent construction (model, instructions, tools)
- **ToolManager** encapsulates one-time creation of search/file tooling
- Agents remain slim: no embedded upload or connection logic

――――――――――――――――――――――――――――――

## 4. From Ad‑Hoc to Structured: The Factory Pattern

Your original `agent_factory.py` formalizes: load config → validate model → create agents with different instructions. We generalize those instruction blocks (removing domain-specific security/compliance text) into concise roles:

| Agent (Original)              | Neutral Renamed Purpose              | Core Idea in Article |

|-------------------------------|--------------------------------------|----------------------|

| `data_collection_agent`       | `retrieval_agent`                    | Pull targeted info   |

| `scd_generator_agent`         | `composer_agent`                     | Transform context    |

| `validate_scd_agent`          | `validator_agent`                    | Quality / rule checks|

――――――――――――――――――――――――――――――

## 5. Tool Layer Abstraction

The original `tool_manager.py` demonstrates:

1. Distinct Bing search configurations (two connection IDs) → separation of retrieval intent
2. File upload + vector store build → local knowledge augmentation
3. Ability to expose one agent as a tool to another (`ConnectedAgentTool`)

These patterns become **capability capsules**. Each tool returns *definitions* and associated *resources* (vector store IDs, etc.).

### Simplified ToolManager Pattern (Derived)

# tool_manager_slim.py (illustrative abstraction)

```python
from azure.ai.agents.models import (
    BingCustomSearchTool, FileSearchTool, FilePurpose, ToolResources, ConnectedAgentTool
)

class ToolManager:
    def __init__(self, agents_client, project, cfg):
        self.agents_client = agents_client
        self.project = project
        self.cfg = cfg
        self._bing_ids = {}
        self._vector_store_id = None

    def _resolve_connection(self, logical_name: str):
        if logical_name not in self._bing_ids:
            conn = self.project.connections.get(name=self.cfg[logical_name]['connection'])
            self._bing_ids[logical_name] = conn.id
        return self._bing_ids[logical_name]

    def make_bing_tool(self, slot: str):
        conn_id = self._resolve_connection(slot)
        inst_name = self.cfg[slot]['instance']
        return BingCustomSearchTool(connection_id=conn_id, instance_name=inst_name)

    def build_file_search(self, files):
        if self._vector_store_id:  # reuse
            return FileSearchTool(vector_store_ids=[self._vector_store_id]), self._vector_store_id
        uploaded_ids = []
        for fp in files:
            f = self.agents_client.files.upload_and_poll(file_path=fp, purpose=FilePurpose.AGENTS)
            uploaded_ids.append(f.id)
        vs = self.agents_client.vector_stores.create_and_poll(file_ids=uploaded_ids, name=f"kb_{len(uploaded_ids)}")
        self._vector_store_id = vs.id
        return FileSearchTool(vector_store_ids=[vs.id]), vs.id

    def connect_agent(self, agent_id: str, name: str, description: str):
        return ConnectedAgentTool(id=agent_id, name=name, description=description)

    def assemble(self, *tool_objs, vector_store_id=None):
        all_defs = []
        for t in tool_objs:
            all_defs += t.definitions
        resources = ToolResources(file_search={"vector_store_ids": [vector_store_id]}) if vector_store_id else None
        return all_defs, resources

```

Focus: Idempotent creation + separation of responsibilities.

### Explaining the Snippet

- *What it does:** Centralizes creation of Bing search, file search (vector store) and connected-agent tools; ensures each underlying asset (connection ID, vector store) is resolved once then reused.
- *Why structured this way:** Keeping cloud resource lookups (connections, uploads, vector store builds) out of agent construction makes agents pure descriptors (model + instructions + tools). This reduces creation latency and avoids duplicated uploads when adding more agents later.
- *Extension points:**
- Add a caching dictionary for query → search results.
- Introduce a `cleanup()` method mirroring original code to tear down vector stores in ephemeral environments.
- Inject a policy object to filter which files get indexed.
- *Failure modes to watch:**
- Missing connection name → raise early inside `_resolve_connection`.
- Upload failures for some files → continue but log; abort only if zero successes.
- Duplicate vector store build attempts → short-circuit via the `_vector_store_id` guard.

――――――――――――――――――――――――――――――

## 6. Creating the First Agent (Retrieval)

Below, a condensed version inspired by `AgentFactory`. We keep validation gentle and instructions succinct.

```python
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

class AgentFactory:
    def __init__(self):
        self.endpoint = os.getenv("PROJECT_CONNECTION_STRING")  # naming kept for parity
        self.model = os.getenv("AZURE_OPENAI_CHAT_COMPLETION_MODEL", "gpt-4o")
        if not self.endpoint:
            raise RuntimeError("PROJECT_CONNECTION_STRING missing")
        self.project = AIProjectClient(credential=DefaultAzureCredential(), endpoint=self.endpoint)
        self.agents = self.project.agents

    def create_retrieval_agent(self, tools, tool_resources):
        agent = self.agents.create_agent(
            model=self.model,
            name="retrieval_agent",
            instructions=(
                "You specialize in gathering concise, factual excerpts from approved sources. "
                "Use tools when queries require external or file-based context; otherwise answer directly."
            ),
            tools=tools,
            tool_resources=tool_resources,
            headers={"x-ms-enable-preview": "true"},
        )
        return agent.id

```

Key choices:

- **Short role message**: Domain specifics removed; emphasize tool gating
- **Feature flag header** preserved (mirrors original preview usage)

### Explaining the Snippet

- *What it does:** Wraps Azure AI Project client creation and exposes a single method to instantiate a retrieval-focused agent with an injected tool set and tool resource bindings.
- *Why structured this way:** The factory hides environment + credential pluming. By passing `tools` and `tool_resources` in, we decouple *capability assembly* (ToolManager) from *agent definition*. This isolation lets you unit test planning/instruction changes without touching file uploads or connectivity.
- *Extension points:**
- Add optional `planning_mode` flag to alter instructions for experimentation.
- Log the tool names registered for observability.
- Wrap `create_agent` in a retry decorator for transient network exceptions.
- *Common pitfalls:** Forgetting the preview header (if required for certain tool features) or mixing environment variable names for hub vs. project style endpoints.

――――――――――――――――――――――――――――――

## 7. Composing a Second Agent That Consumes the First

Pattern taken from the connected-agent tool usage: create the first agent → wrap it as a tool → feed into second agent.

```python

def create_composer_agent(factory: AgentFactory, tool_manager: ToolManager, retrieval_agent_id: str):
    connected_tool = tool_manager.connect_agent(
        agent_id=retrieval_agent_id,
        name="retrieval_agent",
        description="Use to fetch focused contextual snippets before composing an answer."
    )
    # Minimal additional tools if desired (e.g., same file search)
    file_tool, vec_id = tool_manager.build_file_search(["docs/intro.md"])  # example
    all_tools, resources = tool_manager.assemble(connected_tool, file_tool, vector_store_id=vec_id)

    composer = factory.agents.create_agent(
        model=factory.model,
        name="composer_agent",
        instructions=(
            "You transform retrieved snippets into structured, readable summaries. "
            "Call the retrieval tool first when user asks for non-trivial or source-backed content."
        ),
        tools=all_tools,
        tool_resources=resources,
        headers={"x-ms-enable-preview": "true"},
    )
    return composer.id

```

Notes:

- We intentionally keep the retrieval agent’s internal instructions hidden from the composer (enforced by tool boundary)
- Encourages an explicit call chain: user → composer → retrieval tool

### Explaining the Snippet

- *What it does:** Introduces a *consumer* agent that treats the retrieval agent itself as a callable tool while also attaching file search for supplemental grounding.
- *Why structured this way:** Instead of giving every agent broad data access, we funnel knowledge acquisition through a single retrieval specialization. This reduces duplication and creates a natural choke point for governance (rate limiting, audit, caching).
- *Extension points:**
- Add a lightweight planner step that decides whether to invoke the connected retrieval tool based on question complexity.
- Provide multiple retrieval variants (e.g., `retrieval_lite` vs `retrieval_deep`) and have the composer choose dynamically.
- Capture provenance by appending which tools were invoked to the final response metadata.
- *Edge cases:** Composer may attempt retrieval for trivial queries—mitigate with a heuristic: if user prompt < N chars and no interrogatives, answer directly.

――――――――――――――――――――――――――――――

## 8. Adding a Lightweight Validator Agent

The original code had a very detailed, rule-heavy validator. We generalize to a *pattern*:

```python

def create_validator_agent(factory: AgentFactory):
    validator = factory.agents.create_agent(
        model=factory.model,
        name="validator_agent",
        instructions=(
            "You review drafted outputs for formatting, over-claims, and missing source mentions. "
            "Return a JSON object: {status: 'pass'|'revise', issues: [...], suggestions: [...]}"
        ),
        headers={"x-ms-enable-preview": "true"},
    )
    return validator.id

```

return validator.id

Guidance: keep validator outputs structured so upstream automation can branch (accept vs. refine loop).

### Explaining the Snippet

- *What it does:** Creates a minimal validator agent whose sole purpose is to return a structured JSON assessment object about a draft response.
- *Why structured this way:** Separating validation from composition simplifies each prompt, improves traceability (separate run IDs), and allows iterative chains (composer → validator → optional re-compose) without ballooning a single agent’s instruction set.
- *Extension points:**
- Provide severity levels (`minor`, `critical`) for issues to drive automated acceptance thresholds.
- Add a tool (e.g., regex policy checker or external classification API) inside the validator for deeper semantic checks.
- Serialize cumulative validation history per thread for analytics.
- *Failure considerations:** If validator returns malformed JSON, have caller wrap invocation and fall back to a safe "revise" path.

――――――――――――――――――――――――――――――

## 9. Wiring It All Together (Bootstrap Flow)

```python
from dotenv import load_dotenv
import os

load_dotenv()

factory = AgentFactory()
# Configure tool manager with a simple dict rather than many env lookups for clarity
config = {
  "retrieval_search": {"connection": os.getenv("DATA_COLLECTION_BING_CONNECTION_NAME"), "instance": os.getenv("DATA_COLLECTION_BING_INSTANCE_NAME")},
  "validation_search": {"connection": os.getenv("VALIDATION_BING_CONNECTION_NAME"), "instance": os.getenv("VALIDATION_BING_INSTANCE_NAME")},
}

tool_manager = ToolManager(factory.agents, factory.project, cfg=config)

# 1. Build base tools for retrieval agent
bing_tool = tool_manager.make_bing_tool("retrieval_search")
file_tool, vec_id = tool_manager.build_file_search(["knowledge/base.md"])  # example path
retrieval_tools, retrieval_resources = tool_manager.assemble(bing_tool, file_tool, vector_store_id=vec_id)
retrieval_id = factory.create_retrieval_agent(retrieval_tools, retrieval_resources)

# 2. Composer (consumes retrieval agent as tool)
composer_id = create_composer_agent(factory, tool_manager, retrieval_id)

# 3. Validator (stand-alone)
validator_id = create_validator_agent(factory)

print("Agents ready:", retrieval_id, composer_id, validator_id)

```

Resilience enhancements you can add:

- Wrap each creation in retry (transient network errors)
- Cache vector store ID for reuse across runs
- Parameterize roles via config file for faster iteration

### Explaining the Snippet

- *What it does:** Shows a linear bootstrap: configure tools → create retrieval agent → wrap it into composer → create validator. Outputs agent IDs for subsequent thread operations.
- *Why structured this way:** The ordering enforces dependency flow (composer needs retrieval ID). Grouping environment extraction up-front gives a single failure point rather than scattering `os.getenv` calls.
- *Extension points:**
- Convert to a declarative YAML describing agents & tools; generate this bootstrap automatically.
- Insert diagnostics (time each step) for cold-start tuning.
- Persist the mapping (logical_name → agent_id) to a small JSON registry so later processes (batch jobs, evaluation harness) can attach without recreating agents.
- *Potential refinements:** Use a simple inversion-of-control container to resolve `ToolManager` and allow mocking in tests.

――――――――――――――――――――――――――――――

## 10. Running Threads & Interactions (Conceptual)

While not shown in the extracted code sample here, typical lifecycle:

1. Create a **thread** (conversation container)
2. Post a **message** from user
3. **Run** an agent against the thread
4. Poll / stream the result
5. Optionally pass result to next agent (e.g., composer → validator)

Pseudo-flow:

thread = factory.agents.create_thread()

factory.agents.create_message(thread.id, role="user", content="Summarize the latest patterns for X")

run = factory.agents.create_run(thread.id, agent_id=composer_id)

# poll until status == 'completed'

result_messages = factory.agents.list_messages(thread.id)

Keep intermediate artifacts lean; purge threads no longer needed.

### Explaining the Snippet

- *What it does:** Illustrates the lifecycle primitives: thread (conversation scope), message append, run creation, result retrieval.
- *Why structured this way:** Threads decouple conversational state from agent identities so multiple agents can act sequentially over the same context. Polling pattern ensures you can implement timeouts and progressive UI updates.
- *Extension points:**
- Replace polling with streaming if SDK support is available for progressive token display.
- Implement a mediator that decides which agent to run next based on last message metadata.
- Attach a small transcript summarizer after every N messages to keep context within token limits.
- *Caution:** Avoid unbounded thread growth—summarize or snapshot older turns.

――――――――――――――――――――――――――――――

## 11. Instruction Crafting Tips (Abstracted from Original Detailed Blocks)

| Goal | Strategy | Keep It Short |

|------|----------|---------------|

| Tool gating | “Use tools only when info isn’t already in prior context.” | Avoid huge enumerations |

| Role clarity | One verb phrase (“gather domain facts”, “compose structured summary”) | 1–2 sentences |

| Guardrails | Emphasize source-backed, no speculation | Declarative tone |

| Multi-agent handoff | Mention explicit dependency (“call retrieval tool first”) | Deterministic sequence |

Avoid giant prompt monoliths; iterative refinement beats prompt bloat.

――――――――――――――――――――――――――――――

## 12. Managing Vector Content

Original pattern: upload allowed files → create vector store → attach via `FileSearchTool`. Good practices:

- Maintain an *allowlist* directory (`files/`)
- Pre-clean documents (strip boilerplate, unify encoding)
- Log file → vector store ID mapping
- Reuse the vector store between agent creations when content unchanged

Cleanup routine (inspired by original `cleanup_vector_store`):

def teardown(tool_manager: ToolManager):

if tool_manager.vector_store_id:

tool_manager.agents_client.vector_stores.delete(tool_manager.vector_store_id)

――――――――――――――――――――――――――――――

## 13. Evolving Beyond Three Agents

- **Planner Agent**: decides which specialized agent to invoke (retrieval vs. composer) based on query type
- **Evaluator Loop**: re-run composer if validator flags ‘revise’
- **Cost Tracking Decorators**: wrap each run with token accounting
- **Caching Layer**: hash user question → retrieval results to skip duplicate external calls

――――――――――――――――――――――――――――――

## 14. Common Failure Points & Mitigations

| Issue | Cause | Mitigation |

|-------|-------|------------|

| Model deployment not found | Wrong env var | Echo model name during startup & assert via deployments list |

| Empty vector store | No matching files | Pre-flight file glob + explicit error message |

| Tool call latency | External search API | Add simple in-memory cache keyed by query+topK |

| Prompt drift | Overly long instructions | Periodic pruning + version control prompts |

| Chained agent recursion | Composer re-calls retrieval unnecessarily | Add plan step or call budget counter |

――――――――――――――――――――――――――――――

## 15. Security & Hygiene (Neutralized Abstract)

- Do not hardcode secrets; rely on environment variables or managed identities
- Sanitize any external text before echoing to clients (length, unexpected HTML)
- Restrict file ingestion to curated directory (avoid arbitrary path traversal)
- Log agent IDs and run IDs, not raw prompt tokens

――――――――――――――――――――――――――――――

## 16. Minimal Checklist Before Publishing (Your Blog)

- Replace placeholder file names with ones you’re comfortable making public
- Re-run a clean bootstrap from empty vector store to confirm reproducibility
- Strip any leftover internal/domain phrasing
- Optionally add a Mermaid diagram for the multi-agent flow

――――――――――――――――――――――――――――――

## 17. Summary

You now have a layered approach:

1. **Factory** creates consistent agents
2. **ToolManager** encapsulates search + file augmentation + cross-agent linking
3. **Specialized Agents** (retrieval → composer → validator) enable clearer reasoning boundaries
4. **Extensible Patterns** for adding planning, evaluation, caching, and governance

Start with one agent + one tool. Add only when a new capability is truly needed. That restraint keeps maintenance low and clarity high.

――――――――――――――――――――――――――――――

- End of draft.*

agent_factory.py

agent_registry.py

create_Agent_simple.py

debug_agent_response.py

dual_bing_search_config.py

azure_function.py

github_integration.py

nist_csf_validator.py

requirements.txt

rigourous_output_validator.py

sanitizer.py

scd_generator.py

scd_storage_manager.py

session_manager.py

trst_dual_bing_Search.py

tool_manager.py

request_schema.json

agw.md

aks.md

azure_cache_redis.md

azure_database.md

databricks.md

sqlmi.md

storage.md

vm.md

subscription.md

vnet&subnet.md

pep.md

gen_load_balancer.md

gen_linux_function_app.md