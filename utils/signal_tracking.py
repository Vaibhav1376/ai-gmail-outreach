"""
Track signal performance over time
"""
import json
import os
from datetime import datetime
from typing import Dict

SIGNAL_LOG = "tmp/signal_performance.jsonl"

def log_signal_usage(company: Dict, signal_type: str, confidence: int):
    """Log when a signal is used"""
    os.makedirs(os.path.dirname(SIGNAL_LOG), exist_ok=True)
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'company': company.get('name'),
        'signal_type': signal_type,
        'signal': company.get('signal'),
        'confidence': confidence,
        'tier': company.get('signal_tier'),
        'score': company.get('signal_score')
    }
    
    with open(SIGNAL_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')

def get_signal_stats() -> Dict:
    """Get signal usage statistics"""
    if not os.path.exists(SIGNAL_LOG):
        return {'total_signals': 0, 'by_type': {}}
    
    stats = {'total_signals': 0, 'by_type': {}}
    
    with open(SIGNAL_LOG, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                stats['total_signals'] += 1
                signal_type = entry.get('signal_type', 'unknown')
                stats['by_type'][signal_type] = stats['by_type'].get(signal_type, 0) + 1
            except:
                continue
    
    return stats
