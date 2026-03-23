#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# PI / Wisdom-in-Action Engine v20 — One-Click Installer
# Supports 16+ AI coding platforms
# Interactive TUI selector: arrow keys to navigate, space to
# toggle, enter to confirm
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PI_REPO_ARCHIVE_URL="${PI_REPO_ARCHIVE_URL:-https://github.com/share-skills/pi/archive/refs/heads/main.tar.gz}"
BOOTSTRAP_TMP_DIR=""
CURSOR_HIDDEN=0

cleanup_bootstrap_dir() {
  if [[ -n "$BOOTSTRAP_TMP_DIR" && -d "$BOOTSTRAP_TMP_DIR" ]]; then
    rm -rf "$BOOTSTRAP_TMP_DIR"
  fi
}

restore_cursor() {
  if [[ "$CURSOR_HIDDEN" == "1" ]]; then
    printf '\033[?25h'
    CURSOR_HIDDEN=0
  fi
}

on_exit() {
  restore_cursor
  cleanup_bootstrap_dir
}

trap on_exit EXIT

repo_assets_present() {
  local dir="$1"
  [[ -f "$dir/install.sh" ]] \
    && [[ -f "$dir/commands/pi.md" ]] \
    && [[ -f "$dir/skills/pi/SKILL.md" ]]
}

ensure_script_dir() {
  if repo_assets_present "$SCRIPT_DIR"; then
    return 0
  fi

  if ! command -v curl >/dev/null 2>&1; then
    echo "install.sh requires curl when running outside a PI checkout." >&2
    exit 1
  fi

  if ! command -v tar >/dev/null 2>&1; then
    echo "install.sh requires tar when bootstrapping PI assets from the release archive." >&2
    exit 1
  fi

  BOOTSTRAP_TMP_DIR="$(mktemp -d)"

  local archive="$BOOTSTRAP_TMP_DIR/pi.tar.gz"
  local extract_root="$BOOTSTRAP_TMP_DIR/extract"
  mkdir -p "$extract_root"
  curl -fsSL "$PI_REPO_ARCHIVE_URL" -o "$archive"
  tar -xzf "$archive" -C "$extract_root"

  local extracted_dir
  extracted_dir="$(find "$extract_root" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
  if [[ -z "$extracted_dir" ]] || ! repo_assets_present "$extracted_dir"; then
    echo "Failed to bootstrap PI installer assets from $PI_REPO_ARCHIVE_URL" >&2
    exit 1
  fi

  SCRIPT_DIR="$extracted_dir"
}

# --- Locale detection ---
detect_lang() {
  local locale="${LANG:-${LC_ALL:-${LC_MESSAGES:-en}}}"
  case "$locale" in
    zh*|ZH*) echo "zh" ;;
    *) echo "en" ;;
  esac
}

LANG_CODE="$(detect_lang)"

# --- i18n messages ---
if [[ "$LANG_CODE" == "zh" ]]; then
  MSG_TITLE="🐲 PI 智行合一引擎 — 一键安装"
  MSG_DETECT="正在检测可用平台..."
  MSG_FOUND="检测到以下平台（↑↓ 移动，空格 选择/取消，a 全选/全不选，回车 确认）："
  MSG_NONE="未检测到任何已知平台。请先安装至少一个支持的 AI 编程工具。"
  MSG_LANG_TITLE="选择语言版本（↑↓ 移动，回车 确认）："
  MSG_EDITION_TITLE="选择 PI 版本（↑↓ 移动，回车 确认）："
  MSG_INSTALLING="正在安装到"
  MSG_DONE="安装完成！"
  MSG_SKIP="跳过（未在仓库中找到对应文件）"
  MSG_COACH_TITLE="是否安装 Agent Team 角色？（↑↓ 移动，回车 确认）："
  MSG_COACH_DONE="Agent Team 文件已安装到"
  MSG_VISUALIZER_READY="可视化启动器已安装到"
  MSG_VISUALIZER_SKIP="跳过可视化启动器（未找到 setup 脚本，且无法自动下载）"
  MSG_SUCCESS="🐲 PI 智行合一引擎安装成功！善战者，致人而不致于人。"
  MSG_INVALID="无效选择，请重新输入"
  MSG_NO_SELECTION="未选择任何平台，退出安装"
  LANG_OPT_1="中文"
  LANG_OPT_2="英文"
  LANG_OPT_3="双语（中文 + 英文）"
  EDITION_OPT_1="原版（完整认知框架，适合大模型）"
  EDITION_OPT_2="渐进式（轻量引导+按需加载，适合上下文敏感场景）"
  EDITION_OPT_3="两个都装"
  COACH_OPT_Y="是，安装 Teammate + Coach"
  COACH_OPT_N="否，跳过"
