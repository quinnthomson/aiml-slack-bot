# -*- coding: utf-8 -*-

import logging
import re
import time
import traceback
from enum import Enum
import aimlResponder

from slackbot.utils import to_utf8, WorkerPool

logger = logging.getLogger(__name__)

AT_MESSAGE_MATCHER = re.compile(r'^\<@(\w+)\>:? (.*)$')

class MessageType(Enum):
    none = 0
    generalMessage = 1
    atBotMessage = 2
    botMessage = 3

class MessageInfo(object):
    def __init__(self, messageType, message, sender, isChangedMessage, isRulesMessage):
        self.messageType = messageType
        self.message = message
        self.sender = sender
        self.isChangedMessage = isChangedMessage
        self.isRulesMessage = isRulesMessage

class MessageDispatcher(object):

    def __init__(self, slackclient, plugins):
        self._client = slackclient
        self._pool = WorkerPool(self.dispatch_msg)
        self._plugins = plugins
        self.aimlBot = aimlResponder.aliceBot()

    def start(self):
        self._pool.start()

    def dispatch_msg(self, messageInfo):
        print messageInfo.message

        if messageInfo.isChangedMessage == False:
            if messageInfo.isRulesMessage:
                self.dispatchRulesMessage(messageInfo)
            else:
                self.dispatchAIMLMessage(messageInfo)

    def dispatchAIMLMessage(self, messageInfo):
        print messageInfo.sender
        channel = self._client.get_channel(messageInfo.message['channel'])
        print channel._body

        if messageInfo.sender == 'quinn.thomson' or channel.name() == 'beepboop-lab':
            if messageInfo.messageType == MessageType.atBotMessage:
                self._client.rtm_send_message(messageInfo.message['channel'], self.aimlBot.respond(messageInfo.message['text']))

    def dispatchRulesMessage(self, messageInfo):
        text = messageInfo.message['text']

        category = 'listen_to'
        if messageInfo.messageType == MessageType.atBotMessage:
            category = 'respond_to'

        for func, args in self._plugins.get_plugins(category, text):
            if func:
                try:
                    func(Message(self._client, messageInfo.message), *args)
                except:
                    logger.exception('failed to handle message %s with plugin "%s"', text, func.__name__)
                    reply = '[%s] I have problem when handling "%s"\n' % (func.__name__, text)
                    reply += '```\n%s\n```' % traceback.format_exc()
                    self._client.rtm_send_message(messageInfo.message['channel'], reply)

    def parseMessage(self, msg):
        # determine if message was a changed message
        subtype = msg.get('subtype', '')
        messageChanged = False
        if subtype == 'message_changed':
            messageChanged = True

        # determine who sent the message
        botname = self._client.login_data['self']['name']
        try:
            msguser = self._client.users.get(msg['user'])
            username = msguser['name']
        except (KeyError, TypeError):
            if 'username' in msg:
                username = msg['username']
            else:
                return

        # early exit if the message if from the bot itself
        if username == botname:
            return MessageInfo(MessageType.botMessage, msg, botname, messageChanged, False)

        # determine if its an @message
        msgRespondTo = self.msgRespondTo(msg)

        # determine if the bot should reply to the slackbot listen_to or respond_to plugins
        text = msg['text']
        isRulesMessage = False
        for category in ['respond_to', 'listen_to']:
            for func, args in self._plugins.get_plugins(category, text):
                if func:
                    isRulesMessage = True

        if msgRespondTo:
            return MessageInfo(MessageType.atBotMessage, msgRespondTo, username, messageChanged, isRulesMessage)
        else:
            return MessageInfo(MessageType.generalMessage, msg, username, messageChanged, isRulesMessage)

    def msgRespondTo(self, msg):
        text = msg.get('text', '')
        channel = msg['channel']

        if channel[0] == 'C' or channel[0] == 'G':
            m = AT_MESSAGE_MATCHER.match(text)
            if not m:
                return
            atuser, text = m.groups()
            if atuser != self._client.login_data['self']['id']:
                # a channel message at other user
                return
            logger.debug('got an AT message: %s', text)
            msg['text'] = text
        else:
            m = AT_MESSAGE_MATCHER.match(text)
            if m:
                msg['text'] = m.group(2)
        return msg

    def loop(self):
        while True:
            events = self._client.rtm_read()
            for event in events:
                if event.get('type') != 'message':
                    continue
                messageInfo = self.parseMessage(event)
                self._pool.add_task(messageInfo)
            time.sleep(1) # this is what prevents the bot from spewing responses out right away

    def _default_reply(self, msg):
        default_reply = [
            u'Bad command "%s", You can ask me one of the following questions:\n' % msg['text'],
        ]
        default_reply += [u'    • `{0}` {1}'.format(p.pattern, v.__doc__ or "") \
            for p, v in self._plugins.commands['respond_to'].iteritems()]
            
        self._client.rtm_send_message(msg['channel'],
                                     '\n'.join(to_utf8(default_reply)))


class Message(object):
    def __init__(self, slackclient, body):
        self._client = slackclient
        self._body = body

    def _get_user_id(self):
        if 'user' in self._body:
            return self._body['user']

        return self._client.find_user_by_name(self._body['username'])

    def _gen_at_message(self, text):
        text = u'<@{}>: {}'.format(self._get_user_id(), text)
        return text

    def _gen_reply(self, text):
        chan = self._body['channel']
        if chan.startswith('C') or chan.startswith('G'):
            return self._gen_at_message(text)
        else:
            return text

    def reply_webapi(self, text):
        """
            Send a reply to the sender using Web API

            (This function supports formatted message
            when using a bot integration)
        """
        text = self._gen_reply(text)
        self.send_webapi(text)

    def send_webapi(self, text, attachments=None):
        """
            Send a reply using Web API

            (This function supports formatted message
            when using a bot integration)
        """
        self._client.send_message(
            self._body['channel'],
            to_utf8(text),
            attachments=attachments)

    def reply(self, text):
        """
            Send a reply to the sender using RTM API

            (This function doesn't supports formatted message
            when using a bot integration)
        """
        text = self._gen_reply(text)
        self.send(text)

    def send(self, text):
        """
            Send a reply using RTM API

            (This function doesn't supports formatted message
            when using a bot integration)
        """
        self._client.rtm_send_message(
            self._body['channel'], to_utf8(text))

    @property
    def channel(self):
        return self._client.get_channel(self._body['channel'])

    @property
    def body(self):
        return self._body
