# fitsParser
This class provided utitlities for working with fits files, building upon astropy's file IO library.
In a fitsParser instance there is:
  - data: a pandas DataFrame object containing the collums of data specified, with keys given by the objects alias
  - tableinfo: a dictionary mapping from the collum name as it appears in fits file, to the units, alias, and format of the collum
  - filename: the name of the fits file
  - include: a list of the included collums

There are two ways to sepcifiy which collums of the data to include:
  - as a list of strings passed to the constructor
  - as a text file where items are referenced by either their name in the fits file of the collum in which they appear, delimited     
    by new lines. 
 In either of the cases  it is possbible to have the collums appear under an alias in the data frame. 
 For example, if one wanted to have item x appear in the dataFrame under name y, include either 'x as y' in the include list, or    
 have the line x as y in the file
 
 If either the file is empty, or the list is empty, then by default all items in the list are included
 
 To specify the fits file to be read, users can either:
  - pass a filename argument
  - specifiy the fits file name in the include file using the keyword "from"
    Ex: from Data.fits
