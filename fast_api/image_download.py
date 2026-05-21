import requests
import time
import os
import json
from datetime import datetime, timedelta

#==========================
#   ファイル関連
#==========================
save_dir = "images"     #画像保存用フォルダパス
os.makedirs(save_dir, exist_ok=True)    # 画像保存用フォルダ作成
json_path = './scraping_config.json'    # JSON読み込み用パス
download_error_log_path = f'{save_dir}/download_error.log'  #エラーログ記録用パス

# ヘッダー設定
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

# 開始日時設定
end_date_str = "20260514"
end_date = datetime.strptime(end_date_str, "%Y%m%d")
# 開始日時より何日遡るか
duration_days = 20  
start_date = end_date - timedelta(days=duration_days)

# url接頭語
url_prefix = f"https://cam.river.go.jp/cam/history/"

# スクレイピング情報記述jsonファイル読み込み
try:
    with open(json_path, 'r' , encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"エラー: {json_path} が見つかりません。")
    exit()
except json.JSONDecodeError:
    print("エラー: JSONの形式が正しくありません。")
    exit()

for location_id, info in data.items():

    url_suffix = info['url_suffix']

    area_dir = f"{save_dir}/{info['area']}"
    os.makedirs(area_dir, exist_ok=True)

    for i in range(duration_days):
        target_date = start_date + timedelta(days=i)

        formatted_date = target_date.strftime("%Y%m%d")

        for hour in range(14):      # 時間（5時〜18時）
            formattad_hour = f"{hour + 5:02d}"          #時間単位を記述

            for minutes  in range(6):  # 分（00分〜50分）
                formattad_minutes = f"{minutes * 10:02d}"   #分単位を記述

                target_datetime = formatted_date + formattad_hour + formattad_minutes   #日時分からフォーマット済文字列を作成

                file_path = f'{save_dir}/{info["area"]}/{location_id}-{target_datetime}.jpg'   #保存先パス

                # ファイルの存在チェック
                if os.path.exists(file_path):
                    print(f"Skip: {file_path} はすでに存在します")
                
                else:
                    url = F'{url_prefix}{target_datetime}{url_suffix}'
                    response = requests.get(url, headers=headers)
                    # レスポンス取得成功チェック
                    if response.status_code == 200:
                        with open(file_path, "wb") as f:
                            f.write(response.content)
                            print(f"成功： {file_path}")
                    else:
                        #エラーログを書きコンソールに出力
                        with open(download_error_log_path, mode='a') as f:
                            f.write(f'\nDownload Error： {url}')
                            print(f'失敗({response.status_code})： {url}')
                    
                    time.sleep(1.5)