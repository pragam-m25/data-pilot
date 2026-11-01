from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# --- Module A: Dataset & Profiling ---
class ColumnProfile(BaseModel):
    name: str
    type: str
    null_count: int = 0
    null_percentage: float = 0.0
    distinct_count: int = 0
    sample_values: List[Any] = []
    min: Optional[Any] = None
    max: Optional[Any] = None
    mean: Optional[float] = None
    std: Optional[float] = None

class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    columns: List[ColumnProfile]
    correlations: Optional[Dict[str, Dict[str, float]]] = None
    summary_insights: List[str] = []
    suggested_questions: List[str] = []

class CleaningStep(BaseModel):
    id: str
    action: Literal["drop_duplicates", "drop_nulls", "fill_nulls", "cast_type", "rename_column", "filter_rows"]
    params: Dict[str, Any] = {}
    description: str

# --- Module B: Dashboard Specification ---
class WidgetGrid(BaseModel):
    x: int
    y: int
    w: int
    h: int

class WidgetChartConfig(BaseModel):
    xKey: Optional[str] = None
    yKeys: Optional[List[str]] = None
    colorScheme: Optional[str] = "indigo"
    valuePrefix: Optional[str] = ""
    valueSuffix: Optional[str] = ""

class WidgetSpec(BaseModel):
    id: str
    type: Literal["kpi", "line", "bar", "pie", "area", "table", "scatter"]
    title: str
    description: Optional[str] = None
    sql: str
    grid: WidgetGrid
    chartConfig: Optional[WidgetChartConfig] = None

class DashboardFilter(BaseModel):
    id: str
    column: str
    type: Literal["date_range", "select", "search"]
    label: str

class DashboardSpec(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    dataset_id: Optional[str] = None
    theme: str = "dark"
    filters: List[DashboardFilter] = []
    widgets: List[WidgetSpec] = []

# --- Module C: Database Connections & Query ---
class ConnectionSpec(BaseModel):
    id: str
    name: str
    dialect: Literal["postgresql", "mysql", "sqlite", "mongodb", "bigquery", "snowflake"]
    is_read_only: bool = True
    tables_count: Optional[int] = 0

class QueryResult(BaseModel):
    query: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    execution_time_ms: float
    row_count: int
    explanation: Optional[str] = None
    suggested_chart: Optional[Dict[str, Any]] = None

# --- Module D: Pipelines ---
class PipelineNode(BaseModel):
    id: str
    type: Literal["source", "transform_sql", "transform_python", "quality_check", "destination"]
    title: str
    code: Optional[str] = None
    config: Dict[str, Any] = {}

class PipelineEdge(BaseModel):
    source: str
    target: str

class PipelineSpec(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    schedule_cron: Optional[str] = None
    nodes: List[PipelineNode] = []
    edges: List[PipelineEdge] = []

# --- Module E: App Project with Inspector ---
class AppColumn(BaseModel):
    name: str
    type: str
    primary_key: Optional[bool] = False

class AppEntity(BaseModel):
    name: str
    table_name: str
    columns: List[AppColumn]
    seed_count: int = 10

class AppRoute(BaseModel):
    path: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    handler_name: str
    sql_query: str
    description: str

class AppComponent(BaseModel):
    dp_id: str
    name: str
    file_path: str
    api_endpoint: Optional[str] = None
    handler_ref: Optional[str] = None
    sql_ref: Optional[str] = None
    explanation: Optional[str] = None

class AppProjectSpec(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    entities: List[AppEntity] = []
    routes: List[AppRoute] = []
    components: List[AppComponent] = []
    files: Dict[str, str] = {}

# --- Module F: Agentic Workflows ---
class WorkflowNode(BaseModel):
    id: str
    type: Literal["trigger", "llm_step", "tool_call", "condition", "human_approval", "output"]
    name: str
    config: Dict[str, Any] = {}

class WorkflowEdge(BaseModel):
    source: str
    target: str
    condition_label: Optional[str] = None

class WorkflowSpec(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    nodes: List[WorkflowNode] = []
    edges: List[WorkflowEdge] = []