else
  MSG_TITLE="🐲 PI Wisdom-in-Action Engine — One-Click Install"
  MSG_DETECT="Detecting available platforms..."
  MSG_FOUND="Detected platforms (↑↓ move, Space toggle, a select/deselect all, Enter confirm):"
  MSG_NONE="No known platforms detected. Please install at least one supported AI coding tool first."
  MSG_LANG_TITLE="Select language (↑↓ move, Enter confirm):"
  MSG_EDITION_TITLE="Select PI edition (↑↓ move, Enter confirm):"
  MSG_INSTALLING="Installing to"
  MSG_DONE="Installation complete!"
  MSG_SKIP="Skipped (source files not found in repo)"
  MSG_COACH_TITLE="Install Agent Team roles? (↑↓ move, Enter confirm):"
  MSG_COACH_DONE="Agent Team files installed to"
  MSG_VISUALIZER_READY="Visualizer launcher installed to"
  MSG_VISUALIZER_SKIP="Skipped visualizer launcher (setup script missing and auto-download unavailable)"
  MSG_SUCCESS="🐲 PI Engine installed successfully! Wisdom in Action — control the pace."
  MSG_INVALID="Invalid selection, please try again"
  MSG_NO_SELECTION="No platforms selected, exiting"
  LANG_OPT_1="Chinese"
  LANG_OPT_2="English"
  LANG_OPT_3="Both (Chinese + English)"
  EDITION_OPT_1="Original (full cognitive framework)"
  EDITION_OPT_2="Progressive (lightweight bootstrap + on-demand loading)"
  EDITION_OPT_3="Both"
  COACH_OPT_Y="Yes, install Teammate + Coach"
  COACH_OPT_N="No, skip"
fi

ensure_script_dir

# ============================================================
# TUI Components — pure bash interactive selectors
# ============================================================

# Colors
_C_RESET='\033[0m'
_C_BOLD='\033[1m'
_C_DIM='\033[2m'
_C_CYAN='\033[36m'
_C_GREEN='\033[32m'
_C_YELLOW='\033[33m'

# Read a single keypress, handling escape sequences for arrow keys
_read_key() {
  local key
  IFS= read -rsn1 key < /dev/tty 2>/dev/null || true
  if [[ "$key" == $'\x1b' ]]; then
    local seq
    # Bash 3.2 (macOS default) truncates -t 0.1 to -t 0 (immediate timeout),
    # so we use -t 1 to reliably capture arrow key escape sequences.
    IFS= read -rsn1 -t 1 seq < /dev/tty 2>/dev/null || true
    if [[ "$seq" == "[" ]]; then
      IFS= read -rsn1 -t 1 seq < /dev/tty 2>/dev/null || true
      case "$seq" in
        A) echo "UP" ;;
        B) echo "DOWN" ;;
        C) echo "RIGHT" ;;
        D) echo "LEFT" ;;
        *) echo "OTHER" ;;
      esac
    else
      echo "ESC"
    fi
  elif [[ "$key" == "" ]]; then
    echo "ENTER"
  elif [[ "$key" == " " ]]; then
    echo "SPACE"
  elif [[ "$key" == "a" || "$key" == "A" ]]; then
    echo "ALL"
  elif [[ "$key" == "q" || "$key" == "Q" ]]; then
    echo "QUIT"
  else
    echo "OTHER"
  fi
}

