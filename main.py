import os
import re
import random
import hashlib
import hmac
from string import letters

import webapp2
import jinja2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)

secret = 'uiopl2846dkkuc8'


def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

# Securing userID cookie string


def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())


def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

# Validating users input

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")


def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")


def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE = re.compile(r'^[\S]+@[\S]+\.[\S]+$')


def valid_email(email):
    return not email or EMAIL_RE.match(email)

# Main Handler


class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    # Handling secured cookie for user authentication
    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    # User login, setting secured cookie
    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    # User logout, erasing cookie
    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))


def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)

# Main page with list of posts


class MainPage(BlogHandler):
    def get(self):
        posts = greetings = Post.all().order('-created')
        if self.user:
            self.render('blog_front.html', posts=posts,
                        username=self.user.name)
        else:
            self.render('blog_front.html', posts=posts)


def make_salt(length=5):
    return ''.join(random.choice(letters) for x in xrange(length))


def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)


def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

# Defining User model


def users_key(group='default'):
    return db.Key.from_path('User', group)


class User(db.Model):
    name = db.StringProperty(required=True)
    pw_hash = db.StringProperty(required=True)
    email = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent=users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    @classmethod
    def register(cls, name, pw, email=None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent=users_key(),
                    name=name,
                    pw_hash=pw_hash,
                    email=email)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u


# Defining Post model


def post_key(name='default'):
    return db.Key.from_path('blogs', name)


class Post(db.Model):
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    author = db.ReferenceProperty(User, required=True)
    comment_count = db.IntegerProperty()
    like_count = db.IntegerProperty()

    @classmethod
    def by_id(cls, uid):
        return Post.get_by_id(uid, parent=post_key())

    # Lookup post's author entity
    def author_user(self):
        return User.get_by_id(self.author.key().id(), parent=users_key())

    # Render the post entity with author's name to display
    def render(self, username=''):
        self._render_text = self.content.replace('\n', '<br>')

        can_like = False
        if username:
            u = User.by_name(username)
            if u:
                l = self.like_post_collection.filter('author =', u).fetch(1)
                if not l:
                    can_like = True

        likes = self.like_post_collection.order('created').fetch(20)
        like_str = ''
        for l in likes:
            like_str = like_str + l.author_user().name + ' '
        return render_str("blog_post.html", p=self,
                          post_id=str(self.key().id()),
                          username=username,
                          like_str=like_str,
                          can_like=can_like)


# Defining Comment model


def comment_key(name='default'):
    return db.Key.from_path('blog_comments', name)


class Comment(db.Model):
    comment = db.TextProperty(required=True)
    author = db.ReferenceProperty(User, required=True)
    post = db.ReferenceProperty(Post, collection_name='post_collection',
                                required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    moderated = db.BooleanProperty(default=False)

    @classmethod
    def by_id(cls, uid):
        return Comment.get_by_id(uid, parent=comment_key())

    # Lookup comment's author entity
    def author_user(self):
        return User.get_by_id(self.author.key().id(), parent=users_key())

    # Render the comment entity to display
    def render(self, username=''):
        self._render_text = self.comment.replace('\n', '<br>')
        return render_str("blog_comment.html", p=self,
                          comment_id=str(self.key().id()),
                          post_id=str(self.post.key().id()),
                          username=username)


# Defining Like model for future usage


def like_key(name='default'):
    return db.Key.from_path('Like', name)


class Like(db.Model):
    author = db.ReferenceProperty(User, required=True)
    post = db.ReferenceProperty(Post, collection_name='like_post_collection',
                                required=True)
    created = db.DateTimeProperty(auto_now_add=True)

    @classmethod
    def by_id(cls, uid):
        return Like.get_by_id(uid, parent=like_key())

    def author_user(self):
        return User.get_by_id(self.author.key().id(), parent=users_key())

    def render(self, username=''):
        return render_str("blog_like.html", p=self,
                          like_id=str(self.key().id()),
                          post_id=str(self.post.key().id()),
                          username=username)


class BlogFront(BlogHandler):
    def get(self):
        posts = greetings = Post.all().order('-created')
        if self.user:
            self.render('blog_front.html', posts=posts,
                        username=self.user.name)
        else:
            self.render('blog_front.html', posts=posts)


# Display a post with comment


class PostPage(BlogHandler):
    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id), parent=post_key())
        posted = db.get(key)

        # if post is not found, redirect to error page
        if not posted:
            self.redirect('/error?code=no_post_found')
            return

        # Getting post's first 100 comments
        post_comment = db.get(key)
        comments = post_comment.post_collection.order('-created').fetch(100)
        likes = post_comment.like_post_collection.order('created').fetch(1000)

        if self.user:
            self.render("blog_permalink.html", posted=posted,
                        comments=comments,
                        likes=likes,
                        post_id=post_id,
                        username=self.user.name)
        else:
            self.render("blog_permalink.html", posted=posted,
                        comments=comments,
                        likes=likes,
                        post_id=post_id)

    def post(self, post_id):
        if not self.user:
            return self.redirect('/login')

        comment_id = self.request.get('comment_id')

        if comment_id:
            c = Comment.by_id(int(comment_id))
            # Check the comment existing
            if c:
                # Check that the user try to delete his/her own post
                if (self.user.name == c.author_user().name):
                    c.delete()
                    return self.redirect('/%s' % post_id)
                else:
                    return self.redirect('/error?code=no_right')
        else:
            return self.redirect('/')


