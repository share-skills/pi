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

# PI Shared Shell Utilities
# 提供基础的环境变量获取、Session管理、JSON 构造和隐私脱敏功能

# --- Configuration ---
PI_ROOT="${HOME}/.pi"
DECISIONS_ROOT="${PI_ROOT}/decisions"
TODAY=$(date +%F)
SESSION_DIR="${DECISIONS_ROOT}/${TODAY}"
DEBUG_LOG="${PI_ROOT}/hooks-debug.log"
SESSION_TTL_SECONDS="${PI_SESSION_TTL_SECONDS:-1800}"

# Ensure directories exist
mkdir -p "${SESSION_DIR}"

# --- Logging ---
log_debug() {
    echo "[$(date +%T)] $*" >> "${DEBUG_LOG}"
}

# --- Session Management ---
# 获取或初始化 Session ID
# 优先使用平台提供的真实会话 ID；缺失时按 owner key + TTL 进行回退复用，
# 避免不同会话长期混写到同一个 session 文件。
generate_session_id() {
    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen
    else
        printf '%s-%s\n' "$(date +%s)" "$(od -x /dev/urandom | head -1 | awk '{print $2$3}')"
    fi
}

generate_node_id() {
    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen
    else
        printf '%s-%s-%s\n' "$(date +%s)" "$$" "$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')"
    fi
}

session_owner_key() {
    if [ -n "${PI_SESSION_ID}" ]; then
        echo "env:${PI_SESSION_ID}"
        return
    fi

    if [ -n "${CLAUDE_SESSION_ID}" ]; then
        echo "env:${CLAUDE_SESSION_ID}"
        return
    fi

    if [ -n "${COPILOT_SESSION_ID}" ]; then
        echo "env:${COPILOT_SESSION_ID}"
        return
    fi

    local tty_name
    tty_name=$(tty 2>/dev/null || echo "notty")
    local project_root="${CLAUDE_PLUGIN_ROOT:-${COPILOT_WORKSPACE_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}}"
    if [ "${tty_name}" = "notty" ]; then
        # In non-TTY automation we bias toward isolating concurrent contexts
        # instead of risking multiple sessions being merged into one file.
        echo "fallback:${tty_name}:ppid:${PPID:-0}:root:${project_root}"
    else
        echo "fallback:${tty_name}:root:${project_root}"
    fi
}

write_session_state() {
    local state_file="$1"
    local session_id="$2"
    local owner_key="$3"
    local seen_at="$4"
    printf '%s\t%s\t%s\n' "$session_id" "$owner_key" "$seen_at" > "${state_file}"
}

session_state_file_for_owner() {
    local owner_key="$1"
    local owner_hash
    owner_hash=$(printf '%s' "$owner_key" | cksum | awk '{print $1}')
    printf '%s/current_session_id_%s\n' "${PI_ROOT}" "${owner_hash}"
}

write_session_state_legacy() {
    local session_id="$1"
    local owner_key="$2"
    local seen_at="$3"
    printf '%s\t%s\t%s\n' "$session_id" "$owner_key" "$seen_at" > "${PI_ROOT}/current_session_id"
}

get_session_id() {
    if [ -n "${PI_SESSION_ID}" ]; then
        echo "${PI_SESSION_ID}"
        return
    fi
    
    # Check for Claude/Copilot specific session env vars
    if [ -n "${CLAUDE_SESSION_ID}" ]; then
        echo "${CLAUDE_SESSION_ID}"
        return
    fi

    if [ -n "${COPILOT_SESSION_ID}" ]; then
        echo "${COPILOT_SESSION_ID}"
        return
    fi

    local now owner_key session_state_file legacy_state_file stored_id stored_owner stored_seen age
    now=$(date +%s)
    owner_key=$(session_owner_key)
    session_state_file=$(session_state_file_for_owner "$owner_key")
    legacy_state_file="${PI_ROOT}/current_session_id"

    if [ -f "${session_state_file}" ]; then
        IFS=$'\t' read -r stored_id stored_owner stored_seen < "${session_state_file}"
        if [ -n "${stored_id}" ] && [ -n "${stored_owner}" ] && [ -n "${stored_seen}" ]; then
            age=$((now - stored_seen))
            if [ "${stored_owner}" = "${owner_key}" ] && [ "${age}" -le "${SESSION_TTL_SECONDS}" ]; then
                write_session_state "${session_state_file}" "${stored_id}" "${owner_key}" "${now}"
                echo "${stored_id}"
                return
            fi
        fi
    fi

    if [ -f "${legacy_state_file}" ]; then
        IFS=$'\t' read -r stored_id stored_owner stored_seen < "${legacy_state_file}"
        if [ -n "${stored_id}" ] && [ -n "${stored_owner}" ] && [ -n "${stored_seen}" ]; then
            age=$((now - stored_seen))
            if [ "${stored_owner}" = "${owner_key}" ] && [ "${age}" -le "${SESSION_TTL_SECONDS}" ]; then
                write_session_state "${session_state_file}" "${stored_id}" "${owner_key}" "${now}"
                echo "${stored_id}"
                return
            fi
        fi
    fi

    local new_id
    new_id=$(generate_session_id)
    write_session_state "${session_state_file}" "${new_id}" "${owner_key}" "${now}"
    write_session_state_legacy "${new_id}" "${owner_key}" "${now}"
    echo "${new_id}"
}

