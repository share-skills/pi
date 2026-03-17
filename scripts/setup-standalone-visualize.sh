#!/usr/bin/env bash
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

# Setup PI Standalone Visualizer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh | bash
#   or
#   ./scripts/setup-standalone-visualize.sh

set -euo pipefail

PI_ROOT="${HOME}/.pi"
INSTALL_DIR="${PI_ROOT}/visualize"
SETUP_SCRIPT="${PI_ROOT}/setup-standalone-visualize.sh"
REPO_URL="https://github.com/share-skills/pi.git"
SCRIPT_URL="https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh"

echo "🔮 Setting up PI Standalone Visualizer..."

mkdir -p "$PI_ROOT"

# Ensure mill is installed
if ! command -v mill &> /dev/null; then
    echo "❌ 'mill' is required to build the visualizer." >&2
    echo "Install it first: https://com-lihaoyi.github.io/mill/mill/Intro_to_Mill.html#_installation" >&2
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "❌ 'git' is required to bootstrap or update the standalone visualizer runtime." >&2
    exit 1
fi

# Clone/Update visualize directory
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing installation at $INSTALL_DIR..."
    cd "$INSTALL_DIR"
    git pull
elif [ -d "$INSTALL_DIR" ]; then
    echo "Replacing non-git directory at $INSTALL_DIR with a fresh clone..."
    rm -rf "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    echo "Cloning full PI repository into $INSTALL_DIR..."
    echo "(Note: We use the visualize/ subdirectory, but clone the repo to support updates)"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR/visualize"
mill frontend.standaloneHtml

# Keep a local copy so future runs can re-bootstrap even after `curl | bash`.
CLONED_SETUP_SCRIPT="$INSTALL_DIR/scripts/setup-standalone-visualize.sh"
if [[ -r "$CLONED_SETUP_SCRIPT" && "$CLONED_SETUP_SCRIPT" != "$SETUP_SCRIPT" ]]; then
    cp "$CLONED_SETUP_SCRIPT" "$SETUP_SCRIPT"
elif [[ -n "${BASH_SOURCE[0]:-}" && -r "${BASH_SOURCE[0]}" ]]; then
    SOURCE_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
    if [[ "$SOURCE_SCRIPT" != "$SETUP_SCRIPT" ]]; then
        cp "$SOURCE_SCRIPT" "$SETUP_SCRIPT"
    fi
elif command -v curl >/dev/null 2>&1; then
    curl -fsSL "$SCRIPT_URL" -o "$SETUP_SCRIPT"
else
    echo "❌ Unable to persist $SETUP_SCRIPT because this run has no readable source file and 'curl' is unavailable." >&2
    exit 1
fi
chmod +x "$SETUP_SCRIPT"

# Create wrapper script
WRAPPER_SCRIPT="${PI_ROOT}/visualize.sh"
cat <<EOF > "$WRAPPER_SCRIPT"
#!/usr/bin/env bash
set -euo pipefail

PI_ROOT="\${HOME}/.pi"
INSTALL_DIR="\${PI_ROOT}/visualize"
SETUP_SCRIPT="\${PI_ROOT}/setup-standalone-visualize.sh"
CLONED_SETUP_SCRIPT="\${INSTALL_DIR}/scripts/setup-standalone-visualize.sh"

if [[ ! -f "\${INSTALL_DIR}/visualize/build.mill" ]]; then
  echo "PI visualizer runtime is not installed yet."
  echo "Bootstrapping standalone visualizer into \${INSTALL_DIR}..."
  if [[ ! -x "\$SETUP_SCRIPT" ]]; then
    if [[ -r "\$CLONED_SETUP_SCRIPT" ]]; then
      echo "Restoring setup script from \${CLONED_SETUP_SCRIPT}..."
      cp "\$CLONED_SETUP_SCRIPT" "\$SETUP_SCRIPT"
      chmod +x "\$SETUP_SCRIPT"
    elif command -v curl >/dev/null 2>&1; then
      echo "Refreshing missing setup script into \$SETUP_SCRIPT..."
      curl -fsSL "$SCRIPT_URL" -o "\$SETUP_SCRIPT"
      chmod +x "\$SETUP_SCRIPT"
    else
      echo "Missing setup script: \$SETUP_SCRIPT" >&2
      exit 1
    fi
  fi
  bash "\$SETUP_SCRIPT"
fi

cd "\${INSTALL_DIR}/visualize"
mill frontend.standaloneHtml >/dev/null
exec mill cli.run "\$@"
EOF
chmod +x "$WRAPPER_SCRIPT"

echo "✅ PI Visualizer setup complete!"
echo "Run it with: $WRAPPER_SCRIPT"
