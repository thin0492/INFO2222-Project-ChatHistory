'''
socket_routes
file containing all the routes related to socket.io
'''


from flask_socketio import join_room, emit, leave_room
from flask import request
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

try:
    from __main__ import socketio
except ImportError:
    from app import socketio

from models import Room

import db
import app

room = Room()
online_users = {}

# when the client connects to a socket
# this event is emitted when the io() function is called in JS
"""@socketio.on('connect')
def connect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    if room_id is None or username is None:
        return
    # socket automatically leaves a room on client disconnect
    # so on client connect, the room needs to be rejoined
    join_room(int(room_id))
    emit("incoming", (f"{username} has connected", "green"), to=int(room_id))"""
@socketio.on('connect')
def connect():
    username = request.cookies.get("username")
    if username:
        join_room(username)
        online_users[username] = request.sid
        
        # Emit events to update the client-side UI with initial data
        friends = db.get_friends(username)
        friend_requests = db.get_friend_requests(username)
        sent_friend_requests = db.get_sent_friend_requests(username)
        print(f"User {username} connected")
        print("Online users: ", online_users)  
        
    
        emit("friends_list", friends, room=username)
        emit("friend_requests_list", [request.sender for request in friend_requests], room=username)
        emit("sent_friend_requests_list", [request.receiver for request in sent_friend_requests], room=username)
        emit("online", {'user_list': list(online_users.keys())}, broadcast=True)


        room_id = request.cookies.get("room_id")
        if room_id:
            join_room(int(room_id))
            emit("incoming", (f"{username} has connected", "green"), to=int(room_id))

# event when client disconnects
# quite unreliable use sparingly
@socketio.on('disconnect')
def disconnect():
    username = request.cookies.get("username")
    room_id = request.cookies.get("room_id")
    if room_id is None or username is None:
        return
    emit("incoming", (f"{username} has disconnected", "red"), to=int(room_id))
    
    
    
#event for when user closes browser 
@socketio.on('logoff')
def handle_disconnect():
   for username, sid in online_users.items():
        if sid == request.sid:
            print(f"Usern {username} logged off")
            del online_users[username]
            print("Online users: ", online_users)    
            #emit event to inform clients about the online status change 
            emit("offline", {'username': username},broadcast=True)
            break

# send message event handler
#@socketio.on("send")
#def send(username, message, room_id):
#    emit("incoming", (f"{username}: {message}"), to=room_id)

@socketio.on("send")
def send(sender, receiver, encryptedMessage, key, mac, room_id):

    sender_user = db.get_user(sender)
    receiver_user = db.get_user(receiver)
    sender_password = sender_user.password if sender_user else None
    receiver_password = receiver_user.password if receiver_user else None
    
    if sender_password and receiver_password:
        # The server acts as a middleman and does not decrypt the message
        db.insert_message(sender, receiver, encryptedMessage, key, mac, sender_password, receiver_password) #NEW CODE
        print(f"Message stored in the database")
        emit("incoming", (sender, encryptedMessage, key, mac), to=room_id)
    else:
        print("Sender or receiver password not found in the database")

# join room event handler
# sent when the user joins a room
@socketio.on("join")
def join(sender_name, receiver_name):

    sender = app.authenticate_user(sender_name) #WAYNE CODE
    receiver = app.authenticate_user(receiver_name) #WAYNE CODE
    print(f"Sender name: {sender_name}, Reciever Name: {receiver_name}")

    

    
    receiver = db.get_user(receiver_name)
    if receiver is None:
        return "Unknown receiver!"
    
    sender = db.get_user(sender_name)
    if sender is None:
        return "Unknown sender!"
    
    sender_hashed_password = sender.password
    receiver_hashed_password = receiver.password

    chat_history = db.get_chat_history(sender_name, receiver_name, sender_hashed_password, receiver_hashed_password)
    print(f"Retrieved chat history: {chat_history}")

    if not db.are_friends(sender_name, receiver_name):
        return "You must be friends to join the chatroom!"

    room_id = room.get_room_id(receiver_name)

    for message in chat_history: #NEW CODE
        print(f"Emitting message: {message}")
        emit("incoming", (message.sender, message.content, message.key, message.mac), room=request.sid) #NEW CODE

    # if the user is already inside of a room 
    if room_id is not None:
        
        room.join_room(sender_name, room_id)
        join_room(room_id)
        # emit to everyone in the room except the sender
        emit("incoming", (f"{sender_name} has joined the room.", "green"), to=room_id, include_self=False)
        # emit only to the sender
        emit("incoming", (f"{sender_name} has joined the room. Now talking to {receiver_name}.", "green"))
        return room_id

    # if the user isn't inside of any room, 
    # perhaps this user has recently left a room
    # or is simply a new user looking to chat with someone
    room_id = room.create_room(sender_name, receiver_name)
    join_room(room_id)
    emit("incoming", (f"{sender_name} has joined the room. Now talking to {receiver_name}.", "green"), to=room_id)
    return room_id

# leave room event handler
@socketio.on("leave")
def leave(username, room_id):
    emit("incoming", (f"{username} has left the room.", "red"), to=room_id)
    leave_room(room_id)
    room.leave_room(username)

@socketio.on("friend_request_sent")
def handle_friend_request_sent(sender, receiver):
    db.send_friend_request(sender, receiver)
    emit("friend_request_received", (sender,), room=receiver)
    emit("friend_request_sent_success", (receiver,), room=sender)

@socketio.on("friend_request_accepted")
def handle_friend_request_accepted(sender, receiver):
    if db.accept_friend_request(sender, receiver):
        emit("friend_added", (receiver,), room=sender)
        emit("friend_added", (sender,), room=receiver)
        emit("friend_request_removed", (sender,), room=receiver)
        emit("friend_request_accepted", (sender, receiver), room=sender)
        emit("friends_list_updated", db.get_friends(sender), room=sender)
        emit("friends_list_updated", db.get_friends(receiver), room=receiver)

@socketio.on("friend_request_rejected")
def handle_friend_request_rejected(sender, receiver):
    if db.reject_friend_request(sender, receiver):
        emit("friend_request_rejected", (sender,), room=receiver)
        emit("friend_request_rejected_sender", (receiver,), room=sender)

@socketio.on("friend_request_cancelled")
def handle_friend_request_cancelled(sender, receiver):
    db.reject_friend_request(sender, receiver)
    emit("friend_request_cancelled", (sender, receiver), room=sender)
    emit("friend_request_cancelled_receiver", (sender,), room=receiver)


@socketio.on("friend_removed")
def handle_friend_removed(user1, user2):
    db.remove_friendship(user1, user2)
    emit("friend_removed", (user2,), room=user1)
    emit("friend_removed", (user1,), room=user2)
    emit("friends_list_updated", db.get_friends(user1), room=user1)
    emit("friends_list_updated", db.get_friends(user2), room=user2)


@socketio.on("add_friend_to_chat")
def add_friend_to_chat(room_id, friend_username):
    sender = request.cookies.get("username")
    db.send_chat_invitation(sender, friend_username, room_id)
    emit("chat_invitation_sent", to=friend_username)

@socketio.on("accept_chat_invitation")
def accept_chat_invitation(invitation_id):
    invitation = db.get_chat_invitation(invitation_id)
    if invitation:
        room.join_room(invitation.receiver, invitation.room_id)
        emit("incoming", (f"{invitation.receiver} has joined the chat.", "green"), to=invitation.room_id)
        db.remove_chat_invitation(invitation_id)

@socketio.on("reject_chat_invitation")
def reject_chat_invitation(invitation_id):
    db.remove_chat_invitation(invitation_id)
