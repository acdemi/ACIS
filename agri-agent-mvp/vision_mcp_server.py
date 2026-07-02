"""
视觉感知 MCP Server — 植物病害图像识别

基于 Swin-Tiny Transformer（HuggingFace 预训练模型），
提供植物叶片病害分类能力。

模型来源：gianlab/swin-tiny-patch4-window7-224-finetuned-plantdisease
架构：Swin-Tiny（28M 参数），层级化 Vision Transformer
训练数据：PlantVillage（38 类，54000+ 图像）

也可切换为其他模型（见 MODEL_REGISTRY）。
"""

import os
import json
from typing import Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("vision-perception")

# ============================================================
# 模型注册表（可随时切换模型，无需改代码）
# ============================================================

MODEL_REGISTRY = {
    "swin-tiny": {
        "model_id": "gianlab/swin-tiny-patch4-window7-224-finetuned-plantdisease",
        "architecture": "Swin-Tiny",
        "params": "28M",
        "description": "Swin Transformer Tiny，层级化 ViT，植物病害分类",
        "task": "image-classification",
    },
    "vit-base": {
        "model_id": "Alan04020/vit-plant-disease-v2",
        "architecture": "ViT-Base/16",
        "params": "86M",
        "description": "Vision Transformer Base，高准确率",
        "task": "image-classification",
    },
    "mobilenet-v2": {
        "model_id": "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification",
        "architecture": "MobileNetV2",
        "params": "3.4M",
        "description": "轻量级，适合边缘部署",
        "task": "image-classification",
    },
    "tomato-vit": {
        "model_id": "wellCh4n/tomato-leaf-disease-classification-vit",
        "architecture": "ViT-Base/16",
        "params": "86M",
        "description": "番茄专用病害分类模型",
        "task": "image-classification",
    },
}

# 当前使用的模型（可通过 MCP 工具切换）
_current_model_name = "swin-tiny"
_classifier = None  # 懒加载

# ============================================================
# 病害类别映射（PlantVillage 38 类 → 中文名）
# ============================================================

DISEASE_LABELS = {
    "Tomato___Bacterial_spot": "番茄细菌性斑点病",
    "Tomato___Early_blight": "番茄早疫病",
    "Tomato___Late_blight": "番茄晚疫病",
    "Tomato___Leaf_Mold": "番茄叶霉病",
    "Tomato___Septoria_leaf_spot": "番茄斑枯病",
    "Tomato___Spider_mites Two-spotted_spider_mite": "番茄二斑叶螨",
    "Tomato___Target_Spot": "番茄靶斑病",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "番茄黄化曲叶病毒",
    "Tomato___Tomato_mosaic_virus": "番茄花叶病毒",
    "Tomato___healthy": "番茄健康",
    "Potato___Early_blight": "马铃薯早疫病",
    "Potato___Late_blight": "马铃薯晚疫病",
    "Potato___healthy": "马铃薯健康",
    "Pepper,_bell___Bacterial_spot": "辣椒细菌性斑点病",
    "Pepper,_bell___healthy": "辣椒健康",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "玉米灰斑病",
    "Corn_(maize)___Common_rust_": "玉米普通锈病",
    "Corn_(maize)___Northern_Leaf_Blight": "玉米大斑病",
    "Corn_(maize)___healthy": "玉米健康",
    "Apple___Apple_scab": "苹果黑星病",
    "Apple___Black_rot": "苹果黑腐病",
    "Apple___Cedar_apple_rust": "苹果锈病",
    "Apple___healthy": "苹果健康",
    "Grape___Black_rot": "葡萄黑腐病",
    "Grape___Esca_(Black_Measles)": "葡萄黑麻疹病",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "葡萄叶枯病",
    "Grape___healthy": "葡萄健康",
}


def _get_classifier():
    """懒加载分类器（首次调用时才加载模型）"""
    global _classifier, _current_model_name
    if _classifier is not None:
        return _classifier

    model_info = MODEL_REGISTRY[_current_model_name]
    model_id = model_info["model_id"]

    try:
        from transformers import pipeline
        _classifier = pipeline("image-classification", model=model_id, top_k=5)
        return _classifier
    except Exception as e:
        # 如果模型下载失败，返回模拟分类器
        return None


def _mock_classify(image_path: str) -> list[dict]:
    """模拟分类结果（当模型不可用时）"""
    # 根据文件名猜测作物类型
    fname = os.path.basename(image_path).lower() if image_path else ""
    if "tomato" in fname or "番茄" in fname:
        return [
            {"label": "Tomato___Leaf_Mold", "score": 0.87},
            {"label": "Tomato___Early_blight", "score": 0.08},
            {"label": "Tomato___healthy", "score": 0.03},
        ]
    elif "cucumber" in fname or "黄瓜" in fname:
        return [
            {"label": "Tomato___Leaf_Mold", "score": 0.45},  # 最近似
            {"label": "Potato___Late_blight", "score": 0.30},
            {"label": "Tomato___healthy", "score": 0.15},
        ]
    else:
        return [
            {"label": "Tomato___Leaf_Mold", "score": 0.60},
            {"label": "Tomato___Early_blight", "score": 0.20},
            {"label": "Tomato___healthy", "score": 0.10},
        ]


