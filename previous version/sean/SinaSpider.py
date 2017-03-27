# -*- coding: utf-8 -*-

import os
import getpass
import json
import requests
import cookielib
import urllib
import urllib2
import gzip
import StringIO
import time
import re
from bs4 import BeautifulSoup as BS

import dataEncode
from Logger import LogClient


class SinaClient(object):
    def __init__(self, username=None, password=None):
        # 用户输入的用户名与密码
        self.username = username
        self.password = password
        # 从prelogin.php中获取的数据
        self.servertime = None
        self.nonce = None
        self.pubkey = None
        self.rsakv = None
        # 请求时提交的数据列表
        self.post_data = None
        self.headers = {}
        # 用于存储登录后的session
        self.session = None
        self.cookiejar = None
        # 用于输出log信息
        self.logger = None
        # 存储登录状态，初始状态为False
        self.state = False
        # 初始时调用initParams方法，初始化相关参数
        self.initParams()

    # 初始化参数
    def initParams(self):
        self.logger = LogClient().createLogger('SinaClient',
                                               'out/log_' + time.strftime("%Y%m%d", time.localtime()) + '.log')
        self.headers = dataEncode.headers
        return self

    # 设置username 和 password
    def setAccount(self, username, password):
        self.username = username
        self.password = password
        return self

    # 设置post_data
    def setPostData(self):
        self.servertime, self.nonce, self.pubkey, self.rsakv = dataEncode.get_prelogin_info()
        self.post_data = dataEncode.encode_post_data(self.username, self.password, self.servertime, self.nonce,
                                                     self.pubkey, self.rsakv)
        return self

    # 使用requests库登录到 https://login.sina.com.cn
    def login(self, username=None, password=None):
        # 根据用户名和密码给默认参数赋值,并初始化post_data
        self.setAccount(username, password)
        self.setPostData()
        # 登录时请求的url
        login_url = r'https://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.15)'
        session = requests.Session()
        response = session.post(login_url, data=self.post_data)
        json_text = response.content.decode('gbk')
        res_info = json.loads(json_text)
        try:
            if res_info["retcode"] == "0":
                self.logger.info("Login success!")
                self.state = True
                # 把cookies添加到headers中
                cookies = session.cookies.get_dict()
                cookies = [key + "=" + value for key, value in cookies.items()]
                cookies = "; ".join(cookies)
                session.headers["Cookie"] = cookies
            else:
                self.logger.error("Login Failed! | " + res_info["reason"])
        except Exception, e:
            self.logger.error("Loading error --> " + e)
        self.session = session
        return session

    # 生成Cookie,接下来的所有get和post请求都带上已经获取的cookie
    def enableCookie(self, enableProxy=False):
        self.cookiejar = cookielib.LWPCookieJar()  # 建立COOKIE
        cookie_support = urllib2.HTTPCookieProcessor(self.cookiejar)
        if enableProxy:
            proxy_support = urllib2.ProxyHandler({'http': 'http://122.96.59.107:843'})  # 使用代理
            opener = urllib2.build_opener(proxy_support, cookie_support, urllib2.HTTPHandler)
            self.logger.info("Proxy enable.")
        else:
            opener = urllib2.build_opener(cookie_support, urllib2.HTTPHandler)
        urllib2.install_opener(opener)

    # 使用urllib2模拟登录过程
    def login2(self, username=None, password=None):
        self.logger.info("Start to login...")
        # 根据用户名和密码给默认参数赋值,并初始化post_data
        self.setAccount(username, password)
        self.setPostData()
        self.enableCookie()
        # 登录时请求的url
        login_url = r'https://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.15)'
        headers = self.headers
        request = urllib2.Request(login_url, urllib.urlencode(self.post_data), headers)
        resText = urllib2.urlopen(request).read()
        try:
            jsonText = json.loads(resText)
            if jsonText["retcode"] == "0":
                self.logger.info("Login success!")
                self.state = True
                # 将cookie加入到headers中
                cookies = ';'.join([cookie.name + "=" + cookie.value for cookie in self.cookiejar])
                headers["Cookie"] = cookies
            else:
                self.logger.error("Login Failed --> " + jsonText["reason"])
        except Exception, e:
            print e
        self.headers = headers
        return self

    # 打开url时携带headers,此header需携带cookies
    def openURL(self, url, data=None):
        req = urllib2.Request(url, data=data, headers=self.headers)
        text = urllib2.urlopen(req).read()
        return text

    # 功能：将文本内容输出至本地
    def output(self, content, out_path, save_mode="a"):
        self.logger.info("Download html page to local machine. | path: " + out_path)
        prefix = os.path.dirname(out_path)
        if not os.path.exists(prefix):
            os.makedirs(prefix)
        fw = open(out_path, save_mode)
        fw.write(content)
        fw.close()
        return self

    """
    防止读取出来的HTML乱码，测试样例如下
    req = urllib2.Request(url, headers=headers)
    text = urllib2.urlopen(req).read()
    unzip(text)
    """

    def unzip(self, data):
        data = StringIO.StringIO(data)
        gz = gzip.GzipFile(fileobj=data)
        data = gz.read()
        gz.close()
        return data

        # 调用login1进行登录

