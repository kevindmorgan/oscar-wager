from google.appengine.api import mail

from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.conf import settings

from wager.forms import WagerForm, UserForm, PickForm
from wager.models import Wager, User, Award


def index(request):
    if request.method == 'POST':
        wager_form = WagerForm(data=request.POST)
        if wager_form.is_valid():
            wager = wager_form.save()
            return redirect('wager', slug=wager.slug)
    else:
        wager_form = WagerForm()
    return render_to_response('index.html', {'wager_form': wager_form}, context_instance=RequestContext(request))


def wager(request, slug):
    wager = get_object_or_404(Wager, slug=slug)
    users = wager.users.all()
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        if user_form.is_valid():
            user = User(name=user_form.cleaned_data['name'], email=user_form.cleaned_data['email'], wager=wager)
            user.save()
            mail.send_mail(sender="Oscar Wager Team <team@oscar-wager.appspotmail.com>",
                           to="%s" % user.email,
                           subject="Oscar Wager - %s" % user.wager.name,
                           body="""
Hi %s,

You've signed up to be part of an awesome Oscar wager!

Choose your films wisely young Padawan and eat your greens.

Here's the link to your Oscar wager: http://%s/%s/pick/%s/%s/ (keep this secret!).

Thanks,
The Oscar Wager team""" % (user.name, settings.ROOT_URL, user.wager.slug, user.slug, user.hash))
            return redirect('pick', wager_slug=wager.slug, user_slug=user.slug, user_hash=user.hash)
    else:
        user_form = UserForm()
    return render_to_response('wager.html', {'wager': wager, 'user_form': user_form, 'ROOT_URL': settings.ROOT_URL, 'users': users}, context_instance=RequestContext(request))


def pick(request, wager_slug, user_slug, user_hash, pick_id=None):
    wager = get_object_or_404(Wager, slug=wager_slug)
    user = get_object_or_404(User, slug=user_slug, hash=user_hash, wager=wager)
    awards = set(Award.objects.all())
    picks = user.picks.all()
    pick_form = PickForm()
    if request.method == 'POST':
        pick_form = PickForm(data={'user': user.id, 'wager': wager.id, 'entry': request.POST.get('winner')})
        if pick_form.is_valid():
            pick_form.save()
    picked_awards = set([pick.entry.award for pick in picks])
    user_picks = [(pick.entry.award, pick.entry) for pick in picks]
    not_picked_awards = list(awards - picked_awards)
    if len(not_picked_awards) == 0:
        return render_to_response('pick_overview.html', {'wager': wager, 'user': user, 'picks': picks})
    award = not_picked_awards[0]
    entries = award.entries.all()
    entries[0].getCachedEntry()
    context = {'wager': wager,
                'user': user,
                'award': award,
                'entries': entries,
                'pick_form': pick_form,
                'awards_total': len(awards),
                'picked_total': len(picked_awards) + 1,
                'user_picks': user_picks,
                'not_picked_awards': not_picked_awards[1:]}
    return render_to_response('pick.html', context, context_instance=RequestContext(request))
