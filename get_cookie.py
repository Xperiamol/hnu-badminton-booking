import sys
import os
import re

def get_cookie():
    print("=" * 60)
    print("湖南大学体育场馆预约系统 - Cookie获取工具")
    print("=" * 60)
    print()
    print("请按照以下步骤获取Cookie：")
    print()
    print("1. 打开浏览器，访问:")
    print("   https://eportal.hnu.edu.cn/")
    print()
    print("2. 登录您的学号和密码")
    print()
    print("3. 进入体育场馆预约页面:")
    print("   https://eportal.hnu.edu.cn/v2/reserve")
    print()
    print("4. 按F12打开开发者工具")
    print()
    print("5. 点击 Network(网络) 标签")
    print()
    print("6. 刷新页面(F5)")
    print()
    print("7. 在网络请求中找到任意一个请求")
    print()
    print("8. 右键点击 -> Copy -> Copy as cURL")
    print()
    print("9. 或者直接复制请求头中的Cookie值")
    print()
    print("-" * 60)
    
    cookie_input = input("请粘贴完整的Cookie字符串 (或cURL命令): ").strip()
    
    if not cookie_input:
        print("错误: Cookie不能为空!")
        return
    
    if cookie_input.startswith('curl'):
        cookie_match = re.search(r"-H ['\"]Cookie: ([^'\"]+)['\"]", cookie_input)
        if cookie_match:
            cookie_string = cookie_match.group(1)
        else:
            print("错误: 无法从cURL命令中提取Cookie!")
            return
    else:
        cookie_string = cookie_input
    
    cookie_string = cookie_string.strip()
    if cookie_string.startswith('Cookie: '):
        cookie_string = cookie_string[8:]
    
    try:
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        
        cookie_file = os.path.join(script_dir, "cookie.txt")
        
        with open(cookie_file, "w", encoding="utf-8") as f:
            f.write(cookie_string)
        
        print(f"\nCookie已成功保存到: {cookie_file}")
        print("\n现在您可以运行主预约脚本了!")
        
    except Exception as e:
        print(f"\n保存Cookie时出错: {e}")

if __name__ == "__main__":
    try:
        get_cookie()
        input("\n按回车键退出...")
    except KeyboardInterrupt:
        print("\n\n用户取消操作。")
    except Exception as e:
        print(f"\n发生错误: {e}")
        input("\n按回车键退出...")