#这个先放着做参考，实际没有用到
    def getUserInfos(self, uid):
        url_app = "http://weibo.cn/%s/info" % uid
        text_app = self.openURL(url_app)
        soup_app = unicode(BS(text_app, "html.parser"))
        nickname = re.findall(u'\u6635\u79f0[:|\uff1a](.*?)<br', soup_app)  # 昵称
        gender = re.findall(u'\u6027\u522b[:|\uff1a](.*?)<br', soup_app)  # 性别
        address = re.findall(u'\u5730\u533a[:|\uff1a](.*?)<br', soup_app)  # 地区（包括省份和城市）
        birthday = re.findall(u'\u751f\u65e5[:|\uff1a](.*?)<br', soup_app)  # 生日
        desc = re.findall(u'\u7b80\u4ecb[:|\uff1a](.*?)<br', soup_app)  # 简介
        sexorientation = re.findall(u'\u6027\u53d6\u5411[:|\uff1a](.*?)<br', soup_app)  # 性取向
        marriage = re.findall(u'\u611f\u60c5\u72b6\u51b5[:|\uff1a](.*?)<br', soup_app)  # 婚姻状况
        homepage = re.findall(u'\u4e92\u8054\u7f51[:|\uff1a](.*?)<br', soup_app)  # 首页链接
        # 根据app主页获取数据
        app_page = "http://weibo.cn/%s" % uid
        text_homepage = self.openURL(app_page)
        soup_home = unicode(BS(text_homepage, "html.parser"))
        tweets_count = re.findall(u'\u5fae\u535a\[(\d+)\]', soup_home)
        follows_count = re.findall(u'\u5173\u6ce8\[(\d+)\]', soup_home)
        fans_count = re.findall(u'\u7c89\u4e1d\[(\d+)\]', soup_home)
        # 根据web用户详情页获取注册日期
        url_web = "http://weibo.com/%s/info" % uid
        text_web = self.openURL(url_web)
        reg_date = re.findall(r"\d{4}-\d{2}-\d{2}", text_web)
        # 根据标签详情页获取标签
        tag_url = "http://weibo.cn/account/privacy/tags/?uid=%s" % uid
        text_tag = self.openURL(tag_url)
        soup_tag = BS(text_tag, "html.parser")
        res = soup_tag.find_all('div', {"class": "c"})
        tags = "|".join([elem.text for elem in res[2].find_all("a")])

        # 将用户信息合并
        userinfo = {}
        userinfo["uid"] = uid
        userinfo["nickname"] = nickname[0] if nickname else ""
        userinfo["gender"] = gender[0] if gender else ""
        userinfo["address"] = address[0] if address else ""
        userinfo["birthday"] = birthday[0] if birthday else ""
        userinfo["desc"] = desc[0] if desc else ""
        userinfo["sex_orientation"] = sexorientation[0] if sexorientation else ""
        userinfo["marriage"] = marriage[0] if marriage else ""
        userinfo["homepage"] = homepage[0] if homepage else ""
        userinfo["tweets_count"] = tweets_count[0] if tweets_count else "0"
        userinfo["follows_count"] = follows_count[0] if follows_count else "0"
        userinfo["fans_count"] = fans_count[0] if fans_count else "0"
        userinfo["reg_date"] = reg_date[0] if reg_date else ""
        userinfo["tags"] = tags if tags else ""
        return userinfo

#练习抓取用，最终不用
    def getUserInfos2(self,uid):
        url_app = "http://weibo.cn/%s/info" % uid
        text_app = self.openURL(url_app)
        soup_app = BS(text_app, "lxml")
        haha = soup_app.find_all(href=re.compile("gender"))
        b = haha[0].string
        c = haha[0].next_sibling

        print b,type(haha),c

        # 获取了Uid
    def getUserUid(self):
        url_app = "http://weibo.cn/"
        text_app = self.openURL(url_app)
        soup_app = BS(text_app, "lxml")
        # 网页中提取出Uid
        uuid = soup_app.find('div', class_='tip2').contents
        uuid2 = uuid[0]
        urlhaha = uuid2.get('href')
        Uid = urlhaha[1:11]
    #   print uuid,type(uuid),'\n',uuid2,'\n',type(uuid2),'\n',urlhaha,'\n',type(urlhaha),'\n',Uid
        return Uid
#获取个人发表到微博文本内容并打印
    def getUserWeibo(self,uid):
        url_app = "http://weibo.cn/%s/profile" % uid
        text_app = self.openURL(url_app)
        soup_app = BS(text_app, "lxml")
        weiboTxt = soup_app.find_all('span',class_='ctt')
        weibo = ['\n']
        for i in weiboTxt:
            lines = i.stripped_strings
            for j in lines:

                #print j,type(j)
                k = str(j.encode('utf-8'))
                #print k,type(k)
                #把那些都放入weibo这个list中
                weibo = weibo + ['%s'%k]

        return weibo





#测试用
def testLogin():
    client = SinaClient()
    username = raw_input("Please input username: ")
    password = getpass.getpass("Please input your password: ")
    session = client.login(username, password)

    follow = session.post("http://weibo.com/3570572115/").text.encode("utf-8")
    client.output(follow, "out/follow.html")


# 调用login2进行登录
def testLogin2():
    client = SinaClient()
    username = raw_input("Please input username: ")
    password = getpass.getpass("Please input your password: ")
    session = client.login2(username, password)

#    info = session.openURL("http://weibo.com/profile")
#    client.output(info, "out/info2.html")
    print '\n'
    uid = client.getUserUid()
#    infos = client.getUserInfos2(uid)
#    print infos
    weibo = client.getUserWeibo(uid)
    for i in weibo:
        print i
        client.output(i, "out/%sweibo.txt"%uid)



if __name__ == '__main__':
    testLogin2()