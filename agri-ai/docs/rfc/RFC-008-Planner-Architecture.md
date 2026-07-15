# RFC-008: Planner Architecture Specification


- **RFC Number:** 008
- **Title:** Planner Architecture Specification
- **Status:** Draft
- **Category:** Cognitive Architecture
- **Version:** 1.0
- **Created:** 2026-07-10
- **Authors:** ACIS Team


---

# Abstract


ACIS Planner Architecture 定义 Agent 将目标转化为行动计划的机制。


该 RFC 规范：

- Goal Understanding
- Task Decomposition
- Planning Strategy
- Plan Generation
- Plan Evaluation
- Dynamic Replanning


目标：

使 Agent 从：

```
Reactive Agent

```

进入：

```
Goal Directed Agent

```


核心流程：

```
Goal

↓

Understanding

↓

Decomposition

↓

Planning

↓

Execution

↓

Feedback

↓

Replanning

```


---

# 1. Motivation


## 1.1 Reactive Agent Limitation


简单 Agent：

```
Input

↓

LLM

↓

Response

```


适合：

简单问题。


但是复杂任务：

例如：

```
调研新疆智慧农业发展趋势

```


需要：

```
搜索资料

↓

整理数据

↓

分析趋势

↓

生成报告

↓

验证结论

```


---

## 1.2 Planning Is Intelligence


智能的重要表现：

不是回答。


而是：

```
知道下一步应该做什么

```


---

# 2. Design Principles


## 2.1 Goal First


所有计划：

必须由目标驱动。


```
Goal

↓

Plan

↓

Action

```


---

## 2.2 Plan Is Not Fixed


现实环境变化。


因此：

```
Initial Plan

↓

Observation

↓

Update Plan

```


---

## 2.3 Planning Must Be Observable


计划必须可解释。


保存：

- 为什么这样规划
- 为什么选择该路径


---

# 3. Planner Architecture


```

             User Goal


                 |

                 v


        +----------------+

        | Goal Analyzer |

        +----------------+


                 |

                 v


        +----------------+

        | Task Decomposer|

        +----------------+


                 |

                 v


        +----------------+

        | Plan Generator |

        +----------------+


                 |

                 v


        +----------------+

        | Plan Evaluator |

        +----------------+


                 |

                 v


              Executor


```


---

# 4. Goal Understanding


Planner 首先解析目标。


输入：

```
User Intent

+

Context

```


输出：

Goal Object:


```json
{

"goal":

"research agriculture market",


"constraints":

[],


"priority":

"high"

}

```


---

# 5. Task Decomposition


复杂目标拆解。


Example:


目标：

```
制作农业市场分析报告

```


拆解：

```
Task 1

Collect Data


Task 2

Analyze Market


Task 3

Generate Report


Task 4

Review

```


---

# 6. Task Graph


ACIS 使用：

Task Graph。


结构：

```

        Goal


          |


    +-----+-----+


    |           |


 Task A      Task B


    |


 Task C


```


---

# 7. Planning Strategies


ACIS 支持多种 Planner。


---

# 7.1 Sequential Planner


顺序规划。


```
A

↓

B

↓

C

```


适合：

简单流程。


---

# 7.2 Parallel Planner


并行规划。


```
      A

     /

Goal


     \

      B

```


适合：

信息收集。


---

# 7.3 Hierarchical Planner


层级规划。


```
High Goal


↓

Sub Goal


↓

Task


↓

Action

```


适合：

复杂任务。


---

# 7.4 Adaptive Planner


动态规划。


根据反馈：

修改计划。


---

# 8. Plan Representation


Plan Object:


```json
{

"id":

"plan001",


"goal":

"",


"tasks":

[],


"dependencies":

[],


"status":

"running"

}

```


---

# 9. Plan Evaluation


生成计划后：

需要评估。


指标：


## Feasibility

是否可执行。


---

## Cost

资源消耗。


---

## Risk

失败概率。


---

## Efficiency

执行效率。


---

# 10. Dynamic Replanning


执行过程中：

环境变化。


Example:


```
Task A Failed


↓

Analyze


↓

Generate New Plan


```


流程：


```
Observe

↓

Detect Failure

↓

Modify Plan

↓

Continue

```


---

# 11. Planner And Decision Pipeline


关系：


Planner:

```
What should we do?

```


Decision Pipeline:

```
Which option should choose?

```


关系：


```
Goal

↓

Planner

↓

Decision

↓

Action

```


---

# 12. Planner Memory


Planner 使用：


RFC-004 Memory


包括：


- Historical Plans
- Successful Strategies
- Failure Cases


---

# 13. Planner Learning


连接 RFC-007。


Planner 可以学习：


```
Plan A

成功率80%


Plan B

成功率95%

```


未来：

优先选择 Plan B。


---

# 14. Multi-Agent Planning


多个 Agent 协同规划。


Example:


```

Planner Agent


       |

 +-----+-----+

 |           |

Research   Analysis

Agent       Agent


```


---

# 15. Implementation Reference


目录：


```
acis/


planner/


├── goal.py

├── decomposer.py

├── generator.py

├── evaluator.py

├── replanner.py

└── graph.py

```


---

# 16. Core Interface


```python

class Planner:


    def create_plan(
        self,
        goal
    ):


        tasks = decompose(goal)


        plan = generate(tasks)


        return plan



    def replan(
        self,
        feedback
    ):


        update_plan()

```


---

# 17. Relationship With Other RFC


```
RFC-004

Memory


        |


RFC-006

Decision Pipeline


        |


RFC-007

Learning Pipeline


        |


RFC-008

Planner


        |


RFC-009

Executive Agent


```


---

# 18. Future Extensions


## RFC-008.1

Tree of Thoughts Planner


复杂推理搜索。


---

## RFC-008.2

Multi-Agent Planner


自动组织 Agent。


---

## RFC-008.3

Self Planning Agent


自主生成长期目标。


---

# 19. Conclusion


ACIS Planner Architecture 核心原则：


> 智能不仅是做出正确选择，更是知道如何到达目标。


核心链路：

```
Goal

↓

Plan

↓

Decision

↓

Action

↓

Feedback

↓

Learning

```


RFC-008 使 ACIS 从响应式 Agent 进入目标驱动 Agent。