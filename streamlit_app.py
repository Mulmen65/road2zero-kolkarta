"""Kolkarta Malmö i Streamlit.

Visar samma sida som index.html (karta, parametrar, tabell). Data och rasterlager bäddas in i sidan,
eftersom Streamlits komponent inte kan läsa repots filer med fetch. All räkning sker i webbläsaren.
"""
import base64, json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROT = Path(__file__).parent

st.set_page_config(page_title="Kolkarta Malmö", layout="wide")


def filversion() -> str:
    """Ändras när någon av sidans filer ändras, så att cachen byggs om efter en push."""
    import hashlib
    h = hashlib.sha256()
    for f in sorted([ROT / "index.html", *ROT.glob("data/*.geojson"), *ROT.glob("lager/*")]):
        h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()


@st.cache_data
def sida(version: str) -> str:
    inline = {}
    for namn in ["lager/lager.json", "data/omraden.geojson", "data/deso.geojson"]:
        inline[namn] = json.loads((ROT / namn).read_text(encoding="utf-8"))
    for lager in inline["lager/lager.json"]:
        png = (ROT / lager["fil"]).read_bytes()
        inline[lager["fil"]] = "data:image/png;base64," + base64.b64encode(png).decode()
    html = (ROT / "index.html").read_text(encoding="utf-8")
    data = "<script>window.__INLINE=" + json.dumps(inline, ensure_ascii=False) + ";</script>\n"
    return html.replace('<script src="https://cdnjs', data + '<script src="https://cdnjs', 1)


components.html(sida(filversion()), height=1900, scrolling=True)
