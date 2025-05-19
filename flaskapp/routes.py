from flask import render_template, flash, redirect, url_for, request
from flaskapp import app, db
from flaskapp.models import BlogPost, IpView, Day, UkData
from flaskapp.forms import PostForm
import datetime

import pandas as pd
import json
import plotly
import plotly.express as px


# Route for the home page, which is where the blog posts will be shown
@app.route("/")
@app.route("/home")
def home():
    # Querying all blog posts from the database
    posts = BlogPost.query.all()
    return render_template('home.html', posts=posts)


# Route for the about page
@app.route("/about")
def about():
    return render_template('about.html', title='About page')


# Route to where users add posts (needs to accept get and post requests)
@app.route("/post/new", methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = BlogPost(title=form.title.data, content=form.content.data, user_id=1)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form)


# Route to the dashboard page
@app.route('/dashboard')
def dashboard():
    days = Day.query.all()
    df = pd.DataFrame([{'Date': day.id, 'Page views': day.views} for day in days])

    fig = px.bar(df, x='Date', y='Page views')

    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('dashboard.html', title='Page views per day', graphJSON=graphJSON)

@app.route('/student_conservative')
@app.route('/student_conservative')
def student_conservative():
    # Query data from database
    uk_data = UkData.query.all()
    
    # Prepare data for visualization with error handling
    constituencies = []
    student_percentages = []
    conservative_votes = []
    
    for item in uk_data:
        # Only include items with valid data
        if (item.c11FulltimeStudent is not None and 
            item.ConVote19 is not None and 
            item.TotalVote19 is not None and 
            item.TotalVote19 > 0):
            
            constituencies.append(item.constituency_name)
            student_percentages.append(item.c11FulltimeStudent)
            conservative_votes.append(item.ConVote19 / item.TotalVote19 * 100)
    
    # Create the data structure directly for Plotly.js
    data = [{
        'x': student_percentages,
        'y': conservative_votes,
        'mode': 'markers',
        'type': 'scatter',
        'text': constituencies,
        'name': 'Constituencies'
    }]
    
    layout = {
        'title': 'Relationship Between Student Population and Conservative Vote Share',
        'xaxis': {'title': 'Full-time Student Population (%)'},
        'yaxis': {'title': 'Conservative Vote Share (%)'},
        'hovermode': 'closest'
    }
    
    # Package the data and layout together
    fig = {'data': data, 'layout': layout}
    
    # Convert to JSON
    graphJSON = json.dumps(fig)
    
    return render_template('uk_viz.html', title='UK Student Population vs Conservative Vote', 
                          graphJSON=graphJSON)

@app.route('/regional_party_comparison')
@app.route('/regional_party_comparison')
def regional_party_comparison():
    # Query data from database
    uk_data = UkData.query.all()
    
    # Prepare data for regional analysis with error handling
    region_data = {}
    
    for item in uk_data:
        # Skip items with invalid data
        if (item.region is None or 
            item.ConVote19 is None or 
            item.LabVote19 is None or 
            item.TotalVote19 is None):
            continue
            
        if item.region not in region_data:
            region_data[item.region] = {
                'con_votes': 0, 
                'lab_votes': 0, 
                'total_votes': 0
            }
        
        region_data[item.region]['con_votes'] += item.ConVote19
        region_data[item.region]['lab_votes'] += item.LabVote19
        region_data[item.region]['total_votes'] += item.TotalVote19
    
    # Calculate percentages
    regions = []
    con_percentages = []
    lab_percentages = []
    
    for region, votes in sorted(region_data.items()):
        if votes['total_votes'] > 0:
            regions.append(region)
            con_percentages.append(votes['con_votes'] / votes['total_votes'] * 100)
            lab_percentages.append(votes['lab_votes'] / votes['total_votes'] * 100)
    
    # Create the data structure directly for Plotly.js
    data = [
        {
            'x': regions,
            'y': con_percentages,
            'type': 'bar',
            'name': 'Conservative',
            'marker': {'color': 'blue'}
        },
        {
            'x': regions,
            'y': lab_percentages,
            'type': 'bar',
            'name': 'Labour',
            'marker': {'color': 'red'}
        }
    ]
    
    layout = {
        'title': 'Conservative vs Labour Vote Share by UK Region',
        'xaxis': {'title': 'UK Region'},
        'yaxis': {'title': 'Vote Share (%)'},
        'barmode': 'group'
    }
    
    # Package the data and layout together
    fig = {'data': data, 'layout': layout}
    
    # Convert to JSON
    graphJSON = json.dumps(fig)
    
    return render_template('uk_viz.html', title='Regional Party Comparison', 
                          graphJSON=graphJSON)

@app.before_request
def before_request_func():
    day_id = datetime.date.today()  # get our day_id
    client_ip = request.remote_addr  # get the ip address of where the client request came from

    query = Day.query.filter_by(id=day_id)  # try to get the row associated to the current day
    if query.count() > 0:
        # the current day is already in table, simply increment its views
        current_day = query.first()
        current_day.views += 1
    else:
        # the current day does not exist, it's the first view for the day.
        current_day = Day(id=day_id, views=1)
        db.session.add(current_day)  # insert a new day into the day table

    query = IpView.query.filter_by(ip=client_ip, date_id=day_id)
    if query.count() == 0:  # check if it's the first time a viewer from this ip address is viewing the website
        ip_view = IpView(ip=client_ip, date_id=day_id)
        db.session.add(ip_view)  # insert into the ip_view table

    db.session.commit()  # commit all the changes to the database
