import secrets, os
from PIL import Image
from flask import render_template, redirect, flash, request, url_for, abort
from flaskblog import app, db, bcrypt, mail
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, BlogPostForm, RequestResetForm, ResetPasswordForm, ApartmentForm, ApartmentScoreForm
from flaskblog.models import User, BlogPost, Apartment, ApartmentScore
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message
from flaskblog.scrape import gen_title_link

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

@app.route('/properties', methods = ['GET','POST'])
def properties():
    page = request.args.get('page', 1, type=int)
    properties = Apartment.query.order_by(Apartment.date_posted.desc()).paginate(per_page=7, page=page)
    return render_template('properties.html', properties=properties)


@app.route('/property/rate/<int:property_id>', methods = ['GET','POST'])
@login_required
def rate_property(property_id):
    form = ApartmentScoreForm()
    property = Apartment.query.get_or_404(property_id)
    # perform check to see if this user has submitted for this property already
    list_of_submitted_scores = property.scores
    for score in list_of_submitted_scores:
        if score.author.email == current_user.email:
            flash('You have already rated this property.', 'danger')
            return redirect('/properties')
    if form.validate_on_submit():
        score = ApartmentScore(location_score=form.location_score.data, price_score=form.price_score.data, title=property, author=current_user)
        db.session.add(score)
        db.session.commit()
        flash('Your rating has been submitted!', 'success')
        #this next portion is just for gathering the admins to send email notifications to of a new rating submitted
        admins = User.query.filter_by(admin=True)
        recipients = []
        for user in admins:
            recipients.append(user.email)
        msg = Message('Your posted location has been rated', sender='noreplytestingflask@demo.com', recipients=recipients)
        msg.body = f'''New rating has been submitted for {property.title} by {score.author}. Please login to view.'''
        mail.send(msg)
        return redirect('/properties')
    return render_template('property_rate.html', form=form, title=property.title, property=property)
    

@app.route('/property/new', methods=['GET','POST'])
@login_required
def new_property():
    if current_user.admin:
        form = ApartmentForm()
        if form.validate_on_submit():
            property = Apartment(title=form.title.data, link=form.link.data, monthly_cost=form.monthly_cost.data, city=form.city.data)
            db.session.add(property)
            db.session.commit()
            flash('Your property has been listed!', 'success')
            return redirect('/properties')
        return render_template('new_property.html', form=form, legend='New Property')
    else:
        flash('Only Admins can list properties!', 'danger')
        return redirect('/properties')


@app.route('/property/ratings', methods=['GET'])
@login_required
def view_ratings():
    if current_user.admin:
        scores = ApartmentScore.query.order_by(ApartmentScore.date_posted.desc())
        cache = {}
        for score in scores:
            if score.title.title in cache:
                cache[score.title.title][0].append(score.location_score)
                cache[score.title.title][1].append(score.price_score)
            else:
                cache[score.title.title] = [[score.location_score],[score.price_score]]
        averages = []
        for title,ratings in cache.items():
            averages.append((title,sum(ratings[0])/len(ratings[0]),sum(ratings[1])/len(ratings[1])))
        return render_template('view_ratings.html', averages=averages)
    else:
        flash('Only Admins can list properties!', 'danger')
        return redirect('/properties')



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


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect('/')
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, highest_rent=form.highest_rent.data, admin=False)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}! You can now login with these credentials.', 'success')
        return redirect('/login')
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user,remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect('/')
        else:
            flash('Login failed, incorrect login info', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')



@app.route('/account', methods=['GET','POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.highest_rent = form.highest_rent.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect('/account')
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


@app.route('/user/<string:username>', methods = ['GET','POST'])
def user_posts(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = BlogPost.query.filter_by(author=user)\
        .order_by(BlogPost.date_posted.desc())\
        .paginate(per_page=7, page=page)
    return render_template('user_posts.html', posts=posts, user=user)


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    f_name,f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path,'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return picture_fn

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender='noreplytestingflask@demo.com', recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then please ignore this email. No change will be made      
'''
    mail.send(msg)


@app.route('/reset_password', methods=['GET', 'POST'])
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


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
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
        flash(f'Account password for {user.email} has been updated! You can now login with these credentials.', 'success')
        return redirect('/login')
    return render_template('reset_token.html', form=form, title='Reset Password')


@app.route('/binghamton_mls_scraped', methods=['GET', 'POST'])
def view_binghamton():
    if current_user.admin:
        pairs = gen_title_link()
        return render_template('binghamtonmls_scraped.html', pairs=pairs)
    else:
        flash('You do not have the necessary entitlements to view.', 'warning')
        return redirect('/properties')