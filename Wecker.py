#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import datetime
import logging
import os, subprocess, sys
import RPi.GPIO as GPIO
from crontab import CronTab
from rotary import RotaryEncoder
from Adafruit_LED_Backpack import SevenSegment
from Properties import Properties
from Transition import Transition
from State import State
from ActionButton import ActionButton
from Request import Request
from StateMachine import StateMachine

class Wecker:
    musicPlays=False
    showMenu=False
    editMenu=False
    pause=1
    menuItem=0
    
    prop = Properties()
    alarmtime = prop.getProperty("Weckzeit")
    volume = int(prop.getProperty("Lautstaerke"))
    alarm = prop.getProperty("Alarm")
    playlist = prop.getProperty("Playlist")
    playlists = []
    segment = {}
    stateMachine = {}


    def __init__(self, segment):
        logging.info("Initialisiere Wecker")
        self.segment = segment
        
        subprocess.Popen(["mpc", "clear"], stdout=subprocess.PIPE).communicate()
        subprocess.Popen(["mpc", "load", self.playlist], stdout=subprocess.PIPE).communicate()
        
        self.playlists = self.getAvailablePlayLists()
        
    def switch_event(self, event):
        if event == RotaryEncoder.CLOCKWISE:
            self.stateMachine.apply(ActionButton.ROTATE_UP)
        elif event == RotaryEncoder.ANTICLOCKWISE:
            self.stateMachine.apply(ActionButton.ROTATE_DOWN)
    

    def buttonPressed(self, channel):
        if channel == BUTTON_L:
                logging.info("Linker Knopf gedrückt")
                self.stateMachine.apply(ActionButton.BUTTON_LEFT)
        elif channel == BUTTON_R:
                logging.info("Rechter Knopf gedrückt")
                self.stateMachine.apply(ActionButton.BUTTON_RIGHT)

    def switchAlarm(self, channel):
        logging.info("Alarm Schalter = " + str(GPIO.input(SWITCH)) + " (war " + str(self.alarm) + ")")
        if (self.alarm != GPIO.input(SWITCH)):
            logging.warn("Alarm geändert")
            self.alarm = GPIO.input(SWITCH)
            wz = int(self.alarmtime)
            minutes = wz % 100
            hours = int(wz / 100)

            self.prop.setProperty("Alarm", self.alarm)

            if (self.alarm):
                self.createCron(hours, minutes)
            else:
                self.deleteCrons()


    def musicIsPlaying(self):
        logging.info("Prüfe ob Musik schon spielt...")
        mpcCall = ["mpc"] + sys.argv[1:]
        inp, err = subprocess.Popen(mpcCall, stdout=subprocess.PIPE).communicate()
        inp = inp.split("\n")
        if len(inp) > 2:
            logging.info("Musik spielt")
            return True
        else:
            logging.info("Musik spielt nicht")
            return False

    def getPlayListID(self, pl):
        try:
            return self.playlists.index(pl)
        except:
            return 0

    def getAvailablePlayLists(self):
        inp, err = subprocess.Popen(["mpc", "lsplaylists"], stdout=subprocess.PIPE).communicate()
        inp = inp.split("\n")
        playlist_names = []
        for pl in inp:
            if pl:
                logging.debug(pl)
                playlist_names.append(pl)
        return playlist_names


    def musicStart(self):
        if self.musicIsPlaying():
            self.musicStop()
            self.stateMachine.request.state = State.Uhrzeit
        else:
            logging.info("Starte Playback")
            self.musicPlays = True
            subprocess.Popen(["mpc", "play"], stdout=subprocess.PIPE).communicate()
        
    def musicStop(self):
        logging.info("Stoppe Playback")
        self.musicPlays = False
        subprocess.Popen(["mpc", "stop"], stdout=subprocess.PIPE).communicate()
        self.prop.setProperty("Lautstaerke", self.volume)

    def musicVolUp(self):
        if self.volume < 100:
            self.volume = self.volume +1
            subprocess.Popen(["mpc", "volume", str(self.volume)], stdout=subprocess.PIPE).communicate()

        self.segment.clear()
        self.segment.print_number_str(str(self.volume))
        self.segment.write_display()

    def musicVolDown(self):
        if self.volume > 0:
            self.volume = self.volume -1
            subprocess.Popen(["mpc", "volume", str(self.volume)], stdout=subprocess.PIPE).communicate()

        self.segment.clear()
        self.segment.print_number_str(str(self.volume))
        self.segment.write_display()

    def musicNext(self):
        logging.info("Nächster Playlist-Eintrag")
        i = self.getPlayListID(self.playlist)
        i = i+1
        if (i >= len(self.playlists)):
            i = 0

        self.playlist = self.playlists[i]
        self.prop.setProperty("Playlist", self.playlist)
        logging.info("Neuer Playlist-Eintrag " + str(i) + " = " + self.playlist + " (total " + str(len(self.playlists)) + ")")

        self.segment.clear()
        self.segment.print_number_str(str(i))
        self.segment.write_display()

        subprocess.Popen(["mpc", "clear"], stdout=subprocess.PIPE).communicate()
        subprocess.Popen(["mpc", "load", self.playlist], stdout=subprocess.PIPE).communicate()
        self.musicStart()
        

    def musicPrev(self):
        logging.info("Vorheriger Playlist-Eintrag")
        i = self.getPlayListID(self.playlist)
        i = i-1
        if (i < 0):
            i = len(self.playlists) - 1

        self.playlist = self.playlists[i]
        self.prop.setProperty("Playlist", self.playlist)
        logging.info("Neuer Playlist-Eintrag " + str(i) + " = " + self.playlist + " (total " + str(len(self.playlists)) + ")")

        self.segment.clear()
        self.segment.print_number_str(str(i))
        self.segment.write_display()

        subprocess.Popen(["mpc", "clear"], stdout=subprocess.PIPE).communicate()
        subprocess.Popen(["mpc", "load", self.playlist], stdout=subprocess.PIPE).communicate()
        self.musicStart()


    def menuShow(self):
        if (self.stateMachine.request.state is State.Uhrzeit or self.stateMachine.request.state is State.Menu1) and self.musicIsPlaying():
            logging.info("Stoppe Musik")
            self.musicStop()
            self.stateMachine.apply(ActionButton.CANCEL)

            logging.info("Musik pausiert für 7 Minuten")
            p1 = subprocess.Popen(["/bin/echo", "mpc", "play"], stdout=subprocess.PIPE)
            subprocess.Popen(["at", "now", "+", "7min"], stdin=p1.stdout, stdout=subprocess.PIPE).communicate()
        else:
            logging.info("Zeige Menü")
            if self.stateMachine.request.state is State.Menu1:
                logging.info("Menu 1 - Alarmzeit einstellen")
                self.segment.clear()
                logging.info("Alarmzeit:" +str(self.alarmtime))
                self.segment.print_number_str(self.alarmtime)
                self.segment.set_decimal(0, True)
                self.segment.write_display()

            elif self.stateMachine.request.state is State.Menu2:
                logging.info("Menu 2")
                self.segment.clear()
                self.segment.set_decimal(1, True)
                self.segment.write_display()

            elif self.stateMachine.request.state is State.Menu3:
                logging.info("Menu 3")
                self.segment.clear()
                self.segment.set_decimal(2, True)
                self.segment.write_display()

            elif self.stateMachine.request.state is State.Menu4:
                logging.info( "Menu4")
                self.segment.clear()
                self.segment.set_decimal(3, True)
                self.segment.write_display()

            elif self.stateMachine.request.state is State.Playlist:
                logging.info("Menu Paylist")
                self.segment.clear()
                i = self.getPlayListID(self.playlist)
                self.segment.print_number_str(str(i))
                self.segment.write_display()


    def menuSave(self):
        logging.info("Speichere Einstellungen")
        if self.stateMachine.request.state is State.Menu1:
            logging.info("Speichere Weckzeit " + str(self.alarmtime))
            self.prop.setProperty("Weckzeit", self.alarmtime)
            if (self.alarm):
                self.deleteCrons()

                wz = int(self.alarmtime)
                minutes = wz % 100
                hours = int(wz / 100)
                self.createCron(hours, minutes)

    
    def menuIncrement(self):
        if self.stateMachine.request.state is State.Edit_Menu1:
            wz = int(self.alarmtime)
            minutes = wz % 100
            hours = int(wz / 100)

            minutes = minutes + 1
            if minutes >= 60:
                minutes = 0
                hours = hours + 1
            m = str(minutes)
            if minutes < 10:
                m = "0" +m

            if hours == 24:
                hours = 0
            h = str(hours)
            if hours < 10:
                h = "0" +h

            self.alarmtime = h + m
            
            logging.debug(str(wz) + " -> " + h + ":" + m)
            self.segment.clear()
            self.segment.print_number_str(self.alarmtime)
            self.segment.set_decimal(0, True)
            self.segment.write_display()
    

    def menuDecrement(self):
        if self.stateMachine.request.state is State.Edit_Menu1:
            wz = int(self.alarmtime)
            minutes = wz % 100
            hours = int(wz / 100)

            minutes = minutes - 1
            if minutes < 0:
                minutes = 59
                hours = hours - 1
            m = str(minutes)
            if minutes < 10:
                m = "0" +m

            if hours < 0:
                hours = 23
            h = str(hours)
            if hours < 10:
                h = "0" +h

            self.alarmtime = h + m
          
            logging.debug(str(wz) + " -> " + h + ":" + m)
            self.segment.clear()
            self.segment.print_number_str(self.alarmtime)
            self.segment.set_decimal(0, True)
            self.segment.write_display()

    def createCron(self, hours, minutes):
        logging.info("Erstelle cron " + str(hours) + "h " + str(minutes) + "m")
        cron = CronTab(user='pi')
        job  = cron.new(command='/usr/bin/mpc play')
        job.hour.on(hours)
        job.minute.on(minutes)
        job.enable()
        logging.info("Cron aktiv? " + str(job.is_enabled()))
        cron.write_to_user( user='pi' )

    def deleteCrons(self):
        logging.info("Lösche alle crons")
        cron = CronTab(user='pi')
        cron.remove_all()
        cron.write_to_user( user='pi' )        
        for job in cron:
            logging.debug(str(job))
            cron.remove( job )
        cron.write_to_user( user='pi' )        

