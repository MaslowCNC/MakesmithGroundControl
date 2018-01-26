from   kivy.uix.gridlayout                       import   GridLayout
from   UIElements.fileBrowser                    import   FileBrowser
from   UIElements.pageableTextPopup              import   PageableTextPopup
from   kivy.uix.popup                            import   Popup
import re
from DataStructures.makesmithInitFuncs           import MakesmithInitFuncs
from os                                          import    path
import cv2
import numpy as np


#ToDo: Relocate these to the config section
#Marker HSV Specs
backgroundTLHSV = [(30,40,80),(90,255,255)]
backgroundBLHSV = [(90,60,80),(140,255,255)]
backgroundTRHSV = [(160, 60, 60),(10,255,255)]
backgroundBRHSV = [(160, 60, 60),(10,255,255)]

#Location of the markers
TR = ( 1225, 615)
TL = (-1225, 515)
BL = (-1225,-615)
BR = ( 1325,-615)

backgroundfile='c:\crap\cv2\T3i2.JPG'

def findHSVcenter(img, hsv, hsvLow, hsvHi, bbtl, bbbr):
    #Mask to find the blobs
    if hsvLow[0] > hsvHi[0]:
        #It's wrapped [red]
        bottom = (0, hsvLow[1], hsvLow[2])
        maska=cv2.inRange(hsv, bottom,hsvHi)

        top = (180, hsvHi[1], hsvHi[2])
        maskb=cv2.inRange(hsv, hsvLow, top)
        mask=cv2.bitwise_or(maska, maskb)
    else:
        mask=cv2.inRange(hsv, hsvLow, hsvHi)

    #erode-dilate to clean up noise
    mask = cv2.erode(mask, None, iterations=3)
    mask = cv2.dilate(mask, None, iterations=3)
    cv2.imwrite('c:\crap\cv2\maskb.jpg', mask)

    #find contours
    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    center = None
    centers = []
    if len(cnts) > 0:
        # find the largest contour in the mask, then use
        # it to compute the minimum enclosing circle and
        # centroid
        c = max(cnts, key=cv2.contourArea)	
        for c in cnts:
            if cv2.contourArea(c) > 1000:
                ((x, y), radius) = cv2.minEnclosingCircle(c)
                M = cv2.moments(c)
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))   #ToDo - why not use the XY above?
                if center[0] >= bbtl[0] and center[0] <= bbbr[0]  and center[1] >= bbtl[1] and center[1] <= bbbr[1]:
                    #Make sure we're inside the bounding box
                    centers.append(center)
                    #Mark the image
                    cv2.circle(img, (int(x), int(y)), int(radius), (0, 255, 255), 2)
                    cv2.circle(img, center, 5, (0, 0, 255), -1)
        return centers


class BackgroundMenu(GridLayout, MakesmithInitFuncs):
    
    def openBackground(self):
        '''
        
        Open The Pop-up To Load A File
        
        Creates a new pop-up which can be used to open a file.
        
        '''
        #starting path is either where the last opened file was or the users home directory
        startingPath = path.dirname(self.data.backgroundFile)
        if startingPath is "": 
            startingPath = path.expanduser('~')
        
        #We want to filter to show only files that ground control can open
        validFileTypes = ".png, .jpg, .gif, .bmp".replace(" ", "").split(',')
        validFileTypes = ['*{0}'.format(fileType) for fileType in validFileTypes] #add a '*' to each one to match the format the widget expects
        
        content = FileBrowser(select_string='Select', 
                    favorites=[(startingPath, 'Last Location')], 
                    path = startingPath, 
                    filters = validFileTypes)
                    
        content.bind(on_success=self.load,
                         on_canceled=self.dismiss_popup,
                         on_submit=self.load)

        #ToDo: Add a "latest" checkbox or "dir select button" so that it loads the latest file...
        #load=self.load, cancel=self.dismiss_popup
        
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()
    def reloadBackground(self):
        self.processBackground()
        self.close()
        
    def processBackground(self):
        filename = 'c:\crap\cv2\T3i2.JPG'   #ToDo: Fixthis
        print "ProcessBackground",filename
        #ToDo: handle yet-to-be-invented "LatestInCurrentDir" bit

        if filename=="":
            img = None
        else:
            img = cv2.imread(filename)
            hsv = hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)    #HSV colorspace is easier to do "Color" than RGB
            xmax=img.shape[1]
            ymax=img.shape[0]
            xmid = xmax/2
            ymid = ymax/2;

            #Find the centers of the markers:ToDo - handle duplicate/unique colors properly...
            centers = []
            for c in findHSVcenter(img, hsv, backgroundTLHSV[0], backgroundTLHSV[1], (0,0), (xmid,ymid)):
                centers.append(c)
            for c in findHSVcenter(img, hsv, backgroundTRHSV[0], backgroundTRHSV[1], (xmid,0),(xmax, ymid)):
                centers.append(c)
            for c in findHSVcenter(img, hsv, backgroundBLHSV[0], backgroundBLHSV[1], (0,ymid), (xmid, ymax)):
                centers.append(c)
            for c in findHSVcenter(img, hsv, backgroundBRHSV[0], backgroundBRHSV[1], (xmid,ymid), (xmax, ymax)):
                centers.append(c)
            
            #ToDo - what do we do if we don't find points?
            pts1 = np.float32([centers[0],centers[1],centers[2],centers[3]])
            leftmost = min(TL[0],BL[0])
            rightmost=max(TR[0],BR[0])
            topmost=max(TL[1],TR[1])
            botmost=min(BL[1],BR[1])
            h = topmost-botmost
            w = rightmost-leftmost

            pts2 = np.float32(
                [[TL[0]-leftmost,TL[1]-botmost],[TR[0]-leftmost, TR[1]-botmost],
                 [BL[0]-leftmost,BL[1]-botmost],[BR[0]-leftmost,BR[1]-botmost]]) 
            
            M = cv2.getPerspectiveTransform(pts1,pts2)
            img = cv2.warpPerspective(img,M,(w,h))
    
    def clear_background(self):
        '''
        
        Clear background
        
        '''
        filename=""
        self.processBackground()
        self.close()

 
    
    def load(self, instance):
        '''
        
        Load A Backround Image File from the file dialog
        
        Takes in a file path (from pop-up) and handles the file appropriately for the given file-type.
        
        '''
        
        filename = instance.selection[0]
        print(filename)
        backgroundFile = filename
        
        #close the open file popup
        self.dismiss_popup()
        self.processBackground()
        
        #And close the menu
        self.close()
    
    def openBackgroundSettings(self):
        '''
        Open the background settings page
        '''
        dosomething
        
    
    def dismiss_popup(self, *args):
        '''
        
        Close The File Picker (cancel was pressed instead of OK).
        
        '''
        self._popup.dismiss()
