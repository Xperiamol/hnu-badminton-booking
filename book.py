import json
from curl_cffi import requests as cffi_requests
import sys
import time
import re
import os
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def parse_time_ranges(input_str):
    if not input_str:
        return []
    ranges = []
    parts = input_str.split(';')
    for part in parts:
        if '-' not in part:
            raise ValueError(f"格式错误: '{part}' 缺少 '-'")
        start_str, end_str = part.split('-')
        try:
            start_hour = int(start_str.strip())
            end_hour = int(end_str.strip())
            if start_hour >= end_hour:
                raise ValueError(f"格式错误: {start_hour} 必须小于 {end_hour}")
            ranges.append((start_hour, end_hour))
        except ValueError:
            raise ValueError(f"格式错误: '{part}' 必须为数字, 例如 '9-11'")
    return ranges

def is_time_in_ranges(slot_time_string, ranges):
    if not ranges:
        return True
    if not slot_time_string:
        return False
    try:
        slot_start_hour_str = slot_time_string.split('-')[0].split(':')[0]
        slot_start_hour = int(slot_start_hour_str)
    except Exception:
        return False
    for start_range, end_range in ranges:
        if start_range <= slot_start_hour < end_range:
            return True
    return False

def try_book_slot(slot, session_headers, resource_id, target_date, retry_count=3):
    for attempt in range(retry_count):
        try:
            session = cffi_requests.Session()
            session.headers.update(session_headers)
            
            data_list_for_json = [
                {
                    "date": target_date,
                    "period": slot['period_id'],
                    "sub_resource_id": slot['sub_id']
                }
            ]

            payload_data = {
                "resource_id": resource_id,
                "code": "",
                "remarks": "",
                "deduct_num": "",
                "data": json.dumps(data_list_for_json)
            }
            
            response = session.post(
                BOOK_URL,
                data=payload_data,
                impersonate="chrome110",
                timeout=8
            )
            response.raise_for_status()
            
            result = response.json()
            return {
                'slot': slot,
                'success': result.get("e") == 0,
                'message': result.get('m', '未知响应'),
                'response': response.text,
                'attempts': attempt + 1
            }
            
        except Exception as e:
            if attempt < retry_count - 1:
                time.sleep(0.1 * (attempt + 1))
                continue
            else:
                return {
                    'slot': slot,
                    'success': False,
                    'message': f'请求异常(重试{retry_count}次): {str(e)}',
                    'response': None,
                    'attempts': retry_count
                }

def load_cookie():
    COOKIE_FILENAME = "cookie.txt"
    try:
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
        cookie_file_path = os.path.join(script_dir, COOKIE_FILENAME)

        if not os.path.exists(cookie_file_path):
            print(f"严重错误: 未找到 {cookie_file_path}")
            print(f"请先运行 get_cookie.py 脚本来生成 {COOKIE_FILENAME}。")
            sys.exit()

        with open(cookie_file_path, "r", encoding="utf-8") as f:
            cookie_string = f.read().strip()

        if not cookie_string:
            print(f"严重错误: {COOKIE_FILENAME} 文件为空。")
            print(f"请重新运行 get_cookie.py 脚本。")
            sys.exit()
        
        print(f"成功从 {cookie_file_path} 加载 Cookie。")
        return cookie_string
        
    except Exception as e:
        print(f"严重错误: 加载 {COOKIE_FILENAME} 时出错: {e}")
        sys.exit()

def load_config():
    CONFIG_FILENAME = "book_config.json"
    try:
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
        config_file_path = os.path.join(script_dir, CONFIG_FILENAME)
        
        if os.path.exists(config_file_path):
            with open(config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            print(f"加载配置文件: {config_file_path}")
            return config
        else:
            return {}
    except Exception as e:
        print(f"配置文件加载失败: {e}")
        return {}

def save_config(config):
    CONFIG_FILENAME = "book_config.json"
    try:
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
        config_file_path = os.path.join(script_dir, CONFIG_FILENAME)
        
        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"配置已保存: {config_file_path}")
    except Exception as e:
        print(f"配置保存失败: {e}")

