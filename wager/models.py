import urllib
import urllib2
import uuid
import hashlib

from django.utils import simplejson
from django.db import models
from django.core.cache import cache
from django.template.defaultfilters import slugify


def generate_token():
    """ Genereates unique token hash."""
    return uuid.uuid4().bytes.encode('base64').replace('+', '').replace('/', '').strip('=\n')[:4]


class Wager(models.Model):
    """Wager model detailing the agreement of participants."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(db_index=True, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)

    def save(self):
        """Override save to slugify the name to form the URL."""
        self.slug = slugify(self.name)
        super(Wager, self).save()


class User(models.Model):
    """User model detailing the name and email address of the users in a wager."""
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=320)
    slug = models.SlugField(db_index=True)
    hash = models.CharField(max_length=4, default=generate_token)
    wager = models.ForeignKey(Wager, related_name='users')

    class Meta:
        unique_together = ('name', 'email', 'wager')

    def save(self):
        self.slug = slugify(self.name)
        super(User, self).save()

    def _gravatar_url(self):
        email = hashlib.md5(self.email.lower()).hexdigest()
        return 'http://www.gravatar.com/avatar/%s?size=48' % email

    gravatar_url = property(_gravatar_url)


class Award(models.Model):
    """Award model detailing the name of the award."""
    name = models.CharField(max_length=50)


class Entry(models.Model):
    """Entry model detailing the name of the entry(film, actor)
       and a reference of where/why nominated(film, director)."""
    name = models.CharField(max_length=50)
    award = models.ForeignKey(Award, related_name='entries')
    reference = models.CharField(max_length=50, null=True)

    def getPoster(self):
        """Retrieves the poster image for the entry film."""
        data = self.getCachedEntry()
        if len(data) > 0 and 'posters' in data[0] and len(data[0]['posters']) > 2:
            return data[0]['posters'][3]['image']['url']
        elif len(data) > 0 and 'profile' in data[0] and len(data[0]['profile']) > 2:
            return data[0]['profile'][1]['image']['url']
        elif len(data) > 1 and 'profile' in data[1] and len(data[1]['profile']) > 2:
            return data[1]['profile'][1]['image']['url']
        else:
            return ''

    def storeCachedEntry(self):
        """ Builds a key for caching an entry."""
        return slugify(self.name) + "entry"

    def getCachedEntry(self):
        """ Gets a key for caching an entry."""
        c_key = self.storeCachedEntry()
        entry = cache.get(c_key)
        if entry == None:
            import re
            url = 'http://api.themoviedb.org'
            key = '31978081436f3021d35a3275c385491b'
            chk = re.search('.*"(.*)"', self.name)
            if chk > 0:
                title = urllib.quote(chk.group(1).encode("utf-8"))
            else:
                title = urllib.quote(self.name.encode("utf-8"))
            try:
                if re.search('Actor|Actress', self.award.name):
                    conn = urllib2.urlopen('%s/2.1/Person.search/en/json/%s/%s' % (url, key, title))
                else:
                    conn = urllib2.urlopen('%s/2.1/Movie.search/en/json/%s/%s+2010' % (url, key, title))
                entry = simplejson.loads(conn.read())
            finally:
                conn.close()
            if entry == [u'Nothing found.']:
                ref = urllib.quote(self.reference.encode("utf-8"))
                conn = urllib2.urlopen('%s/2.1/Movie.search/en/json/%s/%s+2010' % (url, key, ref))
                try:
                    entry = simplejson.loads(conn.read())
                finally:
                    conn.close()
            if entry != [u'Nothing found.']:
                cache.set(c_key, entry, 85000)
        return entry


class Pick(models.Model):
    """Pick model detailing the selection of votes made against a user for a wager."""
    entry = models.ForeignKey(Entry, related_name='picks')
    wager = models.ForeignKey(Wager)
    user = models.ForeignKey(User, related_name='picks')

    class Meta:
        unique_together = ('entry', 'wager', 'user',)


def entry_cache_key(name):
    """ Builds a key for caching an entry."""
    return slugify(name) + "entry"


def entry_cache_get(name, reference):
    """ Gets a key for caching an entry."""
    c_key = entry_cache_key(name)
    entry = cache.get(c_key)
    if entry == None:
        url = 'http://api.themoviedb.org'
        key = '31978081436f3021d35a3275c385491b'
        title = urllib.quote(name.encode("utf-8"))
        conn = urllib2.urlopen('%s/2.1/Movie.search/en/json/%s/%s+2010' % (url, key, title))
        try:
            entry = simplejson.loads(conn.read())
        finally:
            conn.close()
        if entry == [u'Nothing found.']:
            conn = urllib2.urlopen('%s/2.1/Person.search/en/json/%s/%s' % (url, key, title))
            try:
                entry = simplejson.loads(conn.read())
            finally:
                conn.close()
        cache.set(c_key, entry, 85000)
    return entry
