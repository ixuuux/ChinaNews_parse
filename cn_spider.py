# -*- coding: utf-8 -*-
import jieba
import os
from lxml import etree
import requests
import time
from wordcloud import WordCloud
import threading as td

max_req = 5  # 最大重试次数

DIR_NAME = time.strftime("%Y-%m-%d %H_%M_%S", time.localtime())
try:
    os.mkdir(DIR_NAME)
except Exception as e:
    print(e)
    pass


class GetHtml(object):
    num = 0

    def get_one_page(self, url, headers, timeout=5):
        if self.num < max_req:
            try:
                response = requests.get(url=url, headers=headers, timeout=timeout)
                if response.status_code == 200:
                    self.num = 0
                    return response
            except TimeoutError:
                print("Time Out", url)
                self.num += 1
                time.sleep(self.num)
                return self.get_one_page(url=url, headers=headers, timeout=timeout + self.num * 3)
            except Exception as e:
                print(e, url)
                self.num += 1
                time.sleep(self.num)
                return self.get_one_page(url=url, headers=headers, timeout=timeout + self.num * 3)


class BaseClass(GetHtml):
    def __init__(self, url, name):
        self.url = url
        self.name = name
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/67.0.3396.62 Safari/537.36"
        }
        self.timeout = 5
        pass

    def get_html(self):
        return self.get_one_page(url=self.url, headers=self.headers, timeout=self.timeout).content.decode()

    def parse(self, html):
        pass

    def save(self, info):
        with open(".\\{}\\{}.txt".format(DIR_NAME, self.name), "a", encoding="utf-8") as f:
            f.write(info)
            f.write("\n")

    def run(self):
        s = time.time()
        html = self.get_html()
        for info in self.parse(html):
            self.save(info)
        self.wordc(self.name)
        e = time.time()
        print("{}完成，用时：".format(self.name), e - s)

    def wordc(self, file_name, font_path="msyh.ttc"):
        with open(".\\{}\\{}.txt".format(DIR_NAME, file_name), encoding="utf-8") as f:
            seg_list = jieba.cut(f.read(), cut_all=False)
            a = " ".join(seg_list)
            word_coulds = WordCloud(
                font_path=font_path,  # 字体
                background_color='white',  # 背景颜色
                max_words=5000,  # 要显示的词的最大个数
                min_font_size=9,  # 显示的最小的字体大小
                width=1100,  # 输出的画布宽度，默认为400像素
                height=650,  # 输出的画布高度，默认为400像素
                relative_scaling=1,  # 词频和字体大小的关联性
                random_state=20  # 可以有多少种随机配色
            )
            a = word_coulds.generate(a)
            a.to_file(".\\{}\\{}.jpg".format(DIR_NAME, file_name))

    def __del__(self):
        print(os.getcwd())


class RenminRibao(BaseClass):  # 人民日报
    def __init__(self):
        url = "http://paper.people.com.cn/rmrb/html/{}/nbs.D110000renmrb_01.htm".format(time.strftime("%Y-%m/%d"))
        super().__init__(url, "人民日报")

    def parse(self, html):
        try:
            ele = etree.HTML(html)
            for i in ele.xpath('//div[@id="pageList"]/ul/div'):
                if i.xpath('.//text()')[1][-2:] == "要闻":
                    nbs = i.xpath('.//a[@id="pageLink"]/@href')
                    qz_url = "http://paper.people.com.cn/rmrb/html/{}/".format(time.strftime("%Y-%m/%d"))
                    if nbs[0][:3] == "nbs":
                        info_html = self.get_one_page(qz_url + nbs[0], headers=self.headers).content.decode()
                    else:
                        info_html = self.get_one_page(qz_url + nbs[0][2:], headers=self.headers).content.decode()
                    elee = etree.HTML(info_html)
                    for ii in elee.xpath('//div[@id="titleList"]/ul//li'):
                        data_html = self.get_one_page(qz_url + ii.xpath('./a/@href')[0],
                                                      headers=self.headers).content.decode()
                        etr = etree.HTML(data_html)
                        yield "".join(etr.xpath('//div[@id="ozoom"]//p//text()'))
        except IndexError as e:
            print("人民日报", e)


class XinhuaRibao(BaseClass):  # 新华日报
    def __init__(self):
        url = "http://xh.xhby.net/mp3/pc/layout/{}/".format(time.strftime("%Y%m/%d"))
        super().__init__(url, "新华日报")

    def get_html(self):
        return self.get_one_page(url=self.url + "l1.html", headers=self.headers, timeout=self.timeout).content.decode()

    def parse(self, html):
        try:
            ele = etree.HTML(html)
            for i in ele.xpath('//ul[@class="page-num"]//li'):
                if i.xpath('./a/text()')[0][4:] in ["要闻", "重要新闻"]:
                    info_url = self.url + i.xpath('./a/@href')[0]
                    info_html = self.get_one_page(info_url, headers=self.headers).content.decode()
                    elee = etree.HTML(info_html)
                    for ii in elee.xpath('//ul[@id="articlelist"]//li'):
                        data_url = ii.xpath('./a/@href')[0].replace("../../..", "http://xh.xhby.net/mp3/pc")
                        data_html = self.get_one_page(data_url, headers=self.headers).content.decode()
                        el = etree.HTML(data_html)
                        yield "".join(el.xpath('//div[@id="ozoom"]//p//text()'))
        except IndexError as e:
            print("新华日报", e)
        except:
            pass


