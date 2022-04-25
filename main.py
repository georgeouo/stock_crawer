import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import requests
from bs4 import BeautifulSoup
import time
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *



help_txt = """
股市聊天機器人


目前支援的指令有：

1. 查詢  搜尋該股票當日的價格  例：查詢 2330
2. 教學  顯示教學  例：教學 
3. 新增  新增每日收集的股票代碼  例：新增 2330 
4. 刪除  刪除每日收集中的股票代碼  例：刪除 2330 
5. 每日蒐集股票代碼 傳出每日收集的股票代碼 例:每日蒐集股票代碼
"""

line_bot_api = LineBotApi("")

handler = WebhookHandler("")

user_id = ""



firebase_admin.initialize_app()
db = firestore.client()

def yahoo_stock_crawler(stock_id):
    doc = requests.get(f"https://tw.stock.yahoo.com/q/q?s={stock_id}")
    html = BeautifulSoup(doc.text, 'html.parser')
    table = html.findAll("table", {"border": 2})[0]
    data_row = table.select("tr")[1].select("td")

    return {
        "open": float(data_row[8].text),
        "high": float(data_row[9].text),
        "low": float(data_row[10].text),
        "close": float(data_row[2].text),
        "lastClose": float(data_row[7].text),
        "dailyReturn": float(data_row[2].text)/float(data_row[7].text)-1
    }
    
def dayfind(stock_number):
    doc = requests.get(f"https://tw.stock.yahoo.com/q/q?s={stock_number}")
    html = BeautifulSoup(doc.text, 'html.parser')
    tables = html.findAll("table" ,{"cellpadding": "1"})
    table = tables[0]
    td = table.findAll("td")
    day = td[1].text
    day=day.split(' ')
    return day[1]
    
def createReplyMessge(sid):
    doc = db.collection(f"{sid}_daily_data").document(f"{time.strftime('%Y%m%d')}").get()
    if doc.to_dict() == None:
        data =  yahoo_stock_crawler(sid)
    else:
        data = doc.to_dict()

    replyCheckMessage = ("查詢資料\n\n"
                         f"開盤價：{data['open']} 元\n"
                         f"最高價：{data['high']} 元\n"
                         f"最低價：{data['low']} 元\n"
                         f"收盤價：{data['close']} 元\n"
                         f"漲幅：{ round(data['dailyReturn'] * 100, 2) }\n")

    return replyCheckMessage

app = Flask(__name__)    

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    print(body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@app.route("/", methods=["GET"])
def loby():
    return render_template("loby.html")

@app.route("/index.html", methods=["GET"])                            
def greet():
    number = request.args.get("number")
    test = db.collection(f"{number}_daily_data").document(f"{time.strftime('%Y%m%d')}").get()
    if test.to_dict() == None:
        data = yahoo_stock_crawler(number)
        day = dayfind(number)
    else:
        data = test.to_dict()
        day = time.strftime('%Y/%m/%d')
    return render_template("index.html", number=number,data=data,day=day)                        
                         
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if "查詢" in event.message.text: 
        sid = event.message.text.split()[1]
        line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text=createReplyMessge(sid), type="text")
        )
        
    elif "help" in event.message.text or "教學" in event.message.text:
        line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text=help_txt, type="text")
        )
        
    elif "新增" in event.message.text:
        a = event.message.text.split()[1]
        test = db.collection("watch_list").document("stocks").get()
        test = test.to_dict()
        if a not in test["watch_list"]:
            test["watch_list"].append(a)
            db.collection("watch_list").document("stocks").set(test)
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="新增完成", type="text")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="已在每日蒐集中", type="text")
            )
            
    elif "刪除" in event.message.text:
        a = event.message.text.split()[1]
        test = db.collection("watch_list").document("stocks").get()
        test = test.to_dict()
        if a in test["watch_list"]:
            test["watch_list"].remove(a)
            db.collection("watch_list").document("stocks").set(test)
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="刪除成功", type="text")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="此代碼不在每日蒐集中喔!", type="text")
            )
            
    
    elif "增加每日通知" in event.message.text:
        a = event.message.text.split()[1]
        test = db.collection("spcial").document("id").get()
        test = test.to_dict()
        if a not in test["spcial_id"]:
            test["spcial_id"].append(a)
            db.collection("spcial").document("id").set(test)
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="新增完成", type="text")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="已在每日通知中", type="text")
            )
        
    elif "移除每日通知" in event.message.text:
        a = event.message.text.split()[1]
        test = db.collection("spcial").document("id").get()
        test = test.to_dict()
        if a in test["spcial_id"]:
            test["spcial_id"].remove(a)
            db.collection("spcial").document("id").set(test)
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="移除完成", type="text")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="此代碼不在每日通知中喔!", type="text")
            )
        
    elif "每日蒐集股票代碼" in event.message.text:
        test = db.collection("watch_list").document("stocks").get()
        test = test.to_dict()
        for i in test["watch_list"]:
            line_bot_api.push_message(user_id, TextSendMessage(text=i))
        
if __name__ == "__main__":
    app.run(debug=True)