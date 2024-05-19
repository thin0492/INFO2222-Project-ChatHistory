'''
models
defines sql alchemy data models
also contains the definition for the room class used to keep track of socket.io rooms

Just a sidenote, using SQLAlchemy is a pain. If you want to go above and beyond, 
do this whole project in Node.js + Express and use Prisma instead, 
Prisma docs also looks so much better in comparison

or use SQLite, if you're not into fancy ORMs (but be mindful of Injection attacks :) )
'''

from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Dict
from datetime import datetime



# data models
class Base(DeclarativeBase):
    pass

# model to store user information
class User(Base):
    __tablename__ = "user"
    
    # looks complicated but basically means
    # I want a username column of type string,
    # and I want this column to be my primary key
    # then accessing john.username -> will give me some data of type string
    # in other words we've mapped the username Python object property to an SQL column of type String 
    username: Mapped[str] = mapped_column(String, primary_key=True)
    password: Mapped[str] = mapped_column(String)
    salt: Mapped[str]= mapped_column(String) #WAYNE CODE
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("role.id"))
    role: Mapped["Role"] = relationship("Role")
    muted: Mapped[bool] = mapped_column(Boolean, default=False)

class Role(Base):
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    

# stateful counter used to generate the room id
class Counter():
    def __init__(self):
        self.counter = 0
    
    def get(self):
        self.counter += 1
        return self.counter

# Room class, used to keep track of which username is in which room
class Room():
    def __init__(self):
        self.counter = Counter()
        # dictionary that maps the username to the room id
        # for example self.dict["John"] -> gives you the room id of 
        # the room where John is in
        self.dict: Dict[str, int] = {}

    def create_room(self, sender: str, receiver: str) -> int:
        room_id = self.counter.get()
        self.dict[sender] = room_id
        self.dict[receiver] = room_id
        return room_id
    
    def join_room(self,  sender: str, room_id: int) -> int:
        self.dict[sender] = room_id

    def leave_room(self, user):
        if user not in self.dict.keys():
            return
        del self.dict[user]

    # gets the room id from a user
    def get_room_id(self, user: str):
        if user not in self.dict.keys():
            return None
        return self.dict[user]
    
class Friendship(Base):
    __tablename__ = "friendship"

    user1: Mapped[str] = mapped_column(String, primary_key=True)
    user2: Mapped[str] = mapped_column(String, primary_key=True)

class FriendRequest(Base):
    __tablename__ = "friend_request"

    sender: Mapped[str] = mapped_column(String, primary_key=True)
    receiver: Mapped[str] = mapped_column(String, primary_key=True)

class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender: Mapped[str] = mapped_column(String)
    receiver: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    key: Mapped[str] = mapped_column(String)
    mac: Mapped[str] = mapped_column(String)
    sender_password: Mapped[str] = mapped_column(String)
    receiver_password: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ChatInvitation(Base):
    __tablename__ = "chat_invitation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender: Mapped[str] = mapped_column(String, ForeignKey("user.username"))
    receiver: Mapped[str] = mapped_column(String, ForeignKey("user.username"))
    room_id: Mapped[int] = mapped_column(Integer)

class KnowledgeArticle(Base):
    __tablename__ = "knowledge_article"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String, ForeignKey("user.username"))

class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(String)
    author: Mapped[str] = mapped_column(String, ForeignKey("user.username"))
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("knowledge_article.id"))