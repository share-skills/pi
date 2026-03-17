#!/usr/bin/env python3
"""
PI 分发器 v2：读取平台 _frontmatter + body 拼接
用法：python3 tools/distribute.py <source_file> <variant>

variant:
  cn        → 中文原版
  cn-lite   → 中文白话版
  en        → 英文原版
  en-lite   → 英文白话版
  prog      → 渐进式中文版
  prog-en   → 渐进式英文版（预留）

工作流：
  1. 从 source_file 提取 frontmatter 元数据 + body
  2. 按需 PURGE-01（删 Loop 规则）
  3. 读取各平台 _frontmatter 模板文件，填充变量
  4. 拼接 frontmatter + body → 写入目标文件

设计原则：
  - body 只生成一次，frontmatter 只是 patch
  - 各平台 _frontmatter 文件独立维护，脚本只做读取+填充+拼接
  - SKILL.md 和 SKILL_LITE.md 分发路径严格分离
"""

import sys
import os
import re
import shutil
from pathlib import Path

# --- 项目根目录 ---
ROOT = Path(__file__).resolve().parent.parent

# --- 平台配置 ---
# (frontmatter_dir, output_path, needs_purge)
# frontmatter_dir: _frontmatter 文件所在目录（相对 ROOT）
# output_path: 输出文件路径（相对 ROOT）
# needs_purge: 是否需要 PURGE-01（删 Loop）

VARIANTS = {
    "cn": {
        "name": "pi",
        "lang": "cn",
        "targets": [
            ("skills/pi",              "skills/pi/SKILL.md",              True),
            ("claude-code/pi",         "claude-code/pi/SKILL.md",         True),
            ("cursor/rules",           "cursor/rules/pi.mdc",             True),
            ("kiro/steering",          "kiro/steering/pi.md",             True),
            ("openclaw/pi",            "openclaw/pi/SKILL.md",            True),
            ("copilot-cli/pi",         "copilot-cli/pi/SKILL.md",         False),
        ],
    },
    "cn-lite": {
        "name": "pi-lite",
        "lang": "cn",
        "targets": [
            ("skills/pi",              "skills/pi/SKILL_LITE.md",         True),
            ("claude-code/pi",         "claude-code/pi/SKILL_LITE.md",    True),
            ("cursor/rules",           "cursor/rules/pi-lite.mdc",        True),
            ("kiro/steering",          "kiro/steering/pi-lite.md",        True),
            ("openclaw/pi",            "openclaw/pi/SKILL_LITE.md",       True),
            ("copilot-cli/pi",         "copilot-cli/pi/SKILL_LITE.md",    False),
        ],
    },
    "en": {
        "name": "pi-en",
        "lang": "en",
        "targets": [
            ("skills/pi-en",           "skills/pi-en/SKILL.md",           True),
            ("claude-code/pi-en",      "claude-code/pi-en/SKILL.md",      True),
            ("cursor/rules",           "cursor/rules/pi-en.mdc",          True),
            ("kiro/steering",          "kiro/steering/pi-en.md",          True),
            ("openclaw/pi-en",         "openclaw/pi-en/SKILL.md",         True),
            ("copilot-cli/pi-en",      "copilot-cli/pi-en/SKILL.md",      False),
        ],
    },
    "en-lite": {
        "name": "pi-en-lite",
        "lang": "en",
        "targets": [
            ("skills/pi-en",           "skills/pi-en/SKILL_LITE.md",      True),
            ("claude-code/pi-en",      "claude-code/pi-en/SKILL_LITE.md", True),
            ("cursor/rules",           "cursor/rules/pi-en-lite.mdc",     True),
            ("kiro/steering",          "kiro/steering/pi-en-lite.md",     True),
            ("openclaw/pi-en",         "openclaw/pi-en/SKILL_LITE.md",    True),
            ("copilot-cli/pi-en",      "copilot-cli/pi-en/SKILL_LITE.md", False),
        ],
    },
    "prog": {
        "name": "pi-progressive",
        "lang": "cn",
        "progressive": True,
        "refs_source": "skills/pi-progressive/references",
        "targets": [
            ("skills/pi-progressive",          "skills/pi-progressive/SKILL.md",           True),
            ("claude-code/pi-progressive",      "claude-code/pi-progressive/SKILL.md",      True),
            ("copilot-cli/pi-progressive",      "copilot-cli/pi-progressive/SKILL.md",      False),
            ("openclaw/pi-progressive",         "openclaw/pi-progressive/SKILL.md",         True),
        ],
    },
    "prog-lite": {
        "name": "pi-progressive",
        "lang": "cn",
        "progressive": True,
        "refs_source": "skills/pi-progressive/references",
        "targets": [
            ("skills/pi-progressive",          "skills/pi-progressive/SKILL_LITE.md",      True),
            ("claude-code/pi-progressive",      "claude-code/pi-progressive/SKILL_LITE.md", True),
            ("copilot-cli/pi-progressive",      "copilot-cli/pi-progressive/SKILL_LITE.md", False),
            ("openclaw/pi-progressive",         "openclaw/pi-progressive/SKILL_LITE.md",    True),
        ],
    },
    "prog-en": {
        "name": "pi-en-progressive",
        "lang": "en",
        "progressive": True,
        "refs_source": "skills/pi-en-progressive/references",
        "targets": [
            ("skills/pi-en-progressive",        "skills/pi-en-progressive/SKILL.md",        True),
            ("claude-code/pi-en-progressive",    "claude-code/pi-en-progressive/SKILL.md",   True),
            ("copilot-cli/pi-en-progressive",    "copilot-cli/pi-en-progressive/SKILL.md",   False),
            ("openclaw/pi-en-progressive",       "openclaw/pi-en-progressive/SKILL.md",      True),
        ],
    },
    "prog-en-lite": {
        "name": "pi-en-progressive",
        "lang": "en",
        "progressive": True,
        "refs_source": "skills/pi-en-progressive/references",
        "targets": [
            ("skills/pi-en-progressive",        "skills/pi-en-progressive/SKILL_LITE.md",   True),
            ("claude-code/pi-en-progressive",    "claude-code/pi-en-progressive/SKILL_LITE.md", True),
            ("copilot-cli/pi-en-progressive",    "copilot-cli/pi-en-progressive/SKILL_LITE.md", False),
            ("openclaw/pi-en-progressive",       "openclaw/pi-en-progressive/SKILL_LITE.md", True),
        ],
    },
}


