from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from bidittemdb.management.commands.config import *
from bidittemdb.management.commands.crawl_data_save import CrawlData

import os
import re
import time
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


# コマンドが実行された際のメソッド
class Command(BaseCommand):
    def handle(self, *args, **options):

        # ===変数の設定===
        headless = True  # True=GUIなし
        # トップページ
        url = "https://ebidjk2.ebid2.pref.saitama.lg.jp/koukai/do/KF000ShowAction"
        # 業務区分 '工事等' or '物品等'
        division = '工事等'
        # division='物品等'
        # 調達区分 ’建設工事' or '設計・調査・測量' or '土木施設維持管理'　division=工事などの場合のみ
        # supply_type='建設工事'
        supply_type = '設計・調査・測量'
        # supply_type='土木施設維持管理'
        # 検索範囲
        start = {'year': 2020, 'month': 1, 'day': 23}
        end = {'year': 2020, 'month': 1, 'day': 23}
        # 表示件数 10 or 25 or 50 or 100
        max_items = [10, 25, 50, 100]
        max_item = max_items[0]
        # ===変数の設定(ここまで)===

        # ===ChromeDriverの設定===
        option = Options()
        if headless:  # GUIなしの場合
            option.add_argument('--headless')

        # driver_path='' #chrome driverにpathが通っていない場合設定
        # ===ChromeDriverの設定(ここまで)===

        # ===Functions===
        # 業務区分を選択して検索ページを開く
        def select_division(driver, division):
            # 右フレーム(frmRIGHT)を選択
            WebDriverWait(driver, 30).until(
                EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="frsMAIN"]/frame[2]')))

            # 業務区分を選択
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'chotatsuType')))
            dropdown = driver.find_element(By.ID, 'chotatsuType')
            select = Select(dropdown)
            select.select_by_visible_text(division)

            # 「5. 入札・見積結果情報の検索」をクリック
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'link5')))
            go_to_result_search = driver.find_element(By.ID, 'link5')
            go_to_result_search.click()
            time.sleep(1)

            return driver

        # ======
        # 検索の実行
        # start, end=開札日検索範囲, max_item=表示件数, division=業務区分, supplytype=調達区分
        def search(driver, start, end, max_item, division, supply_type=None):

            # 調達区分を選択(業務区分(division)="工事等"の場合のみ)
            if division == "工事等":
                dropdown = driver.find_element(By.NAME, 'supplytype')
                select = Select(dropdown)
                select.select_by_visible_text(supply_type)
                time.sleep(1)

            # 開札日の検索範囲を設定
            dropdown = driver.find_element(By.NAME, 'kaishi_nen')
            select = Select(dropdown)
            select.select_by_visible_text(str(start['year']))
            time.sleep(1)

            dropdown = driver.find_element(By.NAME, 'nyusatsubi_kaishi_tsuki')
            select = Select(dropdown)
            select.select_by_visible_text(str(start['month']))
            time.sleep(1)

            dropdown = driver.find_element(By.NAME, 'nyusatsubi_kaishi_nichi')
            select = Select(dropdown)
            select.select_by_visible_text(str(start['day']))
            time.sleep(1)

            dropdown = driver.find_element(By.NAME, 'owari_nen')
            select = Select(dropdown)
            select.select_by_visible_text(str(end['year']))
            time.sleep(1)

            dropdown = driver.find_element(By.NAME, 'nyusatsubi_owari_tsuki')
            select = Select(dropdown)
            select.select_by_visible_text(str(end['month']))
            time.sleep(1)

            dropdown = driver.find_element(By.NAME, 'nyusatsubi_owari_nichi')
            select = Select(dropdown)
            select.select_by_visible_text(str(end['day']))
            time.sleep(1)

            # 表示件数を設定
            dropdown = driver.find_element(By.NAME, 'A300')
            select = Select(dropdown)
            select.select_by_visible_text(str(max_item))
            time.sleep(1)

            # 検証ボタンをクリック
            go_to_result = driver.find_elements(By.CLASS_NAME, 'CystageBtn')[0]
            go_to_result.click()
            time.sleep(1)

            return driver

        # ======
        # beautifulsoapでの詳細情報・発注情報解析
        # soup=beautifulsoupオブジェクト、item=結果格納用配列
        def read_result(soup, item):

            tds = soup.find_all('td', class_='TableTitle')
            if len(tds) == 0:  # テーブルがない場合（該当する発注情報がない場合
                return

            for td in tds:
                title = td.get_text().strip()
                value = td.next_sibling.get_text().strip()  # class=TableTitleのtdの隣のtd
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
                elif title == '調達案件名称':
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
                    item[ESTIMATED_PRICE] = int(value.replace(',', ''))  # カンマを除去してintに変換
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

                # else:   #フォーマット決定後は削除
                #       item[title]=value

        # ======
        # beautifulsoapでの入札経過テーブルの解析
        # soup=beautifulsoupオブジェクト、item=結果格納用配列#item=結果格納用配列
        def read_bid_result(soup, item):

            # 入札結果テーブルに関する定数
            col_seriol_no = 0  # 業者番号・法人番号の列数
            col_bidder = 1  # 業者名の列数
            col_result = 2  # 結果の左端列数

            # 入札結果のtableを探す
            # class='TableTitle'のthが含まれるtableを取得
            th = soup.find('th', class_='TableTitle')
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

        # ======
        # 検索結果のテーブルを1行ずつ解析してデータを取得
        # line=行、division=業務区分、data=取得データ
        def get_result(driver, line, division, data):

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
            item[BID_METHOD_TYPE] = 0  # 電子調達(デフォルト)
            item[ATTACHED_FILE] = []
            item[BID_RESULT] = []
            if division == '物品等':  # 業務区分='物品等'の場合、調達区分が表示されないためデフォルトで設定
                item[CATEGORY_TYPE] = 2

            # 詳細情報ページへ移動
            if division == '工事等':  # 業務区分(division)='工事等'の場合
                path_for_detail = '/html/body/form/table/tbody/tr[' + str(line) + ']/td[3]/a'
            elif division == '物品等':  # 業務区分(division)='物品等'の場合
                path_for_detail = '/html/body/form/table/tbody/tr[' + str(line) + ']/td[2]/a'
            else:
                print('詳細ページへ移動できません')
                driver.quit()

            go_to_detail = driver.find_element(By.XPATH, path_for_detail)
            go_to_detail.click()
            time.sleep(1)

            # ページが全て読み込まれるまで待つ
            WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located)

            # 詳細情報はfrmRIGHTに表示されるので切り替える
            driver.switch_to.default_content()
            WebDriverWait(driver, 30).until(
                EC.frame_to_be_available_and_switch_to_it((By.XPATH, '//*[@id="frsMAIN"]/frame[2]')))

            # 全て読み込まれるのを待つ
            WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located)

            # beautifulsoapで詳細情報の解析
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            [tag.extract() for tag in soup(string='\n')]  # 余分な改行を消す
            read_result(soup, item)
            read_bid_result(soup, item)

            # 発注情報画面に移動
            go_to_order = driver.find_elements(By.CLASS_NAME, 'CystageBtn')[0]
            go_to_order.click()
            time.sleep(1)

            # 全て読み込まれるのを待つ
            WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located)

            # beautifulsoapで解析
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            [tag.extract() for tag in soup(string='\n')]  # 余分な改行を消す
            read_result(soup, item)

            # dataに解析結果(item)を追加する
            data.append(item)

            # 検索結果まで戻る
            go_back = driver.find_elements(By.CLASS_NAME, 'CystageBtn')[1]
            go_back.click()
            time.sleep(1)
            go_back = driver.find_elements(By.CLASS_NAME, 'CystageBtn')[1]
            go_back.click()
            time.sleep(1)

            # frmMainに切り替える
            WebDriverWait(driver, 30).until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'frmMain')))
            # ページが全て読み込まれるまで待つ
            WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located)

            return driver

        # ======
        # 検索結果ページを表示
        # page=ページ数, division=業務区分, data=取得データ
        def show_result_page(driver, page, division, data):

            # 検索結果がfrmRIGHTの中のfrmMainに表示されるので切り替える
            WebDriverWait(driver, 30).until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'frmMain')))

            # ページが全て読み込まれるまで待つ
            WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located)

            # tableの行数を読み込む
            max_line = len(
                driver.find_element(By.XPATH, '/html/body/form/table/tbody').find_elements(By.TAG_NAME, 'tr'))

            # 1行ずつデータを解析する
            for line in range(max_line):
                line = line + 1  # (line=1~max_line)
                driver = get_result(driver, line, division, data)  # データを1行ずつ解析・dataに追加

            # 親フレーム(frmRIGHT)に戻る
            driver.switch_to.parent_frame()

            return driver

        # 検索結果次ページへ移動
        def go_to_next_page(driver, page):
            next_page = page + 1

            # ページ数の入力
            WebDriverWait(driver, 30).until(EC.presence_of_element_located(
                (By.XPATH, '/html/body/form[1]/table[4]/tbody/tr[2]/td/table/tbody/tr[2]/td/input[1]')))
            input = driver.find_element(By.XPATH,
                                        '/html/body/form[1]/table[4]/tbody/tr[2]/td/table/tbody/tr[2]/td/input[1]')
            input.clear()
            time.sleep(1)
            input.send_keys(str(next_page))

            ##Goボタンのクリック
            go_to_page = driver.find_element(By.XPATH,
                                             '/html/body/form[1]/table[4]/tbody/tr[2]/td/table/tbody/tr[2]/td/a[1]')
            go_to_page.click()
            time.sleep(1)

            return driver

        # ===Functions(ここまで)===

        # chromedriverにpathが通っていない場合
        # with webdriver.Chrome(executable_path=driver_path, options=option) as driver:
        # chromedriverにpathが通っている場合
        try:
            driver = webdriver.Chrome(options=option)
            print("Start Chrome Driver.")

            # トップページにアクセス
            driver.get(url)
            time.sleep(1)

            # 業務区分を選択して検索ページを開く
            driver = select_division(driver, division)
            print('Open Search Page.')

            # 調達区分・開札日の検索範囲を設定、検索を実行
            WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located)  # 全部読み込んでから選択開始
            driver = search(driver, start, end, max_item, division, supply_type)
            print('Search is conducted.')

            # 最大ページ数の取得
            try:
                WebDriverWait(driver, 30).until(EC.presence_of_element_located(
                    (By.XPATH, '/html/body/form[1]/table[4]/tbody/tr[2]/td/table/tbody/tr[2]/td/input[2]')))
                max_page = int(driver.find_element(By.XPATH,
                                                   '/html/body/form[1]/table[4]/tbody/tr[2]/td/table/tbody/tr[2]/td/input[2]').get_attribute(
                    "value"))
            except NoSuchElementException:
                print('検索結果が見つかりません')
                driver.quit()

            # 1ページずつデータを取得
            data = []  # 取得データ配列

            for page in range(max_page):

                page = page + 1  # pageは1ページ目から

                # 検索結果ページを表示
                driver = show_result_page(driver, page, division, data)
                print('result page ' + str(page) + '/' + str(max_page))
                # 最終ページの場合
                if page == max_page:  # 最終ページ
                    break

                # 次ページへ移動
                driver = go_to_next_page(driver, page)

            # データ確認
            # if len(data)>2:
            #    test_data=[data[0], data[1]]
            #    print(test_data)
            #    crawl_data_class=CrawlData()
            #    print(crawl_data_class.check_list_data(test_data))

            print(str(len(data)) + ' data are processed.')
            driver.quit()

        finally:
            driver.quit()