# Multi-select checkbox TUI
# Usage: multiselect result_var "title" option1 option2 ...
# Sets result_var to space-separated indices (0-based) of selected items
multiselect() {
  local _result_var="$1"
  local _title="$2"
  shift 2
  local -a _options=("$@")
  local _count=${#_options[@]}
  local _cursor=0
  local -a _selected=()

  # Initialize all as selected
  for ((i = 0; i < _count; i++)); do
    _selected+=("1")
  done

  # Hide cursor
  printf '\033[?25l'
  CURSOR_HIDDEN=1

  while true; do
    # Move cursor to start and clear lines
    printf '\r'

    # Print title
    printf "${_C_BOLD}${_C_CYAN}%s${_C_RESET}\n" "$_title"

    # Print options
    for ((i = 0; i < _count; i++)); do
      local _check
      if [[ "${_selected[$i]}" == "1" ]]; then
        _check="${_C_GREEN}[x]${_C_RESET}"
      else
        _check="${_C_DIM}[ ]${_C_RESET}"
      fi

      if [[ $i -eq $_cursor ]]; then
        printf "  ${_C_YELLOW}▸${_C_RESET} ${_check} ${_C_BOLD}%s${_C_RESET}\n" "${_options[$i]}"
      else
        printf "    ${_check} %s\n" "${_options[$i]}"
      fi
    done

    # Read key
    local _key
    _key=$(_read_key)

    # Move cursor up to redraw (title + options)
    printf "\033[%dA" $((_count + 1))

    case "$_key" in
      UP)
        ((_cursor > 0)) && ((_cursor--)) || true
        ;;
      DOWN)
        ((_cursor < _count - 1)) && ((_cursor++)) || true
        ;;
      SPACE)
        if [[ "${_selected[$_cursor]}" == "1" ]]; then
          _selected[$_cursor]="0"
        else
          _selected[$_cursor]="1"
        fi
        ;;
      ALL)
        # Toggle all: if any unselected, select all; else deselect all
        local _any_off=0
        for ((i = 0; i < _count; i++)); do
          [[ "${_selected[$i]}" == "0" ]] && _any_off=1
        done
        local _new_val="0"
        [[ $_any_off -eq 1 ]] && _new_val="1"
        for ((i = 0; i < _count; i++)); do
          _selected[$i]="$_new_val"
        done
        ;;
      ENTER)
        # Final redraw
        printf '\r'
        printf "${_C_BOLD}${_C_CYAN}%s${_C_RESET}\n" "$_title"
        for ((i = 0; i < _count; i++)); do
          local _check
          if [[ "${_selected[$i]}" == "1" ]]; then
            _check="${_C_GREEN}[x]${_C_RESET}"
          else
            _check="${_C_DIM}[ ]${_C_RESET}"
          fi
          if [[ $i -eq $_cursor ]]; then
            printf "  ${_C_YELLOW}▸${_C_RESET} ${_check} ${_C_BOLD}%s${_C_RESET}\n" "${_options[$i]}"
          else
            printf "    ${_check} %s\n" "${_options[$i]}"
          fi
        done
        # Collect results
        local _result=""
        for ((i = 0; i < _count; i++)); do
          if [[ "${_selected[$i]}" == "1" ]]; then
            _result+="$i "
          fi
        done
        restore_cursor
        eval "$_result_var='${_result% }'"
        return 0
        ;;
      QUIT)
        restore_cursor
        echo ""
        exit 0
        ;;
    esac
  done
}

# Single-select radio TUI
# Usage: singleselect result_var "title" option1 option2 ...
# Sets result_var to the index (0-based) of the selected item
singleselect() {
  local _result_var="$1"
  local _title="$2"
  shift 2
  local -a _options=("$@")
  local _count=${#_options[@]}
  local _cursor=0

  # Hide cursor
  printf '\033[?25l'
  CURSOR_HIDDEN=1

  while true; do
    printf '\r'
    printf "${_C_BOLD}${_C_CYAN}%s${_C_RESET}\n" "$_title"

    for ((i = 0; i < _count; i++)); do
      local _radio
      if [[ $i -eq $_cursor ]]; then
        _radio="${_C_GREEN}(*)${_C_RESET}"
        printf "  ${_C_YELLOW}▸${_C_RESET} ${_radio} ${_C_BOLD}%s${_C_RESET}\n" "${_options[$i]}"
      else
        _radio="${_C_DIM}( )${_C_RESET}"
        printf "    ${_radio} %s\n" "${_options[$i]}"
      fi
    done

    local _key
    _key=$(_read_key)

    printf "\033[%dA" $((_count + 1))

    case "$_key" in
      UP)
        ((_cursor > 0)) && ((_cursor--)) || true
        ;;
      DOWN)
        ((_cursor < _count - 1)) && ((_cursor++)) || true
        ;;
      ENTER)
        # Final redraw
        printf '\r'
        printf "${_C_BOLD}${_C_CYAN}%s${_C_RESET}\n" "$_title"
        for ((i = 0; i < _count; i++)); do
          local _radio
          if [[ $i -eq $_cursor ]]; then
            _radio="${_C_GREEN}(*)${_C_RESET}"
            printf "  ${_C_YELLOW}▸${_C_RESET} ${_radio} ${_C_BOLD}%s${_C_RESET}\n" "${_options[$i]}"
          else
            _radio="${_C_DIM}( )${_C_RESET}"
            printf "    ${_radio} %s\n" "${_options[$i]}"
          fi
        done
        restore_cursor
        eval "$_result_var=$_cursor"
        return 0
        ;;
      QUIT)
        restore_cursor
        echo ""
        exit 0
        ;;
    esac
  done
}

