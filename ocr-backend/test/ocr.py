from paddleocr import PaddleOCR
import json

ocr = PaddleOCR(
    ocr_version="PP-OCRv5",
    device="gpu",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)

# 识别技能及位置
result = ocr.predict("./skills.png")
save_path = "./skills_result.json"
for res in result:
    res.save_to_json(save_path)
print(f"Saved to {save_path}")

# 识别宠物状态-自己宠物
result = ocr.predict("./state_self.png")
save_path = "./state_self_result.json"
for res in result:
    res.save_to_json(save_path)
print(f"Saved to {save_path}")

# 识别宠物状态-自己宠物
result = ocr.predict("./state_self2.png")
save_path = "./state_self2_result.json"
for res in result:
    res.save_to_json(save_path)
print(f"Saved to {save_path}")


# 识别宠物状态-敌方宠物
result = ocr.predict("./state_enemy.png")
save_path = "./state_enemy_result.json"
for res in result:
    res.save_to_json(save_path)
print(f"Saved to {save_path}")

# 识别宠物状态-敌方宠物
result = ocr.predict("./state_enemy2.png")
save_path = "./state_enemy2_result.json"
for res in result:
    res.save_to_json(save_path)
print(f"Saved to {save_path}")