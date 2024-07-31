import re
from typing import Any, Dict 

TO_IGNORE = [
    "asin", 
    "poids_de_larticle", 
    "relie", 
    "taille_du_fichier", 
    "utilisation_simultanee_de_lappareil",
    "pagination_isbn_de_ledition_imprimee_de_reference",
    "dimensions",
    "isbn_10",
    "isbn_13",
    "pense_betes",
    "lecteur_decran",
]

def parse_book_data(data: Dict[str, Any]) -> Dict[str, Any]:
    cleaned_data = {}

    for key, value in data.items():
        clean_key = re.sub(r'\u200e', '', key).strip().lower().replace(' ', '_')

        if clean_key in TO_IGNORE:
            continue
        
        if isinstance(value, str):
            clean_value = re.sub(r'\u200e', '', value).strip()
        else:
            clean_value = value

        cleaned_data[clean_key] = clean_value

    return cleaned_data
