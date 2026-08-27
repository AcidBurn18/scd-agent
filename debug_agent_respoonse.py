#!/usr/bin/env python3
"""
Quick debug script to test what the SCD Generator agent is actually returning
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from session_manager import SessionManager
from agent_registry import AgentRegistry
from agent_factory import AgentFactory

def test_agent_response():
    """Test what the agent returns for a simple SCD generation request"""
    
    # Initialize with proper agents_client
    agent_factory = AgentFactory()
    session_manager = SessionManager(agent_factory.agents_client)
    agent_registry = AgentRegistry()
    
    # Get the SCD generator agent ID
    agent_info = agent_registry.get_agent("scd_generator")
    if not agent_info:
        print("ERROR: SCD Generator agent not found in registry")
        return
    
    scd_generator_agent_id = agent_info['agent_id']
    print(f"Using SCD Generator Agent ID: {scd_generator_agent_id}")
    
    # Test with a very simple message
    test_message = """
Generate a simple Security Control Documentation table for Azure Storage.

Create a markdown table with these columns:
| Control ID | Security Control for Service | Policy Name | Policy Description | Mapping to NIST CSF v1.1 control |

Include these mandatory controls first:
| ID.AM-5.1 | Tags and metadata tags must be applied using the organization's developed tagging conventions to assist in managing Azure Storage. | Tag Azure Storage as per organization's tagging standards. | Every Azure Storage must be tagged in accordance to organization's tagging standards. | ID.AM-5: Resources (e.g., hardware, devices, data, time, personnel, and software) are prioritized based on their classification, criticality, and business value |
| ID.AM-5.2 | The organization's naming conventions must be followed to keep Azure Storage easily identifiable & standardized. | Configure Azure Storage to adhere to organization's naming conventions. | Every Azure Storage which is being provisioned in a Subscription must adhere to organization's naming conventions. | ID.AM-5: Resources (e.g., hardware, devices, data, time, personnel, and software) are prioritized based on their classification, criticality, and business value |

Then add 3 more Azure Storage specific controls.
"""
    
    print("Sending test message to agent...")
    print("=" * 50)
    
    try:
        response = session_manager.send_message_and_run(
            scd_generator_agent_id, 
            "debug_session", 
            test_message
        )
        
        print("AGENT RESPONSE:")
        print("=" * 50)
        print(response)
        print("=" * 50)
        print(f"Response length: {len(response)} characters")
        
        # Check if response looks like the input message
        if "Generate a simple Security Control Documentation" in response:
            print("\n❌ PROBLEM DETECTED: Agent is echoing the input message!")
        elif "| Control ID |" in response and "| ID.AM-5.1 |" in response:
            print("\n✅ SUCCESS: Agent returned proper SCD table format")
        else:
            print("\n⚠️  UNCLEAR: Agent response doesn't match expected patterns")
            
    except Exception as e:
        print(f"ERROR: Failed to get response from agent: {e}")

if __name__ == "__main__":
    test_agent_response()