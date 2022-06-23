from SPARQLWrapper import SPARQLWrapper, JSON, BASIC
from collections import OrderedDict
import validators
import sys, traceback
import logging.config


# logging setup
logging.config.fileConfig(fname='conf/logging.ini', disable_existing_loggers=False)
logger = logging.getLogger('sparql')

class SparqlQuries:
    def __init__(self):
        pass

    def test(self):
        sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        sparql.setQuery("""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?label
            WHERE { <http://dbpedia.org/resource/Asturias> <http://www.w3.org/2000/01/rdf-schema#comment> ?label .
                    FILTER (lang(?label) = 'en') }
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        for result in results["results"]["bindings"]:
            logger.info(result["label"]["value"])

        return results

    def query_names(self, names, endpoint):
        result_set = OrderedDict()
        try:
            if validators.url(endpoint):
                if len(names) < 1:
                    return {}

                for i, name in names.items():
                    logger.debug("Query names: %s",name)
                    # http://yasgui.org/short/ATCBjNyFz
                    #endpoint = "http://ldf.fi/henko/sparql"

                    query = """ PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                                SELECT DISTINCT ?names ?name ?label ?nameLabel ?nameType ?referencesPlace ?referencesVocation (sum(?lkm)as ?count)   WHERE {
                                  VALUES ?names { $names }
                                  BIND(STRLANG(?names,'fi') AS ?label)
                                  ?name skos:prefLabel ?label .
                                  ?nameUsage <http://ldf.fi/schema/henko/hasName> ?name .
                                  ?nameUsage <http://ldf.fi/schema/henko/count> ?lkm .
                                  ?nameType <http://ldf.fi/schema/henko/isUsed> ?nameUsage .
                                  OPTIONAL { ?nameUsage <http://ldf.fi/schema/henko/gender> ?gender . }
                                  OPTIONAL { ?nameType <http://ldf.fi/schema/henko/refersPlace> ?referencesPlace . }
                                  OPTIONAL { ?nameType <http://ldf.fi/schema/henko/refersVocation> ?referencesVocation . }
                                  ?nameType a ?type .
                                  ?type rdfs:label ?typeLabel .                      
                                  FILTER (lang(?typeLabel) = 'fi')
                                  BIND(STR(?typeLabel) AS ?nameLabel) .
                                } GROUP BY ?names ?name ?label ?nameLabel ?nameType ?gender ?referencesPlace ?referencesVocation ORDER BY DESC(?name) DESC(?nameType)"""

                    query = query.replace('$names', " ".join(['"{0}"'.format(x) for x in name]))

                    logger.debug("endpoint: %s", endpoint)
                    logger.debug("query: %s", query)

                    sparql = SPARQLWrapper(endpoint)
                    sparql.setQuery(query)

                    sparql.setReturnFormat(JSON)
                    results = sparql.query().convert()

                    logger.debug("results: %s", results)
                    n = str(i) + "_" + " ".join(name)
                    if n not in result_set.keys():
                        result_set[n] = list()
                    result_set[n]=self.parse_sparql_result(name, results)


            return result_set
        except ValueError as verr:
            logger.error("Unable to query, url is not valid: %s", sys.exc_info()[0])
            logger.error(traceback.print_exc())
        except Exception as err:
            logger.error("Unexpected error: %s", sys.exc_info()[0])
            logger.error(traceback.print_exc())
        finally:
            return result_set

    def parse_sparql_result(self, values, results):
        resultset = SparqlResultSet()
        resultset.parse(values, results)
        return resultset


class SparqlResultSet():
    def __init__(self):
        self.resultset = OrderedDict()
        self.id_map = OrderedDict()
        self.len = 0

    def parse(self, values, results):
        for val in values:
            self.resultset[self.len] = list()
            item = SparqlResultSetItem()
            item.set_label(val)
            item.set_ord(self.len)
            self.id_map[self.len] = item
            self.len += 1
        logger.debug(self.id_map)
        logger.debug(self.resultset)

        for result in results["results"]["bindings"]:
            for i in self.resultset.keys():
                item = SparqlResultSetItem()
                item.parse(result, i)
                logger.debug(item)
                if item == self.id_map[i]:
                    self.resultset[i].append(item)
                else:
                    logger.debug("%s not in %s", str(item), str(self.id_map[i]))

    def get_item(self, ind, item):
        for i in self.resultset[ind]:
            if self.resultset[ind][i] == item:
                return self.resultset[ind][i]
        return None

    def get_resultset(self):
        return self.resultset

class SparqlResultSetItem():
    def __init__(self):
        self.uri = None
        self.name = ""
        self.ord = 0
        self.label = ""
        self.linkage = None
        self.type = ""
        self.count = 0
        self.refersPlace = None
        self.refersVocation = None

    def parse(self, result, ord):
        logger.debug("Result: %s", str(result))
        self.ord = ord
        self.uri = str(result["name"]["value"])
        self.name = str(result["names"]["value"])
        self.label = str(result["label"]["value"])
        self.count = int(result["count"]["value"])
        self.type = str(result["nameLabel"]["value"])
        self.linkage = str(result["nameType"]["value"])
        if 'referencesPlace' in result:
            self.refersPlace = str(result["referencesPlace"]["value"])
            logger.debug("referencesPlace in results: %s",str(self.refersPlace))
        else:
            logger.debug("referencesPlace not in results")
        if 'referencesVocation' in result:
            self.refersVocation = str(result["referencesVocation"]["value"])

    def set(self, ord, uri, name, label, count, type, linkage, place, vocation):
        self.name = name
        self.uri = uri
        self.ord = ord
        self.label = label
        self.linkage = linkage
        self.type = type
        self.count = count
        self.refersPlace = place
        self.refersVocation = vocation

    # getters and setters

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_ord(self):
        return self.ord

    def set_ord(self, ord):
        self.ord = ord

    def get_label(self):
        return self.label

    def set_label(self, value):
        self.label = value

    def get_linkage(self):
        return self.linkage

    def set_linkage(self, value):
        self.linkage = value

    def get_type(self):
        return self.type

    def set_type(self, value):
        self.type = value

    def get_count(self):
        return self.count

    def set_count(self, value):
        self.count = value

    def get_uri(self):
        return self.uri

    def set_uri(self, value):
        self.uri = value

    def get_ref_place(self):
        return self.refersPlace

    def set_ref_place(self, value):
        self.refersPlace = value

    def get_ref_vocation(self):
        return self.refersVocation

    def set_ref_vocation(self, value):
        self.refersVocation = value

    def __str__(self):
        return "SparqlResultSetItem: "+str(self.ord) + ". " + str(self.name) + " (" + str(self.label) + ", " + str(self.count) + ", "+ str(self.type) +")"

    def __repr__(self):
        return "SparqlResultSetItem: "+str(self.ord) + ". " + str(self.name) + " (" + str(self.label) + ", " + str(self.count) + ", "+ str(self.type) +")"

    def __eq__(self, other):
        if self.label == other.get_label():
            if self.ord == other.get_ord():
                return True
        return False

    def __lt__(self, other):
        if self.ord < other.get_ord():
            return True
        return False

    def __gt__(self, other):
        if self.ord > other.get_ord():
            return True
        return False






