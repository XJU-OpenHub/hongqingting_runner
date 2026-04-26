import gzip
import hashlib
import json
import random
import re
import time

import requests

# 存储多个设备标识符，用于模拟不同设备
uid_list = ['352746021020302352746021020302b49dccd2e6ba44a38afe24122e81f6761683709579$b09ba8a94241a377a6047ee1d45e879d',
            '6535120246660563535120246660562d80bb4741374315b44a0ad50ee005731679203060$59a091bd0851f40d38b55b0d1713fe47',
            '472d781c51894a8911489c115616518931d56351651b61861a61as961894618769198640$59a091b4v68162aa48f55b0d1713fe47',
            '69fedf13faaddfe49896b487dbb984897a984cb94c4fcf8014d83aa62bad6341f7167912$8489a4b49b8dc69ba59bd3ca577b64d6',
            'f5efdf13faaddfe59181548dfbb984897a984cb94c4fcf8014d83aa62bad634s1b156d1g65fa516ab5b8dc69ba59bd3ca577b64d6']

# HTTP请求头信息
headers = {
    # 'Charset': 'UTF-8',
    'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 10; LIO-AN00 Build/PQ3B.190801.002)',
    # 'Host': 'quantiwang.cn:8012',
    # 'Accept-Encoding': 'gzip',
    # 'Content-Length': '',
    # 'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
    'Content-Type': 'application/x-www-form-urlencoded',
    # 'Connection': 'keep-alive',
    # 'Accept': '*/*',
    # 'User-Agent': '%E9%A3%9E%E7%BF%94%E7%9A%84%E7%BA%A2%E8%9C%BB%E8%9C%93/20221212 CFNetwork/1402.0.8 Darwin/22.2.0',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',

}

# 获取学生信息
def GetStuInfo():
    # 20221302002 13.258km
    print("输入学号(密码默认Stu+学号)")
    no = input()
    # no = '20221303205'
    password = 'Stu' + no
    hl = hashlib.md5()
    hl.update(password.encode(encoding='utf-8'))
    md5_password = hl.hexdigest()
    url = 'http://quantiwang.cn:8012/cloud/DflyServer'
    data = "name=%5B%27bangding%27%2C%2710755%27%2C%27student%27%2C%27" + no + "%27%2C%27" + md5_password + "%27%5D"
    headers['Content-Length'] = str(len(data))
    headers['User-Agent'] = 'Dalvik/2.1.0 (Linux; U; Android 12; LIO-AN00 Build/PQ3B.190801.002)'

    resp = requests.post(url=url, headers=headers, data=data)
    print(resp.text)
    return no

# 查询跑步数据
def GetRunMeter(no):
    # data = "{'studentno':'20221303219','uid':'','schoolno':'10755'}"
    data = "{'studentno':" + no + ",'uid':'d69fedf13faaddfed69fedf13faaddfeb9d0c4fcf8014d83aa62bad7076341f71679132300$811092b17532ad13b7aae68f6c69bd3c','schoolno':'10755'}"
    url = 'http://218.195.237.156:8029/DragonFlyServ/Api/webserver/getRunDataSummary'
    gzip_data = gzip.compress(bytes(data, 'utf-8'))
    gzip_length = str(len(gzip_data))
    headers['Host'] = '218.195.237.156:8029'
    headers['User-Agent'] = 'Dalvik/2.1.0 (Linux; U; Android 12; LIO-AN00 Build/PQ3B.190801.002)'
    headers['Content-Length'] = gzip_length
    # print(data)
    resp = requests.post(url=url, headers=headers, data=gzip_data)
    data_dict = json.loads(resp.text)
    time_strmp = time.localtime(data_dict['lasttime'])
    time_ymd = time.strftime("%Y/%m/%d %H:%M:%S", time_strmp)
    print(f"跑步里程:{data_dict['m']},查询时间:{time_ymd}")

