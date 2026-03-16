#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# PI / Wisdom-in-Action Engine v2 — One-Click Installer
# Supports 16+ AI coding platforms
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
  MSG_FOUND="检测到以下平台："
  MSG_NONE="未检测到任何已知平台。请先安装至少一个支持的 AI 编程工具。"
  MSG_SELECT="请选择要安装的平台（输入编号，多个用空格分隔，a=全部，q=退出）："
  MSG_LANG_SELECT="选择语言版本（1=中文, 2=英文, 3=双语）："
  MSG_EDITION_SELECT="选择 PI 版本（1=原版·适合大模型, 2=白话版·适合小模型, 3=两个都装）："
  MSG_INSTALLING="正在安装到"
  MSG_DONE="安装完成！"
  MSG_SKIP="跳过（未在仓库中找到对应文件）"
  MSG_COACH="是否安装 Agent Team 角色（Teammate + Coach）？(y/N)："
  MSG_COACH_DONE="Agent Team 文件已安装到"
  MSG_SUCCESS="🐲 PI 智行合一引擎安装成功！善战者，致人而不致于人。"
  MSG_INVALID="无效选择，请重新输入"
else
  MSG_TITLE="🐲 PI Wisdom-in-Action Engine — One-Click Install"
  MSG_DETECT="Detecting available platforms..."
  MSG_FOUND="Detected platforms:"
  MSG_NONE="No known platforms detected. Please install at least one supported AI coding tool first."
  MSG_SELECT="Select platforms to install (enter numbers separated by spaces, a=all, q=quit):"
  MSG_LANG_SELECT="Select language (1=Chinese, 2=English, 3=Both):"
  MSG_EDITION_SELECT="Select PI edition (1=Original·for large models, 2=Lite·for small models, 3=Both):"
  MSG_INSTALLING="Installing to"
  MSG_DONE="Installation complete!"
  MSG_SKIP="Skipped (source files not found in repo)"
  MSG_COACH="Install Agent Team roles (Teammate + Coach)? (y/N):"
  MSG_COACH_DONE="Agent Team files installed to"
  MSG_SUCCESS="🐲 PI Engine installed successfully! Wisdom in Action — control the pace."
  MSG_INVALID="Invalid selection, please try again"
fi

echo ""
echo "============================================"
echo "  $MSG_TITLE"
echo "============================================"
echo ""

# --- Platform definitions ---
# Format: NAME|DETECT_PATH|INSTALL_FUNC
declare -a PLATFORMS=()
declare -a DETECTED=()

# Detection functions — check if the platform config dir exists
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

# Install functions
install_skill_to_dir() {
  local target_dir="$1"
  local source_dir="$2"
  local cn_name="$3"
  local en_name="$4"
  local lang="$5"
  local edition="$6"

  if [[ "$lang" == "1" || "$lang" == "3" ]]; then
    if [[ -f "$source_dir/$cn_name/SKILL.md" ]]; then
      mkdir -p "$target_dir/$cn_name"
      if [[ "$edition" == "1" || "$edition" == "3" ]]; then
        cp "$source_dir/$cn_name/SKILL.md" "$target_dir/$cn_name/SKILL.md"
      fi
      if [[ "$edition" == "2" ]]; then
        # LITE only: install as SKILL.md (rename for direct use)
        if [[ -f "$source_dir/$cn_name/SKILL_LITE.md" ]]; then
          cp "$source_dir/$cn_name/SKILL_LITE.md" "$target_dir/$cn_name/SKILL.md"
        fi
      fi
      if [[ "$edition" == "3" ]]; then
        # Both: also copy LITE as SKILL_LITE.md
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
  # Claude Code uses plugin install or manual copy
  local target="$HOME/.claude/plugins/pi"
  mkdir -p "$target"
  # Copy the whole repo as a plugin
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
  # Also copy agents
  mkdir -p "$target/agents"
  cp "$SCRIPT_DIR/agents/pi-coach.md" "$target/agents/" 2>/dev/null || true
  cp "$SCRIPT_DIR/agents/pi-coach-en.md" "$target/agents/" 2>/dev/null || true
  cp "$SCRIPT_DIR/agents/pi-teammate.md" "$target/agents/" 2>/dev/null || true
  cp "$SCRIPT_DIR/agents/pi-teammate-en.md" "$target/agents/" 2>/dev/null || true
  # Copy commands
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
  "Qoder CLI"
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

echo "$MSG_FOUND"
echo ""
for idx in "${!DETECTED[@]}"; do
  i="${DETECTED[$idx]}"
  echo "  $((idx + 1)). ${PLATFORM_NAMES[$i]}"
done
echo ""

# --- Select platforms ---
read -rp "$MSG_SELECT " selection

if [[ "$selection" == "q" || "$selection" == "Q" ]]; then
  exit 0
fi

declare -a SELECTED=()
if [[ "$selection" == "a" || "$selection" == "A" ]]; then
  SELECTED=("${DETECTED[@]}")
else
  for num in $selection; do
    if [[ "$num" =~ ^[0-9]+$ ]] && (( num >= 1 && num <= ${#DETECTED[@]} )); then
      SELECTED+=("${DETECTED[$((num - 1))]}")
    else
      echo "$MSG_INVALID: $num"
    fi
  done
fi

if [[ ${#SELECTED[@]} -eq 0 ]]; then
  echo "$MSG_INVALID"
  exit 1
fi

echo ""

# --- Select language ---
read -rp "$MSG_LANG_SELECT " lang_choice

case "$lang_choice" in
  1|2|3) ;;
  *) lang_choice="3" ;;
esac

echo ""

# --- Select edition ---
read -rp "$MSG_EDITION_SELECT " edition_choice

case "$edition_choice" in
  1|2|3) ;;
  *) edition_choice="1" ;;
esac

echo ""

# --- Install ---
for i in "${SELECTED[@]}"; do
  echo "${PLATFORM_NAMES[$i]}:"
  ${PLATFORM_INSTALLERS[$i]} "$lang_choice" "$edition_choice"
done

echo ""

# --- Coach install ---
read -rp "$MSG_COACH " coach_choice
if [[ "$coach_choice" == "y" || "$coach_choice" == "Y" ]]; then
  coach_dir=".claude/agents"
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
