import requests
import time
import os
import json
import sys
import traceback
from datetime import datetime, timedelta

#==========================
#   変数宣言
#==========================

#--------- フォルダ関連 -------------
save_dir = "images"     #画像保存用フォルダパス
os.makedirs(save_dir, exist_ok=True)    # 画像保存用フォルダ作成
json_path = './scraping_config.json'    # JSON読み込み用パス
download_error_log_path = f'{save_dir}/download_error.log'  #エラーログ記録用パス
progress_json_path = './scraping_progress.json'  # 進捗保存用JSONパス

# --------- ヘッダー設定 ------------
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

# --------- スクレイピング関連 ---------
# 開始日時設定
end_date_str = "20260514"
end_date = datetime.strptime(end_date_str, "%Y%m%d")
# 開始日時より何日遡るか
duration_days = 20  
start_date = end_date - timedelta(days=duration_days)

# url接頭語
url_prefix = f"https://cam.river.go.jp/cam/history/"

# for文外からも変数を確認できるようスコープを広げる
location_id = day = hour = minutes = None

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

#--------------------------------------------------
# 進捗保存・読み込み機能
#--------------------------------------------------
def save_progress(location_id, day, hour, minutes, status="running", error_msg=None):
    progress = {
        "location_id": location_id,
        "day": day,
        "hour": hour,
        "minutes": minutes,
        "status": status,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    if error_msg:
        progress["error"] = error_msg
    with open(progress_json_path, 'w', encoding='utf-8') as pf:
        json.dump(progress, pf, indent=4, ensure_ascii=False)

# 前回の中断データを読み込み
try:
    with open(progress_json_path, 'r', encoding='utf-8') as pf:
        last_state = json.load(pf)
        print(f"中断位置から再開: {last_state['location_id']} | {last_state['day']}日後 | {last_state['hour']+5}時 | {last_state['minutes']*10}分")
        
        resume_location = last_state.get("location_id")
        resume_day = last_state.get("day")
        resume_hour = last_state.get("hour")
        resume_minutes = last_state.get("minutes")
        
        # 再開位置が存在する場合のみスキップフラグを立てる
        is_skipping = True
except FileNotFoundError:
    resume_location = resume_day = resume_hour = resume_minutes = None
    is_skipping = False

try:
    for location_id, info in data.items():

        # 再開場所にたどり着いてないならスキップ
        if is_skipping:
            if location_id != resume_location:
                continue

        url_suffix = info['url_suffix']

        # フォルダの作成
        area_dir = f"{save_dir}/{info['area']}" # フォルダパスを作成
        os.makedirs(area_dir, exist_ok=True)    # 存在チェックしつつ作成

        for day in range(duration_days):
            # 再開場所にたどり着いてないならスキップ
            if is_skipping:
                    if day != resume_day:
                        continue

            target_date = start_date + timedelta(days=day)  # 該当日時を計算
            formatted_date = target_date.strftime("%Y%m%d") # フォーマット

            for hour in range(14):      # 時間（5時〜18時）
                # 再開場所にたどり着いてないならスキップ
                if is_skipping:
                    if hour != resume_hour:
                        continue  # ターゲットの時間に届くまで飛ばす

                formattad_hour = f"{hour + 5:02d}"          #時間単位を記述
                
                for minutes  in range(6):  # 分（00分〜50分）
                    if is_skipping:
                            if minutes != resume_minutes:
                                continue  # ターゲットの分に届くまで飛ばす
                            else:
                                # 一致したので目的の場所にたどり着いたとわかる
                                is_skipping = False  # スキップフラグを解除
                                continue  # 保存済みの最後の1件なので、これ自体はスキップ

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

    # 全て正常終了したら進捗ファイルを削除
        if os.path.exists(progress_json_path):
            os.remove(progress_json_path)
        print("【完了】すべてのスクレイピングタスクが正常に終了しました。")

except KeyboardInterrupt:
    print("\n[ユーザー中断] 状態を記録して終了します。")
    save_progress(location_id, day, hour, minutes, status="stopped_by_user")
    sys.exit(0)

except Exception as e:
    print(f"\n[エラー発生] 異常終了しました: {e}")
    error_details = traceback.format_exc()
    print(error_details)
    
    save_progress(location_id, day, hour, minutes, status="error_terminated", error_msg=str(e))
    with open(f"{save_dir}/system_crash.log", "a", encoding="utf-8") as f:
        f.write(f"\n--- {datetime.now()} ---\n{error_details}\n")
    sys.exit(1)