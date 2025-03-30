import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import configparser
import json
import re

config = configparser.ConfigParser()
config.read("config.ini")

client = OpenAI(api_key=config["DEFAULT"]["OPENAI_API_KEY"])
MODEL = config["DEFAULT"]["MODEL"]
 
 
# 詳細URLから記事の詳細，企業情報，カテゴリー情報を取得する関数
def get_detail(url):
    """
    指定されたURLからHTMLを取得し、企業情報とカテゴリー情報をパースして辞書形式で返す。
    """
    # 企業情報を取得
    company_info = parce_company_details(url)
    
    # カテゴリー情報を取得
    category_info = parce_category_details(url)
    
    # プレスリリースの詳細情報をGPT APIを用いて取得
    press_release_info, tokun_num = details_inf(url)

    # 結果をまとめる
    return {**company_info, **category_info, **press_release_info}, tokun_num
  

# 企業情報を取得する関数
def parce_company_details(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; YourScraper/1.0)"
    }
    # 指定URLからHTMLを取得
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # HTTPエラーがあれば例外発生
    soup = BeautifulSoup(response.text, "html.parser")

    # クラス属性が "table_container__cTu_r table_screen__WRwml" の<dl>を検索
    # 会社概要が記載されているクラス名
    dl_tag = soup.find("dl", class_="table_container__cTu_r table_screen__WRwml")
    

    # 結果用の辞書を初期化
    result = {
        "企業名": "",
        "企業HP": "",
        "電話番号": "",
        "住所": ""
    }

    # <dl> 内の <dt> と <dd> のペアを取得
    # dt_dd_pairs は [(dt要素, dd要素), ...] のリストになる
    dt_tags = dl_tag.find_all("dt")
    dd_tags = dl_tag.find_all("dd")

    # dt_tags と dd_tags の順序が対応していると仮定して進める
    # （実際のHTMLでは <dt> と <dd> の順番が正しくペアになっているはず）
    for dt_tag, dd_tag in zip(dt_tags, dd_tags):
        dt_text = dt_tag.get_text(strip=True)
        dd_text = dd_tag.get_text(strip=True)

        if dt_text == "URL":
            # URL→企業HP
            # aタグがあれば、hrefまたはテキストのどちらを格納するかは要件次第
            a_tag = dd_tag.find("a")
            if a_tag and a_tag.has_attr("href"):
                result["企業HP"] = a_tag["href"]
            else:
                # なければ dd_text 全体を入れる
                result["企業HP"] = dd_text

        elif dt_text == "本社所在地":
            result["住所"] = dd_text.replace("\n", " ")

        elif dt_text == "電話番号":
            result["電話番号"] = dd_text
    
    # 企業名は <dl> タグの外にある <a> タグから取得
    company_name_tag = soup.find("a", class_="company-name_companyName__xoNVA")
    
    result["企業名"] = company_name_tag.get_text(strip=True) if company_name_tag else ""

    return result


# 企業カテゴリを取得する関数
def parce_category_details(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; YourScraper/1.0)"
    }
    # 指定URLからHTMLを取得
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # HTTPエラーがあれば例外発生
    soup = BeautifulSoup(response.text, "html.parser")

    # クラス属性が "<dl class="table_table__GbIoE table_tableScreen__p3URt">" の<dl>を検索
    # カテゴリーが記載されているクラス名
    dl_tag = soup.find("dl", class_="table_table__GbIoE table_tableScreen__p3URt")

    # キーワードのみ抽出する
    # 結果を格納する辞書
    result = {
        "種類": "",
        "ビジネスカテゴリ": [],
        "キーワード": []
    }

    # <dl> の中にある複数の <div class="table_row__O3IbK ..."> が1行に相当
    rows = dl_tag.find_all("div", class_="table_row__O3IbK table_rowScreen__inKSh")
    
    for row in rows:
        dt_tag = row.find("dt", class_="table_term__ym03J")
        dd_tag = row.find("dd", class_="table_definition__03NU_")
        if not dt_tag or not dd_tag:
            continue
        
        key_text = dt_tag.get_text(strip=True)
        # 例：「種類」「ビジネスカテゴリ」「キーワード」
        
        if key_text == "種類":
            # 例：「その他」
            # <span class="table_item__NmAWQ"><a href=...>その他</a></span>
            # → a タグのテキストを取得
            a_tag = dd_tag.find("a")
            if a_tag:
                result["種類"] = a_tag.get_text(strip=True)

        elif key_text == "ビジネスカテゴリ":
            # 複数のカテゴリがある場合も想定 => <span><a>カテゴリ</a></span> が複数
            # ここでは1件か複数かにかかわらず同じ書き方で対応
            span_tags = dd_tag.find_all("span", class_="table_item__NmAWQ")
            categories = []
            for span in span_tags:
                a_tag = span.find("a")
                if a_tag:
                    categories.append(a_tag.get_text(strip=True))
            result["ビジネスカテゴリ"] = categories
        
        elif key_text == "キーワード":
            # 複数キーワードがある場合 => <span><a>キーワード</a></span> が複数
            keywords = []
            span_tags = dd_tag.find_all("span", class_="table_item__NmAWQ")
            for span in span_tags:
                a_tag = span.find("a")
                if a_tag:
                    keywords.append(a_tag.get_text(strip=True))
            result["キーワード"] = keywords
        
        else:
            # 「関連リンク」など、今回不要な行はスキップ
            pass

    return result


