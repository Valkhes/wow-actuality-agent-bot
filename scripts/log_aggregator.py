#!/usr/bin/env python3
"""
Log aggregation and analysis script for WoW Actuality Bot
Processes logs from all services and generates monitoring reports
"""

import os
import json
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import re


class LogAggregator:
    """Aggregate and analyze logs from all services"""
    
    def __init__(self, logs_dir: str = "./logs"):
        self.logs_dir = Path(logs_dir)
        self.services = ["discord-bot", "api-service", "crawler-service", "litellm-gateway"]
        self.error_patterns = {
            "timeout": r"timeout|timed out|TimeoutError",
            "connection": r"connection|ConnectionError|refused|unreachable",
            "auth": r"auth|authentication|unauthorized|forbidden|401|403",
            "rate_limit": r"rate.?limit|429|too many requests",
            "security": r"security|injection|blocked|malicious",
            "validation": r"validation|invalid|malformed|bad request|400"
        }
    
    def aggregate_logs(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate logs for a specific date (default: today)"""
        if not date:
            date = datetime.utcnow().strftime('%Y%m%d')
        
        aggregated = {
            "date": date,
            "services": {},
            "overall_stats": {
                "total_log_entries": 0,
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0
            },
            "error_analysis": {},
            "performance_metrics": {},
            "security_events": []
        }
        
        for service in self.services:
            service_data = self._process_service_logs(service, date)
            if service_data:
                aggregated["services"][service] = service_data
                
                # Update overall stats
                stats = service_data.get("stats", {})
                aggregated["overall_stats"]["total_log_entries"] += stats.get("total_entries", 0)
                aggregated["overall_stats"]["error_count"] += stats.get("error_count", 0)
                aggregated["overall_stats"]["warning_count"] += stats.get("warning_count", 0)
                aggregated["overall_stats"]["info_count"] += stats.get("info_count", 0)
                
                # Merge error analysis
                for error_type, count in service_data.get("error_analysis", {}).items():
                    aggregated["error_analysis"][error_type] = aggregated["error_analysis"].get(error_type, 0) + count
                
                # Collect security events
                aggregated["security_events"].extend(service_data.get("security_events", []))
        
        # Calculate error rate
        total_entries = aggregated["overall_stats"]["total_log_entries"]
        if total_entries > 0:
            aggregated["overall_stats"]["error_rate"] = (
                aggregated["overall_stats"]["error_count"] / total_entries * 100
            )
        
        return aggregated
    
    def _process_service_logs(self, service: str, date: str) -> Dict[str, Any]:
        """Process logs for a specific service and date"""
        log_pattern = f"{service}_{date}.log"
        log_files = list(self.logs_dir.glob(log_pattern))
        
        if not log_files:
            return None
        
        service_data = {
            "service": service,
            "log_files": [str(f) for f in log_files],
            "stats": {
                "total_entries": 0,
                "error_count": 0,
                "warning_count": 0,
                "info_count": 0,
                "debug_count": 0
            },
            "error_analysis": {},
            "performance_metrics": {
                "avg_response_time": 0,
                "slow_queries": 0,
                "total_requests": 0
            },
            "security_events": [],
            "top_errors": [],
            "recent_errors": []
        }
        
        total_response_times = []
        error_messages = []
        
        for log_file in log_files:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        if line.strip():
                            log_entry = self._parse_log_entry(line.strip())
                            if log_entry:
                                self._process_log_entry(service_data, log_entry, total_response_times, error_messages)
                    except Exception as e:
                        # Skip malformed log entries
                        continue
        
        # Calculate performance metrics
        if total_response_times:
            service_data["performance_metrics"]["avg_response_time"] = sum(total_response_times) / len(total_response_times)
            service_data["performance_metrics"]["slow_queries"] = sum(1 for t in total_response_times if t > 1000)
        
        # Analyze top errors
        if error_messages:
            error_counter = Counter(error_messages)
            service_data["top_errors"] = [
                {"message": msg, "count": count}
                for msg, count in error_counter.most_common(10)
            ]
        
        return service_data
    
    def _parse_log_entry(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a log entry (JSON or structured text)"""
        try:
            # Try JSON first
            return json.loads(line)
        except json.JSONDecodeError:
            # Try to parse structured text log
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', line)
            level_match = re.search(r'\[(ERROR|WARNING|INFO|DEBUG)\]', line)
            
            if timestamp_match and level_match:
                return {
                    "timestamp": timestamp_match.group(1),
                    "level": level_match.group(1),
                    "event": line,
                    "parsed_from_text": True
                }
        
        return None
    
    def _process_log_entry(self, service_data: Dict[str, Any], entry: Dict[str, Any], response_times: List[float], error_messages: List[str]):
        """Process a single log entry"""
        service_data["stats"]["total_entries"] += 1
        
        level = entry.get("level", "").upper()
        if level == "ERROR":
            service_data["stats"]["error_count"] += 1
            error_msg = entry.get("event", entry.get("error_message", "Unknown error"))
            error_messages.append(error_msg[:100])  # Truncate for grouping
            
            # Store recent errors
            if len(service_data["recent_errors"]) < 20:
                service_data["recent_errors"].append({
                    "timestamp": entry.get("timestamp"),
                    "message": error_msg[:200],
                    "context": entry.get("context", {})
                })
        elif level == "WARNING":
            service_data["stats"]["warning_count"] += 1
        elif level == "INFO":
            service_data["stats"]["info_count"] += 1
        elif level == "DEBUG":
            service_data["stats"]["debug_count"] += 1
        
        # Analyze error patterns
        message = entry.get("event", entry.get("error_message", "")).lower()
        for pattern_name, pattern in self.error_patterns.items():
            if re.search(pattern, message):
                service_data["error_analysis"][pattern_name] = service_data["error_analysis"].get(pattern_name, 0) + 1
        
        # Extract performance metrics
        if "duration" in entry:
            try:
                duration = float(entry["duration"])
                response_times.append(duration)
                service_data["performance_metrics"]["total_requests"] += 1
            except (ValueError, TypeError):
                pass
        
        # Detect security events
        if any(keyword in message for keyword in ["blocked", "injection", "security", "malicious"]):
            service_data["security_events"].append({
                "timestamp": entry.get("timestamp"),
                "service": service_data["service"],
                "event": message[:200],
                "severity": "HIGH" if level == "ERROR" else "MEDIUM"
            })
    
    def generate_report(self, aggregated_data: Dict[str, Any], output_file: Optional[str] = None) -> str:
        """Generate a human-readable report"""
        report_lines = [
            f"# WoW Actuality Bot Log Analysis Report",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"Date: {aggregated_data['date']}",
            "",
            "## Overall Statistics",
            f"- Total log entries: {aggregated_data['overall_stats']['total_log_entries']:,}",
            f"- Errors: {aggregated_data['overall_stats']['error_count']:,}",
            f"- Warnings: {aggregated_data['overall_stats']['warning_count']:,}",
            f"- Info: {aggregated_data['overall_stats']['info_count']:,}",
            f"- Error rate: {aggregated_data['overall_stats'].get('error_rate', 0):.2f}%",
            ""
        ]
        
        # Service breakdown
        if aggregated_data["services"]:
            report_lines.append("## Service Breakdown")
            for service, data in aggregated_data["services"].items():
                stats = data["stats"]
                report_lines.extend([
                    f"### {service}",
                    f"- Total entries: {stats['total_entries']:,}",
                    f"- Errors: {stats['error_count']:,}",
                    f"- Warnings: {stats['warning_count']:,}",
                    f"- Avg response time: {data['performance_metrics']['avg_response_time']:.1f}ms",
                    f"- Slow queries: {data['performance_metrics']['slow_queries']}",
                    ""
                ])
        
        # Error analysis
        if aggregated_data["error_analysis"]:
            report_lines.extend([
                "## Error Analysis",
                "Error types by frequency:"
            ])
            for error_type, count in sorted(aggregated_data["error_analysis"].items(), key=lambda x: x[1], reverse=True):
                report_lines.append(f"- {error_type}: {count}")
            report_lines.append("")
        
        # Security events
        if aggregated_data["security_events"]:
            report_lines.extend([
                "## Security Events",
                f"Total security events: {len(aggregated_data['security_events'])}"
            ])
            for event in aggregated_data["security_events"][-10:]:  # Show last 10
                report_lines.append(f"- [{event['timestamp']}] {event['service']}: {event['event']}")
            report_lines.append("")
        
        # Recent errors by service
        for service, data in aggregated_data.get("services", {}).items():
            if data.get("recent_errors"):
                report_lines.extend([
                    f"## Recent Errors - {service}",
                ])
                for error in data["recent_errors"][-5:]:  # Show last 5
                    report_lines.append(f"- [{error['timestamp']}] {error['message']}")
                report_lines.append("")
        
        # Recommendations
        report_lines.extend([
            "## Recommendations",
            self._generate_recommendations(aggregated_data),
            ""
        ])
        
        report = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
        
        return report
    
    def _generate_recommendations(self, data: Dict[str, Any]) -> str:
        """Generate recommendations based on log analysis"""
        recommendations = []
        
        error_rate = data["overall_stats"].get("error_rate", 0)
        if error_rate > 5:
            recommendations.append("- **HIGH**: Error rate is above 5%. Investigate error patterns immediately.")
        
        if "rate_limit" in data["error_analysis"] and data["error_analysis"]["rate_limit"] > 10:
            recommendations.append("- **MEDIUM**: High number of rate limit errors. Consider implementing backoff strategies.")
        
        if "timeout" in data["error_analysis"] and data["error_analysis"]["timeout"] > 5:
            recommendations.append("- **MEDIUM**: Timeout errors detected. Check service connectivity and response times.")
        
        if len(data["security_events"]) > 20:
            recommendations.append("- **HIGH**: High number of security events. Review security monitoring and blocking rules.")
        
        for service, service_data in data.get("services", {}).items():
            avg_response = service_data["performance_metrics"]["avg_response_time"]
            if avg_response > 5000:  # 5 seconds
                recommendations.append(f"- **MEDIUM**: {service} has high average response time ({avg_response:.1f}ms). Optimize performance.")
        
        if not recommendations:
            recommendations.append("- **GOOD**: No critical issues detected in logs.")
        
        return "\n".join(recommendations)
    
    def export_to_json(self, aggregated_data: Dict[str, Any], output_file: str):
        """Export aggregated data to JSON"""
        with open(output_file, 'w') as f:
            json.dump(aggregated_data, f, indent=2, default=str)
    
    def cleanup_old_reports(self, days_to_keep: int = 30):
        """Clean up old log reports"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        for report_file in self.logs_dir.glob("log_report_*.json"):
            try:
                # Extract date from filename
                date_str = report_file.stem.split("_")[-1]
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                if file_date < cutoff_date:
                    report_file.unlink()
                    print(f"Cleaned up old report: {report_file}")
            except (ValueError, IndexError):
                continue


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Aggregate and analyze WoW Actuality Bot logs")
    parser.add_argument("--logs-dir", default="./logs", help="Directory containing log files")
    parser.add_argument("--date", help="Date to analyze (YYYYMMDD format, default: today)")
    parser.add_argument("--output-report", help="Output file for text report")
    parser.add_argument("--output-json", help="Output file for JSON data")
    parser.add_argument("--cleanup", action="store_true", help="Cleanup old reports")
    parser.add_argument("--cleanup-days", type=int, default=30, help="Days of reports to keep")
    
    args = parser.parse_args()
    
    aggregator = LogAggregator(args.logs_dir)
    
    if args.cleanup:
        aggregator.cleanup_old_reports(args.cleanup_days)
        return
    
    # Aggregate logs
    print(f"Aggregating logs from {args.logs_dir}...")
    aggregated_data = aggregator.aggregate_logs(args.date)
    
    # Generate report
    date_str = args.date or datetime.utcnow().strftime('%Y%m%d')
    
    if not args.output_report:
        args.output_report = f"./reports/log_report_{date_str}.md"
    
    os.makedirs(os.path.dirname(args.output_report), exist_ok=True)
    report = aggregator.generate_report(aggregated_data, args.output_report)
    
    print(f"Report generated: {args.output_report}")
    
    # Export JSON if requested
    if args.output_json:
        aggregator.export_to_json(aggregated_data, args.output_json)
        print(f"JSON data exported: {args.output_json}")
    
    # Print summary
    stats = aggregated_data["overall_stats"]
    print(f"\nSummary for {date_str}:")
    print(f"  Total entries: {stats['total_log_entries']:,}")
    print(f"  Errors: {stats['error_count']:,}")
    print(f"  Error rate: {stats.get('error_rate', 0):.2f}%")
    print(f"  Security events: {len(aggregated_data['security_events'])}")


if __name__ == "__main__":
    main()