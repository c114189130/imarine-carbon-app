import json
import os

def ensure_json_file(file_path, default_content):
    """確保 JSON 檔案存在"""
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_content, f, ensure_ascii=False, indent=2)

def read_json(file_path, default=None):
    """讀取 JSON 檔案，支援預設值"""
    if not os.path.exists(file_path):
        return default if default is not None else []
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(file_path, data):
    """寫入 JSON 檔案"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)