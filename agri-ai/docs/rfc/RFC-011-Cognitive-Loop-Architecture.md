# RFC-011: Cognitive Loop Architecture Specification


- **RFC Number:** 011
- **Title:** Cognitive Loop Architecture Specification
- **Status:** Draft
- **Category:** Cognitive Architecture
- **Version:** 1.0
- **Created:** 2026-07-10
- **Authors:** ACIS Team


---

# Abstract


ACIS Cognitive Loop Architecture 定义 Agent 持续感知、理解、规划、行动和学习的循环机制。


该 RFC 规范：

- Perception Loop
- Attention Mechanism
- Working Memory
- Reasoning Loop
- Action Loop
- Reflection Loop
- Goal Management


目标：

使 ACIS 从：

```
Task Agent

```

进入：

```
Continuous Cognitive Agent

```


核心循环：

```
Perceive

↓

Understand

↓

Think

↓

Plan

↓

Act

↓

Observe

↓

Reflect

↓

Learn

↓

Perceive Again

```


---

# 1. Motivation


## 1.1 Task Based Agent Limitation


传统 Agent：

```
Request

↓

Response

↓

End

```


生命周期：

短暂。


---

## 1.2 Cognitive Agent Requirement


真正智能系统：

需要：

持续存在。


例如：

农业智能 Agent：


```
Monitor Field

↓

Detect Change

↓

Predict Risk

↓

Recommend Action

↓

Observe Result

↓

Improve Model

```


---

# 2. Design Principles


## 2.1 Intelligence Is A Loop


智能不是一次计算。


而是：

```
Continuous Process

```


---

## 2.2 Internal State Matters


Agent 必须拥有：

内部状态。


包括：

- Current Goal
- Belief
- Memory
- Attention
- Plan


---

## 2.3 Cognitive Process Must Be Observable


每次认知循环：

必须记录：

```
What observed?

What thought?

What decided?

What changed?

```


---

# 3. Cognitive Loop Architecture


```

                 Environment


                     |

                     v


              Perception Layer


                     |

                     v


              Attention System


                     |

                     v


              Working Memory


                     |

                     v


              Reasoning System


                     |

                     v


              Planning System


                     |

                     v


              Action System


                     |

                     v


              Observation


                     |

                     v


              Reflection


                     |

                     v


              Learning


                     |

                     +---------+

                               |

                               v


                          New Cycle


```

---

# 4. Perception Loop


负责：

获取世界信息。


来源：

- User Input
- Sensor
- Tool Result
- External Data


输入：

```
Raw Observation

```


输出：

```
Meaningful Information

```


---

# 5. Attention Mechanism


智能系统不能处理所有信息。


需要选择重点。


Attention 根据：

- Goal
- Importance
- Uncertainty
- Risk


筛选信息。


Example:


农业场景：

大量数据：

```
Temperature

Humidity

Soil

Market

```


当前目标：

病害检测。


Attention：

提高：

```
Leaf Image

Weather

Humidity

```


权重。


---

# 6. Working Memory


短期认知空间。


保存：

当前任务相关信息。


结构：


```json
{

"goal":

"",


"current_task":

"",


"active_plan":

"",


"recent_observation":

[]

}

```


---

# 7. Reasoning Loop


推理过程：


```
Observation

↓

Interpretation

↓

Hypothesis

↓

Evaluation

```


---

# 8. Goal Management


Agent 需要管理目标。


Goal 类型：


## Primary Goal


用户目标。


---

## Secondary Goal


系统生成目标。


---

## Maintenance Goal


长期目标。


例如：

```
Maintain Knowledge Accuracy

```


---

# 9. Action Loop


连接 RFC-009。


流程：

```
Decide

↓

Execute

↓

Observe

```


行动结果：

反馈进入：

下一轮循环。


---

# 10. Reflection Loop


任务结束后：

Agent 复盘。


Reflection:


```
What happened?

↓

Why happened?

↓

How improve?

```


输出：

```
Reflection Memory

```


---

# 11. Cognitive State Model


ACIS Cognitive State:


```json
{

"goal":

"",


"belief":

[],


"attention":

[],


"memory":

[],


"plan":

"",


"emotion":

null

}

```


---

# 12. Belief System


Agent 对世界拥有：

当前信念。


例如：


```
Belief:

Crop disease probability = 0.8

```


随着新信息：

更新。


---

# 13. Cognitive Cycle State Machine


```

Idle


 ↓


Perceiving


 ↓


Understanding


 ↓


Reasoning


 ↓


Planning


 ↓


Acting


 ↓


Reflecting


 ↓


Learning


 ↓


Idle


```


---

# 14. Relationship With Existing RFC


```
RFC-004

Memory


        |


RFC-006

Decision


        |


RFC-007

Learning


        |


RFC-008

Planner


        |


RFC-009

Executive Agent


        |


RFC-010

World Model


        |


RFC-011

Cognitive Loop

```


---

# 15. Implementation Reference


目录：

```
acis/


cognition/


├── perception.py

├── attention.py

├── working_memory.py

├── reasoning.py

├── goal.py

├── reflection.py

└── loop.py

```


---

# 16. Core Interface


```python

class CognitiveLoop:


    def run(self):


        observation = perceive()


        focus = attention(
            observation
        )


        decision = reason(
            focus
        )


        action = execute(
            decision
        )


        reflect(action)


        learn()



```


---

# 17. Future Extensions


## RFC-011.1

Self Model Architecture


建立：

"我是谁"

模型。


---

## RFC-011.2

Emotion / Motivation Model


模拟：

驱动力机制。


---

## RFC-011.3

Conscious Attention System


高级注意机制。


---

# 18. Conclusion


ACIS Cognitive Loop Architecture 核心原则：


> 智能不是一个函数，而是一个持续运行的过程。


完整循环：

```
Perception

↓

Attention

↓

Understanding

↓

Planning

↓

Action

↓

Reflection

↓

Learning

↓

Evolution

```


RFC-011 使 ACIS 从 Agent Framework 进入 Cognitive System。 