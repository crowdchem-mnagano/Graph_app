# -*- coding: utf-8 -*-
"""
Streamlitアプリ版：Graphviz + JSONCrack風ツリー可視化（Cloud用）
"""

import streamlit as st
import json
import html
import subprocess
import tempfile
from io import StringIO
from typing import Any, Dict, List, Union
from PIL import Image
import os
import base64
import streamlit.components.v1 as components

# ────────── フォント設定 ──────────
os.environ["GDFONTPATH"]  = "/usr/share/fonts/truetype/noto"
os.environ["DOT_FONTPATH"] = "/usr/share/fonts/truetype/noto"
FONT = "Noto Sans CJK JP"

# ────────── Graphviz生成 ──────────
def _next(n: int) -> str:
    return f"N{n:04d}"

def _to_dot(parent: str, data: Any, idx: int, buf: StringIO) -> int:
    name = _next(idx)
    if isinstance(data, list):
        buf.write(f'{name} [label=<\n<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">\n')
        for i, item in enumerate(data):
            cell = "&nbsp;"*4 if isinstance(item, (dict, list)) else html.escape(str(item))
            buf.write(f'<TR><TD BORDER="0">{i}</TD><TD PORT="p_{i}">{cell}</TD></TR>\n')
        buf.write('</TABLE>>];\n')
        buf.write(f'{parent}->{name};\n')
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                idx = _to_dot(f"{name}:p_{i}", item, idx+1, buf)
        return idx

    if isinstance(data, dict):
        buf.write(f'{name} [label=<\n<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">\n')
        for i, (k, v) in enumerate(data.items()):
            cell = "&nbsp;"*4 if isinstance(v, (dict, list)) else html.escape(str(v))
            buf.write(f'<TR><TD>{html.escape(str(k))}</TD><TD PORT="p_{i}">{cell}</TD></TR>\n')
        buf.write('</TABLE>>];\n')
        buf.write(f'{parent}->{name};\n')
        for i, v in enumerate(data.values()):
            if isinstance(v, (dict, list)):
                idx = _to_dot(f"{name}:p_{i}", v, idx+1, buf)
        return idx

    buf.write(f'{name} [label="{html.escape(str(data))}"];\n')
    buf.write(f'{parent}->{name};\n')
    return idx

def json2graphviz(json_data: Union[Dict, List], png_path: str, svg_path: str, root_label: str):
    dot = StringIO()
    dot.write("digraph G {\n")
    dot.write(f'  graph [rankdir=LR, fontname="{FONT}", charset="UTF-8"];\n')
    dot.write(f'  node  [shape=plaintext, fontname="{FONT}"];\n')
    dot.write(f'  edge  [fontname="{FONT}"];\n')
    dot.write(f'  root [label="{root_label}", shape=circle, fontname="{FONT}"];\n')
    _to_dot("root", json_data, 0, dot)
    dot.write("}\n")
    dot_input = dot.getvalue()
    subprocess.run(["dot", "-Tpng", "-o", png_path], input=dot_input, text=True, check=True)
    subprocess.run(["dot", "-Tsvg", "-o", svg_path], input=dot_input, text=True, check=True)

# ────────── JSONツリー（JSONCrack風）表示 ──────────
def show_d3_tree(json_data):
    with open("json_tree.html", "r", encoding="utf-8") as f:
        html_template = f.read()
    html_filled = html_template.replace("__JSON_DATA__", json.dumps(json_data))
    components.html(html_filled, height=800, scrolling=True)

# ────────── Streamlitアプリ部分 ──────────
st.set_page_config(page_title="JSON可視化：Graphviz + JSONツリー", layout="wide")
st.title("🧩 JSON → Graphviz & JSONツリー（Cloud対応）")

uploaded_file = st.file_uploader("JSONファイルをアップロード", type=["json"])
root_label = st.text_input("ルートノードのラベル（例：物性）", value="物性")

if uploaded_file:
    json_data = json.load(uploaded_file)
    st.success("✅ JSONの読み込みに成功しました。")

    mode = st.radio("表示モードを選択", ["Graphviz（静的PNG/SVG）", "JSONツリー（JSONCrack風）"])

    if mode == "Graphviz（静的PNG/SVG）":
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png, \
             tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_svg:
            json2graphviz(json_data, tmp_png.name, tmp_svg.name, root_label)
            img = Image.open(tmp_png.name)
            st.image(img, caption="Graphviz可視化結果", use_container_width=True)

            with open(tmp_svg.name, "r", encoding="utf-8") as f:
                svg_data = f.read()
            b64 = base64.b64encode(svg_data.encode("utf-8")).decode("utf-8")
            href = f"data:image/svg+xml;base64,{b64}"
            st.markdown(f'<a href="{href}" target="_blank">🔗 SVGを新しいタブで開く</a>', unsafe_allow_html=True)

    elif mode == "JSONツリー（JSONCrack風）":
        show_d3_tree(json_data)

st.markdown("---")
st.caption("※ Graphviz(dot)とfonts-noto-cjkが必要です。JSONツリーモードはD3.jsで描画されます。")
