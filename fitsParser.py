# Provide utilities for reading fits files
# @author: Zachary Watkins
import re
import numpy as np
from astropy.io import fits
import pandas as pd

#Regular expressions to parse the header
NAME_MATCH = re.compile("TTYPE[0-9]+\s*=\s*'\s*[^\s]+\s*'")
REMOVE_NAME = re.compile("(TTYPE[0-9]+\s*=\s*'\s*)|(\s*')|(\s+)")
FORMAT_MATCH = re.compile("TFORM[0-9]+\s*=\s*'\s*[^\s]+\s*'")
REMOVE_FORMAT = re.compile("(TFORM[0-9]+\s*=\s*'\s*)|(\s*')|(\s+)")
UNIT_NUMBMATCH = re.compile("TUNIT[0-9]+")
REMOVE_UNITNUMB = re.compile("TUNIT")
UNIT_MATCH = re.compile("TUNIT[0-9]+\s*=\s*'\s*[^\s]+\s*'")
REMOVE_UNIT = re.compile("(TUNIT[0-9]+\s*=\s*'\s*)|(\s*')|(\s+)")
AS_REGEX = re.compile(".+\s+as\s+.+")
INCLUDE_NAME_REGEX = re.compile(".+(?=\sas)")
ALIAS_REGEX = re.compile("(?<=as\s).+")
fileRegex = re.compile("from\s+[^\s]+\n|$")
rfileRegex = re.compile("(from)|(\s+)|\n|$")
NUM_REGEX = re.compile("[0-9]+")
IN_REGEX = re.compile(".+-i")
OUT_REGEX = re.compile(".+-o")
INCLUDE_ALL = re.compile("\s*-all\s*$|\n")

class fitsParser:

    def __init__(self, filename = None, include = list(), includefile = None):
        
        self.data = pd.DataFrame()
        self.include = list(include)
        self.inputs = list()
        self.outputs = list()
        self.includeAll = False

        if(includefile != None):
            infile = open(includefile, "r")
            inString = infile.read()
            self.filename = fitsParser.findAndRemove(inString, fileRegex, rfileRegex)[0]
            inString = re.sub(fileRegex,"", inString)
            for line in re.compile('(.+(?=$|\n))').findall(inString):
                self.include.append(line)
            infile.close()
        
        #give precedent to filename passed directly
        if filename!=None:
            self.filename = filename
        
        self.hduList = fits.open(self.filename)
        self.tableinfo = self.parseHeader(str(self.hduList[1].header), self.include) #Gather the collum names from the header file
        
        if self.includeAll:
            Allinfo = self.parseHeader(str(self.hduList[1].header), list())
            for field in Allinfo.keys():
                if field not in self.tableinfo:
                    self.tableinfo[field]=Allinfo[field]
               
        
        for name in self.tableinfo.keys():
            self.data[self.tableinfo.get(name).get('alias')] = self.hduList[1].data.field(name).byteswap().newbyteorder()
        
        
        
        
    #Parse Header takes the header string of a fits file and depending on the arguments passed, retrives needed information
    #params: header, the header string of the fits file
    #        include, a list of paramaters to be exlusively in the data frame
    #        includefile  allows for passing the same arguments as in include, but written in a text file
    #returns: a dictionary mapping from the name of the field to be include in the data frame as it appears there, to paramater, format, units, alias
    
    def parseHeader(self, header, include):
         
        names = fitsParser.findAndRemove(header, NAME_MATCH, REMOVE_NAME)
        formats = fitsParser.findAndRemove(header, FORMAT_MATCH, REMOVE_FORMAT)
        unitNumbs = fitsParser.findAndRemove(header, UNIT_NUMBMATCH, REMOVE_UNITNUMB)
        units = fitsParser.findAndRemove(header, UNIT_MATCH, REMOVE_UNIT)
        params = dict()
        if len(include)==0:
            for i in range(len (names)):
                if i in unitNumbs:
                    unit = units[0]
                    units.remove(0)
                else:
                    unit = None
                params[names[i]] = {'format': formats[i], 'units': unit, 'alias': names[i]}
                
        else:
            #TODO: account for x as y //done 
            for name in include:
                In, Out = False, False
                
                if bool(INCLUDE_ALL.match(name)):
                    self.includeAll = True
                
                else:
                    if bool(IN_REGEX.match(name)):
                        name = re.sub('\s*-i\s*', "", name)
                        In = True

                    elif bool(OUT_REGEX.match(name)):
                        name = re.sub('\s*-o\s*',"", name)
                        Out = True

                    if bool(AS_REGEX.match(name)):
                        realName = INCLUDE_NAME_REGEX.findall(name)[0]
                        alias = ALIAS_REGEX.findall(name)[0]

                    else: 
                        alias = name
                        realName = name

                    if bool(NUM_REGEX.match(realName)):
                        realName = names[int(realName)-1]

                    if In:
                        self.inputs.append(alias)
                    elif Out:
                        self.inputs.append(alias)

                    params[realName] = {'format': formats[names.index(str(realName))], 'units': units[unitNumbs.index(names.index(str(realName)))] if names.index(str(realName)) in unitNumbs else None, 'alias': alias}
                        
        return params
    
    #add a collum based on a collum name. If the collum name in the fits file is x, but one wants to load it under the name y, pass: x as y
    #loading all the collums at the very begining should be more efficitent
    def addCollum(self, collumName):
        #update the alias if need be
        if bool(AS_REGEX.match(collumName)):
            realName = str(INCLUDE_NAME_REGEX.findall(collumName)[0])
            alias = str(ALIAS_REGEX.findall(collumName)[0])
            
        else:
            realName = str(collumName)
            alias = str(collumName)
        
        inList = list()
        inList.append(collumName)
        self.tableinfo.update(fitsParser.parseHeader(str(self.hduList[1].header), inList))
        self.data[alias] = self.hduList[1].data.field(realName)
    
    
    #find all instances given regex within a string, and trim it accordingly
    #params: target, the string from which all instances of a regex
    #        findRegex, the regex to find
    #        removeRegex, the regex to trim found the found strings
    #returns: a list of the found/trimmed strings. An empty list is return if no strings     are found
    
    @staticmethod
    def findAndRemove(target, findRegex, removeRegex):
        strlist = findRegex.findall(target)
        strlist = list(map(lambda x : re.sub(removeRegex, "", x), strlist))
        return strlist 
    
    def __str__(self):
        return str(self.data)