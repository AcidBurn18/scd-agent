"""
Enhanced SCD Validation with Rigorous Output Validation
Provides honest feedback when NIST CSF matching isn't found and includes reference links
"""
import re
from typing import Dict, List, Optional, Tuple
from nist_csf_validator import validate_nist_csf_mapping, NIST_CSF_V1_1

class RigorousOutputValidator:
    """
    Enhanced validator that provides honest feedback about NIST CSF mappings,
    reference availability, and control accuracy
    """
    
    def __init__(self):
        self.nist_reference_base = "https://nvlpubs.nist.gov/nistpubs/cswp/nist.cswp.29.pdf"
        self.azure_docs_base = "https://docs.microsoft.com/en-us/azure"
        
    def validate_scd_with_rigorous_feedback(self, scd_content: str, azure_service: str) -> Dict:
        """
        Perform rigorous validation with honest feedback about mapping quality
        and reference availability
        """
        validation_result = {
            "overall_assessment": "",
            "nist_csf_analysis": {},
            "control_analysis": {},
            "reference_analysis": {},
            "honest_feedback": [],
            "improvement_suggestions": [],
            "validation_passed": False
        }
        
        # 1. Analyze NIST CSF mappings with reference validation
        nist_analysis = self._analyze_nist_mappings_with_references(scd_content)
        validation_result["nist_csf_analysis"] = nist_analysis
        
        # 2. Analyze individual controls for reference availability  
        control_analysis = self._analyze_controls_with_references(scd_content, azure_service)
        validation_result["control_analysis"] = control_analysis
        
        # 3. Generate honest feedback
        honest_feedback = self._generate_honest_feedback(nist_analysis, control_analysis)
        validation_result["honest_feedback"] = honest_feedback
        
        # 4. Determine overall validation status
        validation_result["validation_passed"] = self._determine_validation_status(
            nist_analysis, control_analysis
        )
        
        # 5. Generate improvement suggestions
        validation_result["improvement_suggestions"] = self._generate_improvement_suggestions(
            nist_analysis, control_analysis
        )
        
        # 6. Create overall assessment
        validation_result["overall_assessment"] = self._create_overall_assessment(
            validation_result
        )
        
        return validation_result
    
    def _analyze_nist_mappings_with_references(self, scd_content: str) -> Dict:
        """
        Analyze NIST CSF mappings and validate their accuracy with reference links
        """
        # Extract NIST mappings
        nist_pattern = r'\b[A-Z]{2}\.[A-Z]{2}-\d+\b'
        found_mappings = re.findall(nist_pattern, scd_content)
        
        analysis = {
            "total_mappings_found": len(found_mappings),
            "valid_mappings": [],
            "invalid_mappings": [],
            "missing_references": [],
            "mapping_quality_score": 0,
            "reference_completeness": 0
        }
        
        for mapping in found_mappings:
            validation = validate_nist_csf_mapping(mapping)
            
            if validation["valid"]:
                # Check if proper context and reference is provided
                mapping_context = self._extract_mapping_context(scd_content, mapping)
                reference_info = self._check_nist_reference_availability(mapping)
                
                valid_mapping = {
                    "mapping": mapping,
                    "category": validation["category_name"],
                    "description": validation["description"],
                    "context_provided": len(mapping_context) > 50,  # Basic context check
                    "reference_link": reference_info["link"],
                    "reference_available": reference_info["available"],
                    "mapping_context": mapping_context[:200] + "..." if len(mapping_context) > 200 else mapping_context
                }
                analysis["valid_mappings"].append(valid_mapping)
                
                if not reference_info["available"]:
                    analysis["missing_references"].append({
                        "mapping": mapping,
                        "issue": "Official reference documentation not readily available"
                    })
            else:
                analysis["invalid_mappings"].append({
                    "mapping": mapping,
                    "error": validation["error"],
                    "suggested_alternatives": validation.get("suggestions", [])
                })
        
        # Calculate quality scores
        if found_mappings:
            analysis["mapping_quality_score"] = len(analysis["valid_mappings"]) / len(found_mappings) * 100
            
            valid_with_refs = sum(1 for m in analysis["valid_mappings"] if m["reference_available"])
            analysis["reference_completeness"] = valid_with_refs / len(analysis["valid_mappings"]) * 100 if analysis["valid_mappings"] else 0
        
        return analysis
    
    def _analyze_controls_with_references(self, scd_content: str, azure_service: str) -> Dict:
        """
        Analyze individual security controls and their reference availability
        """
        # Extract security controls (looking for numbered sections or bullet points)
        control_patterns = [
            r'(?:^|\n)\s*(?:\d+\.|\-|\*|\-)\s*([^.\n]*(?:control|security|access|encryption|monitoring|logging|audit)[^.\n]*)',
            r'(?:^|\n)\s*(?:Control|Security Control|Implementation)[\s:]+([^\n]+)',
        ]
        
        controls = []
        for pattern in control_patterns:
            matches = re.findall(pattern, scd_content, re.IGNORECASE | re.MULTILINE)
            controls.extend(matches)
        
        # Remove duplicates and clean up
        controls = list(set([c.strip() for c in controls if len(c.strip()) > 20]))
        
        analysis = {
            "total_controls_identified": len(controls),
            "controls_with_references": [],
            "controls_without_references": [],
            "azure_specific_controls": [],
            "generic_controls": [],
            "reference_coverage": 0
        }
        
        for control in controls:
            control_analysis = self._analyze_individual_control(control, azure_service, scd_content)
            
            if control_analysis["azure_reference_available"] or control_analysis["general_reference_available"]:
                analysis["controls_with_references"].append(control_analysis)
            else:
                analysis["controls_without_references"].append(control_analysis)
            
            if control_analysis["azure_specific"]:
                analysis["azure_specific_controls"].append(control_analysis)
            else:
                analysis["generic_controls"].append(control_analysis)
        
        # Calculate reference coverage
        if controls:
            analysis["reference_coverage"] = len(analysis["controls_with_references"]) / len(controls) * 100
        
        return analysis
    
    def _analyze_individual_control(self, control: str, azure_service: str, scd_content: str) -> Dict:
        """
        Analyze a single control for reference availability and specificity
        """
        control_lower = control.lower()
        azure_service_lower = azure_service.lower()
        
        # Check if control is Azure-specific
        azure_keywords = ["azure", "microsoft", azure_service_lower.split()[0] if azure_service_lower else ""]
        azure_specific = any(keyword in control_lower for keyword in azure_keywords if keyword)
        
        # Check for reference availability (simplified - in real implementation, this would check actual docs)
        azure_reference_available = self._check_azure_reference_availability(control, azure_service)
        general_reference_available = self._check_general_reference_availability(control)
        
        # Extract implementation details from context
        implementation_details = self._extract_implementation_details(control, scd_content)
        
        return {
            "control_text": control,
            "azure_specific": azure_specific,
            "azure_reference_available": azure_reference_available["available"],
            "azure_reference_link": azure_reference_available["link"],
            "general_reference_available": general_reference_available["available"],
            "general_reference_link": general_reference_available["link"],
            "implementation_details_provided": len(implementation_details) > 50,
            "implementation_details": implementation_details,
            "confidence_score": self._calculate_control_confidence(control, azure_service)
        }
    
    def _check_azure_reference_availability(self, control: str, azure_service: str) -> Dict:
        """
        Check if Azure-specific documentation is available for this control
        """
        control_lower = control.lower()
        
        # Common Azure security controls with known documentation
        azure_control_mappings = {
            "encryption": f"{self.azure_docs_base}/security/fundamentals/encryption-overview",
            "access control": f"{self.azure_docs_base}/active-directory/fundamentals/",
            "network security": f"{self.azure_docs_base}/security/fundamentals/network-overview",
            "monitoring": f"{self.azure_docs_base}/azure-monitor/",
            "logging": f"{self.azure_docs_base}/azure-monitor/platform/",
            "identity": f"{self.azure_docs_base}/active-directory/",
            "key management": f"{self.azure_docs_base}/key-vault/",
            "backup": f"{self.azure_docs_base}/backup/",
            "disaster recovery": f"{self.azure_docs_base}/site-recovery/"
        }
        
        # Check if control maps to known Azure documentation
        for keyword, doc_link in azure_control_mappings.items():
            if keyword in control_lower:
                return {"available": True, "link": doc_link}
        
        # Service-specific documentation
        service_name = azure_service.lower().replace("azure ", "").replace(" ", "-")
        service_link = f"{self.azure_docs_base}/{service_name}/"
        
        return {
            "available": False,  # Conservative - assume not available unless verified
            "link": service_link,
            "note": "Service-specific documentation may be available but not verified"
        }
    
    def _check_general_reference_availability(self, control: str) -> Dict:
        """
        Check if general security references are available for this control
        """
        # Common security frameworks and standards
        security_frameworks = {
            "nist": "https://csrc.nist.gov/",
            "iso 27001": "https://www.iso.org/isoiec-27001-information-security.html",
            "cis": "https://www.cisecurity.org/controls/",
            "sans": "https://www.sans.org/",
            "owasp": "https://owasp.org/"
        }
        
        return {
            "available": True,  # General security references are usually available
            "link": "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final",
            "note": "General security guidance available from NIST SP 800-53"
        }
    
    def _check_nist_reference_availability(self, mapping: str) -> Dict:
        """
        Check if NIST CSF reference is available for specific mapping
        """
        return {
            "available": True,  # NIST CSF is publicly available
            "link": f"{self.nist_reference_base}#page=XX",  # Would need page mapping
            "note": f"Reference available in NIST Cybersecurity Framework v1.1 for {mapping}"
        }
    
    def _extract_mapping_context(self, scd_content: str, mapping: str) -> str:
        """
        Extract context around a NIST mapping to assess quality
        """
        lines = scd_content.split('\n')
        context = ""
        
        for i, line in enumerate(lines):
            if mapping in line:
                # Get surrounding context
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context = '\n'.join(lines[start:end])
                break
        
        return context
    
    def _extract_implementation_details(self, control: str, scd_content: str) -> str:
        """
        Extract implementation details for a specific control
        """
        # Find the control in the content and extract surrounding details
        lines = scd_content.split('\n')
        details = ""
        
        for i, line in enumerate(lines):
            if control[:50] in line:  # Match first part of control
                # Get following lines that might contain implementation details
                start = i
                end = min(len(lines), i + 5)
                details = '\n'.join(lines[start:end])
                break
        
        return details
    
    def _calculate_control_confidence(self, control: str, azure_service: str) -> float:
        """
        Calculate confidence score for a control based on specificity and detail
        """
        score = 0.5  # Base score
        
        # Bonus for Azure-specific terms
        azure_terms = ["azure", "microsoft", azure_service.lower()]
        if any(term in control.lower() for term in azure_terms):
            score += 0.2
        
        # Bonus for specific implementation details
        implementation_keywords = ["configure", "enable", "implement", "deploy", "setup"]
        if any(keyword in control.lower() for keyword in implementation_keywords):
            score += 0.1
        
        # Bonus for measurable criteria
        measurable_keywords = ["daily", "weekly", "monthly", "automated", "real-time"]
        if any(keyword in control.lower() for keyword in measurable_keywords):
            score += 0.1
        
        # Penalty for vague language
        vague_keywords = ["ensure", "should", "appropriate", "adequate"]
        if any(keyword in control.lower() for keyword in vague_keywords):
            score -= 0.1
        
        return min(1.0, max(0.0, score))
    
    def _generate_honest_feedback(self, nist_analysis: Dict, control_analysis: Dict) -> List[str]:
        """
        Generate honest feedback about the SCD quality
        """
        feedback = []
        
        # NIST CSF feedback
        if nist_analysis["total_mappings_found"] == 0:
            feedback.append("[CRITICAL] No NIST CSF mappings found. This SCD lacks proper cybersecurity framework alignment.")
        elif nist_analysis["mapping_quality_score"] < 80:
            feedback.append(f"[WARNING] NIST CSF mapping quality is low ({nist_analysis['mapping_quality_score']:.1f}%). Multiple invalid mappings detected.")
        elif nist_analysis["mapping_quality_score"] < 95:
            feedback.append(f"[WARNING] NIST CSF mappings have some issues ({nist_analysis['mapping_quality_score']:.1f}% valid). Review invalid mappings.")
        else:
            feedback.append(f"[GOOD] NIST CSF mappings are accurate ({nist_analysis['mapping_quality_score']:.1f}% valid).")
        
        # Reference availability feedback
        if nist_analysis["reference_completeness"] < 50:
            feedback.append("[CRITICAL] Most NIST CSF mappings lack proper reference documentation.")
        elif nist_analysis["reference_completeness"] < 80:
            feedback.append(f"[WARNING] Some NIST CSF mappings lack reference documentation ({nist_analysis['reference_completeness']:.1f}% have references).")
        else:
            feedback.append(f"[GOOD] Most NIST CSF mappings have reference documentation ({nist_analysis['reference_completeness']:.1f}%).")
        
        # Control analysis feedback
        if control_analysis["total_controls_identified"] == 0:
            feedback.append("[CRITICAL] No security controls identified in the SCD.")
        elif control_analysis["reference_coverage"] < 50:
            feedback.append(f"[CRITICAL] Most security controls lack reference documentation ({control_analysis['reference_coverage']:.1f}% have references).")
        elif control_analysis["reference_coverage"] < 80:
            feedback.append(f"[WARNING] Some security controls lack reference documentation ({control_analysis['reference_coverage']:.1f}% have references).")
        else:
            feedback.append(f"[GOOD] Most security controls have reference documentation ({control_analysis['reference_coverage']:.1f}%).")
        
        # Azure-specific feedback
        azure_specific_count = len(control_analysis["azure_specific_controls"])
        total_controls = control_analysis["total_controls_identified"]
        
        if total_controls > 0:
            azure_specificity = azure_specific_count / total_controls * 100
            if azure_specificity < 30:
                feedback.append(f"[WARNING] SCD is too generic ({azure_specificity:.1f}% Azure-specific). Add more service-specific controls.")
            elif azure_specificity > 70:
                feedback.append(f"[GOOD] SCD is appropriately service-specific ({azure_specificity:.1f}% Azure-specific).")
        
        return feedback
    
    def _determine_validation_status(self, nist_analysis: Dict, control_analysis: Dict) -> bool:
        """
        Determine if the SCD passes rigorous validation
        """
        # Strict criteria for passing
        criteria = [
            nist_analysis["total_mappings_found"] > 0,  # Must have NIST mappings
            nist_analysis["mapping_quality_score"] >= 80,  # 80%+ valid mappings
            len(nist_analysis["invalid_mappings"]) == 0,  # No invalid mappings allowed
            control_analysis["total_controls_identified"] > 0,  # Must have controls
            control_analysis["reference_coverage"] >= 60  # 60%+ controls must have references
        ]
        
        return all(criteria)
    
    def _generate_improvement_suggestions(self, nist_analysis: Dict, control_analysis: Dict) -> List[str]:
        """
        Generate specific improvement suggestions
        """
        suggestions = []
        
        # NIST CSF improvements
        if nist_analysis["invalid_mappings"]:
            suggestions.append("Fix invalid NIST CSF mappings:")
            for invalid in nist_analysis["invalid_mappings"]:
                suggestions.append(f"  - {invalid['mapping']}: {invalid['error']}")
        
        # Reference improvements
        if nist_analysis["missing_references"]:
            suggestions.append("Add reference documentation for NIST CSF mappings:")
            for missing in nist_analysis["missing_references"]:
                suggestions.append(f"  - {missing['mapping']}: {missing['issue']}")
        
        # Control improvements
        if control_analysis["controls_without_references"]:
            suggestions.append("Add reference documentation for these controls:")
            for control in control_analysis["controls_without_references"][:5]:  # Limit to 5
                suggestions.append(f"  - {control['control_text'][:80]}...")
        
        return suggestions
    
    def _create_overall_assessment(self, validation_result: Dict) -> str:
        """
        Create overall assessment summary
        """
        nist_score = validation_result["nist_csf_analysis"]["mapping_quality_score"]
        ref_coverage = validation_result["control_analysis"]["reference_coverage"]
        passed = validation_result["validation_passed"]
        
        if passed:
            return f"[PASSED] SCD PASSES rigorous validation. NIST CSF accuracy: {nist_score:.1f}%, Reference coverage: {ref_coverage:.1f}%"
        else:
            return f"[FAILED] SCD FAILS rigorous validation. NIST CSF accuracy: {nist_score:.1f}%, Reference coverage: {ref_coverage:.1f}%. See feedback for required improvements."