# ============================================================
# Platform detection & install functions
# ============================================================

declare -a DETECTED=()
VISUALIZER_SETUP_URL="${PI_VISUALIZER_SETUP_URL:-https://raw.githubusercontent.com/share-skills/pi/main/scripts/setup-standalone-visualize.sh}"

# Detection functions
detect_claude_code()  { [[ -d "$HOME/.claude" ]]; }
detect_codex_cli()    { [[ -d "$HOME/.codex" ]] || command -v codex &>/dev/null; }
detect_cursor()       { [[ -d ".cursor" ]] || [[ -d "$HOME/.cursor" ]]; }
detect_kiro()         { [[ -d ".kiro" ]] || [[ -d "$HOME/.kiro" ]]; }
detect_openclaw()     { [[ -d "$HOME/.openclaw" ]] || command -v claw &>/dev/null; }
detect_antigravity()  { [[ -d "$HOME/.gemini/antigravity" ]]; }
detect_opencode()     { [[ -d "$HOME/.config/opencode" ]] || command -v opencode &>/dev/null; }
detect_gemini_cli()   { [[ -d "$HOME/.gemini" ]] || command -v gemini &>/dev/null; }
detect_copilot_cli()  { [[ -d "$HOME/.copilot" ]] || command -v github-copilot-cli &>/dev/null; }
detect_qwen_code()    { [[ -d "$HOME/.qwen" ]] || command -v qwen &>/dev/null; }
detect_qoder_cli()    { [[ -d "$HOME/.qoder" ]] || command -v qoder &>/dev/null; }
detect_iflow()        { [[ -d "$HOME/.iflow" ]] || command -v iflow &>/dev/null; }
detect_copaw()        { [[ -d "$HOME/.copaw" ]] || command -v copaw &>/dev/null; }
detect_trae()         { [[ -d "$HOME/.trae" ]] || [[ -d ".trae" ]] || command -v trae &>/dev/null; }
detect_augment()      { [[ -d "$HOME/.augment" ]] || [[ -d ".augment" ]] || command -v augment &>/dev/null; }
detect_windsurf()     { [[ -d "$HOME/.windsurf" ]] || [[ -d ".windsurf" ]] || command -v windsurf &>/dev/null; }

# Install helper
install_skill_to_dir() {
  local target_dir="$1"
  local source_dir="$2"
  local cn_name="$3"
  local en_name="$4"
  local lang="$5"
  local edition="$6"

  # Clean old files before copying to ensure overwrite
  if [[ "$lang" == "1" || "$lang" == "3" ]]; then
    rm -rf "${target_dir:?}/$cn_name"
    [[ "$edition" == "3" ]] && rm -rf "${target_dir:?}/${cn_name}-progressive"
  fi
  if [[ "$lang" == "2" || "$lang" == "3" ]]; then
    rm -rf "${target_dir:?}/$en_name"
    [[ "$edition" == "3" ]] && rm -rf "${target_dir:?}/${en_name}-progressive"
  fi

  if [[ "$lang" == "1" || "$lang" == "3" ]]; then
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      # Original
      if [[ -f "$source_dir/$cn_name/SKILL.md" ]]; then
        mkdir -p "$target_dir/$cn_name"
        cp "$source_dir/$cn_name/SKILL.md" "$target_dir/$cn_name/SKILL.md"
      fi
    fi
    if [[ "$edition" == "2" ]]; then
      # Progressive only → install as main skill
      if [[ -f "$source_dir/${cn_name}-progressive/SKILL.md" ]]; then
        mkdir -p "$target_dir/$cn_name"
        cp "$source_dir/${cn_name}-progressive/SKILL.md" "$target_dir/$cn_name/SKILL.md"
        if [[ -d "$source_dir/${cn_name}-progressive/references" ]]; then
          cp -r "$source_dir/${cn_name}-progressive/references" "$target_dir/$cn_name/references"
        fi
      fi
    fi
    if [[ "$edition" == "3" ]]; then
      # Both → progressive goes to separate dir
      if [[ -f "$source_dir/${cn_name}-progressive/SKILL.md" ]]; then
        mkdir -p "$target_dir/${cn_name}-progressive"
        cp "$source_dir/${cn_name}-progressive/SKILL.md" "$target_dir/${cn_name}-progressive/SKILL.md"
        if [[ -d "$source_dir/${cn_name}-progressive/references" ]]; then
          cp -r "$source_dir/${cn_name}-progressive/references" "$target_dir/${cn_name}-progressive/references"
        fi
      fi
    fi
  fi
  if [[ "$lang" == "2" || "$lang" == "3" ]]; then
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      # Original
      if [[ -f "$source_dir/$en_name/SKILL.md" ]]; then
        mkdir -p "$target_dir/$en_name"
        cp "$source_dir/$en_name/SKILL.md" "$target_dir/$en_name/SKILL.md"
      fi
    fi
    if [[ "$edition" == "2" ]]; then
      # Progressive only → install as main skill
      if [[ -f "$source_dir/${en_name}-progressive/SKILL.md" ]]; then
        mkdir -p "$target_dir/$en_name"
        cp "$source_dir/${en_name}-progressive/SKILL.md" "$target_dir/$en_name/SKILL.md"
        if [[ -d "$source_dir/${en_name}-progressive/references" ]]; then
          cp -r "$source_dir/${en_name}-progressive/references" "$target_dir/$en_name/references"
        fi
      fi
    fi
    if [[ "$edition" == "3" ]]; then
      # Both → progressive goes to separate dir
      if [[ -f "$source_dir/${en_name}-progressive/SKILL.md" ]]; then
        mkdir -p "$target_dir/${en_name}-progressive"
        cp "$source_dir/${en_name}-progressive/SKILL.md" "$target_dir/${en_name}-progressive/SKILL.md"
        if [[ -d "$source_dir/${en_name}-progressive/references" ]]; then
          cp -r "$source_dir/${en_name}-progressive/references" "$target_dir/${en_name}-progressive/references"
        fi
      fi
    fi
  fi
}

