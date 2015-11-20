__author__ = 'qthomson_l'

import aiml
import os

def aliceBot():
    kernel = aiml.Kernel()
    loadAlice(kernel)
    return kernel

def standardBot():
    kernel = aiml.Kernel()
    loadStandard(kernel)
    return kernel

def loadAlice(kernel):
    os.chdir("/Library/Python/2.7/site-packages/aiml/alice/")
    kernel.learn("startup.xml")
    kernel.respond("load alice")

def loadStandard(kernel):
    os.chdir("/Library/Python/2.7/site-packages/aiml/standard/")
    kernel.learn("startup.xml")
    kernel.respond("load aiml b")

####################################################################


# @respond_to('.')
# def hello_reply_formatting(message):
#     # Format message with italic style
#     message.reply(kernel.respond(message))

# while True:
#     userResponse = raw_input("> ")
#     if userResponse == "exit()":
#         break
#     else:
#         print kernel.respond(userResponse)