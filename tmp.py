
import psycopg2
import requests
import random
import string
import time
from datetime import datetime, timedelta

retry_num = 3  # 重试次数
retry_delay = 0.5  # 重试间隔时间（秒）
# 定义连接到数据库的函数
def connect_to_db():
    return psycopg2.connect(
        database="cdn_vod",
        user="postgres",
        password="098lkj.",
        host="10.8.24.117"
    )

# 生成随机 17 位大小写编码
def generate_random_asset_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=17))

# 获取当前时间和两小时之前的时间戳
def get_time_stamps():
    current_time = datetime.now()
    start_time = current_time - timedelta(hours=1, minutes=44, seconds=6.81)
    start_timestamp = int(start_time.timestamp())
    end_timestamp = int(current_time.timestamp())
    return start_timestamp, end_timestamp

# 发送请求并插入数据到数据库
def send_request_and_insert_to_db():
    asset_id = 's_grid_channel2' + generate_random_asset_id()
    start_time, end_time = get_time_stamps()

    # 构造请求体
    payload = {
        "streamCode": "grid_channel2",
        "assetId": asset_id,
        "programName": "节目名称",
        "startTime": str(start_time),
        "endTime": str(end_time),
    }

    # 发送请求
    url = "http://192.168.1.106/api/cms/tvod/notice"
    headers = {"Host": "mcmpserver.test-xxl.com"}
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        print(f"请求成功：{response.json()}")
        # 插入到数据库
        conn = connect_to_db()
        cursor = conn.cursor()

        # 插入数据到 public.t_asset
        metadata_json = '{"name": "tests3G8509021490i", "size": 1530040444, "width": 1920, "format": "mpegts", "height": 800, "version": 0, "duration": 6246805333, "snapshot": {"width": 256, "height": 144, "package": "zip", "snapfiles": [{"seq": 0, "name": "tests3G8509021490i-0000-78.webp", "offset": 0}, {"seq": 1, "name": "tests3G8509021490i-0001-78.webp", "offset": 698999}, {"seq": 2, "name": "tests3G8509021490i-0002-78.webp", "offset": 1249726}, {"seq": 3, "name": "tests3G8509021490i-0003-78.webp", "offset": 1762871}, {"seq": 4, "name": "tests3G8509021490i-0004-78.webp", "offset": 2600848}, {"seq": 5, "name": "tests3G8509021490i-0005-78.webp", "offset": 3264535}, {"seq": 6, "name": "tests3G8509021490i-0006-78.webp", "offset": 3900476}, {"seq": 7, "name": "tests3G8509021490i-0007-78.webp", "offset": 4554067}, {"seq": 8, "name": "tests3G8509021490i-0008-78.webp", "offset": 5116942}, {"seq": 9, "name": "tests3G8509021490i-0009-78.webp", "offset": 5765057}, {"seq": 10, "name": "tests3G8509021490i-000a-78.webp", "offset": 6370298}, {"seq": 11, "name": "tests3G8509021490i-000b-78.webp", "offset": 6874371}, {"seq": 12, "name": "tests3G8509021490i-000c-78.webp", "offset": 7451398}, {"seq": 13, "name": "tests3G8509021490i-000d-78.webp", "offset": 8119769}, {"seq": 14, "name": "tests3G8509021490i-000e-78.webp", "offset": 8787044}, {"seq": 15, "name": "tests3G8509021490i-000f-78.webp", "offset": 9190341}, {"seq": 16, "name": "tests3G8509021490i-0010-78.webp", "offset": 9650624}, {"seq": 17, "name": "tests3G8509021490i-0011-78.webp", "offset": 10199647}, {"seq": 18, "name": "tests3G8509021490i-0012-78.webp", "offset": 10869976}], "combine_hn": 10, "combine_wn": 12, "nb_snapfiles": 19, "nb_snapshots": 2188}, "nb_streams": 3, "audio_codec": "aac", "video_codec": "hevc", "video_fps_1001": 23998, "audio_sample_rate": 48000}'
        
        insert_asset_query = f"""
        INSERT INTO public.t_asset
        (provider_id, asset_id, asset_user, media_code, "name", lang, predist_flag, source_url, status, create_time, update_time, metadata, tag, quality, heat)
        VALUES('nil', '{asset_id}', 'RV', '{asset_id}', '', 'en', 0, 'http://192.168.1.152:23816/record/724bddfd4a7e4cef90622199e559ef5d', 'avail', '{datetime.now()}', '{datetime.now()}', '{metadata_json}'::jsonb, '[]', '', 10);"""
        cursor.execute(insert_asset_query)

        # 插入数据到 public.t_file
        insert_file_queries = [
            f"INSERT INTO public.t_file (asset_id, file_id, file_type, file_size, store_uri, store_group, status, md5, origin, avg_bitrate, create_time, update_time, format, f_type, s3_master) VALUES ('{asset_id}', '{asset_id}_media', 'ts', 1530040444, 'group154/M00/03/9E/wKgBmmfKrEOAEZsXWzKQfHf-NI85914.ts', 'group154', 'avail', '1b9dd0048c26d4d4693bc8cfe08d0afd', 'ingest', '0', '{datetime.now()}', '{datetime.now()}', 'ts', 'media', '');",
            f"INSERT INTO public.t_file (asset_id, file_id, file_type, file_size, store_uri, store_group, status, md5, origin, avg_bitrate, create_time, update_time, format, f_type, s3_master) VALUES ('{asset_id}', '{asset_id}_idx', 'idxg', 26328, 'group154/M00/03/9F/wKgBmmfKrEOANe_yAABm2GW3Djw95.idxg', 'group154', 'avail', 'dc9388ad249a3a98bfa71845a4c840ce', 'ingest', '0', '{datetime.now()}', '{datetime.now()}', 'idxg', 'idx', '');",
            f"INSERT INTO public.t_file (asset_id, file_id, file_type, file_size, store_uri, store_group, status, md5, origin, avg_bitrate, create_time, update_time, format, f_type, s3_master) VALUES ('{asset_id}', '{asset_id}_snapshot', 'zip', 11033848, 'group154/M00/03/9F/wKgBmmfKrEOAG6ryAKhc-Pv5bIo929.zip', 'group154', 'avail', 'ab1be738e27e15f9ab493a211bf9f634', 'ingest', '0', '{datetime.now()}', '{datetime.now()}', 'zip', 'attachment', '');",
            f"INSERT INTO public.t_file (asset_id, file_id, file_type, file_size, store_uri, store_group, status, md5, origin, avg_bitrate, create_time, update_time, format, f_type, s3_master) VALUES ('{asset_id}', '{asset_id}_meta', 'torrent', 29703, 'group154/M00/03/9F/wKgBmmfKrEOAW4D7AAB0BzrSqm46521775', 'group154', 'avail', 'f6abdf8741f321e33b9bf2d6038d51e9', 'ingest', '0', '{datetime.now()}', '{datetime.now()}', 'torrent', 'meta', '');"
        ]

        # 执行插入操作
        for query in insert_file_queries:
            cursor.execute(query)

        # 提交事务并关闭连接
        conn.commit()
        cursor.close()
        conn.close()
        print(f"数据插入成功，assetId: {asset_id}")
    else:
        print(f"请求失败，状态码：{response.status_code}")
        print(f"响应内容：{response.text}")
        print(''' curl -X POST "http://mcmpserver.test-xxl.com/api/cms/tvod/notice" -H "Content-Type: application/json" -d '{"streamCode": "grid_channel2", "assetId": "2a3dc76683e74b39bb8dc477bc075478", "programName": "节目名称", "startTime": "1743412320", "endTime": "1743412680"}' ''')


# 每 2 小时执行一次
while True:
    send_request_and_insert_to_db()
    time.sleep(7200)  # 7200 秒 = 2 小时




#tests3G8509021490i














# test curl -X POST "http://mcmpserver.test-xxl.com/api/cms/tvod/notice" -H "Content-Type: application/json" -d '{"streamCode": "grid_channel2", "assetId": "2a3dc76683e74b39bb8dc477bc075478", "programName": "节目名称", "startTime": "1743412320", "endTime": "1743412680"}'
