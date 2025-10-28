# -*- coding: utf-8 -*-
"""
Streamlitアプリ版：JSON → Graphviz(PNG+SVG)＋PyVis(ドラッグ可) 可視化（Cloud用：fonts-noto-cjk対応）
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
import networkx as nx
from pyvis.network import Network

# ────────── フォント設定 ──────────
os.environ["GDFONTPATH"]  = "/usr/share/fonts/truetype/noto"
os.environ["DOT_FONTPATH"] = "/usr/share/fonts/truetype/noto"
FONT = "Noto Sans CJK JP"

# ────────── JSON構造 → DOT ──────────
def _next(n: int) -> str:
    return f"N{n:04d}"

def _to_dot(parent: str, data: Any, idx: int, buf: StringIO) -> int:
    name = _next(idx)
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

def json2graphviz(json_data: Union[Dict, List], png_path: str, svg_path: str, root_label: str = "物性") -> None:
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

# ────────── PyVis 用：JSON → NetworkX → PyVis ──────────
def add_nodes_edges(G, parent, data):
    if isinstance(data, dict):
        for k, v in data.items():
            child = f"{parent}.{k}"
            G.add_node(child, label=str(k))
            G.add_edge(parent, child)
            add_nodes_edges(G, child, v)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            child = f"{parent}[{i}]"
            G.add_node(child, label=f"[{i}]")
            G.add_edge(parent, child)
            add_nodes_edges(G, child, item)
    else:
        val = str(data)
        child = f"{parent}:{val}"
        G.add_node(child, label=val, color="#ffd966")
        G.add_edge(parent, child)

def json2pyvis(json_data: Union[Dict, List]):
    G = nx.DiGraph()
    G.add_node("root", label="root")
    add_nodes_edges(G, "root", json_data)
    nt = Network(height="750px", width="100%", directed=True, bgcolor="#ffffff", font_color="black")
    nt.from_nx(G)
    nt.force_atlas_2based()
    tmp_html = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
    nt.save_graph(tmp_html.name)
    return tmp_html.name

# ────────── Streamlit アプリ ──────────
st.set_page_config(page_title="JSON→Graphviz+PyVis 可視化", layout="wide")
st.title("🧩 JSON → Graphviz（静的）＋ PyVis（ドラッグ可）可視化ツール")

uploaded_file = st.file_uploader("JSONファイルをアップロード", type=["json"])
root_label = st.text_input("ルートノードのラベル（例：物性）", value="物性")

if uploaded_file:
    try:
        json_data = json.load(uploaded_file)
        st.success("✅ JSONの読み込みに成功しました。")

        # ------- Graphviz 生成 -------
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png, \
             tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_svg:
            json2graphviz(json_data, tmp_png.name, tmp_svg.name, root_label)
            img = Image.open(tmp_png.name)
            st.subheader("🖼 Graphviz（高解像度PNG）")
            st.image(img, caption="Graphviz可視化結果", use_container_width=True)

            # SVG リンク生成
            with open(tmp_svg.name, "r", encoding="utf-8") as f:
                svg_data = f.read()
            b64 = base64.b64encode(svg_data.encode("utf-8")).decode("utf-8")
            href = f"data:image/svg+xml;base64,{b64}"
            st.markdown(
                f'<a href="{href}" target="_blank" download="json_graph.svg">🔗 SVGを新しいタブで開く／ダウンロード</a>',
                unsafe_allow_html=True
            )

        # ------- PyVis 生成 -------
        st.subheader("🧭 PyVis（ドラッグで動かせるインタラクティブ版）")
        html_path = json2pyvis(json_data)
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        st.components.v1.html(html_content, height=750, scrolling=True)

        # PNG ダウンロード
        with open(tmp_png.name, "rb") as f:
            st.download_button("📥 PNGをダウンロード", f, file_name="json_graph.png")

    except Exception as e:
        st.error(f"❌ エラーが発生しました: {e}")

st.markdown("---")
st.caption("※ Graphviz と PyVis の両方を利用。PyVisはノードをドラッグ移動・ズームできます。packages.txtに 'fonts-noto-cjk' を追加してください。")