# 上传跑步数据函数
# no学号, day距现在几天前, 随机uid序号
def PostRunData_12km(no, day, uid):
    headers['User-Agent'] = 'okhttp/5.0.0-alpha.10'
    # location格式:'纬度';'经度';时间戳;null;null;相较于上一次移动的位移,默认0.02;null@
    if (day != 0):
        begintime = int(time.time() - ((86400) * day) + random.randint(1, 3600))  # 现在减day天
        endtime = begintime + 5800 + random.randint(1, 600)
    else:
        endtime = int(time.time() - random.randint(1, 3600))
        begintime = endtime - 5800 - random.randint(1, 600)

    distance = 12000.0 + random.uniform(1.0, 500.0)
    runtime = begintime
    usetime = endtime - begintime - random.randint(1, 10)
    speed = (usetime / 60) / (distance / 1000)

    # 读取轨迹
    f = open(file=f'./location_12km', mode='r', encoding='utf-8')
    text = f.read()

    text_find = re.findall(r'.*?@', text)
    delta_time = usetime / len(text_find)
    loc_r = ""  # 替换时间位置
    for item in text_find:
        loc = re.search(r"(?P<loc>.*?);.*?;", item)
        text_r = re.sub(r'.*?;.*?;null;null;', f"{loc['loc']};{str(int(runtime))};null;null;", item)
        loc_r += text_r
        runtime += delta_time

    loc_r = re.sub(r'.$', "", loc_r)

    begin_ymd = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(begintime))
    end_ymd = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(endtime))

    print(
        f"开始时间:{begin_ymd}, 结束时间:{end_ymd}, 用时:{usetime}秒, 里程:{distance / 1000}千米, 速度:{speed}分钟/千米")
    data = "{'begintime':'" + str(begintime) + "','endtime':'" + str(
        endtime) + "','uid':'" + uid_list[
               uid] + "','schoolno':'10755','distance':'" + f"{distance:.1f}" + "','speed':'" + str(
        speed) + "','studentno':'" + no + "','atttype':'3','eventno':'803','location':'" + loc_r + "','pointstatus':'1','usetime':'" + str(
        usetime) + "','path':'null'}"
    # print(data)
    gzip_data = gzip.compress(bytes(data, 'utf-8'))
    url = 'http://218.195.237.156:8029/DragonFlyServ/Api/webserver/uploadRunData'
    gzip_length = str(len(gzip_data))
    headers['Content-Length'] = gzip_length

    print("检查时间是否有误,无误输入1发包,输入任意键退出")
    key = input()
    if (key == '1'):
        resp = requests.post(url=url, headers=headers, data=gzip_data)
        print(resp.text)
        GetRunMeter(no)


# 发1.6km的包,从宿舍到一教
def PostRunData_1_6km(no, day, uid):
    headers['User-Agent'] = 'okhttp/5.0.0-alpha.10'
    # location格式:'纬度';'经度';时间戳;null;null;相较于上一次移动的位移,默认0.02;null@
    if (day != 0):
        begintime = int(time.time() - ((86400) * day) + random.randint(1, 360))  # 现在减day天
        endtime = begintime + 320 + random.randint(1, 100)
    else:
        endtime = int(time.time() - random.randint(1, 3600))
        begintime = endtime - 320 - random.randint(1, 100)

    distance = 1600.0 + random.uniform(-100.0, 100.0)
    runtime = begintime
    usetime = endtime - begintime - random.randint(1, 10)
    speed = (usetime / 60) / (distance / 1000)

    # 读取轨迹
    f = open(file=f'./location_1_6km', mode='r', encoding='utf-8')
    text = f.read()

    text_find = re.findall(r'.*?@', text)
    delta_time = usetime / len(text_find)
    loc_r = ""  # 替换时间位置
    for item in text_find:
        loc = re.search(r"(?P<loc>.*?);.*?;", item)
        text_r = re.sub(r'.*?;.*?;null;null;', f"{loc['loc']};{str(int(runtime))};null;null;", item)
        loc_r += text_r
        runtime += delta_time

    loc_r = re.sub(r'.$', "", loc_r)

    begin_ymd = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(begintime))
    end_ymd = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(endtime))

    print(
        f"开始时间:{begin_ymd}, 结束时间:{end_ymd}, 用时:{usetime}秒, 里程:{distance / 1000}千米, 速度:{speed}分钟/千米")
    data = "{'begintime':'" + str(begintime) + "','endtime':'" + str(
        endtime) + "','uid':'" + uid_list[
               uid] + "','schoolno':'10755','distance':'" + f"{distance:.1f}" + "','speed':'" + str(
        speed) + "','studentno':'" + no + "','atttype':'3','eventno':'803','location':'" + loc_r + "','pointstatus':'1','usetime':'" + str(
        usetime) + "','path':'null'}"
    # print(data)
    gzip_data = gzip.compress(bytes(data, 'utf-8'))
    url = 'http://218.195.237.156:8029/DragonFlyServ/Api/webserver/uploadRunData'
    gzip_length = str(len(gzip_data))
    headers['Content-Length'] = gzip_length

    print("检查时间是否有误,无误输入1发包,输入任意键退出")
    # key = input()
    # if (key == '1'):
    resp = requests.post(url=url, headers=headers, data=gzip_data)
    print(resp.text)
    GetRunMeter(no)


