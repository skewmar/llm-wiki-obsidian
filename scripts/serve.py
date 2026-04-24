#!/usr/bin/env python3
"""
serve.py — Local knowledge graph visualization.

Reads wiki/ and renders an interactive D3.js force-directed graph on localhost.
Nodes are colored by type, sized by connections, clickable for detail.

Usage:
    python scripts/serve.py
    python scripts/serve.py --port 5050
    python scripts/serve.py --no-browser
"""

import re
import json
import argparse
import webbrowser
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

ROOT = Path(__file__).parent.parent
WIKI_DIR = ROOT / "wiki"

NODE_COLORS = {
    "entity":     "#58a6ff",
    "concept":    "#bc8cff",
    "comparison": "#f97316",
    "summary":    "#3fb950",
}
DEFAULT_COLOR = "#8b949e"


# ── Graph builder ──────────────────────────────────────────────────────────────

def _frontmatter(text: str) -> dict:
    fm = {}
    if not text.startswith("---"):
        return fm
    end = text.find("---", 3)
    if end == -1:
        return fm
    for line in text[3:end].split("\n"):
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def _title(text: str) -> str:
    for line in text.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _description(text: str) -> str:
    for line in text.split("\n"):
        if line.startswith("> "):
            return line[2:].strip()
    return ""


def build_graph() -> dict:
    nodes = {}
    SUBDIRS = {
        "entities":    "entity",
        "concepts":    "concept",
        "comparisons": "comparison",
        "summaries":   "summary",
    }

    for subdir, fallback_type in SUBDIRS.items():
        d = WIKI_DIR / subdir
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            if f.name.startswith("_"):
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            fm = _frontmatter(text)
            ntype = fm.get("type", fallback_type)
            nodes[f.stem] = {
                "id":          f.stem,
                "label":       _title(text) or f.stem.replace("-", " ").title(),
                "type":        ntype,
                "domain":      fm.get("domain", "general"),
                "description": _description(text),
                "maturity":    fm.get("maturity", ""),
                "status":      fm.get("status", ""),
                "color":       NODE_COLORS.get(ntype, DEFAULT_COLOR),
                "content":     text[:4000],
            }

    # Edges: [[wikilinks]] and [text](../type/slug.md) and entities_mentioned frontmatter
    wl  = re.compile(r'\[\[([^\]|#\n]+)')
    ml  = re.compile(r'\[[^\]]+\]\(\.\.?/(?:entities|concepts|comparisons|summaries)/([^).]+)\.md\)')
    em  = re.compile(r"entities_mentioned:\s*\[([^\]]*)\]")

    seen, links = set(), []

    def _add(src, tgt):
        if tgt in nodes and tgt != src:
            key = tuple(sorted([src, tgt]))
            if key not in seen:
                seen.add(key)
                links.append({"source": src, "target": tgt})

    for subdir in SUBDIRS:
        d = WIKI_DIR / subdir
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            if f.name.startswith("_"):
                continue
            if f.stem not in nodes:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for m in wl.finditer(text):
                _add(f.stem, m.group(1).strip())
            for m in ml.finditer(text):
                _add(f.stem, m.group(1).strip())

    summaries_dir = WIKI_DIR / "summaries"
    if summaries_dir.exists():
        for f in summaries_dir.glob("*.md"):
            if f.name.startswith("_") or f.stem not in nodes:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            m = em.search(text)
            if m:
                for pair in re.findall(r"'([^']+)'|\"([^\"]+)\"", m.group(1)):
                    slug = (pair[0] or pair[1]).lower().replace(" ", "-")
                    _add(f.stem, slug)

    domains = sorted(set(n["domain"] for n in nodes.values()))
    types   = sorted(set(n["type"]   for n in nodes.values()))

    return {
        "nodes": list(nodes.values()),
        "links": links,
        "meta":  {
            "total_nodes": len(nodes),
            "total_links": len(links),
            "domains": domains,
            "types":   types,
        },
    }


# ── HTML ───────────────────────────────────────────────────────────────────────

