#!/usr/bin/env bash
# Creates GCP log-based metrics for the Climate Impacts MCP server.
# Run once after deploying to Cloud Run:
#   bash gcp/log_metrics.sh <PROJECT_ID>
#
# Prerequisites: gcloud CLI authenticated with Logging Admin role.

set -euo pipefail

PROJECT_ID="${1:?Usage: $0 <GCP_PROJECT_ID>}"
SERVICE="climate-impacts-mcp"

LOG_FILTER='resource.type="cloud_run_revision"
resource.labels.service_name="'"$SERVICE"'"
jsonPayload.tool!=""'

echo "==> Creating log-based metrics in project: $PROJECT_ID"

# 1. Tool call counter (labeled by tool name and success)
echo "  -> mcp/tool_call_count"
gcloud logging metrics create mcp_tool_call_count \
  --project="$PROJECT_ID" \
  --description="Count of MCP tool calls, labeled by tool and success" \
  --log-filter="$LOG_FILTER" \
  --label-extractors='tool=EXTRACT(jsonPayload.tool),success=EXTRACT(jsonPayload.success)' \
  2>/dev/null || echo "     (already exists, skipping)"

# 2. Tool call latency distribution
echo "  -> mcp/tool_call_latency"
gcloud logging metrics create mcp_tool_call_latency \
  --project="$PROJECT_ID" \
  --description="Latency distribution of MCP tool calls in ms" \
  --log-filter="$LOG_FILTER" \
  --label-extractors='tool=EXTRACT(jsonPayload.tool)' \
  --value-extractor='EXTRACT(jsonPayload.duration_ms)' \
  --bucket-options='explicit-buckets="10,25,50,100,250,500,1000,2500,5000,10000"' \
  2>/dev/null || echo "     (already exists, skipping)"

echo ""
echo "==> Done. Metrics will populate as new tool calls are logged."
echo ""
echo "--- Useful Log Explorer queries ---"
echo ""
echo "All tool calls:"
echo '  resource.type="cloud_run_revision"'
echo '  resource.labels.service_name="'"$SERVICE"'"'
echo '  jsonPayload.tool!=""'
echo ""
echo "Failed tool calls:"
echo '  resource.type="cloud_run_revision"'
echo '  resource.labels.service_name="'"$SERVICE"'"'
echo '  jsonPayload.success=false'
echo ""
echo "Specific tool:"
echo '  resource.type="cloud_run_revision"'
echo '  resource.labels.service_name="'"$SERVICE"'"'
echo '  jsonPayload.tool="get_climate_projections"'
echo ""
echo "--- View metrics ---"
echo "  Cloud Console -> Monitoring -> Metrics Explorer"
echo "  Search: logging/user/mcp_tool_call_count"
echo "  Group by: tool"
