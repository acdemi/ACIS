"""VisionAgent — 视觉感知层"""
from __future__ import annotations
import os
from agents.types import AgentOutput, RequestContext

class VisionAgent:
    name = "视觉Agent"
    def run(self, context: RequestContext) -> AgentOutput:
        if not context.image_path:
            return AgentOutput(layer="感知层", agent=self.name, claim="未提供图像，视觉诊断跳过", confidence=0.0, warnings=["缺少叶片图像，病害判断依赖症状与环境数据"])
        if not os.path.exists(context.image_path):
            return AgentOutput(layer="感知层", agent=self.name, claim="图像路径不存在，无法执行视觉识别", confidence=0.0, evidence={"image_path": context.image_path}, warnings=["请提供有效的叶片图片路径"])
        try:
            from agents.vision import diagnose_image
            result = diagnose_image(context.image_path)
        except Exception as exc:
            return AgentOutput(layer="感知层", agent=self.name, claim="视觉模型调用失败", confidence=0.0, evidence={"error": str(exc)}, warnings=["视觉通道不可用，需要依赖其他 Agent 交叉判断"])
        if "error" in result:
            return AgentOutput(layer="感知层", agent=self.name, claim="视觉识别未给出有效结论", confidence=0.1, evidence=result, warnings=[result["error"]])
        top = result.get("top_prediction", {})
        disease = top.get("chinese_name") or top.get("label") or "未知类别"
        confidence = float(top.get("confidence", 0.0))
        return AgentOutput(layer="感知层", agent=self.name, claim=f"图像最可能识别为：{disease}", confidence=confidence, evidence=result, recommendations=["将视觉结果与传感器湿度、知识库症状匹配结果交叉验证"])
