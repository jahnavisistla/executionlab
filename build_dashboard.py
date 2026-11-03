"""Embed pre-aggregated research data into a standalone local dashboard HTML."""
from pathlib import Path

root=Path(__file__).parent
template=(root/"dashboard.html").read_text()
market=(root/"ui_data.json").read_text()
scenarios=(root/"scenario_data.json").read_text()
payload="globalThis.EXECUTIONLAB_MARKET="+market+";\n"+"globalThis.EXECUTIONLAB_SCENARIOS="+scenarios+";"
output=template.replace("/* EXECUTIONLAB_DATA_INJECTION */",payload)
(root/"dashboard_interactive.html").write_text(output)
print("Created dashboard_interactive.html")
