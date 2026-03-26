#!/usr/bin/env python3
"""Convert MHTML files to clean Markdown.

Usage:
    python3 tools/mhtml2md.py input.mhtml [output.md]

If output path is omitted, writes to the same directory with .md extension.
"""

import email
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class HTMLToMarkdown(HTMLParser):
    SKIP_TAGS = {"script", "style", "nav", "footer", "header", "noscript", "svg", "path"}

    def __init__(self):
        super().__init__()
        self.result: list[str] = []
        self.tag_stack: list[str] = []
        self.skip_depth = 0
        self.in_pre = False
        self.in_code = False
        self.current_text = ""
        self._link_href: str | None = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag in self.SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth > 0:
            return

        self.tag_stack.append(tag)

        if tag == "pre":
            self.in_pre = True
            self._flush()
            self.result.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.in_code = True
            self.current_text += "`"
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            level = int(tag[1])
            self.result.append("\n" + "#" * level + " ")
        elif tag == "p":
            self._flush()
            self.result.append("\n\n")
        elif tag == "br":
            self.current_text += "\n"
        elif tag == "li":
            self._flush()
            self.result.append("\n- ")
        elif tag in ("ul", "ol"):
            self._flush()
            self.result.append("\n")
        elif tag in ("strong", "b"):
            self.current_text += "**"
        elif tag in ("em", "i"):
            self.current_text += "*"
        elif tag == "a":
            href = attrs_dict.get("href", "")
            if href and not href.startswith("#"):
                self._link_href = href
                self.current_text += "["
            else:
                self._link_href = None
        elif tag == "img":
            alt = attrs_dict.get("alt", "")
            if alt.strip():
                self.current_text += f"[Image: {alt}]"
        elif tag == "blockquote":
            self._flush()
            self.result.append("\n> ")
        elif tag == "tr":
            self.current_text += "\n| "
        elif tag in ("td", "th"):
            self.current_text += " "

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self.skip_depth -= 1
            return
        if self.skip_depth > 0:
            return

        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()

        if tag == "pre":
            self.in_pre = False
            self.result.append("\n```\n")
        elif tag == "code" and not self.in_pre:
            self.in_code = False
            self.current_text += "`"
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self.result.append("\n")
        elif tag == "p":
            self._flush()
        elif tag in ("strong", "b"):
            self.current_text += "**"
        elif tag in ("em", "i"):
            self.current_text += "*"
        elif tag == "a":
            if self._link_href:
                self.current_text += f"]({self._link_href})"
                self._link_href = None
        elif tag in ("td", "th"):
            self.current_text += " |"

    def handle_data(self, data):
        if self.skip_depth > 0:
            return
        if self.in_pre:
            self.result.append(data)
        else:
            self.current_text += data

    def _flush(self):
        if self.current_text.strip():
            text = self.current_text
            if not self.in_pre:
                text = re.sub(r"\s+", " ", text)
            self.result.append(text)
        self.current_text = ""

    def get_markdown(self) -> str:
        self._flush()
        return "".join(self.result)


def extract_html_from_mhtml(mhtml_path: str) -> str:
    """Extract the HTML part from an MHTML file."""
    with open(mhtml_path, "rb") as f:
        msg = email.message_from_bytes(f.read())

    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            if payload:
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")

    raise ValueError("No text/html part found in MHTML file")


def html_to_markdown(html: str) -> str:
    """Convert HTML string to Markdown."""
    extractor = HTMLToMarkdown()
    extractor.feed(html)
    return extractor.get_markdown()


def clean_markdown(md: str) -> str:
    """Post-process: remove noise, collapse blank lines."""
    # Remove newsletter/footer sections
    for pattern in (
        r"\n## Get the developer newsletter.*",
        r"\nProduct updates, how-tos, community spotlights.*",
    ):
        match = re.search(pattern, md, re.DOTALL)
        if match:
            md = md[: match.start()]

    # Remove empty image tags
    md = re.sub(r"\[Image:\s*\]", "", md)
    # Remove UI artifacts like "CopyExpand"
    md = re.sub(r"\nCopyExpand\n", "\n", md)
    # Collapse excessive blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)

    return md.strip() + "\n"


def convert(mhtml_path: str, output_path: str | None = None) -> str:
    """Full pipeline: MHTML → clean Markdown file.

    Returns the output file path.
    """
    if output_path is None:
        output_path = str(Path(mhtml_path).with_suffix(".md"))

    html = extract_html_from_mhtml(mhtml_path)
    md = html_to_markdown(html)
    md = clean_markdown(md)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    return output_path


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    mhtml_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    result = convert(mhtml_path, output_path)
    print(f"Saved to {result}")


if __name__ == "__main__":
    main()
