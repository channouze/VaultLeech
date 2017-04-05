import os
import requests
import sys
from lxml import etree

version = '0.0.1'

class VaultLeech(object):

    def __init__(self, talkurl, login, password):
        """ Start up... """
        self.login = login
        self.password = password
        self.talkurl = talkurl
        
        self.loginurl = ''

        # TODO: verify args
        print 'VaultLeech v' + version + '\nA GDC Vault Backup Tool\nUsage: VaultLeech url (user) (pass)'

        self.buildPathToVideo()

    def loginToVault(self):
        r = requests.get(self.loginurl, auth=(self.login, self.password))
        self.checkURLResponse(r)

    def validateEmail(self):
        pass

    def validateTalkURL(self):
        pass

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
        # xmlVideo = xmlVideo.split('=')

        # builds the final xml url
        # outputs http://evt.dispeak.com/ubm/gdc/sf17/xml/847415_GXDS.xml
        xmlRequest = baseURL + 'xml/' + xmlVideo
        
        # find the mp4 files in xml
        # outputs   mp4:assets/ubm/gdc/sf17/847254_WTDP-v9f81f-500.mp4
        #           mp4:assets/ubm/gdc/sf17/847254_WTDP-v9f81f-800.mp4
        #           mp4:assets/ubm/gdc/sf17/847254_WTDP-v9f81f-1300.mp4
        tree = etree.parse(xmlRequest)
        mp4list = []
        for mp4 in tree.xpath('/podiumPresentation/metadata/MBRVideos/MBRVideo/streamName'):
            mp4list.append(mp4.text)
        
        # build host from js file in player.html
        # TODO: make it work with pre 2015 videos
        r = requests.get(xmlURL)
        self.checkURLResponse(r)
        for line in r.iter_lines():
            if 'custom/player02-a.js' in line:
                break
            if 'custom/player01.js' in line:
                break
        if 'custom/player02-a.js' or 'custom/player01.js' in line:
            pass
        else:
            print 'failed to find the js file, maybe this is a pre-2015 video?'

        # outputs http://evt.dispeak.com/ubm/gdc/sf17/custom/player02-a.js
        js = xmlURL.rsplit('player.html')[0] + 'custom/player02-a.js'

        r = requests.get(js)
        self.checkURLResponse(r)

        for line in r.iter_lines():
            if 'httpHostSource' in line:
                break

        # host should now be something like 'http://s3-2u-d.digitallyspeaking.com'
        host = line.rsplit('=')[-1]
        host = host[2:-2]

        # joins host and mp4 file
        urls = []

        for index in range (0,len(mp4list)):
            urls.append(host + '/' + str(mp4list[index])[4:])
        
        # display download details (if found)
        self.showDetails(xmlRequest, urls)
    
    # show video details    
    def showDetails(self, xml, filelist):
        tree = etree.parse(xml)

        print '='*50

        print self.getEvent(xml), self.getYear(xml)
        for title in tree.xpath('/podiumPresentation/metadata/title'):
            print title.text

        for speaker in tree.xpath('/podiumPresentation/metadata/speaker'):
            print 'Speaker(s): ' + speaker.text

        for talkLength in tree.xpath('/podiumPresentation/metadata/endTime'):
            print 'Duration: ' + talkLength.text
        
        print '='*50
        # prints the files available and the bitrate information
        print 'Available files:\n'
        # TODO: bitrate information
        bitrate = [0,1,2]
        size = [0,1,2]
        for index in range (0,len(filelist)):
            # print str(index)+':', filelist[index].rsplit('/')[-1], 'Bitrate: ', bitrate[index], 'Size: ', size[index]
            print str(index)+':', filelist[index].rsplit('/')[-1]

        # TODO: Accept input from user
        # TODO: Check input from user
        
        # Finally, Get video
        self.getVideo(filelist[0], self.getYear(xml), title.text)

        return None

    # return if we're dealing with GDC or VRDC
    def getEvent(self, string):

        event = string.rsplit('/')[5]
        event = event [:-2]

        return event.upper()
    
    # return the year of the event from the video url
    def getYear(self, string):

        year = string.rsplit('/')[5]
        year = year [-2:]
        
        if (int(year) >= int(96)):
            stryear = 1900+int(year)
        else:
            stryear = 2000+int(year)
        return int(stryear)

    def checkURLResponse(self, req):
        if (req.status_code != 200):
            print 'something went wrong'

    def getVideo(self, link, year, name):
        
        # TODO Beautify the file name
        
#        file_name = 'GDC'+str(year)+' '+name+'.mp4'
#
#        print file_name
#        for char in file_name:
#            if char.isalnum() or char == ' ':

        file_name = link.rsplit('/')[-1]        

        with open(file_name, "wb") as f:
            print "\nDownloading %s" % file_name
            # TODO: implement SSL verify the proper way
            # TODO: headers and referer to a variable
            response = requests.get(link, stream=True, verify=False, headers={'Referer': 'http://evt.dispeak.com/ubm/gdc/sf17/player.html', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36'})
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
            print '\n'