# --- PURGE-01: 删除 Loop 规则 ---
def purge_loop(body: str, lang: str = "cn") -> str:
    """从 body 中删除 Loop 模式相关内容"""
    lines = body.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip Loop row in interaction mode table
        if '🔄 **Loop**' in line:
            i += 1
            continue

        # Skip Loop mode rules section (header + numbered items until blank line)
        if ('**Loop 模式规则**' in line or '**Loop Mode Rules**' in line or
            '**Loop mode rules**' in line or '**Loop Mode rules**' in line):
            while i < len(lines) and lines[i].strip():
                i += 1
            i += 1  # skip the blank line too
            continue

        # Skip Loop exit traps (header + table)
        if ('**Loop 退出陷阱**' in line or '**Loop Exit Traps**' in line or
            '**Loop exit traps**' in line or '**Loop Exit traps**' in line):
            while i < len(lines) and lines[i].strip():
                i += 1
            i += 1
            continue

        # Skip Loop startup protocol
        if ('**Loop 启动协议**' in line or '**Loop Startup Protocol**' in line or
            '**Loop startup protocol**' in line or '**Loop Startup protocol**' in line):
            while i < len(lines) and lines[i].strip():
                i += 1
            i += 1
            continue

        # Skip Loop interaction section (header + table)
        if ('**Loop interaction**' in line or '**Loop 循环交互**' in line):
            while i < len(lines) and lines[i].strip():
                i += 1
            i += 1
            continue

        # Skip Loop warning note
        if ('⚠️' in line and 'Loop' in line and
            ('自主决策权' in line or 'autonomous' in line or 'decision' in line)):
            i += 1
            continue

        # Fix mode selection line (case-insensitive for "Selection"/"selection")
        if ('**模式选择**' in line or '**Mode selection**' in line or
            '**Mode Selection**' in line) and 'Loop' in line:
            if lang == "cn":
                result.append('**模式选择**：默认 Auto 模式，三档自治度生效。')
            else:
                result.append('**Mode selection**: Default Auto mode, three autonomy levels active.')
            i += 1
            continue

        # Fix mode loading matrix
        line = line.replace('Loop:✅ Auto:⚡', '⚡')
        line = line.replace('Loop:✅ Auto:接续提问', '接续提问')
        line = line.replace('Loop:✅ Auto:follow-up questions', 'follow-up questions')

        # Fix progressive delivery header
        if 'Loop模式强制' in line:
            line = line.replace('（🔄Loop模式强制，Auto模式按需）', '（按需）')
        if 'Loop mode mandatory' in line:
            line = line.replace('(🔄Loop mode mandatory, Auto mode as needed)', '(as needed)')

        # Fix pact trigger Loop reference
        if 'Loop' in line and ('明约' in line or 'Pact' in line or '交付确认' in line):
            line = re.sub(r'\s*·?\s*Loop\s*模式下.*提问收尾', '', line)
            line = re.sub(r'\s*·?\s*In Loop mode.*closing questions', '', line)

        result.append(line)
        i += 1

    return '\n'.join(result)


def parse_frontmatter_simple(content: str) -> dict:
    """简单解析 frontmatter（无 yaml 依赖）"""
    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}
    fm_text = parts[1]
    data = {}
    metadata = {}
    in_metadata = False

    for line in fm_text.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # metadata block detection
        if stripped == 'metadata:':
            in_metadata = True
            continue

        if in_metadata:
            if line.startswith('  '):
                # metadata sub-key
                m = re.match(r'\s+([\w-]+):\s*"?([^"]*)"?\s*$', line)
                if m:
                    metadata[m.group(1)] = m.group(2)
                continue
            else:
                in_metadata = False

        # top-level key
        m = re.match(r'([\w-]+):\s*"?(.+?)"?\s*$', line)
        if m:
            key, val = m.group(1), m.group(2)
            # Strip surrounding quotes
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            data[key] = val

    data['metadata'] = metadata
    return data


