#!/bin/bash
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Copyright (c) 2026 HePin
#

# PI Tool Result Capture Hook
# 触发时机：PostToolUse (Bash 命令执行后)
# 功能：捕获工具执行结果、耗时、状态码，用于分析执行效率和失败模式

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/pi-shared.sh" ]; then
    source "${SCRIPT_DIR}/pi-shared.sh"
else
    echo "Error: pi-shared.sh not found in ${SCRIPT_DIR}" >&2
    exit 1
fi

HOOK_VARIANT="${1:-success}"
HOOK_INPUT=$(cat)
INPUT_SESSION_ID=$(json_extract_string_field "$HOOK_INPUT" "session_id")
if [ -n "$INPUT_SESSION_ID" ]; then
    export PI_SESSION_ID="$INPUT_SESSION_ID"
fi

# --- Metadata Collection ---

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NODE_ID=$(generate_node_id)
SESSION_ID=$(get_session_id)

TOOL_NAME="${COPILOT_TOOL_NAME:-$(json_extract_string_field "$HOOK_INPUT" "tool_name")}"
if [ -z "$TOOL_NAME" ]; then
    TOOL_NAME="bash"
fi
EXIT_CODE="${COPILOT_TOOL_EXIT_CODE:-}"
if [ -z "$EXIT_CODE" ]; then
    if [ "$HOOK_VARIANT" = "failure" ]; then
        EXIT_CODE="1"
    else
        EXIT_CODE="0"
    fi
fi
DURATION_MS="${COPILOT_TOOL_DURATION_MS:-0}"
EXIT_CODE=$(json_number_or_zero "$EXIT_CODE")
DURATION_MS=$(json_number_or_zero "$DURATION_MS")
OUTPUT_SUMMARY="${COPILOT_TOOL_OUTPUT_SUMMARY:-}"
if [ -n "$OUTPUT_SUMMARY" ]; then
    OUTPUT_SUMMARY=$(summarize_text "$OUTPUT_SUMMARY" 180)
fi

# Fallback: if no specific tool info, optionally try to get last command from history.
# Disabled by default because shell history may contain sensitive arguments.
if [ "$TOOL_NAME" == "bash" ] && [ -z "$OUTPUT_SUMMARY" ] && [ "${PI_CAPTURE_HISTORY_FALLBACK:-0}" = "1" ]; then
    # Try to read last command from history file if available
    # Note: This is best-effort and might not work in all environments
    LAST_CMD=$(history 1 | sed 's/^[ ]*[0-9]*[ ]*//')
    if [ -n "$LAST_CMD" ]; then
        # Sanitize sensitive info from command line
        SANITIZED_CMD=$(sanitize_text "$LAST_CMD")
        OUTPUT_SUMMARY="Command executed: ${SANITIZED_CMD:0:100}..."
    fi
fi

# Determine outcome based on exit code
OUTCOME="success"
if [ "$EXIT_CODE" -ne 0 ]; then
    OUTCOME="failure"
fi

MODEL_NAME=$(current_model_name)
MODEL_PROVIDER=$(current_model_provider)

JSON_PAYLOAD="{\"node_id\": $(json_escape "$NODE_ID"), \"session_id\": $(json_escape "$SESSION_ID"), \"timestamp\": $(json_escape "$TIMESTAMP"), \"label\": $(json_escape "$(summarize_text "${TOOL_NAME} ${OUTCOME}" 96)"), \"category\": \"exec\", \"decision_point\": \"tool.execution\", \"scene\": \"execution\", \"difficulty\": \"⚡\", \"battle_level\": 1, \"failure_count\": $( [ \"$OUTCOME\" = \"failure\" ] && printf '1' || printf '0' ), \"payload\": {\"tool\": $(json_escape "$TOOL_NAME"), \"exit_code\": ${EXIT_CODE}, \"duration_ms\": ${DURATION_MS}, \"summary\": $(json_escape "$OUTPUT_SUMMARY"), \"hook_event\": $(json_escape "$HOOK_VARIANT"), \"model_context\": {\"name\": $(json_escape "$MODEL_NAME"), \"provider\": $(json_escape "$MODEL_PROVIDER"), \"input_tokens\": $(json_number_or_zero "$(current_input_tokens)"), \"output_tokens\": $(json_number_or_zero "$(current_output_tokens)")}}, \"privacy_level\": \"redacted\", \"outcome\": $(json_escape "$OUTCOME"), \"children_node_ids\": []}"

# Write to JSONL file
append_event_jsonl "$JSON_PAYLOAD"

# Logging
log_debug " captured tool result: $TOOL_NAME (exit: $EXIT_CODE)"
