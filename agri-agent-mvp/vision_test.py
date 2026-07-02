"""
Swin-Tiny 视觉分类测试脚本

在你的 Windows 上运行（需要有 GPU 或 CPU）：
1. pip install torch transformers torchvision pillow
2. python vision_test.py

如果 torch 安装太慢，可以只装 CPU 版：
pip install torch --index-url https://download.pytorch.org/whl/cpu

首次运行会自动从 HuggingFace 下载模型（约 100MB），可能需要几分钟。
"""

import sys
import os

# 设置环境变量，确保 transformers 使用 CPU
os.environ["TRANSFORMERS_OFFLINE"] = "0"

from transformers import pipeline, AutoImageProcessor, AutoModelForImageClassification
from PIL import Image
import numpy as np
import time

# ============================================================
# 模型配置
# ============================================================

MODELS = {
    "swin-tiny": {
        "model_id": "gianlab/swin-tiny-patch4-window7-224-finetuned-plantdisease",
        "architecture": "Swin-Tiny",
        "params": "28M",
        "description": "Swin Transformer Tiny - 层级化 ViT，植物病害分类",
    },
    "mobilenet-v2": {
        "model_id": "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification",
        "architecture": "MobileNetV2",
        "params": "3.4M",
        "description": "MobileNetV2 - 轻量级，适合边缘部署",
    },
    "vit-base": {
        "model_id": "Alan04020/vit-plant-disease-v2",
        "architecture": "ViT-Base/16",
        "params": "86M",
        "description": "Vision Transformer Base - 高准确率",
    },
}

# PlantVillage 38 类 → 中文
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


def load_model(name: str) -> pipeline:
    """加载指定模型"""
    config = MODELS[name]
    print(f"\n加载模型: {name} ({config['architecture']}, {config['params']})")
    print(f"  模型地址: {config['model_id']}")
    print(f"  首次运行需要下载模型，请稍候...")

    start = time.time()
    try:
        clf = pipeline("image-classification", model=config["model_id"], top_k=5)
        elapsed = time.time() - start
        print(f"  ✅ 加载完成，耗时 {elapsed:.1f}s")
        return clf
    except Exception as e:
        print(f"  ❌ 加载失败: {e}")
        print("  提示: 请检查网络连接，确保能访问 HuggingFace Hub")
        return None


def create_test_image() -> str:
    """创建一张测试图片（纯色，用于验证管道是否工作）"""
    img = Image.new("RGB", (224, 224), color=(50, 150, 50))  # 绿色
    path = os.path.join(os.path.dirname(__file__), "_test_image.jpg")
    img.save(path, "JPEG")
    return path


def diagnose(clf, image_path: str) -> dict:
    """对图片进行病害识别"""
    print(f"\n📷 识别图片: {image_path}")

    start = time.time()
    results = clf(image_path)
    elapsed = time.time() - start

    print(f"  ⏱️ 推理耗时: {elapsed:.3f}s")

    top = results[0]
    label = top["label"]
    conf = top["score"]
    cn = DISEASE_LABELS.get(label, label)

    print(f"  🏷️  Top-1: {cn} ({label})")
    print(f"  📊  置信度: {conf:.4f}")
    print(f"  📊  Top-3:")
    for r in results[:3]:
        cn_r = DISEASE_LABELS.get(r["label"], r["label"])
        print(f"       {r['label']:45s} {r['score']:.4f}  ({cn_r})")

    return {
        "label": label,
        "label_cn": cn,
        "confidence": conf,
        "top3": results[:3],
        "inference_time_s": round(elapsed, 3),
    }


def run_benchmark(clf, name: str, image_path: str, iterations: int = 5):
    """性能基准测试"""
    print(f"\n⚡ {name} 性能基准 ({iterations} 次推理平均):")

    times = []
    for i in range(iterations):
        start = time.time()
        clf(image_path)
        times.append(time.time() - start)

    avg = sum(times) / len(times)
    print(f"  平均耗时: {avg*1000:.1f}ms")
    print(f"  最快: {min(times)*1000:.1f}ms")
    print(f"  最慢: {max(times)*1000:.1f}ms")
    return avg


def main():
    print("=" * 60)
    print("  Swin-Tiny 植物病害识别测试")
    print("=" * 60)

    # 检查 torch
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"  PyTorch: {torch.__version__}")
        print(f"  设备: {device}")
        if device == "cuda":
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("  ❌ PyTorch 未安装。请先运行:")
        print("     pip install torch transformers torchvision pillow")
        return

    # 创建测试图片
    test_img = create_test_image()

    # 选择模型
    model_choice = sys.argv[1] if len(sys.argv) > 1 else "swin-tiny"
    if model_choice not in MODELS:
        print(f"  可用模型: {list(MODELS.keys())}")
        return

    # 加载模型
    clf = load_model(model_choice)
    if clf is None:
        return

    # 运行诊断
    result = diagnose(clf, test_img)

    # 性能基准
    run_benchmark(clf, model_choice, test_img, iterations=3)

    # 清理
    os.unlink(test_img)

    print("\n" + "=" * 60)
    print("  测试完成 ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
