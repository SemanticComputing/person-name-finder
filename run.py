from flask import Flask, jsonify
from flask import request
import sys, os
import csv
import nltk
import nltk.data
from src.namefinder import NameFinder
from src.text_structure import SentenceChunk, TextParser
from distutils.util import strtobool
from datetime import datetime as dt
import traceback
from flask import abort
import logging.config

app = Flask(__name__)

logging.config.fileConfig(fname='conf/logging.ini', disable_existing_loggers=False)
logger = logging.getLogger('run')


@app.before_request
def before_request():
    if True:
        print("HEADERS", request.headers)
        print("REQ_path", request.path)
        print("ARGS", request.args)
        print("DATA", request.data)
        print("FORM", request.form)


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
        logger.error("Environment variable NAME_FINDER_CONFIG_ENV not set: %s", sys.exc_info()[0])
        logger.error(traceback.print_exc())
        env = None
        abort(500, 'Problem with setup: internal server error')
    except Exception as err:
        logger.error("Unexpected error: %s", sys.exc_info()[0])
        logger.error(traceback.print_exc())
        env = None
        abort(500, 'Unexpected Internal Server Error')

    if request.method == 'GET':
        text = request.args.get('text')
        gender = extract_value(get_args_data('gender'))
        title = extract_value(get_args_data('title'))
        date = extract_value(get_args_data('date'))
        word = extract_value(get_args_data('word'))
        if text is not None:
            input = {0: text}
            logger.debug("%s, %s", gender, text)
            sentence_data, indexes, regex_checks, full_sentences = tokenization(text, env=env)
            logger.debug("tokenization results: %s", sentences)
            sentences, index_list = do_lemmatization(sentence_data, indexes)
            logger.debug("data: %s", input)
        else:
            return input, sentences, index_list, gender, title, date
    elif request.method == "POST":
        if 'Content-Type' in request.headers and request.headers['Content-Type'] == 'text/plain' and len(request.data) > 0:
            text = str(request.data.decode('utf-8'))
        elif 'text' in request.form:
            text = get_form_data('text')
        elif 'text' in request.args:
            text = request.args.get('text')
        elif 'Text' in request.headers:
            text = request.headers['Text']
        else:
            input_error(request)

        # get other arguments that are boolean
        gender = get_bool_argument('gender')
        title = get_bool_argument('title')
        date = get_bool_argument('date')
        word = get_bool_argument('word')

        if text is None:
            return input, sentences, index_list, gender, title, date
        if len(text) > 0:
            logger.debug("%s, %s", gender, text)
            sentence_data, indexes, regex_checks, full_sentences = tokenization(text, env=env)
            logger.debug("sentences dataset: %s", sentence_data)
            sentences, index_list = do_lemmatization(sentence_data, indexes)
            input = {0: str(request.data.decode('utf-8'))}
            logger.debug("data: %s", input)
            logger.debug("sentences: %s", sentences)
    else:
        logger.warnning("This method is not yet supported: %s", request.method)
    return env, input, sentences, index_list, gender, title, date, word, regex_checks, full_sentences


def input_error(request):
    logger.warnning(
        "Unable to process the request! When using post, give param text using raw data or add it to form, url, "
        "or header.")
    logger.warnning("Bad type: %s", request.headers['Content-Type'])
    logger.warnning("Missing data: %s", request.data)
    logger.warnning("Missing from header: %s", request.headers)
    logger.warnning("Missing from form: %s", request.form)
    logger.warnning("Missing from arg: %ss", request.args)


def get_bool_argument(key):
    val = None
    if key in request.form:
        val = extract_value(get_form_data(key))
    elif key in request.args:
        val = extract_value(get_args_data(key))
    elif key in request.headers:
        val = extract_value(get_header_data(key))
    return val


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
            logger.debug("Add abbreviation: %s", row[0])
            tokenizer._params.abbrev_types.add(row[0])
    for i in range(0, 301):
        tokenizer._params.abbrev_types.add(i)
    return tokenizer


def tokenization(text, env):
    # print('Tokenize this:', text)
    sentence_list = list()
    regex_check = dict()
    structure = dict()

    tokenizer = setup_tokenizer()
    tp = TextParser(text, env)
    sentence_list, structure, regex_check, full_sentences = tp.parse_input(tokenizer)

    return sentence_list, structure, regex_check, full_sentences


# def has_numbers(inputString):
#     return any(char.isdigit() for char in inputString)


def do_lemmatization(sentence_data, indeces):
    output = dict()
    index_lists = dict()
    for i in range(0, len(sentence_data)):
        output[i] = sentence_data[i]  # .get_lemma()

        index_lists[i] = indeces[i]
        logger.debug("Index list: %s. %s, %s", i, indeces[i], sentence_data[i])

    return output, index_lists


#
# def lemmatize(text, env):
#     las = lasQuery(env)
#     lemmatized = las.lexical_analysis(text, 'fi')
#     #print("Lemmatized:", lemmatized)
#     return lemmatized


@app.route('/', methods=['POST', 'GET'])
def index():
    env, input_data, sentences, index_list, gender, title, date, word, regex_check, original_sentences = parse_input(
        request)
    logger.info("DATA: %s", sentences)
    if input_data != None:
        name_finder = NameFinder()
        print("Params:")
        print("Gender:", gender)
        print("Title:", title)
        print("Date:", date)
        results, code, responses = name_finder.identify_name(env, sentences, index_list, original_sentences,
                                                             check_date=regex_check, gender=gender, title=title,
                                                             date=date, word=word)

        if code == 1:
            logger.info('results: %s', results)
            data = {"status": 200, "data": results, "service": "Person Name Finder",
                    "timestamp": dt.today().strftime('%Y-%m-%d %H:%M:%S'), "version":"version 1.1-beta"}
            return jsonify(data)
        else:
            data = {"status": -1, "error": results, "service": "Person Name Finder",
                    "timestamp": dt.today().strftime('%Y-%m-%d %H:%M:%S'), "version":"version 1.1-beta"}
            return jsonify(data)
    message = "<h3>Unable to process request</h3><p>Unable to retrieve results for text (%s).</p>" % str(
        request.args.get('text'))
    message += "<p>Please give parameters using GET or POST method. GET method example: <a href='http://127.0.0.1:5000/?text=Minna Susanna Claire Tamper' target='_blank'>http://127.0.0.1:5000/?text=Minna Susanna Claire Tamper</a></p>" + \
               "POST method can be used by transmitting the parameters using url, header, or a form."
    data = {"status": -1, "error": str(message), "service": "Person Name Finder", "timestamp": dt.today().strftime('%Y-%m-%d %H:%M:%S'), "version":"version 1.1-beta"}

    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)
