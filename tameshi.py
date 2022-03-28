from pydoc import html
from unicodedata import name
import click
from django.test import tag
from datetime import datetime
from importlib_resources import contents
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import time
import requests
from selenium.common.exceptions import NoSuchElementException
import re
from datetime import datetime
from django.utils.timezone import make_aware
from time import sleep
from bidittemdb.management.commands.config import *
from bidittemdb.management.commands.crawl_data_save import *
from django.core.management.base import BaseCommand
from django.core.management.base import BaseCommand
import os
import re
import copy
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
from datetime import datetime
from datetime import date
from bidittemdb.models import Project, AttachedFile, Bidder, Prefecture, City, BidResult
from bidittemdb.management.commands.crawl_data_save import CrawlData
from japanera import Japanera, EraDate


def read_result(soup, item, self):
    tds = soup.find_all('table', class_='Sheet')
    if len(tds) == 0:  # テーブルがない場合（該当する発注情報がない場合
        return

    td = tds[1]
    titles = td.find_all('td', class_='FieldLabel')
    values = td.find_all('td', class_='FieldData')
    for i in range(0, len(titles)):
        title = titles[i].get_text()
        value = values[i].get_text()
        # print(f'title(outside)={title}')
        # print(f'value={value}')
        # print(value)

        if title == '案件名称':
            item[NAME] = value.replace("\u3000", "None").replace("\xa0", "None")
        elif title == '案件番号':
            item[SERIAL_NO] = value.replace("\u3000", "None").replace("\xa0", "None")
        elif title == '発注者':
            item[NAME] = value.replace("\u3000", "None").replace("\xa0", "None")
        elif title == '入札結果':
            item[BID_RESULT] = value
        if '落札失敗' in value:
            item[BID_RESULT] = 0
        elif '落札' in value:
            item[BID_RESULT] = 1
        elif '辞退' in value:
            item[BID_RESULT] = 2


        elif title == '結果登録日':

            value = value.replace("令和", "").replace("年", " ").replace("月", " ").replace("日", "")
            value = list(value.split())
            value[0] = str(int(value[0]) + 2018)
            value = "/".join(value)
            date_dt = make_aware(datetime.strptime(value, '%Y/%m/%d'))
            item[OPENING_DATE] = date_dt

            # date = contents[10]
        # date = date.replace("令和","").replace("年"," ").replace("月"," ").replace("日","")
        # date = list(date.split())
        # date[0] = str(int(date[0]) + 2018)
        # date = "-".join(date)
        # elems_date.append(datetime.strptime(date, "%Y-%m-%d"))

        # if key == CONTRACT_TO:
        # value = self.change_calendar_to_western(value)

        elif title == '落札金額（※）':
            item[CONTRACT_PRICE] = value.replace("\u3000", "None").replace("\xa0", "None")
        elif title == '落札業者名':
            item[NAME] = value.replace("\u3000", "None").replace("\xa0", "None")
        elif title == '落札業者住所':
            item[CITY] = value.replace("\u3000", "None").replace("\xa0", "None")
            # if departments[0].endswith('富山県'):  # 最初の区切りに"県"が含まれる場合
            #    item[CITY] = None
            #    item[CITY] = departments[0]  # 最初の区切りに"市町村"が含まれる場合
            #    department = ""
            #    for i in range(1, len(departments)):  # 2つ目の区切り以降の文字を全てつなげる
            #      department = epartment + departments[i]
            #      item[DEPARTMENT] = department
        elif title == '工事場所':
            item[PLACE] = value.replace("\u3000", "None").replace("\xa0", "None")
        elif title == '工期':
            item[CONTRACT_TO] = value.replace("\u3000", "None").replace("\xa0", "None")
        elif title == '予定価格（※）':
            item[ESTIMATED_PRICE] = value.replace("\u3000", "None").replace("\xa0", "None")
        if item[ESTIMATED_PRICE] is None:
            item[ESTIMATED_PRICE] = int(value)
        if title == '最低制限価格（※）':
            item[CONTRACT_PRICE] = value.replace("\u3000", "None").replace("\xa0", "None")


def read_bid_result(soup, item, self):
    tds = soup.find_all('table', class_='Sheet')
    for i in tds:
        value = i.find_all('td', class_='ListData')
        for it in value:
            values = it.get_text()
            print(values)


def pass_result(soup, item, self):
    tds = soup.find_all('table', class_='Sheet')
    for i in tds:
        value = i.find_all('td', class_='ListData')
        for it in value:
            values = it.get_text()
            print(values)

    # if len(tds) == 0:  # テーブルがない場合（該当する発注情報がない場合
    #   return

    # titles=td.find_all('td', class_='ListLabel')
    # values=td.find_all('td', class_='ListData')
    # for i in range(0, len(titles)):
    # title = titles[i].get_text()
    # value = values[i].get_text()
    # print(title)
    # print(value)


def paser_result(soup, item, self):
    tds = soup.find_all('table', class_='Sheet')
    if len(tds) == 0:  # テーブルがない場合（該当する発注情報がない場合
        return

    td = tds[1]
    titles = td.find_all('td', class_='FieldLabel')
    values = td.find_all('td', class_='FieldData')
    for i in range(0, len(titles)):
        title = titles[i].get_text()
        value = values[i].get_text()
        print(f'title(outside)={title}')
        print(f'value={value}')
        print(value)


