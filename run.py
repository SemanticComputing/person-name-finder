from flask import Flask
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
import xml.dom.minidom
import xml.etree.ElementTree as ET
from src.las_query import lasQuery
from distutils.util import strtobool
from datetime import datetime as dt

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
    if request.method == 'GET':
        text = request.args.get('text')
        gender = extract_value(get_args_data('gender'))
        title = extract_value(get_args_data('title'))
        date = extract_value(get_args_data('date'))
        word = extract_value(get_args_data('word'))
        if text != None:
            input = {0:text}
            print(gender, text)
            sentence_data, indeces, regex_checks = tokenization(text)
            #print("tokenization results",sentences)
            sentences, index_list = do_lemmatization(sentence_data, indeces)
            #print("data", input)
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
            print(gender, text)
            sentence_data, indeces, regex_checks = tokenization(text)
            print("sentences dataset:", sentence_data)
            sentences, index_list = do_lemmatization(sentence_data, indeces)
            input = {0: str(request.data.decode('utf-8'))}
            print("data:", input)
            print("sentences:", sentences)
    else:
        print("This method is not yet supported:", request.method)
    return input, sentences, index_list, gender, title, date, word, regex_checks


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
    with open('data/abbreviations.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=';')
        for row in csv_reader:
            print("Add abbreviation", row[0])
            tokenizer._params.abbrev_types.add(row[0])
    return tokenizer


def tokenization(text):
    separators = [', ','; ', ' (', ') ', ' ja ', ' tai ']
    exceptional_separators = [' (', ') ']
    regex_check = dict()
    chunk_regex_check = 0
    result = list()
    structure = dict()
    counter = 0
    chunk_counter = 0
    print('Tokenize this:', text)
    tokenizer = setup_tokenizer()
    sentences = tokenizer.tokenize(text)
    for sentence in sentences:
        splitted = re.split(r'(, |; | \(|\) | ja | tai )', sentence) #sentence.split('[,;]')

        if len(splitted) > 1:
            for chunk in splitted:
                if chunk not in separators:
                    result.append(chunk)
                    if chunk_counter not in structure:
                        structure[chunk_counter] = counter
                        if chunk_regex_check > 0:
                            print("Check chunk? ", chunk)
                            if has_numbers(chunk):
                                print("This chunk has to be checked!")
                                regex_check[chunk_counter] = chunk
                        chunk_counter += 1
                elif chunk == ' (':
                    print('Start bracket checking')
                    chunk_regex_check = 1
                elif chunk == ') ':
                    chunk_regex_check = 0
                    print('End bracket checking')


        else:
            result.append(sentence)
            if chunk_counter not in structure:
                structure[chunk_counter] = counter
                chunk_counter += 1
        counter += 1

    print("Splitted:", result)
    return result, structure, regex_check


def has_numbers(inputString):
    return any(char.isdigit() for char in inputString)


def do_lemmatization(sentence_data, indeces):
    output = dict()
    index_lists = dict()
    for i in range(0, len(sentence_data)):
        output[i] = lemmatize(sentence_data[i])

        index_lists[i] = indeces[i]
        print("Index list:", i, indeces[i], sentence_data[i])


    #{i: lemmatize(sentence_data[i]) for i in range(0, len(sentence_data))}
    return output, index_lists


def lemmatize(text):
    las = lasQuery()
    lemmatized = las.lexical_analysis(text, 'fi')
    print("Lemmatized:", lemmatized)
    return lemmatized


@app.route('/', methods=['POST', 'GET'])
def index():
    print("APP name",__name__)
    input_data, sentences, index_list, gender, title, date, word, regex_check = parse_input(request)
    print("DATA", sentences)
    if input_data != None:
        name_finder = NameFinder()
        results, code, responses = name_finder.identify_name(sentences, index_list, check_date=regex_check, gender=gender, title=title, date=date, word=word)

        if code == 1:
            print('results',results)
            data = {"status":200,"data":results, "service":"name-finder", "date":dt.today().strftime('%Y-%m-%d')}
            return json.dumps(data, ensure_ascii=False)
        else:
            data = {"status":-1,"error":str(results), "service":"name-finder", "date":dt.today().strftime('%Y-%m-%d')}
            return json.dumps(data, ensure_ascii=False)
    message = "<h3>Unable to process request</h3><p>Unable to retrieve results for text (%s).</p>" % str(request.args.get('text'))
    message += "<p>Please give parameters using GET or POST method. GET method example: <a href='http://127.0.0.1:5000/?text=Minna Susanna Claire Tamper' target='_blank'>http://127.0.0.1:5000/?text=Minna Susanna Claire Tamper</a></p>"+\
                    "POST method can be used by transmitting the parameters using url, header, or a form."
    return message


if __name__ == '__main__':
    app.run(debug=True)
