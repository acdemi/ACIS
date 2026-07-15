# RFC-009: Executive Agent Architecture Specification


- **RFC Number:** 009
- **Title:** Executive Agent Architecture Specification
- **Status:** Draft
- **Category:** Cognitive Architecture
- **Version:** 1.0
- **Created:** 2026-07-10
- **Authors:** ACIS Team


---

# Abstract


ACIS Executive Agent Architecture 定义 Agent 将计划转化为实际行动的执行机制。


该 RFC 规范：

- Action Execution
- Tool Invocation
- Execution Loop
- Observation
- Error Recovery
- Self Correction
- Task Completion


目标：

使 Agent 从：

```
Thinking System

```

进入：

```
Acting System

```


核心循环：

```
Plan

↓

Execute

↓

Observe

↓

Evaluate

↓

Adjust

↓

Complete

```


---

# 1. Motivation


## 1.1 Planning Without Execution


Planner 可以生成：

```
Task A

↓

Task B

↓

Task C

```


但是：

如果没有执行层：

计划只是：

```
Text Description

```


---

## 1.2 Executive Function


人类认知：

```
Thinking

+

Action

```


ACIS 中：

Planner 类似：

"大脑规划"


Executive Agent 类似：

"行动控制系统"


---

# 2. Design Principles


## 2.1 Execution Is State Driven


执行不是：

```
Run Once

```


而是：

```
State

↓

Action

↓

Observation

↓

Next State

```


---

## 2.2 Actions Must Be Observable


所有行动必须记录：


- Action
- Input
- Result
- Error
- Cost


---

## 2.3 Execution Must Be Recoverable


失败不能导致任务终止。


必须支持：

- Retry
- Alternative Action
- Replanning


---

# 3. Executive Agent Architecture


```

                 Plan


                  |

                  v


        +----------------+

        | Task Controller|

        +----------------+


                  |

                  v


        +----------------+

        | Action Selector|

        +----------------+


                  |

                  v


        +----------------+

        | Tool Executor |

        +----------------+


                  |

                  v


             Environment


                  |

                  v


        Observation Feedback


                  |

                  v


             State Update


```


---

# 4. Executive Agent Components


## 4.1 Task Controller


负责：

- 接收 Plan
- 管理 Task 状态
- 调度执行顺序


Example:


```json
{

"task":

"collect_data",


"status":

"running"

}

```


---

## 4.2 Action Selector


决定：

下一步执行什么。


输入：

```
Current State

+

Plan

+

Context

```


输出：

```
Next Action

```


---

## 4.3 Tool Executor


连接：

RFC-005 Tool Protocol。


负责：

- Tool 调用
- 参数验证
- 返回处理


流程：

```
Action

↓

Tool Request

↓

Execution

↓

Result

```


---

## 4.4 Observation Handler


执行后：

观察结果。


包括：

- Success
- Failure
- Unexpected Output


---

# 5. Action Model


ACIS Action Object:


```json
{

"id":

"action001",


"type":

"tool_call",


"target":

"search_api",


"input":

{},


"status":

"pending"

}

```


---

# 6. Execution Loop


核心：

Action Loop。


```

while task_not_complete:


    observe()


    select_action()


    execute()


    evaluate_result()


    update_state()


```


---

# 7. Execution State Machine


```

Created

↓

Ready

↓

Executing

↓

Waiting

↓

Observing

↓

Completed


        |

        v


      Failed

        |

        v


    Recovery

```


---

# 8. Tool Execution


Tool 调用流程：


```

Executive Agent


        |

        v


Tool Protocol


        |

        v


External Capability


        |

        v


Result


        |

        v


Observation


```


---

# 9. Error Recovery


执行失败：


## Retry


适用于：

临时错误。


```
Failure

↓

Retry

```


---

## Alternative Tool


例如：

```
Search API Failed

↓

Use Backup Search

```


---

## Replanning


复杂失败：

返回 Planner。


```
Failure

↓

Planner

↓

New Plan

```


---

# 10. Human In The Loop


部分任务：

需要人工确认。


例如：

```
Financial Transaction

Medical Decision

Industrial Control

```


流程：

```
Action

↓

Human Approval

↓

Execute

```


---

# 11. Execution Memory


连接 RFC-004。


保存：

- Successful Actions
- Failed Actions
- Tool Performance


用于：

RFC-007 Learning。


---

# 12. Multi-Agent Execution


多个 Executive Agent：

可以协同。


Example:


```

Main Executive Agent


        |

 +------+------+

 |             |


Research     Coding

Agent        Agent


```


---

# 13. Relationship With Cognitive Loop


完整链路：


```

Goal

 |

 v

Planner

 |

 v

Decision

 |

 v

Executive Agent

 |

 v

Action

 |

 v

Observation

 |

 v

Learning


```


---

# 14. Implementation Reference


目录：


```
acis/


executor/


├── controller.py

├── action.py

├── executor.py

├── observer.py

├── recovery.py

└── loop.py

```


---

# 15. Core Interface


```python

class ExecutiveAgent:


    def execute(
        self,
        plan
    ):


        while not complete:

            action = select_action()

            result = execute(action)

            observe(result)



```


---

# 16. Safety Constraints


Executive Agent 必须遵守：


- Tool Permission
- Resource Limit
- Action Policy


禁止：

```
Agent

↓

Direct External Action

```


必须：

```
Agent

↓

Executive Layer

↓

Tool Layer

```


---

# 17. Future Extensions


## RFC-009.1

Autonomous Action Optimization


优化行动策略。


---

## RFC-009.2

Physical Agent Interface


连接：

机器人

IoT

自动驾驶


---

## RFC-009.3

Multi-Agent Executor


大规模协同执行。


---

# 18. Conclusion


ACIS Executive Agent Architecture 核心原则：


> 智能最终必须作用于现实，而执行是连接认知与世界的桥梁。


完整执行闭环：

```
Plan

↓

Decision

↓

Execute

↓

Observe

↓

Learn

↓

Improve

```


RFC-009 使 ACIS 从思考系统进入行动系统。