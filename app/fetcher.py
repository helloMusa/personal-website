from math import ceil
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import requests
import json
import praw
from app import db
from app.models import Post, Fetch


sched = BackgroundScheduler()


class BackgroundFetcher():
	""" Class which allows data to be fetched from APIs in the background. """
	def __init__(self, fetch_list=None):
		"""
		Args:
			fetch_list (list): List of data fetched via API calls
		"""
		self.fetch_list = []

	def fetch_all(self):
		""" Populates fetch_list using necessary functions and stores in database """
		self.fetch_list = [github_fetcher(), blog_fetcher(), reddit_fetcher()]
		fetch = Fetch.query.first()
		fetch.repo_title, fetch.repo_time = self.fetch_list[0]
		fetch.blog_title, fetch.blog_url = self.fetch_list[1]
		fetch.comment_url, fetch.comment_time = self.fetch_list[2]
		db.session.commit()

	def background_scheduler(self):
		""" Starts the BackgroundScheduler with a 10 second interval between executions """
		sched.add_job(self.fetch_all, 'interval', seconds=10)
		sched.start()


def db_to_list():
	"""
	Turns database entries into list

	Returns:
		fetch_list (list): List of data stored in database, fetched via API calls
	"""
	fetch = Fetch.query.first()
	fetch_list = [fetch.repo_title, fetch.repo_time,
				  fetch.blog_title, fetch.blog_url,
				  fetch.comment_url, fetch.comment_time]
	return fetch_list


def get_post(post_title):
	"""
	Gets post from database given title of blog post

	Args:
		post_title (string): Title of given blog post

	Returns:
		post (database row): Title, subtitle, content, and date posted of given blog post
	"""
	db_titles = [post.title.replace(" ", "-") for post in Post.query.all()]

	if post_title not in db_titles:
		return redirect(url_for('home'))

	post_title = post_title.replace("-", " ")
	post = Post.query.filter_by(title=post_title).first()

	return post


def get_time_difference(current_time, new_time, var):
	"""
	Gets the difference between two times for a certain inquiry

	Args:
		current_time (datetime object): Current time in UTC
		new_time (datetime object): Time of latest comment/commit/blog post in UTC
		var (string): Either the latest repo or latest comment

	Returns:
		return_list (list): List of repo name/comment permalink and the time since latest commit/comment
	"""
	return_list = [var]
	difference = current_time - new_time
	minutes = difference.seconds//60
	hours = minutes//60
	days = difference.days
	minutes -= 60*hours

	if days > 1: # If total days greater than 1, display days
		return_list.append(f'{days} days')
	elif (60*hours + minutes) < 60: # If total minutes is less than 60, display minutes
		return_list.append(f'{minutes} minutes')
	else: # If total minutes is greater than 60, display hours
		return_list.append(f'{ceil(hours)} hours')

	return return_list


def github_fetcher():
	"""
	Gets latest GitHub commit

	Returns:
		return_list (list): List of repo name and time since latest commit

	"""	
	with open('tokens.txt', 'r') as f: # Get token from .txt file
		token = f.readline().strip()

	url = 'https://api.github.com/users/hellomusa/repos'
	github_token = token
	params = {'access_token': github_token}

	response = requests.get(url, params=params)

	repo_names = []
	commits = {}

	if response:
		data = json.loads(response.content)

		# Get each repository name
		for repo in data:
			repo_names.append(repo['full_name'][10:])

		# Get each commit time for repos in repo list
		for repo_name in repo_names:
			commit_url = f'https://api.github.com/repos/hellomusa/{repo_name}/commits/master'
			response = requests.get(commit_url, params=params)

			if response:
				data = json.loads(response.content)
				commit_date = data['commit']['author']['date']
				commit_date_dt = datetime.strptime(commit_date, "%Y-%m-%dT%H:%M:%SZ")
				commits[repo_name] = commit_date_dt
			else:
				print('INVALID RESPONSE')

		# Compare current time with latest commit time, return the difference
		commit_times = [commits[repo] for repo in commits]
		newest_commit_time = max(commit_times)

		newest_commit_repo = ''
		for repo in commits:
			if commits[repo] == newest_commit_time:
				newest_commit_repo = repo

		current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
		current_time_dt = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")

		return_list = get_time_difference(current_time_dt, newest_commit_time, newest_commit_repo)

		return return_list

	else:
		print('INVALID RESPONSE')


def blog_fetcher():
	"""
	Gets latest blog post from website blog

	Returns:
		return_list (list): List of blog post title and its URL
	"""
	latest_post = Post.query.all()[-1]
	post_title = latest_post.title
	post_url = post_title.replace(" ", "-")
	return_list = [post_title, post_url]

	return return_list


def reddit_fetcher():
	"""
	Gets latest Reddit comment

	Returns:
		return_list (list): List of comment permalink and time since comment
	"""
	with open('tokens.txt', 'r') as f:
		f.readline()
		f.readline()
		CLIENT_ID = f.readline().strip()
		CLIENT_SECRET = f.readline().strip()

	reddit = praw.Reddit(user_agent='Comment Extraction by /u/hellomusa', 
						client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

	user = reddit.redditor('hellomusa')
	comments = [comment for comment in user.comments.new()]
	latest_comment = comments[0]
	link_permalink = latest_comment.permalink
	comment_date = datetime.utcfromtimestamp(latest_comment.created_utc)

	current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
	current_time_dt = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")

	return_list = get_time_difference(current_time_dt, comment_date, link_permalink)

	return return_list



