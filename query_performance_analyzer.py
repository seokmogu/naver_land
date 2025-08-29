#!/usr/bin/env python3
"""
QUERY PERFORMANCE ANALYZER
Advanced query optimization and performance analysis for Naver real estate system
- Automatic N+1 query detection and resolution
- Query execution plan analysis with recommendations
- Slow query identification and optimization suggestions
- Index usage analysis and optimization recommendations
"""

import psycopg2
import psycopg2.extras
import asyncpg
import time
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import contextmanager
import hashlib
from collections import defaultdict, Counter
import sqlparse
from sqlparse.sql import Statement, Token
from sqlparse.tokens import Keyword, Name

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class QueryAnalysisConfig:
    """Configuration for query analysis"""
    slow_query_threshold_ms: int = 1000  # Queries slower than 1s
    n_plus_one_threshold: int = 10  # N+1 if more than 10 similar queries
    analysis_window_minutes: int = 60  # Analysis time window
    max_analyzed_queries: int = 100  # Max queries to analyze per session
    enable_explain_analyze: bool = False  # Enable EXPLAIN ANALYZE (more expensive)
    cache_execution_plans: bool = True
    
@dataclass
class QueryMetrics:
    """Query performance metrics"""
    query_hash: str
    query_text: str
    execution_count: int
    total_duration_ms: float
    avg_duration_ms: float
    max_duration_ms: float
    min_duration_ms: float
    rows_examined: int
    rows_returned: int
    first_seen: datetime
    last_seen: datetime
    table_scans: int
    index_scans: int
    
    @property
    def efficiency_ratio(self) -> float:
        """Query efficiency: rows returned / rows examined"""
        if self.rows_examined == 0:
            return 1.0
        return min(1.0, self.rows_returned / self.rows_examined)
    
    @property
    def performance_score(self) -> float:
        """Overall performance score (0-100)"""
        duration_score = max(0, 100 - (self.avg_duration_ms / 100))  # Penalize slow queries
        efficiency_score = self.efficiency_ratio * 100
        return (duration_score + efficiency_score) / 2

@dataclass
class ExecutionPlan:
    """Query execution plan analysis"""
    query_hash: str
    plan_json: Dict[str, Any]
    total_cost: float
    execution_time_ms: float
    rows_estimated: int
    rows_actual: int
    node_types: List[str]
    table_scans: List[str]
    index_scans: List[str]
    joins: List[Dict[str, str]]
    sorts: List[Dict[str, Any]]
    recommendations: List[str]

@dataclass
class NPlusOneDetection:
    """N+1 query detection result"""
    base_query_hash: str
    base_query: str
    repeated_query_hash: str
    repeated_query: str
    occurrence_count: int
    total_duration_ms: float
    affected_tables: List[str]
    suggested_solution: str
    confidence_score: float  # 0-1, how confident we are this is N+1

