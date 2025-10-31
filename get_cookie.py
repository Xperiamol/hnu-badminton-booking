import time
import json
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 配置
LOGIN_PAGE_URL = "https://cas.hnu.edu.cn/cas/login?service=https%3A%2F%2Feportal.hnu.edu.cn%2Fsite%2Flogin%2Fcas-login%3Fredirect_url%3Dhttps%253A%252F%252Feportal.hnu.edu.cn%252Fv2%252Freserve%252FreserveDetail%253Fid%253D57"
COOKIE_FILENAME = "cookie.txt"

def get_cookies_via_manual_login():
    """半自动登录函数"""
    print("\n--- 正在启动 Chrome 浏览器 (Selenium) ---")
    
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1000,800")
    
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"正在浏览器中打开: {LOGIN_PAGE_URL}")
        driver.get(LOGIN_PAGE_URL)
        
        print("\n" + "="*50)
        print(">>> 浏览器已打开。请您在浏览器窗口中...")
        print(">>> 1. 手动输入学号")
        print(">>> 2. 手动输入密码")
        print(">>> 3. 手动点击 '登录' 按钮")
        print("\n>>> 脚本正在等待您登录成功...")
        print("    (您有 120 秒的时间)")
        print("="*50)
        
        try:
            WebDriverWait(driver, 120).until_not(
                EC.url_contains("cas/login")
            )
        except Exception:
            print("\n!!! 操作超时 (120秒)。")
            print("    您是否未能在规定时间内完成登录, 或者登录失败 (密码错误)？")
            return None
        
        print(f"\n登录成功！已检测到页面跳转。")
        print(f"    最终跳转 URL: {driver.current_url}")
        
        print("\n--- 正在提取 Cookie ---")
        cookies = driver.get_cookies()
        
        return cookies
        
    except Exception as e:
        print(f"!!! 登录过程中发生严重错误: {e}")
        return None
    finally:
        print("Cookie 抓取完成, 正在关闭浏览器...")
        time.sleep(2)
        driver.quit()

# 主程序
print(f"--- 自动 Cookie 抓取工具 (v4.3) ---")
print(f"    (脚本将打开浏览器, 请您手动登录)")
print(f"    (成功后, Cookie 将保存到 {COOKIE_FILENAME})")

try:
    extracted_cookies = get_cookies_via_manual_login()
    
    if extracted_cookies:
        cookie_string = ""
        for cookie in extracted_cookies:
            cookie_string += f"{cookie['name']}={cookie['value']}; "
        
        # 确定保存路径
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 .exe
            script_dir = os.path.dirname(sys.executable)
        else:
            # 如果是 .py 脚本
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
        cookie_file_path = os.path.join(script_dir, COOKIE_FILENAME)
        
        try:
            with open(cookie_file_path, "w", encoding="utf-8") as f:
                f.write(cookie_string)
            
            print("\n" + "="*50)
            print(f"成功将 Cookie 保存到: {cookie_file_path}")
            print("="*50)
            
        except Exception as e:
            print(f"\n!!! 严重错误: 无法将 Cookie 写入 {cookie_file_path}")
            print(f"    错误详情: {e}")
            
    else:
        print("\n!!! 自动抓取失败。请检查上面的错误日志。")

except KeyboardInterrupt: 
    print("\n\n!!! 用户手动停止了脚本。")
    sys.exit()
except Exception as e:
    print(f"!!! 发生未知错误: {type(e).__name__} - {e}")
