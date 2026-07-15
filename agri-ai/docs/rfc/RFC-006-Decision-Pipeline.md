# RFC-006: Decision Pipeline Specification


- **RFC Number:** 006
- **Title:** Decision Pipeline Specification
- **Status:** Draft
- **Category:** Cognitive Architecture
- **Version:** 1.0
- **Created:** 2026-07-10
- **Authors:** ACIS Team


---

# Abstract


ACIS Decision Pipeline 定义 Agent 从信息输入到行动选择之间的核心认知流程。


该 RFC 描述：

- 状态感知
- 上下文构建
- 目标分析
- 方案生成
- 方案评估
- 决策选择
- 行动反馈


Decision Pipeline 是 ACIS Cognitive Loop 的核心组件。


核心流程：


```
Observation

↓

Understanding

↓

Reasoning

↓

Evaluation

↓

Decision

↓

Action

↓

Feedback

```


目标：

使 Agent 不只是生成文本，而能够形成：

```
Situation

+

Goal

+

Knowledge

+

Reasoning

+

Action

```

驱动的智能决策。


---

# 1. Motivation


## 1.1 LLM Output Is Not Decision


传统 LLM：

```
Input

↓

LLM

↓

Output

```


问题：

模型输出：

- 缺少目标约束
- 缺少状态信息
- 缺少行动规划
- 缺少反馈机制


因此：

```
Answer

!=

Decision

```


---

# 1.2 Agent Requires Decision Process


Agent:

不是回答问题。

Agent:

需要：

```
Observe

↓

Understand

↓

Decide

↓

Act

```


例如：


用户：

```
帮我优化农业灌溉方案

```


普通 LLM：

```
输出建议

```


Agent：

```
读取环境数据

↓

分析作物状态

↓

生成方案

↓

评估风险

↓

执行调整

↓

观察结果

```


---

# 2. Design Principles


## 2.1 Decision Is A Process


ACIS 不保存：

```
Final Answer

```


而保存：

```
Decision Trace

```


---

## 2.2 Context Before Reasoning


推理必须建立在：

```
Current State

+

Memory

+

Observation

```


之上。


---

## 2.3 Separate Thinking and Acting


禁止：

```
Reasoning

↓

Immediate Action

```


必须：

```
Reasoning

↓

Decision

↓

Execution

```


---

# 3. Architecture Overview


```

              Observation


                   |

                   v


          +----------------+

          | Context Builder|

          +----------------+


                   |


                   v


          +----------------+

          | Reasoning Core |

          +----------------+


                   |


                   v


          +----------------+

          | Decision Maker |

          +----------------+


                   |


                   v


          +----------------+

          | Action Planner |

          +----------------+


                   |


                   v


              Executor


                   |

                   v


              Feedback


```


---

# 4. Decision Pipeline Stages


# Stage 1: Observation


输入：

- 用户请求
- 环境信息
- 工具返回
- Memory


Example:


```json
{
"user_input":

"是否需要灌溉？",


"sensor":

{

"soil":

35

}

}
```


---

# Stage 2: Context Construction


Context Builder 负责：

整合：


```
Current State

+

Memory

+

Knowledge

+

Constraints

```


输出：


```json
{
"context":

{

"goal":"",

"state":"",

"knowledge":[]

}

}
```


---

# Stage 3: Situation Understanding


Agent 判断：

当前：

- 发生什么
- 需要解决什么
- 缺少什么信息


输出：


```json
{

"situation":

"soil moisture low"

}

```


---

# Stage 4: Reasoning


Reasoning Core 生成：

候选方案。


例如：

```
Option A:

立即灌溉


Option B:

等待降雨


Option C:

调整参数


```


---

# Stage 5: Decision Evaluation


评估因素：


## Goal Alignment


是否符合目标。


---

## Cost


资源消耗。


---

## Risk


潜在风险。


---

## Confidence


可信程度。


---

Decision Score:


```
Score =

Goal

+

Cost

+

Risk

+

Confidence

```


---

# Stage 6: Decision Selection


输出最终选择。


Decision Object:


```json
{

"id":

"decision001",


"choice":

"A",


"confidence":

0.91,


"reason":

""

}

```


---

# Stage 7: Action Preparation


Decision 不直接执行。


进入 Action Planner。


```
Decision

↓

Action Plan

↓

Executor

```


---

# 5. Decision State Model


Decision 生命周期：


```
Created

↓

Analyzing

↓

Evaluated

↓

Approved

↓

Executed

↓

Reviewed

```


---

# 6. Decision Trace


每次决策必须记录：


```json
{

"decision_id":

"",


"input":

"",


"context":

"",


"reasoning":

"",


"action":

"",


"result":

""

}

```


用于：

- Debug
- Learning
- Reflection


---

# 7. Multi-Agent Decision


多个 Agent：

可以参与决策。


结构：


```

Problem


 |

 +-----------+

 |           |


Research   Critic


 |           |


 +-----------+


      |

Consensus

```


---

# 8. Uncertainty Handling


Agent 必须表达：

不知道。


Confidence:

```
0-1

```


规则：

```
Low Confidence

↓

Gather More Information

```


而不是：

```
Low Confidence

↓

Generate Answer

```


---

# 9. Decision Failure Handling


## Missing Information


```
Need Data

↓

Request Tool

↓

Continue

```


---

## Conflicting Reasoning


```
Conflict

↓

Re-evaluate

↓

Ask Human

```


---

## Wrong Decision


进入：

```
Reflection

↓

Learning Pipeline

```


---

# 10. Implementation Reference


目录：


```
acis/


decision/


├── context.py

├── reasoning.py

├── evaluator.py

├── selector.py

├── trace.py

└── pipeline.py

```


---

# 11. Core Interface


```python

class DecisionPipeline:


    def run(
        self,
        state
    ):


        context = build_context(
            state
        )


        reasoning = reason(
            context
        )


        decision = evaluate(
            reasoning
        )


        return decision

```


---

# 12. Relationship With Other RFC


```
RFC-002

Workflow State


        |


RFC-004

Memory System


        |


RFC-005

Tool Protocol


        |


RFC-006

Decision Pipeline


        |


RFC-007

Learning Pipeline


        |


RFC-008

Planner

```


---

# 13. Future Extensions


## RFC-006.1

Decision Graph


支持复杂任务决策。


---

## RFC-006.2

Multi-Agent Consensus


多 Agent 协商。


---

## RFC-006.3

Decision Simulation


预测行动结果。


---

# 14. Conclusion


ACIS Decision Pipeline 核心原则：


> Agent 的智能不在于输出答案，而在于形成可解释、可验证、可执行的决策过程。


核心循环：

```
Observe

↓

Understand

↓

Reason

↓

Decide

↓

Act

↓

Learn

```


RFC-006 是 ACIS Cognitive Architecture 的决策核心。