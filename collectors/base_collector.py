#!/usr/bin/env python3
"""
수집기 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseCollector(ABC):
    def __init__(self):
        self.collected_articles = []
        self.failed_articles = []
        self.stats = {
            'total_attempted': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
    
    @abstractmethod
    def collect_article(self, article_no: str) -> Optional[Dict]:
        pass
    
    @abstractmethod
    def collect_area(self, area_code: str) -> List[str]:
        pass
    
    def update_stats(self, status: str):
        self.stats['total_attempted'] += 1
        if status in self.stats:
            self.stats[status] += 1
    
    def get_collection_summary(self) -> Dict[str, Any]:
        return {
            'stats': self.stats,
            'collected_count': len(self.collected_articles),
            'failed_count': len(self.failed_articles),
            'success_rate': f"{(self.stats['successful'] / max(1, self.stats['total_attempted']) * 100):.2f}%"
        }