def build_html(graph: dict) -> str:
    graph_json = json.dumps(graph)
    colors_json = json.dumps(NODE_COLORS)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Knowledge Graph</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: #0d1117;
  color: #e6edf3;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}}
#topbar {{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #161b22;
  border-bottom: 1px solid #30363d;
  flex-shrink: 0;
  flex-wrap: wrap;
}}
#topbar h1 {{ font-size: 14px; font-weight: 600; color: #e6edf3; white-space: nowrap; }}
#search {{
  flex: 1;
  min-width: 140px;
  max-width: 280px;
  padding: 5px 10px;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
  color: #e6edf3;
  font-size: 13px;
  outline: none;
}}
#search:focus {{ border-color: #58a6ff; }}
#search::placeholder {{ color: #484f58; }}
.filter-group {{
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}}
.filter-label {{
  font-size: 12px;
  color: #8b949e;
}}
.chip {{
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1.5px solid transparent;
  transition: opacity 0.15s, border-color 0.15s;
  user-select: none;
}}
.chip.active {{ border-color: currentColor; }}
.chip.inactive {{ opacity: 0.35; }}
.chip .dot {{
  width: 8px; height: 8px;
  border-radius: 50%;
  background: currentColor;
}}
#stats {{
  font-size: 12px;
  color: #484f58;
  white-space: nowrap;
  margin-left: auto;
}}
#main {{
  display: flex;
  flex: 1;
  overflow: hidden;
}}
#graph-container {{
  flex: 1;
  position: relative;
  overflow: hidden;
}}
svg {{
  width: 100%;
  height: 100%;
  cursor: grab;
}}
svg:active {{ cursor: grabbing; }}
.link {{
  stroke: #30363d;
  stroke-width: 1.2;
  stroke-opacity: 0.7;
  transition: stroke-opacity 0.2s;
}}
.link.highlighted {{ stroke: #8b949e; stroke-opacity: 1; stroke-width: 1.8; }}
.link.dimmed {{ stroke-opacity: 0.08; }}
.node-group {{ cursor: pointer; }}
.node-circle {{
  stroke: #161b22;
  stroke-width: 1.5;
  transition: stroke 0.15s, stroke-width 0.15s;
}}
.node-group:hover .node-circle, .node-group.selected .node-circle {{
  stroke: #fff;
  stroke-width: 2.5;
}}
.node-group.dimmed {{ opacity: 0.15; }}
.node-label {{
  font-size: 10px;
  fill: #8b949e;
  pointer-events: none;
  text-anchor: middle;
  transition: fill 0.15s;
}}
.node-group:hover .node-label, .node-group.selected .node-label {{
  fill: #e6edf3;
  font-weight: 600;
}}
.node-group.dimmed .node-label {{ fill: #30363d; }}
#tooltip {{
  position: absolute;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 12px;
  max-width: 280px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s;
  z-index: 100;
  line-height: 1.5;
}}
#tooltip.visible {{ opacity: 1; }}
#tooltip .tt-title {{ font-weight: 600; color: #e6edf3; margin-bottom: 4px; }}
#tooltip .tt-type {{ color: #8b949e; font-size: 11px; margin-bottom: 4px; }}
#tooltip .tt-desc {{ color: #c9d1d9; }}
#detail {{
  width: 0;
  overflow: hidden;
  transition: width 0.25s ease;
  background: #161b22;
  border-left: 1px solid #30363d;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}}
#detail.open {{ width: 340px; }}
#detail-header {{
  padding: 14px 16px 10px;
  border-bottom: 1px solid #30363d;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}}
#detail-type-dot {{
  width: 10px; height: 10px;
  border-radius: 50%;
  margin-top: 4px;
  flex-shrink: 0;
}}
#detail-title {{ font-size: 15px; font-weight: 600; color: #e6edf3; line-height: 1.3; }}
#detail-meta {{ font-size: 11px; color: #8b949e; margin-top: 3px; }}
#detail-close {{
  margin-left: auto;
  background: none;
  border: none;
  color: #8b949e;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  padding: 0 2px;
  flex-shrink: 0;
}}
#detail-close:hover {{ color: #e6edf3; }}
#detail-body {{
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px;
  font-size: 12px;
  line-height: 1.7;
  color: #c9d1d9;
}}
#detail-body::-webkit-scrollbar {{ width: 4px; }}
#detail-body::-webkit-scrollbar-track {{ background: transparent; }}
#detail-body::-webkit-scrollbar-thumb {{ background: #30363d; border-radius: 2px; }}
#detail-description {{
  color: #8b949e;
  font-style: italic;
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid #21262d;
}}
#detail-connections {{
  margin-bottom: 14px;
}}
#detail-connections h4 {{
  font-size: 11px;
  font-weight: 600;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}}
