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

HOOK_INPUT=$(cat)
INPUT_SESSION_ID=$(json_extract_string_field "$HOOK_INPUT" "session_id")
if [ -n "$INPUT_SESSION_ID" ]; then
    export PI_SESSION_ID="$INPUT_SESSION_ID"
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NODE_ID=$(generate_node_id)
SESSION_ID=$(get_session_id)

PROMPT_TEXT=$(json_extract_string_field "$HOOK_INPUT" "prompt")
PROMPT_SUMMARY=$(summarize_text "$PROMPT_TEXT" 180)
PROMPT_WORDS=$(word_count "$PROMPT_TEXT")
SCENE="${PI_SCENE:-user_interaction}"
BATTLE_LEVEL="${PI_BATTLE_LEVEL:-1}"
DIFFICULTY=$(difficulty_for_level "$BATTLE_LEVEL")
FAILURE_COUNT="${PI_FAILURE_COUNT:-0}"
INTERACTION_MODE="${PI_INTERACTION_MODE:-}"

if [ -z "$PROMPT_SUMMARY" ]; then
    PROMPT_SUMMARY="Human input"
fi

JSON_PAYLOAD="{\"node_id\": $(json_escape "$NODE_ID"), \"session_id\": $(json_escape "$SESSION_ID"), \"timestamp\": $(json_escape "$TIMESTAMP"), \"label\": $(json_escape "$PROMPT_SUMMARY"), \"category\": \"interaction\", \"decision_point\": \"human.input\", \"scene\": $(json_escape "$SCENE"), \"difficulty\": $(json_escape "$DIFFICULTY"), \"battle_level\": $(json_number_or_zero "$BATTLE_LEVEL"), \"failure_count\": $(json_number_or_zero "$FAILURE_COUNT"), \"retry_count\": $(json_number_or_zero "$FAILURE_COUNT"), \"agent_id\": \"human\", \"payload\": {\"prompt_summary\": $(json_escape "$PROMPT_SUMMARY"), \"word_count\": $(json_number_or_zero "$PROMPT_WORDS"), \"interaction_point\": \"user_prompt_submit\", \"scene_snapshot\": $(json_escape "$SCENE"), \"interaction_mode\": $(json_escape "$INTERACTION_MODE")}, \"privacy_level\": \"redacted\", \"outcome\": \"pending\", \"children_node_ids\": []}"

append_event_jsonl "$JSON_PAYLOAD"
log_debug " captured prompt input: $NODE_ID"
