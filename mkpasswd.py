#!/usr/bin/env python2

# mkpasswd: Create random password according to user specification.
#
# This is a Python re-write of the mkpasswd program written in Tcl
# by Don Libes of NIST. This version of the code does not support
# automated setting of the generated password via calling passwd or
# friends.

import sys
import json
import random


# Default arguments
defaultArgs = {
    'length'     : 20,
    'minNum'     : 5,
    'minLower'   : 5,
    'minUpper'   : 5,
    'minSpecial' : 2,
    'distribute' : True
}

args = {}
assert len(sys.argv) in [1,2], "Too few or too many arguments."
if 2 == len(sys.argv):
    args = json.loads(sys.argv[1])

# Fill in default arguments
for k in defaultArgs.keys():
    if not k in args:
        args[k] = defaultArgs[k]


length     = args['length']
minNum     = args['minNum']
minLower   = args['minLower']
minUpper   = args['minUpper']
minSpecial = args['minSpecial']
distribute = args['distribute']

if minNum + minLower + minUpper + minSpecial > length:
    assert False, "Impossible to generate %d-character password " \
                  "with %d numbers, %d lowercase letters, " \
                  "%d uppercase letters and " \
                  "%d special characters." % (length, minNum, minLower, minUpper, minSpecial)

minLower = length - (minNum + minUpper + minSpecial)

# Password characters typed by the left and right hand
lpass = []
rpass = []

# Choose left or right starting hand
initiallyLeft = random.choice([True, False])

lkeys = ['q', 'w', 'e', 'r', 't', 'a', 's', 'd', 'f', 'g', 'z', 'x', 'c', 'v', 'b']
rkeys = ['y', 'u', 'i', 'o', 'p', 'h', 'j', 'k', 'l', 'n', 'm']
lnums = ['1', '2', '3', '4', '5', '6']
rnums = ['7', '8', '9', '0']
lspec = ['!', '@', '#', '$', '%']
rspec = ['^', '&', '*', '(', ')', '-', '=', '_', '+', '[', ']', '{', '}', '\\', '|', ';', ':', '\'', '"', '<', '>', ',', '.', '?', '/']

# If distribute is set to False we merge all the 
# lists
if not distribute:
    lkeys = lkeys + rkeys
    rkeys = lkeys

    lnums = lnums + rnums
    rnums = lnums

    lspec = lspec + rspec
    rspec = lspec

# Insert x into lst at a random position
def randomInsert(lst, x):
    if 0 == len(lst):
        lst.append(x)
    else:
        lst.insert(random.randrange(0, len(lst)+1), x)

# Split x into left and right
def splitHalf(x):
    return x/2, x - x/2

# Insert selected values as chosen by the functions f and g.
# This function access the global variables
# isLeft, lpass and rpass.
def insertChoice(n, f, g):
    global isLeft
    global lpass
    global rpass

    if isLeft:
        left, right = splitHalf(n)
        isLeft = 1 - (n%2)
    else:
        right, left = splitHalf(n)
        isLeft = n%2
    
    for i in range(left):
        randomInsert(lpass, f())
    for i in range(right):
        randomInsert(rpass, g())

isLeft = initiallyLeft

insertChoice(minNum    , lambda: random.choice(lnums)        , lambda: random.choice(rnums))
insertChoice(minLower  , lambda: random.choice(lkeys)        , lambda: random.choice(rkeys))
insertChoice(minUpper  , lambda: random.choice(lkeys).upper(), lambda: random.choice(rkeys).upper())
insertChoice(minSpecial, lambda: random.choice(lspec)        , lambda: random.choice(rspec))

# Fill up with empty spaces so that we can iterate over
# both lists at the same time.
while len(lpass) < len(rpass):
    randomInsert(lpass, "")
while len(rpass) < len(lpass):
    randomInsert(rpass, "")

password = ""
for i in range(len(lpass)): # == range(len(rpass))
    if initiallyLeft:
        password = password + lpass[i] + rpass[i]
    else:
        password = password + rpass[i] + lpass[i]

assert len(password) == length, "Internal error."

print password

