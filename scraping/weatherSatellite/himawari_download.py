import requests
from PIL import Image
from io import BytesIO
import time
import os
import json
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv(dotenv_path='local.env')
url = os.getenv("HIMAWARI_BASE_URL")

# ==========================
# 変数・パス設定
# ==========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = "/data/himawari"
ERROR_LOG_PATH = os.path.join(BASE_DIR, "download_error.log")
ERROR_JSON_PATH = os.path.join(BASE_DIR, "error_details.json")
RESUME_FILE = os.path.join(BASE_DIR, "resume_point.json")

os.makedirs(SAVE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/124.0.0.0",
    "Referer": "https://himawari8.nict.go.jp/"
}

def save_error_to_json(url, error_message):
    data = {}
    if os.path.exists(ERROR_JSON_PATH):
        with open(ERROR_JSON_PATH, 'r', encoding='utf-8') as f:
            try: data = json.load(f)
            except json.JSONDecodeError: data = {}
    data[url] = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "error": error_message}
    with open(ERROR_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def fetch_and_merge_tiles(base_url, save_path):
    tiles = {}
    coords = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for x, y in coords:
        url = f"{base_url}{x}_{y}.png"
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            tiles[(x, y)] = Image.open(BytesIO(response.content))
        elif response.status_code == 404:
            raise ValueError(f"Not Found: {url}")
        else:
            raise Exception(f"Failed {url} Status: {response.status_code}")
        time.sleep(0.2)
    tile_w, tile_h = tiles[(0, 0)].size
    merged_img = Image.new('RGB', (tile_w * 2, tile_h * 2))
    merged_img.paste(tiles[(0, 0)], (0, 0))
    merged_img.paste(tiles[(1, 0)], (tile_w, 0))
    merged_img.paste(tiles[(0, 1)], (0, tile_h))
    merged_img.paste(tiles[(1, 1)], (tile_w, tile_h))
    merged_img.save(save_path)

# ==========================
# メイン処理
# ==========================
start_jst = datetime(2026, 4, 24, 5, 0)
end_jst = datetime(2026, 6, 3, 18, 50)

# JSONから再開位置を読み込み
if os.path.exists(RESUME_FILE):
    with open(RESUME_FILE, 'r') as f:
        try:
            resume_data = json.load(f)
            current_jst = datetime.strptime(resume_data['last_time'], "%Y%m%d%H%M")
            print(f"中断位置から再開します: {current_jst}")
        except:
            current_jst = start_jst
else:
    current_jst = start_jst

# 終了時刻を過ぎていたらリセット
if current_jst > end_jst:
    current_jst = start_jst

reload_flg = 0

while current_jst <= end_jst:
    # 処理開始前に、今の時刻をJSONに記録
    with open(RESUME_FILE, 'w') as f:
        json.dump({'last_time': current_jst.strftime("%Y%m%d%H%M")}, f)

    try:
        utc_time = current_jst - timedelta(hours=9)
        date_path = utc_time.strftime("%Y/%m/%d")
        time_path = utc_time.strftime("%H%M00")
        file_name = f"himawari-{current_jst.strftime('%Y%m%d%H%M')}.png"
        save_path = os.path.join(SAVE_DIR, file_name)
        
        if not os.path.exists(save_path):
            base_url = f"{url}/{date_path}/{time_path}_"
            print(f"Downloading: {file_name}")
            fetch_and_merge_tiles(base_url, save_path)
            time.sleep(2.0)

        reload_flg = 0
        current_jst += timedelta(minutes=10)
        if current_jst.hour >= 19:
            current_jst = (current_jst + timedelta(days=1)).replace(hour=5, minute=0)
            continue
            
    except ValueError as ve:
        error_url = str(ve).replace("Not Found: ", "")
        save_error_to_json(error_url, str(ve))
        with open(ERROR_LOG_PATH, "a") as f:
            f.write(f"{datetime.now()}: {ve}\n")
        print(f"スキップ (404): {ve}")
        reload_flg = 0
        current_jst += timedelta(minutes=10)
        if current_jst.hour >= 19:
            current_jst = (current_jst + timedelta(days=1)).replace(hour=5, minute=0)

    except Exception as e:
        with open(ERROR_LOG_PATH, "a") as f:
            f.write(f"{datetime.now()}: FATAL ERROR: {traceback.format_exc()}\n")
        print(f"致命的なエラーのため一時停止します: {e}")
        reload_flg += 1
        if reload_flg >= 3:
            print("3回連続で致命的なエラーが発生しました。処理を終了します。")
            raise SystemExit("致命的なエラーのため処理を終了します。")
        time.sleep(60)  # 1分待機して再試行
        continue

# 全て完了したらJSONを削除
if os.path.exists(RESUME_FILE):
    os.remove(RESUME_FILE)

print("処理が正常に完了しました。")