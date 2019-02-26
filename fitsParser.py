# Provide utilities for reading fits files
# @author: Zachary Watkins
import re
import numpy as np
from astropy.io import fits
import pandas as pd

#Regular expressions to parse the header/command file
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
IN_REGEX = re.compile(".+-i.*")
OUT_REGEX = re.compile(".+-o.*")
INCLUDE_ALL = re.compile("\s*-all\s*$|\n")
COMMENT_REGEX = re.compile(".*#.*")
COLOUR_REGEX = re.compile(".+-c[[][0-9]+[]].*")
UNCERT_REGEX = re.compile("(?<!\[\])d[^\s]+")
LIST_REGEX = re.compile("[^\s]*[[]([^,]+,)+?[^,]+(?=[]])[]][^\s]*")
CONTENTS_REGEX = re.compile("(?<=[[]).+?(?=[]])")
PREFIX_REGEX = re.compile(".+(?=[[])")
POSTFIX_REGEX = re.compile("(?<=[]]).+")
SET_REGEX = re.compile("set\s+([A-Z]|[a-z])+\s*=\s*.+")
MULTIBLOCK_REGEX = re.compile("from(?:.+\n*)+?(?=$|(?:from))")

class fitsParser:


    def __init__(self, filename = None, include = None, includefile = None):

        if include == None:
            include = list()
        
        self.data = pd.DataFrame()
        self.include = list(include)
        self.inputs = list()
        self.outputs = list()
        self.includeAll = False
        self._colourDic = dict()
        self.colours = list()
        self.uncert = list()
        self.Ncolours = 2
        self.input_uncert = list()
        self.output_uncert = list()
        self.FileCommands = dict()
        self.__super__ = None
        self.__other__ = None

        if(includefile != None):
            if (includefile != 'Do Recursion'):
                infile = open(includefile, "r")
                inString = infile.read()
                thisCode = MULTIBLOCK_REGEX.findall(inString)
                infile.close()

            else:
                thisCode = include
                self.include = list()

            if(len(thisCode)==0):
                raise(IOError('No File Specified'))
            
            elif (len(thisCode)>1):
                self.__other__ = fitsParser(include=thisCode[1:], includefile='Do Recursion')
                self.__other__.__super__ = self
            
            inString = thisCode[0]
            self.filename = fitsParser.findAndRemove(inString, fileRegex, rfileRegex)[0]

            inString = re.sub(fileRegex,"", inString)
            for line in re.compile('(.+(?=$|\n))').findall(inString):
                self.include.append(line)
            
        
            
        
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
        
        # can only make colours once everything is set up. If the users wants a different value for N, the can call
        # makeColours again, and the dataFrame and colours list will be updated, or set colours = N in the include file
        self.makeColours(N = self.Ncolours)
        
        #check for uncertainties matching inputs and ouputs
        self.in_out_uncert()
        
        
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
            
                if bool(COMMENT_REGEX.match(name)):
                    name = fitsParser.findAndRemove(name, COMMENT_REGEX, re.compile("#.*"))
                    name = name[0]

                if bool(SET_REGEX.match(name)):
                    self.setStatement(name)
                    
                elif name!='':
                    self._nameProcedure(name, params, formats, unitNumbs, units, names)

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

    #helper method to parser a line
    #name is not the empty string
    #name is not a comment
    #name should be valid syntax
    def _nameProcedure(self, name, params, formats, unitNumbs, units, names):
        
        In, Out = False, False
        colour = -1

        if bool(INCLUDE_ALL.match(name)):
            self.includeAll = True

        else:
            #check for input output designation
            if bool(IN_REGEX.match(name)):
                name = re.sub('\s*-i\s*', "", name)
                In = True
                
            elif bool(OUT_REGEX.match(name)):
                name = re.sub('\s*-o\s*',"", name)
                Out = True

            #check for colour designation
            if bool(COLOUR_REGEX.match(name)):
                colour = int(float(fitsParser.findAndRemove(name,
                                                            re.compile('-c[[][0-9]+[.]?[0-9]*[]]'), re.compile("(-c[[])|([]])"))[0]))
                name = re.sub("-c[[][0-9]+[.]?[0-9]*[]]\s*", "", name)

            if bool(AS_REGEX.match(name)):
                realName = INCLUDE_NAME_REGEX.findall(name)[0]
                alias = ALIAS_REGEX.findall(name)[0]

            else: 
                alias = name
                realName = name

            if(LIST_REGEX.match(realName)):
                namelist = fitsParser._listParse(realName, alias)
                for command in namelist:
                    if In == True:
                        command += "-i"
                    elif Out == True:
                        command += '-o'
                    self._nameProcedure(command, params, formats, unitNumbs, units, names)
                return

            alias = alias.strip()
            realName = realName.strip()

            if bool(NUM_REGEX.match(realName)):
                realName = names[int(realName)-1]
            
            if bool(UNCERT_REGEX.match(alias)):
                self.uncert.append(alias)
                
            
            alias = re.sub(r"\\", "", alias)
            
            
            
            if In:
                self.inputs.append(alias)
            elif Out:
                self.outputs.append(alias)
            
            if colour != -1:
                self._colourDic[alias] = colour

            params[realName] = {'format': formats[names.index(str(realName))], 'units': units[unitNumbs.index(names.index(str(realName)))] if names.index(str(realName)) in unitNumbs else None, 'alias': alias}
    
    #helper method to generate the colour list
    #modifies 
    def makeColours(self, N=2):
            sortedColours = list(map(lambda x : x[0], 
                                sorted(self._colourDic.items(), key=lambda x: x[1])))
            colours = list()
                       
            for name in sortedColours:
                for i in range(sortedColours.index(name)+1, sortedColours.index(name)+1+N):
                    
                    if i>=len(sortedColours):
                        break
                    
                    self.data[name+'-'+sortedColours[i]]=self.data[name]-self.data[sortedColours[i]]
                    colours.append(name+'-'+sortedColours[i])
                    
            self.colours = colours           
                        

    @staticmethod
    def _listParse(realName , alias): 
        funk = lambda x : x[0] if len(x)>0 else ""
        realPre = funk(PREFIX_REGEX.findall(realName))
        realPost = funk(POSTFIX_REGEX.findall(realName))
        aliasPre = funk(PREFIX_REGEX.findall(alias))
        aliasPost= funk(POSTFIX_REGEX.findall(alias))
        realContents = fitsParser.findAndSplit(realName, re.compile("(?<=[[]).+(?=[]])"), re.compile("\s*,\s*"))
        aliasContents = fitsParser.findAndSplit(alias, re.compile("(?<=[[]).+(?=[]])"), re.compile("\s*,\s*"))
        commands = list()
        
        for i in range(len(realContents)):
            commands.append(realPre+realContents[i]+realPost+" as "+aliasPre+aliasContents[i]+aliasPost)

        return commands
    
    def execSetColours(self, value):
        N = int(value)
        self.Ncolours = N
    
    def setStatement(self, statment):
        statment = re.sub("\s*set\s*", "", statment)
        field = fitsParser.findAndRemove(statment, re.compile('.+='), re.compile('\s*='))[0]
        value = fitsParser.findAndRemove(statment, re.compile('=.+'), re.compile('=\s*'))[0]
        field = str.strip(field)
        value = str.strip(value)
        switch = {
            'colours' : fitsParser.execSetColours
        }
        func = switch.get(field)
        func(self, value)
        
    def in_out_uncert(self):
        #uncertanites corresponding to sepcific inputs and outputs should differ only by a leading d
        self.input_uncert = filter(lambda name : name[1:] in self.inputs, self.uncert)
        copy = filter(lambda uncert : uncert not in self.input_uncert, self.uncert)
        self.output_uncert = filter(lambda name : name[1:] in self.outputs, copy)   
    
        

    @staticmethod
    def findAndSplit(target, find, splitRe):
        findlist = find.findall(target)
        splitlist = list()
        for x in findlist:
            for string in splitRe.split(x):
                splitlist.append(string)
        return splitlist

    def getFiles(self):
        return self.getField('filename')

    def getField(self, field):
        return [self.__dict__[field]] + self.__other__.getField(field) if self.__other__ != None else [self.__dict__[field]]
    
    def getData(self):
        return self.getField('data')

    def joinData(self):
        dataList = self.getData()
        
        if len(dataList) == 1:
            return self.data

        all_true = lambda x : False not in x
        #collect the common fields between the data
        fields = list(filter(lambda x : all_true(pd.DataFrame([x in data.keys()  for data in dataList[1:]])), dataList[0].keys()))
        print(fields)