prepare_visualizer_setup_script() {
  local dest="$1"
  local source="$SCRIPT_DIR/scripts/setup-standalone-visualize.sh"

  mkdir -p "$(dirname "$dest")"

  if [[ -f "$source" ]]; then
    cp "$source" "$dest"
  elif command -v curl >/dev/null 2>&1; then
    curl -fsSL "$VISUALIZER_SETUP_URL" -o "$dest"
  else
    return 1
  fi

  chmod +x "$dest"
}

install_visualizer_launcher() {
  local pi_root="$HOME/.pi"
  local setup_script="$pi_root/setup-standalone-visualize.sh"
  local launcher="$pi_root/visualize.sh"

  if ! prepare_visualizer_setup_script "$setup_script"; then
    echo "  $MSG_VISUALIZER_SKIP"
    return 0
  fi

  if ! command -v node >/dev/null 2>&1; then
    if [[ "$LANG_CODE" == "zh" ]]; then
      echo "  ⚠️  未检测到 Node.js。可视化启动器已安装，但首次运行时需要 node 和 npm。"
      echo "     安装 Node.js: https://nodejs.org/"
    else
      echo "  ⚠️  Node.js not detected. Visualizer launcher installed, but node & npm are required on first run."
      echo "     Install Node.js: https://nodejs.org/"
    fi
  fi

  cat > "$launcher" <<EOF
#!/usr/bin/env bash
set -euo pipefail

PI_ROOT="\${HOME}/.pi"
INSTALL_DIR="\${PI_ROOT}/visualize"
SETUP_SCRIPT="\${PI_ROOT}/setup-standalone-visualize.sh"
CLONED_SETUP_SCRIPT="\${INSTALL_DIR}/scripts/setup-standalone-visualize.sh"

if [[ ! -f "\${INSTALL_DIR}/visualize/package.json" ]]; then
  echo "PI visualizer runtime is not installed yet."
  echo "Bootstrapping standalone visualizer into \${INSTALL_DIR}..."
  if [[ ! -x "\$SETUP_SCRIPT" ]]; then
    if [[ -r "\$CLONED_SETUP_SCRIPT" ]]; then
      echo "Restoring setup script from \${CLONED_SETUP_SCRIPT}..."
      cp "\$CLONED_SETUP_SCRIPT" "\$SETUP_SCRIPT"
      chmod +x "\$SETUP_SCRIPT"
    elif command -v curl >/dev/null 2>&1; then
      echo "Refreshing missing setup script into \$SETUP_SCRIPT..."
      curl -fsSL "$VISUALIZER_SETUP_URL" -o "\$SETUP_SCRIPT"
      chmod +x "\$SETUP_SCRIPT"
    else
      echo "Missing setup script: \$SETUP_SCRIPT" >&2
      exit 1
    fi
  fi
  bash "\$SETUP_SCRIPT"
fi

cd "\${INSTALL_DIR}/visualize"
if [[ ! -d "node_modules" ]]; then
  npm install
fi
exec npm run server -- "\$@"
EOF

  chmod +x "$launcher"
  echo "  $MSG_VISUALIZER_READY $launcher"
}

