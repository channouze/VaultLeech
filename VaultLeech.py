import os
import requests
import sys
from lxml import etree

version = '0.0.1c'

class VaultLeech(object):

    def __init__(self, talkurl, login, password):
        """ Start up... """
        self.login = login
        self.password = password
        self.talkurl = talkurl
        
        self.loginurl = ''

        # TODO: verify args
        # print 'VaultLeech v' + version + '\nA GDC Vault Backup Tool\nUsage: VaultLeech url (user) (pass)'
        print 'VaultLeech v' + version + '\nA GDC Vault Backup Tool\nUsage: VaultLeech url'

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
        # baseURL = xmlURL[:xmlURL.find('player.html')]
        baseURL = xmlURL[:xmlURL.find(self.getPlayername(xmlURL))]

        # outputs player.html?xml=847415_GXDS.xml
        xmlVideo = xmlURL.rsplit('/')[-1]

        # if we're dealing with post-2013 html code we need additional parsing
        if self.getYear(baseURL) > 2012:
            xmlVideo = xmlVideo[xmlVideo.find('xml=')+4:]
            # outputs 847415_GXDS.xml
        
        # builds the final xml url
        # outputs http://evt.dispeak.com/ubm/gdc/sf17/xml/847415_GXDS.xml
        xmlRequest = baseURL + 'xml/' + xmlVideo
        
        # find the mp4 files in xml
        # outputs   mp4:assets/ubm/gdc/sf17/847254_WTDP-v9f81f-500.mp4
        #           mp4:assets/ubm/gdc/sf17/847254_WTDP-v9f81f-800.mp4
        #           mp4:assets/ubm/gdc/sf17/847254_WTDP-v9f81f-1300.mp4
        tree = etree.parse(xmlRequest)
        
        # treat separately pre-2012 videos (flv)
        videoList = []
        if self.getYear(xmlRequest) > 2012:
            # we have mp4s (yay!)
            for mp4 in tree.xpath('/podiumPresentation/metadata/MBRVideos/MBRVideo/streamName'):
                videoList.append(mp4.text)
        else:
            for flv in tree.xpath('/podiumPresentation/metadata/speakerVideo'):
                # we have flvs (onoes!)
                videoList.append(flv.text)
        
        # build host from js file in the right html player
        r = requests.get(xmlURL)
        
        self.checkURLResponse(r)

        # get the proper js filename depending on the year the event occured
        # because it's different between 2014+, 2011-13, ...
        js = self.getJavascriptFilename(self.getEvent(xmlRequest), self.getYear(xmlRequest))

        for line in r.iter_lines():
            if js in line:
                break
        if js not in line:
            pass
            # print 'failed to find the js file, fallback to xml...'

        # outputs http://evt.dispeak.com/ubm/gdc/sf17/custom/player02-a.js
        # except for pre-2014 where we'll read straight from the xml
        if self.getYear(xmlRequest) > 2014:
            js = xmlURL.rsplit(self.getPlayername(xmlURL))[0] + js

            r = requests.get(js)
            self.checkURLResponse(r)

            for line in r.iter_lines():
                if 'httpHostSource' in line:
                    break
            if 'httpHostSource' not in line:
                sys.exit('failed to find the host, aborting...')

            host = line.rsplit('=')[-1]
            host = host[2:-2]
        else:
            tree = etree.parse(xmlRequest)

            host = tree.xpath('/podiumPresentation/metadata/mp4video')
            if host == '':
                host = line.text.rsplit('/assets')[0]
            else:            
                host = 'http://s3-2u-d.digitallyspeaking.com'
                # best guess when all else fail (e.g. paywall videos)
                # TODO: find the host for 2012 videos and below

        # joins host and mp4/flv file and build the list of available videos
        urls = []

        for index in range (0,len(videoList)):
            urls.append(host + '/' + str(videoList[index])[4:])
        
        # display download details (if found)
        self.showDetails(xmlRequest, urls)
    
    # show video details    
    def showDetails(self, xml, filelist):
        tree = etree.parse(xml)

        print '='*50

        # display event and year
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
        # TODO: bitrate & size information
        # bitrate = [0,1,2]
        # size = [0,1,2]
        for index in range (0,len(filelist)):
            # print str(index)+':', filelist[index].rsplit('/')[-1], 'Bitrate: ', bitrate[index], 'Size: ', size[index]
            print str(index)+':', filelist[index].rsplit('/')[-1]

        while True:
            try:
                videoSelected = raw_input('\nChoose file:')
            except ValueError:
                print 'Enter a single-digit number'
                continue
            else:
                # TODO: Support single videos
                if videoSelected.lower() in ('0', '1', '2'):
                    break
                else:
                    print 'Enter a single-digit number comprised between 0 and', len(filelist)-1
        
        # Finally, Get video
        self.getVideo(filelist[int(videoSelected)], self.getYear(xml), title.text)

        return None

    # returns the right playerName.html
    def getPlayername(self, url):
        
        if self.getYear(url) == 2016 and self.getEvent(url) == 'GDC':
            return 'player2.html'
        else:
            return 'player.html'
    
    # returns the right .js file we need to find the host, depending on the event
    def getJavascriptFilename(self, event, year):
        if event == 'GDC':
            if year == 2017:
                return 'custom/player02-a.js'
            if year == 2015 or year == 2016:
                return 'custom/player2.js'
            if year <= 2014:
                return 'no js for pre-2014 (use xml instead!)'
        else:
            if event == 'VRDC':
                return 'custom/player01.js'
        return 'js not found'

    # returns GDC or VRDC depending on the URL fed
    def getEvent(self, string):

        event = string.rsplit('/')[5]
        event = event [:-2]

        # sf means GDC, vrdc means, well, VRDC
        if event == 'sf':
            event = 'gdc'

        return event.upper()
    
    # return the year of the event from the video url
    def getYear(self, string):

        year = string.rsplit('/')[5] # TODO: Make it work with the older urls pre-2011
        year = year [-2:]
        
        if (int(year) >= int(96)):
            stryear = 1900+int(year)
        else:
            stryear = 2000+int(year)

        return int(stryear)

    def checkURLResponse(self, req):
        if (req.status_code != 200):
            sys.exit('something went wrong')

    def getVideo(self, link, year, name):
        
        # TODO Beautify the file name
        
        file_name = link.rsplit('/')[-1]        

        with open(file_name, "wb") as f:
            print "\nDownloading %s" % file_name
            # TODO: implement SSL verify the proper way
            # TODO: headers and referer to a variable, built from source url
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
