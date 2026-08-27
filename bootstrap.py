#!/usr/bin/env python3
"""Bootstrap script to create agents and tools from this repo.

Supports a safe `--dry-run` mode that lists actions without calling Azure.

Usage:
  python3 bootstrap.py --dry-run
  python3 bootstrap.py        # runs real creation (requires env vars & credentials)
  python3 bootstrap.py --cleanup
"""
import argparse
import os
import sys
from pathlib import Path

DEFAULT_FILES_DIR = Path(__file__).parent / "files"


def list_files():
    patterns = ("*.pdf", "*.docx", "*.txt", "*.md")
    files = []
    for p in patterns:
        files.extend(sorted(DEFAULT_FILES_DIR.glob(p)))
    return files


def dry_run():
    print("DRY RUN: Will not call Azure. Showing planned actions:\n")
    print("1) Inspect environment variables:")
    for k in ("PROJECT_CONNECTION_STRING", "AZURE_OPENAI_CHAT_COMPLETION_MODEL", "DATA_COLLECTION_BING_CONNECTION_NAME", "DATA_COLLECTION_BING_INSTANCE_NAME", "VALIDATION_BING_CONNECTION_NAME", "VALIDATION_BING_INSTANCE_NAME"):
        print(f" - {k}: {os.getenv(k) or '<NOT SET>'}")

    print("\n2) Files to upload into vector store (from 'files/' folder):")
    if not DEFAULT_FILES_DIR.exists():
        print(f" - {DEFAULT_FILES_DIR} does not exist. Create and add documents to proceed.")
    else:
        f = list_files()
        if not f:
            print(f" - No supported files found in {DEFAULT_FILES_DIR}. Add PDFs, DOCX, TXT or MD files.")
        else:
            for fp in f:
                print(f" - {fp.name}")

    print("\n3) Planned resources to create:")
    print(" - Bing custom search tool for data collection (if connection configured)")
    print(" - File vector store built from files/* (if files present)")
    print(" - Data collection agent using model deployment from AZURE_OPENAI_CHAT_COMPLETION_MODEL")
    print(" - SCD generator agent (scd_generator_agent)")
    print(" - Validation agent (validate_scd_agent) wired to NIST/validation Bing + file search")


def real_run(cleanup=False):
    # Import lazily to avoid failing dry-run when Azure libs or env are missing
    try:
        from agent_factory import AgentFactory
        from tool_manager import ToolManager
        from azure.ai.agents.models import ToolResources
    except Exception as e:
        print("Failed to import project modules or Azure SDK.\nMake sure you ran 'pip install -r requirements.txt' and that the repo is in PYTHONPATH.")
        print(str(e))
        sys.exit(1)

    # Initialize factory and tool manager
    try:
        factory = AgentFactory()
    except Exception as e:
        print(f"Could not initialize AgentFactory: {e}")
        print("If you intended a dry-run, re-run with --dry-run. Ensure Azure credentials and PROJECT_CONNECTION_STRING are set for real runs.")
        sys.exit(1)

    tm = ToolManager(factory.agents_client, factory.project)

    # 1) Setup data collection Bing tool
    try:
        print("Setting up data collection Bing tool...")
        bing_tool = tm.setup_data_collection_bing_tool()
    except Exception as e:
        print(f"Warning: failed to setup data collection Bing tool: {e}")
        print("Proceeding without Bing tool (you can add it later).")
        bing_tool = None

    # 2) Setup file search tool (uploads files and builds vector store)
    try:
        print("Setting up file search tool (uploads + vector store)...")
        file_tool, vec_id = tm.setup_file_search_tool()
    except Exception as e:
        print(f"Error: failed to setup file search tool: {e}")
        print("Ensure you have a 'files/' directory with supported documents or handle uploads manually.")
        sys.exit(1)

    # 3) Create data collection agent (uses Bing + file search)
    try:
        tools_defs = []
        if bing_tool:
            tools_defs += bing_tool.definitions
        tools_defs += file_tool.definitions

        tool_resources = ToolResources(file_search={"vector_store_ids": [vec_id]})

        print("Creating data collection agent...")
        data_agent_id = factory.create_data_collection_agent(tools=tools_defs, tool_resources=tool_resources)
    except Exception as e:
        print(f"Failed to create data collection agent: {e}")
        sys.exit(1)

    # 4) Create SCD generator agent (no external tools expected by this factory method)
    try:
        print("Creating SCD generator agent...")
        scd_agent_id, scd_agent_name = factory.create_scd_generator_agent()
    except Exception as e:
        print(f"Failed to create SCD generator agent: {e}")
        sys.exit(1)

    # 5) Setup validation Bing tool and create validation agent wired to SCD generator + file search
    try:
        print("Setting up validation Bing tool...")
        validation_bing = tm.setup_validation_bing_tool()
    except Exception as e:
        print(f"Warning: failed to setup validation Bing tool: {e}")
        validation_bing = None

    try:
        connected_tool = tm.create_connected_agent_tool(agent_id=scd_agent_id, agent_name=scd_agent_name)
        validation_tools = []
        if validation_bing:
            validation_tools += validation_bing.definitions
        validation_tools += file_tool.definitions
        validation_tools += connected_tool.definitions

        validation_resources = ToolResources(file_search={"vector_store_ids": [vec_id]})

        print("Creating validation agent...")
        validation_agent_id, validation_agent_name = factory.create_validate_scd_agent(tools=validation_tools, tool_resources=validation_resources)
    except Exception as e:
        print(f"Failed to create validation agent: {e}")
        sys.exit(1)

    print("\nBootstrap complete. Created agents:")
    print(f" - Data collection agent: {data_agent_id}")
    print(f" - SCD generator agent: {scd_agent_id} ({scd_agent_name})")
    print(f" - Validation agent: {validation_agent_id} ({validation_agent_name})")

    if cleanup:
        print("\nCleanup requested: deleting vector store...")
        tm.cleanup_vector_store()


def main():
    parser = argparse.ArgumentParser(description="Bootstrap agents and tools from this repo")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without calling Azure")
    parser.add_argument("--cleanup", action="store_true", help="If set, cleanup vector store after successful run")
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
        return

    real_run(cleanup=args.cleanup)


if __name__ == "__main__":
    main()
