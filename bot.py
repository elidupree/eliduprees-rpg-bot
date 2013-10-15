# Eli Dupree's RPG Bot
# Written in 2013 by Eli Dupree ( web@elidupree.com )
# To the extent possible under law, the author(s) have dedicated all copyright and related and neighboring rights to this software to the public domain worldwide. This software is distributed without any warranty.
# You should have received a copy of the CC0 Public Domain Dedication along with this software. If not, see <http://creativecommons.org/publicdomain/zero/1.0/>.

import socket
import re
import random
import time
import sys
rand = random.SystemRandom()
from PyQt4 import QtCore, QtGui, QtNetwork
from collections import deque
import pickle

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)


nick = "EliRPGBot"
channel = "#xkcd-qrpg"
mirc_colors = ['#ffffff', '#000000', '#000080', '#008000', '#ff0000', '#804040', '#8000ff', '#808000', '#ffff00', '#00ff00', '#008080', '#00ffff', '#0000ff', '#ff00ff', '#808080', '#c0c0c0']
legit_colors = [3,4,5,6,7,9,10,12,13,15]

def eval_arithmetic(string):
  def eval_match(match):
    return " "+str(eval_arithmetic(match.group(1)))+" "
  while True:
    parens_out = re.sub(r"\(([^\(\)]*)\)", eval_match, string)
    if parens_out == string:
      string = parens_out
      break
    string = parens_out
  
  while True:
    def mult_fix(match):
      try:
        return str((int(match.group(1)) // int(match.group(3))) if (match.group(2) == "/") else (int(match.group(1)) * int(match.group(3))))
      except ZeroDivisionError:
        raise Exception("eval_arithmetic failed with string: "+string)
    mult_out = re.sub(r"(-?\d+)\s*([/\*\s])\s*(-?\d+)", mult_fix, string)
    if mult_out == string:
      string = mult_out
      break
    string = mult_out
  
  while True:
    def plus_fix(match):
      return str((int(match.group(1)) + int(match.group(3))) if (match.group(2) == "+") else (int(match.group(1)) - int(match.group(3))))
    plus_out = re.sub(r"(-?\d+)\s*([+-])\s*(-?\d+)", plus_fix, string)
    if plus_out == string:
      string = plus_out
      break
    string = plus_out
  
  try:
    return int(string)
  except ValueError:
    raise Exception("eval_arithmetic failed with string: "+string)

def style_msg(msg):
  def bold_convert(match):
    return chr(2)+match.group(1)+chr(2)
  return re.sub(r"b\((.*)\)", bold_convert, msg)

class bot_control_window(QtGui.QWidget):
  character_slots = []
  inited = False
  message_debt = 0
  send_queue = deque()
  
  def __init__(self):
    super(bot_control_window, self).__init__()
    try:
      self.subs = pickle.load(open("remembered_substitutions", "rb"))
    except:
      self.subs = {}
    self.initUI()
  
  def initUI(self):
    self.irc = QtNetwork.QTcpSocket()
    self.irc.connectToHost("irc.foonetic.net", 6667)
    self.irc.waitForConnected(-1)
    self.irc.readyRead.connect(self.irc_receive_event)
    self.irc_send("USER "+nick+" "+nick+" "+nick+" :"+nick)
    self.irc_send("NICK "+nick)

    self.command_edit = QtGui.QLineEdit()
    self.command_edit.returnPressed.connect(self.command_enter)
    self.gm_edit = QtGui.QLineEdit()
    self.gm_edit.returnPressed.connect(self.gm_enter)
    grid = QtGui.QGridLayout()
    vbox = QtGui.QVBoxLayout()
    vbox.addLayout(grid)
    vbox.addStretch(1)
    
    grid.setColumnStretch(2,1)
    
    grid.addWidget(QtGui.QLabel("Command"), 0, 1)
    grid.addWidget(self.command_edit, 0, 2)
    grid.addWidget(QtGui.QLabel("GM"), 1, 1)
    grid.addWidget(self.gm_edit, 1, 2)
    
    for i in range(0,10):
      name = QtGui.QLineEdit()
      text = QtGui.QLineEdit()
      name.setText("NAME")
      name.setFixedWidth(90)
      name.setStyleSheet('color: '+mirc_colors[legit_colors[i]])
      text.setStyleSheet('color: '+mirc_colors[legit_colors[i]])
      text.character_index = i
      text.returnPressed.connect(self.character_enter)
      self.character_slots.append((name, text))
      grid.addWidget(QtGui.QLabel(str(legit_colors[i])), i+2, 0)
      grid.addWidget(name, i+2, 1)
      grid.addWidget(text, i+2, 2)
    
    self.setLayout(vbox)
    self.setGeometry(100,100,350,500)
    self.setWindowTitle("Eli's RPG Bot")
    self.show()
  
  def command_enter(self):
    cmd = str(self.command_edit.text())
    if cmd == "clear":
      self.send_queue.clear()
    if cmd == "flood safety test":
      for i in range(0,20):
        self.channel_message("flood safety test")
    self.command_edit.setText('')
    
  def gm_enter(self):
    #+chr(3)+"0,1" .. +chr(2)
    self.channel_message(chr(2)+"[GM] "+style_msg(str(self.gm_edit.text())))
    self.gm_edit.setText('')
  def character_enter(self):
    i = self.sender().character_index
    self.channel_message(chr(3)+str(legit_colors[i])+"["+str(self.character_slots[i][0].text())+"] "+style_msg(str(self.sender().text())))
    self.sender().setText('')
  
  def irc_receive_event(self):
    while not self.irc.atEnd():
      self.irc_receive(self.irc.readLine(4096))
      
  def channel_message(self, msg):
    self.irc_send("PRIVMSG "+channel+" :"+msg)
  
  def irc_send(self, msg):
    print("Queueing: "+msg)
    if self.message_debt < 3: # rfc allows up to 5; reserving one to respond to pings and one to play it safe
      self.irc_send_immediate(msg)
    else:
      self.send_queue.append(msg)
    
  def message_paid_off(self):
    self.message_debt = self.message_debt - 1
    if self.message_debt >= 1:
      QtCore.QTimer.singleShot(2000, self.message_paid_off)
    if (self.message_debt < 3) and (len(self.send_queue) > 0):
      self.irc_send_immediate(self.send_queue.popleft())
    
  def irc_send_immediate(self, msg):
    self.message_debt = self.message_debt + 1
    print("Sending: "+msg)
    self.irc.write(msg+"\r\n")
    if self.message_debt == 1:
      QtCore.QTimer.singleShot(2000, self.message_paid_off)
  
    
  def irc_receive(self, data):
    print("Received: "+data)
  
    if data[0:4] == "PING":
      self.irc_send_immediate("PONG "+data[5:])
    
    parts = data[1:].split(":",1)
    info = parts[0].split(" ")
    msg = (parts[1] if (len(parts) > 1) else "")
    cmd = (info[1] if (len(info) > 1) else "")
    user = info[0].split("!")[0]
    
    if cmd == "001":
      self.irc_send("MODE "+nick+" +B")
      self.irc_send("JOIN "+channel)
      self.inited = True
    if (cmd == "PRIVMSG") and (info[2] == channel) and (msg[0] == "!"):
      bot_command = msg[1:].strip()
    
      def_match = re.match(r"def\s+([^\s]+)\s+(.*)", bot_command)
      undef_match = re.match(r"undef\s+([^\s]+)", bot_command)
      if def_match:
        if user not in self.subs:
          self.subs[user] = {}
        self.subs[user][def_match.group(1)] = def_match.group(2)
        self.channel_message(user+": defined '"+def_match.group(1)+"' as '"+def_match.group(2)+"'")
        pickle.dump(self.subs, open("remembered_substitutions", "wb"))
      elif undef_match:
        if user in self.subs and undef_match.group(1) in self.subs[user]:
          del self.subs[user][undef_match.group(1)]
          self.channel_message(user+": undefined '"+undef_match.group(1)+"'")
        else:
          self.channel_message(user+": '"+undef_match.group(1)+"' wasn't defined")
        pickle.dump(self.subs, open("remembered_substitutions", "wb"))
      else:
        output = [bot_command]
    
        subbed = bot_command
        if user in self.subs:
          for key in self.subs[user]:
            subbed = subbed.replace(key, self.subs[user][key])
      
        if subbed != bot_command:
          output.append(subbed)
      
        def roll_repl(match):
          dice = (1 if (match.group(1) == "") else int(match.group(1)))
          sides = int(match.group(2))
          if (dice < 1):
            return "0"
          if (sides < 1):
            return match.group(0)
          if (dice > 30):
            return "(more than 30 dice is too many)"
          if (sides > 100000):
            return "(more than 100000 sides is too many)"
          return "("+"+".join([str(rand.randrange(1,sides+1)) for x in range(dice)])+")"
      
        rolled = re.sub(r"(\d*)[Dd](\d+)", roll_repl, subbed)
        if rolled != subbed:
          output.append(rolled)
    
        def arith_repl(match):
          try:
            return str(eval_arithmetic(match.group(0)))
          except Exception as e:
            if (str(e).find("eval_arithmetic failed") != -1):
              print(str(e))
            else:
              raise e
            return match.group(0)
            
        arithmeticked = re.sub(r"[\d\-(][\s\d+\-*/()]*[\d)]", arith_repl, rolled)
        if arithmeticked != rolled:
          output.append(chr(2)+arithmeticked+chr(2))
        
        if (len(output) > 1):
          self.channel_message(user+": "+" = ".join(output))
        
        
app = QtGui.QApplication(sys.argv)
control_window = bot_control_window()
sys.exit(app.exec_())

