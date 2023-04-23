from datetime import date
from functools import wraps
from flask import Flask, render_template, redirect, url_for, flash,g,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_login import UserMixin, LoginManager, current_user,login_user,logout_user,login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from forms import CreatePostForm, RegisterForm, LoginForm,CommentForm
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship,declarative_base
from flask_gravatar import Gravatar


Base = declarative_base()
app = Flask(__name__)
app.app_context().push()
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)


##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


##CONFIGURE TABLES
class User(UserMixin, db.Model):#parent
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(1000), nullable=False)
    # The "posts" attribute for the User object is a list.
    # This list defines the relationship and it can be empty or contain zero or many objects.
    # To add a post to a user you'll define a user object, a post object and append the post object to user.posts.
    # The back_populates allows you to get the user object from a post object (post.user).
    # With back_populates, both sides of the relationship are defined explicitly
    # Create reference to the BlogPost class - "author" refers to the author property in the BlogPost class
    # posts is a "pseudo column" in this "users" table
    # For example, you could use user.posts to retrieve the list of posts that user has created
    posts =db.relationship("BlogPost",back_populates='author')
    #add relationship to Comment:
    comments=db.relationship('Comment',back_populates="comment_author")

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

class BlogPost(db.Model):#child
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # Create ForeignKey "users.id" - refers to the tablename of User class
    # ForeignKey refers to the primary key in the other *table* (users)
    # author_id is a real column in this "blog_posts" table
    # Without the ForeignKey, the relationships would not work.
    author_id=db.Column(db.Integer,db.ForeignKey('users.id'))
    # Create reference to the User class - "posts" refers to the posts property in the User class
    # author is a "pseudo column" in this "blog_posts" table
    # For example, you could use blog_post.author to retrieve the user who created the post
    author=db.relationship('User',back_populates='posts')
    #add relationship to Comment:
    comments=db.relationship('Comment',back_populates='parent_post')

class Comment(db.Model):
    __tablename__="comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    #relationship with User
    comment_author=db.relationship('User',back_populates='comments')
    author_id=db.Column(db.Integer,db.ForeignKey('users.id'))
    #relationship with BlogPost
    parent_post=db.relationship('BlogPost',back_populates='comments')
    post_id=db.Column(db.Integer,db.ForeignKey('blog_posts.id'))


db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id==1:
            return f(*args, **kwargs)
        else:
            return abort(403)
    return decorated_function

#def login_required(f):
#    @wraps(f)
#    def decorated_function(*args, **kwargs):
#        if current_user.is_authenticated:
#            return f(*args, **kwargs)
#        else:
#            flash("please login first",'error')
#            return redirect(url_for('login'))
#    return decorated_function



@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html",all_posts=posts)#logged_in=current_user.is_authenticated)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('You already have an account, please login!','error')
            return redirect(url_for('login'))

        safe_password = generate_password_hash(form.password.data,
                                               method='pbkdf2:sha256',
                                               salt_length=8)

        new_user = User(

            email=form.email.data,
            password=safe_password,
            name=form.name.data
        )
        db.session.add(new_user)
        db.session.commit()
        #login user
        login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form,logged_in=current_user.is_authenticated)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("That email does not exist, please try again.",'error')
            return redirect(url_for("login"))
        elif not check_password_hash(user.password, password):
            flash("please check your password",'error')
            return redirect(url_for("login"))
        else:
            #login user
            login_user(user)
            return redirect(url_for("get_all_posts"))

    return render_template("login.html", form=form,logged_in=current_user.is_authenticated)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=["GET", "POST"])
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to make comment",'error')
            return redirect(url_for('login'))
        new_comment=Comment(
            text=comment_form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post,
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html", post=requested_post,current_user=current_user,form=comment_form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,current_user=current_user)


@app.route("/edit-post/<int:post_id>",methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,

        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data

        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=False)