class QueryPerformanceAnalyzer:
    """Advanced query performance analysis engine"""
    
    def __init__(self, database_url: str, config: QueryAnalysisConfig = None):
        self.database_url = database_url
        self.config = config or QueryAnalysisConfig()
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self.execution_plans: Dict[str, ExecutionPlan] = {}
        self.n_plus_one_patterns: List[NPlusOneDetection] = []
        self._query_sequence: List[Tuple[str, datetime]] = []
        
    def _generate_query_hash(self, query: str) -> str:
        """Generate consistent hash for normalized query"""
        # Normalize query by removing specific values
        normalized = self._normalize_query(query)
        return hashlib.md5(normalized.encode()).hexdigest()[:12]
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query by removing specific parameter values"""
        try:
            # Parse SQL
            parsed = sqlparse.parse(query)[0]
            
            # Replace literal values with placeholders
            normalized_tokens = []
            for token in parsed.flatten():
                if token.ttype in (sqlparse.tokens.Literal.String.Single, 
                                  sqlparse.tokens.Literal.Number.Integer,
                                  sqlparse.tokens.Literal.Number.Float):
                    normalized_tokens.append('?')
                elif token.ttype in sqlparse.tokens.Name:
                    # Keep table/column names but normalize case
                    normalized_tokens.append(token.value.lower())
                else:
                    normalized_tokens.append(token.value.upper() if token.is_keyword else token.value)
            
            return ' '.join(normalized_tokens).strip()
            
        except Exception as e:
            logger.warning(f"Failed to normalize query: {e}")
            # Fallback: simple regex-based normalization
            normalized = re.sub(r"'[^']*'", "'?'", query)  # String literals
            normalized = re.sub(r'\b\d+\b', '?', normalized)  # Numbers
            normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces
            return normalized.strip().upper()
    
    def _extract_tables_from_query(self, query: str) -> List[str]:
        """Extract table names from SQL query"""
        tables = []
        try:
            parsed = sqlparse.parse(query)[0]
            
            # Look for table names after FROM, JOIN, UPDATE, INSERT INTO, DELETE FROM
            tokens = list(parsed.flatten())
            
            keywords_before_table = {'FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 
                                   'FULL JOIN', 'UPDATE', 'INSERT INTO', 'DELETE FROM'}
            
            for i, token in enumerate(tokens):
                if token.ttype is Keyword and token.value.upper() in keywords_before_table:
                    # Next non-whitespace token should be table name
                    for j in range(i + 1, len(tokens)):
                        next_token = tokens[j]
                        if not next_token.is_whitespace:
                            if next_token.ttype in (Name, None) and next_token.value.replace('"', '').isalnum():
                                tables.append(next_token.value.strip('"').lower())
                            break
            
            return list(set(tables))  # Remove duplicates
            
        except Exception as e:
            logger.warning(f"Failed to extract tables: {e}")
            
            # Fallback: regex-based extraction
            table_patterns = [
                r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                r'INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)'
            ]
            
            for pattern in table_patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                tables.extend(matches)
            
            return list(set([t.lower() for t in tables]))
    
    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(
                self.database_url,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def analyze_query(self, query: str, execution_time_ms: float = None, 
                     rows_returned: int = None) -> QueryMetrics:
        """Analyze individual query performance"""
        query_hash = self._generate_query_hash(query)
        current_time = datetime.now()
        
        # Record query in sequence for N+1 detection
        self._query_sequence.append((query_hash, current_time))
        
        # Clean old entries
        cutoff_time = current_time - timedelta(minutes=self.config.analysis_window_minutes)
        self._query_sequence = [(h, t) for h, t in self._query_sequence if t > cutoff_time]
        
        # Update or create metrics
        if query_hash in self.query_metrics:
            metrics = self.query_metrics[query_hash]
            metrics.execution_count += 1
            metrics.last_seen = current_time
            
            if execution_time_ms:
                metrics.total_duration_ms += execution_time_ms
                metrics.avg_duration_ms = metrics.total_duration_ms / metrics.execution_count
                metrics.max_duration_ms = max(metrics.max_duration_ms, execution_time_ms)
                metrics.min_duration_ms = min(metrics.min_duration_ms, execution_time_ms)
            
            if rows_returned:
                metrics.rows_returned += rows_returned
                
        else:
            metrics = QueryMetrics(
                query_hash=query_hash,
                query_text=query[:500],  # Truncate for storage
                execution_count=1,
                total_duration_ms=execution_time_ms or 0,
                avg_duration_ms=execution_time_ms or 0,
                max_duration_ms=execution_time_ms or 0,
                min_duration_ms=execution_time_ms or 0,
                rows_examined=0,
                rows_returned=rows_returned or 0,
                first_seen=current_time,
                last_seen=current_time,
                table_scans=0,
                index_scans=0
            )
            self.query_metrics[query_hash] = metrics
        
        # Get execution plan if enabled
        if self.config.cache_execution_plans and query_hash not in self.execution_plans:
            execution_plan = self._analyze_execution_plan(query, query_hash)
            if execution_plan:
                self.execution_plans[query_hash] = execution_plan
                
                # Update metrics with execution plan info
                metrics.rows_examined = execution_plan.rows_estimated
                metrics.table_scans = len(execution_plan.table_scans)
                metrics.index_scans = len(execution_plan.index_scans)
        
        return metrics
    
    def _analyze_execution_plan(self, query: str, query_hash: str) -> Optional[ExecutionPlan]:
        """Analyze query execution plan"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Use EXPLAIN (ANALYZE, FORMAT JSON) if enabled, otherwise just EXPLAIN
                    if self.config.enable_explain_analyze:
                        explain_query = f"EXPLAIN (ANALYZE, FORMAT JSON, BUFFERS) {query}"
                    else:
                        explain_query = f"EXPLAIN (FORMAT JSON, COSTS TRUE) {query}"
                    
                    start_time = time.time()
                    cursor.execute(explain_query)
                    execution_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    plan_result = cursor.fetchone()[0]
                    plan_json = plan_result[0] if isinstance(plan_result, list) else plan_result
                    
                    return self._parse_execution_plan(query_hash, plan_json, execution_time)
                    
        except Exception as e:
            logger.error(f"Failed to analyze execution plan for query {query_hash}: {e}")
            return None
    
    def _parse_execution_plan(self, query_hash: str, plan_json: Dict, 
                            execution_time_ms: float) -> ExecutionPlan:
        """Parse PostgreSQL execution plan JSON"""
        plan = plan_json.get('Plan', {})
        
        # Extract basic metrics
        total_cost = plan.get('Total Cost', 0)
        rows_estimated = plan.get('Plan Rows', 0)
        rows_actual = plan.get('Actual Rows', rows_estimated)
        
        # Recursively extract node information
        node_types = []
        table_scans = []
        index_scans = []
        joins = []
        sorts = []
        
        def extract_nodes(node):
            node_type = node.get('Node Type', '')
            node_types.append(node_type)
            
            # Identify scan types
            if 'Seq Scan' in node_type:
                relation_name = node.get('Relation Name', 'unknown')
                table_scans.append(relation_name)
            elif 'Index' in node_type:
                relation_name = node.get('Relation Name', 'unknown')
                index_name = node.get('Index Name', 'unknown')
                index_scans.append(f"{relation_name}.{index_name}")
            
            # Identify joins
            if 'Join' in node_type:
                join_type = node.get('Join Type', 'Unknown')
                join_condition = node.get('Hash Cond', node.get('Merge Cond', node.get('Join Filter', '')))
                joins.append({
                    'type': join_type,
                    'condition': join_condition,
                    'node_type': node_type
                })
            
            # Identify sorts
            if 'Sort' in node_type:
                sort_key = node.get('Sort Key', [])
                sort_method = node.get('Sort Method', 'Unknown')
                sorts.append({
                    'keys': sort_key,
                    'method': sort_method,
                    'cost': node.get('Total Cost', 0)
                })
            
            # Recursively process child plans
            for child in node.get('Plans', []):
                extract_nodes(child)
        
        extract_nodes(plan)
        
        # Generate recommendations
        recommendations = self._generate_plan_recommendations(
            node_types, table_scans, index_scans, joins, sorts, total_cost
        )
        
        return ExecutionPlan(
            query_hash=query_hash,
            plan_json=plan_json,
            total_cost=total_cost,
            execution_time_ms=execution_time_ms,
            rows_estimated=rows_estimated,
            rows_actual=rows_actual,
            node_types=node_types,
            table_scans=table_scans,
            index_scans=index_scans,
            joins=joins,
            sorts=sorts,
            recommendations=recommendations
        )
    
    def _generate_plan_recommendations(self, node_types: List[str], table_scans: List[str], 
                                     index_scans: List[str], joins: List[Dict], 
                                     sorts: List[Dict], total_cost: float) -> List[str]:
        """Generate optimization recommendations based on execution plan"""
        recommendations = []
        
        # Check for sequential scans on large tables
        if table_scans:
            for table in table_scans:
                recommendations.append(
                    f"Consider adding index on {table} - sequential scan detected"
                )
        
        # Check for expensive sorts
        for sort in sorts:
            if sort['cost'] > 1000:  # High cost sort
                recommendations.append(
                    f"Expensive sort on {sort['keys']} - consider index or query optimization"
                )
        
        # Check for nested loop joins without indexes
        nested_loops = [j for j in joins if 'Nested Loop' in j.get('node_type', '')]
        if nested_loops:
            recommendations.append(
                "Nested loop joins detected - ensure proper indexes on join columns"
            )
        
        # Check overall query cost
        if total_cost > 10000:
            recommendations.append(
                f"High total cost ({total_cost:.0f}) - consider query restructuring"
            )
        
        # Check for missing join conditions
        hash_joins_without_condition = [
            j for j in joins 
            if 'Hash' in j.get('node_type', '') and not j.get('condition')
        ]
        if hash_joins_without_condition:
            recommendations.append(
                "Hash join without proper condition detected - check join logic"
            )
        
        return recommendations
    
    def detect_n_plus_one_queries(self) -> List[NPlusOneDetection]:
        """Detect N+1 query patterns in recent query history"""
        detections = []
        
        # Group queries by hash and count occurrences
        query_counts = Counter([query_hash for query_hash, _ in self._query_sequence])
        
        # Look for patterns: one query followed by many similar queries
        potential_n_plus_one = {}
        
        # Sliding window approach to detect patterns
        window_size = 50  # Look at windows of 50 queries
        for i in range(len(self._query_sequence) - window_size):
            window = self._query_sequence[i:i + window_size]
            window_counts = Counter([query_hash for query_hash, _ in window])
            
            # Find queries that appear frequently in this window
            for query_hash, count in window_counts.items():
                if count >= self.config.n_plus_one_threshold:
                    if query_hash not in potential_n_plus_one:
                        potential_n_plus_one[query_hash] = []
                    potential_n_plus_one[query_hash].append(count)
        
        # Analyze potential N+1 patterns
        for query_hash, counts in potential_n_plus_one.items():
            if query_hash not in self.query_metrics:
                continue
            
            metrics = self.query_metrics[query_hash]
            avg_count = sum(counts) / len(counts)
            
            # Calculate confidence score
            confidence = min(1.0, (avg_count - 5) / 20)  # Scale from 5-25 occurrences
            
            # Determine affected tables
            affected_tables = self._extract_tables_from_query(metrics.query_text)
            
            # Generate solution suggestion
            solution = self._suggest_n_plus_one_solution(metrics.query_text, affected_tables)
            
            detection = NPlusOneDetection(
                base_query_hash="unknown",  # Would need more sophisticated pattern matching
                base_query="unknown",
                repeated_query_hash=query_hash,
                repeated_query=metrics.query_text,
                occurrence_count=int(avg_count),
                total_duration_ms=metrics.total_duration_ms,
                affected_tables=affected_tables,
                suggested_solution=solution,
                confidence_score=confidence
            )
            
            detections.append(detection)
        
        self.n_plus_one_patterns = detections
        return detections
    
    def _suggest_n_plus_one_solution(self, query: str, tables: List[str]) -> str:
        """Suggest solution for N+1 query pattern"""
        if not tables:
            return "Consider using bulk queries or joins to fetch related data"
        
        if len(tables) == 1:
            return f"Use bulk query with IN clause for {tables[0]} instead of individual queries"
        else:
            return f"Use JOIN to fetch data from {', '.join(tables)} in single query"
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryMetrics]:
        """Get slowest queries by average execution time"""
        slow_queries = [
            metrics for metrics in self.query_metrics.values()
            if metrics.avg_duration_ms >= self.config.slow_query_threshold_ms
        ]
        
        return sorted(slow_queries, key=lambda x: x.avg_duration_ms, reverse=True)[:limit]
    
    def get_inefficient_queries(self, limit: int = 10) -> List[QueryMetrics]:
        """Get queries with low efficiency ratios"""
        inefficient = [
            metrics for metrics in self.query_metrics.values()
            if metrics.efficiency_ratio < 0.1  # Less than 10% efficiency
        ]
        
        return sorted(inefficient, key=lambda x: x.efficiency_ratio)[:limit]
    
    def get_most_frequent_queries(self, limit: int = 10) -> List[QueryMetrics]:
        """Get most frequently executed queries"""
        return sorted(
            self.query_metrics.values(),
            key=lambda x: x.execution_count,
            reverse=True
        )[:limit]
    
    def generate_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        
        # Detect N+1 patterns
        n_plus_one_detections = self.detect_n_plus_one_queries()
        
        report = {
            'analysis_summary': {
                'total_queries_analyzed': len(self.query_metrics),
                'analysis_period_minutes': self.config.analysis_window_minutes,
                'slow_queries_count': len(self.get_slow_queries(100)),
                'n_plus_one_patterns': len(n_plus_one_detections),
                'execution_plans_cached': len(self.execution_plans)
            },
            
            'slow_queries': [
                {
                    'query_hash': m.query_hash,
                    'query_preview': m.query_text[:100] + '...' if len(m.query_text) > 100 else m.query_text,
                    'avg_duration_ms': round(m.avg_duration_ms, 2),
                    'execution_count': m.execution_count,
                    'performance_score': round(m.performance_score, 1),
                    'recommendations': self.execution_plans.get(m.query_hash, ExecutionPlan(
                        '', {}, 0, 0, 0, 0, [], [], [], [], [], []
                    )).recommendations
                }
                for m in self.get_slow_queries(10)
            ],
            
            'n_plus_one_patterns': [
                {
                    'repeated_query_preview': d.repeated_query[:100] + '...' if len(d.repeated_query) > 100 else d.repeated_query,
                    'occurrence_count': d.occurrence_count,
                    'total_duration_ms': round(d.total_duration_ms, 2),
                    'affected_tables': d.affected_tables,
                    'suggested_solution': d.suggested_solution,
                    'confidence_score': round(d.confidence_score, 2)
                }
                for d in n_plus_one_detections
            ],
            
            'inefficient_queries': [
                {
                    'query_hash': m.query_hash,
                    'query_preview': m.query_text[:100] + '...' if len(m.query_text) > 100 else m.query_text,
                    'efficiency_ratio': round(m.efficiency_ratio, 3),
                    'rows_examined': m.rows_examined,
                    'rows_returned': m.rows_returned
                }
                for m in self.get_inefficient_queries(5)
            ],
            
            'most_frequent_queries': [
                {
                    'query_hash': m.query_hash,
                    'query_preview': m.query_text[:100] + '...' if len(m.query_text) > 100 else m.query_text,
                    'execution_count': m.execution_count,
                    'avg_duration_ms': round(m.avg_duration_ms, 2),
                    'total_duration_ms': round(m.total_duration_ms, 2)
                }
                for m in self.get_most_frequent_queries(5)
            ],
            
            'optimization_recommendations': self._generate_global_recommendations()
        }
        
        return report
    
    def _generate_global_recommendations(self) -> List[str]:
        """Generate global optimization recommendations"""
        recommendations = []
        
        # Check for overall patterns
        total_queries = len(self.query_metrics)
        slow_queries = len(self.get_slow_queries(1000))
        n_plus_one_count = len(self.n_plus_one_patterns)
        
        if slow_queries / max(total_queries, 1) > 0.1:  # More than 10% slow queries
            recommendations.append(
                "High percentage of slow queries detected - review database indexing strategy"
            )
        
        if n_plus_one_count > 0:
            recommendations.append(
                f"Found {n_plus_one_count} potential N+1 query patterns - implement bulk loading"
            )
        
        # Check for common table access patterns
        table_access_counts = defaultdict(int)
        for metrics in self.query_metrics.values():
            tables = self._extract_tables_from_query(metrics.query_text)
            for table in tables:
                table_access_counts[table] += metrics.execution_count
        
        if table_access_counts:
            most_accessed = max(table_access_counts, key=table_access_counts.get)
            recommendations.append(
                f"Most accessed table: {most_accessed} - ensure optimal indexing"
            )
        
        # Check execution plan patterns
        common_issues = defaultdict(int)
        for plan in self.execution_plans.values():
            if plan.table_scans:
                common_issues['sequential_scans'] += len(plan.table_scans)
            if any('Nested Loop' in join.get('node_type', '') for join in plan.joins):
                common_issues['nested_loops'] += 1
            if any(sort['cost'] > 1000 for sort in plan.sorts):
                common_issues['expensive_sorts'] += 1
        
        if common_issues['sequential_scans'] > total_queries * 0.3:
            recommendations.append(
                "Many queries using sequential scans - add selective indexes"
            )
        
        if common_issues['nested_loops'] > total_queries * 0.2:
            recommendations.append(
                "Many nested loop joins detected - optimize join conditions and indexes"
            )
        
        return recommendations
    
    def print_analysis_report(self):
        """Print formatted analysis report"""
        report = self.generate_optimization_report()
        
        print("\n" + "="*80)
        print("📊 QUERY PERFORMANCE ANALYSIS REPORT")
        print("="*80)
        
        # Summary
        summary = report['analysis_summary']
        print(f"📈 Total Queries Analyzed: {summary['total_queries_analyzed']}")
        print(f"⏰ Analysis Period: {summary['analysis_period_minutes']} minutes")
        print(f"🐌 Slow Queries: {summary['slow_queries_count']}")
        print(f"🔄 N+1 Patterns: {summary['n_plus_one_patterns']}")
        print(f"📋 Execution Plans: {summary['execution_plans_cached']}")
        
        # Slow queries
        if report['slow_queries']:
            print(f"\n🐌 TOP SLOW QUERIES:")
            print("-" * 60)
            for i, query in enumerate(report['slow_queries'][:5], 1):
                print(f"{i}. Query: {query['query_preview']}")
                print(f"   Avg Duration: {query['avg_duration_ms']}ms")
                print(f"   Executions: {query['execution_count']}")
                print(f"   Performance Score: {query['performance_score']}/100")
                if query['recommendations']:
                    print(f"   Recommendations: {', '.join(query['recommendations'][:2])}")
                print()
        
        # N+1 patterns
        if report['n_plus_one_patterns']:
            print(f"🔄 N+1 QUERY PATTERNS:")
            print("-" * 60)
            for i, pattern in enumerate(report['n_plus_one_patterns'], 1):
                print(f"{i}. Pattern: {pattern['repeated_query_preview']}")
                print(f"   Occurrences: {pattern['occurrence_count']}")
                print(f"   Total Duration: {pattern['total_duration_ms']}ms")
                print(f"   Tables: {', '.join(pattern['affected_tables'])}")
                print(f"   Solution: {pattern['suggested_solution']}")
                print(f"   Confidence: {pattern['confidence_score']}")
                print()
        
        # Global recommendations
        if report['optimization_recommendations']:
            print(f"💡 OPTIMIZATION RECOMMENDATIONS:")
            print("-" * 60)
            for i, rec in enumerate(report['optimization_recommendations'], 1):
                print(f"{i}. {rec}")
            print()
        
        print("="*80)
    
    def reset_analysis(self):
        """Reset all analysis data"""
        self.query_metrics.clear()
        self.execution_plans.clear()
        self.n_plus_one_patterns.clear()
        self._query_sequence.clear()
        logger.info("🔄 Query analysis data reset")