# プレスリリースの詳細情報を取得する関数
def fetch_press_release_text(url):
    """
    指定URLからHTMLを取得し、<div id="press-release-body">のテキストを全て抽出して返す。
    ※ メールはGPT-4に抽出させるため、HTML解析では検索しない。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; YourScraper/1.0)"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # <div id="press-release-body"> のテキストを取得
    body_div = soup.find("div", id="press-release-body")
    article_text = body_div.get_text(separator="\n").strip() if body_div else ""

    return article_text


def summarize_and_extract_email_with_gpt4(article_text, approx_length=100, counter=0, token_num=0):
    """
    GPT-4 を用いて、以下の2つを行う:
      1) 文章をおよそ `approx_length` 文字で要約
      2) 文章中にメールアドレスがあれば抜き出し、なければ空白を返す

    戻り値: (summary, email)
    """
    if counter >= 3:
        print("[EEROR] GPTからの応答に3回失敗しました。")
        return "", ""
    
    
    # システムメッセージ（ロール:system）
    system_message = (
        "あなたは優秀な日本語文章の要約者かつ、文中からメールアドレスを見つける能力を備えています。"
        "指示に従い、文章を短く要約し、メールがあれば返し、なければ空白を回答してください。"
    )

    # ユーザーメッセージ（ロール:user）。すべての文章を丸ごと渡す。
    user_message = f"""
以下の文章を要約し、約{approx_length}文字の日本語要約を作成してください。
また、文章中にメールアドレスが含まれていればそれを返し、なければ空白を返してください。

出力はJSON形式とし、
  {{
    "詳細": "<要約文>",
    "メール": "<メールアドレス or 空白>"
  }}
の構造を厳守してください。

文章:
{article_text}
"""

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "developer", "content": system_message},
            {"role": "user", "content": user_message}
        ],
    )

    return_data = completion.choices[0].message.content.replace("json", "").replace("```", "")
    
    # print("[*]使用したトークン総数:",completion.usage.total_tokens)
    
    try:
        json_data = json.loads(return_data)
        return json_data["詳細"], json_data["メール"], token_num + completion.usage.total_tokens 
    except:
        print("[EEROR]GPTからの応答に問題がありました。もう一度実行します。")
        print("[*]応答内容:", return_data)
        return summarize_and_extract_email_with_gpt4(article_text, counter=counter+1, token_num=token_num + completion.usage.total_tokens)
    

# 詳細情報を取得する関数(OpenAI APIを使用)
def details_inf(url):
    # 取得対象のURL
    # url = "https://prtimes.jp/main/html/rd/p/000000251.000120285.html"  # 例

    # 1) HTMLを取得し、<div id="press-release-body">のテキストをまるごと抽出
    article_text = fetch_press_release_text(url).strip()
    article_text = re.sub(r"\s+", " ", article_text)  # 余分な空白を削除
   
    # 2) GPT-4で要約とメール抽出
    summary, email, tokun_num = summarize_and_extract_email_with_gpt4(article_text, approx_length=100)

    # 3) 結果を最終JSON構造へ
    result = {
        "詳細": summary,
        "メール": email
    }

    return result, tokun_num

