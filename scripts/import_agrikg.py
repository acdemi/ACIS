"""将 AgriKG 真实数据导入 Neo4j。

数据来源：qq547276542/Agriculture_KnowledgeGraph（clone 或解压到 --repo-dir）。

真实数据 schema（与早期版本假设的 crop/disease/pest/pesticide JSON 不同——那些
文件在 AgriKG 中并不存在，旧脚本无法运行）：

  节点 :HudongItem {title, detail, url, image, openTypeList,
                    baseInfoKeyList, baseInfoValueList}
  节点 :NewNode {title}
  关系 (:HudongItem|:NewNode)-[:RELATION {type}]->(:HudongItem|:NewNode)
        来源：wikidata_relation.csv / wikidata_relation2.csv / attributes.csv
  导入后按标题关键词为部分 HudongItem 追加标签 :Disease / :Pest，便于病害/虫害检索。

用法：
    python scripts/import_agrikg.py --repo-dir ./Agriculture_KnowledgeGraph-master

可选参数：
    --disease-only   只导入病害/虫害相关实体（图小、导入快，适合 MVP）
    --batch-size N   批量写入大小（默认 1000）
    --clean          清空现有图谱后再导入（默认交互确认）
    --yes            跳过交互确认

环境变量：NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
         （默认 bolt://localhost:7687 / neo4j / neo4j）
"""

import argparse
import csv
import json
import os
import zipfile
from pathlib import Path

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j")

# 病害 / 虫害标题关键词（用于 --disease-only 过滤与 :Disease/:Pest 打标）
DISEASE_KEYWORDS = [
    "病", "疫", "锈", "枯", "萎", "霉", "炭疽", "白粉",
    "霜霉", "叶斑", "根腐", "立枯", "猝倒", "灰霉", "菌核", "黑星",
]
PEST_KEYWORDS = [
    "虫", "蝇", "虱", "蚜", "螨", "蛾", "螟", "蚁", "蝗", "蚧",
]


def get_driver():
    from neo4j import GraphDatabase  # 懒加载：未安装 neo4j 时 --help 仍可用
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


def is_disease_or_pest(title):
    return any(k in title for k in DISEASE_KEYWORDS + PEST_KEYWORDS)


# ------------------------------------------------------------------
# 读取 hudong_pedia JSON（流式，单行一个对象，避免一次性载入 100+MB）
# ------------------------------------------------------------------
def iter_hudong_json(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line in ("[", "]"):
                continue
            if line.startswith(","):
                line = line[1:]
            if line.endswith(","):
                line = line[:-1]
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def resolve_hudong_json(repo_dir):
    """定位 hudong_pedia*.json；若只有 .json.zip 则自动解压。"""
    data_dir = repo_dir / "MyCrawler" / "MyCrawler" / "data"
    paths = []
    for stem in ("hudong_pedia", "hudong_pedia2"):
        j = data_dir / f"{stem}.json"
        if not j.exists():
            z = data_dir / f"{stem}.json.zip"
            if z.exists():
                print(f"  解压 {z.name} ...")
                with zipfile.ZipFile(z) as zf:
                    zf.extractall(data_dir)
        if j.exists():
            paths.append(j)
    return paths


# ------------------------------------------------------------------
# 批量写入
# ------------------------------------------------------------------
def batched_run(session, cypher, rows, batch_size):
    rows = list(rows)
    total = len(rows)
    for i in range(0, total, batch_size):
        session.run(cypher, {"rows": rows[i:i + batch_size]}).consume()
    return total


# ------------------------------------------------------------------
# 导入步骤
# ------------------------------------------------------------------
def create_constraints(session):
    for label in ("HudongItem", "NewNode", "Disease", "Pest"):
        session.run(
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:" + label + ") "
            "REQUIRE n.title IS UNIQUE"
        ).consume()
    print("✓ 约束/索引就绪")


def load_hudong_items(session, json_paths, batch_size, disease_only):
    cypher = (
        "UNWIND $rows AS row "
        "MERGE (n:HudongItem {title: row.title}) "
        "SET n.detail = row.detail, n.url = row.url, n.image = row.image, "
        "n.openTypeList = row.openTypeList, "
        "n.baseInfoKeyList = row.baseInfoKeyList, "
        "n.baseInfoValueList = row.baseInfoValueList"
    )
    buf, total = [], 0
    for path in json_paths:
        print(f"  读取 {path.name} ...")
        for ent in iter_hudong_json(path):
            title = (ent.get("title") or "").strip()
            if not title:
                continue
            if disease_only and not is_disease_or_pest(title):
                continue
            buf.append({
                "title": title,
                "detail": ent.get("detail") or "",
                "url": ent.get("url") or "",
                "image": ent.get("image") or "",
                "openTypeList": ent.get("openTypeList") or "",
                "baseInfoKeyList": ent.get("baseInfoKeyList") or "",
                "baseInfoValueList": ent.get("baseInfoValueList") or "",
            })
            if len(buf) >= batch_size:
                session.run(cypher, {"rows": buf}).consume()
                total += len(buf)
                buf = []
                print(f"    HudongItem 已写入 {total} ...")
    if buf:
        session.run(cypher, {"rows": buf}).consume()
        total += len(buf)
    print(f"  ✓ HudongItem 节点: {total}")
    return total


def load_new_nodes(session, csv_path, batch_size):
    if not csv_path.exists():
        print("  new_node.csv 不存在，跳过")
        return
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            title = (r.get("title") or "").strip()
            if title:
                rows.append({"title": title})
    n = batched_run(session, "UNWIND $rows AS row MERGE (n:NewNode {title: row.title})",
                    rows, batch_size)
    print(f"  ✓ NewNode 节点: {n}")


