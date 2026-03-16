#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# PI / Wisdom-in-Action Engine v2 — One-Click Installer
# Supports 16+ AI coding platforms
# Interactive TUI selector: arrow keys to navigate, space to
# toggle, enter to confirm
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

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
  MSG_SUCCESS="🐲 PI 智行合一引擎安装成功！善战者，致人而不致于人。"
  MSG_INVALID="无效选择，请重新输入"
  MSG_NO_SELECTION="未选择任何平台，退出安装"
  LANG_OPT_1="中文"
  LANG_OPT_2="英文"
  LANG_OPT_3="双语（中文 + 英文）"
  EDITION_OPT_1="原版（适合大模型：Claude/GPT-4o/Gemini Pro）"
  EDITION_OPT_2="白话版（适合小模型：Haiku/GPT-4o-mini/开源模型）"
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
  MSG_SUCCESS="🐲 PI Engine installed successfully! Wisdom in Action — control the pace."
  MSG_INVALID="Invalid selection, please try again"
  MSG_NO_SELECTION="No platforms selected, exiting"
  LANG_OPT_1="Chinese"
  LANG_OPT_2="English"
  LANG_OPT_3="Both (Chinese + English)"
  EDITION_OPT_1="Original (for large models: Claude/GPT-4o/Gemini Pro)"
  EDITION_OPT_2="Lite (for small models: Haiku/GPT-4o-mini/open-source)"
  EDITION_OPT_3="Both"
  COACH_OPT_Y="Yes, install Teammate + Coach"
  COACH_OPT_N="No, skip"
fi

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
  IFS= read -rsn1 key 2>/dev/null || true
  if [[ "$key" == $'\x1b' ]]; then
    local seq
    IFS= read -rsn1 -t 0.1 seq 2>/dev/null || true
    if [[ "$seq" == "[" ]]; then
      IFS= read -rsn1 -t 0.1 seq 2>/dev/null || true
      case "$seq" in
        A) echo "UP" ;;
        B) echo "DOWN" ;;
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
  # Ensure cursor is restored on exit
  trap 'printf "\033[?25h"' EXIT

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
        printf '\033[?25h'
        trap - EXIT
        eval "$_result_var='${_result% }'"
        return 0
        ;;
      QUIT)
        printf '\033[?25h'
        trap - EXIT
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
  trap 'printf "\033[?25h"' EXIT

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
        printf '\033[?25h'
        trap - EXIT
        eval "$_result_var=$_cursor"
        return 0
        ;;
      QUIT)
        printf '\033[?25h'
        trap - EXIT
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
  fi
  if [[ "$lang" == "2" || "$lang" == "3" ]]; then
    rm -rf "${target_dir:?}/$en_name"
  fi

  if [[ "$lang" == "1" || "$lang" == "3" ]]; then
    if [[ -f "$source_dir/$cn_name/SKILL.md" ]]; then
      mkdir -p "$target_dir/$cn_name"
      if [[ "$edition" == "1" || "$edition" == "3" ]]; then
        cp "$source_dir/$cn_name/SKILL.md" "$target_dir/$cn_name/SKILL.md"
      fi
      if [[ "$edition" == "2" ]]; then
        if [[ -f "$source_dir/$cn_name/SKILL_LITE.md" ]]; then
          cp "$source_dir/$cn_name/SKILL_LITE.md" "$target_dir/$cn_name/SKILL.md"
        fi
      fi
      if [[ "$edition" == "3" ]]; then
        if [[ -f "$source_dir/$cn_name/SKILL_LITE.md" ]]; then
          cp "$source_dir/$cn_name/SKILL_LITE.md" "$target_dir/$cn_name/SKILL_LITE.md"
        fi
      fi
    fi
  fi
  if [[ "$lang" == "2" || "$lang" == "3" ]]; then
    if [[ -f "$source_dir/$en_name/SKILL.md" ]]; then
      mkdir -p "$target_dir/$en_name"
      if [[ "$edition" == "1" || "$edition" == "3" ]]; then
        cp "$source_dir/$en_name/SKILL.md" "$target_dir/$en_name/SKILL.md"
      fi
      if [[ "$edition" == "2" ]]; then
        if [[ -f "$source_dir/$en_name/SKILL_LITE.md" ]]; then
          cp "$source_dir/$en_name/SKILL_LITE.md" "$target_dir/$en_name/SKILL.md"
        fi
      fi
      if [[ "$edition" == "3" ]]; then
        if [[ -f "$source_dir/$en_name/SKILL_LITE.md" ]]; then
          cp "$source_dir/$en_name/SKILL_LITE.md" "$target_dir/$en_name/SKILL_LITE.md"
        fi
      fi
    fi
  fi
}

