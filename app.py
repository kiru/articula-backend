from flask import Flask
from dataclasses import dataclass

app = Flask(__name__)
# we need to persist some data
# and return those data


@dataclass
class WordLogEntry:
    word: str
    # e.g. h1 / h2
    format: str
    startTime: int
    endTime: int

@app.route('/api/log', methods=['POST'])
def hello_world():
    return 'Hello World!'

if __name__ == '__main__':
    app.run()