SESSION_ID=$(get_session_id)
SESSION_FILE="${SESSION_DIR}/session-${SESSION_ID}.json"

# Initialize session file if not exists
init_session_file() {
    if [ ! -f "${SESSION_FILE}" ]; then
        # Create initial structure
        cat <<EOF > "${SESSION_FILE}"
{
  "session_id": "${SESSION_ID}",
  "date": "${TODAY}",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "summary": "Session started",
  "scene": "unknown",
  "difficulty": "⚡",
  "model_info": {
    "name": "${CLAUDE_MODEL_NAME:-unknown}",
    "provider": "unknown",
    "input_tokens": 0,
    "output_tokens": 0
  },
  "agents": [],
  "nodes": [],
  "metrics": {
    "total_tokens": 0,
    "complexity_score": 0,
    "deep_exploration_count": 0,
    "loop_count": 0,
    "quality_score": 0,
    "max_battle_level": 1,
    "beast_activations": 0
  }
}
EOF
    fi
}

# --- Privacy & Sanitization ---

# 脱敏路径：将用户家目录替换为 ~，将项目根目录替换为 $PROJECT_ROOT
sanitize_path() {
    local path="$1"
    local project_root="${CLAUDE_PLUGIN_ROOT:-$(pwd)}"
    # Replace project root
    path="${path//${project_root}/\$PROJECT_ROOT}"
    # Replace home
    path="${path//${HOME}/~}"
    # Mask obvious sensitive paths (e.g., /Users/xxx, /home/xxx, /root, /tmp, /private)
    path=$(echo "$path" | sed -E 's#/(Users|home|root|private|tmp)/[^/]+#/[REDACTED]#g')
    echo "${path}"
}

# 脱敏敏感关键词
sanitize_text() {
    local text="$1"
    # Privacy boundary: sanitize before persisting to on-disk JSONL or rendering labels.

    # Mask $HOME and project root
    text="${text//${HOME}/~}"
    local project_root="${CLAUDE_PLUGIN_ROOT:-$(pwd)}"
    text="${text//${project_root}/\$PROJECT_ROOT}"

    # Redact common credential flags (space-separated and = forms).
    # Note: value matching intentionally stops at common delimiters (quotes/commas/braces)
    # to avoid corrupting embedded JSON strings.
    text=$(echo "$text" | sed -E 's/(--?(password|pass|passwd|pwd|token|access[-_]?token|refresh[-_]?token|id[-_]?token|secret|api[-_]?key|client[-_]?secret|private[-_]?key|auth|authorization|bearer))=([^[:space:]",}]+)([",}]?)/\1=[REDACTED]\4/gI')
    text=$(echo "$text" | sed -E 's/(--?(password|pass|passwd|pwd|token|access[-_]?token|refresh[-_]?token|id[-_]?token|secret|api[-_]?key|client[-_]?secret|private[-_]?key|auth|authorization|bearer))[[:space:]]+([^[:space:]",}]+)([",}]?)/\1 [REDACTED]\4/gI')

    # Redact key=value / key:value forms.
    text=$(echo "$text" | sed -E 's/((access|refresh|id)[-_]?token|token|secret|password|passwd|api[-_]?key|client[-_]?secret|private[-_]?key)[=:]([^[:space:]",}]+)([",}]?)/\1=[REDACTED]\4/gI')

    # Mask long tokens/keys (20+ alphanum)
    text=$(echo "$text" | sed -E 's/[A-Za-z0-9_\-]{20,}/[REDACTED]/g')
    # Mask obvious sensitive paths
    text=$(echo "$text" | sed -E 's#/(Users|home|root|private|tmp)/[^/]+#/[REDACTED]#g')

    echo "$text"
}