def _format_result(raw_results: list[dict], image_path: str) -> dict:
    """将模型原始输出格式化为结构化诊断结果"""
    top = raw_results[0] if raw_results else {}
    label = top.get("label", "unknown")
    confidence = top.get("score", 0)

    # 查找中文名
    cn_name = DISEASE_LABELS.get(label, label)
    is_healthy = "healthy" in label.lower()

    # 构建 top-3 匹配
    top3 = []
    for r in raw_results[:3]:
        r_label = r.get("label", "")
        top3.append({
            "disease": DISEASE_LABELS.get(r_label, r_label),
            "disease_en": r_label,
            "confidence": round(r.get("score", 0), 4),
        })

    return {
        "image_path": image_path,
        "model": _current_model_name,
        "model_info": MODEL_REGISTRY[_current_model_name],
        "diagnosis": {
            "primary": cn_name,
            "primary_en": label,
            "confidence": round(confidence, 4),
            "is_healthy": is_healthy,
            "top3": top3,
        },
        "summary": (
            f"✅ 作物健康，未发现明显病害" if is_healthy
            else f"⚠️ 检测到 {cn_name}（置信度 {confidence:.1%}）"
        ),
    }


# ============================================================
# MCP Tools
# ============================================================

@mcp.tool()
def diagnose_image(image_path: str) -> dict:
    """对植物叶片图像进行病害识别。

    Args:
        image_path: 图像文件路径（支持 jpg, png, bmp）
    """
    if not os.path.exists(image_path):
        return {"error": f"图像文件不存在: {image_path}"}

    classifier = _get_classifier()

    if classifier is not None:
        try:
            raw_results = classifier(image_path)
            return _format_result(raw_results, image_path)
        except Exception as e:
            return {"error": f"模型推理失败: {str(e)}", "fallback": "mock"}
    else:
        # 使用模拟分类器
        raw_results = _mock_classify(image_path)
        result = _format_result(raw_results, image_path)
        result["note"] = "⚠️ 模型未加载，使用模拟数据。请安装 transformers 和 torch 后重试。"
        return result


@mcp.tool()
def diagnose_image_base64(image_base64: str, filename: str = "upload.jpg") -> dict:
    """对 Base64 编码的植物叶片图像进行病害识别。

    Args:
        image_base64: Base64 编码的图像数据
        filename: 文件名（用于结果标识）
    """
    import base64
    import tempfile

    try:
        image_data = base64.b64decode(image_base64)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(image_data)
            temp_path = f.name

        result = diagnose_image(temp_path)
        result["filename"] = filename

        # 清理临时文件
        os.unlink(temp_path)
        return result
    except Exception as e:
        return {"error": f"Base64 解码失败: {str(e)}"}


@mcp.tool()
def list_models() -> dict:
    """列出所有可用的视觉模型。"""
    models = {}
    for name, info in MODEL_REGISTRY.items():
        models[name] = {
            **info,
            "active": name == _current_model_name,
        }
    return {"current_model": _current_model_name, "models": models}


@mcp.tool()
def switch_model(model_name: str) -> dict:
    """切换视觉模型。

    Args:
        model_name: 模型名称，可选: swin-tiny, vit-base, mobilenet-v2, tomato-vit
    """
    global _classifier, _current_model_name

    if model_name not in MODEL_REGISTRY:
        return {"error": f"未知模型: {model_name}，可选: {list(MODEL_REGISTRY.keys())}"}

    _current_model_name = model_name
    _classifier = None  # 重置，下次调用时重新加载

    return {
        "status": "ok",
        "message": f"已切换到 {model_name}（{MODEL_REGISTRY[model_name]['description']}）",
        "model_info": MODEL_REGISTRY[model_name],
    }


@mcp.tool()
def get_disease_info_cn(disease_label: str) -> dict:
    """获取病害的中文信息。

    Args:
        disease_label: 病害英文标签，如 Tomato___Leaf_Mold
    """
    cn_name = DISEASE_LABELS.get(disease_label)
    if not cn_name:
        return {"error": f"未知病害标签: {disease_label}"}
    return {
        "label": disease_label,
        "name_cn": cn_name,
        "is_healthy": "healthy" in disease_label.lower(),
    }


if __name__ == "__main__":
    mcp.run()