def load_relations(session, csv_path, start_label, end_label,
                   start_col, end_col, rel_col, batch_size, label):
    if not csv_path.exists():
        print(f"  {csv_path.name} 不存在，跳过")
        return
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            s = (r.get(start_col) or "").strip()
            e = (r.get(end_col) or "").strip()
            t = (r.get(rel_col) or "").strip()
            if s and e and t:
                rows.append({"start": s, "end": e, "rel": t})
    cypher = (
        "UNWIND $rows AS row "
        "MATCH (a:" + start_label + " {title: row.start}) "
        "MATCH (b:" + end_label + " {title: row.end}) "
        "MERGE (a)-[:RELATION {type: row.rel}]->(b)"
    )
    n = batched_run(session, cypher, rows, batch_size)
    print(f"  ✓ {label}: 处理 {n} 条三元组")


def load_attributes(session, csv_path, batch_size):
    """attributes.csv：Entity --AttributeName--> Attribute，两端均可能为
    HudongItem 或 NewNode，按 README 做 4 种 label 组合匹配（命中才建边）。"""
    if not csv_path.exists():
        print("  attributes.csv 不存在，跳过")
        return
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            s = (r.get("Entity") or "").strip()
            e = (r.get("Attribute") or "").strip()
            t = (r.get("AttributeName") or "").strip()
            if s and e and t:
                rows.append({"start": s, "end": e, "rel": t})
    print(f"  attributes 三元组: {len(rows)} 条，按 4 种 label 组合建边 ...")
    for sl in ("HudongItem", "NewNode"):
        for el in ("HudongItem", "NewNode"):
            cypher = (
                "UNWIND $rows AS row "
                "MATCH (a:" + sl + " {title: row.start}) "
                "MATCH (b:" + el + " {title: row.end}) "
                "MERGE (a)-[:RELATION {type: row.rel}]->(b)"
            )
            batched_run(session, cypher, rows, batch_size)
    print("  ✓ attributes 关系处理完成")


def label_diseases_and_pests(session):
    session.run(
        "MATCH (n:HudongItem) "
        "WHERE ANY(k IN $kws WHERE n.title CONTAINS k) SET n:Disease",
        {"kws": DISEASE_KEYWORDS},
    ).consume()
    session.run(
        "MATCH (n:HudongItem) "
        "WHERE ANY(k IN $kws WHERE n.title CONTAINS k) SET n:Pest",
        {"kws": PEST_KEYWORDS},
    ).consume()
    print("✓ 已为病害/虫害实体打标 :Disease / :Pest")


def verify(session):
    nodes = session.run(
        "MATCH (n) UNWIND labels(n) AS lb "
        "RETURN lb AS label, count(*) AS cnt ORDER BY cnt DESC"
    ).data()
    rels = session.run(
        "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS cnt ORDER BY cnt DESC"
    ).data()
    print("\n=== 导入统计 ===")
    for n in nodes:
        print("  :" + n["label"] + ": " + str(n["cnt"]))
    print("\n关系:")
    for r in rels:
        print("  -[:" + r["t"] + "]->: " + str(r["cnt"]))


def clean_graph(driver):
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
    print("✓ 已清空图谱")


def main():
    ap = argparse.ArgumentParser(description="将 AgriKG 真实数据导入 Neo4j")
    ap.add_argument("--repo-dir", default="./Agriculture_KnowledgeGraph-master",
                    help="AgriKG 仓库根目录（clone 或解压后的 Agriculture_KnowledgeGraph-master）")
    ap.add_argument("--disease-only", action="store_true",
                    help="只导入病害/虫害相关实体")
    ap.add_argument("--batch-size", type=int, default=1000)
    ap.add_argument("--clean", action="store_true", help="清空现有图谱")
    ap.add_argument("--yes", action="store_true", help="跳过交互确认")
    args = ap.parse_args()

    repo = Path(args.repo_dir)
    if not repo.exists():
        raise SystemExit("仓库目录不存在: " + str(repo) + "\n请先 clone 或解压 Agriculture_KnowledgeGraph")

    try:
        driver = get_driver()
        driver.verify_connectivity()
    except ModuleNotFoundError:
        raise SystemExit("缺少依赖 neo4j，请先运行 pip install neo4j")
    except Exception as e:
        raise SystemExit("无法连接 Neo4j (" + NEO4J_URI + "): " + str(e) + "\n请先启动 Neo4j。")

    if args.clean or (not args.yes and
                      input("是否清空现有图谱？(y/N): ").strip().lower() == "y"):
        clean_graph(driver)

    proc = repo / "wikidataSpider" / "wikidataProcessing"
    with driver.session() as session:
        create_constraints(session)
        json_paths = resolve_hudong_json(repo)
        if not json_paths:
            print("⚠ 未找到 hudong_pedia*.json，HudongItem 节点将不会被导入")
        load_hudong_items(session, json_paths, args.batch_size, args.disease_only)
        load_new_nodes(session, proc / "new_node.csv", args.batch_size)
        load_relations(session, proc / "wikidata_relation.csv",
                       "HudongItem", "HudongItem",
                       "HudongItem1", "HudongItem2", "relation",
                       args.batch_size, "RELATION (HudongItem->HudongItem)")
        load_relations(session, proc / "wikidata_relation2.csv",
                       "HudongItem", "NewNode",
                       "HudongItem", "NewNode", "relation",
                       args.batch_size, "RELATION (HudongItem->NewNode)")
        load_attributes(session, repo / "attributes.csv", args.batch_size)
        label_diseases_and_pests(session)
        verify(session)
    driver.close()
    print("\n✓ 导入完成！现在可运行 knowledge_graph_mcp.py 测试。")


if __name__ == "__main__":
    main()