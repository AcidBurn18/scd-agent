"""
Tool Manager - Handles tool creation and setup
"""
import os
import glob
from azure.ai.agents.models import BingCustomSearchTool, FileSearchTool, FilePurpose, ToolResources, ConnectedAgentTool
from dotenv import load_dotenv

load_dotenv()

class ToolManager:
    def __init__(self, agents_client, project):
        self.agents_client = agents_client
        self.project = project
        
        # Separate Bing configurations for different purposes
        self.data_collection_bing_connection = os.getenv("DATA_COLLECTION_BING_CONNECTION_NAME")
        self.data_collection_bing_instance = os.getenv("DATA_COLLECTION_BING_INSTANCE_NAME")
        
        self.validation_bing_connection = os.getenv("VALIDATION_BING_CONNECTION_NAME") 
        self.validation_bing_instance = os.getenv("VALIDATION_BING_INSTANCE_NAME")
        
        self._data_collection_bing_connection_id = None
        self._validation_bing_connection_id = None
        self._vector_store_id = None

    def setup_data_collection_bing_tool(self) -> BingCustomSearchTool:
        """Setup Bing search tool specifically for Azure service data collection (docs.microsoft.com focus)"""
        if not self._data_collection_bing_connection_id:
            bing_connection = self.project.connections.get(name=self.data_collection_bing_connection)
            self._data_collection_bing_connection_id = bing_connection.id
            print(f"Connected to Data Collection Bing: {self._data_collection_bing_connection_id}")
        
        print(f"[DEBUG] Data Collection Bing - Connection: {self.data_collection_bing_connection}, Instance: {self.data_collection_bing_instance}")
        return BingCustomSearchTool(
            connection_id=self._data_collection_bing_connection_id, 
            instance_name=self.data_collection_bing_instance
        )

    def setup_validation_bing_tool(self) -> BingCustomSearchTool:
        """Setup Bing search tool specifically for NIST CSF validation (nist.gov focus)"""
        if not self._validation_bing_connection_id:
            bing_connection = self.project.connections.get(name=self.validation_bing_connection)
            self._validation_bing_connection_id = bing_connection.id
            print(f"Connected to Validation Bing: {self._validation_bing_connection_id}")
        
        print(f"[DEBUG] Validation Bing - Connection: {self.validation_bing_connection}, Instance: {self.validation_bing_instance}")
        return BingCustomSearchTool(
            connection_id=self._validation_bing_connection_id, 
            instance_name=self.validation_bing_instance
        )

    def setup_file_search_tool(self) -> tuple[FileSearchTool, str]:
        """Setup file search tool with vector store"""
        if not self._vector_store_id:
            files_folder = os.path.join(os.path.dirname(__file__), "files")
            if not os.path.exists(files_folder):
                raise Exception("'files' folder not found. Please create a 'files' folder and add your documents.")
            
            file_patterns = ["*.pdf", "*.docx", "*.txt", "*.md"]
            file_paths = []
            for pattern in file_patterns:
                file_paths.extend(glob.glob(os.path.join(files_folder, pattern)))
            
            if not file_paths:
                raise Exception(f"No supported files found in 'files' folder at {files_folder}. Supported formats: PDF, DOCX, TXT, MD")
            
            uploaded_file_ids = []
            for file_path in file_paths:
                try:
                    file = self.agents_client.files.upload_and_poll(
                        file_path=file_path,
                        purpose=FilePurpose.AGENTS
                    )
                    uploaded_file_ids.append(file.id)
                    print(f"Uploaded: {os.path.basename(file_path)} -> {file.id}")
                except Exception as e:
                    print(f"Failed to upload {file_path}: {str(e)}")
            
            if not uploaded_file_ids:
                raise Exception("Failed to upload any files from 'files' folder.")
            
            vector_store = self.agents_client.vector_stores.create_and_poll(
                file_ids=uploaded_file_ids,
                name=f"data_collection_vector_store_{len(uploaded_file_ids)}_files"
            )
            self._vector_store_id = vector_store.id
            print(f"Created vector store: {self._vector_store_id} with {len(uploaded_file_ids)} files")
        
        file_search_tool = FileSearchTool(vector_store_ids=[self._vector_store_id])
        return file_search_tool, self._vector_store_id

    def get_file_search_tool_definition(self):
        """Get file search tool definition"""
        from azure.ai.agents.models import FileSearchToolDefinition
        return FileSearchToolDefinition()

    def create_connected_agent_tool(self, agent_id: str, agent_name: str) -> ConnectedAgentTool:
        """Create connected agent tool"""
        return ConnectedAgentTool(
            id=agent_id,
            name=agent_name, 
            description="Use this agent to generate Security Control Documentation (SCD) after collecting comprehensive data about an Azure service. Call this agent when you have gathered sufficient information about Azure service security features, capabilities, and organizational formatting standards, and need to create the final SCD markdown table."
        )

    def combine_tools_and_resources(self, bing_tool, file_search_tool, connected_agent_tool, vector_store_id):
        """Combine all tools and create tool resources"""
        all_tools = bing_tool.definitions + file_search_tool.definitions + connected_agent_tool.definitions
        
        tool_resources = ToolResources(
            file_search={"vector_store_ids": [vector_store_id]}
        )
        
        return all_tools, tool_resources

    def cleanup_vector_store(self):
        """Clean up vector store"""
        if self._vector_store_id:
            try:
                self.agents_client.vector_stores.delete(self._vector_store_id)
                print(f"Deleted vector store: {self._vector_store_id}")
                self._vector_store_id = None
            except Exception as e:
                print(f"Error deleting vector store: {e}")

    @property
    def vector_store_id(self):
        return self._vector_store_id

    def get_vector_store_id(self):
        """Get the current vector store ID"""
        return self._vector_store_id
