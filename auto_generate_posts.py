import requests
import xmltodict
import json
import time
import random
import os
from datetime import datetime

# 配置
# 必须从环境变量获取，不提供默认敏感信息
RSS_URL = os.getenv("RSS_URL", "https://rss.mydrivers.com/Rss.aspx?Tid=1").strip()
MEITUAN_API_KEY = os.getenv("MEITUAN_API_KEY", "").strip()
UPLOAD_API_URL = os.getenv("UPLOAD_API_URL", "https://ongwu-site.vercel.app/api/upload").strip()
UPLOAD_API_TOKEN = os.getenv("UPLOAD_API_TOKEN", "").strip()

if not MEITUAN_API_KEY:
    raise ValueError("❌ 错误: 未设置 MEITUAN_API_KEY 环境变量")

if not UPLOAD_API_TOKEN:
    raise ValueError("❌ 错误: 未设置 UPLOAD_API_TOKEN 环境变量")

KEYWORDS = ["科技", "计算机", "网络", "技术", "系统", "AI", "人工智能", "芯片", "软件"]

def fetch_rss():
    print(f"正在获取 RSS: {RSS_URL}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(RSS_URL, headers=headers, timeout=30) # 增加 User-Agent 和超时时间
        response.encoding = 'utf-8'
        data = xmltodict.parse(response.text)
        items = data['rss']['channel']['item']
        print(f"获取到 {len(items)} 条新闻")
        return items
    except Exception as e:
        print(f"RSS 获取失败: {e}")
        return []

def filter_news(items):
    filtered = []
    for item in items:
        title = item['title']
        description = item.get('description', '')
        # 简单关键词匹配
        if any(k in title for k in KEYWORDS) or any(k in description for k in KEYWORDS):
            filtered.append(item)
    print(f"筛选出 {len(filtered)} 条相关新闻")
    return filtered

def call_meituan_ai(prompt):
    print(f"正在调用 AI 生成内容 (Prompt 长度: {len(prompt)})...")
    
    url = "https://api.longcat.chat/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MEITUAN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "LongCat-Flash-Chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4000, # 增加 token 限制以支持长文
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60) # 增加超时时间
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print("AI 生成成功")
                return content
            else:
                print(f"AI 响应格式异常: {result}")
                return ""
        else:
            print(f"AI 请求失败: {response.status_code} - {response.text}")
            return ""
    except Exception as e:
        print(f"AI 调用出错: {e}")
        return ""

def generate_article(news_item, category="tech"):
    original_title = news_item['title']
    print(f"正在处理 [{category}]: {original_title}")
    
    # 1. 生成 3 个标题
    prompt_title = f"请根据原新闻标题“{original_title}”，生成3个吸引人的、科技感强的文章标题。要求：\n1. 严禁使用数字序号（如1. 2. 3.）\n2. 严禁使用引号\n3. 每行一个标题，只返回标题文本"
    titles_text = call_meituan_ai(prompt_title)
    
    # 分割并清洗标题
    new_titles = []
    for t in titles_text.split('\n'):
        clean_t = t.strip()
        # 去除开头的数字和点 (例如 "1. ", "2. ")
        import re
        clean_t = re.sub(r'^\d+[\.、\s]+', '', clean_t)
        # 去除首尾引号
        clean_t = clean_t.strip('"\'')
        if clean_t:
            new_titles.append(clean_t)
            
    new_titles = new_titles[:3]
    if not new_titles:
        new_titles = [original_title]
    
    selected_title = random.choice(new_titles) # 随机选一个，而不是总是第一个
    print(f"选用标题: {selected_title}")
    
    # 2. 生成正文
    prompt_content = f"请以 'ongwu' 的口吻，根据标题“{selected_title}”和原新闻“{original_title}”，写一篇2000字左右的深度科技文章。风格要专业、客观且有见地。使用 Markdown 格式。正文中不要包含图片。"
    content = call_meituan_ai(prompt_content)
    
    # 清洗 AI 返回的内容，去除可能存在的 markdown 代码块标记
    content = content.replace("```markdown", "").replace("```", "").strip()
    
    return {
        "title": selected_title,
        "content": content,
        "menu": category, # 使用传入的分类
        "keywords": "科技,AI,自动生成",
        "description": f"关于 {original_title} 的深度解读"
    }

def upload_post(article):
    print(f"正在上传: {article['title']}...")
    headers = {
        "Authorization": f"Bearer {UPLOAD_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 生成 slug (简单处理，使用时间戳)
    slug = f"auto-{int(time.time())}-{random.randint(100,999)}"
    
    payload = {
        "title": article['title'],
        "content": article['content'],
        "menu": article['menu'],
        "slug": slug,
        "keywords": article['keywords'],
        "description": article['description']
    }
    
    try:
        resp = requests.post(UPLOAD_API_URL, json=payload, headers=headers)
        if resp.status_code == 200:
            print("✅ 上传成功")
        else:
            print(f"❌ 上传失败: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ 请求错误: {e}")

def main():
    items = fetch_rss()
    filtered = filter_news(items)
    
    if len(filtered) < 2:
        print("符合条件的新闻不足 2 条，无法分别生成 tech 和 news")
        # 也可以放宽条件，或者重复使用
        if not filtered:
            return
    
    # 随机选择 2 条不同的新闻
    # 如果只有 1 条，就只能用这一条生成两次不同的（或者只生成一次）
    # 这里假设新闻足够多
    
    # 这里的逻辑是：
    # 1. 选一条给 tech
    # 2. 选另一条给 news
    
    selected_items = random.sample(filtered, min(2, len(filtered)))
    
    # 第一篇：Tech
    print("\n=== 生成 Tech 文章 ===")
    article_tech = generate_article(selected_items[0], category="tech")
    upload_post(article_tech)
    
    # 第二篇：News (如果有足够的新闻)
    if len(selected_items) > 1:
        print("\n=== 生成 News 文章 ===")
        article_news = generate_article(selected_items[1], category="news")
        upload_post(article_news)
    else:
        # 如果只有一条新闻，用同一条新闻再生成一篇 news
        print("\n=== 生成 News 文章 (复用新闻源) ===")
        article_news = generate_article(selected_items[0], category="news")
        upload_post(article_news)
        
    print("-" * 50)

if __name__ == "__main__":
    main()