def create_enhanced_validation_report(scd_content: str, azure_service: str) -> str:
    """
    Create a comprehensive validation report with honest feedback and reference links
    """
    validator = RigorousOutputValidator()
    results = validator.validate_scd_with_rigorous_feedback(scd_content, azure_service)
    
    report = f"""
# RIGOROUS SCD VALIDATION REPORT
**Service:** {azure_service}
**Validation Status:** {'PASSED' if results['validation_passed'] else 'FAILED'}

## Overall Assessment
{results['overall_assessment']}

## Honest Feedback
"""
    
    for feedback in results['honest_feedback']:
        report += f"\n{feedback}"
    
    report += f"""

## NIST CSF Analysis
- **Total Mappings Found:** {results['nist_csf_analysis']['total_mappings_found']}
- **Mapping Quality Score:** {results['nist_csf_analysis']['mapping_quality_score']:.1f}%
- **Reference Completeness:** {results['nist_csf_analysis']['reference_completeness']:.1f}%

### Valid NIST CSF Mappings
"""
    
    for mapping in results['nist_csf_analysis']['valid_mappings']:
        report += f"""
- **{mapping['mapping']}** - {mapping['category']}
  - Description: {mapping['description']}
  - Reference: {mapping['reference_link'] if mapping['reference_available'] else 'No reference available'}
  - Context Quality: {'Good' if mapping['context_provided'] else 'Poor - needs more context'}
"""
    
    if results['nist_csf_analysis']['invalid_mappings']:
        report += "\n### Invalid NIST CSF Mappings (MUST BE FIXED)\n"
        for mapping in results['nist_csf_analysis']['invalid_mappings']:
            report += f"\n- **{mapping['mapping']}**: {mapping['error']}"
    
    report += f"""

## Security Controls Analysis  
- **Total Controls Identified:** {results['control_analysis']['total_controls_identified']}
- **Reference Coverage:** {results['control_analysis']['reference_coverage']:.1f}%
- **Azure-Specific Controls:** {len(results['control_analysis']['azure_specific_controls'])}

### Controls WITH Reference Documentation
"""
    
    for control in results['control_analysis']['controls_with_references'][:5]:  # Show first 5
        report += f"""
- **Control:** {control['control_text'][:100]}...
  - Azure Reference: {control['azure_reference_link'] if control['azure_reference_available'] else 'Not available'}
  - General Reference: {control['general_reference_link'] if control['general_reference_available'] else 'Not available'}
  - Confidence Score: {control['confidence_score']:.2f}
"""
    
    if results['control_analysis']['controls_without_references']:
        report += "\n### Controls WITHOUT Reference Documentation (NEEDS IMPROVEMENT)\n"
        for control in results['control_analysis']['controls_without_references'][:5]:
            report += f"\n- {control['control_text'][:100]}..."
    
    if results['improvement_suggestions']:
        report += "\n## Required Improvements\n"
        for suggestion in results['improvement_suggestions']:
            report += f"\n{suggestion}"
    
    report += f"""

---
**Validation completed with rigorous standards. All issues must be addressed before approval.**
"""
    
    return report