from pydoc import html
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
            value = value.get_text()  # class=TableTitleのtdの隣のtd

        if value == '' or value.startswith('*'):  # データが空白の場合と"*"から始まる場合、次の行に移る
            continue

        if title == '入札方式':
            if '一般競争入札' in value:
                item[BID_FORMAT_TYPE] = 0
            elif '指名競争入札' in value:
                item[BID_FORMAT_TYPE] = 1
            elif '公募' in value or 'プロポーザル' in value:
                item[BID_FORMAT_TYPE] = 2
            elif '随意契約' in value:
                item[BID_FORMAT_TYPE] = 3
        elif title == '案件名称':
            item[NAME] = value
        elif title == '案件番号':
            item[SERIAL_NO] = value
        elif title == '調達区分':  # 業務区分=工事等の場合のみ
            if value == '建設工事':
                item[CATEGORY_TYPE] = 0  # 工事
            elif value == '設計・調査・測量':
                item[CATEGORY_TYPE] = 1  # コンサル
            elif value == '土木施設維持管理':
                item[CATEGORY_TYPE] = 3  # 委託
            item[SECTOR] = value
        elif title == '業種／業務' or title == '業種及び格付':
            if item[SECTOR] is None:
                item[SECTOR] = value
            else:
                item[SECTOR] = item[SECTOR] + '/' + value
        elif title == '案件場所' or title == '納入場所':
            item[PLACE] = re.sub(r"\s", "", value)  # 空白・改行を削除
        elif title == '案件概要':  # 発注情報のみ
            item[DESCRIPTION] = re.sub(r"\s", "", value)  # 空白・改行を削除
        elif title == '備考':  # 発注情報・業務区分=物品の時のみ
            item[ETC] = re.sub(r"\s", "", value)  # 空白・改行を削除
        elif title == '公開日':  # 発注情報のみ
            date_dt = make_aware(datetime.strptime(value.split()[0], '%Y/%m/%d'))
            item[RELEASE_DATE] = date_dt
        elif title == '開札日':
            date_dt = make_aware(datetime.strptime(value.split()[0], '%Y/%m/%d'))
            item[OPENING_DATE] = date_dt
        elif '予定価格' in title:
            if item[ESTIMATED_PRICE] is None:  # カンマを除去してintに変換
                pass
            else:
                item[ESTIMATED_PRICE] = int(value.replace(',', ''))
        elif '設計額' in title:
            if item[ESTIMATED_PRICE] is None:
                item[ESTIMATED_PRICE] = int(value.replace(',', ''))
        elif title == '課所名':
            departments = value.split()  # 空白でvalueを区切る
            if departments[0].endswith('県'):  # 最初の区切りに"県"が含まれる場合
                item[CITY] = None
            else:
                item[CITY] = departments[0]  # 最初の区切りに"市町村"が含まれる場合

            department = ""
            for i in range(1, len(departments)):  # 2つ目の区切り以降の文字を全てつなげる
                department = department + departments[i]
            item[DEPARTMENT] = department

        elif title.startswith('結果図書ファイル') or title.startswith('入札公告等ファイル') or title.startswith('発注図書ファイル'):
            if value != None:
                attached_file = {}
                # 添付ファイル名
                attached_file[NAME] = value
                # 添付ファイルパス(リンクの代わりにxpathを記録:2022/2/2現在)
                if title.startswith('発注図書ファイル'):
                    id = re.sub(r"\D", "", title)  # titleから数値のみを取り出す
                    attached_file[PATH] = '/html/body/form/div[3]/table[4]/tbody/tr[' + str(id) + ']/td[2]/a'
                else:
                    id = td.next_sibling.find('a').get('id')  # XPATHをidで指定する
                    attached_file[PATH] = '//*[@id="' + id + '"]'

                item[ATTACHED_FILE].append(attached_file)


