#!/usr/bin/env python3
"""
PI 渐进式披露拆分器：将完整版 SKILL.md 拆分为核心版 + references/
用法：python3 tools/progressive.py <input_file> <output_dir> [--name NAME]

工作流：
  1. 读取已分发的 SKILL.md（含 frontmatter + body）
  2. 按章节边界提取 4 个 references 段落
  3. 在核心版中用摘要+链接替换提取的段落
  4. 写入核心版 SKILL.md + references/ 目录

拆分规则：
  - four-dojos.md:       第四章 · 器 — 四道合一
  - battle-momentum.md:  第五章 · 势 + 第六章 · 灵
  - team-protocol.md:    第七章 · 和 — 团队协作
  - resonance-forms.md:  §8.8 共振五式

语言自动检测：通过章节标题判断 CN/EN。
"""

import sys
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# --- 摘要模板 ---

SUMMARIES = {
    "cn": {
        "four-dojos": (
            "## 4. 四道合一\n\n"
            '四大道场共享"四令+三则"认知结构。四令 = 必达的认知关卡；三则 = 必守的行动准则。\n\n'
            "> 📂 详见 [references/four-dojos.md](references/four-dojos.md) — "
            "编程(四令·正名三则·调试六步·审码四维)·测试·产品·运营 + 验证矩阵 + 步步为营"
        ),
        "battle-momentum": (
            "## 5. 动态响应 + 6. 灵兽图腾\n\n"
            "失败计数驱动六阶战势升级(易辙→深搜→系统→决死→截道→天行)。\n\n"
            "> 📂 详见 [references/battle-momentum.md](references/battle-momentum.md) — "
            "六阶战势 + 肃阵语气层 + 天行终极协议 + 战势情报(域收敛·败因标签·全局路径) + 截教 + 十二灵兽 + 止损三阶"
        ),
        "team-protocol": (
            "## 7. 团队协作\n\n"
            "Agent Team 三角色协同：Leader 统帅 + Teammate 执行 + Coach 巡检。\n\n"
            "> 📂 详见 [references/team-protocol.md](references/team-protocol.md) — "
            "协作协议 + 决策三权 + 信息流分级 + Coach巡检 + 汇报节奏"
        ),
        "resonance-forms": (
            "### 8.8 共振五式 —— 思维透明化\n\n"
            "人机协同之要：AI 思维对人**可见·可追问·可干预**。\n\n"
            "> 📂 详见 [references/resonance-forms.md](references/resonance-forms.md) — "
            "明链·明证·明树·明心·明约 详细格式与联动规则"
        ),
    },
    "en": {
        "four-dojos": (
            "## 4. Four Domains United\n\n"
            "Four domains share the \"Four Directives + Three Rules\" cognitive structure.\n\n"
            "> 📂 See [references/four-dojos.md](references/four-dojos.md) — "
            "Coding (Four Directives·Naming Rules·Debug Steps·Code Review) · Testing · Product · Operations + Verification Matrix + Step-by-Step"
        ),
        "battle-momentum": (
            "## 5. Dynamic Response + 6. Spirit Totems\n\n"
            "Failure count drives six battle stage escalation (Pivot→Deep Search→Systematic→Last Stand→Interception→Skyward).\n\n"
            "> 📂 See [references/battle-momentum.md](references/battle-momentum.md) — "
            "Six Battle Stages + Stern Mode + Skyward Ultimate Protocol + Battle Intel (Domain Convergence·Failure Tags·Global Path) + Interception + Twelve Spirit Totems + Stop-Loss"
        ),
        "team-protocol": (
            "## 7. Team Collaboration\n\n"
            "Agent Team three-role synergy: Leader command + Teammate execute + Coach patrol.\n\n"
            "> 📂 See [references/team-protocol.md](references/team-protocol.md) — "
            "Collaboration Protocol + Decision Triad + Info Flow Tiers + Coach Patrol + Reporting Cadence"
        ),
        "resonance-forms": (
            "### 8.8 Five Resonance Modes — Thinking Transparency\n\n"
            "Key to human-AI collaboration: AI thinking must be **visible · challengeable · intervenable**.\n\n"
            "> 📂 See [references/resonance-forms.md](references/resonance-forms.md) — "
            "Chain·Evidence·Tree·Heart·Pact detailed formats and interaction rules"
        ),
    },
}