install_claude_code() {
  local lang="$1"
  local edition="$2"
  local target="$HOME/.claude/skills/pi"
  # Clean old install to ensure full overwrite
  rm -rf "${target:?}"
  mkdir -p "$target"
  cp -r "$SCRIPT_DIR/.claude-plugin" "$target/.claude-plugin" 2>/dev/null || true
  if [[ "$lang" == "1" || "$lang" == "3" ]]; then
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      mkdir -p "$target/skills/pi"
      cp "$SCRIPT_DIR/claude-code/pi/SKILL.md" "$target/skills/pi/SKILL.md" 2>/dev/null || true
    fi
    if [[ "$edition" == "2" ]]; then
      # Progressive only → install as main skill
      mkdir -p "$target/skills/pi"
      cp "$SCRIPT_DIR/claude-code/pi-progressive/SKILL.md" "$target/skills/pi/SKILL.md" 2>/dev/null || true
      if [[ -d "$SCRIPT_DIR/claude-code/pi-progressive/references" ]]; then
        cp -r "$SCRIPT_DIR/claude-code/pi-progressive/references" "$target/skills/pi/references" 2>/dev/null || true
      fi
    fi
    if [[ "$edition" == "3" ]]; then
      # Both → progressive goes to separate dir
      mkdir -p "$target/skills/pi-progressive"
      cp "$SCRIPT_DIR/claude-code/pi-progressive/SKILL.md" "$target/skills/pi-progressive/SKILL.md" 2>/dev/null || true
      if [[ -d "$SCRIPT_DIR/claude-code/pi-progressive/references" ]]; then
        cp -r "$SCRIPT_DIR/claude-code/pi-progressive/references" "$target/skills/pi-progressive/references" 2>/dev/null || true
      fi
    fi
  fi
  if [[ "$lang" == "2" || "$lang" == "3" ]]; then
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      mkdir -p "$target/skills/pi-en"
      cp "$SCRIPT_DIR/skills/pi-en/SKILL.md" "$target/skills/pi-en/SKILL.md" 2>/dev/null || true
    fi
    if [[ "$edition" == "2" ]]; then
      # Progressive only → install as main skill
      mkdir -p "$target/skills/pi-en"
      cp "$SCRIPT_DIR/skills/pi-en-progressive/SKILL.md" "$target/skills/pi-en/SKILL.md" 2>/dev/null || true
      if [[ -d "$SCRIPT_DIR/skills/pi-en-progressive/references" ]]; then
        cp -r "$SCRIPT_DIR/skills/pi-en-progressive/references" "$target/skills/pi-en/references" 2>/dev/null || true
      fi
    fi
    if [[ "$edition" == "3" ]]; then
      # Both → progressive goes to separate dir
      mkdir -p "$target/skills/pi-en-progressive"
      cp "$SCRIPT_DIR/skills/pi-en-progressive/SKILL.md" "$target/skills/pi-en-progressive/SKILL.md" 2>/dev/null || true
      if [[ -d "$SCRIPT_DIR/skills/pi-en-progressive/references" ]]; then
        cp -r "$SCRIPT_DIR/skills/pi-en-progressive/references" "$target/skills/pi-en-progressive/references" 2>/dev/null || true
      fi
    fi
  fi
  mkdir -p "$target/agents"
  cp "$SCRIPT_DIR/agents/pi-coach.md" "$target/agents/" 2>/dev/null || true
  cp "$SCRIPT_DIR/agents/pi-coach-en.md" "$target/agents/" 2>/dev/null || true
  cp "$SCRIPT_DIR/agents/pi-teammate.md" "$target/agents/" 2>/dev/null || true
  cp "$SCRIPT_DIR/agents/pi-teammate-en.md" "$target/agents/" 2>/dev/null || true
  if [[ -d "$SCRIPT_DIR/commands" ]]; then
    cp -r "$SCRIPT_DIR/commands" "$target/commands" 2>/dev/null || true
  fi
  echo "  $MSG_INSTALLING $target"
}

