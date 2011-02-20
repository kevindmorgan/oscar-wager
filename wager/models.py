import simplejson, urllib, urllib2, uuid

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
    wager = models.ForeignKey(Wager)
    
    class Meta:
        unique_together = ('name', 'email', 'wager')
    
    def save(self):
        self.slug = slugify(self.name)
        super(User, self).save()

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
        data = entry_cache_get(self.name, self.reference)
        return data[0]['posters'][3]['image']['url'] if len(data) > 0 and data[0].has_key('posters') and len(data[0]['posters']) > 2 else ''

class Pick(models.Model):
    """Pick model detailing the selection of votes made against a user for a wager."""
    entry = models.ForeignKey(Entry)
    wager = models.ForeignKey(Wager)
    user = models.ForeignKey(User, related_name='picks')
    
def entry_cache_key(name):
    """ Builds a key for caching an entry."""
    return slugify(name)+"entry"

def entry_cache_get(name, reference):
    """ Gets a key for caching an entry."""
    c_key = entry_cache_key(name)
    entry = cache.get(c_key)
    if entry == None:
        url = 'http://api.themoviedb.org'
        key = '31978081436f3021d35a3275c385491b'
        title = urllib.quote(name.encode("utf-8"))
        conn  = urllib2.urlopen('%s/2.1/Movie.search/en/json/%s/%s' % (url, key, title))
        try:
            entry = simplejson.loads(conn.read())
        finally:
            conn.close()
        if len(entry) == 0:
            ref = urllib.quote(reference.encode("utf-8"))
            conn = urllib2.urlopen('%s/2.1/Movie.search/en/json/%s/%s' % (url, key, ref))
            try:
                entry = simplejson.loads(conn.read())
            finally:
                conn.close()
        cache.set(c_key, entry, 85000)
    return entry
