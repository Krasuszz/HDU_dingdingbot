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
    url = 'https://api.nasa.gov/planetary/apod?api_key=vsK3ocVYEWb768DrpD4cvGuoLgQumolhM3IcUNJz'
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
            send_markdown_msg('Insufficient User Permissions', '<font color=\"#ff8000\"> Insufficient User Permissions </font> \n> contact administrator for assistance', webhook_url)
            return 0
        user_id = np.where(user_names == senderNick)[0][0]
        user_permission = int(user_permissions[user_id])
        if user_permission < 1:
            insufficient_permission(senderNick, webhook_url)
            return 0

        len_qa = int(qa_index[-1])  # 从index 1 开始算
        if text_info[0:4] == 'help':
            print('\033[1;35m [command] \033[0m Show Help:', senderNick)
            send_text_msg('/help\n/list\n/add [question] [answer]\n/del [index]\n/user [user] [level]', webhook_url)
        elif text_info[0:4] == 'list':
            print('\033[1;35m [command] \033[0m Show List:', senderNick)
            send_text_msg(show_QA(), webhook_url)

        elif text_info[0:4] == 'add ':
            if user_permission < 2:
                insufficient_permission(senderNick, webhook_url)
                return 0
            text_info = text_info[4:].split(' ')
            if len(text_info) == 2:
                add_QA(text_info[0], text_info[1], senderNick, webhook_url)
                save_qa()
            else:
                format_error(senderNick, webhook_url)

        elif text_info[0:4] == 'del ':
            if user_permission < 2:
                insufficient_permission(senderNick, webhook_url)
                return 0
            text_info = text_info[4:]

            if text_info.isdigit():
                del_index = int(text_info)
                if del_index > len_qa or del_index < 1:
                    index_out(senderNick, webhook_url)
                else:
                    del_QA(del_index, senderNick, webhook_url)
                    save_qa()
            else:
                format_error(senderNick, webhook_url)

        elif text_info[0:5] == 'user ':
            if user_permission < 2:
                insufficient_permission(senderNick, webhook_url)
                return 0
            text_info = text_info[5:].split(' ')
            if len(text_info) == 2:
                if text_info[1].isdigit():
                    if int(text_info[1]) > 2 or int(text_info[1]) < 0:
                        index_out(senderNick, webhook_url)
                    else:
                        change_user_permission(text_info[0], text_info[1], senderNick, webhook_url)
                        save_user()
                else:
                    format_error(senderNick, webhook_url)
            else:
                format_error(senderNick, webhook_url)
        else:
            format_error(senderNick, webhook_url)
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

# 用户权限不足
def insufficient_permission(senderNick,webhook_url):
    print('\033[1;35m [command] \033[0m User Not Registered:', senderNick)
    send_markdown_msg('Insufficient User Permissions',
                      '<font color=\"#ff8000\"> Insufficient User Permissions </font> \n> contact administrator for assistance',
                      webhook_url)
# 指令格式错误
def format_error(senderNick, webhook_url):
    print('\033[1;35m [command] \033[0m Format Error:', senderNick)
    send_markdown_msg('Format Error',
                      '<font color=\"#ff8000\"> Format Error </font> \n> send /help for more help',
                      webhook_url)
# 下标越界
def index_out(senderNick, webhook_url):
    print('\033[1;35m [command] \033[0m Index Out of Range:', senderNick)
    send_markdown_msg('Index Out of Range',
                      '<font color=\"#ff8000\"> Index Out of Range </font> \n> check the index and try again',
                      webhook_url)


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

# 新增QA
def add_QA(question, answer, senderNick, webhook_url):
    global qa_index, qa_questions, qa_answers
    qa_index = np.append(qa_index, str(int(qa_index[-1])+1))
    qa_questions = np.append(qa_questions, question)
    qa_answers = np.append(qa_answers, answer)
    print('\033[1;35m [command] \033[0m New QA Added:', senderNick)
    send_markdown_msg('QA Successfully Added',
                      '<font color=\"#4ce572\"> QA Successfully Added </font> \n> send /list to check the new list',
                      webhook_url)
# 删除指定QA
def del_QA(del_index, senderNick, webhook_url):
    global qa_index, qa_questions, qa_answers
    m = 0
    while qa_index[m] == '0':
        m += 1
    qa_index = np.delete(qa_index, del_index+m-1)
    qa_questions = np.delete(qa_questions, del_index+m-1)
    qa_answers = np.delete(qa_answers, del_index+m-1)
    n = 1
    for i in range(m, len(qa_index)):
        qa_index[i] = str(n)
        n += 1
    print('\033[1;35m [command] \033[0m QA Deleted:', str(del_index), senderNick)
    send_markdown_msg('QA Successfully Deleted',
                      '<font color=\"#4ce572\"> QA Successfully Deleted </font> \n> send /list to check the new list',
                      webhook_url)

# 显示预设问答列表
def show_QA():
    n = len(qa_questions)
    msg = ''
    m = 0
    while qa_index[m] == '0':
        m += 1
    for i in range(m, n):
        msg += qa_index[i]+'\n'+qa_questions[i]+'\n'+qa_answers[i]+'\n\n'
    return msg

# 改变用户权限
def change_user_permission(user, permission, senderNick, webhook_url):
    global user_index, user_names, user_permissions
    if user not in user_names:
        user_index = np.append(user_index, str(int(user_index[-1])+1))
        user_names = np.append(user_names, user)
        user_permissions = np.append(user_permissions, permission)
    else:
        if permission == '2':
            insufficient_permission(senderNick, webhook_url)
            return 0
        else:
            user_permissions[user_names == user] = permission
    print('\033[1;35m [command] \033[0m User Permission Changed:', user, permission, senderNick)
    send_markdown_msg('User Permission Successfully Changed',
                      '<font color=\"#4ce572\"> User Permission Successfully Changed </font> \n> '+user+' '+permission,
                      webhook_url)


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
    np.savetxt(QAfile, np.array([qa_index, qa_questions, qa_answers]).T, delimiter=",", header='序号,问,答', comments="", encoding='utf-8', fmt='%s')

def read_user():
    global user_index, user_names, user_permissions
    with open(Userfile) as user:
        read_csv = np.array(list(csv.reader(user)))
        user_index = read_csv[1:, 0]
        user_names = read_csv[1:, 1]
        user_permissions = read_csv[1:, 2]

def save_user():
    print('\033[1;35m [action] \033[0m Userfile saved')
    np.savetxt(Userfile, np.array([user_index, user_names, user_permissions]).T, delimiter=",", header='序号,用户名,权限等级', comments="", encoding='utf-8', fmt='%s')

if __name__ == '__main__':
    print('start')
    QAfile = 'QA.csv'
    Userfile = 'User.csv'
    read_user()
    read_qa()
    app.run(host='0.0.0.0', port=8000)
