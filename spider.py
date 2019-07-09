import os
import re
from hashlib import md5
from multiprocessing import Pool
import pymongo
import requests
from urllib.parse import urlencode
from requests.exceptions import RequestException
import json
from bs4 import BeautifulSoup
from config import *

client = pymongo.MongoClient(MONGO_URL, connect=False)
db = client[MONGO_DB]


def get_page_index(offset, keyword):
    headers = {
        'cookie': 'tt_webid = 6711267168514786823;WEATHER_CITY = % E5 % 8C % 97 % E4 % BA % AC;UM_distinctid = 16bd18ae52d4fe - 08dcc4376eb956 - 3f71045b - 1fa400 - 16bd18ae52ed65;tt_webid = 6711267168514786823;csrftoken = c9953e64d57a075230e53d661012c290;s_v_web_id = c75afae8b202e7e5701b90809a85fd1f;CNZZDATA1259612802 = 1359058011 - 1562585966 - https % 253A % 252F % 252Fwww.google.com % 252F % 7C1562591366;tasessionId = 5mo1x1cym1562592549443'
    }
    data = {
        'aid': '24',
        'app_name': 'web_search',
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
    }
    url = 'https://www.toutiao.com/api/search/content/?'+ urlencode(data)
    try:
        response = requests.get(url, headers = headers)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求索引页出错')
        return None

def parse_page_index(html):
    data = json.loads(html)
    if data and 'data' in data.keys():
        for item in data.get('data'):
            yield item.get('article_url')

def get_page_detail(url):
    headers = {
        'cookie': 'tt_webid = 6711267168514786823;WEATHER_CITY = % E5 % 8C % 97 % E4 % BA % AC;UM_distinctid = 16bd18ae52d4fe - 08dcc4376eb956 - 3f71045b - 1fa400 - 16bd18ae52ed65;tt_webid = 6711267168514786823;csrftoken = c9953e64d57a075230e53d661012c290;s_v_web_id = c75afae8b202e7e5701b90809a85fd1f;CNZZDATA1259612802 = 1359058011 - 1562585966 - https % 253A % 252F % 252Fwww.google.com % 252F % 7C1562591366;tasessionId = 5mo1x1cym1562592549443',
        'user-agent': 'Mozilla / 5.0(X11;Linuxx86_64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 75.0.3770.100Safari / 537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求详情页出错', url)
        return None

def parse_page_detail(html, url):
    soup = BeautifulSoup(html, 'lxml')
    title = soup.select('title')[0].get_text()
    print(title)
    content_pattern = re.compile('content: (.*?),', re.S)
    result = re.search(content_pattern, html)
    images_pattern = re.compile('img src&#x3D;&quot;(.*?)&quot', re.S)
    if result:
        images = re.findall(images_pattern, result.group(1))
        if (images):
            images = [img for img in images]
            for image in images: download_images(image)
            return {
                'title': title,
                'url': url,
                'images': images
            }
    return None

def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功', result)
        return True
    return False

def download_images(url):
    print('正在下载', url)
    headers = {
        'cookie': 'tt_webid = 6711267168514786823;WEATHER_CITY = % E5 % 8C % 97 % E4 % BA % AC;UM_distinctid = 16bd18ae52d4fe - 08dcc4376eb956 - 3f71045b - 1fa400 - 16bd18ae52ed65;tt_webid = 6711267168514786823;csrftoken = c9953e64d57a075230e53d661012c290;s_v_web_id = c75afae8b202e7e5701b90809a85fd1f;CNZZDATA1259612802 = 1359058011 - 1562585966 - https % 253A % 252F % 252Fwww.google.com % 252F % 7C1562591366;tasessionId = 5mo1x1cym1562592549443',
        'user-agent': 'Mozilla / 5.0(X11;Linuxx86_64) AppleWebKit / 537.36(KHTML, likeGecko) Chrome / 75.0.3770.100Safari / 537.36'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            save_images(response.content)
        return None
    except RequestException:
        print('请求图片出错', url)
        return None

def save_images(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd()+'/imgs', md5(content).hexdigest(), 'jpg')
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)
            f.close()

def main(offset):
    html = get_page_index(offset, KEYWORD)
    for url in parse_page_index(html):
        if url:
            html = get_page_detail(url)
            if html:
                result = parse_page_detail(html, url)
                if result:
                    save_to_mongo(result)

if __name__ == '__main__':
    groups = [x*20 for x in range(GROUP_START, GROUP_END)]
    pool = Pool()
    pool.map(main, groups)