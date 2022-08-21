from urllib.parse import unquote
from flask import Flask, request
from selenium import webdriver
from bs4 import BeautifulSoup
import requests
import json
import os

app = Flask(__name__)
BASEURL = 'https://m.arabseed.sbs'


@app.route('/')
def index():
    return 'WELCOME TO EGYFLIX'


class Egyflix:
    # get movies, series list
    @app.route('/get/<action>/page=<int:page>')
    def get_data(action, page):
        result = []

        url = '{}/category/{}/?page={}'.format(BASEURL, action, page)
        soup = Egyflix.request(url)

        soup = BeautifulSoup(soup.text, 'html.parser')
        soup = soup.select('.MovieBlock')
        for s in soup:
            name = s.select_one('.BlockName h4').getText().split(
                ' ', 1)[1]
            category = s.select_one('.category').getText()
            image = s.select_one('.Poster img').get('data-src')
            link = s.select_one('a').get('href')
            rating = s.select_one('.RateNumber')
            quality = s.select_one('.Ribbon')

            if quality and rating != None:
                quality = quality.getText()
                rating = rating.getText()
            else:
                quality = ''
                rating = 0

            result.append({'name': name, 'quality': quality,
                          'image': image, 'rating': rating, 'category': category, 'link': link})

        return result

    # search details for movie, series
    @app.route('/search/details/<search>', methods=["GET", "POST"])
    def search_data(search):
        result = {}
        if request.data:
            post = json.loads(request.data)
            if post['link'] != None:
                link = post['link']
        else:
            url = '{}/find/?find={}'.format(BASEURL, search)
            soup = Egyflix.request(url)

            soup = BeautifulSoup(soup.text, 'html.parser')
            soup = soup.select_one('.MovieBlock')

            link = soup.select_one('a').get('href')

        detailsSoup = Egyflix.request(link)
        detailsSoup = BeautifulSoup(detailsSoup.text, 'html.parser')

        result['name'] = detailsSoup.select_one(
            '.Title').getText().split(' ', 1)[1]
        result['category'] = detailsSoup.select_one(
            '.category').getText()
        result['image'] = detailsSoup.select_one('.Poster img').get('data-src')
        result['watch'] = Egyflix.get_links(link + 'download')
        result['story'] = detailsSoup.select(
            '.StoryLine .descrip')[1].getText()

        info = detailsSoup.select('.MetaTermsInfo li')
        for i in info:
            if i.select_one('a').get('href') == 'javascript:void(0)':
                release_date = i.select_one('a').getText()
                result['release_date'] = release_date
            else:
                result[i.select_one('a').get('href').split('/')[3]] = {
                    'name': i.select_one('a').getText(),
                    'link': i.select_one('a').get('href')
                }
                if i.select_one('a').get('href').split('/')[3] == 'genre':
                    genre = []
                    for gen in i.select('a'):
                        genre.append(
                            {'name': gen.getText(), 'link':  gen.get('href')})
                    result['genre'] = genre

        rating = detailsSoup.select_one('.RatingImdb em')
        if rating != None:
            result['rating'] = rating.getText()
        else:
            result['rating'] = 0

        if len(detailsSoup.select('.SeasonsListHolder')) > 0:
            result['seasons'] = Series.get_seasons(link)

        return [result]

    # get watch links for movie, series
    @app.route('/get/links', methods=["GET", "POST"])
    def get_links(link=None):
        if request.data:
            post = json.loads(request.data)
            if post['link'] != None:
                link = post['link']

        soup = Egyflix.request(link)
        soup = BeautifulSoup(soup.text, 'html.parser')

        result = []
        block = soup.select('.DownloadBlock')
        for b in block:
            quality = b.select_one('h3 span').getText()
            ref = b.select_one('a').get('href')
            result.append({'quality': quality, 'link': ref})

        return result

    # request url using scraper api
    def request(link, status='host'):
        if status == 'host':
            payload = {
                'api_key': 'fd37ca458851abfd1350b898184bce77', 'url': link}
            response = requests.get(
                'http://api.scraperapi.com', params=payload)

        if status == 'local':
            response = requests.get(link)

        return response


class Download:
    # get download links for movies, series
    @app.route('/get/download', methods=["GET", "POST"])
    def getDownloadSources(link=None):
        if request.data:
            post = json.loads(request.data)
            if post['link'] != None:
                link = post['link']

        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(executable_path=os.environ.get(
            "CHROMEDRIVER_PATH"), chrome_options=chrome_options)
        driver.get(link)

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        ref = soup.select_one('.plyr__video-wrapper video').get('src')
        image = soup.select_one('.adm-image img').get('src')
        name = soup.select_one('.fsh-header__left').getText()
        result = [{'link': ref, 'image': image, 'name': name}]

        return result


class Series:
    # get seasons of series
    @app.route('/series/seasons', methods=["GET", "POST"])
    def get_seasons(link=None):
        if request.data:
            post = json.loads(request.data)
            if post['link'] != None:
                link = post['link']

        soup = Egyflix.request(link)
        soup = BeautifulSoup(soup.text, 'html.parser')
        result = []

        if len(soup.select('.SeasonsListHolder')) > 0:
            seasons = soup.select('.SeasonsListHolder ul li')
            for s in seasons:
                season = s.select_one('span').getText()
                if season == '':
                    continue
                result.append({'season': season.split(" ")[1]})
        return result

    # get episodes of series
    @app.route('/series/episodes', methods=["GET", "POST"])
    def get_episodes(link=None, season=None):
        if request.data:
            post = json.loads(request.data)
            if post['link'] and post['season'] != None:
                link = post['link']
                season = post['season']

        soup = Egyflix.request(link)
        soup = BeautifulSoup(soup.text, 'html.parser')
        result = []

        seasonLink = soup.select('.BreadCrumbs ol li a')[3].get('href')
        seasonLink = unquote(seasonLink)
        seasonLink = seasonLink[:-1] + '-الموسم-{}'.format(season)

        episodes = soup.select('.ContainerEpisodesList a')
        for ep in episodes:
            epLink = ep.get('href')
            epName = ep.select_one('em').getText()
            result.append({'link': epLink, 'episode': epName})

        return result


class Search:
    # search for movie, series
    @app.route('/search/<search>/page=<int:page>')
    def search(search, page):
        url = '{}/find/?find={}&offset={}'.format(BASEURL, search, page)
        soup = Egyflix.request(url)
        soup = BeautifulSoup(soup.text, 'html.parser')

        result = []
        block = soup.select('.MovieBlock')
        for s in block:
            name = s.select_one('.BlockName h4').getText().split(
                ' ', 1)[1]
            category = s.select_one('.category').getText()
            image = s.select_one('.Poster img').get('data-src')
            link = s.select_one('a').get('href')
            rating = s.select_one('.RateNumber')
            quality = s.select_one('.Ribbon')

            if quality and rating != None:
                quality = quality.getText()
                rating = rating.getText()
            else:
                quality = ''
                rating = 0

            result.append({'name': name, 'quality': quality,
                          'image': image, 'rating': rating, 'category': category, 'link': link})
        searchRes = []
        excludedCategory = ['اغاني اجنبي',
                            'موبايلات', 'برامج كمبيوتر', 'اغاني عربي', 'العاب كمبيوتر']

        pagesNum = len(soup.select('.page-numbers li')) + 1 - 2
        if pagesNum > 0:
            searchRes.append({"pages": pagesNum})
        else:
            searchRes.append({"pages": 1})

        for item in result:
            if item['category'] in excludedCategory:
                continue
            else:
                searchRes.append(item)

        return searchRes


if __name__ == "__main__":
    app.run()
