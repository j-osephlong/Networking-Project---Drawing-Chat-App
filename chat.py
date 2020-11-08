import user, dbinterface as db
from user import tokenAuth
from chatSocket import sio
from flask import Flask
from flask import request, render_template, redirect, Response, jsonify, session, make_response, Blueprint
from flask_socketio import SocketIO, join_room, leave_room

from datetime import datetime
import json

chat = Blueprint('chat', __name__, template_folder='templates')

chats = {
            0 : {
                'name': 'Main Chat',
                'creator': 'server',
                'activeSince': datetime.now(),
                'users': [],
                'persistantChats': True,
                'N':0,
                'id': 0
            },
            -1 : {
                'name': 'Testing Room',
                'creator': 'server',
                'activeSince': datetime.now(),
                'users': [],
                'persistantChats': False,
                'N':0,
                'id':-1
            }  
        }

def initChats():
    for chat in chats:
        N = int(db.query('msgs', 'COUNT(*)', 'WHERE chatID = ' + str(chat))[0][0])
        chats[chat]['N'] = N

@chat.route('/chat/makeChat', methods=['POST'])
def makeChat():
    pass

@sio.on('join')
def joinChat(data):
    newToken = tokenAuth(data['userName'], data['token'])
    if not newToken:
        print('badToken')
        return {'error':'invalid-token'}, 401

    if int(data['chatID']) not in chats:
        print('badChat')
        return {'error':'invalid-chatID'}, 400 

    user.userSockets[request.sid] = (data['userName'], int(data['chatID']))

    join_room(int(data['chatID']))
    # print(sio.rooms)
    if data['userName'] not in chats[int(data['chatID'])]['users']:
        chats[int(data['chatID'])]['users'].append(data['userName'])

    print(str(data['chatID'])+" - "+str(chats[int(data['chatID'])]['users']))
 
    sio.emit('userJoined', {'username': data['userName']}, room = int(data['chatID']))
    return {'chatID':data['chatID'], 'newToken':newToken}

@chat.route('/chat/chatInfo', methods=['GET'])
def getChatInfo():
    data = request.json
    return chats[int(data['chatID'])]

@chat.route('/chat/listChats', methods=['GET'])
def listChats():
    #token not required - public info
    return chats

@chat.route('/chat/send', methods=['POST'])
def newMsg():
    data = json.loads(request.data)
    if int(data['chatID']) not in chats:
        return {'error':'invalid-chatID'}, 400

    newToken = tokenAuth(data['userName'], data['token'])
    if newToken == False:
        return {'error': 'invalid-token'}, 401
    
    sio.emit('newMessage', {
        'imgData':data['img'],
        'userName':data['userName'],
        'imgID':int(chats[int(data['chatID'])]['N']),
        'caption': data['caption']
    }, room=int(data['chatID']))

    chats[int(data['chatID'])]['N']+=1

    if chats[int(data['chatID'])]['persistantChats']:
        print('saving msg in chat' + str(data['chatID']))
        db.insert('msgs', (
            str(data['chatID']),
            str(chats[int(data['chatID'])]['N']),
            "\'"+data['userName']+"\'",
            "\'"+str(datetime.now())+"\'",
            "\'"+data['img']+"\'",
            "\'"+data['caption']+"\'" if (data['caption'] != None) else "'None'"
        ))

    return {'newToken': newToken}

@chat.route('/chat/fetch', methods=['POST'])
def sendMsgsBulk():
    data = json.loads(request.data)
    if int(data['chatID']) not in chats:
        return {'error':'invalid-chatID'}, 400

    newToken = tokenAuth(data['userName'], data['token'])
    if newToken == False:
        return {'error': 'invalid-token'}, 401

    offset = data['offset']
    n = data['n']
    chatID = data['chatID']

    messages = db.toJSON('msgs', 
        db.query('msgs', args='WHERE chatID = {c} ORDER BY msgID DESC LIMIT {o}, {n}'.format(c = chatID, o = offset, n = n)),
        ('sentAt', 'chatID'))

    return {'newToken':newToken, 'msgs': messages}

@sio.on('disconnect')
def disconnect():
    username = None
    chatID = None
    sid = None
    for sid in user.userSockets:
        if sid == request.sid:
            sid = request.sid
            break

    if sid == None:
        print("socket " + str(request.sid) + " disconnected")
        return;

    username = user.userSockets[sid][0]
    chatID = user.userSockets[sid][1]
    del user.userSockets[sid]
    leave_room(chatID)
    sio.emit('userLeft', {'username': username}, room = chatID)
    # chats[chatID]['users'].remove(username) <- weird

    print("user " + str(username) + " left chat " + str(chatID))