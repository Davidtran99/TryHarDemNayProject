"""
Entity extraction utilities for extracting fine codes, procedure names, and resolving pronouns.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from hue_portal.core.models import Fine, Procedure, Office


def extract_fine_code(text: str) -> Optional[str]:
    """
    Extract fine code (V001, V002, etc.) from text.
    
    Args:
        text: Input text.
    
    Returns:
        Fine code string or None if not found.
    """
    # Pattern: V followed by 3 digits
    pattern = r'\bV\d{3}\b'
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        return matches[0].upper()
    return None


def extract_procedure_name(text: str) -> Optional[str]:
    """
    Extract procedure name from text by matching against database.
    
    Args:
        text: Input text.
    
    Returns:
        Procedure name or None if not found.
    """
    text_lower = text.lower()
    
    # Get all procedures and check for matches
    procedures = Procedure.objects.all()
    for procedure in procedures:
        procedure_title_lower = procedure.title.lower()
        # Check if procedure title appears in text
        if procedure_title_lower in text_lower or text_lower in procedure_title_lower:
            return procedure.title
    
    return None


def extract_office_name(text: str) -> Optional[str]:
    """
    Extract office/unit name from text by matching against database.
    
    Args:
        text: Input text.
    
    Returns:
        Office name or None if not found.
    """
    text_lower = text.lower()
    
    # Get all offices and check for matches
    offices = Office.objects.all()
    for office in offices:
        office_name_lower = office.unit_name.lower()
        # Check if office name appears in text
        if office_name_lower in text_lower or text_lower in office_name_lower:
            return office.unit_name
    
    return None


def extract_reference_pronouns(text: str, context: Optional[List[Dict[str, Any]]] = None) -> List[str]:
    """
    Extract reference pronouns from text.
    
    Args:
        text: Input text.
        context: Optional context from recent messages.
    
    Returns:
        List of pronouns found.
    """
    # Vietnamese reference pronouns
    pronouns = [
        "cái đó", "cái này", "cái kia",
        "như vậy", "như thế",
        "thủ tục đó", "thủ tục này",
        "mức phạt đó", "mức phạt này",
        "đơn vị đó", "đơn vị này",
        "nó", "đó", "này", "kia"
    ]
    
    text_lower = text.lower()
    found_pronouns = []
    
    for pronoun in pronouns:
        if pronoun in text_lower:
            found_pronouns.append(pronoun)
    
    return found_pronouns


def resolve_pronouns(query: str, recent_messages: List[Dict[str, Any]]) -> str:
    """
    Resolve pronouns in query by replacing them with actual entities from context.
    
    Args:
        query: Current query with pronouns.
        recent_messages: List of recent messages with role, content, intent, entities.
    
    Returns:
        Enhanced query with pronouns resolved.
    """
    if not recent_messages:
        return query
    
    # Check for pronouns
    pronouns = extract_reference_pronouns(query)
    if not pronouns:
        return query
    
    # Look for entities in recent messages (reverse order - most recent first)
    resolved_query = query
    entities_found = {}
    
    for msg in reversed(recent_messages):
        # Check message content for entities
        content = msg.get("content", "")
        
        # Extract fine code
        fine_code = extract_fine_code(content)
        if fine_code and "fine_code" not in entities_found:
            entities_found["fine_code"] = fine_code
        
        # Extract procedure name
        procedure_name = extract_procedure_name(content)
        if procedure_name and "procedure_name" not in entities_found:
            entities_found["procedure_name"] = procedure_name
        
        # Extract office name
        office_name = extract_office_name(content)
        if office_name and "office_name" not in entities_found:
            entities_found["office_name"] = office_name
        
        # Check entities field
        msg_entities = msg.get("entities", {})
        for key, value in msg_entities.items():
            if key not in entities_found:
                entities_found[key] = value
        
        # Check intent to infer entity type
        intent = msg.get("intent", "")
        if intent == "search_fine" and "fine_name" not in entities_found:
            # Try to extract fine name from content
            # Look for patterns like "Vượt đèn đỏ", "Không đội mũ bảo hiểm"
            fine_keywords = ["vượt đèn đỏ", "mũ bảo hiểm", "nồng độ cồn", "tốc độ"]
            for keyword in fine_keywords:
                if keyword in content.lower():
                    entities_found["fine_name"] = keyword
                    break
        
        if intent == "search_procedure" and "procedure_name" not in entities_found:
            # Try to extract procedure name from content
            procedure_keywords = ["đăng ký", "thủ tục", "cư trú", "antt", "pccc"]
            for keyword in procedure_keywords:
                if keyword in content.lower():
                    entities_found["procedure_name"] = keyword
                    break
    
    # Replace pronouns with entities
    query_lower = query.lower()
    
    # Replace "cái đó", "cái này", "nó" with most relevant entity
    if any(pronoun in query_lower for pronoun in ["cái đó", "cái này", "nó", "đó"]):
        if "fine_name" in entities_found:
            resolved_query = re.sub(
                r'\b(cái đó|cái này|nó|đó)\b',
                entities_found["fine_name"],
                resolved_query,
                flags=re.IGNORECASE
            )
        elif "procedure_name" in entities_found:
            resolved_query = re.sub(
                r'\b(cái đó|cái này|nó|đó)\b',
                entities_found["procedure_name"],
                resolved_query,
                flags=re.IGNORECASE
            )
        elif "office_name" in entities_found:
            resolved_query = re.sub(
                r'\b(cái đó|cái này|nó|đó)\b',
                entities_found["office_name"],
                resolved_query,
                flags=re.IGNORECASE
            )
    
    # Replace "thủ tục đó", "thủ tục này" with procedure name
    if "thủ tục" in query_lower and "procedure_name" in entities_found:
        resolved_query = re.sub(
            r'\bthủ tục (đó|này)\b',
            entities_found["procedure_name"],
            resolved_query,
            flags=re.IGNORECASE
        )
    
    # Replace "mức phạt đó", "mức phạt này" with fine name
    if "mức phạt" in query_lower and "fine_name" in entities_found:
        resolved_query = re.sub(
            r'\bmức phạt (đó|này)\b',
            entities_found["fine_name"],
            resolved_query,
            flags=re.IGNORECASE
        )
    
    return resolved_query


def extract_all_entities(text: str) -> Dict[str, Any]:
    """
    Extract all entities from text.
    
    Args:
        text: Input text.
    
    Returns:
        Dictionary with all extracted entities.
    """
    entities = {}
    
    # Extract fine code
    fine_code = extract_fine_code(text)
    if fine_code:
        entities["fine_code"] = fine_code
    
    # Extract procedure name
    procedure_name = extract_procedure_name(text)
    if procedure_name:
        entities["procedure_name"] = procedure_name
    
    # Extract office name
    office_name = extract_office_name(text)
    if office_name:
        entities["office_name"] = office_name
    
    # Extract pronouns
    pronouns = extract_reference_pronouns(text)
    if pronouns:
        entities["pronouns"] = pronouns
    
    return entities

