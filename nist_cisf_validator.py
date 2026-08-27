"""
NIST CSF 2.0 Subcategory Validator - ANTI-HALLUCINATION
Prevents AI hallucination of non-existent NIST subcategories
Contains ONLY official NIST CSF v2.0 subcategories with format GV.OC-01, ID.AM-01, etc.
Primary Source: Official NIST Cybersecurity Framework 2.0
Reference: GV.OC, GV.RM, GV.RR, GV.PO, GV.OV, GV.SC | ID.AM, ID.RA, ID.IM | PR.AA, PR.AT, PR.DS, PR.PS, PR.IR
          DE.CM, DE.AE | RS.MA, RS.AN, RS.CO, RS.MI | RC.RP, RC.CO
"""

class NISTCSFValidator:
    """Validates NIST CSF 2.0 subcategories - STRICT anti-hallucination enforcement"""
    
    def __init__(self):
        # ============================================================================
        # Official NIST CSF 2.0 Subcategories ONLY (from official framework table)
        # Format: Function.Category-Subcategory (e.g., GV.OC-01, PR.AA-01, etc.)
        # ============================================================================
        self.VALID_NIST_SUBCATEGORIES = {
            # ============================================================================
            # GOVERN (GV) Function - NIST CSF 2.0 (30 subcategories total)
            # ============================================================================
            # Organizational Context (OC) - 5 subcategories
            "GV.OC-01", "GV.OC-02", "GV.OC-03", "GV.OC-04", "GV.OC-05",
            
            # Risk Management Strategy (RM) - 7 subcategories
            "GV.RM-01", "GV.RM-02", "GV.RM-03", "GV.RM-04", "GV.RM-05", "GV.RM-06", "GV.RM-07",
            
            # Roles, Responsibilities, and Authorities (RR) - 4 subcategories
            "GV.RR-01", "GV.RR-02", "GV.RR-03", "GV.RR-04",
            
            # Policy (PO) - 2 subcategories
            "GV.PO-01", "GV.PO-02",
            
            # Oversight (OV) - 3 subcategories
            "GV.OV-01", "GV.OV-02", "GV.OV-03",
            
            # Cybersecurity Supply Chain Risk Management (SC) - 10 subcategories (FIXED!)
            "GV.SC-01", "GV.SC-02", "GV.SC-03", "GV.SC-04", "GV.SC-05", 
            "GV.SC-06", "GV.SC-07", "GV.SC-08", "GV.SC-09", "GV.SC-10",
            
            # ============================================================================
            # IDENTIFY (ID) Function - NIST CSF 2.0 (21 subcategories total)
            # ============================================================================
            # Asset Management (AM) - 7 subcategories (AM-06 doesn't exist, AM-07 and AM-08 do)
            "ID.AM-01", "ID.AM-02", "ID.AM-03", "ID.AM-04", "ID.AM-05", "ID.AM-07", "ID.AM-08",
            
            # Risk Assessment (RA) - 10 subcategories (FIXED!)
            "ID.RA-01", "ID.RA-02", "ID.RA-03", "ID.RA-04", "ID.RA-05", 
            "ID.RA-06", "ID.RA-07", "ID.RA-08", "ID.RA-09", "ID.RA-10",
            
            # Improvement (IM) - 4 subcategories
            "ID.IM-01", "ID.IM-02", "ID.IM-03", "ID.IM-04",
            
            # ============================================================================
            # PROTECT (PR) Function - NIST CSF 2.0 (25 subcategories total)
            # ============================================================================
            # Identity Management, Authentication, and Access Control (AA) - 6 subcategories (FIXED!)
            "PR.AA-01", "PR.AA-02", "PR.AA-03", "PR.AA-04", "PR.AA-05", "PR.AA-06",
            
            # Awareness and Training (AT) - 2 subcategories (FIXED!)
            "PR.AT-01", "PR.AT-02",
            
            # Data Security (DS) - 4 subcategories (DS-03 to DS-09 don't exist, DS-10, DS-11 do)
            "PR.DS-01", "PR.DS-02", "PR.DS-10", "PR.DS-11",
            
            # Platform Security (PS) - 6 subcategories
            "PR.PS-01", "PR.PS-02", "PR.PS-03", "PR.PS-04", "PR.PS-05", "PR.PS-06",
            
            # Technology Infrastructure Resilience (IR) - 4 subcategories (FIXED!)
            "PR.IR-01", "PR.IR-02", "PR.IR-03", "PR.IR-04",
            
            # ============================================================================
            # DETECT (DE) Function - NIST CSF 2.0 (11 subcategories total)
            # ============================================================================
            # Continuous Monitoring (CM) - 5 subcategories (CM-04, CM-05, CM-07, CM-08 don't exist)
            "DE.CM-01", "DE.CM-02", "DE.CM-03", "DE.CM-06", "DE.CM-09",
            
            # Adverse Event Analysis (AE) - 6 subcategories (AE-01, AE-05 don't exist)
            "DE.AE-02", "DE.AE-03", "DE.AE-04", "DE.AE-06", "DE.AE-07", "DE.AE-08",
            
            # ============================================================================
            # RESPOND (RS) Function - NIST CSF 2.0 (13 subcategories total)
            # ============================================================================
            # Incident Management (MA) - 5 subcategories (FIXED!)
            "RS.MA-01", "RS.MA-02", "RS.MA-03", "RS.MA-04", "RS.MA-05",
            
            # Incident Analysis (AN) - 4 subcategories (AN-01, AN-02, AN-04, AN-05 don't exist)
            "RS.AN-03", "RS.AN-06", "RS.AN-07", "RS.AN-08",
            
            # Incident Response Reporting and Communication (CO) - 2 subcategories (CO-01 doesn't exist)
            "RS.CO-02", "RS.CO-03",
            
            # Incident Mitigation (MI) - 2 subcategories
            "RS.MI-01", "RS.MI-02",
            
            # ============================================================================
            # RECOVER (RC) Function - NIST CSF 2.0 (6 subcategories total)
            # ============================================================================
            # Incident Recovery Plan Execution (RP) - 6 subcategories (FIXED!)
            "RC.RP-01", "RC.RP-02", "RC.RP-03", "RC.RP-04", "RC.RP-05", "RC.RP-06",
            
            # Incident Recovery Communication (CO) - 2 subcategories (CO-01, CO-02 don't exist)
            "RC.CO-03", "RC.CO-04",
        }
        
        # ============================================================================
        # ANTI-HALLUCINATION: Concrete list of INVALID patterns AI commonly generates
        # ============================================================================
        self.KNOWN_INVALID_PATTERNS = {
            # ===============================================================================
            # OLD v1.1 FORMAT (single digits) - DEPRECATED - Use 2-digit format
            # ===============================================================================
            "ID.AM-1", "ID.AM-2", "ID.AM-3", "ID.AM-4", "ID.AM-5", "ID.AM-6", "ID.AM-7", "ID.AM-8",
            "ID.RA-1", "ID.RA-2", "ID.RA-3", "ID.RA-4", "ID.RA-5", "ID.RA-6", "ID.RA-7", "ID.RA-8", "ID.RA-9",
            "PR.AA-1", "PR.AA-2", "PR.AA-3", "PR.AA-4", "PR.AA-5", "PR.AA-6",
            "PR.AT-1", "PR.AT-2",
            "PR.DS-1", "PR.DS-2", "PR.DS-3", "PR.DS-4",
            "PR.PS-1", "PR.PS-2", "PR.PS-3", "PR.PS-4", "PR.PS-5", "PR.PS-6",
            "PR.IR-1", "PR.IR-2", "PR.IR-3", "PR.IR-4",
            "DE.CM-1", "DE.CM-2", "DE.CM-3", "DE.CM-6", "DE.CM-9",
            "DE.AE-1", "DE.AE-2", "DE.AE-3", "DE.AE-4", "DE.AE-6", "DE.AE-7", "DE.AE-8",
            "RS.MA-1", "RS.MA-2", "RS.MA-3", "RS.MA-4", "RS.MA-5",
            "RS.AN-1", "RS.AN-2", "RS.AN-3", "RS.AN-6", "RS.AN-7", "RS.AN-8",
            "RS.CO-1", "RS.CO-2", "RS.CO-3",
            "RS.MI-1", "RS.MI-2",
            "RC.RP-1", "RC.RP-2", "RC.RP-3", "RC.RP-4", "RC.RP-5", "RC.RP-6",
            "RC.CO-1", "RC.CO-2", "RC.CO-3", "RC.CO-4",
            
            # ===============================================================================
            # INVALID SUBCATEGORIES - These IDs don't exist in official NIST CSF 2.0
            # ===============================================================================
            # GV subcategories that don't exist
            "GV.OC-06", "GV.OC-07", "GV.OC-08", "GV.OC-09", "GV.OC-10",  # Only goes to GV.OC-05
            "GV.RM-08", "GV.RM-09", "GV.RM-10",  # Only goes to GV.RM-07
            "GV.RR-05", "GV.RR-06", "GV.RR-07",  # Only goes to GV.RR-04
            "GV.PO-03", "GV.PO-04", "GV.PO-05",  # Only goes to GV.PO-02
            "GV.OV-04", "GV.OV-05", "GV.OV-06",  # Only goes to GV.OV-03
            "GV.SC-11", "GV.SC-12",  # Only goes to GV.SC-10
            
            # ID subcategories that don't exist
            "ID.AM-06", "ID.AM-09", "ID.AM-10",  # AM-06 doesn't exist, skips to AM-07, AM-08
            "ID.RA-11", "ID.RA-12",  # Only goes to ID.RA-10
            "ID.IM-05", "ID.IM-06",  # Only goes to ID.IM-04
            
            # PR subcategories that don't exist  
            "PR.AA-07", "PR.AA-08",  # Only goes to PR.AA-06
            "PR.AT-03", "PR.AT-04", "PR.AT-05",  # Only goes to PR.AT-02
            "PR.DS-03", "PR.DS-04", "PR.DS-05", "PR.DS-06", "PR.DS-07", "PR.DS-08", "PR.DS-09",  # Skips 03-09
            "PR.PS-07", "PR.PS-08",  # Only goes to PR.PS-06
            "PR.IR-05", "PR.IR-06",  # Only goes to PR.IR-04
            
            # DE subcategories that don't exist
            "DE.CM-04", "DE.CM-05", "DE.CM-07", "DE.CM-08", "DE.CM-10",  # Non-existent CM subcategories
            "DE.AE-01", "DE.AE-05", "DE.AE-09", "DE.AE-10",  # Non-existent AE subcategories
            
            # RS subcategories that don't exist
            "RS.MA-06", "RS.MA-07",  # Only goes to RS.MA-05
            "RS.AN-01", "RS.AN-02", "RS.AN-04", "RS.AN-05", "RS.AN-09",  # Non-existent AN subcategories
            "RS.CO-01", "RS.CO-04", "RS.CO-05",  # Non-existent CO subcategories
            "RS.MI-03", "RS.MI-04",  # Only goes to RS.MI-02
            
            # RC subcategories that don't exist
            "RC.RP-07", "RC.RP-08",  # Only goes to RC.RP-06
            "RC.CO-01", "RC.CO-02", "RC.CO-05",  # Non-existent CO subcategories
            
            # ===============================================================================
            # OLD v1.1 CATEGORIES - REMOVED/RENAMED in v2.0
            # ===============================================================================
            # PR categories that DON'T exist in v2.0
            "PR.AC", "PR.AC-01", "PR.AC-02", "PR.AC-03", "PR.AC-04", "PR.AC-05", "PR.AC-06", "PR.AC-07",  # REMOVED - Use PR.AA instead
            "PR.IP", "PR.IP-01", "PR.IP-02", "PR.IP-03", "PR.IP-04", "PR.IP-05", "PR.IP-06", "PR.IP-07", "PR.IP-08", "PR.IP-09", "PR.IP-10", "PR.IP-11", "PR.IP-12",  # REMOVED
            "PR.MA", "PR.MA-01", "PR.MA-02",  # REMOVED
            "PR.PT", "PR.PT-01", "PR.PT-02", "PR.PT-03", "PR.PT-04", "PR.PT-05",  # REMOVED
            
            # ID categories that DON'T exist in v2.0
            "ID.BE", "ID.BE-01", "ID.BE-02", "ID.BE-03", "ID.BE-04", "ID.BE-05",  # REMOVED
            "ID.GV", "ID.GV-01", "ID.GV-02", "ID.GV-03", "ID.GV-04",  # REMOVED - GV is now separate function
            "ID.RM", "ID.RM-01", "ID.RM-02", "ID.RM-03",  # REMOVED - moved to GV
            "ID.SC", "ID.SC-01", "ID.SC-02", "ID.SC-03", "ID.SC-04", "ID.SC-05",  # REMOVED - moved to GV.SC
            
            # RS categories with WRONG format
            "RS.RP", "RS.RP-01", "RS.RP-02", "RS.RP-03", "RS.RP-04", "RS.RP-05",  # WRONG: RS.RP no longer exists - Use RS.MA, RS.AN, RS.CO, RS.MI
            "RS.IM", "RS.IM-01", "RS.IM-02",  # REMOVED - Use RS.MI for Mitigation
            
            # RC categories that DON'T exist
            "RC.IM", "RC.IM-01", "RC.IM-02",  # REMOVED - Not in v2.0
            
            # ===============================================================================
            # NONSENSE PATTERNS (Common AI Hallucinations)
            # ===============================================================================
            # NONSENSE PATTERNS (Common AI Hallucinations)
            # ===============================================================================
            "PR.PT",  # Missing number
            "PR_PT",  # Underscore format - WRONG
            "PR.XX", "DE.XX", "RS.XX", "RC.XX", "ID.XX", "GV.XX",  # XX is not valid
            "PR.NET", "PR.SEC", "PR.ENCRYPT",  # Not valid NIST categories
            "DE.MON", "DE.DETECT", "DE.ALERT",  # Not valid NIST categories
            "RS.INC", "RS.INCIDENT", "RS.RESPONSE",  # Not valid NIST categories
            "RC.RECOVERY", "RC.RESTORE",  # Not valid NIST categories
        }
        
        # ============================================================================
        # Valid NIST 2.0 Categories (only use these for generation)
        # ============================================================================
        self.VALID_CATEGORIES = {
            "GV": ["OC", "RM", "RR", "PO", "OV", "SC"],  # Govern
            "ID": ["AM", "RA", "IM"],                     # Identify (NO BE, GV, RM, SC anymore)
            "PR": ["AA", "AT", "DS", "PS", "IR"],         # Protect (NO AC, IP, MA, PT anymore)
            "DE": ["CM", "AE"],                           # Detect
            "RS": ["MA", "AN", "CO", "MI"],               # Respond (NO RP, IM anymore)
            "RC": ["RP", "CO"]                            # Recover (NO IM anymore)
        }
    
    def is_valid_nist_subcategory(self, subcategory_id: str) -> bool:
        """
        Check if a NIST 2.0 subcategory ID is valid
        ANTI-HALLUCINATION: Returns False for ANY invalid pattern
        """
        if not subcategory_id:
            return False
            
        # Remove any whitespace and convert to uppercase
        clean_id = subcategory_id.strip().upper()
        
        # CONCRETE CHECK 1: Block known invalid patterns explicitly
        if clean_id in self.KNOWN_INVALID_PATTERNS:
            return False
        
        # CONCRETE CHECK 2: Verify format is exactly Function.Category-Number (e.g., GV.OC-01)
        import re
        if not re.match(r'^[A-Z]{2}\.[A-Z]{2}-\d{2}$', clean_id):
            # Special handling: if it's close but wrong format, still reject
            if re.match(r'^[A-Z]{2}\.[A-Z]{2}$', clean_id):  # Missing number like PR.AC
                return False
            if re.match(r'^[A-Z]{2}\.[A-Z]{2}-\d{1}$', clean_id):  # Single digit like PR.AC-1
                return False
            if re.match(r'^[A-Z]{2}_[A-Z]{2}', clean_id):  # Underscore format like PR_AC
                return False
            return False
            
        # CONCRETE CHECK 3: Verify it's in the official valid list
        return clean_id in self.VALID_NIST_SUBCATEGORIES
    
    def validate_nist_mapping(self, mapping_text: str) -> dict:
        """
        Validate NIST 2.0 mappings in a text string
        Returns concrete feedback about what's wrong and how to fix it
        """
        import re
        
        # Find all potential NIST IDs in the text
        potential_ids = re.findall(r'\b([A-Z]{2}[\._][A-Z]{2}[-._]?\d*)\b', mapping_text)
        
        results = {
            "valid_ids": [],
            "invalid_ids": [],
            "validation_passed": True,
            "suggestions": [],
            "error_details": []
        }
        
        for id_candidate in potential_ids:
            # Normalize format
            normalized_id = id_candidate.replace('_', '.').replace('_', '-')
            # Ensure dot then dash format: XX.XX-NN
            parts = normalized_id.split('.')
            if len(parts) == 2:
                func_cat = parts[0]
                num_part = parts[1].replace('-', '')
                normalized_id = f"{func_cat}.{num_part[0:2]}-{num_part[2:4]}" if len(num_part) >= 2 else None
            
            if self.is_valid_nist_subcategory(normalized_id):
                results["valid_ids"].append(normalized_id)
            else:
                results["invalid_ids"].append(id_candidate)
                results["validation_passed"] = False
                
                # CONCRETE FEEDBACK: Provide specific error reason
                # Try to suggest corrections
                suggestion = self._suggest_correction(id_candidate)
                if suggestion:
                    results["suggestions"].append(f"{id_candidate} -> {suggestion}")
        
        return results
    
    def _suggest_correction(self, invalid_id: str) -> str:
        """
        Suggest corrections for invalid NIST IDs with CONCRETE reasoning
        ANTI-HALLUCINATION: Only suggest from official NIST 2.0 list
        """
        import re
        
        # Extract function and category parts
        match = re.match(r'([A-Z]{2})[\._]([A-Z]{2})', invalid_id)
        if not match:
            return None
            
        function, category = match.groups()
        
        # CONCRETE CHECK: Is this an OLD v1.1 ID format?
        if function in ["ID", "PR"] and category in ["AC", "IP", "MA", "PT", "BE", "GV", "RM", "SC", "DP"]:
            # These were removed in v2.0
            error_msg = f"ERROR: {function}.{category} was REMOVED in NIST CSF 2.0"
            
            # Provide concrete mapping to new categories
            old_to_new_mapping = {
                ("ID", "BE"): "Use ID.AM or ID.RA instead",
                ("ID", "GV"): "Governance moved to GV function - Use GV.OC, GV.RM, GV.RR, GV.PO, GV.OV, or GV.SC",
                ("ID", "RM"): "Use GV.RM instead (moved to Govern function)",
                ("ID", "SC"): "Use GV.SC instead (moved to Govern function)",
                ("PR", "AC"): "Use PR.AA instead (renamed to Identity Management, Authentication, and Access Control)",
                ("PR", "IP"): "Use PR.PS or PR.IR instead (split into Platform Security and Infrastructure Resilience)",
                ("PR", "MA"): "Use PR.PS instead (Maintenance merged into Platform Security)",
                ("PR", "PT"): "Use PR.PS or PR.IR instead (Protective Technology merged)",
                ("RS", "RP"): "Use RS.MA, RS.AN, RS.CO, or RS.MI instead",
                ("RS", "IM"): "Use RS.MI instead",
                ("RC", "IM"): "Removed in v2.0 - Use RC.RP or RC.CO instead",
            }
            
            mapping = old_to_new_mapping.get((function, category), f"Check official NIST 2.0 for {function} function categories")
            return mapping
        
        # CONCRETE CHECK: Is this function valid?
        if function not in self.VALID_CATEGORIES:
            return f"ERROR: Function '{function}' is invalid. Use GV, ID, PR, DE, RS, or RC only"
        
        # CONCRETE CHECK: Is this category valid for the function?
        if category not in self.VALID_CATEGORIES[function]:
            valid_cats = ", ".join(self.VALID_CATEGORIES[function])
            return f"ERROR: {function}.{category} invalid. Valid {function} categories: {valid_cats}"
        
        # If we got here, suggest the first valid subcategory in this category
        candidate = f"{function}.{category}-01"
        if candidate in self.VALID_NIST_SUBCATEGORIES:
            return candidate
        
        return None
    
    def get_valid_subcategories_for_function(self, function: str) -> list:
        """Get all valid subcategories for a NIST function"""
        function = function.upper()
        return [sc for sc in self.VALID_NIST_SUBCATEGORIES if sc.startswith(f"{function}.")]
    
    def get_category_description(self, category_code: str) -> str:
        """Get description for NIST 2.0 category codes"""
        descriptions = {
            # GOVERN Function
            "GV.OC": "Organizational Context",
            "GV.RM": "Risk Management Strategy",
            "GV.RR": "Roles, Responsibilities, and Authorities",
            "GV.PO": "Policy",
            "GV.OV": "Oversight",
            "GV.SC": "Cybersecurity Supply Chain Risk Management",
            
            # IDENTIFY Function
            "ID.AM": "Asset Management",
            "ID.RA": "Risk Assessment",
            "ID.IM": "Improvement",
            
            # PROTECT Function
            "PR.AA": "Identity Management, Authentication, and Access Control",
            "PR.AT": "Awareness and Training",
            "PR.DS": "Data Security",
            "PR.PS": "Platform Security",
            "PR.IR": "Technology Infrastructure Resilience",
            
            # DETECT Function
            "DE.CM": "Continuous Monitoring",
            "DE.AE": "Adverse Event Analysis",
            
            # RESPOND Function
            "RS.MA": "Incident Management",
            "RS.AN": "Incident Analysis",
            "RS.CO": "Incident Response Reporting and Communication",
            "RS.MI": "Incident Mitigation",
            
            # RECOVER Function
            "RC.RP": "Incident Recovery Plan Execution",
            "RC.CO": "Incident Recovery Communication",
        }
        
        return descriptions.get(category_code, "Unknown Category")