def extract_body(filepath: str) -> str:
    """提取 body（frontmatter 之后的内容）"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    parts = content.split('---', 2)
    if len(parts) >= 3:
        return parts[2].lstrip('\n')
    return content


def read_frontmatter_template(fm_dir: str) -> str:
    """读取平台 _frontmatter 模板文件"""
    fm_path = ROOT / fm_dir / '_frontmatter'
    if not fm_path.exists():
        print(f"  ⚠️  _frontmatter not found: {fm_path}")
        return None
    with open(fm_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def distribute(source_file: str, variant: str):
    """主分发逻辑"""
    if variant not in VARIANTS:
        print(f"❌ Unknown variant: {variant}")
        print(f"   Available: {', '.join(VARIANTS.keys())}")
        sys.exit(1)

    config = VARIANTS[variant]
    variant_name = config["name"]
    lang = config["lang"]
    targets = config["targets"]

    if not targets:
        print(f"⚠️  Variant '{variant}' has no targets configured.")
        sys.exit(0)

    # 读取源文件
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析 frontmatter 元数据
    fm_data = parse_frontmatter_simple(content)
    metadata = fm_data.get('metadata', {})
    description = fm_data.get('description', '')
    version = metadata.get('version', '20.0.0')
    homepage = metadata.get('homepage', 'https://github.com/share-skills/pi')
    copyright_val = metadata.get('copyright', 'Copyright (c) 2026 HePin. All rights reserved.')
    argument_hint = metadata.get('argument-hint', '[loop|auto] [场景名]')

    # 提取 body
    body = extract_body(source_file)

    # 生成 purged body
    purged_body = purge_loop(body, lang)

    # 统计
    print(f"📦 Distributing: {variant} (name={variant_name})")
    print(f"   Source: {source_file}")
    print(f"   Full body: {len(body.splitlines())} lines")
    print(f"   Purged body: {len(purged_body.splitlines())} lines")
    print(f"   PURGE-01 removed: {len(body.splitlines()) - len(purged_body.splitlines())} lines")
    print()

    for fm_dir, output_path, needs_purge in targets:
        full_output = ROOT / output_path

        # 确保目录存在
        full_output.parent.mkdir(parents=True, exist_ok=True)

        # 读取 _frontmatter 模板
        fm_template = read_frontmatter_template(fm_dir)
        if fm_template is None:
            print(f"   ❌ {output_path}: skipped (no _frontmatter)")
            continue

        # 填充模板
        # 使用 format_map 以便忽略未知占位符
        frontmatter = fm_template.format(
            name=variant_name,
            description=description.replace('"', '\\"'),
            version=version,
            homepage=homepage,
            copyright=copyright_val,
            argument_hint=argument_hint,
        )

        # 选择 body
        selected_body = purged_body if needs_purge else body

        # 拼接并写入
        output = frontmatter + '\n\n' + selected_body
        with open(full_output, 'w', encoding='utf-8') as f:
            f.write(output)

        status = "purged" if needs_purge else "full"
        lines = len(output.splitlines())
        print(f"   ✅ {output_path} ({status}, {lines} lines)")

    # --- 渐进式版本：复制 references/ ---
    refs_source = config.get("refs_source")
    if refs_source:
        refs_src_path = ROOT / refs_source
        if refs_src_path.exists():
            # 先读入内存，防止源目录被覆盖
            ref_files = {}
            for ref_file in sorted(refs_src_path.glob("*.md")):
                with open(ref_file, 'r', encoding='utf-8') as f:
                    ref_files[ref_file.name] = f.read()

            print()
            print(f"   📂 Copying references/ ({len(ref_files)} files) from {refs_source}")

            for fm_dir, output_path, needs_purge in targets:
                target_dir = (ROOT / output_path).parent
                target_refs = target_dir / "references"

                # 清空已有 references/
                if target_refs.exists():
                    shutil.rmtree(target_refs)
                target_refs.mkdir(parents=True, exist_ok=True)

                # 写入每个 reference 文件，按需 PURGE
                for ref_name, ref_content in ref_files.items():
                    if needs_purge:
                        ref_content = purge_loop(ref_content, lang)

                    with open(target_refs / ref_name, 'w', encoding='utf-8') as f:
                        f.write(ref_content)

                purge_tag = "purged" if needs_purge else "full"
                print(f"   ✅ {target_dir.relative_to(ROOT)}/references/ ({len(ref_files)} files, {purge_tag})")
        else:
            print(f"   ⚠️  refs_source not found: {refs_source}")

    print()
    print("✅ Distribution complete.")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 tools/distribute.py <source_file> <variant>")
        print()
        print("Variants:")
        for k, v in VARIANTS.items():
            targets_count = len(v["targets"])
            print(f"  {k:10s} → name={v['name']}, lang={v['lang']}, {targets_count} targets")
        sys.exit(1)

    distribute(sys.argv[1], sys.argv[2])
