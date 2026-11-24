#!/usr/bin/env python3
"""
Результат 2 (MCP-сервер: mcp_server/server.py):
Реалізує Model Context Protocol (JSON-RPC 2.0: `tools/list`, `tools/call`)
для 3 read-only інструментів сховища знань із валідацією описів (anti tool-poisoning).
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.tools import search_forest_docs, query_knowledge_graph, query_olap_metric
from agent.security import validate_tool_descriptor

MCP_TOOLS = [
    {
        "name": "search_forest_docs",
        "description": "Read-only гібридний пошук по корпусу лісогосподарських документів.",
        "inputSchema": {
            "type": "object",
            "required": ["query"],
            "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "maximum": 5}},
        },
        "handler": search_forest_docs,
    },
    {
        "name": "query_knowledge_graph",
        "description": "Read-only пошук виділів і альтернатив конфліктів у графі знань.",
        "inputSchema": {
            "type": "object",
            "required": ["entity_code"],
            "properties": {"entity_code": {"type": "string"}, "include_alternatives": {"type": "boolean"}},
        },
        "handler": query_knowledge_graph,
    },
    {
        "name": "query_olap_metric",
        "description": "Read-only обчислення затвердженої метрики OLAP через семантичний шар.",
        "inputSchema": {
            "type": "object",
            "required": ["metric_name"],
            "properties": {"metric_name": {"type": "string"}, "group_by": {"type": "string"}, "year": {"type": "integer"}},
        },
        "handler": query_olap_metric,
    },
]


def handle_rpc(request: dict) -> dict:
    method = request.get("method")
    rid = request.get("id", 1)
    if method == "tools/list":
        listed = []
        for t in MCP_TOOLS:
            ok, _ = validate_tool_descriptor(t["description"])
            if ok:
                listed.append({"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]})
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": listed}}
    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        for t in MCP_TOOLS:
            if t["name"] == name:
                return {"jsonrpc": "2.0", "id": rid, "result": t["handler"](**args)}
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown tool: {name}"}}
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


if __name__ == "__main__":
    r_list = handle_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    r_call = handle_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                         "params": {"name": "query_olap_metric", "arguments": {"metric_name": "fsc_certified_share_pct", "year": 2025}}})
    print(f"MCP tools/list: {len(r_list['result']['tools'])} tools registered")
    print(f"MCP tools/call: {r_call['result']['rows']}")
