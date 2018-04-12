#!/usr/bin/env python3
import os
import tornado.ioloop
import tornado.web
import tornado.log
import queries
import requests
import time

from geopy.geocoders import Nominatim
geolocator = Nominatim()

from jinja2 import \
    Environment, PackageLoader, select_autoescape, TemplateNotFound

ENV = Environment(
    loader=PackageLoader('weather', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)

class TemplateHandler(tornado.web.RequestHandler):
    def initialize(self):
        self.session = queries.Session(
            'postgresql://postgres@localhost:5432/weather')

    def render_template(self, tpl, context):
        template = ENV.get_template(tpl)
        self.write(template.render(**context))

class MainHandler(TemplateHandler):
    def get(self):
        self.set_header(
            'Cache-Control',
            'no-store, no-cache, must-revalidate, max-age=0')
        self.render_template("home.html", {})

    def post(self):
        city = self.get_body_argument('city')
        city = str.lower(city)
        location = geolocator.geocode(city)
        loc = (location.latitude, location.longitude)
        loc = str(loc).strip("()")


        # check if city exists in db
        results = self.session.query(
            'SELECT * FROM weather WHERE city = %(city)s',
            {'city': city}
            )
        if not results:
            # no db entry for this city, do API requst
            print('Requested city no in db, calling API')
            url = "https://api.darksky.net/forecast/MY_API_KEY/{}".format(loc)
            r = requests.get(url)
            data = r.json()

            now = time.time()
            icon = data['currently']['icon']
            summary = data['currently']['summary']
            temperature = data['currently']['temperature']
            humidity = data['currently']['humidity']
            pressure = data['currently']['pressure']
            windspeed = data['currently']['windSpeed']

            results = self.session.query(
                'INSERT INTO weather (city, time, icon, summary, temp, humid, pressure, wind, loc) VALUES (%(city)s, %(now)s, %(icon)s, %(summary)s, %(temperature)s, %(humidity)s, %(pressure)s, %(windspeed)s, %(loc)s)',
                {'city': city,
                 'now': now,
                 'icon': icon,
                 'summary': summary,
                 'temperature': temperature,
                 'humidity': humidity,
                 'pressure': pressure,
                 'windspeed': windspeed,
                 'loc': loc}
                )
        else:
            # db entry for city exists
            lasttime = int(results[0]['time'])
            currtime = time.time()
            if currtime < (lasttime - (15 * 60)):
                # db entry is old & needs deleting
                print('City exists in db but is old, deleting')
                results = self.session.query(
                    'DELETE FROM weather WHERE city = %(city)s',
                    {'city': city}
                    )
                print('Calling API to replace old entry')
                url = "https://api.darksky.net/forecast/MY_API_KEY/{}".format(loc)
                r = requests.get(url)
                data = r.json()

                now = time.time()
                
                icon = data['currently']['icon']
                summary = data['currently']['summary']
                temperature = data['currently']['temperature']
                humidity = data['currently']['humidity']
                pressure = data['currently']['pressure']
                windspeed = data['currently']['windSpeed']

                results = self.session.query(
                    'INSERT INTO weather (city, time, icon, summary, temp, humid, pressure, wind, loc) VALUES (%(city)s, %(now)s, %(icon)s, %(summary)s, %(temperature)s, %(humidity)s, %(pressure)s, %(windspeed)s, %(loc)s)',
                    {'city': city,
                     'now': now,
                     'icon': icon,
                     'summary': summary,
                     'temperature': temperature,
                     'humidity': humidity,
                     'pressure': pressure,
                     'windspeed': windspeed,
                     'loc': loc}
                    )
            else:
                # db entry is still new
                print('DB entry is still valid for city')

        self.redirect('/city/' + city)

class ResultHandler(TemplateHandler):
    def get(self, city):
        results = self.session.query(
            'SELECT * FROM weather WHERE city = %(city)s',
            {'city': city}
            ).items()
        if not results:
            self.redirect('/error')
        else:
            self.render_template("results.html", {'results': results[0]})

class ErrorHandler(TemplateHandler):
    def get(self):
        self.render_template("error.html", {})


def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/city/(.*)", ResultHandler),
        (r"/error", ErrorHandler),
        (r"/static/(.*)",
            tornado.web.StaticFileHandler, {'path': 'static'}),
    ], autoreload=True)

if __name__ == "__main__":
    tornado.log.enable_pretty_logging()
    app = make_app()
    app.listen(int(os.environ.get('PORT', '8080')))
    tornado.ioloop.IOLoop.current().start()
