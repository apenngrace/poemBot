#!/usr/bin/python

# Vandal Poem of the Day poemBot Printer V3. 
# see http://poetry.lib.uidaho.edu/  
# adapted from Adafruit Python-Thermal-Printer main.py
# https://github.com/adafruit/Python-Thermal-Printer
# this script is designed to run on a headless Raspberry Pi connected to a thermal printer 
# must be run as sudo 

from __future__ import print_function
import RPi.GPIO as GPIO
import subprocess, time, csv, textwrap, random
from thermalPrinter import *

# printer and button set up
ledPin       = 18
buttonPin    = 23
holdTime     = 2     # Duration for button hold (shutdown)
tapTime      = 0.01  # Debounce time for button taps
printer      = Adafruit_Thermal("/dev/ttyAMA0", 19200, timeout=5)

# Print random poem, called on tap 
def printPoem():
    #get a random poem
    randPoem = random.choice(allPoems)
    # nicely wrap the content for the printer
    # csv columns = VPODdate,title,author,poem,book,bookDate,publisher,characters,lines
    # Title and Author are printed in 'M' medium font, limit is 32 character per line
    # poem is printed in 'S' small font, limit is 32 characters per line 
    # book and publisher are in "fontB", limit is 42 character per line 
    wrappedTitle = textwrap.fill(randPoem[1], width=32)
    wrappedBook = textwrap.fill("    from: " + randPoem[4], width=42, subsequent_indent="    ")
    wrappedPoem = ""
    for line in randPoem[3].splitlines():
        wrappedLine = textwrap.fill(line, width=32, subsequent_indent="    ")
        wrappedPoem += wrappedLine +"\n"
    #print the poem on the thermal printer
    printer.justify('L')
    printer.setSize('M')
    printer.println(wrappedTitle + "\n    by " + randPoem[2])
    printer.setSize('S')
    printer.println(wrappedPoem)
    # printer.println(' ')
    printer.writeBytes(0x1B, 0x21, 0x1)
    printer.println(wrappedBook + "\n    " + randPoem[6] + ", " + randPoem[5])
    printer.println("    VPOD " + randPoem[0])
    printer.setSize('S')
    # printer.println(' ')
    printer.justify('C')
    printer.println("A new poem, daily:")
    printer.boldOn()
    printer.println("poetry.lib.uidaho.edu")
    printer.boldOff()
    printer.println(' ')
    printer.println('#DLFforum 2016!')
    printer.println(' ')
    printer.println(' ')
    printer.feed(3)

# Called when button is briefly tapped.  
# prints a random poem
def tap():
  GPIO.output(ledPin, GPIO.HIGH)  # LED on while working
  printPoem()
  GPIO.output(ledPin, GPIO.LOW)

# Called when button is held down.  
# prints goodbye, invokes shutdown process.
def hold():
  GPIO.output(ledPin, GPIO.HIGH)
  printer.println('Goodbye!')
  printer.feed(3)
  subprocess.call("sync")
  subprocess.call(["shutdown", "-h", "now"])
  GPIO.output(ledPin, GPIO.LOW)

# Initialization

# Use Broadcom pin numbers (not Raspberry Pi pin numbers) for GPIO
GPIO.setmode(GPIO.BCM)

# Enable LED and button (w/pull-up on latter)
GPIO.setup(ledPin, GPIO.OUT)
GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# LED on while working
GPIO.output(ledPin, GPIO.HIGH)

# Load up all poems from CSV 
# poem CSV is structured with the columns: 
# VPODdate,title,author,poem,book,bookDate,publisher,characters,lines
# the poem column contains the full text of the poem with no markup, only \n 
# the CSV is in CP437 encoding since the printer only supports this character set
# limited to poems with < 22 lines and 800 characters 
with open('VPOD_22l_800char.csv') as csvPoems:
    allPoems = list(csv.reader(csvPoems, delimiter=','))

# Processor load is heavy at startup; wait a moment to avoid
# stalling during greeting.
time.sleep(30)

# Print greeting
printer.println('     ')
printer.println('Hello!')
printer.println('Ready to print VPOD 15-17.')
printer.feed(3)
GPIO.output(ledPin, GPIO.LOW)

# Poll initial button state and time
prevButtonState = GPIO.input(buttonPin)
prevTime        = time.time()
tapEnable       = False
holdEnable      = False

# Main loop
while(True):

  # Poll current button state and time
  buttonState = GPIO.input(buttonPin)
  t           = time.time()

  # Has button state changed?
  if buttonState != prevButtonState:
    prevButtonState = buttonState   # Yes, save new state/time
    prevTime        = t
  else:                             # Button state unchanged
    if (t - prevTime) >= holdTime:  # Button held more than 'holdTime'?
      # Yes it has.  Is the hold action as-yet untriggered?
      if holdEnable == True:        # Yep!
        hold()                      # Perform hold action (usu. shutdown)
        holdEnable = False          # 1 shot...don't repeat hold action
        tapEnable  = False          # Don't do tap action on release
    elif (t - prevTime) >= tapTime: # Not holdTime.  tapTime elapsed?
      # Yes.  Debounced press or release...
      if buttonState == True:       # Button released?
        if tapEnable == True:       # Ignore if prior hold()
          tap()                     # Tap triggered (button released)
          tapEnable  = False        # Disable tap and hold
          holdEnable = False
      else:                         # Button pressed
        tapEnable  = True           # Enable tap and hold actions
        holdEnable = True

  # LED blinks while idle, for a brief interval every 2 seconds.
  # Pin 18 is PWM-capable and a "sleep throb" would be nice, but
  # the PWM-related library is a hassle for average users to install
  # right now.  Might return to this later when it's more accessible.
  if ((int(t) & 1) == 0) and ((t - int(t)) < 0.15):
    GPIO.output(ledPin, GPIO.HIGH)
  else:
    GPIO.output(ledPin, GPIO.LOW)
