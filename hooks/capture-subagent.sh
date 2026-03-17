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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/pi-shared.sh" ]; then
    source "${SCRIPT_DIR}/pi-shared.sh"
else
    echo "Error: pi-shared.sh not found in ${SCRIPT_DIR}" >&2
    exit 1
fi

EVENT_KIND="${1:-start}"
HOOK_INPUT=$(cat)
INPUT_SESSION_ID=$(json_extract_string_field "$HOOK_INPUT" "session_id")
if [ -n "$INPUT_SESSION_ID" ]; then
    export PI_SESSION_ID="$INPUT_SESSION_ID"
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NODE_ID=$(generate_node_id)
SESSION_ID=$(get_session_id)

AGENT_ID=$(json_extract_string_field "$HOOK_INPUT" "agent_id")
AGENT_TYPE=$(json_extract_string_field "$HOOK_INPUT" "agent_type")
PARENT_AGENT_ID=$(json_extract_string_field "$HOOK_INPUT" "parent_agent_id")
DISPLAY_NAME=$(json_extract_string_field "$HOOK_INPUT" "display_name")
AGENT_ROLE=$(infer_role_from_agent_type "$AGENT_TYPE")
SCENE="${PI_SCENE:-team_collaboration}"
BATTLE_LEVEL="${PI_BATTLE_LEVEL:-1}"
DIFFICULTY=$(difficulty_for_level "$BATTLE_LEVEL")
OUTCOME="pending"

# Infer stop outcome from hook input so failed subagents surface as failures in the UI.
infer_subagent_stop_outcome() {
    local hook_input="$1"

    local raw outcome status success_str
    outcome=$(json_extract_string_field "$hook_input" "outcome")
    status=$(json_extract_string_field "$hook_input" "status")
    success_str=$(json_extract_string_field "$hook_input" "success")

    normalize_word() {
        printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[[:space:]]+/_/g'
    }

    raw=$(normalize_word "$outcome")
    case "$raw" in
        success|succeeded|ok|passed|complete|completed) printf 'success'; return 0 ;;
        failure|failed|error|errored) printf 'failure'; return 0 ;;
        cancel|cancelled|canceled|aborted) printf 'cancelled'; return 0 ;;
    esac

    raw=$(normalize_word "$status")
    case "$raw" in
        success|succeeded|ok|passed|complete|completed) printf 'success'; return 0 ;;
        failure|failed|error|errored) printf 'failure'; return 0 ;;
        cancel|cancelled|canceled|aborted) printf 'cancelled'; return 0 ;;
    esac

    raw=$(normalize_word "$success_str")
    case "$raw" in
        true|1|yes) printf 'success'; return 0 ;;
        false|0|no) printf 'failure'; return 0 ;;
    esac

    if printf '%s' "$hook_input" | grep -Eq '"success"[[:space:]]*:[[:space:]]*false'; then
        printf 'failure'
        return 0
    fi
    if printf '%s' "$hook_input" | grep -Eq '"success"[[:space:]]*:[[:space:]]*true'; then
        printf 'success'
        return 0
    fi

    extract_int_field() {
        local field="$1"
        printf '%s' "$hook_input" | sed -nE 's/.*"'"$field"'"[[:space:]]*:[[:space:]]*"?(-?[0-9]+)"?.*/\1/p; q'
    }

    local exit_code
    exit_code=$(extract_int_field "exit_code")
    if [ -z "$exit_code" ]; then
        exit_code=$(extract_int_field "exitCode")
    fi
    if [ -n "$exit_code" ] && [ "$exit_code" != "0" ]; then
        printf 'failure'
        return 0
    fi

    local error_message
    error_message=$(json_extract_string_field "$hook_input" "error")
    if [ -n "$error_message" ]; then
        printf 'failure'
        return 0
    fi

    if printf '%s' "$hook_input" | grep -Eq '"error"[[:space:]]*:[[:space:]]*(\{|\[)'; then
        printf 'failure'
        return 0
    fi

    printf 'success'
}

if [ "$EVENT_KIND" = "stop" ]; then
    OUTCOME=$(infer_subagent_stop_outcome "$HOOK_INPUT")
fi

if [ -z "$AGENT_TYPE" ]; then
    AGENT_TYPE="subagent"
fi

LABEL=$(summarize_text "Subagent ${EVENT_KIND}: ${AGENT_TYPE}" 120)

JSON_PAYLOAD="{\"node_id\": $(json_escape "$NODE_ID"), \"session_id\": $(json_escape "$SESSION_ID"), \"timestamp\": $(json_escape "$TIMESTAMP"), \"label\": $(json_escape "$LABEL"), \"category\": \"team\", \"decision_point\": $(json_escape "subagent.${EVENT_KIND}"), \"scene\": $(json_escape "$SCENE"), \"difficulty\": $(json_escape "$DIFFICULTY"), \"battle_level\": $(json_number_or_zero "$BATTLE_LEVEL"), \"agent_id\": $(json_escape "${AGENT_ID:-$AGENT_TYPE}"), \"payload\": {\"agent_id\": $(json_escape "$AGENT_ID"), \"agent_type\": $(json_escape "$AGENT_TYPE"), \"parent_agent_id\": $(json_escape "$PARENT_AGENT_ID"), \"display_name\": $(json_escape "$DISPLAY_NAME"), \"agent_role\": $(json_escape "$AGENT_ROLE"), \"identity\": $(json_escape "$AGENT_TYPE"), \"event\": $(json_escape "$EVENT_KIND")}, \"privacy_level\": \"redacted\", \"outcome\": $(json_escape "$OUTCOME"), \"children_node_ids\": []}"

append_event_jsonl "$JSON_PAYLOAD"
log_debug " captured subagent ${EVENT_KIND}: ${AGENT_TYPE}"