# 发1.16km的包,从西区食堂到一教
def PostRunData_1_16km(no, day, uid):
    '''
    :param no: 学号
    :param day: 时间偏移参数
    :param uid: 设备标识符索引
    :return:
    '''
    headers['User-Agent'] = 'okhttp/5.0.0-alpha.10'
    # location格式:'纬度';'经度';时间戳;null;null;相较于上一次移动的位移,默认0.02;null@
    if (day != 0):
        begintime = int(time.time() - (86400) * day)  # 现在减day天
        endtime = begintime + 320 + random.randint(1, 900)
    else:
        endtime = int(time.time() - random.randint(1, 3600))
        begintime = endtime - 320 - random.randint(1, 900)

    distance = 1160.0 + random.uniform(-50.0, 50.0)
    runtime = begintime
    usetime = endtime - begintime - random.randint(1, 10)
    speed = (usetime / 60) / (distance / 1000)

    # 读取轨迹
    f = open(file=f'./location_1_6km', mode='r', encoding='utf-8')
    text = f.read()

    text_find = re.findall(r'.*?@', text)
    delta_time = usetime / len(text_find)
    loc_r = ""  # 替换时间位置
    for item in text_find:
        loc = re.search(r"(?P<loc>.*?);.*?;", item)
        text_r = re.sub(r'.*?;.*?;null;null;', f"{loc['loc']};{str(int(runtime))};null;null;", item)
        loc_r += text_r
        runtime += delta_time

    loc_r = re.sub(r'.$', "", loc_r)

    begin_ymd = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(begintime))
    end_ymd = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(endtime))

    print(
        f"开始时间:{begin_ymd}, 结束时间:{end_ymd}, 用时:{usetime}秒, 里程:{distance / 1000}千米, 速度:{speed}分钟/千米")
    data = "{'begintime':'" + str(begintime) + "','endtime':'" + str(
        endtime) + "','uid':'" + uid_list[
               uid] + "','schoolno':'10755','distance':'" + f"{distance:.1f}" + "','speed':'" + str(
        speed) + "','studentno':'" + no + "','atttype':'3','eventno':'803','location':'" + loc_r + "','pointstatus':'1','usetime':'" + str(
        usetime) + "','path':'null'}"
    # print(data)
    gzip_data = gzip.compress(bytes(data, 'utf-8'))
    # POST  HTTP/1.1
    #        http://218.195.237.156:8029/DragonFlyServ//uploadRunData
    # url = 'http://218.195.237.156:8029/DragonFlyServ/Api/uploadRunData'
    url = 'http://218.195.237.156:8029/DragonFlyServ//uploadRunData'
    gzip_length = str(len(gzip_data))
    headers['Content-Length'] = gzip_length

    print("检查时间是否有误,无误输入1发包,输入任意键退出")
    key = input()
    if key == '1':
        resp = requests.post(url=url, headers=headers, data=gzip_data)
        print(resp.text)
        GetRunMeter(no)


if __name__ == '__main__':
    no = GetStuInfo()   # 输入学号并验证
    GetRunMeter(no)     # 查看当前跑步情况

    # 循环上传60天的跑步数据
    # i 今天往前推多少

    for i in range(0, 30):
        # def PostRunData_1_16km(no, day, uid):
        #   begintime = int(time.time() - (86400) * day)  # 现在减day天 +0.1前推2.4小时 -0.1后推2.4小时
        PostRunData_1_6km(no, i-0.3, 2)
