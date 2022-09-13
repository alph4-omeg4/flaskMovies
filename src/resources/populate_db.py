import bs4
import icu
from datetime import datetime, timedelta
import requests
from flask_restful import Resource

from src import db
from src.services.film_service import FilmService


import threading
# from concurrent.futures.process import ProcessPoolExecutor as PoolExecutor
from concurrent.futures.thread import ThreadPoolExecutor as PoolExecutor

def convert_date(s_date, fmt='d M y'):
    f = icu.SimpleDateFormat(fmt, icu.Locale('ru'))
    # ft = datetime.fromtimestamp(int(f.parse(s_date)))
    ft = datetime.fromtimestamp(0) + timedelta(seconds=f.parse(s_date))
    return ft


def convert_time(time: str) -> float:
    hour, minute = time.split('ч.')
    hour = hour.strip()
    minute = minute.strip('мин.').strip()
    minutes = (60 * int(hour) + int(minute))
    return minutes


class PopulateDB(Resource):
    url = 'https://kino.mail.ru'

    def get(self):
        t0 = datetime.now()
        films_urls = self.get_films_urls()
        films = self.parse_films(films_urls)
        created_films = self.populate_db_with_films(films)
        dt = datetime.now() - t0
        print(f'Done in {dt.total_seconds():.2f} sec.')
        return {'message': f'Database were populated with {len(films)} films in {dt.total_seconds():.2f} sec.'}, 201

    def get_films_urls(self):
        print('Getting film urls', flush=True)
        url = self.url + '/cinema/top/'
        resp = requests.get(url)
        resp.raise_for_status()
        html = resp.text
        soup = bs4.BeautifulSoup(html, features='html.parser')
        movie_containers = soup.find_all('a',
                                         class_='link link_inline link-holder link-holder_itemevent link-holder_itemevent_small')
        movie_links = [movie.attrs['href'] for movie in movie_containers][:10]
        return movie_links

    def parse_films(self, film_urls):
        films_to_create = []
        for url in film_urls:
            url = self.url + url
            print(f'Getting a detailed info about the film - {url}')
            film_content = requests.get(url)
            film_content.raise_for_status()

            html = film_content.text
            soup = bs4.BeautifulSoup(html, features="html.parser")
            title = soup.find('h1', class_="text text_light_promo color_white").text.strip()
            release_date_fetch = list(soup.select(
                'div.table__cell div.p-truncate.p-truncate_ellipsis.js-module.js-toggle__truncate.js-toggle__truncate.js-toggle__truncate-first span.p-truncate__inner.js-toggle__truncate-inner')[
                                    -1].strings)[2]
            release_date = convert_date(release_date_fetch)

            rating = soup.select_one('div.p-movie-rates__item.nowrap span.text.text_bold_huge.text_fixed').string
            description = soup.select_one('span.p-truncate__inner span.text p').text.strip().replace('\xa0', ' ')
            length = convert_time(soup.select_one('div.margin_bottom_20 span.margin_left_40.nowrap').text.strip())
            distributed_by = '%film_studio%'
            # print([title, rating, description, release_date, length, distributed_by])  datetime.now().strftime('%Y-%d-%m')
            print(f'Received information about - {title}', flush=True)
            films_to_create.append(
                {
                    'title': title,
                    'rating': rating,
                    'description': description,
                    'release_date': release_date,
                    'length': length,
                    'distributed_by': distributed_by
                }
            )
        return films_to_create

    @staticmethod
    def populate_db_with_films(films):
        return FilmService.bulk_create_films(db.session, films)


