# -*- coding: utf-8 -*-
"""
Streamlitアプリ版：JSON → Graphviz(PNG) 可視化
"""

import streamlit as st
import json
import html
import subprocess
import tempfile
from io import StringIO
from typing import Any, Dict, List, Union
from PIL import Image

FONT = "Noto Sans CJK JP"  # 日本語フォント

# ────────── ノード名生成 ──────────
def _next(n: int) -> str:
    return f"N{n:04d}"

# ────────── JSON構造 → DOT ──────────
def _to_dot(parent: str, data: Any, idx: int, buf: StringIO) -> int:
    name = _next(idx)

    # list
    if isinstance(data, list):
        buf.write(f'{name} [label=<\n<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">\n')
        if not data:
            buf.write('<TR><TD COLSPAN="2">&nbsp;</TD></TR>\n')
        else:
            for i, item in enumerate(data):
                cell = "&nbsp;"*4 if isinstance(item, (dict, list)) else html.escape(str(item))
                buf.write(f'<TR><TD BORDER="0">{i}</TD><TD PORT="p_{i}">{cell}</TD></TR>\n')
        buf.write('</TABLE>>];\n')
        buf.write(f'{parent}->{name};\n')
        for i, item in enumerate(data):
            if isinstance(item, (dict, list)):
                idx = _to_dot(f"{name}:p_{i}", item, idx+1, buf)
        return idx

    # dict
    if isinstance(data, dict):
        buf.write(f'{name} [label=<\n<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">\n')
        if not data:
            buf.write('<TR><TD COLSPAN="2">&nbsp;</TD></TR>\n')
        else:
            for i, (k, v) in enumerate(data.items()):
                cell = "&nbsp;"*4 if isinstance(v, (dict, list)) else html.escape(str(v))
                buf.write(f'<TR><TD>{html.escape(str(k))}</TD><TD PORT="p_{i}">{cell}</TD></TR>\n')
        buf.write('</TABLE>>];\n')
        buf.write(f'{parent}->{name};\n')
        for i, v in enumerate(data.values()):
            if isinstance(v, (dict, list)):
                idx = _to_dot(f"{name}:p_{i}", v, idx+1, buf)
        return idx

    # scalar
    buf.write(f'{name} [label="{html.escape(str(data))}"];\n')
    buf.write(f'{parent}->{name};\n')
    return idx

# ────────── JSON → PNG ──────────
def json2png(json_data: Union[Dict, List], png_path: str, root_label: str = "物性") -> None:
    dot = StringIO()
    dot.write("digraph G {\n")
    dot.write(f'  graph [rankdir=LR, fontname="{FONT}"];\n')
    dot.write(f'  node  [shape=plaintext, fontname="{FONT}"];\n')
    dot.write(f'  edge  [fontname="{FONT}"];\n')
    dot.write(f'  root [label="{root_label}", shape=circle];\n')
    _to_dot("root", json_data, 0, dot)
    dot.write("}\n")

    subprocess.run(["dot", "-Tpng", "-o", png_path],
                   input=dot.getvalue(), text=True, check=True)

# ────────── Streamlitアプリ部分 ──────────
st.set_page_config(page_title="JSON→Graphviz 可視化", layout="wide")
st.title("🧩 JSON → Graphviz PNG 可視化ツール（物性版）")

uploaded_file = st.file_uploader("JSONファイルをアップロード", type=["json"])

root_label = st.text_input("ルートノードのラベル（例：物性）", value="物性")

if uploaded_file:
    try:
        json_data = json.load(uploaded_file)
        st.success("✅ JSONの読み込みに成功しました。")

        # 一時ファイルでGraphviz生成
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png:
            json2png(json_data, tmp_png.name, root_label)
            img = Image.open(tmp_png.name)
            st.image(img, caption="Graphviz可視化結果", use_container_width=True)

            # ダウンロードボタン
            with open(tmp_png.name, "rb") as f:
                st.download_button("📥 PNGをダウンロード", f, file_name="json_graph.png")

    except Exception as e:
        st.error(f"❌ エラーが発生しました: {e}")

st.markdown("---")
st.caption("※ Graphviz(dot)がインストールされている必要があります。`sudo apt install graphviz` 等で導入可能。")
