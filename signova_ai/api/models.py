from mongoengine import Document, StringField, IntField, EmailField


class User(Document):

    username = StringField(required=True)

    email = EmailField(required=True)

    password = StringField(required=True)

    country = StringField()

    gender = StringField()

    age = IntField()