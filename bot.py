

import socket
import re
import random
rand = random.SystemRandom()

irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
irc.connect(("irc.foonetic.net", 6667))

def send(msg):
  print("Sending: "+msg)
  irc.send(msg)

inited = False
nick = "EliRPGBot"
send("USER "+nick+" "+nick+" "+nick+" :"+nick+"\r\n")
send("NICK "+nick+"\r\n")

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
  
subs = {}
  
while True:
  data = irc.recv(4096)
  print("Received: "+data)
  
  if data[0:4] == "PING":
    send("PONG "+data[5:]+"\r\n")
    
  parts = data[1:].split(":",1)
  info = parts[0].split(" ")
  msg = parts[1]
  cmd = (info[1] if (len(info) > 1) else "")
  user = info[0].split("!")[0]
    
  if cmd == "001":
    send("MODE "+nick+" +B\r\n")
    send("JOIN #xkcd-qrpg\r\n")
    inited = True
  if (cmd == "PRIVMSG") and (info[2] == "#xkcd-qrpg") and (msg[0] == "!"):
    bot_command = msg[1:].strip()
    
    def_match = re.match(r"def\s+([^\s]+)\s+(.*)", bot_command)
    undef_match = re.match(r"undef\s+([^\s]+)", bot_command)
    if def_match:
      if user not in subs:
        subs[user] = {}
      subs[user][def_match.group(1)] = def_match.group(2)
      send("PRIVMSG #xkcd-qrpg "+user+": defined '"+def_match.group(1)+"' as '"+def_match.group(2)+"'\r\n")
    elif undef_match:
      if user in subs:
        del subs[user][undef_match.group(1)]
      send("PRIVMSG #xkcd-qrpg "+user+": undefined '"+undef_match.group(1)+"'\r\n")
    else:
      output = [bot_command]
    
      subbed = bot_command
      if user in subs:
        for key in subs[user]:
          subbed = subbed.replace(key, subs[user][key])
      
      if subbed != bot_command:
        output.append(subbed)
      
      def roll_repl(match):
        dice = (1 if (match.group(1) == "") else int(match.group(1)))
        sides = int(match.group(2))
        if (dice < 1):
          return "0"
        if (sides < 1):
          return "0"
        if (dice > 30):
          return "(more than 30 dice is too many)"
        if (sides > 100000):
          return "(more than 100000 sides is too many)"
        return "("+"+".join([str(rand.randrange(1,sides+1)) for x in range(dice)])+")"
      
      rolled = re.sub(r"(\d*)[Dd](\d+)", roll_repl, subbed)
      if rolled != subbed:
        output.append(rolled)
    
      try:
        arithmeticked = str(eval_arithmetic(rolled))
        if arithmeticked != rolled:
          output.append(arithmeticked)
      except Exception as e:
        if (str(e).find("eval_arithmetic failed") != -1):
          print(str(e))
        else:
          raise e
      else:
        output[len(output)-1] = chr(2)+output[len(output)-1]+chr(2)
      
      if (len(output) > 1):
        send("PRIVMSG #xkcd-qrpg "+user+": "+" = ".join(output)+"\r\n")
    