# Add new post or edit an existing one


class NewPost(BlogHandler):
    def get(self):
        if self.user:
            # if getting a post_id, then edit, else render a blank one
            post_id = self.request.get('post_id')
            if post_id:
                p = Post.by_id(int(post_id))
                if (self.user.name == p.author_user().name):
                    self.render("blog_newpost.html",
                                username=self.user.name,
                                subject=p.subject,
                                content=p.content,
                                post_id=post_id)
            else:
                self.render("blog_newpost.html", username=self.user.name)
        else:
            self.redirect("/")

    def post(self):
        if not self.user:
            return self.redirect('/login')

        post_id = self.request.get('post_id')
        subject = self.request.get('subject')
        content = self.request.get('content')

        if subject and content:

            # if getting a post_id, then edit, else add a new one

            if post_id:
                p = Post.by_id(int(post_id))
                p.subject = subject
                p.content = content
            else:
                p = Post(parent=post_key(), subject=subject,
                         content=content, author=self.user)
            p.put()

            # Redirect to the edited or newly added post

            self.redirect('/%s' % str(p.key().id()))
        else:
            error = "subject and content, please!"
            self.render("blog_newpost.html",
                        subject=subject,
                        content=content,
                        error=error,
                        username=self.user.name)


# Handling deleting a post with confirmation


class DeletePost(BlogHandler):
    def get(self):
        if self.user:
            post_id = self.request.get('post_id')
            if post_id:
                # Check the post existing
                p = Post.by_id(int(post_id))
                if p:
                    # Check that the user try to delete his/her own post
                    if (self.user.name == p.author_user().name):
                        self.render("blog_delete.html",
                                    username=self.user.name,
                                    subject=p.subject,
                                    content=p.content,
                                    post_id=post_id)
                    else:
                        self.redirect('/error?code=no_right')
                else:
                    self.redirect('/error?code=no_post_found')
            else:
                self.redirect('/error?code=no_post_found')
        else:
            return self.redirect('/error?code=you_should_login')

    def post(self):
        if not self.user:
            return self.redirect('/error?code=you_should_login')

        post_id = self.request.get('post_id')
        if post_id:
            p = Post.by_id(int(post_id))
            # Check the post existing
            if p:
                # Check that the user try to delete his/her own post
                if (self.user.name == p.author_user().name):
                    p.delete()
                    self.redirect('/')
                else:
                    return self.redirect('/error?code=no_right')
            else:
                return self.redirect('/error?code=no_post_found')
        else:
            return self.redirect('/error?code=no_post_found')


class DeleteComment(BlogHandler):
    def get(self):
        if self.user:
            comment_id = self.request.get('comment_id')
            post_id = self.request.get('post_id')
            if (comment_id and post_id):
                # Check the comment existing
                p = Post.by_id(long(post_id))
                com = Comment.get_by_id(long(comment_id), parent=p)
                if com:
                    # Check that the user try to delete his/her own comment
                    if (self.user.name == com.author_user().name):
                        self.render("blog_delete_comment.html",
                                    username=self.user.name,
                                    comment=com.comment,
                                    post_id=post_id,
                                    comment_id=comment_id)
                    else:
                        return self.redirect('/error?code=no_right')
                else:
                    return self.redirect('/error?code=no_comment_found')
            else:
                return self.redirect('/error?code=no_comment_found')
        else:
            return self.redirect('/error?code=you_should_login')

    def post(self):
        if not self.user:
            return self.redirect('/error?code=you_should_login')

        post_id = self.request.get('post_id')
        comment_id = self.request.get('comment_id')
        if (post_id and comment_id):
            p = Post.by_id(long(post_id))
            c = Comment.get_by_id(long(comment_id), parent=p)
            # Check the comment existing
            if c:
                # Check that the user try to delete his/her own comment
                if (self.user.name == c.author_user().name):
                    c.delete()

                    p.comment_count = p.comment_count - 1
                    p.put()

                    return self.redirect('/%s' % post_id)
                else:
                    return self.redirect('/error?code=no_right')
            else:
                return self.redirect('/error?code=no_comment_found')
        else:
            return self.redirect('/error?code=no_comment_found')


