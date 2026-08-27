"""
Minimal Agent Creator - Just the essentials
"""

from agent_factory import AgentFactory
from tool_manager import ToolManager
from azure.ai.agents.models import ToolResources

def create_agents_simple():
    """Create all 3 agents with minimal setup"""
    
    print("[STARTING] Creating SCD Agents...")
    
    # Initialize
    factory = AgentFactory()
    tools = ToolManager(factory.agents_client, factory.project)
    
    # 1. SCD Generator Agent (MUST BE CREATED FIRST)
    print("[STEP 1] Creating SCD Generator Agent...")
    scd_agent_id, scd_agent_name = factory.create_scd_generator_agent()
    
    # 2. Data Collection Agent (with connection to SCD generator)
    print("[STEP 2] Creating Data Collection Agent...")
    azure_search = tools.setup_data_collection_bing_tool()
    file_search, vector_store = tools.setup_file_search_tool()
    file_search_definition = tools.get_file_search_tool_definition()
    
    # Create connected agent tool for SCD generator
    connected_agent_tool = tools.create_connected_agent_tool(scd_agent_id, scd_agent_name)
    
    data_agent_id = factory.create_data_collection_agent(
        tools=azure_search.definitions + [file_search_definition] + connected_agent_tool.definitions,
        tool_resources=ToolResources(
            file_search={"vector_store_ids": [vector_store]}
        )
    )
    
    # 3. Validation Agent
    print("[STEP 3] Creating Validation Agent...")
    nist_search = tools.setup_validation_bing_tool()
    
    validation_agent_id, _ = factory.create_validate_scd_agent(
        tools=nist_search.definitions,
        tool_resources=ToolResources()
    )
    
    print(f"""
[COMPLETED] AGENTS CREATED:
   Data Collection: {data_agent_id}
   SCD Generator:   {scd_agent_id}  
   Validation:      {validation_agent_id}
   Vector Store:    {vector_store}
   
[SUCCESS] Ready for SCD generation!
""")
    
    return {
        "data_collection_agent_id": data_agent_id,
        "scd_generator_agent_id": scd_agent_id,
        "validation_agent_id": validation_agent_id,
        "vector_store_id": vector_store
    }

if __name__ == "__main__":
    create_agents_simple()