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

# PI Generic Capture Hook
# Captures arbitrary JSON events from external tools (Qoder, standalone scripts, etc.)
# Usage: echo '{"event": "build_success", "details": "..."}' | ./capture-generic.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/pi-shared.sh" ]; then
    source "${SCRIPT_DIR}/pi-shared.sh"
else
    echo "Error: pi-shared.sh not found" >&2
    exit 1
fi

# Read input
HOOK_INPUT=$(cat)

# Extract or generate session/node IDs
INPUT_SESSION_ID=$(json_extract_string_field "$HOOK_INPUT" "session_id")
if [ -n "$INPUT_SESSION_ID" ]; then
    export PI_SESSION_ID="$INPUT_SESSION_ID"
fi

SESSION_ID=$(get_session_id)
NODE_ID=$(generate_node_id)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Ensure session file exists
if [ ! -f "${SESSION_DIR}/session-${SESSION_ID}.json" ]; then
    init_session_file
fi

# --- Metadata Extraction ---
# Try to extract key fields if the input is JSON, otherwise use defaults.
LABEL=$(json_extract_string_field "$HOOK_INPUT" "label")
if [ -z "$LABEL" ]; then
    # Privacy boundary: never derive labels from arbitrary raw input (may contain secrets).
    LABEL="Generic Event"
fi

CATEGORY=$(json_extract_string_field "$HOOK_INPUT" "category")
if [ -z "$CATEGORY" ]; then CATEGORY="external"; fi

DECISION_POINT=$(json_extract_string_field "$HOOK_INPUT" "decision_point")
if [ -z "$DECISION_POINT" ]; then DECISION_POINT="event.capture"; fi

SCENE=$(json_extract_string_field "$HOOK_INPUT" "scene")
if [ -z "$SCENE" ]; then SCENE="external"; fi

OUTCOME=$(json_extract_string_field "$HOOK_INPUT" "outcome")
if [ -z "$OUTCOME" ]; then OUTCOME="captured"; fi

# We must escape the input carefully for JSON string compatibility.
# The shared helper json_escape handles quotes, newlines, tabs, backslashes.

# Sanitize input for privacy safety
SANITIZED_INPUT=$(sanitize_text "$HOOK_INPUT")
ESCAPED_INPUT=$(json_escape "$SANITIZED_INPUT")

# Manually construct JSON Node
# This structure mimics a decision node so the visualizer can render it as part of the graph.
# We embed the original (sanitized) input as the payload.

JSON_PAYLOAD="{\"node_id\": $(json_escape "$NODE_ID"), \"session_id\": $(json_escape "$SESSION_ID"), \"timestamp\": $(json_escape "$TIMESTAMP"), \"label\": $(json_escape "$LABEL"), \"category\": $(json_escape "$CATEGORY"), \"decision_point\": $(json_escape "$DECISION_POINT"), \"scene\": $(json_escape "$SCENE"), \"difficulty\": \"⚡\", \"battle_level\": 0, \"failure_count\": 0, \"agent_id\": \"external\", \"payload\": $ESCAPED_INPUT, \"privacy_level\": \"redacted\", \"outcome\": $(json_escape "$OUTCOME"), \"children_node_ids\": []}"

# Write to JSONL file (using append_decision_node to treat it as a graph node)
append_decision_node "$JSON_PAYLOAD"

# Logging for debugging
log_debug " captured generic event: $NODE_ID ($LABEL)"
echo "Captured generic event: $NODE_ID"