class EditComment(BlogHandler):
    def get(self):
        if self.user:
            comment_id = self.request.get('comment_id')
            post_id = self.request.get('post_id')
            if (comment_id and post_id):
                # Check the comment existing
                p = Post.by_id(long(post_id))
                com = Comment.get_by_id(long(comment_id), parent=p)
                if com:
                    # Check that the user try to delete his/her own comment
                    if (self.user.name == com.author_user().name):
                        self.render("blog_edit_comment.html",
                                    username=self.user.name,
                                    comment=com.comment,
                                    post_id=post_id,
                                    comment_id=comment_id)
                    else:
                        return self.redirect('/error?code=no_right')
                else:
                    return self.redirect('/error?code=no_comment_found')
            else:
                return self.redirect('/error?code=no_comment_found')
        else:
            return self.redirect('/error?code=you_should_login')

    def post(self):
        if not self.user:
            return self.redirect('/error?code=you_should_login')

        post_id = self.request.get('post_id')
        comment_id = self.request.get('comment_id')
        comment_content = self.request.get('comment_content')
        if (post_id and comment_id):
            p = Post.by_id(long(post_id))
            c = Comment.get_by_id(long(comment_id), parent=p)
            # Check the comment existing
            if c:
                # Check that the user try to delete his/her own comment
                if (self.user.name == c.author_user().name):
                    c.comment = comment_content
                    c.put()

                    return self.redirect('/%s' % post_id)
                else:
                    return self.redirect('/error?code=no_right')
            else:
                return self.redirect('/error?code=no_comment_found')
        else:
            return self.redirect('/error?code=no_comment_found')


# Adding new comment


class NewComment(BlogHandler):
    def post(self):
        if not self.user:
            return self.redirect('/error?code=you_should_login')

        post_id = self.request.get('post_id')
        comment_content = self.request.get('comment_content')

        if post_id and comment_content:
            post = Post.by_id(int(post_id))

            p = Comment(parent=post.key(),
                        post=post,
                        comment=comment_content,
                        author=self.user)
            p.put()

            # Increasing post's comment counter

            if post.comment_count:
                post.comment_count = post.comment_count + 1
            else:
                post.comment_count = 1
            post.put()

            self.redirect('/%s' % post_id)
        else:
            error = "Content, please!"
            self.redirect('/%s?comment_content=%s&error=%s' %
                          (post_id, comment_content, error))


# Adding new like


class NewLike(BlogHandler):
    def post(self):
        if not self.user:
            return self.redirect('/error?code=you_should_login')

        post_id = self.request.get('post_id')

        if post_id:
            post = Post.by_id(int(post_id))

            if (post.author_user() == self.user):
                return self.redirect('/error?code=cannot_like_own_post')

            l = post.like_post_collection.filter(
                    'author =',
                    self.user).fetch(1)

            if l:
                return self.redirect('/error?code=you_already_like_it')
            else:
                new_like = Like(parent=post.key(),
                                post=post,
                                author=self.user)
                new_like.put()

                # Increasing post's comment counter

                if post.like_count:
                    post.like_count = post.like_count + 1
                else:
                    post.like_count = 1
                post.put()

            return self.redirect('/%s' % post_id)
        else:
            return self.redirect('/error?code=no_post_found')


# Delete like


class DeleteLike(BlogHandler):
    def post(self):
        if not self.user:
            return self.redirect('/error?code=you_should_login')

        post_id = self.request.get('post_id')
        like_id = self.request.get('like_id')

        if post_id and like_id:
            post = Post.by_id(int(post_id))
            l = Like.get_by_id(long(like_id), parent=post)

            if post and l:
                l.delete()
                post.like_count = post.like_count - 1
                post.put()

                return self.redirect('/%s' % post_id)

            else:
                return self.redirect('/error?code=no_like_found')

        else:
            return self.redirect('/error?code=no_post_found')


# New user signup


class Signup(BlogHandler):
    def get(self):
        self.render("blog_signup.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username=self.username,
                      email=self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('blog_signup.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError


class Register(Signup):
    def done(self):
        # Make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('blog_signup.html', error_username=msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u)
            self.redirect('/welcome')


# User login


class Login(BlogHandler):
    def get(self):
        self.render('blog_login.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        # using User's login procedure
        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/')
        else:
            msg = 'Invalid login'
            return self.render('blog_login.html', error=msg)


# User logout


class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/')


# New user Welcome


class Welcome(BlogHandler):
    def get(self):
        if self.user:
            self.render('blog_welcome.html', username=self.user.name)
        else:
            return self.redirect('/signup')


# Error page


class ErrorPage(BlogHandler):
    def get(self):
        code = self.request.get('code')

        if self.user:
            self.render('blog_error.html',
                        code=code,
                        username=self.user.name)
        else:
            self.render('blog_error.html', code=code)


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/?', BlogFront),
                               ('/([0-9]+)', PostPage),
                               ('/newpost', NewPost),
                               ('/delete', DeletePost),
                               ('/del_com', DeleteComment),
                               ('/edit_com', EditComment),
                               ('/newcomment', NewComment),
                               ('/editcomment', NewComment),
                               ('/like', NewLike),
                               ('/del_like', DeleteLike),
                               ('/signup', Register),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/welcome', Welcome),
                               ('/error', ErrorPage)
                               ],
                              debug=True)
