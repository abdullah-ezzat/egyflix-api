from base64 import urlsafe_b64decode as decode
from js2py import eval_js as executeJS
from bs4 import BeautifulSoup
from flask import Flask, request
import requests
import urllib
import json
import re

app = Flask(__name__)
BASEURL = "http://www.egy.best"


@app.route('/')
def index():
    return 'WELCOME TO EGYFLIX'


class Egyflix:
    # get movies, series, animes list
    @app.route('/get/<action>/pages=<int:pages>')
    def get_data(action, pages):
        result = []

        for n in range(pages):
            action = action.replace('-', '/')
            url = "{}/{}/?page={}".format(BASEURL, action, n + 1)
            response = Egyflix.request(url)
            soup = BeautifulSoup(response.text, "html.parser")

            movies = soup.select(".movie")
            for movie in movies:
                movieRef = movie.get("href", 0)
                movieName = movie.select_one(".title").getText()
                movieQuality = movie.select_one('.ribbon')
                movieImg = movie.select_one('img').get('src')
                movieRating = movie.select_one('.rating')
                if movieRating and movieQuality != None:
                    movieRating = movieRating.getText()
                    movieQuality = movieQuality.getText()
                else:
                    movieRating = 0
                    movieQuality = 0

                result.append(
                    {"name": movieName, "link": movieRef, 'quality': movieQuality, 'image': movieImg, 'rating': movieRating})

        return result

    # search details for movie, series, anime
    @app.route('/search/details/<search>', methods=["GET", "POST"])
    def search_data(search):
        data = {}

        searchUrl = "{}/explore/?q={}".format(BASEURL, search)
        searchResponse = Egyflix.request(searchUrl)
        searchSoup = BeautifulSoup(searchResponse.text, "html.parser")

        movieResult = searchSoup.select_one(".movie")
        movieAttr = movieResult.get("href", 0)

        if request.data:
            post = json.loads(request.data)
            if post['link'] != None:
                movieAttr = post['link']

        searchResult = Egyflix.request(movieAttr)
        movieSoup = BeautifulSoup(searchResult.text, "html.parser")

        movieName = movieSoup.select_one(
            ".movie_title").getText().split(' (')[0]
        movie_quality = movieSoup.select_one('.ribbon').getText()
        date = movieSoup.select_one('.movie_title h1 a').getText()
        img = movieSoup.select_one('.movie_img > a > img').get('src')
        rating = movieSoup.select_one(
            '.rating').next_sibling.next_sibling.getText()
        video = movieSoup.select_one('.play').get('url')
        videoImg = movieSoup.select_one('img.video').get('src')
        story = movieSoup.select('.pda')[3].getText(' / ')

        if (searchResult.url.split("/")[3] == 'movie'):
            genre = []
            movieGenre = movieSoup.select_one('table.movieTable')
            duration = movieGenre.select('tr')[5].select(
                'td')[1].getText()

            movieGenre = movieGenre.select('tr')[3].select(
                'td')[1].select('a')
            for mg in movieGenre:
                genre.append({'name': mg.getText(), 'link': mg.get('href')})

            data = {
                'name': movieName,
                'release_date': date,
                'quality': movie_quality,
                'image': img,
                'genre': genre,
                'duration': duration,
                'rating': rating,
                'link': movieAttr,
                'video': video,
                'videoImg': videoImg,
                'story': story,
                'type': searchResult.url.split("/")[3]
            }

        else:
            genre = []
            movieGenre = movieSoup.select_one('table.movieTable')
            movieGenre = movieGenre.select('tr')[3].select(
                'td')[1].select('a')
            for mg in movieGenre:
                genre.append(
                    {'name': mg.getText(), 'link': mg.get('href')})

            seasons = []
            seasonsSoup = movieSoup.select('.movies_small')[0].select('.movie')
            for s in seasonsSoup:
                seasons.append({'link': s.get('href'), 'name': s.select_one(
                    '.title').getText(), 'image': s.select_one('img').get('src'), 'season': int(s.get('href').split("/")[4].split('-')[4])})
            totalSeasons = seasonsSoup[0].get(
                'href').split("/")[4].split('-')[4]

            data = {
                'name': movieName,
                'release_date': date,
                'quality': movie_quality,
                'image': img,
                'rating': rating,
                'link': movieAttr,
                'video': video,
                'videoImg': videoImg,
                'story': story,
                'genre': genre,
                'seasons': seasons,
                'total': totalSeasons,
                'type': searchResult.url.split("/")[3]
            }

        return data

    # get watch, dowload links for movie, series, anime
    @app.route('/get/links', methods=["GET", "POST"])
    def get_links():
        baseURL = "http://www.egy.best"
        if request.data:
            post = json.loads(request.data)
            if post['link'] != None:
                link = post['link']

        soup = Egyflix.request(link)
        soup = BeautifulSoup(soup.text, 'html.parser')

        watch = Download().getDownloadSources(link)
        play = baseURL + soup.select_one(".auto-size").get("src")

        movieQualities = soup.select('.dls_table > tbody > tr')
        for i, mq in enumerate(reversed(movieQualities)):
            size = mq.select_one(
                'td').nextSibling.nextSibling.nextSibling.getText()
            quality = mq.select_one(
                'td').nextSibling.nextSibling.getText()
            quality = re.findall(r'\d+', quality)[0]

            fileName = watch[i]['name']
            name_idx = fileName.index("p.mp4")
            fileLink = watch[i]['link']
            link_idx = fileLink.index("p.mp4")

            watch[i]['size'] = size
            watch[i]['quality'] = int(quality)
            watch[i]['link'] = fileLink[:link_idx] + \
                quality + fileLink[link_idx:]
            watch[i]['name'] = fileName[:name_idx] + \
                quality + fileName[name_idx:]

        return {'watch': watch, 'play': play}

    # request url using scraper api
    def request(link, status='host'):
        if status == 'host':
            payload = {
                'api_key': 'fd37ca458851abfd1350b898184bce77', 'url': link}
            response = requests.get(
                'http://api.scraperapi.com', params=payload)

        if status == 'local':
            response = requests.get(link, proxies=urllib.request.getproxies())

        return response


