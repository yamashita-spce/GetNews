import json
import requests
from bs4 import BeautifulSoup


def article_to_json(article_html):
    """
    1つの記事HTMLから、サムネイル形式 or リスト形式でパース方法を分岐し、
    結果を指定形式の辞書にまとめて返す。
    """
    soup = BeautifulSoup(article_html, "html.parser")

    # サムネイル形式かどうかを .thumbnail-title-wrap の有無で判断
    if soup.select_one(".thumbnail-title-wrap"):
        # サムネイル形式
        return parse_thumbnail_article(soup)
    else:
        # それ以外 → リスト形式とみなす
        return parse_list_article(soup)

def parse_list_article(article_html):
    
    """
    1つの記事HTML（文字列）から、指定された形式の辞書を作成して返す。
    例：
    <article class="item item-ordinary">
      <div class="thumbnail-title-wrap">
          <a class="link-thumbnail link-thumbnail-ordinary" href="/main/html/rd/p/000000251.000120285.html" title="「ハタラクエール2025」で最高位の「優良福利厚生法人（総合）」を受賞" style="background-image: url(&quot;/i/120285/251/thumb/118x78/d120285-251-67c233e3b53398c9742e-0.jpg&quot;);"></a>
          <h3 class="title-item title-item-ordinary">
            <a class="link-title-item link-title-item-ordinary thumbnail-title" href="/main/html/rd/p/000000251.000120285.html">「ハタラクエール2025」で最高位の「優良福利厚生法人（総合）」を受賞</a>
          </h3>
      </div>
      <a class="link-name-company name-company name-company-ordinary" href="/main/html/searchrlp/company_id/120285">三菱電機株式会社</a>
      <time class="time-release time-release-ordinary icon-time-release-svg" datetime="2025-03-28T17:38:28+09:00">2025年3月28日 17時38分</time>
    </article>
    """
    
    soup = BeautifulSoup(article_html, "html.parser")

    # タイトル取得
    # 例：<h3 class="title-item ..."><a class="link-title-item link-title-item-ordinary thumbnail-title" ...>タイトル</a></h3>
    title_anchor = soup.select_one("h3.title-item a")
    title = title_anchor.get_text(strip=True) if title_anchor else ""

    # 詳細URL （タイトルの a タグの href）
    detail_url = title_anchor["href"] if title_anchor and title_anchor.has_attr("href") else ""

    # 企業概要URL：企業名のリンク (<a class="link-name-company ...">) の href
    company_anchor = soup.select_one("a.link-name-company")
    company_url = company_anchor["href"] if company_anchor and company_anchor.has_attr("href") else ""

    # 公開日：<time> タグの datetime 属性
    time_tag = soup.find("time")
    pub_date = time_tag["datetime"] if time_tag and time_tag.has_attr("datetime") else ""

    # 以下、まだ取得していない情報は空文字
    article_info = {
        "記事タイトル": title,
        "詳細": "",
        "詳細URL": detail_url,
        "企業概要URL": company_url,
        "公開日": pub_date,
        "企業名": "",
        "企業HP": "",
        "メール": "",
        "電話番号": "",
        "住所": "",
        "種類": "",
        "ビジネスカテゴリ": [],
        "キーワード": [],
    }

    return article_info
    

def parse_thumbnail_article(article_html):
    """
    単一の <article> HTML を解析し、指定の情報を辞書形式で返す。
    
    <article> の例:
    <article id="item-thumbnail-1" class="item item-ordinary">
      <div class="thumbnail-title-wrap">
        <a id="thumbnail-id-63326_286" href="/main/html/rd/p/000000286.000063326.html" class="link-thumbnail link-thumbnail-ordinary" style="background-image:url(...)" title="大人気の《炙り寿司》 ... します！">
        </a>
        <h3 class="title-item title-item-ordinary">
          <a href="/main/html/rd/p/000000286.000063326.html" class="link-title-item link-title-item-ordinary thumbnail-title">
            大人気の《炙り寿司》！3月31日(月)～平日5日間限定！小僧寿し『炙り三昧フェア』を開催します！
          </a>
        </h3>
      </div>
      <time datetime="2025-03-30T20:00:08+0900" class="time-release ...">
        12分前
      </time>
      <a href="/main/html/searchrlp/company_id/63326" class="link-name-company name-company name-company-ordinary thumbnail-name-company" title="KOZOホールディングスのプレスリリース">
        KOZOホールディングス
      </a>
    </article>
    """
    soup = article_html
    
    # 記事タイトル：<h3> 内の <a>テキスト
    title_tag = soup.select_one("h3.title-item a")
    article_title = title_tag.get_text(strip=True) if title_tag else ""
    
    # 詳細URL
    detail_url = title_tag.get("href") if title_tag and title_tag.has_attr("href") else ""
    
    # 企業概要URL：企業リンク (クラス .link-name-company)
    company_tag = soup.select_one("a.link-name-company")
    company_url = company_tag.get("href") if company_tag and company_tag.has_attr("href") else ""
    
    # 公開日 (datetime属性)
    time_tag = soup.select_one("time")
    publication_date = time_tag.get("datetime") if time_tag else ""
    
    # 以下は一覧ページには無い、または後で取得想定なので空文字
    company_name = ""         # 企業名
    detail = ""               # 記事詳細（一覧上には無い）
    company_hp = ""           # 企業HP
    mail = ""                 # メール
    address = ""              # 住所
    phone = ""                # 電話番号
    release_type = ""         # 種類
    
    # JSON形式 (Python辞書)
    article_info = {
        "記事タイトル": article_title,
        "詳細": detail,
        "詳細URL": detail_url,
        "企業概要URL": company_url,
        "公開日": publication_date,
        "企業名": company_name,
        "企業HP": company_hp,
        "メール": mail,
        "電話番号" : phone,
        "住所": address,
        "種類": release_type,
        "ビジネスカテゴリ": [],
        "キーワード": [],
    }
    
    return article_info
