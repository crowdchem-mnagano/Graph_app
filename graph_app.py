# -*- coding: utf-8 -*-
"""
JSON → Graphviz（PNG + SVG）可視化ツール(Visualizer)

概要 / Overview:
このアプリはJSON構造をグラフ形式に変換し、PNGおよびSVG形式で可視化します。
可視化されたグラフを見ておかしなところがないか目視でチャックします。

This app converts a JSON structure into a graph format and visualizes it in both PNG and SVG.
You can visually inspect the generated graph to check for any irregularities or errors.

使い方 / How to use:
1️. JSONファイルをアップロードします。
    → Upload a `.json` file using the uploader.
2️. ルートノードのラベル（例："物性"）を入力します。
    → Enter the root node label (e.g., “Property”).
3️. 「PNG可視化結果」としてツリー構造が描画されます。
    → The PNG graph is displayed inline.
4️. 「SVGを開く」リンクで拡大表示またはダウンロード可能。
    → Click the SVG link to view or download an interactive version.
5️. PNGはダウンロードボタンから保存可能です。
    → You can download the PNG directly.

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

# ───────────── フォント設定 / Font Settings ─────────────
# Cloud環境ではNotoフォントを使用（日本語対応）
# Use Noto Sans CJK JP for Japanese text rendering in cloud environments
os.environ["GDFONTPATH"]  = "/usr/share/fonts/truetype/noto"
os.environ["DOT_FONTPATH"] = "/usr/share/fonts/truetype/noto"
FONT = "Noto Sans CJK JP"

# ───────────── ノード名生成 / Node Naming ─────────────
def _next(n: int) -> str:
    """ノード名をN0001形式で生成 / Generate node names like N0001"""
    return f"N{n:04d}"

# ───────────── JSON構造 → DOT変換 / JSON → DOT ─────────────
def _to_dot(parent: str, data: Any, idx: int, buf: StringIO) -> int:
    """
    JSONの階層構造を再帰的にGraphviz DOT言語へ変換
    Recursively convert JSON structure into Graphviz DOT syntax
    """
    name = _next(idx)

    # --- listの場合 / Case: list ---
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

    # --- dictの場合 / Case: dict ---
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

    # --- スカラー値 / Case: scalar ---
    buf.write(f'{name} [label="{html.escape(str(data))}"];\n')
    buf.write(f'{parent}->{name};\n')
    return idx

# ───────────── JSON → Graphviz出力 / Generate Graphviz Images ─────────────
def json2graph(json_data: Union[Dict, List], png_path: str, svg_path: str, root_label: str = "物性") -> None:
    """
    JSONデータからGraphviz図（PNG + SVG）を生成
    Generate Graphviz diagrams (PNG + SVG) from JSON data
    """
    dot = StringIO()
    dot.write("digraph G {\n")
    dot.write(f'  graph [rankdir=LR, fontname="{FONT}", charset="UTF-8"];\n')
    dot.write(f'  node  [shape=plaintext, fontname="{FONT}"];\n')
    dot.write(f'  edge  [fontname="{FONT}"];\n')
    dot.write(f'  root [label="{root_label}", shape=circle, fontname="{FONT}"];\n')
    _to_dot("root", json_data, 0, dot)
    dot.write("}\n")

    dot_input = dot.getvalue()
    # GraphvizでPNGとSVGを生成 / Generate PNG and SVG via Graphviz
    subprocess.run(["dot", "-Tpng", "-o", png_path], input=dot_input, text=True, check=True)
    subprocess.run(["dot", "-Tsvg", "-o", svg_path], input=dot_input, text=True, check=True)

# ───────────── Streamlitアプリ本体 / Streamlit App UI ─────────────
st.set_page_config(page_title="JSON→Graphviz Visualizer", layout="wide")
st.title("JSON → Graphviz PNG + SVG 可視化ツール / Visualizer (Cloud Version, JP Supported)")

uploaded_file = st.file_uploader("JSONファイルをアップロード / Upload a JSON file", type=["json"])
root_label = st.text_input("物性名を記入(任意) / Enter property name (optional)", value="物性")

if uploaded_file:
    try:
        json_data = json.load(uploaded_file)
        st.success("JSONの読み込みに成功しました。図を表示しています... / JSON successfully loaded. Displaying the graph...")

        # 一時ファイル生成 / Create temporary files for Graphviz output
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png, \
             tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_svg:

            json2graph(json_data, tmp_png.name, tmp_svg.name, root_label)

            # PNG表示 / Display PNG preview
            img = Image.open(tmp_png.name)
            st.image(img, caption="Graphviz PNG 可視化結果 / Visualization Result", use_container_width=True)

            # SVGリンク生成 / Generate clickable SVG link
            with open(tmp_svg.name, "r", encoding="utf-8") as f:
                svg_data = f.read()
            b64 = base64.b64encode(svg_data.encode("utf-8")).decode("utf-8")
            href = f"data:image/svg+xml;base64,{b64}"
            st.markdown(
                f'<a href="{href}" target="_blank" download="json_graph.svg"> SVGを新しいタブで開く／ダウンロード<br>Open or download SVG in a new tab</a>',
                unsafe_allow_html=True
            )

            # PNGダウンロードボタン / PNG download button
            with open(tmp_png.name, "rb") as f:
                st.download_button("PNGをダウンロード / Download PNG", f, file_name="json_graph.png")

    except Exception as e:
        st.error(f"エラーが発生しました / An error occurred: {e}")

# ───────────── 備考 / Notes ─────────────
st.markdown("---")
st.caption("※ packages.txt に 'graphviz' と 'fonts-noto-cjk' を追加してください。SVGはクリックで新しいタブに開きます。\
\nPlease add 'graphviz' and 'fonts-noto-cjk' to packages.txt. SVGs open in a new browser tab.")
