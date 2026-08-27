"""
Session Manager - Handles thread management and agent execution
"""
from typing import Dict, Optional
import json
import os

class SessionManager:
    def __init__(self, agents_client):
        self.agents_client = agents_client
        self.conversation_history_file = "conversation_history.json"
        self._threads: Dict[str, str] = {}  # Maps session IDs to thread IDs
        self._load_persisted_threads()  # Load threads from conversation history

    def _load_persisted_threads(self):
        """Load thread IDs from conversation history file"""
        if os.path.exists(self.conversation_history_file):
            try:
                with open(self.conversation_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                # Extract thread IDs from conversation history
                for session_id, session_data in history.items():
                    for service, service_data in session_data.items():
                        if 'thread_id' in service_data and service_data['thread_id']:
                            # Use the service-specific thread ID as the session thread ID
                            # This maintains compatibility with existing conversation structure
                            if session_id not in self._threads:
                                self._threads[session_id] = service_data['thread_id']
                                print(f"Loaded existing thread for session {session_id}: {service_data['thread_id']}")
                
                print(f"Loaded {len(self._threads)} persisted threads")
            except Exception as e:
                print(f"Warning: Could not load persisted threads: {e}")

    def _update_conversation_history_with_thread(self, session_id: str, thread_id: str):
        """Update conversation history file with thread ID"""
        try:
            history = {}
            if os.path.exists(self.conversation_history_file):
                with open(self.conversation_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            # Ensure session exists
            if session_id not in history:
                history[session_id] = {}
            
            # Store thread ID in session metadata
            if '_metadata' not in history[session_id]:
                history[session_id]['_metadata'] = {}
            
            history[session_id]['_metadata']['primary_thread_id'] = thread_id
            history[session_id]['_metadata']['last_thread_update'] = self._get_current_timestamp()
            
            # Save updated history
            with open(self.conversation_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Warning: Could not update conversation history with thread ID: {e}")

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def get_or_create_thread(self, session_id: str) -> str:
        """Get an existing thread for the session, or create a new one if not present."""
        if session_id in self._threads:
            print(f"Reusing existing thread for session {session_id}: {self._threads[session_id]}")
            return self._threads[session_id]
        
        # Create new thread
        thread = self.agents_client.threads.create()
        self._threads[session_id] = thread.id
        
        # Persist thread ID to conversation history
        self._update_conversation_history_with_thread(session_id, thread.id)
        
        print(f"Created new thread for session {session_id}: {thread.id}")
        return thread.id

    def delete_thread(self, session_id: str):
        """Delete the thread for the session and remove from mapping."""
        thread_id = self._threads.get(session_id)
        if thread_id:
            try:
                self.agents_client.threads.delete(thread_id=thread_id)
                print(f"Deleted thread for session {session_id}: {thread_id}")
            except Exception as cleanup_error:
                print(f"Warning: Failed to cleanup thread {thread_id} - {cleanup_error}")
            
            # Remove from memory
            del self._threads[session_id]
            
            # Remove from conversation history
            self._remove_thread_from_conversation_history(session_id)

    def _remove_thread_from_conversation_history(self, session_id: str):
        """Remove thread ID from conversation history file"""
        try:
            if os.path.exists(self.conversation_history_file):
                with open(self.conversation_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                
                if session_id in history and '_metadata' in history[session_id]:
                    if 'primary_thread_id' in history[session_id]['_metadata']:
                        del history[session_id]['_metadata']['primary_thread_id']
                    
                    # Clean up empty metadata
                    if not history[session_id]['_metadata']:
                        del history[session_id]['_metadata']
                
                with open(self.conversation_history_file, 'w', encoding='utf-8') as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)
                    
        except Exception as e:
            print(f"Warning: Could not remove thread from conversation history: {e}")

    def send_message_and_run(self, agent_id: str, session_id: str, message: str) -> str:
        """Send a message to an agent and get the response"""
        thread_id = self.get_or_create_thread(session_id)
        
        # Send message
        self.agents_client.messages.create(
            thread_id=thread_id,
            role="user",
            content=message,
        )
        
        # Run the agent
        run = self.agents_client.runs.create_and_process(
            thread_id=thread_id,
            agent_id=agent_id
        )
        
        # Check run status
        if run.status != "completed":
            print(f"[WARNING] Agent run did not complete successfully. Status: {run.status}")
            if run.status == "failed":
                print(f"[ERROR] Run failed: {getattr(run, 'last_error', 'Unknown error')}")
                return f"ERROR: Agent run failed with status: {run.status}"
        
        # Get response - filter for assistant messages only
        messages = self.agents_client.messages.list(thread_id=thread_id)
        messages_list = list(messages)
        
        # Find the most recent assistant message (not user message)
        for msg in messages_list:
            if msg.role == "assistant":
                response = msg.content[0].text.value
                return response
        
        # If no assistant message found, something went wrong
        print("[ERROR] No assistant response found after agent run")
        return "ERROR: No response from agent"

    def send_message_to_agent(self, agent_id: str, message: str, session_id: str = None) -> str:
        """Send a message to an agent and get the response - alias for send_message_and_run"""
        if session_id is None:
            session_id = f"default_session_{agent_id}"
        return self.send_message_and_run(agent_id, session_id, message)

    def cleanup_all_threads(self):
        """Clean up all threads"""
        for session_id in list(self._threads.keys()):
            self.delete_thread(session_id)

    def get_active_threads(self) -> Dict[str, str]:
        """Get all active thread mappings for monitoring"""
        return self._threads.copy()

    def get_thread_count(self) -> int:
        """Get count of active threads"""
        return len(self._threads)

    def validate_thread_exists(self, session_id: str) -> bool:
        """Validate that a thread actually exists in AI Foundry"""
        thread_id = self._threads.get(session_id)
        if not thread_id:
            return False
        
        try:
            # Try to access the thread to verify it exists
            self.agents_client.messages.list(thread_id=thread_id, limit=1)
            return True
        except Exception:
            print(f"Thread {thread_id} for session {session_id} no longer exists, removing from cache")
            # Remove invalid thread from memory and persistence
            del self._threads[session_id]
            self._remove_thread_from_conversation_history(session_id)
            return False
