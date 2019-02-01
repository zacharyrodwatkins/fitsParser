# fitsParser
This class provided utitlities for working with fits files, building upon astropy's file IO library.
In a fitsParser instance there is:
  - data: a pandas DataFrame object containing the collums of data specified, with keys given by the objects alias
  - tableinfo: a dictionary mapping from the collum name as it appears in fits file, to the units, alias, and format of the collum
  - filename: the name of the fits file
  - include: a list of the included collums
  - inputs: a list of the collums intended to be inputs
  - Outputs: a list of the collums intended to be outputs

## Basic Commands 

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

## Other Commands

  - '-all': Specifiy that all collums in the fits file should be included in 				the data frame. Other commands still aplly, 
			and aliases provided still hold.
  - '-i': Used to specify inputs, and as such will be added to the inputs list.
  - '-0': Specify outputs to be added to outputs list.
  - '-c[x]: to specify order in wavelength for magnitudes is various band. 
			This format allows for the automatic generation of colours. By 
			default, colours are computed with the 2 nearest bands. If one 				wishes to comupute more colours, they could call makeColours(N=2) 				method on a fitsParser object, obviously specifying ones own value 				for N. x can be either an integer or decimal number
	
## Other Notes on Syntax and Beyond
  - All commands/fields are to be on their own lines.
  - Specifiers are always preceded by a dash: - 
  - If either the file name or the commands are passed directly to the fitsParser constructor, they are given precedence over any
	commands that may be secified in the text file.




