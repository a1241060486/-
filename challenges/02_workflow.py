# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai",
# ]
# ///

import os
import json
import sys
import time
from openai import OpenAI

# ==========================================
# 配置区域
# ==========================================
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
# 允许从环境变量覆盖模型名称，默认为 deepseek-chat
MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")

if not API_KEY:
    print("❌ Error: 请设置环境变量 DEEPSEEK_API_KEY")
    sys.exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

class LongArticleAgent:
    def __init__(self, topic):
        self.topic = topic
        self.outline = []
        self.articles = []

    def step1_generate_outline(self):
        """Step 1: 生成章节大纲"""
        print(f"📋 正在规划主题: {self.topic}...")
        
        # TODO: 编写 Prompt 让模型生成纯 JSON 列表
        prompt = f"请为主题《{self.topic}》生成一个包含3个章节的大纲，严格以json格式返回，只返回三个字段：'chapter1', 'chapter2', 'chapter3'。每个字段的内容为中文文本，且文本长度不超过20个字。不要返回其余内容。"
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,  # 使用配置的模型名
                messages=[
                    {"role": "system", "content": "你是一个专业的写作规划师，只输出 JSON Array。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            content = response.choices[0].message.content
            
            # TODO: 解析返回的 JSON 内容到 self.outline
            data = json.loads(content)
            
            # 简单的容错逻辑示例（候选人需要完善）
            if isinstance(data, list):
                raise ValueError("返回非json格式！")
            elif isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, list):
                        self.outline.append(value[0])
                    else:
                        self.outline.append(value)
            
            if not self.outline:
                raise ValueError("未找到有效的大纲列表")

            print(f"✅ 大纲已生成: {self.outline}")

        except Exception as e:
            print(f"❌ 大纲生成失败: {e}")
            print(f"Raw Content: {content if 'content' in locals() else 'None'}")
            sys.exit(1)

    def step2_generate_content_loop(self):
        """Step 2: 循环生成内容，并维护 Context"""
        if not self.outline:
            return

        # 初始化上下文摘要
        previous_summary = "文章开始，无前文信息。"
        
        print("\n🚀 开始撰写正文...")
        for i, chapter in enumerate(self.outline):
            print(f"[{i+1}/{len(self.outline)}] 正在撰写: {chapter}...")
            
            # TODO: 构造 Prompt，核心在于 Context 的注入
            prompt = f"""
            你是一位专业作家。请撰写章节："{chapter}"。此为章节大纲，围绕该大纲进行写作。
            
            【前情提要】：
            {previous_summary}
            
            要求：
            1. 内容充实，字数约 300 字。
            2. 必须承接【前情提要】的逻辑，不要重复。
            3. 围绕章节大纲进行写作，不要过于发散。
            4. 不要返回章节大纲内容，只返回输出。
            """
            
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,  # 使用配置的模型名
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7
                )
                content = response.choices[0].message.content
                self.articles.append(f"## {chapter}\n\n{content}")
                
                # TODO: 更新 Context (核心考察点)
                # 策略：对输出内容进行压缩，提取全文关键信息，注入prompt

                truc_prompt = f'''你是一位信息提取专家，你擅长将长文本压缩至短文本，来获取关键信息。现在，对下文进行信息提取。
                ------------
                content:
                {content}
                -------------
                注意，返回文本长度不超过100个字。
                '''

                response = client.chat.completions.create(
                    model=MODEL_NAME,  # 使用配置的模型名
                    messages=[{"role": "user", "content": truc_prompt}],
                    temperature=0.7
                )
                truc_content = response.choices[0].message.content

                previous_summary = truc_content
                
            except Exception as e:
                print(f"⚠️ 章节 {chapter} 生成失败: {e}")

    def save_result(self):
        if not self.articles:
            print("⚠️ 没有生成任何内容")
            return
            
        filename = "final_article.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {self.topic}\n\n")
            f.write("\n\n".join(self.articles))
        print(f"\n🎉 文章已保存至 {filename}")

if __name__ == "__main__":
    print(f"🔌 Endpoint: {BASE_URL}")
    print(f"🧠 Model: {MODEL_NAME}\n")
    
    agent = LongArticleAgent("2025年 DeepSeek 对 AI 行业的影响")
    agent.step1_generate_outline()
    agent.step2_generate_content_loop()
    agent.save_result()