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

'''
字体颜色：
print("\033[1;30m 字体颜色：白色\033[0m") # normal
print("\033[1;31m 字体颜色：红色\033[0m") # error
print("\033[1;32m 字体颜色：深黄色\033[0m") # warning
print("\033[1;33m 字体颜色：浅黄色\033[0m")
print("\033[1;34m 字体颜色：蓝色\033[0m") # send
print("\033[1;35m 字体颜色：淡紫色\033[0m") # action
print("\033[1;36m 字体颜色：青色\033[0m") # receive
print("\033[1;37m 字体颜色：灰色\033[0m")
print("\033[1;38m 字体颜色：浅灰色\033[0m")
'''

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
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
    response = requests.get(url + name)
    result = json.loads(response.content.decode())
    # print(result)
    return result


def getNASA():
    url = 'https://api.nasa.gov/planetary/apod?api_key=qT9H2ZeQSmv5P3NYigbigEmFtFJE2Wp6Or6RKfuZ'
    response = requests.get(url)
    result = json.loads(response.content.decode())
    return result


def findAnswer(text):
    max_score = 0
    max_index = 0
    for i in range(len(qa_questions)):
        score = fuzz.ratio(text, qa_questions[i])
        if score > max_score:
            max_score = score
            max_index = i
    return qa_answers[max_index]


date = ''
result = []
def weather(city):
    global date
    global result
    if strftime("%d") != date:
        date = strftime("%d")
        result = getWeather(city)
    today = result['data'][0]
    tomor = result['data'][1]
    ans = '今日天气' + today['narrative'] + '湿度' + today['humidity'] + '，空气质量' + today['air_level'] + '\n'
    ans += '明日天气' + tomor['narrative'] + '湿度' + tomor['humidity'] + '，空气质量' + tomor['air_level'] + '\n'
    return ans.replace(' ', '')

# 显示预设问答列表
def show_QA():
    n = len(qa_questions)
    msg = ''
    for i in range(n):
        msg += qa_index[i]+'\n'+qa_questions[i]+'\n'+qa_answers[i]+'\n\n'
    return msg

def handle_info(req_data):
    # 声明mod是全局变量
    global mod
    # 解析用户发送消息 通讯webhook_url 用户名称
    text_info = req_data['text']['content'].strip()
    webhook_url = req_data['sessionWebhook']
    senderNick = req_data['senderNick']
    # 记录发送人与发送的消息
    print('\033[1;36m [sender_nick] \033[0m', senderNick)
    print('\033[1;36m [text_info] \033[0m', text_info)

    # 判断是否是命令
    if text_info[0] == '/':
        text_info = text_info[1:]
        if not(senderNick in user_names):
            print('\033[1;35m [command] \033[0m User Not Registered:', senderNick)
            send_markdown_msg('<font color=\"#ff8000\"> Insufficient User Permissions </font>', 'contact administrator for assistance', webhook_url)
            return 0
        user_id = np.where(user_names == senderNick)[0][0]
        if int(user_permissions[user_id]) < permission_limit:
            print('\033[1;35m [command] \033[0m Insufficient User Permissions:', senderNick)
            send_markdown_msg('<font color=\"#ff8000\"> Insufficient User Permissions </font>', 'contact administrator for assistance', webhook_url)
            return 0
        if text_info[0:4] == 'help':
            print('\033[1;35m [command] \033[0m Show Help:', senderNick)
            send_text_msg('/help\n/list\n/add [Q] [A]\n/del [i]\n', webhook_url)
        elif text_info[0:4] == 'list':
            print('\033[1;35m [command] \033[0m Show List:', senderNick)
            send_text_msg(show_QA(), webhook_url)
        elif text_info[0:4] == 'add ':
            text_info = text_info[4:].split(' ')
            send_markdown_msg('<font color=\"#ff8000\"> Function Not Deployed </font>', '', webhook_url)
            '''
            if len(text_info) == 2:
                send_text_msg('', webhook_url)
            else:
                send_markdown_msg('<font color=\"#ff8000\"> Format Error </font>', 'send \help for more help', webhook_url)
            '''
        elif text_info[0:4] == 'del ':
            text_info = text_info[4:]
            send_markdown_msg('<font color=\"#ff8000\"> Function Not Deployed </font>', '', webhook_url)
            '''
            if text_info.isdigit():
                del_index = int(text_info)
                if del_index < len(qa_questions):
                
                send_text_msg('', webhook_url)
            else:
                send_markdown_msg('<font color=\"#ff8000\"> Format Error </font>', 'send \help for more help', webhook_url)
            '''
        else:
            send_markdown_msg('<font color=\"#ff8000\"> Format Error </font>', 'send \help for more help', webhook_url)
        return 0

    # 模糊匹配回答，判别回答种类
    answer_msg = findAnswer(text_info.strip('请问'))
    if 'call' in answer_msg:
        if answer_msg == 'call_hellow':
            print('\033[1;34m [responses] \033[0m |text|', send_text_msg("你好", webhook_url))
        elif answer_msg == 'call_time':
            print('\033[1;34m [responses] \033[0m |text|', send_text_msg("现在是" + strftime("%Y年%m月%d日 %H:%M:%S"), webhook_url))
        elif answer_msg == 'call_weather':
            print('\033[1;34m [responses] \033[0m |text|', send_text_msg(weather('杭州'), webhook_url))
        elif answer_msg == 'call_morning':
            nasamsg = getNASA()
            print('\033[1;34m [responses] \033[0m |md|', send_markdown_msg("早上好！", "## " + nasamsg['title'] + " \n> ![pic](" + nasamsg['url'] + ") \n>", webhook_url))
    else:
        answermsg = findAnswer(text_info.strip('请问'))
        print('\033[1;34m [responses] \033[0m |text|', send_text_msg(answermsg, webhook_url))
    return 0

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
    return req.text


def send_markdown_msg(title, message, webhook_url):
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": message
        }
    }
    req = requests.post(webhook_url, json=data)
    return req.text


# 模糊查找答案
def findAnswer(text):
    max_score = 0
    max_index = 0
    for i in range(len(qa_questions)):
        score = fuzz.ratio(text, qa_questions[i])
        if score > max_score:
            max_score = score
            max_index = i
    return qa_answers[max_index]

def read_qa():
    global qa_index, qa_questions, qa_answers
    with open(QAfile) as qa:
        read_csv = np.array(list(csv.reader(qa)))
        qa_index = read_csv[1:, 0]
        qa_questions = read_csv[1:, 1]
        qa_answers = read_csv[1:, 2]

def save_qa():
    print('\033[1;35m [action] \033[0m QAfile saved')
    np.savetxt(QAfile, qa_index, delimiter=",", header='序号,问,答', comments="")

def read_user():
    global user_names, user_permissions
    with open(Userfile) as user:
        read_csv = np.array(list(csv.reader(user)))
        user_names = read_csv[1:, 1]
        user_permissions = read_csv[1:, 2]
    
if __name__ == '__main__':
    print('start')
    QAfile = 'QA.csv'
    Userfile = 'User.csv'
    read_user()
    read_qa()
    permission_limit = 1
    app.run(host='0.0.0.0', port=8000)