class PopulateDBThreaded(Resource):
    url = 'https://kino.mail.ru'

    def get(self):
        threads = []
        films_to_create = []
        t0 = datetime.now()
        film_urls = self.get_film_urls()
        for film_url in film_urls:
            threads.append(threading.Thread(target=self.parse_films, args=(film_url, films_to_create), daemon=True))
        [t.start() for t in threads]
        [t.join() for t in threads]
        created_films = self.populate_db_with_films(films_to_create)

        dt = datetime.now() - t0
        print(f"Done in {dt.total_seconds():.2f} sec.")
        return {'message': f'Database were populated with {created_films} films in {dt.total_seconds():.2f} sec.'}, 201

    def get_film_urls(self):
        print('Getting film urls', flush=True)
        url = self.url + '/cinema/top/'
        resp = requests.get(url)
        resp.raise_for_status()

        html = resp.text
        soup = bs4.BeautifulSoup(html, features="html.parser")
        movie_containers = soup.find_all('a',
                                         class_='link link_inline link-holder link-holder_itemevent link-holder_itemevent_small')
        movie_links = [movie.attrs['href'] for movie in movie_containers][:10]

        return movie_links

    def parse_films(self, film_url, films_to_create):
        url = self.url + film_url
        print(f'Getting a detailed info about the film - {url}', flush=True)
        film_content = requests.get(url)
        film_content.raise_for_status()

        html = film_content.text
        soup = bs4.BeautifulSoup(html, features="html.parser")
        title = soup.find('h1', class_="text text_light_promo color_white").text.strip()
        release_date_fetch = list(soup.select(
            'div.table__cell div.p-truncate.p-truncate_ellipsis.js-module.js-toggle__truncate.js-toggle__truncate.js-toggle__truncate-first span.p-truncate__inner.js-toggle__truncate-inner')[
                                      -1].strings)[2]
        release_date = convert_date(release_date_fetch)

        rating = soup.select_one('div.p-movie-rates__item.nowrap span.text.text_bold_huge.text_fixed').string
        description = soup.select_one('span.p-truncate__inner span.text p').text.strip().replace('\xa0', ' ')
        length = convert_time(soup.select_one('div.margin_bottom_20 span.margin_left_40.nowrap').text.strip())
        distributed_by = '%film_studio%'
        # print([title, rating, description, release_date, length, distributed_by])  datetime.now().strftime('%Y-%d-%m')
        print(f'Received information about - {title}', flush=True)
        films_to_create.append(
            {
                'title': title,
                'rating': rating,
                'description': description,
                'release_date': release_date,
                'length': length,
                'distributed_by': distributed_by
            }
        )

        return films_to_create

    @staticmethod
    def populate_db_with_films(films):
        return FilmService.bulk_create_films(db.session, films)


class PopulateDBThreadPoolExecutor(Resource):
    url = 'https://kino.mail.ru'

    def get(self):
        t0 = datetime.now()
        film_urls = self.get_film_urls()
        work = []
        with PoolExecutor() as executor:
            for film_url in film_urls:
                f = executor.submit(self.parse_films, film_url)
                work.append(f)
        films_to_create = [f.result() for f in work]
        created_films = self.populate_db_with_films(films_to_create)

        dt = datetime.now() - t0
        print(f"Done in {dt.total_seconds():.2f} sec.")
        return {'message': f'Database were populated with {created_films} films in {dt.total_seconds():.2f} sec.'}, 201

    def get_film_urls(self):
        print('Getting film urls', flush=True)
        url = self.url + '/cinema/top/'
        resp = requests.get(url)
        resp.raise_for_status()

        html = resp.text
        soup = bs4.BeautifulSoup(html, features="html.parser")
        movie_containers = soup.find_all('a',
                                         class_='link link_inline link-holder link-holder_itemevent link-holder_itemevent_small')
        movie_links = [movie.attrs['href'] for movie in movie_containers][:10]

        return movie_links

    def parse_films(self, film_url):
        url = self.url + film_url
        print(f'Getting a detailed info about the film - {url}', flush=True)
        film_content = requests.get(url)
        film_content.raise_for_status()

        html = film_content.text
        soup = bs4.BeautifulSoup(html, features="html.parser")
        title = soup.find('h1', class_="text text_light_promo color_white").text.strip()
        release_date_fetch = list(soup.select(
            'div.table__cell div.p-truncate.p-truncate_ellipsis.js-module.js-toggle__truncate.js-toggle__truncate.js-toggle__truncate-first span.p-truncate__inner.js-toggle__truncate-inner')[
                                      -1].strings)[2]
        release_date = convert_date(release_date_fetch)

        rating = soup.select_one('div.p-movie-rates__item.nowrap span.text.text_bold_huge.text_fixed').string
        description = soup.select_one('span.p-truncate__inner span.text p').text.strip().replace('\xa0', ' ')
        length = convert_time(soup.select_one('div.margin_bottom_20 span.margin_left_40.nowrap').text.strip())
        distributed_by = '%film_studio%'
        # print([title, rating, description, release_date, length, distributed_by])  datetime.now().strftime('%Y-%d-%m')
        print(f'Received information about - {title}', flush=True)
        return {
            'title': title,
            'rating': rating,
            'description': description,
            'release_date': release_date,
            'length': length,
            'distributed_by': distributed_by
        }

    @staticmethod
    def populate_db_with_films(films):
        return FilmService.bulk_create_films(db.session, films)
