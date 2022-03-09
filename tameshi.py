from pydoc import html
from unicodedata import name
import click
from django.test import tag
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
from bidittemdb.models import Project, AttachedFile, Bidder, Prefecture, City, BidResult


def read_result(soup, item):
    tds = soup.find_all('table', class_='Sheet')
    if len(tds) == 0:  # テーブルがない場合（該当する発注情報がない場合
        return

    for td in tds:
        titles = td.find_all('td', class_='FieldLabel')
        for title in titles:
            title = title.get_text()

        values = td.find_all('td', class_='FieldData')
        for value in values:
            value = value.get_text()
            print(value)
        # value = ""
        # for value in values:
        # value = value.get_text()
        # if value=='' or value.startswith('*'):
        #   continue
        # print(value)

        # if title == '案件名称':
        #  item[NAME] = value
        # elif title == '案件番号':
        #  item[SERIAL_NO] = value
        # elif title == '発注者':
        #  item[NAME] = value
        # elif title == '入札結果':
        #  item[RESULT_CHOICES] = value
        #  if '落札失敗' in value:
        #    item[RESULT_CHOICES]=0
        #  elif '落札' in value:
        #    item[RESULT_CHOICES]=1
        #  elif '辞退' in value:
        #    item[RESULT_CHOICES]=2
        # elif title == '結果登録日':
        #   item[CREATED_ON] = value
        # elif title == '落札金額（※）':
        #   item[CONTRACT_PRICE] = value
        # elif title == '落札業者名':
        #   item[NAME] =value
        # elif title == '落札業者住所':
        #   departments = value.split()  # 空白でvalueを区切る
        #   if departments[0].endswith('県'):  # 最初の区切りに"県"が含まれる場合
        #      item[CITY] = None
        #   else:
        #      item[CITY] = departments[0]  # 最初の区切りに"市町村"が含まれる場合
        #      department = ""
        #      for i in range(1, len(departments)):  # 2つ目の区切り以降の文字を全てつなげる
        #        department = department + departments[i]
        #        item[DEPARTMENT] = department
        # elif title == '工事場所':
        # item[PLACE] =value
        # elif title == '工期':
        #  item[DELETED_AT] =value[9]
        # elif title =='予定価格（※）':
        #   item[ESTIMATED_PRICE] = int(value[10].replace(',', ''))
        #   if item[ESTIMATED_PRICE] is None:
        #      item[ESTIMATED_PRICE] = int(value[10].replace(',', ''))
        # if title == '最低制限価格（※）':
        #   try:
        #      item[PRICE] =value[11]
        #   except NoSuchElementException:
        #      pass

        # else:   #フォーマット決定後は削除
        #       item[title]=val


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
        options = Options()
        options.headless = True

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
                NAME,
                RESULT_CHOICES,
                CREATED_ON,
                CONTRACT_PRICE,
                NAME,
                CITY,
                DEPARTMENT,
                PLACE,
                DELETED_AT,
                ESTIMATED_PRICE,
                PRICE,
            ])
            item[SERIAL_NO] = 0  # 番号(デフォルト)
            item[NAME] = []
            alll = []
            # print(item)

            driver.switch_to.default_content()
            driver.switch_to_frame("ppimain")
            driver.switch_to_frame("main")
            time.sleep(2)

            for y in range(5):

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
                    break

                time.sleep(1)

                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                tds = soup.find_all('table', class_='Sheet')
                for td in tds:
                    values = td.find_all('td', class_='FieldData')
                    for value in values:
                        value = value.get_text()
                        value.append(value)
                        print(contents)
                        contents = []

                # html = driver.page_source.encode('utf-8')
                # soup = BeautifulSoup(html, 'html.parser')
                # tables = soup.find_all('table',class_='Sheet')
                # for table in tables:
                #    tds = table.find_all('td', class_='FieldData')
                #    for tdss in tds:
                #        tdss= tdss.get_text()
                #        alll.append(tdss)
                #    print(alll)

                # soup=BeautifulSoup(driver.page_source, 'html.parser')
                # [tag.extract() for tag in soup(string='\n')]    #余分な改行を消す
                # read_result(soup, item)
                # read_bid_result(soup, item)
                # print(item)

                # [tag.extract() for tag in soup(string='\n')]  # 余分な改行を消す
                # read_result(soup, item)
                # read_bid_result(soup, item)
                # print(soup, item)

                time.sleep(1)

                alll = []

                time.sleep(1)
                home = driver.find_element_by_xpath(
                    '/html/body/center/form[1]/table[4]/tbody/tr/td/img').click()