def detect_lang(body: str) -> str:
    """通过章节标题检测语言"""
    if '## 4. 四道合一' in body or '智慧矩阵' in body:
        return 'cn'
    if '## 4. Four Domains' in body or 'Wisdom Matrix' in body:
        return 'en'
    # fallback: 检测中文字符比例
    cn_chars = len(re.findall(r'[\u4e00-\u9fff]', body[:500]))
    return 'cn' if cn_chars > 20 else 'en'


def find_section_boundary(lines: list, start_pattern: str, start_from: int = 0) -> int:
    """找到匹配 pattern 的行号"""
    for i in range(start_from, len(lines)):
        if re.match(start_pattern, lines[i]):
            return i
    return -1


def find_chapter_start(lines: list, chapter_num: int, start_from: int = 0) -> int:
    """找到 ## N. 章节的起始行（包含前面的 --- 分隔线）"""
    for i in range(start_from, len(lines)):
        if re.match(rf'^## {chapter_num}\.', lines[i]):
            # 回退到 --- 分隔线
            j = i - 1
            while j >= 0 and lines[j].strip() == '':
                j -= 1
            if j >= 0 and lines[j].strip() == '---':
                return j
            return i
    return -1


def find_subsection_start(lines: list, pattern: str, start_from: int = 0) -> int:
    """找到 ### N.N 子章节的起始行（包含前面的 --- 分隔线）"""
    for i in range(start_from, len(lines)):
        if re.match(pattern, lines[i]):
            # 回退到 --- 分隔线
            j = i - 1
            while j >= 0 and lines[j].strip() == '':
                j -= 1
            if j >= 0 and lines[j].strip() == '---':
                return j
            return i
    return -1