install_codex_cli() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.codex/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.codex/skills/"
}

install_cursor() {
  local lang="$1"
  local edition="$2"
  local target=".cursor/rules"
  mkdir -p "$target"
  if [[ "$lang" == "1" || "$lang" == "3" ]]; then
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      [[ -f "$SCRIPT_DIR/cursor/rules/pi.mdc" ]] && cp "$SCRIPT_DIR/cursor/rules/pi.mdc" "$target/pi.mdc"
    fi
    if [[ "$edition" == "2" ]]; then
      # Cursor doesn't support references/, progressive uses full version
      [[ -f "$SCRIPT_DIR/cursor/rules/pi.mdc" ]] && cp "$SCRIPT_DIR/cursor/rules/pi.mdc" "$target/pi.mdc"
    fi
  fi
  if [[ "$lang" == "2" || "$lang" == "3" ]]; then
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      [[ -f "$SCRIPT_DIR/cursor/rules/pi-en.mdc" ]] && cp "$SCRIPT_DIR/cursor/rules/pi-en.mdc" "$target/pi-en.mdc"
    fi
    if [[ "$edition" == "2" ]]; then
      # Cursor doesn't support references/, progressive uses full version
      [[ -f "$SCRIPT_DIR/cursor/rules/pi-en.mdc" ]] && cp "$SCRIPT_DIR/cursor/rules/pi-en.mdc" "$target/pi-en.mdc"
    fi
  fi
  [[ -f "$SCRIPT_DIR/cursor/rules/pi-visualize.mdc" ]] && cp "$SCRIPT_DIR/cursor/rules/pi-visualize.mdc" "$target/pi-visualize.mdc"
  echo "  $MSG_INSTALLING $target"
}

install_kiro() {
  local lang="$1"
  local edition="$2"
  local target=".kiro/steering"
  mkdir -p "$target"
  if [[ "$lang" == "1" || "$lang" == "3" ]]; then
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      [[ -f "$SCRIPT_DIR/kiro/steering/pi.md" ]] && cp "$SCRIPT_DIR/kiro/steering/pi.md" "$target/pi.md"
    fi
    if [[ "$edition" == "2" ]]; then
      # Kiro doesn't support references/, progressive uses full version
      [[ -f "$SCRIPT_DIR/kiro/steering/pi.md" ]] && cp "$SCRIPT_DIR/kiro/steering/pi.md" "$target/pi.md"
    fi
  fi
  if [[ "$lang" == "2" || "$lang" == "3" ]]; then
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      [[ -f "$SCRIPT_DIR/kiro/steering/pi-en.md" ]] && cp "$SCRIPT_DIR/kiro/steering/pi-en.md" "$target/pi-en.md"
    fi
    if [[ "$edition" == "2" ]]; then
      # Kiro doesn't support references/, progressive uses full version
      [[ -f "$SCRIPT_DIR/kiro/steering/pi-en.md" ]] && cp "$SCRIPT_DIR/kiro/steering/pi-en.md" "$target/pi-en.md"
    fi
  fi
  echo "  $MSG_INSTALLING $target"
}

install_openclaw() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.openclaw/skills" "$SCRIPT_DIR/openclaw" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.openclaw/skills/"
}

install_antigravity() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.gemini/antigravity/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.gemini/antigravity/skills/"
}

install_opencode() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.config/opencode/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.config/opencode/skills/"
}

install_gemini_cli() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.gemini/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.gemini/skills/"
}

install_copilot_cli() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.copilot/skills" "$SCRIPT_DIR/copilot-cli" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.copilot/skills/"
}

install_qwen_code() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.qwen/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.qwen/skills/"
}

install_qoder_cli() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.qoder/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.qoder/skills/"
}

install_iflow() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.iflow/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.iflow/skills/"
}

install_copaw() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.copaw/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.copaw/skills/"
}

install_trae() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.trae/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.trae/skills/"
}

install_augment() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.augment/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.augment/skills/"
}

install_windsurf() {
  local lang="$1"
  local edition="$2"
  install_skill_to_dir "$HOME/.windsurf/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
  echo "  $MSG_INSTALLING ~/.windsurf/skills/"
}

# --- Platform registry ---
PLATFORM_NAMES=(
  "Claude Code"
  "Codex CLI"
  "Cursor"
  "Kiro"
  "OpenClaw"
  "Antigravity"
  "OpenCode"
  "Gemini CLI"
  "Copilot CLI"
  "Qwen Code"
  "Qoder"
  "Iflow"
  "COPAW"
  "Trae"
  "Augment"
  "Windsurf"
)