collapse_whitespace() {
    printf '%s' "$1" | tr '\r\n\t' '   ' | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//'
}

truncate_text() {
    local text="$1"
    local limit="${2:-180}"
    if [ "${#text}" -le "${limit}" ]; then
        printf '%s' "$text"
    elif [ "${limit}" -le 1 ]; then
        printf '…'
    else
        printf '%s…' "${text:0:$((limit - 1))}"
    fi
}

summarize_text() {
    local sanitized
    sanitized=$(sanitize_text "$1")
    sanitized=$(collapse_whitespace "$sanitized")
    truncate_text "$sanitized" "${2:-180}"
}

word_count() {
    local text
    text=$(collapse_whitespace "$1")
    if [ -z "$text" ]; then
        printf '0'
    else
        printf '%s\n' "$text" | wc -w | tr -d ' '
    fi
}

current_model_name() {
    printf '%s' "${PI_MODEL_NAME:-${CLAUDE_MODEL_NAME:-${ANTHROPIC_MODEL:-${COPILOT_MODEL_NAME:-${COPILOT_MODEL:-unknown}}}}}"
}

current_model_provider() {
    if [ -n "${PI_MODEL_PROVIDER:-}" ]; then
        printf '%s' "${PI_MODEL_PROVIDER}"
    elif [ -n "${CLAUDE_MODEL_NAME:-}" ] || [ -n "${ANTHROPIC_MODEL:-}" ]; then
        printf 'anthropic'
    elif [ -n "${COPILOT_MODEL_NAME:-}" ] || [ -n "${COPILOT_MODEL:-}" ]; then
        printf 'github'
    else
        printf 'unknown'
    fi
}

current_input_tokens() {
    printf '%s' "${PI_INPUT_TOKENS:-${CLAUDE_INPUT_TOKENS:-${COPILOT_INPUT_TOKENS:-0}}}"
}

current_output_tokens() {
    printf '%s' "${PI_OUTPUT_TOKENS:-${CLAUDE_OUTPUT_TOKENS:-${COPILOT_OUTPUT_TOKENS:-0}}}"
}

current_cached_input_tokens() {
    printf '%s' "${PI_CACHED_INPUT_TOKENS:-${CLAUDE_CACHED_INPUT_TOKENS:-${COPILOT_CACHED_INPUT_TOKENS:-0}}}"
}

current_reasoning_tokens() {
    printf '%s' "${PI_REASONING_TOKENS:-${CLAUDE_REASONING_TOKENS:-${COPILOT_REASONING_TOKENS:-0}}}"
}

current_tool_tokens() {
    printf '%s' "${PI_TOOL_TOKENS:-${CLAUDE_TOOL_TOKENS:-${COPILOT_TOOL_TOKENS:-0}}}"
}

current_estimated_cost_usd() {
    printf '%s' "${PI_ESTIMATED_COST_USD:-${CLAUDE_ESTIMATED_COST_USD:-${COPILOT_ESTIMATED_COST_USD:-0}}}"
}