def paser_results(soup, item, self):
    tds = soup.find_all('table', class_='Sheet')
    if len(tds) == 0:  # テーブルがない場合（該当する発注情報がない場合
        return

    td = tds[2]
    titles = td.find_all('td', class_='FieldLabel')
    values = td.find_all('td', class_='FieldData')
    for i in range(0, len(titles)):
        title = titles[i].get_text()
        value = values[i].get_text()
        print(f'title(outside)={title}')
        print(f'value={value}')
        print(value)


def pass_paster(soup, item, self):
    tds = soup.find_all('table', class_='Sheet')
    if len(tds) == 0:  # テーブルがない場合（該当する発注情報がない場合
        return

    td = tds[1]
    titles = td.find_all('td', class_='FieldLabel')
    values = td.find_all('td', class_='FieldData')
    for i in range(0, len(titles)):
        title = titles[i].get_text()
        value = values[i].get_text()
        print(f'title(outside)={title}')
        print(f'value={value}')
        print(value)


def pass_pasters(soup, item, self):
    tds = soup.find_all('table', class_='Sheet')
    for i in tds:
        value = i.find_all('td', class_='ListData')
        for it in value:
            values = it.get_text()
            print(values)


class Command(BaseCommand):
    COMMAND = "crawl_toyama"

    def handle(self, *args, **options):

        elems_number = []
        elems_title = []
        elems_order_person = []
        elems_result = []
        elems_register_day = []
        elems_price = []
        elems_get_person = []
        elems_person_adress = []
        elems_construction_place = []
        elems_days = []
        elems_suppose_price = []
        elems_pre_price = []

        elems_remark = []
        contents = []
        sample_data = []
        options = Options()
        options.headless = True

        try:
            driver = webdriver.Chrome(options=options)
            url = 'http://ebid.icals.jp/160008/Public/Server'

            driver.get(url)

            # 入札にアクセス
            driver.switch_to.frame("ppimain")
            driver.switch_to.frame("main")
            new = driver.find_element_by_link_text("入札結果情報")
            new.click()
            time.sleep(2)

            # すべて検索
            # driver.switch_to.default_content()
            # driver.switch_to.frame("ppimain")
            # driver.switch_to.frame("main")
            month = driver.find_element_by_xpath(
                '/html/body/center/form[1]/table[1]/tbody/tr[1]/td[1]/table/tbody/tr[9]/td[2]/select[1]/option[14]').click()
            day = driver.find_element_by_xpath(
                '/html/body/center/form[1]/table[1]/tbody/tr[1]/td[1]/table/tbody/tr[9]/td[2]/select[2]/option[13]').click()
            enter = driver.find_element_by_xpath(
                '/html/body/center/form[1]/table[2]/tbody/tr/td[1]/img')
            # enter.send_keys(Keys.ENTER)
            enter.click()
            print(driver.current_url)

            time.sleep(4)

            enterr = driver.find_element_by_xpath(
                '/html/body/center/form[1]/table/tbody/tr/td[1]/img').click()
            time.sleep(4)
            print(driver.current_url)

            #   #ここまで問題なし
            #    html=driver.page_source
            #    print(html)

            # 予想ではできてるはず。ちょっと実験が。。。。

            # beeatifulsoupの動きでスクレーピングできる？　未定　仮説 できていてただ二回目が空白、戻るキーの問題か？

            for z in range(1):

                item = dict.fromkeys([  # 結果格納用配列=Noneで初期化
                    NAME,
                    SERIAL_NO,
                    BID_METHOD_TYPE,
                    BID_FORMAT_TYPE,
                    CATEGORY_TYPE,
                    SECTOR,
                    PLACE,
                    DESCRIPTION,
                    ETC,
                    RELEASE_DATE,
                    ORIENTATION_DATE,
                    ENTRY_FROM,
                    ENTRY_TO,
                    SUBMIT_FROM,
                    SUBMIT_TO,
                    OPENING_DATE,
                    ESTIMATED_PRICE,
                    CRWAL_URL,
                    CONTRACT_DATE,
                    CONTRACT_PRICE,
                    CONTRACT_FROM,
                    CONTRACT_TO,
                    CITY,
                    DEPARTMENT,
                    ATTACHED_FILE,
                    BID_RESULT,

                ])
                item[BID_RESULT] = []  # 番号(デフォルト)
                item[ATTACHED_FILE] = []
                item[BID_METHOD_TYPE] = 0
                item[BID_FORMAT_TYPE] = 0
                item[CATEGORY_TYPE] = 0
                alll = []

                driver.switch_to.default_content()
                driver.switch_to_frame("ppimain")
                driver.switch_to_frame("main")
                time.sleep(2)

                for y in range(9):

                    driver.switch_to.default_content()
                    driver.switch_to_frame("ppimain")
                    driver.switch_to_frame("main")
                    time.sleep(2)

                    # keywords = ["案件番号", "案件名称", "発注者", "入札結果", "結果登録日", "落札金額",
                    # "落札業者名", "落札業者住所", "工事場所", "工期", "予定価格", "調査基準価格"]
                    # elems_keywords = [elems_number, elems_title, elems_order_person, elems_result, elems_register_day, elems_price,
                    # elems_get_person, elems_person_adress, elems_construction_place, elems_days, elems_suppose_price, elems_pre_price]
                    alll = []
                    number = str(y + 2)

                    try:
                        driver.find_element_by_xpath(
                            '/html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[' + number + ']/td[1]/a').click()
                        # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[2]/td[1]/a
                        time.sleep(4)
                    # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[3]/td[1]/a
                    # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[4]/td[1]/a
                    except NoSuchElementException:
                        pass

                    time.sleep(1)

                    # html = driver.page_source
                    # soup = BeautifulSoup(html, 'html.parser')
                    # tds = soup.find_all('table',class_='Sheet')
                    # for td in tds:
                    #    values=td.find_all('td', class_='FieldData')
                    #    for value in values:
                    #       value = value.get_text()
                    # name.save(value)
                    #       contents.append(value)
                    #    print(contents)
                    #    contents=[]

                    # html = driver.page_source.encode('utf-8')
                    # soup = BeautifulSoup(html, 'html.parser')
                    # tables = soup.find_all('table',class_='Sheet')
                    # for table in tables:
                    #    tds = table.find_all('td', class_='FieldData')
                    #    for tdss in tds:
                    #        tdss= tdss.get_text()
                    #        alll.append(tdss)
                    #    print(alll)

                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    [tag.extract() for tag in soup(string='\n')]  # 余分な改行を消す
                    # read_result(soup, item, self)
                    read_bid_result(soup, item, self)

                    # print(item, "\n\n") #辞書データの出力
                    # sample_data.append(item)

                    # この先の実装の仕方考え中。

                    try:
                        driver.find_element_by_xpath('/html/body/center/form[1]/table[3]/tbody/tr/td[1]/img').click()
                        # /html/body/center/form[1]/table[3]/tbody/tr/td[1]/img
                        time.sleep(2)  # /html/body/center/form[1]/table[3]/tbody/tr/td[1]/img

                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        [tag.extract() for tag in soup(string='\n')]
                        # pass_result(soup, item, self)
                        # print(pass_result(soup, item, self))

                        driver.find_element_by_xpath('/html/body/center/form[1]/table[5]/tbody/tr/td/img').click()

                    # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[3]/td[1]/a
                    # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[4]/td[1]/a
                    except NoSuchElementException:
                        pass

                    try:
                        driver.find_element_by_xpath('/html/body/center/form[1]/table[3]/tbody/tr/td[2]/img').click()
                        # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[2]/td[1]/a
                        time.sleep(2)
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        [tag.extract() for tag in soup(string='\n')]
                        # paser_result(soup, item, self)
                        # paser_results(soup, item, self)

                        driver.find_element_by_xpath('/html/body/center/form[1]/table[2]/tbody/tr/td/img').click()

                    # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[3]/td[1]/a 調べる
                    # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[4]/td[1]/a
                    except NoSuchElementException:
                        pass

                    try:
                        driver.find_element_by_xpath('/html/body/center/form[1]/table[3]/tbody/tr/td[3]/img').click()
                        # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[2]/td[1]/a
                        time.sleep(2)

                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        [tag.extract() for tag in soup(string='\n')]
                        # pass_paster(soup, item, self)
                        # pass_pasters(soup, item, self)

                        driver.find_element_by_xpath('/html/body/center/form[1]/table[3]/tbody/tr/td/img').click()

                    # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[3]/td[1]/a
                    # /html/body/center/form[1]/table[2]/tbody/tr[1]/td[1]/table/tbody/tr[4]/td[1]/a
                    except NoSuchElementException:
                        pass

                        # [tag.extract() for tag in soup(
                    # string='\n')]  # 余分な改行を消す
                    # read_result(soup, item)
                    # read_bid_result(soup, item)
                    # print(soup, item)

                    time.sleep(1)

                    alll = []

                    time.sleep(1)
                    try:
                        home = driver.find_element_by_xpath(
                            '/html/body/center/form[1]/table[4]/tbody/tr/td/img').click()
                    # /html/body/center/form[1]/table[5]/tbody/tr/td/img
                    # /html/body/center/form[1]/table[4]/tbody/tr/td/img
                    # /html/body/center/form[1]/table[5]/tbody/tr/td/img
                    except NoSuchElementException:
                        homem = driver.find_element_by_xpath(
                            '/html/body/center/form[1]/table[5]/tbody/tr/td/img').click()

                    except NoSuchElementException:
                        home = driver.find_element_by_xpath(
                            '/html/body/center/form[1]/table[4]/tbody/tr/td/img').click()

            # print(sample_data, "\n\n")
            #                          /html/body/center/form[1]/table[5]/tbody/tr/td/img
            # crawl_date_class = CrawlData()/html/body/center/form[1]/table[5]/tbody/tr/td/img
            # print(crawl_date_class.check_list_data(sample_data))



        finally:
            driver.quit()
