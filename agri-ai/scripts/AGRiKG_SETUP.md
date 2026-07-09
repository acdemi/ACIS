# AgriKG 集成指南

将 [qq547276542/Agriculture_KnowledgeGraph](https://github.com/qq547276542/Agriculture_KnowledgeGraph)
（AgriKG）真实数据接入本系统的知识图谱 MCP Server。

## 0. 重要：AgriKG 的真实数据结构

早期版本的 `import_agrikg.py` / `knowledge_graph_mcp.py` 假设了 `crop.json / disease.json /
pest.json / pesticide.json / relations.json` 这样的结构化文件——**这些文件在 AgriKG 仓库中并不
存在**，因此旧脚本根本无法运行。AgriKG 的真实数据是一个**通用知识图谱**：

| 数据文件 | 内容 |
|----------|------|
| `MyCrawler/MyCrawler/data/hudong_pedia*.json(.zip)` | 互动百科爬取的农业实体（约 15 万条），含 title/detail/baseInfoKeyList/baseInfoValueList |
| `attributes.csv` | 实体属性三元组 `Entity,AttributeName,Attribute` |
| `wikidataSpider/wikidataProcessing/new_node.csv` | wikidata 补充节点 `title` |
| `wikidataSpider/wikidataProcessing/wikidata_relation.csv` | `HudongItem1,relation,HudongItem2` |
| `wikidataSpider/wikidataProcessing/wikidata_relation2.csv` | `HudongItem,relation,NewNode` |

导入后的 Neo4j 图谱 schema：

```
节点 :HudongItem {title, detail, url, image, openTypeList, baseInfoKeyList, baseInfoValueList}
节点 :NewNode {title}
标签 :Disease / :Pest   （导入时按标题关键词为部分 HudongItem 追加，便于检索）
关系 (:HudongItem|:NewNode)-[:RELATION {type}]->(:HudongItem|:NewNode)
```

> AgriKG **没有**结构化的「温度/湿度/症状/病原/农药」字段，这些信息以自然语言形式存在于
> `detail` 与 `baseInfoKeyList/baseInfoValueList` 中。`knowledge_graph_mcp.py` 已据此重写查询逻辑。

## 一、环境准备（Windows）

### 1. 安装 Neo4j

**方法 A：Neo4j Desktop（推荐）** — https://neo4j.com/download/ ，创建本地数据库（默认密码
`neo4j`），启动并确认 7687 端口可用。

**方法 B：Docker**
```powershell
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/neo4j neo4j:5
```

### 2. 安装 Python 依赖
```powershell
pip install neo4j
# 如需直接以 MCP 进程运行，还需 mcp：
pip install mcp
```

### 3. 获取 AgriKG 数据

把仓库放到 `agri-agent-mvp/Agriculture_KnowledgeGraph-master`（两种方式任选其一）：

```powershell
cd agri-agent-mvp
# 方式 A：git clone
git clone https://github.com/qq547276542/Agriculture_KnowledgeGraph.git Agriculture_KnowledgeGraph-master --depth 1

# 方式 B：用已下载的 zip 解压
# Expand-Archive E:\download\Agriculture_KnowledgeGraph-master.zip -DestinationPath .
# 解压后会得到 agri-agent-mvp\Agriculture_KnowledgeGraph-master\...
```

> 仓库内的 `hudong_pedia*.json` 是 zip 压缩的。导入脚本会在首次运行时**自动解压**，无需手动处理。

## 二、导入数据到 Neo4j

```powershell
cd agri-agent-mvp
# 完整导入（约 15 万实体，首次几分钟）
python scripts\import_agrikg.py --repo-dir .\Agriculture_KnowledgeGraph-master --clean --yes

# 或：只导入病害/虫害相关实体（图小、导入快，适合 MVP 先跑通）
python scripts\import_agrikg.py --repo-dir .\Agriculture_KnowledgeGraph-master --disease-only --clean --yes
```

可选参数：
- `--repo-dir` AgriKG 仓库根目录（默认 `./Agriculture_KnowledgeGraph-master`）
- `--disease-only` 仅导入标题含病害/虫害关键词的实体
- `--batch-size N` 批量写入大小（默认 1000）
- `--clean` 清空现有图谱后导入；`--yes` 跳过交互确认

环境变量（可选）：`NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD`
（默认 `bolt://localhost:7687` / `neo4j` / `neo4j`）

导入结束会打印节点/关系统计，例如：
```
:HudongItem: 149930
:NewNode: 30000+
:Disease: ...
:RELATION: ...
```

## 三、启动测试

```powershell
# 1. 确认 Neo4j 已启动
# 2. 单独跑知识图谱 MCP Server（stdio）
python knowledge_graph_mcp.py

# 3. 或在 main_v3.py 中集成测试
$env:DEEPSEEK_API_KEY = "sk-xxx"
python main_v3.py
```

Neo4j 不可用时，MCP 自动降级到内置的 `FALLBACK_DISEASES` 硬编码规则库，保证系统不中断。

## 四、MCP 工具与真实图谱的对应

| 工具 | 实现（Neo4j 模式） | 说明 |
|------|--------------------|------|
| `search_disease(symptoms, crop)` | 在 `:Disease` 中按 detail/baseInfo 做症状关键词评分 | 自然语言匹配，非精确字段 |
| `get_disease_chain(name)` | 取 `:Disease` 节点的 detail、base_info、`[:RELATION]` 邻居 | 返回百科详情 + 属性 + 关系 |
| `list_crop_diseases(crop)` | `:Disease` 中标题/detail 含该作物 | |
| `search_pesticide(name)` | 该病害 `[:RELATION]` 邻居中防治/药剂相关项 + base_info 防治字段 | AgriKG 无结构化农药，为尽力而为 |
| `search_by_conditions(temp,humid)` | **始终用 fallback** | AgriKG 无温湿度字段 |
| `search_entity(title)` | 模糊搜索 `:HudongItem/:NewNode` | 通用检索 |
| `get_entity_relations(title)` | 出入 `[:RELATION]` 邻居 | 通用检索 |
| `find_entity_path(e1,e2)` | `shortestPath`（≤6 跳） | 通用检索 |
| `get_kg_status()` | 连接状态 + 节点/关系计数 | |

## 五、文件清单

| 文件 | 作用 |
|------|------|
| `knowledge_graph_mcp.py` | 基于 Neo4j 的知识图谱 MCP Server（查询真实 AgriKG schema，Neo4j 不可用时自动降级） |
| `scripts/import_agrikg.py` | 将 AgriKG 真实数据（hudong_pedia JSON + CSV）导入 Neo4j |
| `scripts/AGRiKG_SETUP.md` | 本文档 |
| `Agriculture_KnowledgeGraph-master/` | AgriKG 仓库数据（git clone / 解压得到） |

## 六、过渡策略

```
当前：knowledge_mcp_server.py（硬编码 JSON）
         ↓
第一阶段：knowledge_graph_mcp.py（Neo4j 优先，失败时自动降级到硬编码）  ← 本集成
         ↓
第二阶段：完全依赖 Neo4j，弃用 hardcoded 降级；并将 agri-ai/kg_adapter.py 的
         query_kg() 接到真实图谱（替换 rag.knowledge_base.DISEASE_DB）
```