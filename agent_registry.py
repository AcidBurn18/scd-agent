"""
Agent Registry - Handles persistent storage of agent IDs         self.registry = {}
        self._save_registry()
        print("[REGISTRY] Cleared agent registry")prevent recreation
"""
import json
import os
from typing import Optional

class AgentRegistry:
    def __init__(self, registry_file: str = "agent_registry.json"):
        self.registry_file = registry_file
        self.registry = self._load_registry()
    
    def _load_registry(self) -> dict:
        """Load agent registry from file"""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load agent registry: {e}")
                return {}
        return {}
    
    def _save_registry(self):
        """Save agent registry to file"""
        try:
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save agent registry: {e}")
    
    def get_agent_id(self, agent_type: str) -> Optional[str]:
        """Get stored agent ID for a given type"""
        return self.registry.get(agent_type)
    
    def store_agent_id(self, agent_type: str, agent_id: str, agent_name: str = None):
        """Store agent ID for a given type"""
        self.registry[agent_type] = {
            "id": agent_id,
            "name": agent_name,
            "created_at": str(json.JSONEncoder().encode({"timestamp": "now"}))
        }
        self._save_registry()
        print(f"[REGISTRY] Stored {agent_type} agent ID: {agent_id}")
    
    def get_agent_info(self, agent_type: str) -> Optional[dict]:
        """Get full agent info for a given type"""
        return self.registry.get(agent_type)
    
    def remove_agent(self, agent_type: str):
        """Remove agent from registry"""
        if agent_type in self.registry:
            del self.registry[agent_type]
            self._save_registry()
            print(f"[REGISTRY] Removed {agent_type} from registry")
    
    def list_agents(self) -> dict:
        """List all registered agents"""
        return self.registry
    
    def clear_registry(self):
        """Clear all agents from registry"""
        self.registry = {}
        self._save_registry()
        print("[CLEANUP] Cleared agent registry")
    
    def get_vector_store_id(self) -> Optional[str]:
        """Get stored vector store ID"""
        return self.registry.get("vector_store", {}).get("id")
    
    def store_vector_store_id(self, vector_store_id: str):
        """Store vector store ID"""
        self.registry["vector_store"] = {
            "id": vector_store_id,
            "created_at": str(json.JSONEncoder().encode({"timestamp": "now"}))
        }
        self._save_registry()
        print(f"[REGISTRY] Stored vector store ID: {vector_store_id}")
