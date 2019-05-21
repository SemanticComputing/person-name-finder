import itertools
from nescore import NeScore
import logging, json

logger = logging.getLogger('NamedEntity')
try:
    hdlr = logging.FileHandler('logs/namedentity.log')
except Exception as err:
    hdlr = logging.FileHandler('namedentity.log')
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

class NamedEntity:
    def __init__(self):
        self.uri = ""
        self.string = ""
        self.start_ind = 0
        self.end_ind = 0
        self.ne_type = None
        self.method=""
        self.score=NeScore()
        self.relatedMatches = dict()

    def set_ne(self, uri, string, start, end, type, method, score=None):

        self.uri = uri
        self.string = string
        self.start_ind = start
        self.end_ind = end
        self.set_type(type)
        self.method = method

        if score != None:
            self.score = score

        #print("Writing "+str(self))
        self.score.set_type_score(self.ne_type)

    # Getters
    def get_method(self):
        return self.method

    def get_score(self):
        return self.score

    def get_uri(self):
        return self.uri

    def get_type(self):
        return self.ne_type

    def get_string(self):
        return self.string

    def get_start_ind(self):
        return self.start_ind

    def get_end_ind(self):
        return self.end_ind

    def get_total_score(self):
        return self.score.total_score()

    def get_related_matches(self):
        return self.relatedMatches

    # Setters
    def set_type(self, type_uri):
        uri = type_uri.split("/")
        self.ne_type = uri[(len(uri)-1)]
        # set score for type
        self.score.set_type_score(self.ne_type)

    def set_start_ind(self, ind):
        if ind == None:
            ind = 0
        self.start_ind = ind

    def set_end_ind(self, ind):
        if ind == None:
            ind = 0
        self.end_ind = ind

    def set_method(self, method):
        self.method = method

    def set_score(self, score):
        self.score = score

    # to json
    def json(self):
        data = {"entity":str(self.string), "type":str(self.ne_type), "word_start_index":self.get_start_ind(), "word_end_index":self.get_end_ind()}
        #print(str(data))
        return data

    def add_related_match(self, label, link):
        if label not in self.relatedMatches:
            self.relatedMatches[label] = link
            self.add_score("link",1)

    def add_score(self, metric,  score):
        if metric == "longest":
            self.score.set_longest(score)
        elif metric == "type":
            self.score.set_ne_type(score)
        elif metric == "method":
            self.score.set_method(score)
        elif metric == "link":
            self.score.set_link(score)
        else:
            logging.warning("Unknown metric: ", metric)

    def __repr__(self):
        return self.string + "(@type=" + self.ne_type + ", @start=" + str(self.start_ind) + ", @end=" + str(self.end_ind) + ")"

    def __str__(self):
        return self.string + "(@type=" + self.ne_type + ", @start=" + str(self.start_ind) + ", @end=" + str(self.end_ind)+ ")"

    def __hash__(self):
        return id(self)

    def __eq__(self, other):

        if self.ne_type != other.get_type():
            return False

        if self.string.strip() != other.get_string().strip():
            #print("Not equal strings ", self.string, "!=", other.get_string())
            return False

        if self.start_ind != other.get_start_ind() and self.end_ind != other.get_end_ind():
            return False

        #if self.ne_type != other.get_type():
        #    return False

        return True
