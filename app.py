
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
    'read_fk_id': fields.String(),
    'sentence_id': fields.String(),
    # This is  duplicate ... but on the server I don't know what is the sentence for the given id
    'sentence': fields.String(),
    'format': fields.String(),
    'start_time': fields.DateTime(),
    'end_time': fields.DateTime(),
})

@ns.route('/api/log/')
class WordLog(Resource):
    @ns.doc('add log entry')
    @ns.expect(apiWorldLog)
    @ns.marshal_with(apiWorldLog, code=201)
    def post(self):
        '''Create a new task'''
        payload = api.payload
        print(payload)

        with engine.connect() as con:
            rs = con.execute("""
            insert into log_entry(reads_fk_id, sentence_id, sentence, format, start_time, end_time)
            values (%s, %s, %s, %s, %s, %s)
            """, (
                payload['read_fk_id'],
                payload['sentence_id'],
                payload['sentence'],
                payload['format'],
                payload['start_time'],
                payload['end_time'],
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
        print("articles")
        con.execute("""
        create table if not exists articles
        (
           id  uuid         not null,
           url varchar(255) not null
        )
        """)

        print("reads")
        con.execute("""
        create table if not exists reads
        (
           id            uuid         not null,
           article_fk_id uuid         not null
        )
        """)

        print("log_entry")
        con.execute("""
        create table if not exists log_entry
        (
            reads_fk_id   uuid         not null,
            sentence_id   uuid         not null,
            sentence      varchar(255) not null,
            format        varchar(255) not null,
            start_time    timestamp   not null,
            end_time      timestamp   not null
        )
        """)

