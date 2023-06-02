from cgitb import text
import re
import base64
import hashlib
import requests
import json
import hmac
import csv
import numpy as np
from fuzzywuzzy import fuzz
from flask import request
from flask import Flask
from time import strftime

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def get_data():
    # 第一步验证：是否是post请求
    if request.method == "POST":
        # 签名验证 获取headers中的Timestamp和Sign
        timestamp = request.headers.get('Timestamp')
        sign = request.headers.get('Sign')
        # 第二步验证：签名是否有效
        if check_sig(timestamp) == sign:
            text_info = json.loads(str(request.data, 'utf-8'))
            handle_info(text_info)
            print(text_info)
        else:
            print('11')
    else:
        print('22')
    # get_data()必须要有返回
    return request.method

# 钉钉sign计算
def check_sig(timestamp):
    app_secret = 'cdPUYXVo8kFfPfv3PChRQ6QeErv22NH5OV46YQGwuSIxW2WzKOiuk4bX35KbxLCM'
    app_secret_enc = app_secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, app_secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(app_secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = base64.b64encode(hmac_code).decode('utf-8')
    return sign


# mod用于记录当前对话模式
mod = 0

def getWeather(name):
    url = 'https://v0.yiketianqi.com/api?unescape=1&version=v91&appid=33736357&appsecret=m1HmYfTB&ext=&cityid=&city='
    response = requests.get(url+name)
    result = json.loads(response.content.decode())
    #print(result)
    return result

def getNASA():
    url = 'https://api.nasa.gov/planetary/apod?api_key=qT9H2ZeQSmv5P3NYigbigEmFtFJE2Wp6Or6RKfuZ'
    response = requests.get(url)
    result = json.loads(response.content.decode())
    return result

def findAnswer(text):

    max_score = 0
    max_index = 0
    for i in range(len(questions)):
        score = fuzz.ratio(text, questions[i])
        if score > max_score:
            max_score = score
            max_index = i
    return answers[max_index]


date = ''
result = []
def weather(city):
    global date
    global result
    if strftime("%d")!=date:
        date = strftime("%d")
        result = getWeather(city)
    today = result['data'][0]
    tomor = result['data'][1]
    ans = '今日天气' + today['narrative'] + '湿度' + today['humidity'] + '，空气质量' + today['air_level'] + '\n'
    ans += '明日天气' + tomor['narrative'] + '湿度' + tomor['humidity'] + '，空气质量' + tomor['air_level'] + '\n'
    return ans.replace(' ', '')

def handle_info(req_data):
    # 声明mod是全局变量
    global mod
    # 解析用户发送消息 通讯webhook_url 用户名称
    text_info = req_data['text']['content'].strip()
    webhook_url = req_data['sessionWebhook']
    senderNick = req_data['senderNick'] + ' :{}'.format(text_info)
    # 记录发送人与发送的消息
    print('\033[1;36m [sender_nick] \033[0m',senderNick)
    print('\033[1;36m [text_info] \033[0m',text_info)

    answer_msg = findAnswer(text_info.strip('请问'))

    # if判断用户消息触发的关键词，然后返回对应内容
    if 'call' in answer_msg:
        if answer_msg=='call_hellow':
            print('\033[1;34m [responses] \033[0m',send_text_msg("你好",webhook_url))
        elif answer_msg=='call_time':
            print('\033[1;34m [responses] \033[0m',send_text_msg("现在是"+strftime("%Y年%m月%d日 %H:%M:%S"), webhook_url))
        elif answer_msg=='call_weather':
            print('\033[1;34m [responses] \033[0m',send_text_msg(weather('杭州'), webhook_url))
        elif answer_msg=='call_morning':
            nasamsg = getNASA()
            print('\033[1;34m [responses] \033[0m',send_markdown_msg("早上好！", "## "+nasamsg['title']+" \n> ![pic]("+nasamsg['url']+") \n>", webhook_url))
    else:
        answermsg = findAnswer(text_info.strip('请问'))
        print('\033[1;34m [responses] \033[0m',send_text_msg(answermsg, webhook_url))
    
    

        

# 钉钉消息推送
def send_text_msg(message, webhook_url):
    data = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }
    # 利用requests发送post请求
    req = requests.post(webhook_url, json=data)
    return req
def send_markdown_msg(title, message, webhook_url):
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": message
        }
    }
    req = requests.post(webhook_url, json=data)
    return req

# 模糊查找答案
def findAnswer(text):
    max_score = 0
    max_index = 0
    for i in range(len(questions)):
        score = fuzz.ratio(text, questions[i])
        if score > max_score:
            max_score = score
            max_index = i
    return answers[max_index]

if __name__ == '__main__':
    print('start')
    filename='谈心谈话系统对接QA.csv'
    with open(filename) as f:
        read_csv = np.array(list(csv.reader(f)))
        questions = read_csv[1:, 1]
        answers = read_csv[1:, 2]
    app.run(host='0.0.0.0', port=8000)