logging.basicConfig(filename='wecker.log',level=logging.INFO)


BUTTON_L=33     # GPIO 13 = Pin 33
BUTTON_R=32     # GPIO 12 = Pin 32
SWITCH=29       # GPIO  5 = Pin 29
ROTARY_UP=11    # GPIO 17 = Pin 11
ROTARY_DOWN=13  # GPIO 27 = Pin 13


GPIO.setmode(GPIO.BOARD)
GPIO.setup(BUTTON_R, GPIO.IN) # right button
GPIO.setup(BUTTON_L, GPIO.IN, pull_up_down=GPIO.PUD_UP) # left button
GPIO.setup(SWITCH, GPIO.IN) # switch

segment = SevenSegment.SevenSegment()
wecker = Wecker(segment)

# Menu state transitions
DEFAULT = [ Transition(State.Uhrzeit,     ActionButton.BUTTON_RIGHT,  State.Menu1, wecker.menuShow), 
            Transition(State.Uhrzeit,     ActionButton.BUTTON_LEFT,   State.Play, wecker.musicStart), 
            Transition(State.Menu1,       ActionButton.CANCEL,        State.Uhrzeit),
            Transition(State.Play,        ActionButton.BUTTON_LEFT,   State.Uhrzeit, wecker.musicStop), 
            Transition(State.Play,        ActionButton.BUTTON_RIGHT,  State.Playlist, wecker.menuShow), 
            Transition(State.Play,        ActionButton.ROTATE_UP,     State.Play, wecker.musicVolUp), 
            Transition(State.Uhrzeit,     ActionButton.ROTATE_UP,     State.Play, wecker.musicVolUp), 
            Transition(State.Play,        ActionButton.ROTATE_DOWN,   State.Play, wecker.musicVolDown), 
            Transition(State.Uhrzeit,     ActionButton.ROTATE_DOWN,   State.Play, wecker.musicVolDown), 
            Transition(State.Playlist,    ActionButton.BUTTON_RIGHT,  State.Play), 
            Transition(State.Playlist,    ActionButton.BUTTON_LEFT,   State.Play), 
            Transition(State.Playlist,    ActionButton.ROTATE_UP,     State.Playlist, wecker.musicNext), 
            Transition(State.Playlist,    ActionButton.ROTATE_DOWN,   State.Playlist, wecker.musicPrev), 
            Transition(State.Menu1,       ActionButton.BUTTON_RIGHT,  State.Edit_Menu1),
            Transition(State.Menu1,       ActionButton.BUTTON_LEFT,   State.Uhrzeit),
            #Transition(State.Menu1,       ActionButton.ROTATE_UP,     State.Menu2, wecker.menuShow),
            #Transition(State.Menu1,       ActionButton.ROTATE_DOWN,   State.Menu4, wecker.menuShow),
            #Transition(State.Menu2,       ActionButton.BUTTON_RIGHT,  State.Edit_Menu2),
            #Transition(State.Menu2,       ActionButton.BUTTON_LEFT,   State.Uhrzeit),
            #Transition(State.Menu2,       ActionButton.ROTATE_UP,     State.Menu3, wecker.menuShow),
            #Transition(State.Menu2,       ActionButton.ROTATE_DOWN,   State.Menu1, wecker.menuShow),
            #Transition(State.Menu3,       ActionButton.BUTTON_RIGHT,  State.Edit_Menu4),
            #Transition(State.Menu3,       ActionButton.BUTTON_LEFT,   State.Uhrzeit),
            #Transition(State.Menu3,       ActionButton.ROTATE_UP,     State.Menu4, wecker.menuShow),
            #Transition(State.Menu3,       ActionButton.ROTATE_DOWN,   State.Menu2, wecker.menuShow),
            #Transition(State.Menu4,       ActionButton.BUTTON_RIGHT,  State.Edit_Menu4),
            #Transition(State.Menu4,       ActionButton.BUTTON_LEFT,   State.Uhrzeit),
            #Transition(State.Menu4,       ActionButton.ROTATE_UP,     State.Menu1, wecker.menuShow),
            #Transition(State.Menu4,       ActionButton.ROTATE_DOWN,   State.Menu3, wecker.menuShow),
            Transition(State.Edit_Menu1,  ActionButton.BUTTON_RIGHT,  State.Menu1, wecker.menuSave),
            Transition(State.Edit_Menu1,  ActionButton.BUTTON_LEFT,   State.Menu1, wecker.menuShow),
            Transition(State.Edit_Menu1,  ActionButton.ROTATE_UP,     State.Edit_Menu1, wecker.menuIncrement),
            Transition(State.Edit_Menu1,  ActionButton.ROTATE_DOWN,   State.Edit_Menu1, wecker.menuDecrement),
            Transition(State.Edit_Menu2,  ActionButton.BUTTON_RIGHT,  State.Menu2, wecker.menuShow),
            Transition(State.Edit_Menu2,  ActionButton.BUTTON_LEFT,   State.Menu2, wecker.menuShow),
            Transition(State.Edit_Menu2,  ActionButton.ROTATE_UP,     State.Edit_Menu2, wecker.menuIncrement),
            Transition(State.Edit_Menu2,  ActionButton.ROTATE_DOWN,   State.Edit_Menu2, wecker.menuDecrement),
            Transition(State.Edit_Menu3,  ActionButton.BUTTON_RIGHT,  State.Menu3, wecker.menuShow),
            Transition(State.Edit_Menu3,  ActionButton.BUTTON_LEFT,   State.Menu3, wecker.menuShow),
            Transition(State.Edit_Menu3,  ActionButton.ROTATE_UP,     State.Edit_Menu3, wecker.menuIncrement),
            Transition(State.Edit_Menu3,  ActionButton.ROTATE_DOWN,   State.Edit_Menu3, wecker.menuDecrement),
            Transition(State.Edit_Menu4,  ActionButton.BUTTON_RIGHT,  State.Menu4, wecker.menuShow),
            Transition(State.Edit_Menu4,  ActionButton.BUTTON_LEFT,   State.Menu4, wecker.menuShow),
            Transition(State.Edit_Menu4,  ActionButton.ROTATE_UP,     State.Edit_Menu4, wecker.menuIncrement),
            Transition(State.Edit_Menu4,  ActionButton.ROTATE_DOWN,   State.Edit_Menu4, wecker.menuDecrement)]

