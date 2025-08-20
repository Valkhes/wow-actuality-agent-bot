#!/usr/bin/env python3
"""
Setup script for Langfuse monitoring dashboards and alerts
Creates custom dashboards and sets up basic monitoring configuration
"""

import os
import sys
import asyncio
import httpx
import structlog
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Configuration
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")

class LangfuseMonitoringSetup:
    """Setup Langfuse monitoring dashboards and alerts"""
    
    def __init__(self, host: str, public_key: str = None, secret_key: str = None):
        self.host = host.rstrip('/')
        self.public_key = public_key
        self.secret_key = secret_key
        
        # Setup HTTP client
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Content-Type": "application/json"
            }
        )
    
    async def check_langfuse_health(self) -> bool:
        """Check if Langfuse is accessible"""
        try:
            response = await self.client.get(f"{self.host}/api/public/health")
            response.raise_for_status()
            logger.info("Langfuse health check passed", status_code=response.status_code)
            return True
        except Exception as e:
            logger.error("Langfuse health check failed", error=str(e))
            return False
    
    async def setup_monitoring_dashboards(self) -> Dict[str, Any]:
        """Setup monitoring dashboards for WoW Actuality Bot"""
        
        logger.info("Setting up monitoring dashboards")
        
        # Dashboard configuration
        dashboard_config = {
            "wow_actuality_overview": {
                "title": "WoW Actuality Bot - Overview",
                "description": "Main dashboard for WoW Actuality Discord bot monitoring",
                "metrics": [
                    {
                        "name": "Total Requests",
                        "type": "counter",
                        "description": "Total number of /ask commands processed"
                    },
                    {
                        "name": "Average Response Time", 
                        "type": "duration",
                        "description": "Average time to process questions"
                    },
                    {
                        "name": "Error Rate",
                        "type": "percentage", 
                        "description": "Percentage of failed requests"
                    },
                    {
                        "name": "Token Usage",
                        "type": "counter",
                        "description": "Total tokens consumed by LLM"
                    },
                    {
                        "name": "Cost Estimate",
                        "type": "currency",
                        "description": "Estimated API costs"
                    }
                ]
            },
            "security_monitoring": {
                "title": "WoW Actuality Bot - Security",
                "description": "Security monitoring for prompt injection and abuse detection",
                "metrics": [
                    {
                        "name": "Blocked Requests",
                        "type": "counter", 
                        "description": "Requests blocked by security policies"
                    },
                    {
                        "name": "Rate Limits Hit",
                        "type": "counter",
                        "description": "Rate limit violations"
                    },
                    {
                        "name": "Security Alerts",
                        "type": "counter",
                        "description": "Security-related alerts triggered"
                    }
                ]
            },
            "performance_monitoring": {
                "title": "WoW Actuality Bot - Performance", 
                "description": "Performance metrics and resource usage",
                "metrics": [
                    {
                        "name": "Context Documents Retrieved",
                        "type": "histogram",
                        "description": "Number of context documents used per query"
                    },
                    {
                        "name": "Confidence Scores",
                        "type": "histogram", 
                        "description": "Distribution of AI response confidence scores"
                    },
                    {
                        "name": "Vector Database Latency",
                        "type": "duration",
                        "description": "ChromaDB query response times"
                    }
                ]
            }
        }
        
        results = {}
        for dashboard_id, config in dashboard_config.items():
            try:
                result = await self._create_dashboard_config(dashboard_id, config)
                results[dashboard_id] = {
                    "status": "configured",
                    "config": config,
                    "result": result
                }
                logger.info("Dashboard configured", dashboard_id=dashboard_id)
            except Exception as e:
                logger.error("Failed to configure dashboard", dashboard_id=dashboard_id, error=str(e))
                results[dashboard_id] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return results
    
    async def _create_dashboard_config(self, dashboard_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create dashboard configuration (placeholder - real implementation would use Langfuse API)"""
        
        # In a real implementation, this would create actual dashboards in Langfuse
        # For now, we'll create a configuration file that can be imported
        
        dashboard_file = f"./config/dashboards/{dashboard_id}.json"
        os.makedirs(os.path.dirname(dashboard_file), exist_ok=True)
        
        dashboard_data = {
            "id": dashboard_id,
            "created_at": datetime.utcnow().isoformat(),
            "config": config,
            "langfuse_queries": self._generate_langfuse_queries(config)
        }
        
        with open(dashboard_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        
        return {"file_created": dashboard_file}
    
    def _generate_langfuse_queries(self, config: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate sample Langfuse queries for dashboard metrics"""
        
        queries = []
        
        for metric in config.get("metrics", []):
            if metric["name"] == "Total Requests":
                queries.append({
                    "metric": metric["name"],
                    "query": "SELECT COUNT(*) FROM traces WHERE name = 'ask_question'",
                    "description": "Count all ask_question traces"
                })
            elif metric["name"] == "Average Response Time":
                queries.append({
                    "metric": metric["name"], 
                    "query": "SELECT AVG(duration) FROM traces WHERE name = 'ask_question'",
                    "description": "Average duration of ask_question traces"
                })
            elif metric["name"] == "Error Rate":
                queries.append({
                    "metric": metric["name"],
                    "query": "SELECT (COUNT(CASE WHEN level = 'ERROR' THEN 1 END) * 100.0 / COUNT(*)) FROM traces WHERE name = 'ask_question'",
                    "description": "Error percentage for ask_question traces"
                })
            elif metric["name"] == "Token Usage":
                queries.append({
                    "metric": metric["name"],
                    "query": "SELECT SUM(usage_completion_tokens + usage_prompt_tokens) FROM generations",
                    "description": "Total tokens consumed"
                })
        
        return queries
    
    async def setup_alert_thresholds(self) -> Dict[str, Any]:
        """Setup alert thresholds for monitoring"""
        
        alert_config = {
            "error_rate_threshold": {
                "metric": "error_rate",
                "threshold": 5.0,  # 5% error rate
                "condition": "greater_than",
                "severity": "warning",
                "description": "Alert when error rate exceeds 5%"
            },
            "response_time_threshold": {
                "metric": "avg_response_time", 
                "threshold": 10000,  # 10 seconds
                "condition": "greater_than",
                "severity": "warning",
                "description": "Alert when average response time exceeds 10 seconds"
            },
            "security_alert_threshold": {
                "metric": "blocked_requests",
                "threshold": 10,  # 10 blocked requests per hour
                "condition": "greater_than", 
                "timeframe": "1h",
                "severity": "critical",
                "description": "Alert when more than 10 requests are blocked per hour"
            },
            "cost_threshold": {
                "metric": "daily_cost",
                "threshold": 50.0,  # $50 per day
                "condition": "greater_than",
                "timeframe": "1d",
                "severity": "warning",
                "description": "Alert when daily costs exceed $50"
            }
        }
        
        # Save alert configuration
        alert_file = "./config/alerts.json"
        os.makedirs(os.path.dirname(alert_file), exist_ok=True)
        
        alert_data = {
            "created_at": datetime.utcnow().isoformat(),
            "alerts": alert_config,
            "notification_channels": {
                "email": "admin@example.com",
                "slack": "#wow-bot-alerts",
                "webhook": "http://localhost:8000/monitoring/alerts"
            }
        }
        
        with open(alert_file, 'w') as f:
            json.dump(alert_data, f, indent=2)
        
        logger.info("Alert thresholds configured", config_file=alert_file)
        
        return alert_data
    
    async def generate_usage_report(self) -> Dict[str, Any]:
        """Generate usage report template"""
        
        report_template = {
            "report_type": "usage_summary",
            "generated_at": datetime.utcnow().isoformat(),
            "timeframe": {
                "start": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "end": datetime.utcnow().isoformat()
            },
            "metrics": {
                "total_requests": "To be populated from Langfuse",
                "unique_users": "To be populated from Langfuse", 
                "avg_response_time": "To be populated from Langfuse",
                "total_tokens": "To be populated from Langfuse",
                "estimated_cost": "To be populated from Langfuse",
                "error_count": "To be populated from Langfuse",
                "top_questions": "To be populated from Langfuse"
            },
            "langfuse_dashboard_url": f"{self.host}/",
            "instructions": [
                "1. Open Langfuse dashboard at the URL above",
                "2. Navigate to the Traces section",
                "3. Filter by 'ask_question' traces for the desired timeframe", 
                "4. Export or analyze the data as needed",
                "5. Update this report template with actual values"
            ]
        }
        
        report_file = f"./reports/usage_report_{datetime.utcnow().strftime('%Y%m%d')}.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report_template, f, indent=2)
        
        logger.info("Usage report template generated", report_file=report_file)
        
        return report_template
    
    async def run_setup(self) -> Dict[str, Any]:
        """Run complete monitoring setup"""
        
        logger.info("Starting Langfuse monitoring setup")
        
        results = {
            "started_at": datetime.utcnow().isoformat(),
            "langfuse_host": self.host,
            "steps": {}
        }
        
        # Check Langfuse health
        health_ok = await self.check_langfuse_health()
        results["steps"]["health_check"] = {"status": "passed" if health_ok else "failed"}
        
        if not health_ok:
            logger.warning("Langfuse not accessible, proceeding with configuration setup")
        
        # Setup dashboards
        try:
            dashboard_results = await self.setup_monitoring_dashboards()
            results["steps"]["dashboards"] = dashboard_results
        except Exception as e:
            logger.error("Dashboard setup failed", error=str(e))
            results["steps"]["dashboards"] = {"status": "failed", "error": str(e)}
        
        # Setup alerts
        try:
            alert_results = await self.setup_alert_thresholds() 
            results["steps"]["alerts"] = alert_results
        except Exception as e:
            logger.error("Alert setup failed", error=str(e))
            results["steps"]["alerts"] = {"status": "failed", "error": str(e)}
        
        # Generate usage report template
        try:
            report_results = await self.generate_usage_report()
            results["steps"]["usage_report"] = report_results
        except Exception as e:
            logger.error("Usage report generation failed", error=str(e))
            results["steps"]["usage_report"] = {"status": "failed", "error": str(e)}
        
        results["completed_at"] = datetime.utcnow().isoformat()
        
        # Save setup results
        results_file = "./config/monitoring_setup_results.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info("Monitoring setup completed", results_file=results_file)
        
        return results
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


async def main():
    """Main setup function"""
    
    logger.info("Langfuse Monitoring Setup", version="1.0.0")
    
    if not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY:
        logger.warning(
            "Langfuse keys not configured",
            message="Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY environment variables"
        )
    
    async with LangfuseMonitoringSetup(
        host=LANGFUSE_HOST,
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY
    ) as setup:
        
        results = await setup.run_setup()
        
        print("\n" + "="*60)
        print("LANGFUSE MONITORING SETUP COMPLETE")
        print("="*60)
        print(f"Langfuse Dashboard: {LANGFUSE_HOST}")
        print(f"Setup Results: ./config/monitoring_setup_results.json")
        print("\nNext Steps:")
        print("1. Open Langfuse dashboard in your browser")
        print("2. Review the generated dashboard configurations")
        print("3. Import or manually create dashboards based on the configs")
        print("4. Set up alert notifications as needed")
        print("5. Review usage reports regularly")
        print("="*60)
        
        return results


if __name__ == "__main__":
    try:
        results = asyncio.run(main())
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Setup failed", error=str(e), exc_info=True)
        sys.exit(1)