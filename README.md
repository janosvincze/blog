# A simple blog
## Contents
1. User's manual
  * The link of the blog
  * Home page
  * After login
  * A post's page
2. Developer's manual

## User's manual
### The link of the blog
You can found the working blog at the following link:
[http://engineapp-vj-blog.appspot.com/](https://engineapp-vj-blog.appspot.com/)
### Home page
Before you signup and/or login, you can see the following layout: 
![alt text][without_login_picture]

If you do not have an acount, please use the [Signup](https://engineapp-vj-blog.appspot.com/signup) link on the navigation section to create a new one. Fill out the registration form. After successfully submitting it, you will be logged in.

If you already have an acount, please use [Login](https://engineapp-vj-blog.appspot.com/login) link on the navigation section. 
Use the login form as appropriate.

### After login
After you succesfully login, you can see the following layout:
![alt text][after_login_picture]

After logging in, you can:
  * Create a New post
  * Edit your own posts
  * Delete your own posts

Just following the link as it shown above.

### A post's page

Click a post's title to reach its page.
![alt text][post_page_picture]

You can add a new comment. Fill the blank text area and click the submit button.

## Developer's manual

### Used technology
  * Google App Engine
  * Google Cloud Datastore
  * Python
  * Jinja
  * Html
  * CSS

### Structure

The main python file: [main.py](https://github.com/janosvincze/blog/blob/master/main.py)
The templates files: [templates](https://github.com/janosvincze/blog/tree/master/templates)

### Entities
#### User entity

Storing users' name, password's hash and email address.

#### Post entity

Storing posts' title, content, creation time, author (refering to User entity) and comments counter.

#### Comment entity

Storing comments' content, creation time and author (refering to User entity).






[without_login_picture]: https://github.com/janosvincze/blog/blob/master/screenshots/without_login.png "Home page"
[after_login_picture]: https://github.com/janosvincze/blog/blob/master/screenshots/base.png "Home page after login"
[post_page_picture]: https://github.com/janosvincze/blog/blob/master/screenshots/post.png "A post's page"