def progressive_split(input_file: str, output_dir: str, name_override: str = None):
    """主拆分逻辑"""
    input_path = Path(input_file)
    output_path = Path(output_dir)

    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 分离 frontmatter 和 body
    parts = content.split('---', 2)
    if len(parts) >= 3:
        frontmatter = '---' + parts[1] + '---'
        body = parts[2].lstrip('\n')
    else:
        frontmatter = ''
        body = content

    # 可选：覆盖 name
    if name_override and frontmatter:
        frontmatter = re.sub(
            r'(name:\s*)(\S+)',
            rf'\g<1>{name_override}',
            frontmatter,
            count=1
        )

    lang = detect_lang(body)
    lines = body.split('\n')
    summaries = SUMMARIES[lang]

    print(f"📦 Progressive split: {input_file}")
    print(f"   Language: {lang}")
    print(f"   Total lines: {len(lines)}")

    # --- 定位各章节边界 ---
    ch4_start = find_chapter_start(lines, 4)
    ch5_start = find_chapter_start(lines, 5)
    ch7_start = find_chapter_start(lines, 7)
    ch8_start = find_chapter_start(lines, 8)
    s88_start = find_subsection_start(lines, r'^### 8\.8\b')
    s89_start = find_subsection_start(lines, r'^### 8\.9\b')

    if any(x == -1 for x in [ch4_start, ch5_start, ch7_start, ch8_start, s88_start, s89_start]):
        missing = []
        if ch4_start == -1: missing.append("Ch4")
        if ch5_start == -1: missing.append("Ch5")
        if ch7_start == -1: missing.append("Ch7")
        if ch8_start == -1: missing.append("Ch8")
        if s88_start == -1: missing.append("§8.8")
        if s89_start == -1: missing.append("§8.9")
        print(f"   ❌ Cannot find sections: {', '.join(missing)}")
        sys.exit(1)

    print(f"   Ch4: L{ch4_start+1}, Ch5: L{ch5_start+1}, Ch7: L{ch7_start+1}, "
          f"Ch8: L{ch8_start+1}, §8.8: L{s88_start+1}, §8.9: L{s89_start+1}")

    # --- 提取 4 个 reference 段落 ---
    refs = {
        "four-dojos":       '\n'.join(lines[ch4_start:ch5_start]).strip(),
        "battle-momentum":  '\n'.join(lines[ch5_start:ch7_start]).strip(),
        "team-protocol":    '\n'.join(lines[ch7_start:ch8_start]).strip(),
        "resonance-forms":  '\n'.join(lines[s88_start:s89_start]).strip(),
    }

    # 从 reference 内容中去掉开头的 ---（分隔线属于结构，不属于内容）
    for key in refs:
        ref_content = refs[key]
        if ref_content.startswith('---'):
            ref_content = ref_content[3:].lstrip('\n')
        refs[key] = ref_content

    # --- 构建核心版 body ---
    core_lines = []

    # Part 1: 开头到 Ch4 之前
    core_lines.extend(lines[:ch4_start])

    # Summary: Ch4
    core_lines.append('---')
    core_lines.append('')
    core_lines.append(summaries["four-dojos"])
    core_lines.append('')

    # Summary: Ch5+6
    core_lines.append('---')
    core_lines.append('')
    core_lines.append(summaries["battle-momentum"])
    core_lines.append('')

    # Summary: Ch7
    core_lines.append('---')
    core_lines.append('')
    core_lines.append(summaries["team-protocol"])
    core_lines.append('')

    # Part 2: Ch8 到 §8.8 之前
    core_lines.extend(lines[ch8_start:s88_start])

    # Summary: §8.8
    core_lines.append('---')
    core_lines.append('')
    core_lines.append(summaries["resonance-forms"])
    core_lines.append('')

    # Part 3: §8.9 到结尾
    core_lines.extend(lines[s89_start:])

    core_body = '\n'.join(core_lines)

    # --- 写入文件 ---
    output_path.mkdir(parents=True, exist_ok=True)
    refs_dir = output_path / 'references'
    refs_dir.mkdir(parents=True, exist_ok=True)

    # 核心版
    if frontmatter:
        core_content = frontmatter + '\n\n' + core_body
    else:
        core_content = core_body

    # 检测输入文件名以确定输出文件名 (SKILL.md or SKILL_LITE.md)
    output_filename = input_path.name
    core_file = output_path / output_filename
    with open(core_file, 'w', encoding='utf-8') as f:
        f.write(core_content)

    core_lines_count = len(core_content.splitlines())
    print(f"   ✅ Core: {core_file} ({core_lines_count} lines)")

    # References
    total_ref_lines = 0
    for ref_name, ref_content in refs.items():
        ref_file = refs_dir / f'{ref_name}.md'
        with open(ref_file, 'w', encoding='utf-8') as f:
            f.write(ref_content + '\n')
        ref_lines = len(ref_content.splitlines())
        total_ref_lines += ref_lines
        print(f"   ✅ Ref:  references/{ref_name}.md ({ref_lines} lines)")

    print(f"   📊 Core {core_lines_count} + Refs {total_ref_lines} = {core_lines_count + total_ref_lines} lines "
          f"(original {len(lines)} lines)")
    print()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 tools/progressive.py <input_file> <output_dir> [--name NAME]")
        print()
        print("Examples:")
        print("  python3 tools/progressive.py skills/pi/SKILL.md skills/pi-progressive/")
        print("  python3 tools/progressive.py skills/pi-en/SKILL.md skills/pi-en-progressive/ --name pi-en-progressive")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    name_override = None

    if '--name' in sys.argv:
        idx = sys.argv.index('--name')
        if idx + 1 < len(sys.argv):
            name_override = sys.argv[idx + 1]

    progressive_split(input_file, output_dir, name_override)
