# -*- coding: utf-8 -*-
# pyenv card

import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import configparser 

# additional imports
import tag_to_json as ttj
import get_detail as gd

config = configparser.ConfigParser()
config.read("config.ini")

# rootディレクトリ
BASE_URL = config["DEFAULT"]["BASE_URL"]
#　スクレイピング対象のURL
LISTING_URL = f"{BASE_URL}" + config["DEFAULT"]["LISTING_URL"]


def get_articles(threshold_date_str):
    """
    指定した日付 (例: "2025-03-25") 以降の記事が取得できるまで、
    「もっと見る」ボタンをクリックし、全ての対象 article タグ（HTML文字列）のリストを返す。
    
    対象の article タグは、以下のいずれかの条件に一致するものとする：
      ・<article id="item-thumbnail-1" class="item item-ordinary">  
      ・<article class="item item-ordinary">
      ・または、<article class="item-ordinary">（"item" クラスがなくても）
    """
    # 閾値日付（タイムゾーンは記事側に合わせる）
    threshold_date = datetime.strptime(threshold_date_str, "%Y-%m-%d")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    
    driver.get(LISTING_URL)
    wait = WebDriverWait(driver, 10)
    # 対象の記事タグが表示されるまで待機（ここではCSSセレクタで複数パターンを指定）
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article.item.item-ordinary, article.item-ordinary")))
    
    while True:
        # 対象の記事タグを抽出（複数のパターンを指定）
        articles = driver.find_elements(By.CSS_SELECTOR, "article.item.item-ordinary, article.item-ordinary")
        if not articles:
            break
        last_article = articles[-1]
        try:
            time_elem = last_article.find_element(By.TAG_NAME, "time")
            pub_date_str = time_elem.get_attribute("datetime")
            if not pub_date_str:
                print("公開日時が取得できませんでした。")
                break
            pub_date = datetime.strptime(pub_date_str, "%Y-%m-%dT%H:%M:%S%z")
            threshold_date_aware = threshold_date.replace(tzinfo=pub_date.tzinfo)
            
            # print(f"[*]最終ページ記事公開日時: {pub_date} (閾値: {threshold_date_aware})")
            
            # 最後の記事の公開日時が閾値よりも前ならループ終了
            if pub_date < threshold_date_aware:
                print("閾値より前の記事が見つかったため、ループを終了します。")
                break
            
            print("[*]「もっと見る」ボタンをクリックして、次のページを取得します。")
            
            try:
                more_button = driver.find_element(By.XPATH, "//a[contains(text(), 'もっと見る')]")
                driver.execute_script("arguments[0].scrollIntoView();", more_button)
                more_button.click()
                wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "article.item.item-ordinary, article.item-ordinary")) > len(articles))
                time.sleep(1)
            except Exception as e:
                print("「もっと見る」ボタンが見つからない、またはクリックに失敗しました。", e)
                break

        except Exception as e:
            print("最後の記事の公開日時取得に失敗しました。", e)
            break

    articles = driver.find_elements(By.CSS_SELECTOR, "article.item.item-ordinary:not(.item-toplistview)")
    article_html_list = [article.get_attribute("outerHTML") for article in articles]
    driver.quit()
    
    return article_html_list


if __name__ == "__main__":
    threshold = "2025-03-29"
    print("[*]URL:", LISTING_URL)
    print("[*]閾値:", threshold)
    print("[*]記事取得を開始します...")
    
    articles_list = get_articles(threshold)
    
    print(f"\n最終的に取得した記事数: {len(articles_list)}")
    
    result = [] # 記事情報を格納するリスト
    tokun_num = 0
    total_articles = len(articles_list)
    
    # 取得した記事を1つずつ処理
    for i, article in enumerate(articles_list[0:5]):
        print(f"\n処理中: {i + 1}/{total_articles}")
        
        # 記事HTMLを解析
        article_dict = ttj.parse_list_article(article)
        
        # 詳細URLを取得
        detail_url = BASE_URL + article_dict["詳細URL"]
        
        # 詳細情報を取得
        print("     [*]記事タイトル:", article_dict["記事タイトル"])
        if detail_url:
            # 詳細情報を取得する関数を呼び出す
            detail_info, tokun = gd.get_detail(detail_url)
            result.append(detail_info)
            tokun_num += tokun
            print("     [*]詳細情報:", detail_info)
            print("     [*]消費したtokun数:", tokun)
            # print(detail_info)
            # ここで詳細情報を処理するコードを書くことができます   

        else:
            print("     [*]詳細URLが取得できませんでした。")

    print("[*]トークン料金:", tokun_num*2.5*150/1000000, "円")
    
    #gmail APIs 
    
    

    
    
    
