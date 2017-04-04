import os
import requests
import sys
from lxml import etree

version = '0.0.1'

class VaultLeech(object):

    def __init__(self, login, password, talkurl, loginurl):
        """ Start up... """
        self.login = login
        self.password = password
        self.talkurl = talkurl
        self.loginurl = loginurl

        # todo verify args
        print 'VaultLeech v' + version + '\nA GDC Vault Backup Tool\nUsage: VaultLeech user pass url'

    def loginToVault(self):
        r = requests.get(self.loginurl, auth=(self.login, self.password))
        self.checkURLResponse(r)

    def validateEmail(self):
        print 'todo'

    def validateTalkURL(self):
        print 'todo'

    def buildPathToVideo(self):
        r = requests.get(self.talkurl)
        self.checkURLResponse(r)

        # find the mp4 xml definition file

        for line in r.iter_lines():
            if 'iframe' in line:
                break

        # build the xml request url
        
        # outputs http://evt.dispeak.com/ubm/gdc/sf17/player.html?xml=847415_GXDS.xml
        start = line.find("http")
        end = line.find(".xml&") - len(line) + 4

        xmlURL = line [start:end]

        # outputs http://evt.dispeak.com/ubm/gdc/sf17/
        baseURL = xmlURL[:xmlURL.find('player.html')]
        
        # outputs player.html?xml=847415_GXDS.xml
        xmlVideo = xmlURL.rsplit('/')[-1]

        # outputs 847415_GXDS.xml
        xmlVideo = xmlVideo[xmlVideo.find('xml=')+4:]

        # builds the final xml url
        # outputs http://evt.dispeak.com/ubm/gdc/sf17/xml/847415_GXDS.xml
        xmlRequest = baseURL + 'xml/' + xmlVideo
        
        # find the mp4 files
        rxml = requests.get(xmlRequest)

        self.showDetails(xmlRequest)

        for line in r.iter_lines():
            if 'streamName' in line:
                print line

    
    # show video details    
    def showDetails(self, xml):
        tree = etree.parse(xml)
        print '=================================='
        year = xml[xml.find('sf')+2:xml.find('sf')+4]
        if (int(year)+1000 > 1096) and (int(year)+1000 < 1000):
            stryear = 1900+int(year)
        else:
            stryear = 2000+int(year)
        print 'GDC', stryear
        for title in tree.xpath('/podiumPresentation/metadata/title'):
            print title.text

        for speaker in tree.xpath('/podiumPresentation/metadata/speaker'):
            print 'Speaker(s): ' + speaker.text

        for talkLength in tree.xpath('/podiumPresentation/metadata/endTime'):
            print 'Duration: ' + talkLength.text
        print '=================================='

    def checkURLResponse(self, req):
        if (req.status_code != 200):
            print 'something went wrong'

    def getVideo(self):
        
        link = 'https://romo.ovh/romo.png'
        file_name = 'romo.png'

        with open(file_name, "wb") as f:
            print "Downloading %s" % file_name
            # TODO implement SSL verify the proper way
            response = requests.get(link, stream=True, verify=False)
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

