from services.api_call import tavily_client
from typing import Dict, Any

# ==========================================
# DYNAMIC TAVILY BRAND & COMPOUND RESOLVER
# ==========================================
def tavily_resolve_brand(brand_name: str) -> Dict[str, Any]:
    """
    Uses Tavily to look up regional, branded, or compounded medicines 
    and extract their active ingredients/composition.
    """
    query = f"What are the active ingredients, composition, and generic equivalent of '{brand_name}' medicine?"
    
    try:
        search_res = tavily_client.search(
            query=query,
            include_domains=["1mg.com", "netmeds.com", "drugs.com", "ncbi.nlm.nih.gov"],
            search_depth="advanced",
            max_results=2
        )
        
        results = search_res.get("results", [])
        if results:
            # Aggregate content to gather composition clues
            combined_content = " ".join([r.get("content", "") for r in results])
            return {
                "brand_name": brand_name,
                "composition_summary": combined_content,
                "source_url": results[0].get("url")
            }
    except Exception:
        pass
        
    return None