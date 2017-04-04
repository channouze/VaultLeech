import urllib
import urllib2
import cookielib
import re
import os
import requests

username = ''
password = ''
url = 'https://romo.ovh'

class VaultLeech(object):

    def __init__(self, login, password, talkurl):
        """ Start up... """
        self.login = login
        self.password = password
        self.talkurl = talkurl
        self.loginurl = 'http://ddl.romo.ovh/login.php'

        if(self.login is None or self.password is None or self.talkurl is None):
            print 'usage: VaultLeech e-mail password talkURL'
        else:
            print self.login, self.password, self.talkurl
        
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(debuglevel=0),
            urllib2.HTTPSHandler(debuglevel=0),
            urllib2.HTTPCookieProcessor(self.cj)
        )
        self.opener.addheaders = [
            ('User-agent', ('Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0'))
        ]
        # need this twice - once to set cookies, once to log in...
        self.loginToVault()
        self.loginToVault()

    def loginToVault(self):
        """
        Handle login. This should populate our cookie jar.
        """
        login_data = urllib.urlencode({
            'Email' : self.login,
            'password' : self.password,
        })
        # response = self.opener.open(self.loginurl, login_data)
        # return ''.join(response.readlines())

    def validateEmail(self):
        print 'it works'

    def buildPathToVideo(self):
        print 'wip'

    def getVideo(self):
        
        link = 'https://romo.ovh'
        file_name = 'romo.png'

        with open(file_name, "wb") as f:
            print "Downloading %s" % file_name
            response = requests.get(link, stream=True)
            total_length = response.headers.get('content-length')

            if total_length is None: # no content length header
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    done = int(50 * dl / total_length)
                    sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)) )    
                    sys.stdout.flush()

vaultleecher=VaultLeech(username, password, url)
vaultleecher.getVideo()
