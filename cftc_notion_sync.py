import os
import requests
import re
from datetime import datetime

# 环境变量读取
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
REPO_NAME = os.environ.get("GITHUB_REPO") 

# CFTC Metals and Other 独立直链
CFTC_URL = "https://www.cftc.gov/dea/options/other_lof.htm"

def process_file_and_notion():
    print("Downloading Metals & Other report from CFTC...")
    response = requests.get(CFTC_URL, headers={'User-Agent': 'Mozilla/5.0'})
    response.raise_for_status()
    text_content = response.text
    
    # 1. 精准提取文件中的客观确切时间
    match = re.search(r"Options and Futures Combined, ([A-Za-z]+ \d{1,2}, \d{4})", text_content)
    
    if not match:
        print("Error: Could not extract exact date. Data fetch delayed or format changed. Marking as N/A.")
        # 无法获取最新的确切数值/时间时，停止执行，不进行任何模拟外推
        return
        
    raw_date = match.group(1)
    # 将 "March 10, 2026" 转换为 "2026-03-10"
    parsed_date = datetime.strptime(raw_date, "%B %d, %Y").strftime("%Y-%m-%d")
    print(f"Extracted Exact Date from file: {parsed_date}")
    
    # 2. 将内容保存为本地 txt 文件
    save_dir = "data"
    os.makedirs(save_dir, exist_ok=True)
    file_name = f"CFTC_Metals_Other_Combined_{parsed_date}.txt"
    file_path = f"{save_dir}/{file_name}"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text_content)
        
    # 3. 构造 GitHub Raw URL
    github_raw_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{file_path}"
    
    # 4. 更新 Notion Database
    notion_api_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": "CFTC Metals & Other - Combined"}}]
            },
            "Date": {
                "date": {"start": parsed_date}
            },
            "Files & media": {
                "files": [
                    {
                        "type": "external",
                        "name": file_name,
                        "external": {"url": github_raw_url}
                    }
                ]
            }
        }
    }
    
    res = requests.post(notion_api_url, headers=headers, json=payload)
    if res.status_code == 200:
        print(f"Successfully created Notion record for {parsed_date}!")
    else:
        print(f"Failed to update Notion: {res.text}")

if __name__ == "__main__":
    process_file_and_notion()