json_string_to_text() {
    local raw="$1"
    raw=${raw//\\n/ }
    raw=${raw//\\r/ }
    raw=${raw//\\t/ }
    raw=${raw//\\\"/\"}
    raw=${raw//\\\//\/}
    raw=${raw//\\\\/\\}
    printf '%s' "$raw"
}

json_extract_string_field() {
    local json="$1"
    local target="$2"
    local len=${#json}
    local i=0
    local depth=0
    local in_string=0
    local escape_next=0
    local capturing_key=0
    local current=""
    local key=""
    local expect_colon=0
    local expect_string_value=0

    while [ "${i}" -lt "${len}" ]; do
        local ch="${json:$i:1}"
        if [ "${in_string}" -eq 1 ]; then
            if [ "${escape_next}" -eq 1 ]; then
                current+="${ch}"
                escape_next=0
            elif [ "${ch}" = "\\" ]; then
                current+="${ch}"
                escape_next=1
            elif [ "${ch}" = '"' ]; then
                in_string=0
                if [ "${capturing_key}" -eq 1 ]; then
                    key="${current}"
                    capturing_key=0
                    expect_colon=1
                elif [ "${expect_string_value}" -eq 1 ]; then
                    if [ "${key}" = "${target}" ]; then
                        json_string_to_text "${current}"
                        return 0
                    fi
                    expect_string_value=0
                fi
                current=""
            else
                current+="${ch}"
            fi
        else
            case "${ch}" in
                '{'|'[')
                    depth=$((depth + 1))
                    if [ "${expect_string_value}" -eq 1 ]; then
                        expect_string_value=0
                    fi
                    ;;
                '}'|']')
                    if [ "${depth}" -gt 0 ]; then
                        depth=$((depth - 1))
                    fi
                    expect_colon=0
                    expect_string_value=0
                    ;;
                '"')
                    if [ "${expect_string_value}" -eq 1 ]; then
                        in_string=1
                        capturing_key=0
                        current=""
                    elif [ "${depth}" -eq 1 ] && [ "${expect_colon}" -eq 0 ]; then
                        in_string=1
                        capturing_key=1
                        current=""
                    fi
                    ;;
                ':')
                    if [ "${expect_colon}" -eq 1 ]; then
                        expect_colon=0
                        expect_string_value=1
                    fi
                    ;;
                ',')
                    if [ "${depth}" -eq 1 ]; then
                        key=""
                        expect_colon=0
                        expect_string_value=0
                    fi
                    ;;
                ' ' | $'\n' | $'\r' | $'\t')
                    ;;
                *)
                    if [ "${expect_string_value}" -eq 1 ]; then
                        expect_string_value=0
                    fi
                    ;;
            esac
        fi
        i=$((i + 1))
    done

    return 1
}

infer_role_from_agent_type() {
    local agent_type
    agent_type=$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')
    case "$agent_type" in
        *coach*)
            printf 'coach'
            ;;
        *leader*|*manager*)
            printf 'leader'
            ;;
        *)
            printf 'teammate'
            ;;
    esac
}

difficulty_for_level() {
    local battle_level
    battle_level=$(json_number_or_zero "$1")
    if [ "${battle_level}" -gt 4 ]; then
        printf '🐲'
    elif [ "${battle_level}" -gt 2 ]; then
        printf '🧠'
    else
        printf '⚡'
    fi
}

json_escape() {
    local value="$1"
    local escaped="$value"
    escaped=${escaped//\\/\\\\}
    escaped=${escaped//\"/\\\"}
    escaped=${escaped//$'\n'/\\n}
    escaped=${escaped//$'\r'/\\r}
    escaped=${escaped//$'\t'/\\t}
    printf '"%s"' "$escaped"
}

json_number_or_zero() {
    local value="$1"
    if [[ "$value" =~ ^-?[0-9]+$ ]]; then
        printf '%s' "$value"
    else
        printf '0'
    fi
}

# Like json_number_or_zero, but allows decimals/exponents (e.g. 0.05, 1e-3).
# Keep integer-only helper for fields that must remain Int in downstream parsers.
json_decimal_or_zero() {
    local value="$1"
    if [[ "$value" =~ ^-?([0-9]+([.][0-9]+)?|[.][0-9]+)([eE][+-]?[0-9]+)?$ ]]; then
        printf '%s' "$value"
    else
        printf '0'
    fi
}

# --- JSON Helpers ---

# Append a decision node to the nodes array in the JSON file
# Usage: append_decision_node "json_string"
append_decision_node() {
    local node_json="$1"
    if [ ! -f "${SESSION_FILE}" ]; then
        init_session_file
    fi

    # Keep node capture dependency-free by writing the sanitized payload to a sidecar JSONL stream.
    printf '%s\n' "$node_json" >> "${SESSION_DIR}/session-${SESSION_ID}.nodes.jsonl"
}

# Append to a JSONL file (safer fallback)
append_event_jsonl() {
    local json="$1"
    local outfile="${SESSION_DIR}/session-${SESSION_ID}.events.jsonl"
    printf '%s\n' "$json" >> "$outfile"
}