class ChinaDaily(BaseClass):  # 中国日报，海外
    def __init__(self):
        url = "http://www.chinadaily.com.cn/china/governmentandpolicy"
        super().__init__(url, "中国日报")

    def parse(self, html):  # 提取每篇新闻的url，交由get_doc方法处理
        try:
            ele = etree.HTML(html)
            blo = ele.xpath('//div[@id="lft-art"]//div[contains(@class, "mb10")]')
            for i in blo:
                yield "http:" + i.xpath('.//a/@href')[0]
        except IndexError as e:
            print("中国日报", e)

    def get_doc(self, url):  # 获取新闻正文
        html = self.get_one_page(url, headers=self.headers).text
        ele = etree.HTML(html)
        for i in ele.xpath('//div[@id="Content"]'):
            yield ''.join(i.xpath('.//p/text()'))

    def run(self):
        s = time.time()
        html = self.get_html()
        for url in self.parse(html):
            for info in self.get_doc(url):
                self.save(info)
        self.wordc(self.name)
        e = time.time()
        print("中国日报完成，用时：", e - s)


class GMDaily(BaseClass):  # 光明日报
    def __init__(self):
        url = "http://www.gmw.cn/"
        super().__init__(url, "光明日报")

    def parse(self, html):  # 提取每篇新闻的url，交由get_doc方法处理
        try:
            ele = etree.HTML(html)
            blo = ele.xpath('//div[contains(@class, "focusAreaM")]')
            for i in blo:
                lists = i.xpath('.//a[@target="_blank"]/@href')
                for ii in lists:
                    if ii[:4] == "http":
                        yield ii
        except IndexError as e:
            print("光明日报", e)

    def get_doc(self, url):  # 获取新闻正文
        html = self.get_one_page(url, headers=self.headers)
        if html:
            ele = etree.HTML(html.content.decode())
            for i in ele.xpath('//div[@id="contentMain"]'):
                yield ''.join(i.xpath('.//p//text()'))

    def run(self):
        s = time.time()
        html = self.get_html()
        for url in self.parse(html):
            for info in self.get_doc(url):
                # print(info)
                self.save(info)
        self.wordc(self.name)
        e = time.time()
        print("光明日报完成，用时：", e - s)


class ChinaGov(BaseClass):  # 中国政府网，首页 > 新闻 > 要闻
    # Add China Government Network News
    def __init__(self):
        url = "http://www.gov.cn/xinwen/yaowen.htm"
        super().__init__(url, "中国政府网")

    def get_html(self):
        return self.get_one_page(url=self.url, headers=self.headers, timeout=8)

    def parse(self, html):
        try:
            ele = etree.HTML(html)
            blo = ele.xpath('//div[@class="news_box"]//ul//li')
            for i in blo:
                lists = i.xpath('.//h4/a/@href')
                for ii in lists:
                    if i.xpath('.//h4/span/text()')[0].strip()[-2:] == time.strftime('%d'):
                        if ii[:4] == 'http':
                            yield ii
                        else:
                            yield 'http://www.gov.cn' + ii
        except IndexError as e:
            print("中国政府网", e)
        except Exception as r:
            print('中国政府网', r)

    def get_doc(self, url):
        html = self.get_one_page(url, headers=self.headers).content.decode()
        ele = etree.HTML(html)
        doc = ele.xpath('//div[@class="pages_content"]//p//text()')
        return ''.join([i.strip() for i in doc if i])

    def run(self):
        s = time.time()
        html = self.get_one_page(url=self.url, headers=self.headers, timeout=8).text
        for url in self.parse(html):
            info = self.get_doc(url)
            self.save(info)
        self.wordc(self.name)
        e = time.time()
        print("中国政府网完成，用时：", e - s)


if __name__ == '__main__':
    s = time.time()
    renminribao = RenminRibao()
    xinhuaribao = XinhuaRibao()
    chinadaily = ChinaDaily()
    gmdaily = GMDaily()
    chinagov = ChinaGov()
    td.Thread(target=renminribao.run).start()
    td.Thread(target=xinhuaribao.run).start()
    td.Thread(target=chinadaily.run).start()
    td.Thread(target=gmdaily.run).start()
    td.Thread(target=chinagov.run).start()
    print("用时：", time.time() - s)