install_claude_code() {
  local lang="$1"
  local edition="$2"
  local target="$HOME/.claude/skills/pi"
  # Clean old install to ensure full overwrite
  rm -rf "${target:?}"
  mkdir -p "$target"
  cp -r "$SCRIPT_DIR/.claude-plugin" "$target/.claude-plugin" 2>/dev/null || true
  cp "$SCRIPT_DIR/SKILL.md" "$target/SKILL.md" 2>/dev/null || true
  if [[ "$lang" == "1" || "$lang" == "3" ]]; then
    mkdir -p "$target/skills/pi"
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      cp "$SCRIPT_DIR/claude-code/pi/SKILL.md" "$target/skills/pi/SKILL.md" 2>/dev/null || true
    fi
    if [[ "$edition" == "2" ]]; then
      cp "$SCRIPT_DIR/claude-code/pi/SKILL_LITE.md" "$target/skills/pi/SKILL.md" 2>/dev/null || true
    fi
    if [[ "$edition" == "3" ]]; then
      cp "$SCRIPT_DIR/claude-code/pi/SKILL_LITE.md" "$target/skills/pi/SKILL_LITE.md" 2>/dev/null || true
    fi
  fi
  if [[ "$lang" == "2" || "$lang" == "3" ]]; then
    mkdir -p "$target/skills/pi-en"
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      cp "$SCRIPT_DIR/skills/pi-en/SKILL.md" "$target/skills/pi-en/SKILL.md" 2>/dev/null || true
    fi
    if [[ "$edition" == "2" ]]; then
      cp "$SCRIPT_DIR/skills/pi-en/SKILL_LITE.md" "$target/skills/pi-en/SKILL.md" 2>/dev/null || true
    fi
    if [[ "$edition" == "3" ]]; then
      cp "$SCRIPT_DIR/skills/pi-en/SKILL_LITE.md" "$target/skills/pi-en/SKILL_LITE.md" 2>/dev/null || true
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
      [[ -f "$SCRIPT_DIR/cursor/rules/pi-lite.mdc" ]] && cp "$SCRIPT_DIR/cursor/rules/pi-lite.mdc" "$target/pi.mdc"
    fi
    if [[ "$edition" == "3" ]]; then
      [[ -f "$SCRIPT_DIR/cursor/rules/pi-lite.mdc" ]] && cp "$SCRIPT_DIR/cursor/rules/pi-lite.mdc" "$target/pi-lite.mdc"
    fi
  fi
  if [[ "$lang" == "2" || "$lang" == "3" ]]; then
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      [[ -f "$SCRIPT_DIR/cursor/rules/pi-en.mdc" ]] && cp "$SCRIPT_DIR/cursor/rules/pi-en.mdc" "$target/pi-en.mdc"
    fi
    if [[ "$edition" == "2" ]]; then
      [[ -f "$SCRIPT_DIR/cursor/rules/pi-en-lite.mdc" ]] && cp "$SCRIPT_DIR/cursor/rules/pi-en-lite.mdc" "$target/pi-en.mdc"
    fi
    if [[ "$edition" == "3" ]]; then
      [[ -f "$SCRIPT_DIR/cursor/rules/pi-en-lite.mdc" ]] && cp "$SCRIPT_DIR/cursor/rules/pi-en-lite.mdc" "$target/pi-en-lite.mdc"
    fi
  fi
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
      [[ -f "$SCRIPT_DIR/kiro/steering/pi-lite.md" ]] && cp "$SCRIPT_DIR/kiro/steering/pi-lite.md" "$target/pi.md"
    fi
    if [[ "$edition" == "3" ]]; then
      [[ -f "$SCRIPT_DIR/kiro/steering/pi-lite.md" ]] && cp "$SCRIPT_DIR/kiro/steering/pi-lite.md" "$target/pi-lite.md"
    fi
  fi
  if [[ "$lang" == "2" || "$lang" == "3" ]]; then
    if [[ "$edition" == "1" || "$edition" == "3" ]]; then
      [[ -f "$SCRIPT_DIR/kiro/steering/pi-en.md" ]] && cp "$SCRIPT_DIR/kiro/steering/pi-en.md" "$target/pi-en.md"
    fi
    if [[ "$edition" == "2" ]]; then
      [[ -f "$SCRIPT_DIR/kiro/steering/pi-en-lite.md" ]] && cp "$SCRIPT_DIR/kiro/steering/pi-en-lite.md" "$target/pi-en.md"
    fi
    if [[ "$edition" == "3" ]]; then
      [[ -f "$SCRIPT_DIR/kiro/steering/pi-en-lite.md" ]] && cp "$SCRIPT_DIR/kiro/steering/pi-en-lite.md" "$target/pi-en-lite.md"
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
  install_skill_to_dir "$HOME/.copilot/skills" "$SCRIPT_DIR/skills" "pi" "pi-en" "$lang" "$edition"
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
