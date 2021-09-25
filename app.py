
from flask import Flask, request
from flask_restx import Api, Resource, fields

from dataclasses import dataclass
from sqlalchemy import create_engine

engine = create_engine('postgresql://hackzurich:hackzurich@localhost:5432/hackzurich')
app = Flask(__name__)
api = Api(app, version='1.0', title='TodoMVC API', description='A simple TodoMVC API',)

ns = api.namespace('articula')

# apiReads = api.model('Read', {
#     'id': fields.String(),
#     'article_id': fields.String(),
# })

apiWorldLog = api.model('WordLogEntry', {
    'sentenceId': fields.String(),
    # This is  duplicate ... but on the server I don't know what is the sentence for the given id
    'sentence': fields.String(),
    'format': fields.String(),
    # either 'START_VIEW' (mostly in view) or 'END_VIEW' (partially-view)
    'type': fields.String(),
    'time': fields.DateTime(),
})

events = api.model('Events', {
    'events': fields.List(fields.Nested(apiWorldLog)),
    'articleUrl':  fields.String(),
    'readId': fields.String(),
})

reads = api.model('Reads', {
    'events': fields.List(fields.Nested(apiWorldLog)),
    'articleUrl': fields.String(),
    'readId': fields.String(),
})

sentenceScore = api.model('SentenceScore', {
    'sentence_id': fields.String(),
    'score': fields.Integer(),
})

@ns.route('/api/reads/')
class ReadLogs(Resource):
    def get(self):
        with engine.connect() as con:
            o = con.execute("select * from reads order by id")
            result = [{
                'id': str(each[0]),
                'article_url': each[1]
            } for each in o]

            return result, 201

@ns.route('/api/reads/<string:read_id>/')
class ReadLogs(Resource):
    @ns.doc('sentence scores ')
    def get(self, read_id):
        with engine.connect() as con:
            o = con.execute("select sentence  from log_entry where reads_fk_id = %s order by sentence_id", (read_id))
            result = [{
                'sentence': str(each[0]),
                'score': 30
            } for each in o]

            return result, 201

@ns.route('/api/events/')
class EvenLog(Resource):
    @ns.doc('add event entries')
    @ns.expect(events)
    @ns.marshal_with(events, code=201)
    def post(self):
        '''Create a new task'''
        payload = api.payload
        print(payload)

        events = payload['events']
        with engine.connect() as con:

            # create read entry
            rs = con.execute("""
            insert into reads(id, article_url)
            values (%s, %s)
            """, (
                payload['readId'],
                payload['articleUrl'],
            ))

            ## write all events
            for event in events:
                rs = con.execute("""
                insert into log_entry(reads_fk_id, sentence_id, sentence, format, type, end_time)
                values (%s, %s, %s, %s, %s, %s)
                """, (
                    payload['readId'],
                    event['sentenceId'],
                    event['sentence'],
                    event['format'],
                    event['type'],
                    event['time'],
                ))
                print(rs)

            return {}, 201

@app.route("/")
def home():
    return "Go to /api/"

if __name__ == '__main__':
    app.run(debug=True)


if __name__ == '__main__' or __name__ == 'app':
    # Create DB structure
    # Intentionally skipped FK references
    with engine.connect() as con:
        print("reads")
        con.execute("""
        create table if not exists reads (
           id            uuid         not null,
           article_url   varchar(255) not null
        )
        """)

        print("log_entry")
        con.execute("""
        create table if not exists log_entry
        (
            reads_fk_id   uuid          not null,
            sentence_id   uuid          not null,
            sentence      varchar(1024) not null,
            format        varchar(255)  not null,
            type          varchar(255)  not null,
            end_time      timestamp     not null
        )
        """)

