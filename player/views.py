from django import forms
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import Context, TemplateDoesNotExist
from django.template import RequestContext
from django.template.loader import get_template
from django.views.generic.simple import direct_to_template
from django.conf import settings
from longturn.game.models import Game, Joined
from longturn.player.forms import *
from longturn.player.models import Player
from longturn.poll.models import Poll, Vote
from longturn.views import message
from longturn.main.misc import *
import hashlib
import datetime

@login_required
def myprofile(request):
	maxdate = datetime.datetime(datetime.MAXYEAR, 1, 1)
	joineds = list(Joined.objects.filter(user=request.user))
	joineds.sort(key=lambda x: x.game.date_started or maxdate, reverse=True)
	pending = []
	for j in joineds:
		polls = Poll.objects.filter(game=j.game)
		for p in polls:
			if p.has_ended() == False:
				try:
					Vote.objects.get(poll=p, user=request.user)
				except:
					pending.append(p)
	polls = Poll.objects.filter(game=None)
	for p in polls:
		try:
			Vote.objects.get(poll=p, user=request.user)
		except:
			pending.append(p)

	if request.method == 'POST':
		if 'profile' in request.POST:
			form = ProfileForm(request.POST)
			if form.is_valid():
				password = request.POST['password']
				email = request.POST['email']
				info = request.POST['info']

				user = request.user;
				if password != '':
					user.set_password(password)
					user.get_profile().pass_md5 = hashlib.md5(password).hexdigest()
					user.get_profile().pass_sha1 = hashlib.sha1(password).hexdigest()
				user.email = email
				user.get_profile().info = info
				user.get_profile().save()
				user.save()
				return HttpResponseRedirect("/account/profile")
		elif 'forum_create' in request.POST:
			request.user.get_profile().create_forum_account()
			return HttpResponseRedirect("/account/profile")
		elif 'forum_update' in request.POST:
			a = request.user.get_profile().update_forum_account()
			return HttpResponseRedirect("/account/profile/")
	else:
		form = ProfileForm(
			initial={
				'email': request.user.email,
				'info': request.user.get_profile().info
			})

	return render_to_response(
		"registration/myprofile.html",
		{
			'form': form,
			'polls': pending,
			'joineds': joineds,
		},
		context_instance=RequestContext(request))

@login_required
def profile(request, username):
	maxdate = datetime.datetime(datetime.MAXYEAR, 1, 1)
	try:
		player = User.objects.get(username=username)
	except:
		player = None
	joineds = list(Joined.objects.filter(user=player))
	joineds += getoldjoineds(player)
	olduser = getolduser(player)

	joineds.sort(key=lambda x: x.game.date_started or maxdate, reverse=True)

	if request.method == 'POST':
		form = ContactForm(request.POST)
		if form.is_valid():
			body = request.POST['message']
			send_mail(
				'[longturn] %s, a message from %s!' % (player, request.user),
				body + "\n\n--------\nThis message was sent using the longturn.org contact form."
				+ "\nYou can use the 'reply to' function in your client to answer.",
				request.user.email,
				[player.email, request.user.email],
				fail_silently=False)
			return message(request, "Message to %s has been sent" % player)
	else:
		form = ContactForm()

	return render_to_response(
		"registration/profile.html",
		{
			'olduser': olduser,
			'form': form,
			'player': player,
			'joineds': joineds,
			'username': username,
		},
		context_instance=RequestContext(request))

def register(request):
	if request.method == 'POST':
		form = RegistrationForm(request.POST)
		if form.is_valid():
			username = request.POST['username']
			password = request.POST['password']
			email = request.POST['email']
			user = User.objects.create_user(username, email, password)
			user.is_active = True
			user.save()
			user.get_profile().pass_md5 = hashlib.md5(password).hexdigest()
			user.get_profile().pass_sha1 = hashlib.sha1(password).hexdigest()
			user.get_profile().save()

			auser = auth.authenticate(username=username, password=password)
			auth.login(request, auser)
			return HttpResponseRedirect("/account/profile/")
	else:
		form = RegistrationForm()

	return render_to_response(
		"registration/register.html",
		{
			'form': form,
		},
		context_instance=RequestContext(request))

def players(request, sort):
	reverse = False
	if sort[0] == 'x':
		reverse = True
		sort = sort[1:]

	players = list(User.objects.all())
	if sort == 'username':
		players.sort(key=lambda x: x.username.lower(), reverse=reverse)
	elif sort == 'admin':
		players.sort(key=lambda x: x.is_staff, reverse=reverse)

	return render_to_response(
		"registration/players.html",
		{
			'players': players,
		},
		context_instance=RequestContext(request))
