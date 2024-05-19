from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload
from models import *
from pathlib import Path
import secrets
import hashlib

Path("database").mkdir(exist_ok=True)

engine = create_engine("sqlite:///database/main.db", echo=False)

Base.metadata.create_all(engine)

def insert_user(username: str, password: str, salt: str, role_id: int):
    with Session(engine) as session:
        user = User(username=username, password=password, salt=salt, role_id=role_id)
        session.add(user)
        session.commit()

def get_user(username: str):
    with Session(engine) as session:
        return session.query(User).options(joinedload(User.role)).get(username)
    
def get_friends(username: str):
    with Session(engine) as session:
        user = session.get(User, username)
        if user is None:
            return []
        friendships = session.query(Friendship).filter(
            (Friendship.user1 == username) | (Friendship.user2 == username)
        ).all()
        friends = set()
        for friendship in friendships:
            if friendship.user1 == username:
                friends.add(friendship.user2)
            else:
                friends.add(friendship.user1)
        return list(friends)

def get_friend_requests(username: str):
    with Session(engine) as session:
        friend_requests = session.query(FriendRequest).filter(
            FriendRequest.receiver == username
        ).all()
        return friend_requests

def get_sent_friend_requests(username: str):
    with Session(engine) as session:
        sent_friend_requests = session.query(FriendRequest).filter(
            FriendRequest.sender == username
        ).all()
        return sent_friend_requests

def send_friend_request(sender: str, receiver: str):
    session = Session(engine)
    try:
        friend_request = FriendRequest(sender=sender, receiver=receiver)
        session.add(friend_request)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def accept_friend_request(sender: str, receiver: str):
    session = Session(engine)
    try:
        friend_request = session.query(FriendRequest).filter(
            FriendRequest.sender == sender,
            FriendRequest.receiver == receiver
        ).first()
        if friend_request is not None:
            session.delete(friend_request)
            friendship = Friendship(user1=sender, user2=receiver)
            session.add(friendship)
            session.commit()
            return True
        else:
            return False
    except:
        session.rollback()
        raise
    finally:
        session.close()

def reject_friend_request(sender: str, receiver: str):
    session = Session(engine)
    try:
        friend_request = session.query(FriendRequest).filter(
            FriendRequest.sender == sender,
            FriendRequest.receiver == receiver
        ).first()
        if friend_request is not None:
            session.delete(friend_request)
            session.commit()
            return True
        else:
            return False
    except:
        session.rollback()
        raise
    finally:
        session.close()

def are_friends(user1: str, user2: str):
    with Session(engine) as session:
        friendship = session.query(Friendship).filter(
            ((Friendship.user1 == user1) & (Friendship.user2 == user2)) |
            ((Friendship.user1 == user2) & (Friendship.user2 == user1))
        ).first()
        return friendship is not None
    
def remove_friendship(user1: str, user2: str):
    session = Session(engine)
    try:
        friendship1 = session.query(Friendship).filter(
            Friendship.user1 == user1,
            Friendship.user2 == user2
        ).first()
        friendship2 = session.query(Friendship).filter(
            Friendship.user1 == user2,
            Friendship.user2 == user1
        ).first()
        if friendship1 is not None:
            session.delete(friendship1)
        if friendship2 is not None:
            session.delete(friendship2)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def insert_message(sender: str, receiver: str, content: str, key: str, mac: str, sender_password: str, receiver_password: str):
    with Session(engine) as session:
        message = Message(sender=sender, receiver=receiver, content=content, key=key, mac=mac, sender_password=sender_password, receiver_password=receiver_password)
        session.add(message)
        session.commit()

def get_chat_history(user1: str, user2: str, sender_password: str, receiver_password: str):
    with Session(engine) as session:
        messages = session.query(Message).filter(
            ((Message.sender_password == sender_password) & (Message.receiver_password == receiver_password)) |
            ((Message.sender_password == receiver_password) & (Message.receiver_password == sender_password))
        ).order_by(Message.timestamp).all()
        return messages


def send_chat_invitation(sender: str, receiver: str, room_id: int):
    with Session(engine) as session:
        invitation = ChatInvitation(sender=sender, receiver=receiver, room_id=room_id)
        session.add(invitation)
        session.commit()

def get_chat_invitations(username: str):
    with Session(engine) as session:
        invitations = session.query(ChatInvitation).filter(ChatInvitation.receiver == username).all()
        return invitations

def remove_chat_invitation(invitation_id: int):
    with Session(engine) as session:
        invitation = session.get(ChatInvitation, invitation_id)
        if invitation:
            session.delete(invitation)
            session.commit()

def create_article(title: str, content: str, author: str):
    with Session(engine) as session:
        article = KnowledgeArticle(title=title, content=content, author=author)
        session.add(article)
        session.commit()

def get_all_articles():
    with Session(engine) as session:
        articles = session.query(KnowledgeArticle).all()
        return articles

def get_article(article_id: int):
    with Session(engine) as session:
        article = session.get(KnowledgeArticle, article_id)
        return article

def update_article(article_id: int, title: str, content: str):
    with Session(engine) as session:
        article = session.get(KnowledgeArticle, article_id)
        if article:
            article.title = title
            article.content = content
            session.commit()

def delete_article(article_id: int):
    with Session(engine) as session:
        article = session.get(KnowledgeArticle, article_id)
        if article:
            session.delete(article)
            session.commit()

def create_comment(content: str, author: str, article_id: int):
    with Session(engine) as session:
        comment = Comment(content=content, author=author, article_id=article_id)
        session.add(comment)
        session.commit()

def get_comment(comment_id: int):
    with Session(engine) as session:
        return session.query(Comment).get(comment_id)

def get_comments_by_article(article_id: int):
    with Session(engine) as session:
        comments = session.query(Comment).filter(Comment.article_id == article_id).all()
        return comments

def delete_comment(comment_id: int):
    with Session(engine) as session:
        comment = session.get(Comment, comment_id)
        if comment:
            session.delete(comment)
            session.commit()

def create_role(name: str):
    with Session(engine) as session:
        role = Role(name=name)
        session.add(role)
        session.commit()
        return role.id

def get_role_by_name(name: str):
    with Session(engine) as session:
        role = session.query(Role).filter(Role.name == name).first()
        return role

def assign_role_to_user(username: str, role_id: int):
    with Session(engine) as session:
        user = session.get(User, username)
        if user:
            user.role_id = role_id
            session.commit()

def mute_user(username: str):
    with Session(engine) as session:
        user = session.get(User, username)
        if user:
            user.muted = True
            session.commit()

def unmute_user(username: str):
    with Session(engine) as session:
        user = session.get(User, username)
        if user:
            user.muted = False
            session.commit()