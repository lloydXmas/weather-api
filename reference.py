#!/usr/bin/env python3
import os
import tornado.ioloop
import tornado.web
import tornado.log
import queries
import requests

from jinja2 import \
    Environment, PackageLoader, select_autoescape

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
  def get (self):
    posts = self.session.query('SELECT * FROM post')
    self.render_template("home.html", {'posts': posts})

class AuthorsHandler(TemplateHandler):
    def get (self):
      author = self.session.query('SELECT * FROM author')
      self.render_template("authors.html", {'authors': author})

class AuthorPostHandler(TemplateHandler):
  def get(self, id):
    titles = self.session.query(
      'SELECT * FROM post JOIN author ON author.id = post.author_id WHERE author.id = %(id)s',
      {'id': id}
      )
    print(titles[0]['name'])
    self.render_template("author.html", {'titles': titles})


class BlogPostHandler(TemplateHandler):
  def get (self, slug):
    posts = self.session.query(
     'SELECT * FROM post WHERE slug = %(slug)s',
      {'slug': slug}
    ).items()

    comments = self.session.query(
      'SELECT comment.comment FROM comment JOIN post ON post.id = comment.post_id WHERE slug = %(slug)s',
      {'slug': slug}
      ).items()
    for r in comments:
      print (r)

    author = self.session.query(
      'SELECT * FROM author JOIN post ON post.author_id = author.id WHERE post.slug = %(slug)s',
      {'slug': slug}
      ).items()
    context = {
      'post': posts[0],
      'author': author[0],
      'comments': comments
    }
    self.render_template("post.html", context)


class CommentHandler(TemplateHandler):
  def get (self, slug):
    posts = self.session.query(
      'SELECT * FROM post WHERE slug = %(slug)s',
      {'slug': slug}
    )
    self.render_template("comment.html", {'post': posts[0]})

  def post (self, slug):
    comment = self.get_body_argument('comment')
    posts = self.session.query(
      'SELECT * FROM post WHERE slug = %(slug)s',
      {'slug': slug}
    )
    blog_id = (posts[0]['id'])
    add_comment = self.session.query(
      'INSERT INTO comment (post_id, comment) VALUES (%(blog_id)s, %(comment)s)',
      {'blog_id': blog_id, 'comment': comment}
	  )
    self.redirect('/post/' + slug)


def make_app():
  return tornado.web.Application([
    (r"/", MainHandler),
    (r"/authors", AuthorsHandler),
    (r"/author/(.*)", AuthorPostHandler),
    (r"/post/(.*)/comment", CommentHandler),
    (r"/post/(.*)", BlogPostHandler),
    (r"/static/(.*)",
      tornado.web.StaticFileHandler, {'path': 'static'}),
  ], autoreload=True)

if __name__ == "__main__":
  tornado.log.enable_pretty_logging()
  app = make_app()
  app.listen(int(os.environ.get('PORT', '8080')))
  tornado.ioloop.IOLoop.current().start()
