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

# PI Decision Capture Hook
# 触发时机：Session Stop 或 关键决策点
# 功能：捕获当前上下文状态、决策元数据，生成结构化日志

# Load shared utilities
# 假设脚本位于 hooks 目录下，或者 CLAUDE_PLUGIN_ROOT 已设置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/pi-shared.sh" ]; then
    source "${SCRIPT_DIR}/pi-shared.sh"
else
    # Fallback if shared script missing
    echo "Error: pi-shared.sh not found in ${SCRIPT_DIR}" >&2
    exit 1
fi

HOOK_INPUT=$(cat)
INPUT_SESSION_ID=$(json_extract_string_field "$HOOK_INPUT" "session_id")
if [ -n "$INPUT_SESSION_ID" ]; then
    export PI_SESSION_ID="$INPUT_SESSION_ID"
fi

# --- Metadata Collection ---

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NODE_ID=$(generate_node_id)
SESSION_ID=$(get_session_id)

# Try to capture git context (sanitized before persisting to JSONL).
GIT_BRANCH=$(summarize_text "$(git branch --show-current 2>/dev/null || echo "unknown")" 120)
GIT_COMMIT=$(summarize_text "$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")" 60)

# Try to capture recent PI status from environment or logs
# 这里假设 PI 运行时会将状态写入临时文件，或者我们可以从环境变量推断
# 如果没有，使用默认值
SCENE="${PI_SCENE:-unknown}"
BATTLE_LEVEL="${PI_BATTLE_LEVEL:-1}"
FAILURE_COUNT="${PI_FAILURE_COUNT:-0}"
BEAST="${PI_BEAST:-none}"
STRATEGY="${PI_STRATEGY:-default}"
SKILL_NAME="${PI_SKILL_NAME:-pi}"
SKILL_VERSION="${PI_SKILL_VERSION:-20}"
COGNITIVE_MODE="${PI_COGNITIVE_MODE:-}"
INTERACTION_MODE="${PI_INTERACTION_MODE:-}"
CONFIDENCE="${PI_CONFIDENCE:-}"
CLASSICAL_REFERENCE=$(summarize_text "${PI_CLASSICAL_REFERENCE:-}" 120)
THOUGHT_CHAIN=$(summarize_text "${PI_THOUGHT_CHAIN:-}" 200)
SCENE_ANNOUNCEMENT=$(summarize_text "${PI_SCENE_ANNOUNCEMENT:-}" 160)
STATE_SIGNAL=$(summarize_text "${PI_STATE_SIGNAL:-}" 160)
DELIVERY_CONTRACT=$(summarize_text "${PI_DELIVERY_CONTRACT:-}" 160)
HUMAN_INPUT_SUMMARY=$(summarize_text "${PI_HUMAN_INPUT_SUMMARY:-}" 160)
ASSISTANT_QUESTION=$(summarize_text "${PI_ASSISTANT_QUESTION:-}" 160)
USER_DECISION=$(summarize_text "${PI_USER_DECISION:-}" 120)
RESONANCE_FORMS="${PI_RESONANCE_FORMS:-}"

# Decision Category inference
# 如果是 Stop hook，通常意味着 delivery 或 intercept
CATEGORY="delivery" 
if [ "$FAILURE_COUNT" -gt 0 ]; then
    CATEGORY="battle"
fi

BATTLE_LEVEL_JSON=$(json_number_or_zero "$BATTLE_LEVEL")
FAILURE_COUNT_JSON=$(json_number_or_zero "$FAILURE_COUNT")
DIFFICULTY_JSON=$(difficulty_for_level "$BATTLE_LEVEL_JSON")
MODEL_NAME=$(current_model_name)
MODEL_PROVIDER=$(current_model_provider)
MODEL_INPUT_TOKENS=$(current_input_tokens)
MODEL_OUTPUT_TOKENS=$(current_output_tokens)
MODEL_CACHED_INPUT_TOKENS=$(current_cached_input_tokens)
MODEL_REASONING_TOKENS=$(current_reasoning_tokens)
MODEL_TOOL_TOKENS=$(current_tool_tokens)
MODEL_ESTIMATED_COST=$(current_estimated_cost_usd)

