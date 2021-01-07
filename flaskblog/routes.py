import secrets, os
from PIL import Image
from flask import render_template, redirect, flash, request, url_for, abort
from flaskblog import app, db, bcrypt, mail
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, BlogPostForm, RequestResetForm, ResetPasswordForm
from flaskblog.models import User, BlogPost
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message

@app.route('/')
def index():
    return render_template('index.html')
# this is your home page, index template needs to be adjusted for what youre going to do / any links to include

@app.route('/posts', methods = ['GET','POST'])
def posts():
    #all_posts = BlogPost.query.order_by(BlogPost.date_posted).all()
    page = request.args.get('page', 1, type=int)
    posts = BlogPost.query.order_by(BlogPost.date_posted.desc()).paginate(per_page=7, page=page)
    return render_template('posts.html', posts=posts)


@app.route('/post/<int:post_id>')
def post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


@app.route('/posts/delete/<int:id>')
def delete(id):
    post = BlogPost.query.get_or_404(id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect('/posts')

@app.route('/posts/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit(id):
    post = BlogPost.query.get_or_404(id)
    if post.author != current_user:
        abort(403)
    form = BlogPostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect('/posts')
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('new_post.html', form=form, legend='Update Post')


@app.route('/posts/new', methods=['GET','POST'])
@login_required
def new_post():
    form = BlogPostForm()
    if form.validate_on_submit():
        post = BlogPost(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect('/posts')
    return render_template('new_post.html', form=form, legend='New Post')


#@app.route('/properties')
#This is where we will be getting and posting the list of available properties for clients to view
#They can click into each one and provide feedback










def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender='noreply@demo.com', recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
    {url_for('reset_token', token=token, _external=True)}
If you did not make this request then please ignore this email. No change will be made      
'''
    mail.send(msg)


@app.route('/reset_password', methods=['GET','POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect('/')
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('Email has been sent with instructions to reset password.', 'info')
        return redirect('/login')
    return render_template('reset_request.html', form=form, title='Reset Password')

@app.route('/reset_password/<token>', methods=['GET','POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect('/')
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or Expired Token', 'warning')
        return redirect('/reset_request')
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_password
        db.session.commit()
        flash(f'Account password for {form.username.data} has been updated! You can now login with these credentials.', 'success')
        return redirect('/login')
    return render_template('reset_token.html', form=form, title='Reset Password')