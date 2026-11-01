import re
import uuid
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from app.services.llm.base import BaseLLMAdapter
from app.schemas.specs import (
    DashboardSpec, WidgetSpec, WidgetGrid, WidgetChartConfig, DashboardFilter,
    PipelineSpec, PipelineNode, PipelineEdge,
    AppProjectSpec, AppEntity, AppColumn, AppRoute, AppComponent,
    WorkflowSpec, WorkflowNode, WorkflowEdge
)

T = TypeVar("T", bound=BaseModel)

class MockLLMAdapter(BaseLLMAdapter):
    """Fallback LLM adapter for offline testing, demos, or missing API keys."""
    
    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        prompt_lower = prompt.lower()
        if "sql" in prompt_lower or "query" in prompt_lower:
            return "SELECT date_trunc('month', order_date) AS month, sum(amount) AS total_revenue FROM orders GROUP BY 1 ORDER BY 1;"
        if "insight" in prompt_lower or "quality" in prompt_lower:
            return "Data profile reveals strong monthly recurring revenue growth with 98.4% data completeness. Low null rates detected across transactional tables."
        return f"AI Response: Analyzed '{prompt[:60]}...'. All constraints validated successfully."

    async def complete_structured(self, prompt: str, schema: Type[T], system: Optional[str] = None) -> T:
        prompt_lower = prompt.lower()
        
        # Check target schema type
        if schema == DashboardSpec:
            title = "Business Analytics Dashboard"
            if "sales" in prompt_lower or "revenue" in prompt_lower:
                title = "Revenue & Sales Performance"
            elif "churn" in prompt_lower or "customer" in prompt_lower:
                title = "Customer Health & Churn Metrics"

            spec = DashboardSpec(
                id=str(uuid.uuid4()),
                title=title,
                description=f"Generated dashboard from prompt: {prompt[:80]}",
                theme="dark",
                filters=[
                    DashboardFilter(id="filter_date", column="created_at", type="date_range", label="Date Period"),
                    DashboardFilter(id="filter_cat", column="category", type="select", label="Category")
                ],
                widgets=[
                    WidgetSpec(
                        id="widget_kpi_rev",
                        type="kpi",
                        title="Total Revenue",
                        description="Net revenue across all segments",
                        sql="SELECT COALESCE(SUM(amount), 0) AS value FROM data_table;",
                        grid=WidgetGrid(x=0, y=0, w=3, h=2),
                        chartConfig=WidgetChartConfig(valuePrefix="$")
                    ),
                    WidgetSpec(
                        id="widget_kpi_users",
                        type="kpi",
                        title="Active Accounts",
                        description="Unique active customers",
                        sql="SELECT COUNT(DISTINCT customer_id) AS value FROM data_table;",
                        grid=WidgetGrid(x=3, y=0, w=3, h=2)
                    ),
                    WidgetSpec(
                        id="widget_trend",
                        type="line",
                        title="Revenue Trend Over Time",
                        description="Monthly financial trajectory",
                        sql="SELECT strftime(created_at, '%Y-%m') AS date, SUM(amount) AS revenue FROM data_table GROUP BY 1 ORDER BY 1 LIMIT 12;",
                        grid=WidgetGrid(x=0, y=2, w=6, h=4),
                        chartConfig=WidgetChartConfig(xKey="date", yKeys=["revenue"], colorScheme="emerald")
                    ),
                    WidgetSpec(
                        id="widget_breakdown",
                        type="bar",
                        title="Revenue by Category",
                        description="Distribution across product categories",
                        sql="SELECT category, SUM(amount) AS revenue FROM data_table GROUP BY 1 ORDER BY 2 DESC LIMIT 8;",
                        grid=WidgetGrid(x=6, y=2, w=6, h=4),
                        chartConfig=WidgetChartConfig(xKey="category", yKeys=["revenue"], colorScheme="violet")
                    )
                ]
            )
            return spec  # type: ignore

        if schema == PipelineSpec:
            spec = PipelineSpec(
                id=str(uuid.uuid4()),
                name="Automated Ingestion & ETL Pipeline",
                description=f"Pipeline generated for: {prompt[:80]}",
                schedule_cron="0 2 * * *",
                nodes=[
                    PipelineNode(
                        id="node_src",
                        type="source",
                        title="Source Database Extractor",
                        code="-- Read orders from transactional PostgreSQL\nSELECT id, customer_id, amount, status, created_at FROM orders WHERE created_at >= NOW() - INTERVAL '1 day';",
                        config={"connection": "postgres_main", "table": "orders"}
                    ),
                    PipelineNode(
                        id="node_clean",
                        type="transform_sql",
                        title="Data Cleansing & Normalization",
                        code="-- Standardize currency and filter cancelled orders\nSELECT id, customer_id, ROUND(amount, 2) AS clean_amount, created_at\nFROM source_data\nWHERE status != 'cancelled' AND amount > 0;",
                        config={"runtime": "duckdb"}
                    ),
                    PipelineNode(
                        id="node_check",
                        type="quality_check",
                        title="Quality Assertion",
                        code="-- Assert non-null and valid ranges\nSELECT COUNT(*) AS violations FROM clean_data WHERE clean_amount <= 0 OR customer_id IS NULL;",
                        config={"rule": "violations == 0", "severity": "error"}
                    ),
                    PipelineNode(
                        id="node_dest",
                        type="destination",
                        title="Analytics Warehouse Target",
                        code="-- Upsert into analytics table\nINSERT INTO daily_orders_summary SELECT * FROM clean_data;",
                        config={"target_table": "daily_orders_summary"}
                    )
                ],
                edges=[
                    PipelineEdge(source="node_src", target="node_clean"),
                    PipelineEdge(source="node_clean", target="node_check"),
                    PipelineEdge(source="node_check", target="node_dest")
                ]
            )
            return spec  # type: ignore

        if schema == AppProjectSpec:
            spec = AppProjectSpec(
                id=str(uuid.uuid4()),
                name="SaaS Analytics Portal",
                description="Modern full-stack customer dashboard with real-time metrics",
                entities=[
                    AppEntity(
                        name="Customer",
                        table_name="customers",
                        columns=[
                            AppColumn(name="id", type="INTEGER", primary_key=True),
                            AppColumn(name="name", type="TEXT"),
                            AppColumn(name="plan", type="TEXT"),
                            AppColumn(name="monthly_spend", type="REAL")
                        ],
                        seed_count=10
                    )
                ],
                routes=[
                    AppRoute(
                        path="/api/customers",
                        method="GET",
                        handler_name="get_customers",
                        sql_query="SELECT id, name, plan, monthly_spend FROM customers ORDER BY monthly_spend DESC LIMIT 20;",
                        description="Retrieve top spending customers ordered by monthly spend"
                    ),
                    AppRoute(
                        path="/api/customers/stats",
                        method="GET",
                        handler_name="get_customer_stats",
                        sql_query="SELECT COUNT(*) as total_customers, SUM(monthly_spend) as total_mrr, AVG(monthly_spend) as arpu FROM customers;",
                        description="Compute customer aggregates and MRR"
                    )
                ],
                components=[
                    AppComponent(
                        dp_id="comp-stats-card",
                        name="MetricsSummaryCard",
                        file_path="src/components/MetricsSummaryCard.tsx",
                        api_endpoint="/api/customers/stats",
                        handler_ref="get_customer_stats",
                        sql_ref="SELECT COUNT(*) as total_customers, SUM(monthly_spend) as total_mrr, AVG(monthly_spend) as arpu FROM customers;",
                        explanation="Fetches aggregate MRR and active customer count from the database and renders dynamic KPI metric cards with change indicators."
                    ),
                    AppComponent(
                        dp_id="comp-customer-table",
                        name="CustomerLeaderboardTable",
                        file_path="src/components/CustomerLeaderboardTable.tsx",
                        api_endpoint="/api/customers",
                        handler_ref="get_customers",
                        sql_ref="SELECT id, name, plan, monthly_spend FROM customers ORDER BY monthly_spend DESC LIMIT 20;",
                        explanation="Displays paginated table of top customers with badge status, calling the backend customer endpoint with search and sort support."
                    )
                ],
                files={
                    "src/components/MetricsSummaryCard.tsx": """import React, { useEffect, useState } from 'react';

export function MetricsSummaryCard() {
  const [stats, setStats] = useState({ total_customers: 1420, total_mrr: 48900, arpu: 34.43 });

  useEffect(() => {
    fetch('/api/customers/stats')
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(console.error);
  }, []);

  return (
    <div data-dp-id="comp-stats-card" className="grid grid-cols-3 gap-4 p-4 bg-slate-900 rounded-xl border border-slate-800">
      <div className="p-4 bg-slate-800/50 rounded-lg">
        <span className="text-xs text-slate-400">Total Customers</span>
        <div className="text-2xl font-bold text-white mt-1">{stats.total_customers.toLocaleString()}</div>
      </div>
      <div className="p-4 bg-slate-800/50 rounded-lg">
        <span className="text-xs text-slate-400">Monthly Recurring Revenue</span>
        <div className="text-2xl font-bold text-emerald-400 mt-1">${stats.total_mrr.toLocaleString()}</div>
      </div>
      <div className="p-4 bg-slate-800/50 rounded-lg">
        <span className="text-xs text-slate-400">Average Revenue Per User</span>
        <div className="text-2xl font-bold text-indigo-400 mt-1">${stats.arpu.toFixed(2)}</div>
      </div>
    </div>
  );
}""",
                    "src/components/CustomerLeaderboardTable.tsx": """import React, { useEffect, useState } from 'react';

export function CustomerLeaderboardTable() {
  const [customers, setCustomers] = useState([
    { id: 1, name: "Acme Corp", plan: "Enterprise", monthly_spend: 2400 },
    { id: 2, name: "Globex Logistics", plan: "Pro", monthly_spend: 850 },
    { id: 3, name: "Soylent SaaS", plan: "Enterprise", monthly_spend: 3100 },
    { id: 4, name: "Initech Systems", plan: "Starter", monthly_spend: 290 }
  ]);

  useEffect(() => {
    fetch('/api/customers')
      .then(res => res.json())
      .then(data => { if (Array.isArray(data)) setCustomers(data); })
      .catch(console.error);
  }, []);

  return (
    <div data-dp-id="comp-customer-table" className="mt-6 bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center">
        <h3 className="font-semibold text-white">Top Customer Accounts</h3>
        <span className="text-xs text-slate-400">Live API Synchronized</span>
      </div>
      <table className="w-full text-left text-sm text-slate-300">
        <thead className="bg-slate-800/50 text-xs uppercase text-slate-400">
          <tr>
            <th className="px-6 py-3">Account</th>
            <th className="px-6 py-3">Tier</th>
            <th className="px-6 py-3 text-right">Monthly Spend</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {customers.map((c) => (
            <tr key={c.id} className="hover:bg-slate-800/30">
              <td className="px-6 py-4 font-medium text-white">{c.name}</td>
              <td className="px-6 py-4"><span className="px-2 py-1 rounded-full text-xs bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">{c.plan}</span></td>
              <td className="px-6 py-4 text-right font-mono text-emerald-400">${c.monthly_spend.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}""",
                    "server/main.py": """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI(title="Generated App Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def get_db():
    conn = sqlite3.connect("app_data.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/customers")
def get_customers():
    # Database Query: Fetch top 20 customers
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, plan, monthly_spend FROM customers ORDER BY monthly_spend DESC LIMIT 20;")
        rows = [dict(r) for r in cursor.fetchall()]
        return rows

@app.get("/api/customers/stats")
def get_customer_stats():
    # Database Query: Aggregate KPIs
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total_customers, SUM(monthly_spend) as total_mrr, AVG(monthly_spend) as arpu FROM customers;")
        row = cursor.fetchone()
        return dict(row) if row else {"total_customers": 0, "total_mrr": 0, "arpu": 0}
"""
                }
            )
            return spec  # type: ignore

        if schema == WorkflowSpec:
            spec = WorkflowSpec(
                id=str(uuid.uuid4()),
                name="Revenue Drop Investigation Agent",
                description="Monitors daily metrics, detects anomalies, runs SQL diagnosis, and requests human confirmation",
                nodes=[
                    WorkflowNode(
                        id="node_trigger",
                        type="trigger",
                        name="Scheduled Trigger (Weekly)",
                        config={"cron": "0 9 * * 1", "timezone": "UTC"}
                    ),
                    WorkflowNode(
                        id="node_sql",
                        type="tool_call",
                        name="Execute Revenue Check Query",
                        config={"tool": "run_sql_query", "query": "SELECT sum(amount) as current_rev FROM orders WHERE created_at >= date('now', '-7 days');"}
                    ),
                    WorkflowNode(
                        id="node_eval",
                        type="condition",
                        name="Detect >10% Drop",
                        config={"expression": "current_rev < previous_rev * 0.9"}
                    ),
                    WorkflowNode(
                        id="node_llm",
                        type="llm_step",
                        name="LLM Root Cause Synthesis",
                        config={"prompt": "Analyze revenue discrepancy across regions and summarize key drivers."}
                    ),
                    WorkflowNode(
                        id="node_approval",
                        type="human_approval",
                        name="Confirm Outbound Notification",
                        config={"question": "Approve sending executive incident report via Email/Slack?"}
                    ),
                    WorkflowNode(
                        id="node_output",
                        type="output",
                        name="Dispatch Notification Alert",
                        config={"channel": "slack", "recipient": "#analytics-alerts"}
                    )
                ],
                edges=[
                    WorkflowEdge(source="node_trigger", target="node_sql"),
                    WorkflowEdge(source="node_sql", target="node_eval"),
                    WorkflowEdge(source="node_eval", target="node_llm", condition_label="Drop Detected"),
                    WorkflowEdge(source="node_llm", target="node_approval"),
                    WorkflowEdge(source="node_approval", target="node_output", condition_label="Approved")
                ]
            )
            return spec  # type: ignore

        # Fallback default empty schema instantiate
        return schema()
