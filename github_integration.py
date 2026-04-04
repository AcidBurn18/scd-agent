"""
GitHub Integration for SCD Generator
Handles automatic branch creation, file upload, and PR creation
"""
import os
import requests
import json
from datetime import datetime
from typing import Dict, Optional, Tuple
import base64

class GitHubIntegrator:
    def __init__(self):
        """Initialize GitHub integrator with configuration from environment variables"""
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.repo_owner = os.getenv("GITHUB_REPO_OWNER", "Deloitte-US-Consulting")
        self.repo_name = os.getenv("GITHUB_REPO_NAME", "security-control-docs")
        self.base_branch = os.getenv("GITHUB_BASE_BRANCH", "main")
        self.scd_path_prefix = os.getenv("GITHUB_SCD_PATH_PREFIX", "docs/scd")
        
        # GitHub API base URL
        self.api_base = "https://api.github.com"
        
        # Headers for GitHub API
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SCD-Generator-Bot/1.0"
        }
    
    def is_configured(self) -> bool:
        """Check if GitHub integration is properly configured"""
        return bool(self.github_token and self.repo_owner and self.repo_name)
    
    def create_branch_and_pr(self, scd_content: str, service_name: str, session_id: str) -> Dict:
        """
        Complete GitHub integration workflow:
        1. Create new branch
        2. Upload SCD file
        3. Create pull request
        
        Returns dict with success status and details
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "GitHub integration not configured. Missing GITHUB_TOKEN or repository settings.",
                "pr_url": None
            }
        
        try:
            # Step 1: Get latest commit SHA from base branch
            base_sha = self._get_latest_commit_sha()
            if not base_sha:
                return {
                    "success": False,
                    "error": "Failed to get latest commit from base branch",
                    "pr_url": None
                }
            
            # Step 2: Create new branch
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            branch_name = f"scd-{service_name.lower().replace(' ', '-')}-{timestamp}"
            
            branch_created = self._create_branch(branch_name, base_sha)
            if not branch_created:
                return {
                    "success": False,
                    "error": f"Failed to create branch: {branch_name}",
                    "pr_url": None
                }
            
            # Step 3: Upload SCD file
            file_path = f"{self.scd_path_prefix}/{service_name.lower().replace(' ', '-')}/scd-{timestamp}.md"
            file_uploaded = self._upload_file(file_path, scd_content, branch_name, service_name)
            if not file_uploaded:
                return {
                    "success": False,
                    "error": f"Failed to upload SCD file to branch: {branch_name}",
                    "pr_url": None
                }
            
            # Step 4: Create pull request
            pr_result = self._create_pull_request(branch_name, service_name, session_id, file_path)
            if pr_result["success"]:
                return {
                    "success": True,
                    "branch_name": branch_name,
                    "file_path": file_path,
                    "pr_url": pr_result["pr_url"],
                    "pr_number": pr_result["pr_number"]
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to create pull request: {pr_result['error']}",
                    "pr_url": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"GitHub integration failed: {str(e)}",
                "pr_url": None
            }
    
    def _get_latest_commit_sha(self) -> Optional[str]:
        """Get the latest commit SHA from the base branch"""
        try:
            url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/git/refs/heads/{self.base_branch}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                return data["object"]["sha"]
            else:
                print(f"Failed to get latest commit SHA: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error getting latest commit SHA: {e}")
            return None
    
    def _create_branch(self, branch_name: str, base_sha: str) -> bool:
        """Create a new branch from the base SHA"""
        try:
            url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/git/refs"
            data = {
                "ref": f"refs/heads/{branch_name}",
                "sha": base_sha
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 201:
                print(f"Successfully created branch: {branch_name}")
                return True
            else:
                print(f"Failed to create branch: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error creating branch: {e}")
            return False
    
    def _upload_file(self, file_path: str, content: str, branch_name: str, service_name: str) -> bool:
        """Upload SCD file to the specified branch"""
        try:
            # Encode content to base64
            content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}"
            data = {
                "message": f"Add SCD for {service_name}",
                "content": content_encoded,
                "branch": branch_name
            }
            
            response = requests.put(url, headers=self.headers, json=data)
            
            if response.status_code == 201:
                print(f"Successfully uploaded file: {file_path}")
                return True
            else:
                print(f"Failed to upload file: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False
    
    def _create_pull_request(self, branch_name: str, service_name: str, session_id: str, file_path: str) -> Dict:
        """Create a pull request for the SCD"""
        try:
            url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/pulls"
            
            # Create PR title and body
            pr_title = f"Add Security Control Documentation for {service_name}"
            pr_body = f"""## Security Control Documentation

**Service:** {service_name}
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Session ID:** {session_id}
**File:** `{file_path}`

### Changes
- Added comprehensive Security Control Documentation for {service_name}
- Generated using AI Foundry SCD Generator
- Includes security controls, compliance mappings, and implementation guidance

### Review Notes
Please review the security controls and ensure they align with organizational standards and compliance requirements.