STATUS_AVAILABLE = 1
VENUE_MAP = {
    "1": {"name": "南校区羽毛球馆", "id": 57},
    "2": {"name": "南校区综合馆（羽毛球）", "id": 85},
    "3": {"name": "财院校区羽毛球场", "id": 84},
}

QUERY_URL = "https://eportal.hnu.edu.cn/site/reservation/resource-info-margin"
BOOK_URL = "https://eportal.hnu.edu.cn/site/reservation/launch"

try:
    print("HNU羽毛球场自动预约脚本Designed by Xperiamol")
    
    loaded_cookie_string = load_cookie()
    saved_config = load_config()
    
    my_headers = {
        "Cookie": loaded_cookie_string,
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        "Referer": "https://eportal.hnu.edu.cn/v2/reserve/reserveDetail?id=84"
    }
    
    print("\n请选择您要监控的场馆：")
    for key, info in VENUE_MAP.items():
        print(f"  [{key}] {info['name']} (ID: {info['id']})")

    choice = ""
    default_choice = saved_config.get('venue_choice', '')
    while choice not in VENUE_MAP:
        prompt = f"请输入选项编号 (1, 2, or 3)"
        if default_choice and default_choice in VENUE_MAP:
            prompt += f"，默认[{default_choice}]"
        choice = input(f"{prompt}: ").strip()
        if not choice and default_choice:
            choice = default_choice
    
    selected_venue = VENUE_MAP[choice]
    SELECTED_RESOURCE_ID = selected_venue["id"]
    SELECTED_VENUE_NAME = selected_venue["name"]
    print(f"\n目标场馆: {SELECTED_VENUE_NAME} (ID: {SELECTED_RESOURCE_ID})")

    tomorrow = datetime.now().date() + timedelta(days=1)
    default_date_str = tomorrow.strftime('%Y-%m-%d')
    saved_date = saved_config.get('target_date', default_date_str)
    
    print(f"\n请输入监控日期 (格式 YYYY-MM-DD)")
    while True:
        prompt = f"默认为 [{saved_date}]"
        date_str = input(f"{prompt}: ").strip()
        
        if not date_str:
            TARGET_DATE = saved_date
            break
        
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            TARGET_DATE = date_str
            break
        except ValueError:
            print(f"格式错误: '{date_str}'. 请严格按照 YYYY-MM-DD 格式输入, 例如: {default_date_str}")
    
    print(f"目标日期: {TARGET_DATE}")

    print("\n请输入意向时间段 (例如 '9-11' 或 '9-11;18-20')")
    default_time_ranges = saved_config.get('time_ranges', '')
    prompt = f"留空按回车则预约 [任意时间]"
    if default_time_ranges:
        prompt += f"，默认[{default_time_ranges}]"
    time_ranges_str = input(f"{prompt}: ").strip()
    if not time_ranges_str and default_time_ranges:
        time_ranges_str = default_time_ranges
    
    parsed_time_ranges = parse_time_ranges(time_ranges_str)
    
    if not time_ranges_str:
        print("目标时段: [任意可用时间]")
    else:
        print(f"目标时段: {parsed_time_ranges}")
    
    print("\n请选择预约模式：")
    print("  [1] 顺序预约 (依次尝试，稳定但较慢)")
    print("  [2] 并发预约 (同时尝试多个，快速但可能重复预约)")
    
    default_booking_mode = saved_config.get('booking_mode', '1')
    booking_mode = ""
    while booking_mode not in ["1", "2"]:
        prompt = f"请输入选项编号 (1 or 2)"
        if default_booking_mode:
            prompt += f"，默认[{default_booking_mode}]"
        booking_mode = input(f"{prompt}: ").strip()
        if not booking_mode and default_booking_mode:
            booking_mode = default_booking_mode
            break
    
    use_concurrent = booking_mode == "2"
    mode_name = "并发预约" if use_concurrent else "顺序预约"
    print(f"预约模式: {mode_name}")
    print(f"监控频率: 固定0.5秒高频模式")
    
    current_config = {
        'venue_choice': choice,
        'target_date': TARGET_DATE,
        'time_ranges': time_ranges_str,
        'booking_mode': booking_mode
    }
    save_config(current_config)
        
    print("\n" + "="*40)

    session = cffi_requests.Session()
    session.headers.update(my_headers)
    session.headers.update({
        "Referer": f"https://eportal.hnu.edu.cn/v2/reserve/reserveDetail?id={SELECTED_RESOURCE_ID}"
    })
    
    print("正在预加热网络连接...")
    try:
        warmup_params = {
            "resource_id": SELECTED_RESOURCE_ID,
            "start_time": TARGET_DATE,
            "end_time": TARGET_DATE
        }
        warmup_response = session.get(QUERY_URL, params=warmup_params, impersonate="chrome110", timeout=5)
        print("网络连接预加热完成")
    except Exception as e:
        print(f"预加热失败，继续执行: {e}")

    query_params = {
        "resource_id": SELECTED_RESOURCE_ID,
        "start_time": TARGET_DATE,
        "end_time": TARGET_DATE
    }
    
    available_slots = []
    consecutive_empty_count = 0
    base_sleep_time = 0.5

    display_time_range = "任意时间" if not parsed_time_ranges else time_ranges_str
    print(f">>> 监控开始: 智能频率查询 {SELECTED_VENUE_NAME}，日期 {TARGET_DATE}...")
    print(f"    正在等待 {display_time_range} 内 'Status=1' 的时段... (按 Ctrl+C 停止)")

    while True:
        try:
            response_step1 = session.get(
                QUERY_URL,
                params=query_params,
                impersonate="chrome110"
            )
            response_step1.raise_for_status()
            available_times_json = response_step1.json()

            if available_times_json.get("e") != 0:
                print(f"\n查询失败: {available_times_json.get('m')}.")
                print(f"(这很可能是因为您的 Cookie 已过期, 请重新运行 get_cookie.py 脚本)")
                time.sleep(5)
                continue

            if not available_times_json.get("d"):
                print(f"\n解析错误: 响应中没有 'd' 字段。5秒后重试...")
                time.sleep(5)
                continue

            list_key = list(available_times_json["d"].keys())[0]
            slots_list = available_times_json["d"][list_key]

            available_slots.clear()
            for slot in slots_list:
                if (slot.get("row") and
                    slot.get("row").get("status") == STATUS_AVAILABLE and
                    is_time_in_ranges(slot.get("yaxis"), parsed_time_ranges)):
                    
                    slot_info = {
                        "period_id": slot.get("time_id"),
                        "sub_id": slot.get("sub_id"),
                        "court": slot.get("abscissa"),
                        "time": slot.get("yaxis")
                    }
                    available_slots.append(slot_info)

            if available_slots:
                available_slots.sort(key=lambda x: x['time'])
                
                print(f"\n--- 发现 {len(available_slots)} 个可用场地! (符合时段: {display_time_range}) ---")
                for i, slot in enumerate(available_slots, 1):
                    print(f"   [{i}] 场地: {slot['court']} | 时间: {slot['time']} | ID: {slot['sub_id']}")
                print(f"-------------------------------------------")
                break
            else:
                consecutive_empty_count += 1
                current_sleep = base_sleep_time
                
                print(f"    [{time.strftime('%H:%M:%S')}] 未发现 {display_time_range} 内的可用时段... 正在刷新... (频率: {current_sleep:.1f}s)")
                sys.stdout.flush()
                try:
                    time.sleep(current_sleep)
                except KeyboardInterrupt:
                    print("\n\n用户手动停止了监控。")
                    sys.exit()

        except KeyboardInterrupt:
            print("\n\n用户手动停止了监控。")
            sys.exit()
        except cffi_requests.exceptions.HTTPError as he:
            print(f"\nHTTP 错误: {he.response.status_code}. 0.5秒后重试...")
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n\n用户手动停止了监控。")
                sys.exit()
        except cffi_requests.exceptions.RequestException as re:
            print(f"\n网络连接错误: {re}. 0.5秒后重试...")
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n\n用户手动停止了监控。")
                sys.exit()
    
    if use_concurrent and len(available_slots) > 1:
        print(f">>> 步骤二: 并发模式 - 同时尝试预约所有 {len(available_slots)} 个时段...")
        print("    注意：并发模式可能导致多个预约成功，请谨慎使用")
        
        max_concurrent = min(len(available_slots), 5)
        
        success_results = []
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            future_to_slot = {
                executor.submit(try_book_slot, slot, my_headers, SELECTED_RESOURCE_ID, TARGET_DATE): slot
                for slot in available_slots
            }
            
            for future in as_completed(future_to_slot):
                result = future.result()
                slot = result['slot']
                
                if result['success']:
                    print(f"\n成功预约: {slot['court']} @ {slot['time']}！")
                    success_results.append(result)
                else:
                    print(f"\n预约失败: {slot['court']} @ {slot['time']} - {result['message']}")
        
        if success_results:
            print(f"\n并发预约完成！成功预约了 {len(success_results)} 个时段：")
            for result in success_results:
                slot = result['slot']
                attempts = result.get('attempts', 1)
                print(f"成功 {slot['court']} @ {slot['time']} (重试{attempts}次)")
            
            total_attempts = sum(result.get('attempts', 1) for result in success_results)
            avg_attempts = total_attempts / len(success_results)
            print(f"平均重试次数: {avg_attempts:.1f}")
        else:
            print(f"\n很遗憾，所有时段都预约失败了。")
    
    else:
        print(f">>> 步骤二: 顺序模式 - 依次尝试预约所有可用时段...")
        
        success = False
        for i, slot in enumerate(available_slots, 1):
            if success:
                break
                
            print(f"\n[{i}/{len(available_slots)}] 正在尝试预约: {slot['court']} @ {slot['time']} (ID: {slot['sub_id']})...")
            
            data_list_for_json = [
                {
                    "date": TARGET_DATE,
                    "period": slot['period_id'],
                    "sub_resource_id": slot['sub_id']
                }
            ]

            payload_data = {
                "resource_id": SELECTED_RESOURCE_ID,
                "code": "",
                "remarks": "",
                "deduct_num": "",
                "data": json.dumps(data_list_for_json)
            }
            
            try:
                response_step2 = session.post(
                    BOOK_URL,
                    data=payload_data,
                    impersonate="chrome110"
                )
                response_step2.raise_for_status()
                
                print(f"服务器状态码: {response_step2.status_code}")
                
                try:
                    final_response_json = response_step2.json()
                    print(f"服务器响应: {response_step2.text}")

                    if final_response_json.get("e") == 0:
                        print(f"\n恭喜！成功预约 {slot['court']} @ {slot['time']}！")
                        success = True
                        break
                    else:
                        error_msg = final_response_json.get('m', '未知错误')
                        print(f"预约失败: {error_msg}")
                        
                        if i < len(available_slots):
                            print(f"尝试下一个可用时段...")
                        else:
                            print(f"\n所有可用时段都预约失败了！")
                            
                except json.JSONDecodeError:
                    print(f"    无法解析响应为JSON: {response_step2.text}")
                    if i < len(available_slots):
                        print(f"    尝试下一个可用时段...")
                        
            except KeyboardInterrupt:
                print("\n\n用户手动停止了预约。")
                sys.exit()
            except cffi_requests.exceptions.RequestException as e:
                print(f"    网络请求错误: {e}")
                if i < len(available_slots):
                    print(f"    尝试下一个可用时段...")
        
        if not success:
            print(f"\n 很遗憾，所有 {len(available_slots)} 个可用时段都预约失败了。")
            print("    建议稍后重新运行脚本再次尝试。")

except KeyboardInterrupt:
    print("\n\n用户手动停止了监控。")
    sys.exit()
except ValueError as ve:
    print(f"\n输入错误: {ve}")
    sys.exit()
except Exception as e:
    print(f"发生未知错误: {type(e).__name__} - {e}")