# Integration with existing collector
class PerformanceMonitoringCollector:
    """Enhanced collector with built-in query performance monitoring"""
    
    def __init__(self, original_collector, database_url: str):
        self.collector = original_collector
        self.analyzer = QueryPerformanceAnalyzer(database_url)
        self._start_time = time.time()
    
    def execute_with_monitoring(self, query: str, params: tuple = None):
        """Execute query with performance monitoring"""
        start_time = time.time()
        
        try:
            # Execute original query
            with self.analyzer.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    result = cursor.fetchall()
                    rows_returned = len(result) if result else 0
            
            # Record performance metrics
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            self.analyzer.analyze_query(query, execution_time, rows_returned)
            
            return result
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            self.analyzer.analyze_query(query, execution_time, 0)
            raise
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance monitoring summary"""
        return {
            'monitoring_duration_minutes': (time.time() - self._start_time) / 60,
            'analysis_report': self.analyzer.generate_optimization_report()
        }
    
    def print_performance_summary(self):
        """Print performance monitoring summary"""
        summary = self.get_performance_summary()
        
        print(f"\n⏱️ Performance monitoring duration: {summary['monitoring_duration_minutes']:.1f} minutes")
        self.analyzer.print_analysis_report()

# Example usage
def main():
    """Example usage of query performance analyzer"""
    DATABASE_URL = "postgresql://user:password@localhost:5432/dbname"
    
    config = QueryAnalysisConfig(
        slow_query_threshold_ms=500,
        n_plus_one_threshold=5,
        enable_explain_analyze=False  # Set to True for more detailed analysis
    )
    
    analyzer = QueryPerformanceAnalyzer(DATABASE_URL, config)
    
    # Simulate some queries for analysis
    test_queries = [
        "SELECT * FROM properties_new WHERE region_id = 1",
        "SELECT * FROM property_prices WHERE property_id = 123",
        "SELECT * FROM property_prices WHERE property_id = 124",
        "SELECT * FROM property_prices WHERE property_id = 125",
        "SELECT COUNT(*) FROM properties_new",
        "SELECT * FROM property_locations WHERE latitude BETWEEN 37.4 AND 37.6"
    ]
    
    # Analyze queries
    for query in test_queries * 10:  # Simulate multiple executions
        execution_time = 50 + (len(query) * 2)  # Simulate variable execution times
        analyzer.analyze_query(query, execution_time, 10)
    
    # Generate and print report
    analyzer.print_analysis_report()

if __name__ == "__main__":
    main()