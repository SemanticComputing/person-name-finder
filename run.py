from flask import Flask, jsonify
from flask import request
import argparse
import sys, os
import logging, json
import re
import time
import datetime
import csv
import nltk
import nltk.data
from src.namefinder import NameFinder
from src.text_structure import SentenceChunk, TextParser
import xml.dom.minidom
import xml.etree.ElementTree as ET
from src.las_query import lasQuery
from distutils.util import strtobool
from datetime import datetime as dt
import traceback
from flask import abort

app = Flask(__name__)

@app.before_request
def before_request():
    if True:
        print("HEADERS", request.headers)
        print("REQ_path", request.path)
        print("ARGS",request.args)
        print("DATA",request.data)
        print("FORM",request.form)

def parse_input(request):
    input = None
    sentences = None
    text = ""
    gender = None
    title = None
    date = None
    word = None
    index_list = None
    env = 'DEFAULT'

    # read environment from environment variable
    try:
        env = os.environ['NAME_FINDER_CONFIG_ENV']
    except KeyError as kerr:
        print("Environment variable NAME_FINDER_CONFIG_ENV not set:", sys.exc_info()[0])
        traceback.print_exc()
        env = None
        abort(500, 'Problem with setup: internal server error')
    except Exception as err:
        print("Unexpected error:", sys.exc_info()[0])
        traceback.print_exc()
        env = None
        abort(500, 'Unexpected Internal Server Error')

    if request.method == 'GET':
        text = request.args.get('text')
        gender = extract_value(get_args_data('gender'))
        title = extract_value(get_args_data('title'))
        date = extract_value(get_args_data('date'))
        word = extract_value(get_args_data('word'))
        if text != None:
            input = {0:text}
            #print(gender, text)
            sentence_data, indeces, regex_checks, full_sentences = tokenization(text)
            #print("tokenization results",sentences)
            sentences, index_list = do_lemmatization(sentence_data, indeces)
            #print("data", input)
        else:
            return input, sentences, index_list, gender, title, date
    elif request.method == "POST":
        if request.headers['Content-Type'] == 'text/plain' and len(request.data)>0:
            text = str(request.data.decode('utf-8'))
        elif 'text' in request.form:
            text = get_form_data('text')
            gender = extract_value(get_form_data('gender'))
            title = extract_value(get_form_data('title'))
            date = extract_value(get_form_data('date'))
            word = extract_value(get_form_data('word'))
        elif 'text' in request.args:
            text = request.args.get('text')
            gender = extract_value(get_args_data('gender'))
            title = extract_value(get_args_data('title'))
            date = extract_value(get_args_data('date'))
            word = extract_value(get_args_data('word'))
        elif 'Text' in request.headers:
            text = request.headers['Text']
            gender = extract_value(get_header_data('gender'))
            title = extract_value(get_header_data('title'))
            date = extract_value(get_header_data('date'))
            word = extract_value(get_header_data('word'))
        else:
            print("Unable to process the request! When using post, give param text using raw data or add it to form, url, or header.")
            print("Bad type", request.headers['Content-Type'])
            print("Missing data", request.data)
            print("Missing from header", request.headers)
            print("Missing from form", request.form)
            print("Missing from args", request.args)

        if text == None:
            return input, sentences, index_list, gender, title, date
        if len(text) > 0:
            #print(gender, text)
            sentence_data, indeces, regex_checks, full_sentences = tokenization(text)
            #print("sentences dataset:", sentence_data)
            sentences, index_list = do_lemmatization(sentence_data, indeces)
            input = {0: str(request.data.decode('utf-8'))}
            #print("data:", input)
            #print("sentences:", sentences)
    else:
        print("This method is not yet supported:", request.method)
    return env, input, sentences, index_list, gender, title, date, word, regex_checks, full_sentences


def extract_value(value):
    if value != None:
        return bool(strtobool(value))
    return False


def get_form_data(field):
    if field in request.form:
        return request.form[field]
    return None


def get_args_data(field):
    if field in request.args:
        return request.args.get(field)
    return None


def get_header_data(field):
    Field = field[0].upper() + field[1:]
    if Field in request.headers:
        return request.headers[Field]
    return None


def setup_tokenizer():
    tokenizer = nltk.data.load('tokenizers/punkt/finnish.pickle')
    with open('language-resources/abbreviations.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        for row in csv_reader:
            #print("Add abbreviation", row[0])
            tokenizer._params.abbrev_types.add(row[0])
    for i in range(0, 301):
        tokenizer._params.abbrev_types.add(i)
    return tokenizer

def tokenization(text):
    #print('Tokenize this:', text)
    sentence_list = list()
    regex_check = dict()
    structure = dict()

    tokenizer = setup_tokenizer()
    tp = TextParser(text)
    sentence_list, structure, regex_check, full_sentences = tp.parse_input(tokenizer)

    return sentence_list, structure, regex_check, full_sentences


def has_numbers(inputString):
    return any(char.isdigit() for char in inputString)


def do_lemmatization(sentence_data, indeces):
    output = dict()
    index_lists = dict()
    for i in range(0, len(sentence_data)):
        output[i] = sentence_data[i]#.get_lemma()

        index_lists[i] = indeces[i]
        #print("Index list:", i, indeces[i], sentence_data[i])

    return output, index_lists


def lemmatize(text):
    las = lasQuery()
    lemmatized = las.lexical_analysis(text, 'fi')
    #print("Lemmatized:", lemmatized)
    return lemmatized


@app.route('/', methods=['POST', 'GET'])
def index():
    env, input_data, sentences, index_list, gender, title, date, word, regex_check, original_sentences = parse_input(request)
    #print("DATA", sentences)
    if input_data != None:
        name_finder = NameFinder()
        results, code, responses = name_finder.identify_name(env, sentences, index_list, original_sentences, check_date=regex_check, gender=gender, title=title, date=date, word=word)

        if code == 1:
            print('results',results)
            data = {"status":200,"data":results, "service":"name-finder", "date":dt.today().strftime('%Y-%m-%d')}
            return jsonify(data)
        else:
            data = {"status":-1,"error":results, "service":"name-finder", "date":dt.today().strftime('%Y-%m-%d')}
            return jsonify(data)
    message = "<h3>Unable to process request</h3><p>Unable to retrieve results for text (%s).</p>" % str(request.args.get('text'))
    message += "<p>Please give parameters using GET or POST method. GET method example: <a href='http://127.0.0.1:5000/?text=Minna Susanna Claire Tamper' target='_blank'>http://127.0.0.1:5000/?text=Minna Susanna Claire Tamper</a></p>"+\
                    "POST method can be used by transmitting the parameters using url, header, or a form."
    data = {"status": -1, "error": str(message), "service": "name-finder", "date": dt.today().strftime('%Y-%m-%d')}

    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)
