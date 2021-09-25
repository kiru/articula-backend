
from flask import Flask, request
from flask_restx import Api, Resource, fields, cors
from flask_cors import cross_origin
from flask_cors import CORS
from itertools import groupby



import numpy as np

from dataclasses import dataclass
from sqlalchemy import create_engine

engine = create_engine('postgresql://hackzurich:hackzurich@localhost:5432/hackzurich')
app = Flask(__name__)
api = Api(app, version='1.0', title='TodoMVC API', description='A simple TodoMVC API',)
CORS(app, resources={r'/*': {'origins': '*'}})


ns = api.namespace('articula', decorators=[cross_origin()])

apiWorldLog = api.model('WordLogEntry', {
    'sentenceId': fields.Integer(),
    # This is  duplicate ... but on the server I don't know what is the sentence for the given id
    'sentence': fields.String(),
    'format': fields.String(),
    # either 'START_VIEW' (mostly in view) or 'END_VIEW' (partially-view)
    'type': fields.String(),
    'time': fields.Float(),
})

events = api.model('Events', {
    'events': fields.List(fields.Nested(apiWorldLog)),
    'articleUrl':  fields.String(),
    'totalTimeMillis': fields.Integer(),
    'totalSentenceCount': fields.Integer(),
    'id': fields.String(),
})

reads = api.model('Reads', {
    'events': fields.List(fields.Nested(apiWorldLog)),
    'articleUrl': fields.String(),
    'id': fields.String(),
})

sentenceScore = api.model('SentenceScore', {
    'sentence_id': fields.String(),
    'score': fields.Integer(),
})

@ns.route('/api/reads/')
class ReadLogs(Resource):
    def get(self):
        with engine.connect() as con:
            o = con.execute("select id, article_url, created  + interval '2 hour' from reads order by created desc")
            result = [{
                'id': str(each[0]),
                'articleUrl': each[1],
                'title': str(each[2].strftime("%m.%d.%Y %H:%M")) + ": " + each[1],
                'readAccuracy': read_accuracy(con, each[0])
            } for each in o]

            overall = {
                'id': 'overall',
                'articleUrl': 'overall',
                'title': "Overall",
                'readAccuracy': -1
            }

            result.insert(0, overall)
            return result, 201

def read_accuracy(con, read_id):
    result = final_score(con, read_id)
    scores = [s['score'] for s in result]
    sentenceIds = [s['sentenceId'] for s in result]

    # for sentence scoring
    res = list(con.execute("select total_sentence_count from reads where id = %s", (read_id)))[0]
    totalSentenceCount = res[0]
    rest = set(range(totalSentenceCount)) - set(sentenceIds)
    additional = (len(rest) * [0])

    full = additional + scores
    return round(np.mean(full), 2)


# todo get rid of engine
def final_score(con, reads_id):
    print("Get score for: ", reads_id)
    res = list(con.execute("select totaltimemillis from reads where id = %s", (reads_id)))[0]
    totalTime = res[0]

    res = con.execute("""select distinct sentence_id from log_entry where reads_fk_id = %s order by sentence_id""", (reads_id))
    final = [x[0] for x in res]

    sentence_id_to_mean = []
    for each_sentence_id in final:
        res = list(con.execute("""select time,type from log_entry where sentence_id = %s and reads_fk_id = %s order by order_nr""", (each_sentence_id, reads_id)))
        times = []
        last = 0
        for (time, type) in res:
            if (type == 'START_VIEW'):
                last = time
            elif (type == 'END_VIEW'):
                times.append(time - last)
                last = -1

        if last != -1:
            times.append(totalTime   - last)

        if len(times) > 0:
            sentence_id_to_mean.append((each_sentence_id, np.mean(times)))

    if len(sentence_id_to_mean) == 0:
        print("sentence_id_to_mean is empty")
        return []
    else:
        max_overall = np.max(np.array(sentence_id_to_mean)[:, 1])
        min_overall = np.min(np.array(sentence_id_to_mean)[:, 1])

        final_json = []
        for (id, mean) in sentence_id_to_mean:
            scaled = (mean - min_overall) / (max_overall - min_overall)
            senScore = {'sentenceId': id, 'score': round(float(scaled), 2)}
            final_json.append(senScore)

        return final_json


def by_sentence_id(object):
    return object["sentenceId"]

def sum_scores(some):
    scores = [each['score'] for each in some]
    return round(np.mean(scores), 2)

@ns.route('/api/reads/<string:read_id>/')
class ReadLogs(Resource):
    @ns.doc('sentence scores ')
    def get(self, read_id):
        with engine.connect() as con:
            if(read_id == 'overall'):
                sentence_to_scores = []
                read_ids = list(con.execute("select id from reads"))
                print(read_ids)
                for each_id in read_ids:
                    sentence_to_scores.extend(final_score(con, each_id[0]))

                list_sorted = sorted(sentence_to_scores, key=by_sentence_id)
                x_grouped = [{'sentenceId': k, 'score': sum_scores(list(it))} for k, it in groupby(list_sorted, by_sentence_id)]

                return x_grouped, 201
            else:
                result = final_score(con, read_id)
                return result, 201



@ns.route('/api/reads/<string:read_id>/stats/')
class ReadLogs(Resource):
    @ns.doc('statistics')
    def get(self, read_id):
        result = final_score(engine.connect(), read_id)
        scores = [s['score'] for s in result]
        sentenceIds = [s['sentenceId'] for s in result]
        read_accuracy = 0

        # for sentence scoring
        with engine.connect() as con:
            res = list(con.execute("select total_sentence_count from reads where id = %s", (read_id)))[0]
            totalSentenceCount = res[0]
            rest = set(range(totalSentenceCount)) - set(sentenceIds)
            additional = (len(rest) * [0])

            full = additional + scores
            read_accuracy = round(np.mean(full), 2)

        result = {
            'average': round(np.mean(scores), 2),
            'read_accuracy': read_accuracy
        }
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
            insert into reads(id, article_url, totaltimemillis, created, total_sentence_count)
            values (%s, %s, %s, CURRENT_TIMESTAMP, %s)
            """, (
                payload['id'],
                payload['articleUrl'],
                payload['totalTimeMillis'],
                payload['totalSentenceCount'],
            ))

            ## write all events
            for i, event in enumerate(events):
                rs = con.execute("""
                insert into log_entry(reads_fk_id, sentence_id, sentence, format, type, time, order_nr)
                values (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    payload['id'],
                    event['sentenceId'],
                    event['sentence'],
                    event['format'],
                    event['type'],
                    event['time'],
                    i
                ))
                print(rs)

            print("Written events: ", len(events))
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
           article_url   varchar(255) not null,
           created       timestamp not null default CURRENT_TIMESTAMP,
           totalTimeMillis       integer not null, 
           total_sentence_count integer not null
        )
        """)

        print("log_entry")
        con.execute("""
        create table if not exists log_entry
        (
            reads_fk_id   uuid          not null,
            order_nr      integer       not null,
            sentence_id   integer       not null,
            sentence      varchar(1024) not null,
            format        varchar(255)  not null,
            type          varchar(255)  not null,
            time          Decimal     not null
        )
        """)

