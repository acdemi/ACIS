"""AgriKG 知识图谱包。

- ``kg/mcp_server.py``：基于 Neo4j + AgriKG 的知识图谱 MCP Server（独立进程）。
- ``kg_adapter.py``（项目根）：Judge 使用的混合 KG 检索接口（Neo4j 优先、DISEASE_DB 兜底）。
- ``scripts/import_agrikg.py``：将 AgriKG 真实数据导入 Neo4j。

真实图谱 schema 见 ``scripts/AGRiKG_SETUP.md``。
"""
