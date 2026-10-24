# utils/geo_validator.py

from typing import List, Dict

def detect_multiple_geographies(companies: List[Dict]) -> Dict:
    """
    Detect if campaign spans multiple geographies
    """
    geographies = set()
    
    for company in companies:
        location = str(company.get('location', '')).lower()
        
        # Geography detection
        if any(x in location for x in ['india', 'bangalore', 'mumbai', 'delhi', 'hyderabad', 'chennai', 'pune']):
            geographies.add('India')
        elif any(x in location for x in ['usa', 'us', 'united states', 'california', 'new york', 'texas', 'san francisco', 'boston']):
            geographies.add('US')
        elif any(x in location for x in ['uk', 'united kingdom', 'london', 'manchester']):
            geographies.add('UK')
        elif any(x in location for x in ['canada', 'toronto', 'vancouver']):
            geographies.add('Canada')
        elif any(x in location for x in ['australia', 'sydney', 'melbourne']):
            geographies.add('Australia')
    
    return {
        'multiple_geos': len(geographies) > 1,
        'geographies': sorted(list(geographies)),
        'count': len(geographies),
        'warning': f"⚠️ Campaign spans {len(geographies)} geographies: {', '.join(sorted(geographies))}" if len(geographies) > 1 else None
    }


def validate_geo_coverage(target_cities: List[str]) -> Dict:
    """
    Check if cities are supported
    """
    supported_cities = {
        'India': ['bangalore', 'mumbai', 'delhi', 'hyderabad', 'chennai', 'pune'],
        'US': ['san francisco', 'new york', 'boston', 'austin', 'seattle', 'los angeles'],
        'UK': ['london', 'manchester', 'edinburgh'],
    }
    
    unsupported = []
    
    for city in target_cities:
        city_lower = city.lower()
        is_supported = False
        
        for geo, cities in supported_cities.items():
            if any(supported_city in city_lower for supported_city in cities):
                is_supported = True
                break
        
        if not is_supported:
            unsupported.append(city)
    
    return {
        'all_supported': len(unsupported) == 0,
        'unsupported_cities': unsupported,
        'warning': f"⚠️ Unsupported cities: {', '.join(unsupported)}" if unsupported else None
    }
