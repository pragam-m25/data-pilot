import { z } from "zod";

// --- Module A: Dataset & Profiling ---
export const ColumnProfileSchema = z.object({
  name: z.string(),
  type: z.string(),
  null_count: z.number(),
  null_percentage: z.number(),
  distinct_count: z.number(),
  sample_values: z.array(z.any()),
  min: z.any().optional(),
  max: z.any().optional(),
  mean: z.number().optional(),
  std: z.number().optional(),
});

export const DatasetProfileSchema = z.object({
  row_count: z.number(),
  column_count: z.number(),
  columns: z.array(ColumnProfileSchema),
  correlations: z.record(z.record(z.number())).optional(),
  summary_insights: z.array(z.string()).default([]),
  suggested_questions: z.array(z.string()).default([]),
});

export const CleaningStepSchema = z.object({
  id: z.string(),
  action: z.enum(["drop_duplicates", "drop_nulls", "fill_nulls", "cast_type", "rename_column", "filter_rows"]),
  params: z.record(z.any()),
  description: z.string(),
});

// --- Module B: Dashboard Specification ---
export const WidgetSpecSchema = z.object({
  id: z.string(),
  type: z.enum(["kpi", "line", "bar", "pie", "area", "table", "scatter"]),
  title: z.string(),
  description: z.string().optional(),
  sql: z.string(),
  grid: z.object({
    x: z.number(),
    y: z.number(),
    w: z.number(),
    h: z.number(),
  }),
  chartConfig: z.object({
    xKey: z.string().optional(),
    yKeys: z.array(z.string()).optional(),
    colorScheme: z.string().optional(),
    valuePrefix: z.string().optional(),
    valueSuffix: z.string().optional(),
  }).optional(),
});

export const DashboardSpecSchema = z.object({
  id: z.string().optional(),
  title: z.string(),
  description: z.string().optional(),
  dataset_id: z.string().optional(),
  theme: z.string().default("dark"),
  filters: z.array(z.object({
    id: z.string(),
    column: z.string(),
    type: z.enum(["date_range", "select", "search"]),
    label: z.string(),
  })).default([]),
  widgets: z.array(WidgetSpecSchema),
});

// --- Module C: Database Connections & Query ---
export const ConnectionSpecSchema = z.object({
  id: z.string(),
  name: z.string(),
  dialect: z.enum(["postgresql", "mysql", "sqlite", "mongodb", "bigquery", "snowflake"]),
  is_read_only: z.boolean().default(true),
  tables_count: z.number().optional(),
});

export const QueryResultSchema = z.object({
  query: z.string(),
  columns: z.array(z.string()),
  rows: z.array(z.record(z.any())),
  execution_time_ms: z.number(),
  row_count: z.number(),
  explanation: z.string().optional(),
  suggested_chart: z.object({
    type: z.enum(["kpi", "line", "bar", "pie", "table"]),
    xKey: z.string().optional(),
    yKey: z.string().optional(),
  }).optional(),
});

// --- Module D: Pipelines ---
export const PipelineNodeSchema = z.object({
  id: z.string(),
  type: z.enum(["source", "transform_sql", "transform_python", "quality_check", "destination"]),
  title: z.string(),
  code: z.string().optional(),
  config: z.record(z.any()).default({}),
});

export const PipelineEdgeSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
});

export const PipelineSpecSchema = z.object({
  id: z.string().optional(),
  name: z.string(),
  description: z.string().optional(),
  schedule_cron: z.string().optional(),
  nodes: z.array(PipelineNodeSchema),
  edges: z.array(PipelineEdgeSchema),
});

// --- Module E: App Project with Inspector ---
export const AppEntitySchema = z.object({
  name: z.string(),
  table_name: z.string(),
  columns: z.array(z.object({
    name: z.string(),
    type: z.string(),
    primary_key: z.boolean().optional(),
  })),
  seed_count: z.number().default(10),
});

export const AppRouteSchema = z.object({
  path: z.string(),
  method: z.enum(["GET", "POST", "PUT", "DELETE"]),
  handler_name: z.string(),
  sql_query: z.string(),
  description: z.string(),
});

export const AppComponentSchema = z.object({
  dp_id: z.string(),
  name: z.string(),
  file_path: z.string(),
  api_endpoint: z.string().optional(),
  handler_ref: z.string().optional(),
  sql_ref: z.string().optional(),
  explanation: z.string().optional(),
});

export const AppProjectSpecSchema = z.object({
  id: z.string().optional(),
  name: z.string(),
  description: z.string(),
  entities: z.array(AppEntitySchema),
  routes: z.array(AppRouteSchema),
  components: z.array(AppComponentSchema),
  files: z.record(z.string()).default({}),
});

// --- Module F: Agentic Workflows ---
export const WorkflowNodeSchema = z.object({
  id: z.string(),
  type: z.enum(["trigger", "llm_step", "tool_call", "condition", "human_approval", "output"]),
  name: z.string(),
  config: z.record(z.any()).default({}),
});

export const WorkflowEdgeSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  condition_label: z.string().optional(),
});

export const WorkflowSpecSchema = z.object({
  id: z.string().optional(),
  name: z.string(),
  description: z.string().optional(),
  nodes: z.array(WorkflowNodeSchema),
  edges: z.array(WorkflowEdgeSchema),
});

// TypeScript Inferred Types
export type ColumnProfile = z.infer<typeof ColumnProfileSchema>;
export type DatasetProfile = z.infer<typeof DatasetProfileSchema>;
export type CleaningStep = z.infer<typeof CleaningStepSchema>;
export type WidgetSpec = z.infer<typeof WidgetSpecSchema>;
export type DashboardSpec = z.infer<typeof DashboardSpecSchema>;
export type ConnectionSpec = z.infer<typeof ConnectionSpecSchema>;
export type QueryResult = z.infer<typeof QueryResultSchema>;
export type PipelineNode = z.infer<typeof PipelineNodeSchema>;
export type PipelineEdge = z.infer<typeof PipelineEdgeSchema>;
export type PipelineSpec = z.infer<typeof PipelineSpecSchema>;
export type AppProjectSpec = z.infer<typeof AppProjectSpecSchema>;
export type AppComponent = z.infer<typeof AppComponentSchema>;
export type WorkflowNode = z.infer<typeof WorkflowNodeSchema>;
export type WorkflowEdge = z.infer<typeof WorkflowEdgeSchema>;
export type WorkflowSpec = z.infer<typeof WorkflowSpecSchema>;
