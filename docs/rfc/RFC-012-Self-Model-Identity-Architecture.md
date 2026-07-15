# RFC-012: Self Model & Identity Architecture Specification


- **RFC Number:** 012
- **Title:** Self Model & Identity Architecture Specification
- **Status:** Draft
- **Category:** Cognitive Architecture
- **Version:** 1.0
- **Created:** 2026-07-10
- **Authors:** ACIS Team


---

# Abstract


ACIS Self Model & Identity Architecture 定义 Agent 对自身状态、能力、限制和目标的内部表示机制。


该 RFC 规范：

- Self Representation
- Identity Management
- Capability Awareness
- Limitation Awareness
- Self Evaluation
- Self Consistency
- Agent Continuity


目标：

使 Agent 从：

```
System That Acts

```

进入：

```
System That Knows Its Own State

```


核心能力：

```
World Model

        +

Self Model

        +

Cognition

        =

Self-Aware Agent

```


---

# 1. Motivation


## 1.1 External Understanding Is Not Enough


RFC-010：

World Model:

回答：

```
世界是什么？

```


但是 Agent 还需要回答：

```
我是什么？

```


---

## 1.2 Self Knowledge Enables Better Decisions


没有 Self Model：


Agent:

```
可以执行所有任务

```


容易产生：

- 能力高估
- 错误执行
- 不知道限制


---

有 Self Model：


Agent:

```
知道：

我有什么能力

我缺少什么能力

什么时候需要帮助

```


---

# 2. Design Principles


## 2.1 Self Model Is Internal Representation


Self Model 不是：

人格设定。


而是：

```
Internal State Model

```


---

## 2.2 Identity Must Be Continuous


Agent 不应该每次启动都是：

全新实例。


需要保持：

```
Past State

+

Current State

+

Future Goal

```


---

## 2.3 Self Knowledge Must Be Updated


能力会变化。


例如：

新增工具：

```
New Tool

↓

New Capability

↓

Self Model Update

```


---

# 3. Self Model Architecture


```

                 Agent


                   |

                   v


          +----------------+

          | Self Model     |

          +----------------+

                   |

     +-------------+-------------+

     |             |             |

     v             v             v


 Identity    Capability     Limitation


     |             |             |

     +-------------+-------------+

                   |

                   v


            Self Evaluation


                   |

                   v


            Behavior Adjustment


```


---

# 4. Self Representation


Self Model Object:


```json
{

"id":

"agent001",


"identity":

{

"name":""

},


"capabilities":[],


"limitations":[],


"goals":[]


}

```


---

# 5. Identity Model


Identity 用于保持连续性。


包含：


## Agent Identifier


唯一身份。


---

## History


历史经历。


---

## Role


当前角色。


Example:


```
Agriculture Assistant

```


---

## Purpose


存在目的。


Example:


```
Help optimize crop production

```


---

# 6. Capability Awareness


Agent 必须知道：

自己能做什么。


Capability:


```json
{

"name":

"image_detection",


"confidence":

0.9,


"source":

"YOLO Model"

}

```


---

能力来源：


- Built-in Model
- Tool
- Learned Skill
- External Agent


---

# 7. Limitation Awareness


高级 Agent 必须知道：

自己不能做什么。


Example:


```json
{

"limitation":

"Cannot verify field condition without sensor"

}

```


---

限制类型：


- Missing Knowledge
- Missing Tool
- Low Confidence
- Permission Restriction


---

# 8. Self Evaluation


Agent 定期评估自己。


问题：


```
Current Capability?

Current Performance?

Current Limitation?

```


---

输出：

```json
{

"performance":

0.85,


"weakness":

"poor prediction"

}

```


---

# 9. Self Consistency


保证：

Agent 行为符合自身状态。


Example:


Self Model：

```
No medical capability

```


Decision：

```
Provide medical diagnosis

```


检测：

Conflict。


---

# 10. Self Model Update


更新来源：


## Experience


RFC-007。


---

## Learning


RFC-007。


---

## Capability Change


RFC-005 Tool System。


---

## World Change


RFC-010。


---

# 11. Self Model And Decision


Decision Pipeline 使用：

Self Model。


流程：

```
Goal

+

World State

+

Self State


↓

Decision

```


Example:


目标：

```
Analyze satellite image

```


Self Model:

```
No satellite tool

```


Decision：

```
Request Tool

```


---

# 12. Self Model And Planning


Planner 根据能力规划。


没有：

Self Model:


```
Generate impossible plan

```


有：

```
Generate feasible plan

```


---

# 13. Self Reflection


连接 RFC-011。


Reflection:


```
What did I do?

↓

Was it within capability?

↓

How improve?

```


---

# 14. Multi-Agent Identity


多个 Agent：

需要身份区分。


Example:


```
Research Agent

Coding Agent

Planning Agent

```


每个 Agent：

拥有独立 Self Model。


---

# 15. Implementation Reference


目录：


```
acis/


self/


├── identity.py

├── capability.py

├── limitation.py

├── evaluation.py

├── update.py

└── model.py

```


---

# 16. Core Interface


```python

class SelfModel:


    def update(
        self,
        experience
    ):

        update_capability()



    def evaluate(self):

        return self_state



```


---

# 17. Relationship With Other RFC


```
RFC-004

Memory

     |

     v

RFC-007

Learning

     |

     v

RFC-010

World Model

     |

     v

RFC-011

Cognitive Loop

     |

     v

RFC-012

Self Model


```


---

# 18. Future Extensions


## RFC-012.1

Agent Personality Model


稳定交互风格。


---

## RFC-012.2

Autonomous Goal Generation


自主目标形成。


---

## RFC-012.3

Self Improvement Governance


自我修改限制。


---

# 19. Conclusion


ACIS Self Model Architecture 核心原则：


> 一个智能系统不仅需要理解世界，也需要理解自己在世界中的位置。


完整认知结构：

```
World Model

+

Self Model

+

Memory

+

Planning

+

Action

+

Learning


=

Cognitive Agent

```


RFC-012 是 ACIS 从：

```
Agent

```

迈向：

```
Artificial Cognitive System

```

的重要组成部分。