---
*This PR was automatically generated by the SCD Generator system.*
"""
            
            data = {
                "title": pr_title,
                "head": branch_name,
                "base": self.base_branch,
                "body": pr_body,
                "draft": False
            }
            
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code == 201:
                pr_data = response.json()
                print(f"Successfully created PR: {pr_data['html_url']}")
                return {
                    "success": True,
                    "pr_url": pr_data["html_url"],
                    "pr_number": pr_data["number"]
                }
            else:
                print(f"Failed to create PR: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"GitHub API error: {response.status_code} - {response.text}"
                }
        except Exception as e:
            print(f"Error creating pull request: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_pr_status(self, pr_number: int) -> Dict:
        """Get current status of a pull request"""
        try:
            url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                pr_data = response.json()
                return {
                    "success": True,
                    "pr_number": pr_data.get("number"),
                    "title": pr_data.get("title", "No title"),
                    "state": pr_data.get("state", "unknown"),  # open, closed
                    "merged": pr_data.get("merged", False) if pr_data.get("merged") is not None else False,
                    "mergeable": pr_data.get("mergeable"),
                    "mergeable_state": pr_data.get("mergeable_state", "unknown"),
                    "url": pr_data.get("html_url", ""),
                    "branch": pr_data.get("head", {}).get("ref", "unknown") if pr_data.get("head") else "unknown",
                    "created_at": pr_data.get("created_at", ""),
                    "updated_at": pr_data.get("updated_at", ""),
                    "user": pr_data.get("user", {}).get("login", "unknown") if pr_data.get("user") else "unknown",
                    "comments": pr_data.get("comments", 0),
                    "review_comments": pr_data.get("review_comments", 0),
                    "commits": pr_data.get("commits", 0),
                    "additions": pr_data.get("additions", 0),
                    "deletions": pr_data.get("deletions", 0),
                    "changed_files": pr_data.get("changed_files", 0)
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get PR status: {response.status_code} - {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting PR status: {str(e)}"
            }
    
    def get_pr_comments(self, pr_number: int) -> Dict:
        """Get comments for a pull request"""
        try:
            # Get issue comments (general PR comments)
            comments_url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/issues/{pr_number}/comments"
            comments_response = requests.get(comments_url, headers=self.headers)
            
            # Get review comments (code-specific comments)
            review_comments_url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}/comments"
            review_comments_response = requests.get(review_comments_url, headers=self.headers)
            
            comments = []
            review_comments = []
            
            if comments_response.status_code == 200:
                comments_data = comments_response.json()
                comments = [{
                    "id": comment["id"],
                    "user": comment["user"]["login"],
                    "body": comment["body"],
                    "created_at": comment["created_at"],
                    "updated_at": comment["updated_at"],
                    "type": "general"
                } for comment in comments_data]
            
            if review_comments_response.status_code == 200:
                review_comments_data = review_comments_response.json()
                review_comments = [{
                    "id": comment["id"],
                    "user": comment["user"]["login"],
                    "body": comment["body"],
                    "path": comment["path"],
                    "line": comment.get("line"),
                    "created_at": comment["created_at"],
                    "updated_at": comment["updated_at"],
                    "type": "review"
                } for comment in review_comments_data]
            
            return {
                "success": True,
                "comments": comments,
                "review_comments": review_comments,
                "total_comments": len(comments) + len(review_comments)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting PR comments: {str(e)}",
                "comments": [],
                "review_comments": [],
                "total_comments": 0
            }
    
    def get_branch_status(self, branch_name: str) -> Dict:
        """Get status of a branch"""
        try:
            url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/branches/{branch_name}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                branch_data = response.json()
                return {
                    "success": True,
                    "name": branch_data["name"],
                    "protected": branch_data["protected"],
                    "commit_sha": branch_data["commit"]["sha"],
                    "commit_url": branch_data["commit"]["url"],
                    "exists": True
                }
            elif response.status_code == 404:
                return {
                    "success": True,
                    "name": branch_name,
                    "exists": False,
                    "error": "Branch not found"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get branch status: {response.status_code} - {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting branch status: {str(e)}"
            }
    
    def get_recent_prs(self, limit: int = 10) -> Dict:
        """Get recent PRs for the repository"""
        try:
            url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/pulls"
            params = {
                "state": "all",
                "sort": "updated",
                "direction": "desc",
                "per_page": limit
            }
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                prs_data = response.json()
                prs = []
                for pr in prs_data:
                    try:
                        prs.append({
                            "number": pr.get("number"),
                            "title": pr.get("title", "No title"),
                            "state": pr.get("state", "unknown"),
                            "merged": pr.get("merged", False) if pr.get("merged") is not None else False,
                            "url": pr.get("html_url", ""),
                            "branch": pr.get("head", {}).get("ref", "unknown") if pr.get("head") else "unknown",
                            "created_at": pr.get("created_at", ""),
                            "updated_at": pr.get("updated_at", ""),
                            "user": pr.get("user", {}).get("login", "unknown") if pr.get("user") else "unknown"
                        })
                    except Exception as pr_error:
                        print(f"Error processing PR {pr.get('number', 'unknown')}: {pr_error}")
                        # Skip this PR and continue with others
                        continue
                
                return {
                    "success": True,
                    "prs": prs,
                    "total": len(prs)
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get recent PRs: {response.status_code} - {response.text}",
                    "prs": [],
                    "total": 0
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting recent PRs: {str(e)}",
                "prs": [],
                "total": 0
            }
    
    def test_connection(self) -> Dict:
        """Test GitHub API connection and permissions"""
        if not self.is_configured():
            return {
                "success": False,
                "error": "GitHub integration not configured. Missing GITHUB_TOKEN or repository settings."
            }
        
        try:
            # Test repository access
            url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                repo_data = response.json()
                return {
                    "success": True,
                    "repository": f"{self.repo_owner}/{self.repo_name}",
                    "permissions": repo_data.get("permissions", {}),
                    "default_branch": repo_data.get("default_branch"),
                    "private": repo_data.get("private", False),
                    "description": repo_data.get("description", "No description")
                }
            else:
                return {
                    "success": False,
                    "error": f"Cannot access repository: {response.status_code} - {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection test failed: {str(e)}"
            }