request = Request(State.Uhrzeit)
sm = StateMachine(DEFAULT, request)
wecker.stateMachine = sm

# Reqister interrupts
GPIO.add_event_detect(BUTTON_R, GPIO.FALLING, callback=wecker.buttonPressed, bouncetime=600)
GPIO.add_event_detect(BUTTON_L, GPIO.FALLING, callback=wecker.buttonPressed, bouncetime=600)
GPIO.add_event_detect(SWITCH, GPIO.BOTH, callback=wecker.switchAlarm, bouncetime=600)
RotaryEncoder(ROTARY_DOWN, ROTARY_UP, wecker.switch_event)


# Create display instance on default I2C address (0x70) and bus number.
segment.begin()
segment.set_brightness(0)

logging.info("Starte Wecker")

while True:
    if request.state is State.Uhrzeit or request.state is State.Play:
        now = datetime.datetime.now()
        hour = now.hour
        minute = now.minute
        second = now.second

        segment.clear()
        segment.set_digit(0, int(hour / 10))     # Tens
        segment.set_digit(1, hour % 10)          # Ones
        segment.set_digit(2, int(minute / 10))   # Tens
        segment.set_digit(3, minute % 10)        # Ones
        segment.set_colon(second % 2)            # Toggle colon at 1Hz

        if GPIO.input(SWITCH):
            segment.set_decimal(1, True)
        else:
            segment.set_decimal(1, False)

        segment.write_display()

    time.sleep(0.25)

GPIO.cleanup()
