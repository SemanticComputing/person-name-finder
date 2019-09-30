from SPARQLWrapper import SPARQLWrapper, JSON, BASIC
import logging
import requests, json

logger = logging.getLogger('SparqlQuries')
hdlr = logging.FileHandler('logs/sparql.log')
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)
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
            logging.info(result["label"]["value"])

        return results

    def query_names(self, names):
        result_set = list()
        print(names)
        if len(names) < 1:
            return {}

        for i, name in names.items():
            print("Query names:",name)
            # http://yasgui.org/short/ATCBjNyFz
            endpoint = "http://ldf.fi/henkilonimisto/sparql"

            query = """ PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                        SELECT DISTINCT ?name ?label ?nameLabel ?nameType (sum(?lkm)as ?count)   WHERE {
                          VALUES ?names { $names }
                          BIND(STRLANG(?names,'fi') AS ?label)
                          ?name skos:prefLabel ?label .
                          ?nameUsage <http://ldf.fi/schema/henkilonimisto/hasName> ?name .
                          ?nameUsage <http://ldf.fi/schema/henkilonimisto/count> ?lkm .
                          ?nameType <http://ldf.fi/schema/henkilonimisto/isUsed> ?nameUsage .
                          OPTIONAL { ?nameType <http://ldf.fi/schema/henkilonimisto/gender> ?gender . }
                          ?nameType a ?type .
                          ?type skos:prefLabel ?typeLabel .                      
                          FILTER (lang(?typeLabel) = 'fi')
                          BIND(STR(?typeLabel) AS ?nameLabel) .
                          #FILTER(STRSTARTS(STR(?type), 'http://ldf.fi/schema/henkilonimisto/'))
                        } GROUP BY ?name ?label ?nameLabel ?nameType ?gender """

            query = query.replace('$names', " ".join(['"{0}"'.format(x) for x in name]))

            print("endpoint:", endpoint)
            print("query:", query)

            sparql = SPARQLWrapper(endpoint)
            sparql.setQuery(query)

            sparql.setReturnFormat(JSON)
            results = sparql.query().convert()

            print("results:", results)
            result_set.append(results)

        return result_set


    def query_sentences(self):
        sparql = SPARQLWrapper("http://localhost:3030/test-nif-conversion/query")
        sparql.setQuery("""
            SELECT *
            WHERE {
              GRAPH <http://localhost:3030/test-nif-conversion/data/bio>
             { ?s ?p ?o }
            }
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        return results

    def query_words_from_graph(self, uri, graph, endpoint):

        sparql = SPARQLWrapper(endpoint)

        query = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX dct: <http://purl.org/dc/terms/>
            SELECT * WHERE {
                GRAPH <"""+str(graph)+"""> {
                    ?s a <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#Word> ;
                       <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#WORD> ?word ;
                       <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#ID> ?id ;
                       <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#sentenceOrder> ?sID ;
                       <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#sentence> ?sentence ;
                       <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#structure> ?structure .
  					?sentence dct:isPartOf ?paragraph .
  					?paragraph <"""+str(uri)+"""/data#order> ?i .
                   OPTIONAL {
                       ?s <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#UPOS> ?upos .
                   }
                   OPTIONAL {
                       ?s <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#FEAT> ?feat .
                   }
                   OPTIONAL {
                       ?s <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#EDGE> ?edge .
                   }
                }
              BIND(xsd:integer(?id) as ?x)
              BIND(xsd:decimal(STR(?sID)) as ?y)
  			  BIND(xsd:integer(?i) as ?z)
            } ORDER BY ASC(?structure) ASC(?z) ASC(?y) ASC(?x)
        """

        logging.info("endpoint= %s", endpoint)
        logging.info("query= %s", query)

        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        return results

    def query_words(self, uri, endpoint, structure):
        endpoint = "http://ldf.fi/nbf-nlp/sparql"
        sparql = SPARQLWrapper(endpoint)

        query = """
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX dct: <http://purl.org/dc/terms/>
            SELECT * WHERE {
                BIND( <"""+structure+"""> AS ?structure)
                ?s a <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#Word> ;
                   <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#WORD> ?word ;
                   <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#ID> ?id ;
                   <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#sentenceOrder> ?sID ;
                   <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#sentence> ?sentence ;
                   <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#structure> ?structure .
                ?sentence dct:isPartOf ?paragraph .
                ?paragraph <""" + str(uri) + """/data#order> ?i .
                ?paragraph <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#isString> ?paragraphText .
               OPTIONAL {
                   ?s <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#UPOS> ?upos .
               }
               OPTIONAL {
                   ?s <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#FEAT> ?feat .
               }
               OPTIONAL {
                   ?s <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#EDGE> ?edge .
               }
               OPTIONAL {
                   ?s <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#LEMMA> ?lemma .
               }

              BIND(xsd:integer(?id) as ?x)
              BIND(xsd:decimal(STR(?sID)) as ?y)
              BIND(xsd:integer(?i) as ?z)
            } ORDER BY ASC(?structure) ASC(?z) ASC(?y) ASC(?x)
        """

        logging.info("endpoint= %s", endpoint)
        logging.info("query= %s", query)
        #(query)
        #sparql.setQuery(query)
        #sparql.setReturnFormat(JSON)
        #results = sparql.query().convert()
        print("Check:",endpoint, query)
        results = self.makeSparqlQuery(query, endpoint)
        print(results)
        return results

    def parse_values(self, input):
        documents = list()

        if len(input["results"]["bindings"]) > 0:
            for result in input["results"]["bindings"]:
                logging.info("Res %s", result)
                if 'id' in result:
                    uri = "<" + result["id"]["value"] + ">"
                    documents.append(uri)
        logging.info("Documents %s",documents)
        return documents


    def query_values(self, uri, endpoint, offsetid, limit):
        endpoint = "http://ldf.fi/nbf/sparql"
        sparql = SPARQLWrapper(endpoint)

        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX bioc:  <http://ldf.fi/schema/bioc/>
        PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <http://schema.org/>
        PREFIX skos:  <http://www.w3.org/2004/02/skos/core#>
        PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#>
        PREFIX nbf:    <http://ldf.fi/nbf/>
        PREFIX categories:    <http://ldf.fi/nbf/categories/>
        PREFIX gvp:    <http://vocab.getty.edu/ontology#>
        PREFIX crm:   <http://www.cidoc-crm.org/cidoc-crm/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX gvp: <http://vocab.getty.edu/ontology#>
        PREFIX relations:    <http://ldf.fi/nbf/relations/>
        PREFIX sources:    <http://ldf.fi/nbf/sources/>
    
        SELECT distinct ?id ?structure
        WHERE {
            {
                SELECT distinct ?id WHERE {
                    {  ?id a <http://ldf.fi/nbf/PersonConcept> .  }
                    ?id foaf:focus/^crm:P98_brought_into_life/nbf:time/gvp:estStart ?birth  .
                    ?id dcterms:source <http://ldf.fi/nbf/sources/source1> .
        
                }  ORDER BY DESC(?birth) OFFSET $offsetid #1455 #1222
            }
            ?id skosxl:prefLabel ?id__label .
                OPTIONAL { ?id__label schema:familyName ?id__fname }
                OPTIONAL { ?id__label schema:givenName ?id__gname }
                BIND (CONCAT(COALESCE(?id__gname, "")," ",COALESCE(?id__fname, "")) AS ?id__name)
        
            ?id foaf:focus/schema:gender ?gender .
            ?id foaf:focus/nbf:has_category ?cat .
            FILTER (?cat IN (categories:c133, categories:c44, categories:c41, categories:c12, categories:c43, categories:c51, categories:c61, categories:c46) )
        
            ?id foaf:focus/nbf:has_biography/nbf:has_paragraph [ nbf:content ?content ; nbf:id ?ordinal ] .
            ?structure <http://ldf.fi/nbf/biography/data#docRef> ?id .
            BIND(STR(?content) AS ?str_content)
    
        } $limit
        """

        query = query.replace("$offsetid",str(offsetid))
        query = query.replace("$limit", str(limit))

        # ?structure <http://ldf.fi/nbf/biography/data#bioId> <http://ldf.fi/nbf/p874> .
        print("endpoint:", endpoint)
        print("query:", query)

        #sparql.setQuery(query)
        #sparql.setHTTPAuth(BASIC)
        #sparql.setCredentials("Basic", "c2Vjbzpsb2dvczAz")
        #sparql.setReturnFormat(JSON)
        results = self.makeSparqlQuery(query, endpoint)
        #sparql.query().convert()

        #logging.info("Results %s ", results)

        return results

    def query_predifined_structures(self, uri, endpoint, offsetid, limit=1):
        strlimit = ""
        if limit > 0:
            strlimit = "LIMIT " + str(limit)
        else:
            strlimit = ""

        results = self.query_values(None, None, offsetid, strlimit)
        print("Results:", results, limit)

        return results

    def query_structures(self, uri, endpoint):
        sparql = SPARQLWrapper(endpoint)

        query = """
            SELECT distinct ?structure
            WHERE {
              ?sentence a <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#Sentence> .
              ?sentence <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#structure> ?structure .

            } LIMIT 5
        """
        # ?structure <http://ldf.fi/nbf/biography/data#bioId> <http://ldf.fi/nbf/p874> .
        #logging.info("endpoint= %s", endpoint)
        #logging.info("query= %s", query)

        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = makeSparqlQuery(query, endpoint)#sparql.query().convert()

        return results

    def default_query_words(self, url):
        #logging.info(url)
        endpoint = str(url) + "query"

        sparql = SPARQLWrapper(endpoint)

        query = """
               PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
               PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
               PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
               PREFIX dct: <http://purl.org/dc/terms/>
               SELECT ?x ?y ?sID ?z ?structure ?word ?s ?sentence ?paragraph ?upos ?feat ?edge WHERE {
                   ?s a <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#Word> ;
                       <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#WORD> ?word ;
                       <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#ID> ?id ;
                       <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#sentenceOrder> ?sID ;
                       <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#sentence> ?sentence ;
                       <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#structure> ?structure .
  					?sentence dct:isPartOf ?paragraph .
  					?paragraph <http://ldf.fi/nbf/biography/data#order> ?i .
                   OPTIONAL {
                       ?s <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#UPOS> ?upos .
                   }
                   OPTIONAL {
                       ?s <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#FEAT> ?feat .
                   }
                   OPTIONAL {
                       ?s <http://ufal.mff.cuni.cz/conll2009-st/task-description.html#EDGE> ?edge .
                   }
                 BIND(xsd:integer(?id) as ?x)
  				BIND(xsd:decimal(STR(?sID)) as ?y)
  				BIND(xsd:integer(?i) as ?z)
               } ORDER BY ASC(?structure) ASC(?z) ASC(?y) ASC(?x)
           """

        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        return results

    def makeSparqlQuery(self, query, endpoint):
        AUTHORIZATION_HEADER = {'Authorization': "Basic c2Vjbzpsb2dvczAz"}

        #print("Endpoint:", endpoint)
        #print("Query:", query)
        #print("Auth:", AUTHORIZATION_HEADER)

        try:
            r = requests.post(endpoint,
                              data={'query': query, 'format': 'json'},
                              headers=dict({'Accept': 'application/sparql-results+json'}, **AUTHORIZATION_HEADER))
            #print(r.text)
            cont = json.loads(r.text)
            #fields = cont['head']['vars']

            #bind = cont['results']['bindings']
            #res = []
            #for x in bind:
            #    row = {}
            #    for f in fields:
            #        if f in x and 'value' in x[f] and x[f]['value'] != "":
            #            row[f] = x[f]['value']
            #    res.append(row)
            return cont
        except Exception as e:
            # KeyError: no result
            raise e
        return []

