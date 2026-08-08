# RFC-014: Agent Ecosystem & Marketplace Specification


- **RFC Number:** 014
- **Title:** Agent Ecosystem & Marketplace Specification
- **Status:** Draft
- **Category:** Ecosystem Architecture
- **Version:** 1.0
- **Created:** 2026-07-10
- **Authors:** ACIS Team


---

# Abstract


ACIS Agent Ecosystem 定义 Agent 从创建、发布、发现、组合到生命周期管理的完整生态体系。


该 RFC 规范：

- Agent Registry
- Marketplace
- Agent Discovery
- Agent Package
- Version Management
- Reputation System
- Agent Composition


目标：

建立：

```
Develop

↓

Publish

↓

Discover

↓

Compose

↓

Improve

```

的 Agent 生态闭环。


ACIS 的最终目标不是拥有最多 Agent。

而是：

> 让任何能力都能够被发现、组合和复用。


---

# 1. Motivation


## 1.1 Problem


当前 AI Agent 生态存在：

### 重复开发


不同开发者：

```
Build Research Agent

Build Search Agent

Build Data Agent

```

大量重复。


---

### 能力孤岛


Agent：

```
Agent A

只能自己工作

```

无法：

```
Agent A

+

Agent B

=

New Capability

```


---

### 缺少可信评价


用户无法判断：

```
这个 Agent 是否可靠？

```

---

# 2. Design Principles


## 2.1 Agent As Package


ACIS 中：

Agent 是可分发对象。


结构：

```
Agent

=

Code

+

Memory Schema

+

Capability

+

Policy

+

Evaluation

+
Documentation

```


---

## 2.2 Composable Intelligence


智能来自组合。


例如：


```
Research Agent

+

Data Agent

+

Writing Agent


        |

        v


Research Assistant

```


---

## 2.3 Trust Before Adoption


Agent 使用前：

必须知道：

- 来源
- 版本
- 权限
- 评价
- 安全状态


---

# 3. Ecosystem Architecture


```

              Developer


                  |

                  v


          Agent Package


                  |

                  v


          Agent Registry


                  |

                  v


          Marketplace


                  |

        +---------+---------+

        |                   |


        v                   v


 Discovery             Evaluation


        |                   |


        +---------+---------+


                  |

                  v


              Runtime


                  |

                  v


              Users


```

---

# 4. Agent Package Specification


Agent Package 标准：


```
agent-package/


├── manifest.yaml

├── agent.py

├── capabilities/

├── prompts/

├── policies/

├── tests/

├── README.md

└── LICENSE

```


---

# 5. Agent Manifest


每个 Agent 必须声明。


Example:


```yaml
agent:

 name:

 agriculture-research-agent


 version:

 1.0.0


 author:


 description:


 capabilities:


  - literature_search

  - analysis


permissions:


  - read_web


evaluation:


 score:

 0.91

```


---

# 6. Agent Registry


Registry 是 Agent 索引中心。


负责：

- 存储元数据
- 版本管理
- 查询


结构：


```
Registry


Agent ID

 |

Versions

 |

Metadata

 |

Evaluation

```


---

# 7. Marketplace


Marketplace 提供：

## Discovery


搜索：

```
Find Agent

```

例如：

```
Agriculture Disease Diagnosis Agent

```


---

## Installation


类似：

```
pip install

npm install

docker pull

```


ACIS：

```
acis install agriculture-agent

```


---

## Update


支持：

```
Version Update

Security Patch

Capability Upgrade

```


---

# 8. Agent Discovery System


搜索维度：


## Capability


```
Can analyze images

```


---

## Domain


```
Agriculture

Finance

Healthcare

```


---

## Performance


```
Accuracy

Latency

Cost

```


---

## Trust


```
Developer Reputation

Security Score

Evaluation Score

```


---

# 9. Agent Reputation System


ACIS 引入 Agent Reputation。


评分来源：


```

Benchmark Score

+

User Feedback

+

Runtime History

+

Security Record


```


评分：

```json
{

"quality":

0.92,


"security":

0.95,


"usage":

10000

}

```


---

# 10. Agent Composition


ACIS 支持 Agent 组合。


例如：


```
User Request


     |


Planner Agent


     |


+-------------+

|             |


Research   Analyst


|             |


+-------------+


     |


Writer Agent


```


---

# 11. Agent Dependency Management


Agent 可以依赖其他 Agent。


Example:


```yaml
dependencies:


 - search-agent

 - analysis-agent

```


安装：

自动解决依赖。


---

# 12. Security Model


Marketplace 中：

所有 Agent 必须经过：


## Static Check


检查：

- 权限
- 代码
- 依赖


---

## Runtime Check


运行时：

由 RFC-008 控制。


---

## Evaluation Check


由 RFC-007 提供。


---

# 13. Agent Versioning


采用：

Semantic Versioning


格式：

```
Major.Minor.Patch

```


例如：

```
1.2.3

```


规则：


Major:

破坏性变化


Minor:

新增能力


Patch:

Bug 修复


---

# 14. Private Marketplace


企业支持：

私有 Agent Registry。


结构：


```
Company


 |

Private Registry


 |

Internal Agents

```


适用于：

- 企业
- 政府
- 研究机构


---

# 15. Agent Economics


未来支持：

Agent 服务化。


形式：

```
Free Agent


Paid Agent


Enterprise Agent


```


---

# 16. Implementation Reference


目录：


```
acis/


ecosystem/


├── registry.py

├── marketplace.py

├── discovery.py

├── reputation.py

├── installer.py

└── version.py

```


---

# 17. Core Interface


```python
class AgentRegistry:


    def publish(
        self,
        agent
    ):

        save(agent)



    def search(
        self,
        query
    ):

        return agents

```


---

# 18. Relationship With Other RFC


```
RFC-005

Capability System


        |


RFC-007

Evaluation


        |


RFC-008

Governance


        |


RFC-009

Runtime


        |


RFC-010

Developer Platform


        |


RFC-014

Agent Ecosystem


        |

        v


RFC-012

Enterprise Architecture

```


---

# 19. Future Extensions


## RFC-014.1

Agent Collaboration Network


Agent 自动寻找合作伙伴。


---

## RFC-014.2

Agent Evolution System


基于评价自动优化。


---

## RFC-014.3

Decentralized Agent Registry


去中心化 Agent 网络。


---

# 20. Conclusion


ACIS Agent Ecosystem 的核心原则：

> 能力不应该被封闭，而应该被发现、组合和复用。


最终生态闭环：

```

Developer

↓

SDK

↓

Agent

↓

Registry

↓

Marketplace

↓

User

↓

Evaluation

↓

Improvement


```


RFC-014 使 ACIS 从 Agent Platform 进一步成为 Agent Ecosystem。