PLATFORM_DETECTORS=(
  detect_claude_code
  detect_codex_cli
  detect_cursor
  detect_kiro
  detect_openclaw
  detect_antigravity
  detect_opencode
  detect_gemini_cli
  detect_copilot_cli
  detect_qwen_code
  detect_qoder_cli
  detect_iflow
  detect_copaw
  detect_trae
  detect_augment
  detect_windsurf
)

PLATFORM_INSTALLERS=(
  install_claude_code
  install_codex_cli
  install_cursor
  install_kiro
  install_openclaw
  install_antigravity
  install_opencode
  install_gemini_cli
  install_copilot_cli
  install_qwen_code
  install_qoder_cli
  install_iflow
  install_copaw
  install_trae
  install_augment
  install_windsurf
)

# ============================================================
# Main flow
# ============================================================

echo ""
echo "============================================"
echo "  $MSG_TITLE"
echo "============================================"
echo ""

# --- Detect platforms ---
echo "$MSG_DETECT"
echo ""

for i in "${!PLATFORM_NAMES[@]}"; do
  if ${PLATFORM_DETECTORS[$i]} 2>/dev/null; then
    DETECTED+=("$i")
  fi
done

if [[ ${#DETECTED[@]} -eq 0 ]]; then
  echo "$MSG_NONE"
  echo ""
  echo "Supported platforms: ${PLATFORM_NAMES[*]}"
  exit 0
fi

# --- Step 1: Select platforms (multi-select) ---
declare -a detected_names=()
for i in "${DETECTED[@]}"; do
  detected_names+=("${PLATFORM_NAMES[$i]}")
done

platform_result=""
multiselect platform_result "$MSG_FOUND" "${detected_names[@]}"
echo ""

# Parse selected indices
declare -a SELECTED=()
if [[ -n "$platform_result" ]]; then
  for idx in $platform_result; do
    SELECTED+=("${DETECTED[$idx]}")
  done
fi

if [[ ${#SELECTED[@]} -eq 0 ]]; then
  echo "$MSG_NO_SELECTION"
  exit 0
fi

# --- Step 2: Select language (single-select) ---
lang_result=0
singleselect lang_result "$MSG_LANG_TITLE" "$LANG_OPT_1" "$LANG_OPT_2" "$LANG_OPT_3"
lang_choice=$((lang_result + 1))
echo ""

# --- Step 3: Select edition (single-select) ---
edition_result=0
singleselect edition_result "$MSG_EDITION_TITLE" "$EDITION_OPT_1" "$EDITION_OPT_2" "$EDITION_OPT_3"
edition_choice=$((edition_result + 1))
echo ""

# --- Step 4: Install ---
echo "--------------------------------------------"
for i in "${SELECTED[@]}"; do
  echo "${PLATFORM_NAMES[$i]}:"
  ${PLATFORM_INSTALLERS[$i]} "$lang_choice" "$edition_choice"
done
install_visualizer_launcher
echo "--------------------------------------------"
echo ""

# --- Step 5: Coach install (single-select) ---
coach_result=0
singleselect coach_result "$MSG_COACH_TITLE" "$COACH_OPT_Y" "$COACH_OPT_N"
echo ""

if [[ $coach_result -eq 0 ]]; then
  coach_dir=".claude/agents"
  # Clean old pi agent files before copying
  rm -f "$coach_dir/pi-teammate.md" "$coach_dir/pi-teammate-en.md" "$coach_dir/pi-coach.md" "$coach_dir/pi-coach-en.md" 2>/dev/null || true
  mkdir -p "$coach_dir"
  if [[ "$lang_choice" == "1" || "$lang_choice" == "3" ]]; then
    cp "$SCRIPT_DIR/agents/pi-teammate.md" "$coach_dir/pi-teammate.md"
    cp "$SCRIPT_DIR/agents/pi-coach.md" "$coach_dir/pi-coach.md"
  fi
  if [[ "$lang_choice" == "2" || "$lang_choice" == "3" ]]; then
    cp "$SCRIPT_DIR/agents/pi-teammate-en.md" "$coach_dir/pi-teammate-en.md"
    cp "$SCRIPT_DIR/agents/pi-coach-en.md" "$coach_dir/pi-coach-en.md"
  fi
  echo "  $MSG_COACH_DONE $coach_dir/"
fi

echo ""
echo "============================================"
echo "  $MSG_SUCCESS"
echo "============================================"
echo ""
