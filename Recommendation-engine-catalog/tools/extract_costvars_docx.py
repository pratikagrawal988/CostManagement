#!/usr/bin/env python3
"""Extract CostVars advisory blocks from FinOps_CostVars_Tooling_v2.docx.

Usage:
  python tools/extract_costvars_docx.py source-docs/FinOps_CostVars_Tooling_v2.docx > extracted/costvars_advisories.json

The script reads the DOCX XML directly, identifies Layer headings and advisory titles,
and emits structured JSON with definition, cost driver, optimization opportunity,
telemetry, tooling, and a stable CVAR-* advisory ID.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ADVISORY_TITLES = [
    'GPU Idle Time','GPU Utilisation Rate','GPU Memory Utilisation','GPU MIG Efficiency','CPU–GPU Stall','Spot Preemption Waste',
    'Model Checkpoint Storage','Training Dataset I/O','Model Weight Storage','Vector DB Cost','KV Cache Efficiency','Redundant Data Copies',
    'Egress Costs','InfiniBand / RDMA Efficiency','NVLink Fabric Efficiency','API Retry Network Waste','Service Mesh Overhead',
    'Cluster Idle Capacity','Over-requested Pod Resources','GPU Scheduling Fragmentation','Container Image Pull Latency','Observability Self-Cost','Namespace / Tenant Policy Overhead',
    'Training Compute (FLOPs)','Fine-tuning Cost','Inference Serving Efficiency','Model Version Proliferation','Quantisation Efficiency','Hyperparameter Sweep Cost',
    'Prompt Token Cost','Completion Token Cost','Context Window Bloat','Embedding Call Cost','Agent Loop Token Waste','Multi-model Routing','Rate Limit Retry Waste',
    'RAG Pipeline Cost','Slow DB Query → GPU Stall','API Latency → Cost Amplifier','Guardrail Processing Cost','Inference Warm Pool Cost','Evaluation Pipeline Cost','Shadow Model Traffic Cost',
]

def docx_paragraphs(path: Path) -> list[str]:
    with ZipFile(path) as zf:
        root = ET.fromstring(zf.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    paragraphs = []
    for p in root.findall('.//w:p', ns):
        line = ''.join((t.text or '') for t in p.findall('.//w:t', ns)).strip()
        if line:
            paragraphs.append(line)
    return paragraphs

def extract(path: Path) -> list[dict]:
    paragraphs = docx_paragraphs(path)
    title_set = set(ADVISORY_TITLES)
    index_by_title = {line: idx for idx, line in enumerate(paragraphs) if line in title_set}
    layer_by_title = {}
    current_layer = ''
    for line in paragraphs:
        if line.startswith('Layer '):
            current_layer = line
        elif line in title_set:
            layer_by_title[line] = current_layer

    advisories = []
    for seq, title in enumerate(ADVISORY_TITLES, start=1):
        start = index_by_title[title]
        next_title_starts = [index_by_title[t] for t in ADVISORY_TITLES if index_by_title[t] > start]
        next_layers = [i for i in range(start + 1, len(paragraphs)) if paragraphs[i].startswith('Layer ')]
        end = min(next_title_starts + next_layers + [len(paragraphs)])
        block = paragraphs[start + 1:end]
        advisories.append({
            'advisory_id': f'CVAR-{seq:03d}',
            'title': title,
            'layer': layer_by_title.get(title, ''),
            'definition': block[0] if block else '',
            'cost_driver': next((x.lstrip('⚡').strip() for x in block if x.startswith('⚡')), ''),
            'optimization_opportunity': next((x.lstrip('✓').strip() for x in block if x.startswith('✓')), ''),
            'telemetry': [x.lstrip('• ').strip() for x in block if x.startswith('•')],
            'tooling': [x.lstrip('◆● ').strip() for x in block if x.startswith(('◆', '●'))],
        })
    return advisories

if __name__ == '__main__':
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('source-docs/FinOps_CostVars_Tooling_v2.docx')
    json.dump(extract(source), sys.stdout, indent=2, ensure_ascii=False)
    print()
