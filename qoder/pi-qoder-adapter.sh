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

# PI Qoder Adapter
# Wraps a command to capture its execution context for PI visualization.

PI_ROOT="${HOME}/.pi"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="${SCRIPT_DIR}/../hooks"

# Ensure hooks exist and load shared utilities for escaping
if [ ! -d "$HOOKS_DIR" ]; then
    echo "Error: PI hooks directory not found at $HOOKS_DIR"
    exit 1
fi

if [ -f "$HOOKS_DIR/pi-shared.sh" ]; then
    source "$HOOKS_DIR/pi-shared.sh"
else
    echo "Error: pi-shared.sh not found in $HOOKS_DIR"
    exit 1
fi

# Create session if needed
if [ -z "$PI_SESSION_ID" ]; then
    export PI_SESSION_ID="qoder-$(date +%s)"
fi

echo "🔮 PI Qoder Adapter: Session $PI_SESSION_ID"

# Run the command and capture exit code
"$@"
EXIT_CODE=$?
if [ "$EXIT_CODE" -eq 0 ]; then
    OUTCOME="success"
else
    OUTCOME="failure"
fi

# Capture decision/outcome safely
# We construct a JSON object using safe escaping from pi-shared.sh

# 1. Sanitize and escape the command string
RAW_COMMAND="$*"
SANITIZED_COMMAND=$(sanitize_text "$RAW_COMMAND")
ESCAPED_COMMAND=$(json_escape "$SANITIZED_COMMAND")

# 2. Escape other fields
ESCAPED_SESSION_ID=$(json_escape "$PI_SESSION_ID")
LABEL="Qoder Command: $(summarize_text "$SANITIZED_COMMAND" 40)"
ESCAPED_LABEL=$(json_escape "$LABEL")
ESCAPED_OUTCOME=$(json_escape "$OUTCOME")
ESCAPED_EXIT_CODE=$(json_escape "$EXIT_CODE")

# 3. Construct the JSON payload for the hook
# Note: The payload field is itself a JSON object string, or just a structure we want to pass.
# Here we pass a simple object.
DECISION_JSON="{\"session_id\": $ESCAPED_SESSION_ID, \"label\": $ESCAPED_LABEL, \"category\": \"execution\", \"outcome\": $ESCAPED_OUTCOME, \"payload\": {\"command\": $ESCAPED_COMMAND, \"exit_code\": $ESCAPED_EXIT_CODE}}"

# 4. Send to the generic capture hook
# The generic hook will handle final node wrapping and timestamping.
echo "$DECISION_JSON" | "$HOOKS_DIR/capture-generic.sh"

echo "✅ PI: Execution complete. Visualize at: $PI_ROOT/decisions"
exit $EXIT_CODE
