"""Convierte texto nativo (acentos, símbolos) a entidades HTML en el contenido
de un documento HTML, preservando markup (tags, atributos, comentarios, CDATA)."""
from __future__ import annotations

from html.parser import HTMLParser
from html.entities import codepoint2name
from typing import List, Optional


def _encode_text_to_entities(text: str) -> str:
    out: List[str] = []
    for ch in text:
        cp = ord(ch)
        if cp < 128:
            out.append(ch)
            continue
        name = codepoint2name.get(cp)
        if name:
            out.append(f"&{name};")
        else:
            out.append(f"&#{cp};")
    return "".join(out)


def _encode_attr_value(value: str) -> str:
    out: List[str] = []
    for ch in value:
        cp = ord(ch)
        if cp < 128:
            out.append(ch)
            continue
        name = codepoint2name.get(cp)
        out.append(f"&{name};" if name else f"&#{cp};")
    return "".join(out)


VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


RAW_TEXT_TAGS = {"script", "style"}


class _EntityEncoderParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: List[str] = []
        self.raw_depth = 0

    def _format_attrs(self, attrs) -> str:
        chunks: List[str] = []
        for name, value in attrs:
            if value is None:
                chunks.append(f" {name}")
            else:
                chunks.append(f' {name}="{_encode_attr_value(value)}"')
        return "".join(chunks)

    def handle_starttag(self, tag, attrs):
        if tag in RAW_TEXT_TAGS:
            self.raw_depth += 1
        self.parts.append(f"<{tag}{self._format_attrs(attrs)}>")

    def handle_startendtag(self, tag, attrs):
        self.parts.append(f"<{tag}{self._format_attrs(attrs)}/>")

    def handle_endtag(self, tag):
        if tag in RAW_TEXT_TAGS and self.raw_depth > 0:
            self.raw_depth -= 1
        self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        if self.raw_depth > 0:
            self.parts.append(data)
        else:
            self.parts.append(_encode_text_to_entities(data))

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def handle_comment(self, data):
        self.parts.append(f"<!--{data}-->")

    def handle_decl(self, decl):
        self.parts.append(f"<!{decl}>")

    def handle_pi(self, data):
        self.parts.append(f"<?{data}>")

    def unknown_decl(self, data):
        self.parts.append(f"<![{data}]>")


def encode_html_special_chars(html_text: str) -> str:
    """Devuelve el HTML con todos los caracteres non-ASCII del contenido textual
    y de los valores de atributo convertidos a entidades HTML (named cuando existe
    en `html.entities.codepoint2name`, numéricas en caso contrario).
    Preserva tags, comentarios, doctypes, scripts y styles tal cual."""
    parser = _EntityEncoderParser()
    parser.feed(html_text)
    parser.close()
    return "".join(parser.parts)
