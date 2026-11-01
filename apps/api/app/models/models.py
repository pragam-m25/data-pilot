import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), default="User")
    role = Column(String(50), default="member")  # admin, member
    created_at = Column(DateTime, default=utc_now)

    workspaces = relationship("Workspace", back_populates="owner")
    memberships = relationship("WorkspaceMember", back_populates="user")

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    owner = relationship("User", back_populates="workspaces")
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")
    sources = relationship("DataSource", back_populates="workspace", cascade="all, delete-orphan")
    connections = relationship("DatabaseConnection", back_populates="workspace", cascade="all, delete-orphan")
    terms = relationship("BusinessTerm", back_populates="workspace", cascade="all, delete-orphan")
    metrics = relationship("MetricDefinition", back_populates="workspace", cascade="all, delete-orphan")
    rules = relationship("BusinessRule", back_populates="workspace", cascade="all, delete-orphan")
    queries = relationship("QueryHistory", back_populates="workspace", cascade="all, delete-orphan")
    reports = relationship("DashboardReport", back_populates="workspace", cascade="all, delete-orphan")

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role = Column(String(50), default="editor")  # owner, editor, viewer
    created_at = Column(DateTime, default=utc_now)

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="memberships")

class DataSource(Base):
    """Real uploaded files (CSV/XLSX) or connected tables."""
    __tablename__ = "data_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=False)  # csv, xlsx, postgresql
    connection_id = Column(String(36), ForeignKey("database_connections.id"), nullable=True)
    duckdb_table = Column(String(255), nullable=True)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    profile_json = Column(JSON, default=dict)
    quality_checks_json = Column(JSON, default=list)
    status = Column(String(50), default="ready")  # processing, ready, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    workspace = relationship("Workspace", back_populates="sources")
    columns = relationship("DataSourceColumn", back_populates="source", cascade="all, delete-orphan")
    connection = relationship("DatabaseConnection")

class DataSourceColumn(Base):
    __tablename__ = "data_source_columns"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_id = Column(String(36), ForeignKey("data_sources.id"), nullable=False)
    name = Column(String(255), nullable=False)
    inferred_type = Column(String(50), nullable=False)
    position = Column(Integer, default=0)
    null_count = Column(Integer, default=0)
    null_pct = Column(Float, default=0.0)
    distinct_count = Column(Integer, default=0)
    min_val = Column(String(255), nullable=True)
    max_val = Column(String(255), nullable=True)
    mean_val = Column(Float, nullable=True)
    median_val = Column(Float, nullable=True)
    std_val = Column(Float, nullable=True)
    top_values_json = Column(JSON, default=list)
    profile_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    source = relationship("DataSource", back_populates="columns")

class DatabaseConnection(Base):
    """Real external PostgreSQL connection."""
    __tablename__ = "database_connections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    dialect = Column(String(50), default="postgresql")
    host = Column(String(255), nullable=False)
    port = Column(Integer, default=5432)
    database = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    encrypted_password = Column(Text, nullable=False)
    schema_name = Column(String(100), default="public")
    is_read_only = Column(Boolean, default=True)
    schema_cache_json = Column(JSON, default=dict)
    last_tested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    workspace = relationship("Workspace", back_populates="connections")

class BusinessTerm(Base):
    """Business Glossary: terms, definitions, synonyms."""
    __tablename__ = "business_terms"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    definition = Column(Text, nullable=False)
    synonyms_json = Column(JSON, default=list)  # ["gross sales", "total order value"]
    related_table = Column(String(255), nullable=True)
    related_column = Column(String(255), nullable=True)
    owner = Column(String(255), default="Analytics Team")
    status = Column(String(50), default="draft")  # draft, approved
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    workspace = relationship("Workspace", back_populates="terms")

class MetricDefinition(Base):
    """Metrics Layer: approved SQL formulas, grain, time columns, dimensions, versions."""
    __tablename__ = "metric_definitions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    formula_sql = Column(Text, nullable=False)  # e.g. SUM(net_amount) or COUNT(DISTINCT user_id)
    source_tables_json = Column(JSON, default=list)  # ["orders"]
    grain = Column(String(100), default="order")  # order, user, day
    time_column = Column(String(100), nullable=True)  # created_at, paid_at
    timezone = Column(String(50), default="UTC")
    default_filters_json = Column(JSON, default=list)  # [{"column": "status", "op": "!=", "val": "cancelled"}]
    allowed_dimensions_json = Column(JSON, default=list)  # ["region", "plan", "channel"]
    unit = Column(String(50), default="USD")
    currency = Column(String(10), default="$")
    owner = Column(String(255), default="Finance Team")
    status = Column(String(50), default="approved")  # draft, in_review, approved
    version = Column(Integer, default=1)
    parent_id = Column(String(36), nullable=True)  # For version history chains
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    workspace = relationship("Workspace", back_populates="metrics")

class BusinessRule(Base):
    """Business Rules & Targets: thresholds, reporting periods, exceptions."""
    __tablename__ = "business_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(50), default="threshold")  # threshold, exclusion, baseline
    expression = Column(Text, nullable=False)  # e.g. churn_rate < 0.05
    target_metric_id = Column(String(36), ForeignKey("metric_definitions.id"), nullable=True)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=utc_now)

    workspace = relationship("Workspace", back_populates="rules")

class QueryHistory(Base):
    """Traceable query records: question -> metric resolution -> validated SQL -> execution result."""
    __tablename__ = "query_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(String(36), nullable=True)
    question = Column(Text, nullable=False)
    metric_def_id = Column(String(36), ForeignKey("metric_definitions.id"), nullable=True)
    source_id = Column(String(36), ForeignKey("data_sources.id"), nullable=True)
    generated_sql = Column(Text, nullable=False)
    validation_status = Column(String(50), default="valid")  # valid, error, blocked
    validation_errors_json = Column(JSON, default=list)
    status = Column(String(50), default="executed")  # ready, executed, failed, blocked
    result_rows_json = Column(JSON, default=list)
    result_columns_json = Column(JSON, default=list)
    execution_ms = Column(Float, default=0.0)
    row_count = Column(Integer, default=0)
    how_calculated_json = Column(JSON, default=dict)  # {metric_name, version, source, filters, sql, timestamp}
    created_at = Column(DateTime, default=utc_now)

    workspace = relationship("Workspace", back_populates="queries")
    metric = relationship("MetricDefinition")
    source = relationship("DataSource")

class DashboardReport(Base):
    """Saved Reports backed by genuine executed queries."""
    __tablename__ = "dashboard_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(255), default="Analyst")
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    workspace = relationship("Workspace", back_populates="reports")
    widgets = relationship("ReportWidget", back_populates="report", cascade="all, delete-orphan")

class ReportWidget(Base):
    __tablename__ = "report_widgets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("dashboard_reports.id"), nullable=False)
    widget_type = Column(String(50), nullable=False)  # kpi, line, bar, table
    title = Column(String(255), nullable=False)
    query_id = Column(String(36), ForeignKey("query_history.id"), nullable=True)
    metric_def_id = Column(String(36), ForeignKey("metric_definitions.id"), nullable=True)
    chart_config_json = Column(JSON, default=dict)
    grid_json = Column(JSON, default=dict)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)

    report = relationship("DashboardReport", back_populates="widgets")
    query = relationship("QueryHistory")
    metric = relationship("MetricDefinition")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=False)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)
