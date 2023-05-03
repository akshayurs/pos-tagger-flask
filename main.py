from firebase_admin import auth
from gpt4free import forefront
from flask_cors import CORS
import spacy
import random
from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from gpt4free import forefront
cred = credentials.Certificate('./serviceAccountKey.json')
app = firebase_admin.initialize_app(cred)
db = firestore.client()
nlp = spacy.load("en_core_web_sm")
app = Flask(__name__)

CORS(app)
COLLECTION = 'sentences'

sentences_ref = db.collection(COLLECTION)
users_ref = db.collection('users')

tag_descriptions = {
    "CC": "Coordinating conjunction",
    "CD": "Cardinal number",
    "DT": "Determiner",
    "EX": "Existential there",
    "FW": "Foreign word",
    "IN": "Preposition or subordinating conjunction",
    "JJ": "Adjective",
    "JJR": "Adjective, comparative",
    "JJS": "Adjective, superlative",
    "LS": "List item marker",
    "MD": "Modal",
    "NN": "Noun, singular or mass",
    "NNS": "Noun, plural",
    "NNP": "Proper noun, singular",
    "NNPS": "Proper noun, plural",
    "PDT": "Predeterminer",
    "POS": "Possessive ending",
    "PRP": "Personal pronoun",
    "PRP$": "Possessive pronoun",
    "RB": "Adverb",
    "RBR": "Adverb, comparative",
    "RBS": "Adverb, superlative",
    "RP": "Particle",
    "SYM": "Symbol",
    "TO": "to",
    "UH": "Interjection",
    "VB": "Verb, base form",
    "VBD": "Verb, past tense",
    "VBG": "Verb, gerund or present participle",
    "VBN": "Verb, past participle",
    "VBP": "Verb, non-3rd person singular present",
    "VBZ": "Verb, 3rd person singular present",
    "WDT": "Wh-determiner",
    "WP": "Wh-pronoun",
    "WP$": "Possessive wh-pronoun",
    "WRB": "Wh-adverb"
}

with open('sample1.txt', 'r') as f:
    file_data = f.readlines()
    file_data = [i.strip() for i in file_data]

database_data = []


def refresh_data():
    docs = sentences_ref.stream()
    for doc in docs:
        database_data.append(
            {"id": doc.id, "sentence": doc.to_dict().get('sentence')})


refresh_data()
# database_data = [{"id": "none", "sentence": i} for i in file_data]


def nlp_sentence(sentences):
    data = []
    for item in sentences:
        sentence = item['sentence']
        doc = nlp(sentence)
        pos_tags = [{"word": str(
            i), "tag_description": tag_descriptions.get(str(i.tag_), "None"), "tag": str(i.tag_), "isSubject": i.dep_ == 'nsubj'} for i in doc]
        pos_tags = list(
            filter(lambda x: x['tag_description'] != 'None', pos_tags))
        # random.shuffle(pos_tags)
        data.append({"sentence": sentence, "id": item['id'], "tags": pos_tags})
    return data


@app.route('/random', methods=['GET'])
def random_sentences():
    if (request.method != 'GET'):
        return jsonify({"status": "error", "message": "cant GET this endpoint"})
    args = request.args
    amount = args.get('amount', 1)
    amount = int(amount)
    random_sentences = random.sample(database_data, amount)
    data = nlp_sentence(random_sentences)
    return jsonify({"status": "success", "amount": amount, 'data': data})


@app.route('/tag', methods=['GET'])
def home():
    if (request.method != 'GET'):
        return jsonify({"status": "error", "message": "cant GET this endpoint"})
    args = request.args
    sentence = args.get('sentence')
    data = nlp_sentence([{"id": "null", "sentence": sentence}])
    return jsonify({"status": "success", "amount": 1, 'data': data})


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if (request.method == 'GET'):
        args = request.args
        sentence = args.get("sentence")
        doc_ref = sentences_ref.document()
        doc_ref.set({
            u'sentence': sentence
        })
        return jsonify({"status": "success", "message": "Data uploaded successfully"})
    if (request.method == 'POST'):
        data = request.get_json()
        sentences = data.get("sentences")
        print(sentences)
        for i in sentences:
            doc_ref = sentences_ref.document()
            doc_ref.set({
                u'sentence': i
            })
        return jsonify({"status": "success", "message": "Data uploaded successfully"})


@app.route('/view', methods=['GET'])
def view():
    refresh_data()
    return jsonify({"status": "success", "amount": len(database_data), "data": database_data})


# api route to add file_data to firestore
@app.route('/reset', methods=['GET'])
def reset():
    docs = sentences_ref.stream()
    for doc in docs:
        doc.delete()
    for i in file_data:
        doc_ref = sentences_ref.document()
        doc_ref.set({
            u'sentence': i
        })
    return jsonify({"status": "success", "message": "Data added successfully"})

# Chatbot route
@app.route('/chatbot', methods=['POST'])
def chatbot():
    token = forefront.Account.create(logging=False)
    # print(token)

    # get a response
    output = str("")
    for response in forefront.StreamingCompletion.create(
	    token=token,
	    prompt = str(request.form.get('prompt')),
	    model='gpt-4'
    ):
        output += response.choices[0].text
        # print(response.choices[0].text, end='')
    
    return jsonify( {'response' : output} )


@app.route('/', methods=['GET'])
def default():
    return 'Hello World'


if __name__ == '__main__':
    app.run(debug=True)
