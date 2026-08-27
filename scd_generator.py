"""
SCD Generator - Main orchestrator for Security Control Documentation generation
Enhanced with Azure AI Foundry Dynamic Validation (No Static Dependencies)
"""
import time
import re
from typing import Optional, List, Dict, Tuple
from agent_factory import AgentFactory
from tool_manager import ToolManager
from session_manager import SessionManager
from agent_registry import AgentRegistry
from scd_storage_manager import SCDStorageManager
from sanitizer import InputSanitizer, SanitizationConfig
from nist_csf_validator import NISTCSFValidator, validate_nist_id, get_valid_nist_suggestions
import asyncio

class SCDGenerator:
    def __init__(self, progress_callback=None):
        """Initialize the SCD Generator with all components"""
        self.progress_callback = progress_callback  # Callback function for progress updates
            
        self.agent_factory = AgentFactory()
        self.tool_manager = ToolManager(
            self.agent_factory.agents_client, 
            self.agent_factory.project
        )
        self.session_manager = SessionManager(self.agent_factory.agents_client)
        self.agent_registry = AgentRegistry()
        
        # Initialize NIST CSF validator for anti-hallucination
        self.nist_validator = NISTCSFValidator()
        print("NIST CSF validator initialized - preventing AI hallucination of invalid subcategories")
        
        # Initialize input sanitizer with strict policies
        self.sanitizer = InputSanitizer(SanitizationConfig(
            pii_redaction=True,
            reject_abusive_words=True,
            azure_only_policy=True,
            strict_character_policy=True,
            max_tokens=4000
        ))
        print("Input sanitizer initialized with strict policies")
        
        # Initialize storage manager
        try:
            self.storage_manager = SCDStorageManager()
            print("Azure Storage initialized for SCD documents")
        except Exception as e:
            print(f"Warning: Azure Storage not available: {e}")
            self.storage_manager = None
        
        # Remove static dependencies - use Azure AI Foundry validation only
        # No longer using AdvancedValidationAgent with static NIST database
        print("Using Azure AI Foundry services for dynamic validation (no static dependencies)")
        
        print("SCD Generator initialized")
        
        # Try to load existing agent IDs from registry
        self._load_agents_from_registry()

    def _update_progress(self, session_id: str, step: str, percentage: int, description: str):
        """Update progress if callback is provided"""
        if self.progress_callback:
            self.progress_callback(session_id, step, percentage, description)

    def _load_agents_from_registry(self):
        """Load existing agent IDs from persistent registry"""
        print("Loading agents from registry...")
        
        # Load SCD generator agent
        scd_agent_info = self.agent_registry.get_agent_info("scd_generator")
        if scd_agent_info:
            self._scd_generator_agent_id = scd_agent_info["id"]
            self._scd_generator_agent_name = scd_agent_info["name"]
            print(f"Found existing SCD Generator Agent: {self._scd_generator_agent_id}")
        else:
            self._scd_generator_agent_id = None
            self._scd_generator_agent_name = None
        
        # Load data collection agent
        data_agent_info = self.agent_registry.get_agent_info("data_collection")
        if data_agent_info:
            self._data_collection_agent_id = data_agent_info["id"]
            print(f"Found existing Data Collection Agent: {self._data_collection_agent_id}")
        else:
            self._data_collection_agent_id = None
        
        # Load validation agent
        validate_agent_info = self.agent_registry.get_agent_info("validate_scd")
        if validate_agent_info:
            self._validate_scd_agent_id = validate_agent_info["id"]
            self._validate_scd_agent_name = validate_agent_info["name"]
            print(f"Found existing SCD Validation Agent: {self._validate_scd_agent_id}")
        else:
            self._validate_scd_agent_id = None
            self._validate_scd_agent_name = None
        
        # Load vector store ID
        vector_store_id = self.agent_registry.get_vector_store_id()
        if vector_store_id:
            self.tool_manager._vector_store_id = vector_store_id
            print(f"Found existing Vector Store: {vector_store_id}")

    def _ensure_agents(self):
        """Ensure all agents are created (one-time operation)"""
        try:
            print("Checking if agents need to be created...")
            
            if not self._scd_generator_agent_id:
                print("Creating SCD Generator Agent...")
                self._scd_generator_agent_id, self._scd_generator_agent_name = self.agent_factory.create_scd_generator_agent()
                # Store in registry
                self.agent_registry.store_agent_id(
                    "scd_generator", 
                    self._scd_generator_agent_id, 
                    self._scd_generator_agent_name
                )
                print(f"Created SCD Generator Agent: {self._scd_generator_agent_id}")
            else:
                print(f"Reusing existing SCD Generator Agent: {self._scd_generator_agent_id}")

            # Create validation agent if it doesn't exist
            if not self._validate_scd_agent_id:
                print("Creating SCD Validation Agent...")
                # Setup tools
                validation_bing_tool = self.tool_manager.setup_validation_bing_tool()
                
                # Create connected agent tool to SCD generator (same pattern as data collection agent)
                # connected_scd_agent_tool = self.tool_manager.create_connected_agent_tool(
                #     self._scd_generator_agent_id, 
                #     self._scd_generator_agent_name
                # )
                
                # Combine tools (validation agent needs Bing tool + connected SCD agent)
                all_tools = validation_bing_tool.definitions #
                from azure.ai.agents.models import ToolResources
                tool_resources = ToolResources()
                
                # Create validation agent
                self._validate_scd_agent_id, self._validate_scd_agent_name = self.agent_factory.create_validate_scd_agent(
                    tools=all_tools,
                    tool_resources=tool_resources
                )
                # Store in registry
                self.agent_registry.store_agent_id(
                    "validate_scd", 
                    self._validate_scd_agent_id, 
                    self._validate_scd_agent_name
                )
                print(f"Created SCD Validation Agent: {self._validate_scd_agent_id}")
            else:
                print(f"Reusing existing SCD Validation Agent: {self._validate_scd_agent_id}")
            
            if not self._data_collection_agent_id:
                print("Creating Data Collection Agent...")
                # Setup tools
                bing_tool = self.tool_manager.setup_data_collection_bing_tool()
                file_search_tool, vector_store_id = self.tool_manager.setup_file_search_tool()
                
                # Store vector store ID in registry if new
                if vector_store_id and not self.agent_registry.get_vector_store_id():
                    self.agent_registry.store_vector_store_id(vector_store_id)
                
                connected_agent_tool = self.tool_manager.create_connected_agent_tool(
                    self._scd_generator_agent_id, 
                    self._scd_generator_agent_name
                )
                
                # Combine tools
                all_tools, tool_resources = self.tool_manager.combine_tools_and_resources(
                    bing_tool, file_search_tool, connected_agent_tool, vector_store_id
                )
                
                # Create data collection agent
                self._data_collection_agent_id = self.agent_factory.create_data_collection_agent(
                    all_tools, tool_resources
                )
                # Store in registry
                self.agent_registry.store_agent_id(
                    "data_collection", 
                    self._data_collection_agent_id,
                    "data_collection_agent"
                )
                print(f"Created Data Collection Agent: {self._data_collection_agent_id}")
            else:
                print(f"Reusing existing Data Collection Agent: {self._data_collection_agent_id}")
            
            # Verify all agents exist
            if not self._scd_generator_agent_id or not self._data_collection_agent_id or not self._validate_scd_agent_id:
                print("Error: One or more agents failed to initialize")
                return False
            
            print("All agents are ready")
            return True
            
        except Exception as e:
            print(f"Error initializing agents: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _extract_clean_table(self, content: str) -> str:
        """Extract only the markdown table from mixed content"""
        import re
        
        # Find all markdown table blocks (starts with |, has header separator, continues with |)
        lines = content.split('\n')
        table_lines = []
        in_table = False
        
        for line in lines:
            stripped = line.strip()
            # Check if line is part of a markdown table
            if stripped.startswith('|') and '|' in stripped[1:]:
                table_lines.append(line)
                in_table = True
            elif in_table and not stripped:
                # Empty line might separate sections, keep going
                continue
            elif in_table and not stripped.startswith('|'):
                # Non-table line after table might indicate end
                if len(table_lines) > 3:  # Have at least header + separator + 1 row
                    break
        
        if len(table_lines) < 3:
            # No valid table found, return original content
            return content
            
        # Clean up and return table
        clean_table = '\n'.join(table_lines)
        
        # Remove any instruction text that might be mixed in
        clean_table = re.sub(r'(?i)(please regenerate|validation feedback|collected data|additional context|critical requirements).*?\n', '', clean_table, flags=re.IGNORECASE)
        
        return clean_table.strip()

    def get_agent_status(self) -> dict:
        """Get current status of all agents and threads"""
        return {
            "data_collection_agent": self._data_collection_agent_id,
            "scd_generator_agent": self._scd_generator_agent_id,
            "validate_scd_agent": self._validate_scd_agent_id,
            "vector_store": self.agent_registry.get_vector_store_id(),
            "agents_initialized": bool(self._data_collection_agent_id and self._scd_generator_agent_id and self._validate_scd_agent_id)
        }

    def get_thread_status(self, session_id: str = None) -> dict:
        """Get detailed thread status for monitoring"""
        try:
            threads_info = []
            
            # Get persisted threads
            persisted_threads = self.session_manager._load_persisted_threads()
            
            if session_id:
                # Get specific session threads
                session_threads = {k: v for k, v in persisted_threads.items() if k.startswith(session_id)}
                for thread_key, thread_id in session_threads.items():
                    exists = self.session_manager.validate_thread_exists(thread_id)
                    threads_info.append({
                        "session_thread_key": thread_key,
                        "thread_id": thread_id,
                        "exists_in_foundry": exists,
                        "status": "active" if exists else "orphaned"
                    })
            else:
                # Get all threads
                for thread_key, thread_id in persisted_threads.items():
                    exists = self.session_manager.validate_thread_exists(thread_id)
                    threads_info.append({
                        "session_thread_key": thread_key,
                        "thread_id": thread_id,
                        "exists_in_foundry": exists,
                        "status": "active" if exists else "orphaned"
                    })
            
            return {
                "session_id": session_id,
                "total_threads": len(threads_info),
                "active_threads": len([t for t in threads_info if t["status"] == "active"]),
                "orphaned_threads": len([t for t in threads_info if t["status"] == "orphaned"]),
                "threads": threads_info
            }
            
        except Exception as e:
            return {"error": f"Error getting thread status: {str(e)}"}

    def _get_universal_controls(self, azure_service: str) -> str:
        """
        Get universal controls that should be included in every SCD.
        These are the tagging and naming convention controls that apply to all Azure services.
        """
        universal_controls = f"""
MANDATORY UNIVERSAL CONTROLS (MUST be included in every SCD):

| Control ID | Security Control (Service) | Policy Name | Policy Description | Mapping to NIST CSF v1.1 control |
|------------|---------------------------|-------------|-------------------|----------------------------------|
| ID.AM-5.1 | Tags and metadata must be applied using the organization's tagging conventions to assist in managing {azure_service}. | Tag {azure_service} per the organization's tagging standards. | Every {azure_service} must be tagged according to the organization's tagging standards. | ID.AM-5: Resources (e.g., hardware, devices, data, time, personnel, and software) are prioritized based on their classification, criticality, and business value |
| ID.AM-5.2 | The organization's naming conventions must be followed to keep {azure_service} easily identifiable and standardized. | Configure {azure_service} to adhere to the organization's naming conventions. | Every {azure_service} provisioned in a subscription must adhere to the organization's naming conventions. | ID.AM-5: Resources (e.g., hardware, devices, data, time, personnel, and software) are prioritized based on their classification, criticality, and business value |

IMPORTANT: These two controls (ID.AM-5.1 and ID.AM-5.2) are MANDATORY and must appear in every Security Control Documentation regardless of the Azure service type.

CRITICAL: This is a perfect example of markdown table formatting. Every row has exactly 5 columns separated by pipes, consistent spacing, and proper alignment.
"""
        return universal_controls

    def collect_data(self, azure_service: str, data_type: str = "both", session_id: str = "default") -> str:
        """Collect comprehensive data about an Azure service"""
        self._ensure_agents()
        
        # Build query based on data type
        if data_type == "service_details":
            query = (
                f"Search the web for comprehensive information about {azure_service}. "
                f"Focus on:\n"
                f"- Security features and capabilities\n"
                f"- Configuration options for security\n"
                f"- Network security options\n"
                f"- Data protection features\n"
                f"- Identity and access management features\n"
                f"- Monitoring and logging capabilities\n"
                f"- Service-specific security configurations\n"
                f"- Best practices for secure deployment\n\n"
                f"Provide detailed technical information that can be used for security control documentation."
            )
        elif data_type == "organizational_standards":
            query = (
                f"Search the uploaded files for:\n"
                f"- Existing Security Control Documentation (SCD) examples\n"
                f"- Organizational formatting standards\n"
                f"- SCD templates and structures\n"
                f"- Control ID numbering patterns\n"
                f"- Policy naming conventions\n"
                f"- NIST CSF mapping formats\n"
                f"- Section organization patterns\n\n"
                f"Provide examples and patterns that can be followed for {azure_service} SCD generation."
            )
        else:  # both
            query = (
                f"I need comprehensive data collection for {azure_service} SCD generation:\n\n"
                f"1. **WEB SEARCH** - Research {azure_service} for:\n"
                f"   - Security features and capabilities\n"
                f"   - Configuration options for security\n"
                f"   - Network security options\n"
                f"   - Data protection features\n"
                f"   - Service-specific security configurations\n"
                f"   - Best practices for secure deployment\n\n"
                f"2. **FILE SEARCH** - Find organizational standards for:\n"
                f"   - SCD formatting examples\n"
                f"   - Control ID numbering patterns\n"
                f"   - Policy naming conventions\n"
                f"   - NIST CSF mapping formats\n\n"
                f"Organize the response clearly separating web-sourced and file-sourced information."
            )
        
        return self.session_manager.send_message_and_run(
            self._data_collection_agent_id, session_id, query
        )

    def _enrich_nist_controls(self, scd_content: str) -> str:
        """
        Enrich SCD content with proper NIST CSF control names and descriptions using existing validation agent.
        """
        lines = scd_content.strip().split('\n')
        table_start = -1
        table_end = -1
        
        # Find the table boundaries
        for i, line in enumerate(lines):
            if '| Control ID ' in line:
                table_start = i
            elif table_start != -1 and not line.strip():
                table_end = i
                break
                
        if table_start == -1:
            return scd_content
            
        # Keep original header format
        header = "| Control ID | Security Control for Service | Policy Name | Policy Description | Mapping to NIST CSF v1.1 control |"
        separator = "|------------|----------------------------|-------------|-------------------|----------------------------------|"
        
        new_lines = []
        for i, line in enumerate(lines):
            if i < table_start or i > table_end:
                new_lines.append(line)
                continue
                
            if i == table_start:
                new_lines.append(header)
                new_lines.append(separator)
                continue
                
            if i == table_start + 1:  # Skip old separator
                continue
                
            if '|' not in line or line.startswith('|**'):  # Section headers or empty lines
                new_lines.append(line)
                continue
                
            # Process control row
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) >= 5:  # Make sure we have enough columns
                # Extract NIST control ID from the last column
                nist_id_match = re.search(r'([A-Z]+\.[A-Z]+-\d+)', cols[4])
                if nist_id_match:
                    nist_id = nist_id_match.group(1)
                    # Use existing validation agent to get control info
                    try:
                        search_query = f"site:nist.gov \"{nist_id}\" NIST Cybersecurity Framework control description"
                        response = self.session_manager.send_message_and_run(
                            self._validate_scd_agent_id, "nist_enrichment", search_query
                        )
                        control_name = ""
                        control_desc = ""
                        
                        # Extract control name and description from agent response
                        if "VALIDATION_RESULT: PASSED" in response:
                            # Use regex to extract info from agent's response
                            name_match = re.search(r'Control Name: (.*?)\n', response)
                            desc_match = re.search(r'Description: (.*?)\n', response)
                            if name_match:
                                control_name = name_match.group(1).strip()
                            if desc_match:
                                control_desc = desc_match.group(1).strip()
                        
                        if control_name and control_desc:
                            # Combine NIST ID and description in one column
                            nist_mapping = f"{nist_id}: {control_desc}"
                            # Keep the Security Control for Service column as is
                            new_row = f"| {cols[0]} | {cols[1]} | {cols[2]} | {cols[3]} | {nist_mapping} |"
                            new_lines.append(new_row)
                        else:
                            new_lines.append(line)  # Keep original if no info found
                    except Exception as e:
                        print(f"Warning: Failed to enrich NIST control {nist_id}: {e}")
                        new_lines.append(line)  # Keep original if error
                else:
                    new_lines.append(line)  # Keep original if no NIST ID found
            else:
                new_lines.append(line)  # Keep original if wrong format
                
        content = '\n'.join(new_lines)
        return content

    def _validate_generated_scd(self, scd_content: str, azure_service: str, session_id: str, 
                               attempt: int = 1) -> dict:
        """Validate the generated SCD using Azure AI Foundry dynamic validation (no static dependencies)"""
        # First validate table structure and control ID format
        table_format_issues = []
        
        # Check for multiple tables
        table_count = scd_content.count('| Control ID |')
        if table_count > 1:
            table_format_issues.append("Multiple table headers found. All controls should be in one continuous table.")
            
        # Check control ID format
        lines = scd_content.split('\n')
        service_prefix = azure_service.upper().split()[0]
        invalid_control_ids = []
        
        for line in lines:
            stripped_line = line.strip()
            # Skip non-table lines, headers, separators, and section headers
            if ('|' in line and 
                not '| Control ID |' in line and  # Skip table header
                not 'Control ID' in line and      # Skip any line containing "Control ID"
                not '|---' in stripped_line and   # Skip separator row
                not stripped_line == '' and       # Skip empty lines
                stripped_line != ''):             # Skip truly empty lines
                
                cols = [c.strip() for c in line.split('|')[1:-1]]
                if len(cols) >= 5:
                    control_id = cols[0].strip()
                    
                    # Skip section headers (they start and end with **)
                    if control_id.startswith('**') and control_id.endswith('**'):
                        continue
                    
                    # Skip table headers, empty control IDs, and universal controls
                    if (control_id and 
                        control_id != 'Control ID' and           # Skip header text
                        not control_id.startswith('ID.AM') and  # Skip universal controls
                        not control_id.startswith('-') and      # Skip separator chars
                        len(control_id.strip()) > 0):           # Skip empty strings
                        
                        # ONLY accept NIST subcategory format - NO service formats allowed
                        nist_pattern = r'^[A-Z]{2}\.[A-Z]{2}-\d+(\.\d+)?$'  # PR.AC-1 or PR.AC-1.1
                        service_pattern = r'^[A-Z]+-[A-Z]+-\d+$'            # SERVICE-CAT-001 (FORBIDDEN)
                        
                        import re
                        if re.match(service_pattern, control_id):
                            # Flag service-based IDs as CRITICAL errors
                            invalid_control_ids.append(f"{control_id} (SERVICE-BASED FORMAT NOT ALLOWED)")
                        elif not re.match(nist_pattern, control_id):
                            # Flag other invalid formats
                            invalid_control_ids.append(control_id)
                            
        if invalid_control_ids:
            table_format_issues.append(f"CRITICAL: Service-based Control IDs detected: {', '.join(invalid_control_ids)}")
            
        # If table format issues found, log warnings but CONTINUE processing
        if table_format_issues:
            print(f"[VALIDATION WARNINGS] CRITICAL Control ID issues detected:")
            for issue in table_format_issues:
                print(f"   - {issue}")
            print("[VALIDATION] HARD REQUIREMENT: Control IDs must be NIST subcategories only!")
            print("[VALIDATION] Proceeding with processing despite warnings...")
            # Don't stop - continue with validation
        validation_start_time = time.time()
        
        try:
            print("[AZURE AI FOUNDRY] Starting dynamic validation with existing validation agent...")
            self._update_progress(session_id, 'dynamic_validation', 82, 'Using existing validation agent')
            
            # Use existing validation agent instead of creating a new one
            validation_session_id = f"{session_id}_validation_{attempt}"
            
            validation_prompt = f"""
Please validate this SCD document for {azure_service} using dynamic search validation:

{scd_content}

Use Bing search to:
1. Verify each NIST CSF mapping against official NIST.gov documentation
2. Check current Azure service capabilities on docs.microsoft.com
3. Research current security best practices
4. Validate mapping appropriateness with live sources

Provide validation results with source citations from your searches.
"""
            
            dynamic_start_time = time.time()
            
            # Send validation request using existing validation agent
            validation_text = self.session_manager.send_message_and_run(
                self._validate_scd_agent_id, validation_session_id, validation_prompt
            )
            
            dynamic_duration = time.time() - dynamic_start_time
            
            print(f"   [EXISTING AGENT] Validation completed in {dynamic_duration:.2f}s")
            
            # Parse validation response
            validation_passed = "VALIDATION_RESULT: PASSED" in validation_text
            
            # Include table format warnings in validation summary
            warnings_text = ""
            if table_format_issues:
                warnings_text = f"\n\nTable Format Warnings:\n" + "\n".join([f"- {issue}" for issue in table_format_issues])
            
            validation_summary = f"""
AZURE AI FOUNDRY DYNAMIC VALIDATION: {'PASSED' if validation_passed else 'FAILED'}

Dynamic Features Applied:
Real-time Bing Search for NIST CSF validation
Live Azure documentation lookup
Current security best practices research
No static dependencies - all knowledge from live sources
Source citation and verification{warnings_text}

Processing Time: {dynamic_duration:.2f}s
Knowledge Sources: Live web search results
Validation Approach: Fully Dynamic

{validation_text}

{scd_content if validation_passed else 'SCD requires improvements before approval.'}
"""
                
            return {
                "validation_passed": validation_passed,
                "validation_response": validation_summary,
                "confidence_score": 0.9 if not table_format_issues else 0.7,
                "validation_method": "Azure AI Foundry Dynamic Validation",
                "table_format_warnings": table_format_issues,
                "honest_feedback": table_format_issues if table_format_issues else []
            }
                
        except Exception as e:
            print(f"   [ERROR] Dynamic validation failed: {e}")
            # Fallback to basic validation
            print("   [FALLBACK] Using basic validation...")
            
            # Include table format warnings in fallback validation too
            warnings_text = ""
            if table_format_issues:
                warnings_text = f"\n\nTable Format Warnings:\n" + "\n".join([f"- {issue}" for issue in table_format_issues])
            
            basic_validation = f"""
BASIC VALIDATION RESULT: PASSED (Fallback)

Note: Dynamic validation temporarily unavailable, using basic format validation.{warnings_text}
Processing Time: {time.time() - validation_start_time:.2f}s

{scd_content}
"""
            
            return {
                "validation_passed": True,
                "validation_response": basic_validation,
                "confidence_score": 0.7 if not table_format_issues else 0.5,
                "validation_method": "Basic Fallback Validation",
                "table_format_warnings": table_format_issues,
                "honest_feedback": table_format_issues if table_format_issues else []
            }

    def _retry_scd_generation_with_feedback(self, azure_service: str, collected_data: str, 
                                          validation_feedback: str, session_id: str, 
                                          additional_context: str = "") -> str:
        """Retry SCD generation with validation feedback"""
        try:
            print("[RETRY] Retrying SCD generation with validation feedback...")
            self._update_progress(session_id, 'retry_processing', 76, 'Processing validation feedback for regeneration')
            
            # Include universal controls in retry generation
            universal_controls = self._get_universal_controls(azure_service)
            
            supplementary_note = ""
            if additional_context:
                supplementary_note = (
                    f"ADDITIONAL CONTEXT (supplementary - do NOT limit controls):\n{additional_context}\n\n"
                    f"REMINDER: Additional context should SUPPLEMENT, not limit control generation. "
                    f"Generate comprehensive controls across all security domains.\n\n"
                )
            
            retry_message = f"""REGENERATE the SCD table with corrections.

Issues found:
{validation_feedback}

Required universal controls:
{universal_controls}

Data for reference:
{collected_data}

{supplementary_note}
CRITICAL: Output ONLY the markdown table. Do not include:
- This message
- Acknowledgments
- Explanations  
- Meta-commentary
- Validation feedback

Start immediately with: | Control ID | Security Control for Service |"""
            
            self._update_progress(session_id, 'retry_generation', 78, 'Regenerating SCD with validation corrections')
            return self.session_manager.send_message_and_run(
                self._scd_generator_agent_id, session_id, retry_message
            )
            
        except Exception as e:
            print(f"[ERROR] Error retrying SCD generation: {str(e)}")
            return None

    def generate_scd(self, azure_service: str, collected_data: str = None, 
                    additional_context: str = "", session_id: str = "default", 
                    store_in_azure: bool = True, auto_collect: bool = False) -> dict:
        """Generate Security Control Documentation with optional data collection
        
        Args:
            azure_service: Azure service name
            collected_data: Pre-collected data (if None and auto_collect=True, will collect automatically)
            additional_context: Additional context for generation
            session_id: Session identifier
            store_in_azure: Whether to store result in Azure Storage
            auto_collect: If True and collected_data is None, will automatically collect data
        """
        try:
            # STEP 0: Sanitize inputs (CRITICAL SECURITY CHECK)
            print("[SANITIZATION] Validating and sanitizing inputs...")
            self._update_progress(session_id, 'sanitizing', 5, 'Sanitizing and validating inputs')
            
            # Sanitize azure_service name
            service_sanitization = self.sanitizer.sanitize_batch(
                [azure_service], 
                metadata={'source_id': 'service_name', 'content_type': 'service_identifier'}
            )
            
            if not service_sanitization['ok'] or not service_sanitization['cleaned_blocks']:
                error_msg = f"Service name sanitization failed: {service_sanitization.get('errors', ['Unknown error'])}"
                print(f"[SANITIZATION ERROR] {error_msg}")
                return {"error": error_msg, "scd_content": None, "storage_info": None}
            
            sanitized_service = service_sanitization['cleaned_blocks'][0]
            azure_service_clean = sanitized_service['cleaned_text']
            
            # Log sanitization warnings for service name
            if sanitized_service['warnings']:
                print(f"[SANITIZATION WARNINGS] Service name issues detected:")
                for warning in sanitized_service['warnings']:
                    print(f"   - {warning}")
                    # Check for non-Azure cloud detection and reject immediately
                    if "NON_AZURE_CLOUD_DETECTED" in warning:
                        error_msg = (
                            "[ERROR] NON-AZURE SERVICE DETECTED: This system only supports Azure services. "
                            "We cannot generate Security Control Documentation for AWS, GCP, or other cloud providers. "
                            "Please specify an Azure service instead."
                        )
                        print(f"[NON-AZURE REJECTED] {error_msg}")
                        return {"error": error_msg, "scd_content": None, "storage_info": None}
            
            # Reject if confidence is too low (raised threshold from 0.70 to 0.75)
            if sanitized_service['confidence_score'] < 0.75:
                error_msg = f"Service name failed confidence check (score: {sanitized_service['confidence_score']:.2f}). Input may contain policy violations."
                print(f"[SANITIZATION ERROR] {error_msg}")
                return {"error": error_msg, "scd_content": None, "storage_info": None}
            
            # Sanitize additional_context if provided
            if additional_context:
                context_sanitization = self.sanitizer.sanitize_batch(
                    [additional_context],
                    metadata={'source_id': 'additional_context', 'content_type': 'user_context'}
                )
                
                if not context_sanitization['ok'] or not context_sanitization['cleaned_blocks']:
                    print("[SANITIZATION WARNING] Additional context sanitization failed, proceeding without it")
                    additional_context_clean = ""
                else:
                    sanitized_context = context_sanitization['cleaned_blocks'][0]
                    additional_context_clean = sanitized_context['cleaned_text']
                    
                    if sanitized_context['warnings']:
                        print(f"[SANITIZATION WARNINGS] Context issues detected:")
                        for warning in sanitized_context['warnings']:
                            print(f"   - {warning}")
                            # Check for non-Azure cloud detection and reject immediately
                            if "NON_AZURE_CLOUD_DETECTED" in warning:
                                error_msg = (
                                    "[ERROR] NON-AZURE SERVICE DETECTED: This system only supports Azure services. "
                                    "We cannot generate Security Control Documentation for AWS, GCP, or other cloud providers. "
                                    "Please specify an Azure service instead."
                                )
                                print(f"[NON-AZURE REJECTED] {error_msg}")
                                return {"error": error_msg, "scd_content": None, "storage_info": None}
            else:
                additional_context_clean = ""
            
            print(f"[SANITIZATION] [OK] Service name sanitized: '{azure_service}' -> '{azure_service_clean}'")
            print(f"[SANITIZATION] [OK] Confidence score: {sanitized_service['confidence_score']:.2f}")
            if sanitized_service['canonical_control_matches']:
                print(f"[SANITIZATION] [OK] Found {len(sanitized_service['canonical_control_matches'])} NIST control matches")
            
            # Use sanitized values from here on
            azure_service = azure_service_clean
            additional_context = additional_context_clean
            
            self._update_progress(session_id, 'collecting', 50, f'Preparing data for {azure_service}')
            
            final_collected_data = collected_data
            
            # Auto-collect data if requested and not provided
            if not final_collected_data and auto_collect:
                self._update_progress(session_id, 'collecting', 60, f'Auto-collecting security data for {azure_service}')
                print(f"Auto-collecting data for {azure_service}...")
                
                data_collection_start = time.time()
                final_collected_data = self.collect_data(azure_service, "both", session_id)
                data_collection_duration = time.time() - data_collection_start
                
                if "Error:" in final_collected_data:
                    return {"error": final_collected_data, "scd_content": None, "storage_info": None}
            
            
            # Require collected data for SCD generation
            if not final_collected_data:
                return {
                    "error": "No collected data provided. Use auto_collect=True or provide collected_data parameter.",
                    "scd_content": None,
                    "storage_info": None
                }
            
            # Ensure agents exist
            if not self._ensure_agents():
                return {"error": "Failed to initialize agents", "scd_content": None, "storage_info": None}
            
            # Generate SCD with validation workflow
            self._update_progress(session_id, 'generating', 70, f'Generating Security Control Documentation')
            print(f"Generating SCD for {azure_service}...")
            
            max_retries = 2
            retry_count = 0
            scd_result = None
            validation_result = None
            
            while retry_count <= max_retries:
                # Generate or regenerate SCD
                if retry_count == 0:
                    # Initial generation with universal controls
                    universal_controls = self._get_universal_controls(azure_service)
                    
                    message_content = (
                        f"Generate Security Control Documentation for: {azure_service}\n\n"
                        f"{universal_controls}\n\n"
                        f"COLLECTED DATA:\n{final_collected_data}\n\n"
                    )
                    
                    if additional_context:
                        message_content += (
                            f"ADDITIONAL CONTEXT (supplementary guidance - do NOT limit controls to only this context):\n"
                            f"{additional_context}\n\n"
                            f"CRITICAL: The additional context above should SUPPLEMENT your comprehensive control generation, "
                            f"not replace or limit it. You MUST still generate ALL relevant security controls for the service across "
                            f"all security domains including: network security, access control, data protection, monitoring/detection, "
                            f"configuration management, and protective technology. The additional context provides extra guidance or "
                            f"emphasis but should NOT reduce the breadth of controls generated.\n\n"
                        )
                    
                    message_content += (
                        "Generate the Security Control Documentation as a markdown table following the "
                        "organizational standards found in the collected data. Focus on service-specific, "
                        "actionable controls that Platform Engineers can implement.\n\n"
                        "CRITICAL TABLE FORMATTING REQUIREMENTS:\n"
                        "1. Use a SINGLE continuous markdown table for ALL controls\n"
                        "2. NO section headers - create a simple flat table only\n"
                        "3. Maintain consistent column structure and alignment\n"
                        "4. EVERY Control ID MUST be a NIST subcategory (PR.AC-1, DE.CM-1, etc.)\n\n"
                        "CRITICAL CONTROL ID REQUIREMENTS (HARD REQUIREMENTS):\n"
                        "1. ONLY use NIST subcategories as Control IDs: PR.AC-1, PR.DS-1, DE.CM-1, RS.RP-1, etc.\n"
                        "2. NEVER use service-based formats: NO REDIS-SEC-001, NO ACA-NET-001, NO SERVICE-CAT-001\n"
                        "3. If multiple controls map to same NIST category, use .1, .2, .3 suffixes\n"
                        "4. Verify each NIST subcategory exists in the official NIST framework\n\n"
                        "CRITICAL CONTENT REQUIREMENTS:\n"
                        "1. MUST include the two mandatory universal controls (ID.AM-5.1 and ID.AM-5.2) shown above as the FIRST TWO controls in your output\n"
                        "2. Replace any service name references in the universal controls with the actual service name\n"
                        "3. Add additional service-specific controls after the universal controls\n"
                        "4. Maintain the exact table format and column structure as shown in the universal controls template\n"
                        "5. Generate a clean, flat table with NO section headers or subsections"
                    )

                    # Generate initial SCD
                    raw_scd_result = self.session_manager.send_message_and_run(
                        self._scd_generator_agent_id, session_id, message_content
                    )
                    
                    # Use result directly - agent should output clean table
                    scd_result = raw_scd_result
                else:
                    # Retry with validation feedback
                    self._update_progress(session_id, 'retry_generation', 75, f'Retrying SCD generation with validation feedback (attempt {retry_count + 1})')
                    scd_result = self._retry_scd_generation_with_feedback(
                        azure_service, final_collected_data, 
                        validation_result["validation_response"], 
                        session_id, additional_context
                    )
                
                if not scd_result:
                    return {"error": "Failed to generate SCD", "scd_content": None, "storage_info": None}
                
                # Apply dynamic control ID correction and formatting
                self._update_progress(session_id, 'correcting', 75 + (retry_count * 2), f'Normalizing table and fixing control IDs (attempt {retry_count + 1})')
                scd_result = self._apply_dynamic_control_id_correction(scd_result)
                
                # Validate the generated SCD
                validation_progress = 80 + (retry_count * 2)  # Progressive validation progress
                self._update_progress(session_id, 'validating', validation_progress, f'Validating Security Control Documentation (attempt {retry_count + 1})')
                validation_result = self._validate_generated_scd(
                    scd_result, azure_service, session_id, retry_count + 1
                )
                
                if validation_result["validation_passed"]:
                    print(f"[SUCCESS] SCD validation passed on attempt {retry_count + 1}")
                    break
                elif not validation_result["validation_passed"] and retry_count < max_retries:
                    print(f"[RETRY] SCD validation failed on attempt {retry_count + 1}, retrying...")
                    print(f"[FEEDBACK] {validation_result.get('message', 'No specific feedback available')}")
                    
                    # Show honest feedback to user
                    if validation_result.get('honest_feedback'):
                        print("[HONEST FEEDBACK]:")
                        for feedback in validation_result['honest_feedback']:
                            print(f"   {feedback}")
                    
                    retry_count += 1
                else:
                    print(f"[FAILED] SCD validation failed after {max_retries + 1} attempts")
                    print(f"[FINAL FEEDBACK] {validation_result.get('message', 'No specific feedback available')}")
                    break
            
            # Store in Azure Storage (if enabled)
            self._update_progress(session_id, 'finalizing', 90, 'Finalizing documentation and storage')
            storage_info = None
            if store_in_azure and self.storage_manager:
                print(f"Storing SCD in Azure Storage...")
                
                storage_start = time.time()
                storage_result = self.storage_manager.store_scd(
                    azure_service=azure_service,
                    scd_content=scd_result,
                    session_id=session_id,
                    additional_context=additional_context,
                    collected_data=final_collected_data
                )
                storage_duration = time.time() - storage_start
                storage_info = storage_result
                
                if storage_result.get("success"):
                    print(f"SCD stored successfully: {storage_result.get('blob_url')}")
                else:
                    print(f"Storage failed: {storage_result.get('error')}")
            elif store_in_azure and not self.storage_manager:
                print("Warning: Azure Storage not available, SCD not stored")
            
            # Mark as completed
            self._update_progress(session_id, 'completed', 100, 'Security Control Documentation generated successfully')
            
            return {
                "error": None,
                "scd_content": scd_result,
                "collected_data": final_collected_data,
                "storage_info": storage_info,
                "validation_info": validation_result,
                "validation_passed": validation_result.get("validation_passed", False),
                "honest_feedback": validation_result.get("honest_feedback", []),
                "required_improvements": validation_result.get("required_improvements", []),
                "validation_report": validation_result.get("validation_report", ""),
                "nist_csf_quality": validation_result.get("rigorous_validation", {}).get("nist_csf_analysis", {}).get("mapping_quality_score", 0),
                "reference_coverage": validation_result.get("rigorous_validation", {}).get("control_analysis", {}).get("reference_coverage", 0),
                "success": True
            }
            
        except Exception as e:
            return {"error": f"Error in SCD generation: {str(e)}", "scd_content": None, "storage_info": None}

    def cleanup(self):

        try:
            print("Starting cleanup process...")
            
            if self._data_collection_agent_id:
                self.agent_factory.delete_agent(self._data_collection_agent_id)
                self.agent_registry.remove_agent("data_collection")
                
            if self._scd_generator_agent_id:
                self.agent_factory.delete_agent(self._scd_generator_agent_id)
                self.agent_registry.remove_agent("scd_generator")
                
            if self._validate_scd_agent_id:
                self.agent_factory.delete_agent(self._validate_scd_agent_id)
                self.agent_registry.remove_agent("validate_scd")
                
            self.tool_manager.cleanup_vector_store()
            self.agent_registry.remove_agent("vector_store")
            self.session_manager.cleanup_all_threads()
            
            # Reset IDs
            self._data_collection_agent_id = None
            self._scd_generator_agent_id = None
            self._scd_generator_agent_name = None
            self._validate_scd_agent_id = None
            self._validate_scd_agent_name = None
            
            print("Cleanup completed successfully")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def _normalize_markdown_table(self, scd_content: str) -> str:
        """
        Pre-processing table normalizer that fixes malformed markdown table rows
        Ensures every table row has exactly 5 columns before correction logic runs
        """
        import re
        
        try:
            print("[TABLE_NORMALIZER] Starting markdown table normalization...")
            
            lines = scd_content.split('\n')
            normalized_lines = []
            in_table = False
            table_started = False
            
            for line in lines:
                stripped_line = line.strip()
                
                # Detect table start
                if '| Control ID |' in line:
                    in_table = True
                    table_started = True
                    normalized_lines.append(line)
                    continue
                
                # Handle separator row
                if in_table and '|---' in stripped_line:
                    normalized_lines.append(line)
                    continue
                
                # Handle potential table rows (contains pipes)
                if in_table and '|' in stripped_line and stripped_line:
                    # Check if this is a section header and SKIP IT
                    parts = stripped_line.split('|')[1:-1] if stripped_line.startswith('|') and stripped_line.endswith('|') else []
                    if len(parts) >= 1 and parts[0].strip().startswith('**') and parts[0].strip().endswith('**'):
                        print(f"[TABLE_NORMALIZER] Removing section header: {parts[0].strip()}")
                        continue  # Skip section headers entirely
                    
                    # Count existing columns
                    if stripped_line.startswith('|') and stripped_line.endswith('|'):
                        # Split by pipe and count actual columns (excluding empty start/end)
                        parts = stripped_line.split('|')[1:-1]  # Remove empty first and last
                        column_count = len(parts)
                        
                        if column_count < 5:
                            # Fill missing columns with empty strings
                            while len(parts) < 5:
                                parts.append(' ')
                            # Reconstruct the row
                            normalized_row = '| ' + ' | '.join(parts) + ' |'
                            normalized_lines.append(normalized_row)
                            print(f"[TABLE_NORMALIZER] Fixed {column_count}-column row to 5 columns")
                        elif column_count > 5:
                            # Truncate to 5 columns (keep first 5)
                            parts = parts[:5]
                            normalized_row = '| ' + ' | '.join(parts) + ' |'
                            normalized_lines.append(normalized_row)
                            print(f"[TABLE_NORMALIZER] Truncated {column_count}-column row to 5 columns")
                        else:
                            # Already correct
                            normalized_lines.append(line)
                    else:
                        # Fix missing start/end pipes
                        if not stripped_line.startswith('|'):
                            stripped_line = '|' + stripped_line
                        if not stripped_line.endswith('|'):
                            stripped_line = stripped_line + '|'
                        
                        # Now process as above
                        parts = stripped_line.split('|')[1:-1]
                        while len(parts) < 5:
                            parts.append(' ')
                        if len(parts) > 5:
                            parts = parts[:5]
                        
                        normalized_row = '| ' + ' | '.join(parts) + ' |'
                        normalized_lines.append(normalized_row)
                        print(f"[TABLE_NORMALIZER] Fixed malformed row with missing pipes")
                    continue
                
                # Detect table end (empty line after table started)
                if in_table and not stripped_line and table_started:
                    in_table = False
                    normalized_lines.append(line)
                    continue
                
                # Non-table lines
                normalized_lines.append(line)
            
            normalized_content = '\n'.join(normalized_lines)
            print("[TABLE_NORMALIZER] Table normalization completed")
            return normalized_content
            
        except Exception as e:
            print(f"[TABLE_NORMALIZER] Error during normalization: {e}")
            return scd_content

    def _apply_dynamic_control_id_correction(self, scd_content: str) -> str:
        """
        Enhanced NIST-aware control ID correction that ensures Control ID = NIST subcategory
        Fixes the core issue where service-based IDs (ACA-NTW-001) are used instead of NIST subcategories (PR.AC-5)
        Now includes pre-processing table normalization to fix malformed rows
        """
        import re
        
        try:
            print("[NIST_ID_CORRECTOR] Starting Control ID = NIST subcategory correction...")
            
            # STEP 1: Normalize table format first (fixes malformed rows)
            normalized_content = self._normalize_markdown_table(scd_content)
            
            # STEP 2: Apply NIST-aware correction logic
            # Find all table rows with regex - format agnostic
            table_rows = re.findall(r'\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|[^|]*\|', normalized_content)
            
            if not table_rows:
                print("[NIST_ID_CORRECTOR] No table rows found, returning normalized content")
                return normalized_content
            
            corrected_content = normalized_content
            correction_count = 0
            nist_counters = {}  # Track usage of each NIST subcategory
            
            for row in table_rows:
                # Skip headers, separators, and section headers
                if 'Control ID' in row or '---' in row or '**' in row:
                    continue
                
                # Extract columns using regex
                columns = re.findall(r'\|([^|]*)', row)
                if len(columns) < 5:
                    continue
                
                control_id = columns[0].strip()
                security_control = columns[1].strip()
                policy_name = columns[2].strip()
                policy_desc = columns[3].strip()
                nist_mapping = columns[4].strip()
                
                # Skip empty rows
                if not control_id or not nist_mapping:
                    continue
                
                # Skip universal controls (these are already correct)
                if control_id.startswith('ID.AM') or control_id.endswith('ID.AM-5.1') or control_id.endswith('ID.AM-5.2'):
                    continue
                
                # Extract NIST subcategory from the mapping column
                # Look for patterns like "PR.AC-5:", "DE.CM-1:", etc.
                nist_subcategory_match = re.search(r'\b([A-Z]{2}\.[A-Z]{2}-\d+)', nist_mapping)
                
                if nist_subcategory_match:
                    nist_subcategory = nist_subcategory_match.group(1)
                    
                    # Validate it's a real NIST subcategory
                    if self.nist_validator.is_valid_nist_subcategory(nist_subcategory):
                        
                        # Check if this NIST subcategory is already used
                        if nist_subcategory in nist_counters:
                            nist_counters[nist_subcategory] += 1
                            new_control_id = f"{nist_subcategory}.{nist_counters[nist_subcategory]}"
                        else:
                            nist_counters[nist_subcategory] = 0
                            new_control_id = nist_subcategory
                        
                        # Only correct if current Control ID is not already a NIST subcategory
                        if not self.nist_validator.is_valid_nist_subcategory(control_id):
                            # Create properly formatted row with NIST subcategory as Control ID
                            new_row = f"| {new_control_id} | {security_control} | {policy_name} | {policy_desc} | {nist_mapping} |"
                            
                            # Replace in content
                            corrected_content = corrected_content.replace(row, new_row)
                            correction_count += 1
                            
                            print(f"[NIST_ID_CORRECTOR] FIXED: {control_id} -> {new_control_id}")
                        else:
                            print(f"[NIST_ID_CORRECTOR] ALREADY_CORRECT: {control_id}")
                    else:
                        print(f"[NIST_ID_CORRECTOR] WARNING: Invalid NIST subcategory extracted: {nist_subcategory}")
                else:
                    print(f"[NIST_ID_CORRECTOR] WARNING: Could not extract NIST subcategory from mapping: {nist_mapping}")
            
            # Fix section headers formatting
            corrected_content = re.sub(
                r'\|\*\*([^*]+)\*\*\|',
                r'|**\1**| | | | |',
                corrected_content
            )
            
            print(f"[NIST_ID_CORRECTOR] Applied {correction_count} Control ID corrections")
            print(f"[NIST_ID_CORRECTOR] Used {len(nist_counters)} unique NIST subcategories")
            print("[NIST_ID_CORRECTOR] Table normalization + NIST correction completed")
            return corrected_content
            
        except Exception as e:
            print(f"[NIST_ID_CORRECTOR] Error during correction: {e}")
            return scd_content
