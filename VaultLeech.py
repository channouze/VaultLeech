# =======================================
# GDC Vault Leecher 
# 
# Backup videos for offline use
#
# https://github.com/channouze/VaultLeech
#
# =======================================

import os
import requests
import sys
import time
import json
from lxml import etree
from validate_email import validate_email

version = '1.0'
vaultLoginURL = 'http://gdcvault.com/api/login.php'
vaultLogoutURL = 'http://gdcvault.com/logout'

class VaultLeech(object):

    def __init__(self, talkurl, login = None, password = None):
        # Start up...
        # set-up a session so we could persist our cookies across requests
        self.session = requests.Session()

        self.main(talkurl, login, password)

    def main(self, talkurl, login = None, password = None):

        print 'VaultLeech v' + version + '\nA GDC Vault Backup Tool\nUsage: VaultLeech url (user) (pass)'

        # First: verify the URL so we don't abuse the login API
        # Also: Don't log in if the video is in the free section
        if self.isTalkURLValid(talkurl):
            if (login is None and password is None) or self.isTalkInTheFreeSection(talkurl):
                # Means we handle a free video
                self.buildPathToVideo(talkurl)
            else:
                if self.isEmailValid(login):
                    if self.loginToVault(login,password):
                        # Means we deal with authenticated stuff
                        self.buildPathToVideo(talkurl)
                        self.logoutFromVault()
                    else:
                        print 'ERROR: account is not a GDC Vault subscriber.'
                else:
                    print 'ERROR: e-mail is not valid, please try again.'
        else:
             print 'ERROR: url supplied is not a valid talk url, please try again'

    def loginToVault(self, login, password):
        # First make sure we're not already logged in
        r = self.session.get('http://www.gdcvault.com/')
        self.checkURLResponse(r)

        for logoutData in r.iter_lines():
            if '<li id="nav_logout" class="nav_item nav_link"><a href="/logout">Logout</a></li>' in logoutData:
                # User is already logged in
                self.logoutFromVault()
                break

        # If not, log in using the user supplied credentials
        payload = {'email':login,'password':password}
        r = self.session.post(vaultLoginURL, data=payload)
        self.checkURLResponse(r)

        # our request gets us a cookie which is parsable as a JSON file so we can now check credentials
        cookie = r.json()

        if cookie["isSubscribed"]:
            # TODO: Hardening (when company is None)
            print '** Logged in as', cookie['first_name'], cookie['last_name'], 'from', cookie['company']
            print '** This account subscription expires on', cookie['expiration'].rsplit()[0]

        return True

    def logoutFromVault(self):
        r = self.session.get(vaultLogoutURL)
        self.checkURLResponse(r)

    def isEmailValid(self, email):
        return validate_email(str(email))

    def isTalkURLValid(self, url):
        if url.startswith('http://www.gdcvault.com/play') or url.startswith('http://gdcvault.com/play'):
            return True
        else:
            return False

    def isTalkInTheFreeSection(self, url):
        r = self.session.get(url)
        self.checkURLResponse(r)

        # no iframe tag if we hit the paywall (or if audio only talk)
        for line in r.iter_lines():
            if 'iframe' in line:
                return True
        return False

    def buildPathToVideo(self, talkurl):

        r = self.session.get(talkurl)
        self.checkURLResponse(r)

        # find the mp4 xml definition file
        for line in r.iter_lines():
            if 'iframe' in line:
                # Filter out the pdfs and audio only talks (php instead of html in iframe)
                if '.html' in line:
                    break
        if not '.html' in line:
            print 'ERROR: Talk supplied is not a video. Please check the URL.'
            exit (0)

        

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
        r = self.session.get(xmlURL)
        
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

            r = self.session.get(js)
            self.checkURLResponse(r)

            for line in r.iter_lines():
                if 'httpHostSource' in line:
                    break
            if 'httpHostSource' not in line:
                sys.exit('ERROR: failed to find the host, aborting...')

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
                # Host for 2012 videos and below is protected behind webserver permissions :(

        # joins host and mp4/flv file and build the list of available videos
        urls = []

        for index in range (0,len(videoList)):
            urls.append(host + '/' + str(videoList[index])[4:])
        
        # display download details (if found)
        videoDetails = self.showDetails(xmlRequest, urls)

        # Finally, Get video
        self.getVideo(videoDetails[0], videoDetails[1], videoDetails[2], xmlURL, videoDetails[3])
    
    # shows and returns video details    
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
        # prints the files available
        print 'Available files:\n'

        bitrate = []
        for xmlbitrate in tree.xpath('/podiumPresentation/metadata/MBRVideos/MBRVideo/bitrate'):
            bitrate.append(xmlbitrate.text)
        # TODO: handle the flv NULL size & bitrate
        if len(bitrate) == 1:
            pass

        size = []

        for filesize in filelist:
            r = self.session.head(filesize)
            headers = r.headers
            try:
                filelength = int(headers.get('content-length'))
            except TypeError:
                # CDN error, ignore and continue 
                filelength = 0
            size.append(filelength//(1024*1024))

        for index in range (0,len(filelist)):
            # Displays the list of files along with bitrate and Size
            # if size = 0, it probably means the download is invalid
            if size[index] != 0:
                print str(index)+':', filelist[index].rsplit('/')[-1], bitrate[index], 'kbps  Size: ', size[index], 'MB'

        if len(filelist) == 1 and filelist[len(filelist)-1].endswith('.flv'):
            print '\nWARNING! Download is not supported at the moment for flv videos'
        
        # Let the user decide which video she wants to download, or auto-dl if only one video available
        if len(filelist) > 1:
            while True:
                try:
                    videoSelected = raw_input('\nChoose file: ')
                except ValueError:
                    print 'Enter a single-digit number'
                    continue
                else:
                    # TODO: Make this a little bit cleaner and handle zero sized videos
                    if videoSelected.lower() in ('0', '1', '2'):
                        break
                    else:
                        print 'Enter a single-digit number comprised between 0 and', len(filelist)-1
        else:
            videoSelected = 0

        return (filelist[int(videoSelected)], self.getYear(xml), title.text, size[int(videoSelected)])

    # returns the right playerName.html
    def getPlayername(self, url):
        
        # make sure we've got the full url and not the xml!
        if '.html' in url:
            # outputs http://evt.dispeak.com/ubm/gdc/sf17/player.html
            playerName = url.split('?')[0]
            # outputs player.html
            playerName = playerName.rsplit('/')[-1]        
            return playerName
        else:
            # TODO: tidy this up
            print 'ERROR: malformed url'
            return 'ERROR: malformed url'
    
    # returns the right .js file we need to find the host, depending on the event
    def getJavascriptFilename(self, event, year):
        if event == 'GDC' or event == 'GDC EUROPE':
            if year == 2017 or (event == 'GDC EUROPE' and year == 2016):
                return 'custom/player02-a.js'
            if year == 2015 or year == 2016:
                return 'custom/player2.js'
        else:
            if event == 'VRDC':
                if year == 2017:
                    return 'custom/player02-a.js'
                if year == 2016:
                    return 'custom/player01.js'
        if year <= 2014:
                return 'no js for pre-2014 (use xml instead!)'
           
        # TODO: cleaner implementation
        return 'js not found'

    # returns GDC or VRDC depending on the URL fed
    def getEvent(self, string):

        event = self.getInformationFromURL(string) [:-2]

        # sf means GDC, vrdc means, well, VRDC
        if event == 'sf' or event == 'gdc20':
            event = 'gdc'
        # eur means GDC Europe
        if event == 'eur':
            event = 'gdc europe'
        # online means GDC Austin
        if event == 'online':
            event == 'gdc online'
        # VRDC @ GDC events
        # TODO: Fix this
        # if self.getPlayername(string) == 'playerv.html':
        #     event = 'vrdc'

        return event.upper()
    
    # returns the year of the event from the video url
    def getYear(self, string):

        year = self.getInformationFromURL(string) [-2:]

        if (int(year) >= int(96)):
            stryear = 1900+int(year)
        else:
            stryear = 2000+int(year)

        return int(stryear)

    # returns the useful part of the URL where we can generate event name and year
    def getInformationFromURL(self, string):
        # branch depending on whether we've been supplied the .xml or the .html
        if '?' in string:
            # 1) split the url so we discard everything post player?.html
            string = string.rsplit('player')[0]  
            # 2) count the slashes and strip
            string = string.rsplit('/')[string.count('/')-1]
        else:
            if string.endswith('.xml'):
                # xml url, so go back 2 positions
                string = string.rsplit('/')[string.count('/')-2]
            else:
                # canonical url, so go back 1 pos
                string = string.rsplit('/')[string.count('/')-1]
        return string

    def checkURLResponse(self, req):
        if (req.status_code != 200):
            print 'Error', req.status_code, req.content
            sys.exit('something went wrong')

    def getVideo(self, link, year, name, referer, total_length):
        
        # TODO Beautify the file name
        
        file_name = link.rsplit('/')[-1]        

        with open(file_name, "wb") as f:
            print "\nDownloading %s" % file_name
            # TODO: implement SSL verify the proper way
            # TODO: headers and referer to a generated variable, built from source url
            start = time.clock()
            response = self.session.get(link, stream=True, verify=False, headers={'Referer': 'http://evt.dispeak.com/ubm/gdc/sf17/player.html', 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.75 Safari/537.36'})

            if total_length is None: # no content length header
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)*(1024*1024)
                for chunk in response.iter_content(chunk_size=4096):
                    dl += len(chunk)
                    f.write(chunk)
                    done = int(50 * dl / total_length)
                    # TODO: Display adaptive download speed (MB if > 1000KBps, etc)
                    sys.stdout.write("\r[%s%s] %s Kbps" % ('=' * done, ' ' * (50-done), (dl//(time.clock() - start)//1000)))    
                    sys.stdout.flush()
            sys.stdout.write('\n\nWrote %s\%s\n' % (os.getcwd(), file_name))