# Global validator instance
nist_validator = NISTCSFValidator()

def validate_nist_id(nist_id: str) -> bool:
    """Quick validation function"""
    return nist_validator.is_valid_nist_subcategory(nist_id)

def get_valid_nist_suggestions(security_control_purpose: str) -> list:
    """
    Get valid NIST 2.0 subcategories based on security control purpose
    CONCRETE KEYWORD MATCHING - Only suggests from official v2.0 categories
    """
    purpose_lower = security_control_purpose.lower()
    
    suggestions = []
    
    # ====== NIST CSF 2.0 Keyword-to-Category Mapping ======
    
    # GOVERN (GV) - Organization and Risk Management
    if any(keyword in purpose_lower for keyword in ["governance", "policy", "organizational", "oversight", "roles", "responsibilities", "supply chain"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("GV.")])
    
    # IDENTIFY (ID) - Asset and Risk Identification
    if any(keyword in purpose_lower for keyword in ["asset", "inventory", "risk assessment", "identification", "improvement"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("ID.")])
    
    # PROTECT (PR) - Access Control and Data Protection
    if any(keyword in purpose_lower for keyword in ["access control", "identity", "authentication", "authorization"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("PR.AA")])
    
    if any(keyword in purpose_lower for keyword in ["awareness", "training", "education"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("PR.AT")])
    
    if any(keyword in purpose_lower for keyword in ["data security", "encryption", "data at rest", "data in transit", "storage"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("PR.DS")])
    
    if any(keyword in purpose_lower for keyword in ["platform", "infrastructure", "firewall", "network", "resilience"]):
        # Platform Security (PR.PS) or Infrastructure Resilience (PR.IR)
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("PR.PS")])
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("PR.IR")])
    
    # DETECT (DE) - Monitoring and Anomaly Detection
    if any(keyword in purpose_lower for keyword in ["monitor", "detection", "alert", "continuous monitoring"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("DE.CM")])
    
    if any(keyword in purpose_lower for keyword in ["anomaly", "adverse event", "event analysis"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("DE.AE")])
    
    # RESPOND (RS) - Incident Response
    if any(keyword in purpose_lower for keyword in ["incident management", "incident response"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("RS.MA")])
    
    if any(keyword in purpose_lower for keyword in ["incident analysis", "analysis"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("RS.AN")])
    
    if any(keyword in purpose_lower for keyword in ["communication", "reporting", "notification"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("RS.CO")])
    
    if any(keyword in purpose_lower for keyword in ["mitigation", "containment"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("RS.MI")])
    
    # RECOVER (RC) - Recovery
    if any(keyword in purpose_lower for keyword in ["recovery plan", "recovery", "incident recovery"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("RC.RP")])
    
    if any(keyword in purpose_lower for keyword in ["recovery communication"]):
        suggestions.extend([sc for sc in nist_validator.VALID_NIST_SUBCATEGORIES if sc.startswith("RC.CO")])
    
    # Remove duplicates and return first 5 suggestions
    return list(set(suggestions))[:5]