.conn-item {{
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 4px 0;
  cursor: pointer;
  border-radius: 4px;
}}
.conn-item:hover {{ color: #e6edf3; }}
.conn-dot {{ width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }}
.conn-label {{ font-size: 12px; }}
#detail-content {{
  font-size: 11px;
  color: #6e7681;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-word;
  border-top: 1px solid #21262d;
  padding-top: 14px;
  margin-top: 14px;
}}
#empty-state {{
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #484f58;
}}
#empty-state h2 {{ font-size: 18px; margin-bottom: 10px; color: #8b949e; }}
#empty-state p {{ font-size: 13px; line-height: 1.6; }}
#empty-state code {{ background: #161b22; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
#zoom-controls {{
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}}
.zoom-btn {{
  width: 30px; height: 30px;
  background: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  color: #8b949e;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s, border-color 0.15s;
}}
.zoom-btn:hover {{ color: #e6edf3; border-color: #8b949e; }}
</style>
</head>
<body>

<div id="topbar">
  <h1>🧠 Knowledge Graph</h1>
  <input id="search" type="text" placeholder="Search nodes…">
  <div class="filter-group">
    <span class="filter-label">Show:</span>
    <div id="type-filters"></div>
  </div>
  <div id="stats"></div>
</div>

<div id="main">
  <div id="graph-container">
    <svg id="svg"></svg>
    <div id="tooltip"></div>
    <div id="empty-state" style="display:none">
      <h2>No wiki content yet</h2>
      <p>Run the ingest pipeline first:<br>
      <code>python scripts/ingest.py</code></p>
    </div>
    <div id="zoom-controls">
      <button class="zoom-btn" id="zoom-in">+</button>
      <button class="zoom-btn" id="zoom-fit">⊡</button>
      <button class="zoom-btn" id="zoom-out">−</button>
    </div>
  </div>
  <div id="detail">
    <div id="detail-header">
      <div id="detail-type-dot"></div>
      <div>
        <div id="detail-title"></div>
        <div id="detail-meta"></div>
      </div>
      <button id="detail-close">×</button>
    </div>
    <div id="detail-body">
      <div id="detail-description"></div>
      <div id="detail-connections">
        <h4>Connections</h4>
        <div id="detail-conn-list"></div>
      </div>
      <pre id="detail-content"></pre>
    </div>
  </div>
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const GRAPH = {graph_json};
const COLORS = {colors_json};

const nodes = GRAPH.nodes.map(d => ({{...d}}));
const links = GRAPH.links.map(d => ({{...d}}));
const meta  = GRAPH.meta;

// ── Empty state ──────────────────────────────────────────────────────────────
if (nodes.length === 0) {{
  document.getElementById("empty-state").style.display = "block";
  document.getElementById("stats").textContent = "0 nodes";
}} else {{
  document.getElementById("stats").textContent =
    `${{meta.total_nodes}} nodes · ${{meta.total_links}} edges`;
}}

// ── Type filter chips ────────────────────────────────────────────────────────
const typeColors = {{
  entity:     "#58a6ff",
  concept:    "#bc8cff",
  comparison: "#f97316",
  summary:    "#3fb950",
}};
const typeLabels = {{
  entity: "Entities", concept: "Concepts",
  comparison: "Comparisons", summary: "Summaries",
}};

const activeTypes = new Set(meta.types);
const filtersEl = document.getElementById("type-filters");
filtersEl.style.display = "flex";
filtersEl.style.gap = "6px";

meta.types.forEach(t => {{
  const chip = document.createElement("div");
  const color = typeColors[t] || "#8b949e";
  chip.className = "chip active";
  chip.style.color = color;
  chip.style.background = color + "18";
  chip.innerHTML = `<span class="dot"></span>${{typeLabels[t] || t}}`;
  chip.dataset.type = t;
  chip.addEventListener("click", () => {{
    if (activeTypes.has(t)) {{
      activeTypes.delete(t);
      chip.classList.remove("active");
      chip.classList.add("inactive");
    }} else {{
      activeTypes.add(t);
      chip.classList.add("active");
      chip.classList.remove("inactive");
    }}
    applyFilters();
  }});
  filtersEl.appendChild(chip);
}});

// ── D3 setup ─────────────────────────────────────────────────────────────────
const svg = d3.select("#svg");
const container = document.getElementById("graph-container");
const g = svg.append("g");

const zoom = d3.zoom()
  .scaleExtent([0.1, 4])
  .on("zoom", e => g.attr("transform", e.transform));
svg.call(zoom);

// Degree map for sizing
const degreeMap = {{}};
nodes.forEach(n => {{ degreeMap[n.id] = 0; }});
links.forEach(l => {{
  const s = typeof l.source === "object" ? l.source.id : l.source;
  const t = typeof l.target === "object" ? l.target.id : l.target;
  degreeMap[s] = (degreeMap[s] || 0) + 1;
  degreeMap[t] = (degreeMap[t] || 0) + 1;
}});

const nodeRadius = d => Math.max(6, Math.min(22, 6 + (degreeMap[d.id] || 0) * 2.2));

// ── Simulation ────────────────────────────────────────────────────────────────
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(d => {{
    const st = typeof d.source === "object" ? d.source.type : "entity";
    const tt = typeof d.target === "object" ? d.target.type : "entity";
    return (st === "summary" || tt === "summary") ? 100 : 75;
  }}))
  .force("charge", d3.forceManyBody().strength(d => -120 - (degreeMap[d.id] || 0) * 15))
  .force("center", d3.forceCenter(container.clientWidth / 2, container.clientHeight / 2))
  .force("collision", d3.forceCollide().radius(d => nodeRadius(d) + 6));

// ── Draw links ────────────────────────────────────────────────────────────────
const linkSel = g.append("g").attr("class","links")
  .selectAll("line")
  .data(links)
  .join("line")
  .attr("class","link");

// ── Draw nodes ────────────────────────────────────────────────────────────────
const nodeSel = g.append("g").attr("class","nodes")
  .selectAll("g")
  .data(nodes)
  .join("g")
  .attr("class","node-group")
  .call(d3.drag()
    .on("start", (e, d) => {{
      if (!e.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x; d.fy = d.y;
    }})
    .on("drag",  (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
    .on("end",   (e, d) => {{
      if (!e.active) simulation.alphaTarget(0);
      d.fx = null; d.fy = null;
    }})
  );

nodeSel.append("circle")
  .attr("class", "node-circle")
  .attr("r", d => nodeRadius(d))
  .attr("fill", d => d.color);

nodeSel.append("text")
  .attr("class", "node-label")
  .text(d => {{
    const deg = degreeMap[d.id] || 0;
    if (deg >= 2 || nodes.length < 40) return d.label;
    return "";
  }})
  .attr("dy", d => nodeRadius(d) + 13);

// ── Tooltip ───────────────────────────────────────────────────────────────────
const tooltip = document.getElementById("tooltip");

nodeSel
  .on("mouseover", (e, d) => {{
    tooltip.innerHTML = `
      <div class="tt-title">${{d.label}}</div>
      <div class="tt-type" style="color:${{d.color}}">${{d.type}}${{d.domain !== "general" ? " · " + d.domain : ""}}</div>
      ${{d.description ? `<div class="tt-desc">${{d.description}}</div>` : ""}}
    `;
    tooltip.classList.add("visible");
    positionTooltip(e);
  }})
  .on("mousemove", positionTooltip)
  .on("mouseout",  () => tooltip.classList.remove("visible"))
  .on("click",     (e, d) => {{ e.stopPropagation(); selectNode(d); }});

function positionTooltip(e) {{
  const rect = container.getBoundingClientRect();
  let x = e.clientX - rect.left + 14;
  let y = e.clientY - rect.top - 10;
  if (x + 300 > container.clientWidth)  x = e.clientX - rect.left - 300;
  if (y + 160 > container.clientHeight) y = e.clientY - rect.top  - 160;
  tooltip.style.left = x + "px";
  tooltip.style.top  = y + "px";
}}

// ── Tick ──────────────────────────────────────────────────────────────────────
simulation.on("tick", () => {{
  linkSel
    .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  nodeSel.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
}});

// ── Selection / dimming ───────────────────────────────────────────────────────
let selectedId = null;

function selectNode(d) {{
  if (selectedId === d.id) {{
    clearSelection();
    return;
  }}
  selectedId = d.id;

  const neighborIds = new Set([d.id]);
  links.forEach(l => {{
    const s = l.source.id || l.source;
    const t = l.target.id || l.target;
    if (s === d.id) neighborIds.add(t);
    if (t === d.id) neighborIds.add(s);
  }});

  nodeSel
    .classed("selected", n => n.id === d.id)
    .classed("dimmed",   n => !neighborIds.has(n.id));
  linkSel
    .classed("highlighted", l => {{
      const s = l.source.id || l.source;
      const t = l.target.id || l.target;
      return s === d.id || t === d.id;
    }})
    .classed("dimmed", l => {{
      const s = l.source.id || l.source;
      const t = l.target.id || l.target;
      return s !== d.id && t !== d.id;
    }});

  showDetail(d, neighborIds);
}}

function clearSelection() {{
  selectedId = null;
  nodeSel.classed("selected dimmed", false);
  linkSel.classed("highlighted dimmed", false);
  document.getElementById("detail").classList.remove("open");
}}

svg.on("click", clearSelection);
document.getElementById("detail-close").addEventListener("click", clearSelection);

// ── Detail panel ──────────────────────────────────────────────────────────────
function showDetail(d, neighborIds) {{
  const dot   = document.getElementById("detail-type-dot");
  const title = document.getElementById("detail-title");
  const meta  = document.getElementById("detail-meta");
  const desc  = document.getElementById("detail-description");
  const conn  = document.getElementById("detail-conn-list");
  const body  = document.getElementById("detail-content");

  dot.style.background = d.color;
  title.textContent = d.label;

  const metaParts = [d.type];
  if (d.domain && d.domain !== "general") metaParts.push(d.domain);
  if (d.maturity) metaParts.push(d.maturity);
  if (d.status)   metaParts.push(d.status);
  meta.textContent = metaParts.join(" · ");

  desc.textContent = d.description || "";
  desc.style.display = d.description ? "block" : "none";

  const neighbors = nodes.filter(n => neighborIds.has(n.id) && n.id !== d.id);
  conn.innerHTML = neighbors.length
    ? neighbors.map(n => `
        <div class="conn-item" data-id="${{n.id}}">
          <span class="conn-dot" style="background:${{n.color}}"></span>
          <span class="conn-label">${{n.label}}</span>
        </div>`).join("")
    : `<div style="color:#484f58;font-size:11px">No connections yet</div>`;

  conn.querySelectorAll(".conn-item").forEach(el => {{
    el.addEventListener("click", () => {{
      const target = nodes.find(n => n.id === el.dataset.id);
      if (target) selectNode(target);
    }});
  }});

  // Strip frontmatter from displayed content
  let content = d.content || "";
  if (content.startsWith("---")) {{
    const end = content.indexOf("---", 3);
    if (end !== -1) content = content.slice(end + 3).trim();
  }}
  body.textContent = content;

  document.getElementById("detail").classList.add("open");
}}

// ── Search ────────────────────────────────────────────────────────────────────
document.getElementById("search").addEventListener("input", function () {{
  const q = this.value.trim().toLowerCase();
  if (!q) {{
    nodeSel.classed("dimmed", false);
    linkSel.classed("dimmed", false);
    nodeSel.select("text").text(d => {{
      const deg = degreeMap[d.id] || 0;
      return (deg >= 2 || nodes.length < 40) ? d.label : "";
    }});
    return;
  }}
  const matching = new Set(nodes.filter(n =>
    n.label.toLowerCase().includes(q) ||
    n.description.toLowerCase().includes(q) ||
    n.domain.toLowerCase().includes(q)
  ).map(n => n.id));

  nodeSel.classed("dimmed", d => !matching.has(d.id));
  linkSel.classed("dimmed", true);
  nodeSel.select("text").text(d => matching.has(d.id) ? d.label : "");
}});

// ── Type filters ──────────────────────────────────────────────────────────────
function applyFilters() {{
  nodeSel.style("display", d => activeTypes.has(d.type) ? null : "none");
  linkSel.style("display", l => {{
    const s = l.source.id || l.source;
    const t = l.target.id || l.target;
    const sn = nodes.find(n => n.id === s);
    const tn = nodes.find(n => n.id === t);
    return (sn && tn && activeTypes.has(sn.type) && activeTypes.has(tn.type)) ? null : "none";
  }});
}}

// ── Zoom controls ─────────────────────────────────────────────────────────────
document.getElementById("zoom-in").addEventListener("click",
  () => svg.transition().call(zoom.scaleBy, 1.4));
document.getElementById("zoom-out").addEventListener("click",
  () => svg.transition().call(zoom.scaleBy, 0.7));
document.getElementById("zoom-fit").addEventListener("click", fitView);

function fitView() {{
  const bounds = g.node().getBBox();
  if (!bounds.width) return;
  const w = container.clientWidth, h = container.clientHeight;
  const scale = 0.85 / Math.max(bounds.width / w, bounds.height / h);
  const tx = w / 2 - scale * (bounds.x + bounds.width  / 2);
  const ty = h / 2 - scale * (bounds.y + bounds.height / 2);
  svg.transition().duration(600)
    .call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
}}

// Auto-fit after simulation settles
simulation.on("end", fitView);

// ── Resize ────────────────────────────────────────────────────────────────────
window.addEventListener("resize", () => {{
  simulation.force("center",
    d3.forceCenter(container.clientWidth / 2, container.clientHeight / 2));
  simulation.alpha(0.1).restart();
}});
</script>
</body>
</html>"""


# ── HTTP server ────────────────────────────────────────────────────────────────

_graph_cache = None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress access logs

    def do_GET(self):
        global _graph_cache
        if self.path in ("/", "/index.html"):
            html = build_html(_graph_cache).encode()
            self._respond(200, "text/html; charset=utf-8", html)
        elif self.path == "/api/graph":
            data = json.dumps(_graph_cache).encode()
            self._respond(200, "application/json", data)
        elif self.path == "/api/refresh":
            _graph_cache = build_graph()
            data = json.dumps({"ok": True, "nodes": len(_graph_cache["nodes"])}).encode()
            self._respond(200, "application/json", data)
        else:
            self._respond(404, "text/plain", b"Not found")

    def _respond(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


def main():
    global _graph_cache

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    print("📊 Building graph from wiki/...")
    _graph_cache = build_graph()
    n = len(_graph_cache["nodes"])
    e = len(_graph_cache["links"])

    if n == 0:
        print("  ⚠️  No wiki content found. Run 'python scripts/ingest.py' first.")
    else:
        print(f"  → {n} nodes, {e} edges across domains: {', '.join(_graph_cache['meta']['domains'])}")

    url = f"http://localhost:{args.port}"
    print(f"  → Serving at {url}  (Ctrl+C to stop)")
    print(f"  → Refresh graph after ingest: {url}/api/refresh\n")

    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    server = HTTPServer(("localhost", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")


if __name__ == "__main__":
    main()