def read_bid_result(soup, item):
    # 入札結果テーブルに関する定数
    col_seriol_no = 0  # 業者番号・法人番号の列数
    col_result = 2  # 結果の左端列数

    # 入札結果のtableを探す
    # class='TableTitle'のthが含まれるtableを取得
    th = soup.find_all('table', class_='Sheet')
    if th == None:  # テーブルがない場合（入札結果がない場合)
        return

    table = th.parent.parent
    rows = table.find_all('tr')  # 1行ごとのデータに分解
    number_of_rows = len(rows)
    # 表の見出し(1行目)を取得
    bid_result_header = [c.get_text().strip() for c in rows[0].find_all('th')]
    max_col = len(bid_result_header)
    # 入札回数の最大値を取得 (表の'金額'の個数)
    max_bit_count = len(rows[1].find_all('th'))

    # 入札回数のデータを得る(3列目～)
    # '随意契約'などを無視できるようになれば必要なし
    bid_count_header = []
    for col in range(col_result, col_result + max_bit_count):
        th_item = bid_result_header[col]
        if (str.isdigit(th_item[1]) or th_item == '最終回'):
            bid_count_header.append(col - 1)
        else:
            bid_count_header.append(0)

    # 1行ずつデータを取得
    # 見出し(th)2行が先頭にあるため、3行目のデータから読み込み開始
    for line in range(2, number_of_rows):
        bid_result = dict.fromkeys([  # 入札結果用配列=Noneで初期化
            BIDDER,
            PRICE,
            BID_COUNT,
            RESULT_TYPE,
            SERIAL_NO,
            REPRESENTATIVE,
            MAIL,
            PASSWORD
        ])
        bid_result[RESULT_TYPE] = 0  # 入札結果を「入札失敗」で初期化
        tds = rows[line].find_all('td')

        # 業者名を取得(2列目)
        value = tds[col_bidder].get_text().strip()
        if value == '' or value.startswith('**'):  # 業者名が空白、または'**'で始まる場合、行ごとスキップ
            continue
        else:
            bid_result[BIDDER] = re.sub(r"\s", "", value)  # 空白・改行を削除
            # 業者名にfont(color)が設定されていたら落札成功
            if tds[1].find('font') != None:
                bid_result[RESULT_TYPE] = 1

        # 業者番号・法人番号などを取得(1列目)
        value = tds[col_seriol_no].get_text().strip()
        if value != '' and not (value.startswith('**')):
            bid_result[SERIAL_NO] = int(value)

        # 表の右端のデータを取得、'辞退'・'抜け'の文字が含まれていたら辞退
        value = tds[max_col - 1].get_text().strip()
        if '辞退' in value or '抜け' in value:
            bid_result['result_type'] = 2

            # 金額を取得(1回目=3列目・必ずbid_resultを登録)
        value = tds[col_result].get_text().strip().replace(',', '')  # カンマを除去
        bid_result[BID_COUNT] = 1
        if str.isdigit(value):
            bid_result[PRICE] = int(value)
        else:
            bid_result[PRICE] = None  # priceにNoneが入るのは1回目の時のみ

        # 2回目以降の金額を取得
        for col in range(1, max_bit_count):
            value = tds[col_result + col].get_text().strip().replace(',', '')  # カンマを除去
            if str.isdigit(value):  # priceが数値の場合のみbid_resultを登録する
                if bid_result[PRICE] != None:  # 前回の金額がNoneではない場合
                    # 前回のbid_resultを落札失敗にする
                    temp_result_type = bid_result[RESULT_TYPE]
                    bid_result[RESULT_TYPE] = 0
                    # 前回のデータを登録
                    item[BID_RESULT].append(copy.deepcopy(bid_result))
                    # bid_resultを元に戻す
                    bid_result[RESULT_TYPE] = temp_result_type

                # 回数を上書き
                bid_result[BID_COUNT] = bid_count_header[col]
                # 価格を上書き
                bid_result[PRICE] = int(value)
            else:
                continue

        item[BID_RESULT].append(copy.deepcopy(bid_result))


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
                DEPARTMENT
            ])
            item[SERIAL_NO] = 0  # 番号(デフォルト)
            item[NAME] = []
            alll = []

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

                # time.sleep(3) 実装の確認
                # html = driver.page_source
                # soup = BeautifulSoup(html, 'html.parser')
                # alls = soup.find('table', class_='Field')
                # allss = alls.find_all('td', class_='FieldData')
                # for g in allss:
                # elems_number = g.text
                # contents.append(elems_number)
                # time.sleep(1)
                # alll = []
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
                read_result(soup, item)
                read_bid_result(soup, item)

                # [tag.extract() for tag in soup(string='\n')]  # 余分な改行を消す
                # read_result(soup, item)
                # read_bid_result(soup, item)
                # print(soup, item)

                time.sleep(1)

                alll = []

                time.sleep(1)
                home = driver.find_element_by_xpath(
                    '/html/body/center/form[1]/table[4]/tbody/tr/td/img').click()