class Download:
    # get download links for movies, series, animes
    def getDownloadSources(self, link):
        data = []
        baseLink = link.split("/")[0] + "//" + link.split("/")[2]

        try:
            session = requests.Session()

            page = requests.get(link).text
            soup = BeautifulSoup(page, features="html.parser")

            vidstreamURL = baseLink + soup.select_one('.auto-size').get("src")
            vidstreamResponseText = session.get(vidstreamURL).text
            videoSoup = BeautifulSoup(
                vidstreamResponseText, features="html.parser")

            try:
                qualityLinksFileURL = baseLink + \
                    videoSoup.select_one("source").get("src")

            except AttributeError:
                jsCode = str(videoSoup.find_all("script")[1])

                verificationToken = str(re.findall(
                    "\{'[0-9a-zA-Z_]*':'ok'\}", jsCode)[0][2:-7])
                encodedAdLinkVar = re.findall(
                    "\([0-9a-zA-Z_]{2,12}\[Math", jsCode)[0][1:-5]
                firstEncodingArray = re.findall(
                    ",[0-9a-zA-Z_]{2,12}=\[\]", jsCode)[1][1:-3]
                secondEncodingArray = re.findall(
                    ",[0-9a-zA-Z_]{2,12}=\[\]", jsCode)[2][1:-3]

                jsCode = re.sub(
                    "^<script type=\"text/javascript\">", "", jsCode)
                jsCode = re.sub("[;,]\$\('\*'\)(.*)$", ";", jsCode)
                jsCode = re.sub(
                    ",ismob=(.*)\(navigator\[(.*)\]\)[,;]", ";", jsCode)
                jsCode = re.sub("var a0b=function\(\)(.*)a0a\(\);", "", jsCode)
                jsCode += "var link = ''; for (var i = 0; i <= " + secondEncodingArray + \
                    "['length']; i++) { link += " + firstEncodingArray + "[" + secondEncodingArray + \
                    "[i]] || ''; } return [link, " + \
                    encodedAdLinkVar + "[0]] }"

                jsCodeReturn = executeJS(jsCode)()
                verificationPath = jsCodeReturn[0]
                encodedAdPath = jsCodeReturn[1]

                adLink = baseLink + "/" + \
                    str(decode(encodedAdPath + "=" *
                        (-len(encodedAdPath) % 4)), "utf-8")
                session.get(adLink)
                verificationLink = baseLink + "/tvc.php?verify=" + verificationPath
                session.post(verificationLink, data={verificationToken: "ok"})

                vidstreamResponseText = session.get(vidstreamURL).text
                videoSoup = BeautifulSoup(
                    vidstreamResponseText, features="html.parser")

                qualityLinksFileURL = baseLink + \
                    videoSoup.select_one("source").get("src")

            qualityLinks = session.get(qualityLinksFileURL).text
            qualityLinksArray = qualityLinks.split("\n")[1::]

            for i in range(0, len(qualityLinksArray)-2, 2):
                fileName = link.split(
                    "/")[4] + "-" + "p.mp4"
                mediaLink = requests.utils.quote(qualityLinksArray[i+1], safe=":/").replace(
                    "_", "%5F").replace("/stream/", "/dl/").replace("/stream.m3u8", f"/{fileName}")
                data.append(
                    {'link': mediaLink, 'name': fileName})
        finally:
            return data


class Series:
    # get episodes of series
    @app.route('/series/episodes', methods=["GET", "POST"])
    def get_episodes():
        if request.data:
            post = json.loads(request.data)
            if post['link'] != None:
                link = post['link']

        soup = Egyflix.request(link)
        soup = BeautifulSoup(soup.text, 'html.parser')

        episodes = []
        epSoup = soup.select('.movies_small')[0].select('.movie')
        for s in epSoup:
            episodes.append({'link': s.get('href'), 'name': s.select_one(
                '.title').getText(), 'image': s.select_one('img').get('src'), 'episode': int(s.get('href').split('ep-')[1].split('/')[0])})
        return episodes


class Search:
    # search for movie, series, anime
    @app.route('/search/<search>')
    def search(search):
        result = []
        baseURL = "http://www.egy.best"
        url = "{}/explore/?q={}".format(baseURL, search)

        response = Egyflix.request(url)
        soup = BeautifulSoup(response.text, "html.parser")

        movies = soup.select(".movie")
        for movie in movies:
            movieRef = movie.get("href", 0)
            movieName = movie.select_one(".title").getText()
            movieQuality = movie.select_one('.ribbon')
            movieImg = movie.select_one('img').get('src')
            movieRating = movie.select_one('.rating')
            if movieRating and movieQuality != None:
                movieRating = movieRating.getText()
                movieQuality = movieQuality.getText()
            else:
                movieRating = 0
                movieQuality = 0

            result.append(
                {"name": movieName, "link": movieRef, 'quality': movieQuality, 'image': movieImg, 'rating': movieRating})
        return result


if __name__ == '__main__':
    app.run()