if [ -z "$THOUGHT_CHAIN" ]; then
    THOUGHT_CHAIN=$(summarize_text "场景 ${SCENE} · 难度 ${DIFFICULTY_JSON} · 战势 ${BATTLE_LEVEL_JSON} · 策略 ${STRATEGY} · 灵兽 ${BEAST}" 200)
fi
if [ -z "$SCENE_ANNOUNCEMENT" ]; then
    SCENE_ANNOUNCEMENT=$(summarize_text "🧠 PI · ${SCENE} · ${DIFFICULTY_JSON}" 120)
fi
if [ -z "$RESONANCE_FORMS" ]; then
    RESONANCE_FORMS="transparent_chain"
    if [ -n "$STATE_SIGNAL" ]; then
        RESONANCE_FORMS="${RESONANCE_FORMS},state_signal"
    fi
    if [ -n "$DELIVERY_CONTRACT" ] || [ -n "$ASSISTANT_QUESTION" ]; then
        RESONANCE_FORMS="${RESONANCE_FORMS},delivery_contract"
    fi
fi

JSON_PAYLOAD="{\"node_id\": $(json_escape "$NODE_ID"), \"session_id\": $(json_escape "$SESSION_ID"), \"timestamp\": $(json_escape "$TIMESTAMP"), \"label\": $(json_escape "$SCENE_ANNOUNCEMENT"), \"category\": $(json_escape "$CATEGORY"), \"decision_point\": \"session.stop\", \"scene\": $(json_escape "$SCENE"), \"difficulty\": $(json_escape "$DIFFICULTY_JSON"), \"battle_level\": ${BATTLE_LEVEL_JSON}, \"failure_count\": ${FAILURE_COUNT_JSON}, \"agent_id\": \"pi\", \"payload\": {\"beast\": $(json_escape "$BEAST"), \"strategy\": $(json_escape "$STRATEGY"), \"git_context\": {\"branch\": $(json_escape "$GIT_BRANCH"), \"commit\": $(json_escape "$GIT_COMMIT")}, \"pi_context\": {\"skill_name\": $(json_escape "$SKILL_NAME"), \"skill_version\": $(json_escape "$SKILL_VERSION"), \"scene_announcement\": $(json_escape "$SCENE_ANNOUNCEMENT"), \"thought_chain_summary\": $(json_escape "$THOUGHT_CHAIN"), \"cognitive_mode\": $(json_escape "$COGNITIVE_MODE"), \"interaction_mode\": $(json_escape "$INTERACTION_MODE"), \"confidence\": $(json_escape "$CONFIDENCE"), \"classical_reference\": $(json_escape "$CLASSICAL_REFERENCE"), \"state_signal\": $(json_escape "$STATE_SIGNAL"), \"delivery_contract\": $(json_escape "$DELIVERY_CONTRACT"), \"resonance_forms\": $(json_escape "$RESONANCE_FORMS")}, \"human_context\": {\"input_summary\": $(json_escape "$HUMAN_INPUT_SUMMARY"), \"assistant_question\": $(json_escape "$ASSISTANT_QUESTION"), \"user_decision\": $(json_escape "$USER_DECISION")}, \"model_context\": {\"name\": $(json_escape "$MODEL_NAME"), \"provider\": $(json_escape "$MODEL_PROVIDER"), \"input_tokens\": $(json_number_or_zero "$MODEL_INPUT_TOKENS"), \"output_tokens\": $(json_number_or_zero "$MODEL_OUTPUT_TOKENS"), \"cached_input_tokens\": $(json_number_or_zero "$MODEL_CACHED_INPUT_TOKENS"), \"reasoning_tokens\": $(json_number_or_zero "$MODEL_REASONING_TOKENS"), \"tool_tokens\": $(json_number_or_zero "$MODEL_TOOL_TOKENS"), \"estimated_cost_usd\": $(json_decimal_or_zero "$MODEL_ESTIMATED_COST")}}, \"privacy_level\": \"redacted\", \"outcome\": \"pending\", \"children_node_ids\": []}"

# Write to JSONL file
append_event_jsonl "$JSON_PAYLOAD"

# Logging for debugging
log_debug " captured decision: $NODE_ID ($CATEGORY)"
