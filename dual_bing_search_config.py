"""
Separate Bing Search Configuration Template
Configure different Bing search resources for data collection vs validation

AZURE AI FOUNDRY BING SEARCH SETUP:
This setup prevents cross-contamination between data collection and validation tasks
"""

# =============================================================================
# 1. DATA COLLECTION BING SEARCH (Azure Documentation Focus)
# =============================================================================
"""
Purpose: Collect Azure service information from official Microsoft documentation
Primary Sites: docs.microsoft.com, learn.microsoft.com, azure.microsoft.com

Azure AI Foundry Configuration:
- Resource Name: "azure-docs-bing-search"
- Search Instance: "azure-service-data-collection"
- Site Restrictions: docs.microsoft.com, learn.microsoft.com
- Custom Config: Boost Azure service documentation pages
"""

DATA_COLLECTION_BING_SETTINGS = {
    "connection_name": "azure-docs-bing-search",
    "instance_name": "azure-service-data-collection",
    "search_filters": [
        "site:docs.microsoft.com",
        "site:learn.microsoft.com", 
        "site:azure.microsoft.com"
    ],
    "boost_keywords": [
        "Azure security",
        "Azure configuration",
        "Azure best practices",
        "Azure compliance",
        "Azure networking"
    ],
    "exclude_keywords": [
        "NIST",
        "CSF",
        "compliance framework",
        "regulatory mapping"
    ]
}

# =============================================================================
# 2. VALIDATION BING SEARCH (NIST CSF Focus)
# =============================================================================
"""
Purpose: Validate NIST CSF mappings against official NIST documentation
Primary Sites: nist.gov, csrc.nist.gov

Azure AI Foundry Configuration:
- Resource Name: "nist-validation-bing-search" 
- Search Instance: "nist-csf-validation"
- Site Restrictions: nist.gov, csrc.nist.gov
- Custom Config: Boost NIST Cybersecurity Framework pages
"""

VALIDATION_BING_SETTINGS = {
    "connection_name": "nist-validation-bing-search",
    "instance_name": "nist-csf-validation",
    "search_filters": [
        "site:nist.gov",
        "site:csrc.nist.gov"
    ],
    "boost_keywords": [
        "NIST Cybersecurity Framework",
        "NIST CSF",
        "PR.AC",
        "PR.DS", 
        "DE.CM",
        "RS.RP",
        "RC.RP"
    ],
    "exclude_keywords": [
        "Azure",
        "Microsoft",
        "implementation guide",
        "vendor specific"
    ]
}

# =============================================================================
# ENVIRONMENT VARIABLES TO SET
# =============================================================================
"""
Add these to your .env file or Azure Function App Configuration:

# Data Collection Bing Search
DATA_COLLECTION_BING_CONNECTION_NAME=azure-docs-bing-search
DATA_COLLECTION_BING_INSTANCE_NAME=azure-service-data-collection

# Validation Bing Search  
VALIDATION_BING_CONNECTION_NAME=nist-validation-bing-search
VALIDATION_BING_INSTANCE_NAME=nist-csf-validation
"""

# =============================================================================
# AZURE AI FOUNDRY SETUP STEPS
# =============================================================================
"""
1. CREATE DATA COLLECTION BING RESOURCE:
   - Go to Azure AI Foundry portal
   - Create new Bing Custom Search resource
   - Name: "azure-docs-bing-search"
   - Configure custom search instance: "azure-service-data-collection"
   - Add site restrictions: docs.microsoft.com, learn.microsoft.com
   - Set boost keywords for Azure documentation

2. CREATE VALIDATION BING RESOURCE:
   - Create second Bing Custom Search resource  
   - Name: "nist-validation-bing-search"
   - Configure custom search instance: "nist-csf-validation"
   - Add site restrictions: nist.gov, csrc.nist.gov
   - Set boost keywords for NIST CSF content

3. CONNECT TO AI FOUNDRY PROJECT:
   - Add both Bing resources as connections in your AI Foundry project
   - Update environment variables with connection names
   - Test both search configurations independently
"""

# =============================================================================
# BENEFITS OF SEPARATION
# =============================================================================
"""
[IMPROVEMENT] ACCURACY IMPROVEMENT:
- Data collection gets Azure-specific results only
- Validation gets NIST-specific results only  
- No cross-contamination of search results

[IMPROVEMENT] REDUCED HALLUCINATION:
- Each agent sees only relevant information
- Clear separation of concerns
- Better context quality for AI models

[IMPROVEMENT] BETTER SEARCH QUALITY:
- Custom search instances tuned for specific purposes
- Site-specific boosts and filters
- Optimized keyword relevance

[IMPROVEMENT] COMPLIANCE & AUDIT:
- Clear traceability of validation sources
- Separate search logs for different purposes
- Better compliance documentation
"""

def get_search_configuration_summary():
    """Get summary of the dual Bing search setup"""
    return {
        "data_collection": {
            "purpose": "Azure service documentation research",
            "primary_sites": ["docs.microsoft.com", "learn.microsoft.com"],
            "focus": "Security features, configurations, best practices"
        },
        "validation": {
            "purpose": "NIST CSF mapping validation", 
            "primary_sites": ["nist.gov", "csrc.nist.gov"],
            "focus": "Official NIST Cybersecurity Framework documentation"
        },
        "benefits": [
            "Prevents cross-contamination",
            "Improves search accuracy", 
            "Reduces AI hallucination",
            "Better compliance traceability"
        ]
    }

if __name__ == "__main__":
    print("[SEARCH] Dual Bing Search Configuration")
    print("=" * 50)
    
    config = get_search_configuration_summary()
    
    print("[DATA] DATA COLLECTION SEARCH:")
    print(f"   Purpose: {config['data_collection']['purpose']}")
    print(f"   Sites: {', '.join(config['data_collection']['primary_sites'])}")
    print(f"   Focus: {config['data_collection']['focus']}")
    
    print("\n[VALIDATION] VALIDATION SEARCH:")
    print(f"   Purpose: {config['validation']['purpose']}")
    print(f"   Sites: {', '.join(config['validation']['primary_sites'])}")
    print(f"   Focus: {config['validation']['focus']}")
    
    print("\n[BENEFITS] BENEFITS:")
    for benefit in config['benefits']:
        print(f"   - {benefit}")
    
    print("\n[READY] Ready for separate Bing search resource deployment!")