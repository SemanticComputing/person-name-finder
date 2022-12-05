# name-finder-service

Person Name Finder searches for references of names based on Henko-ontology from the text and links them to it. It can also query context of a name such as titles associated with the name, name bearer's gender, or time span that can be associated with the name of a biographical person for instance.

## About

Using [person name ontology (HENKO)](http://light.onki.fi/henko/en/) and [LAS](http://demo.seco.tkk.fi/las/) the application extractes probable names from given input text.

### API

The service has also a usable API for testing. The service API description can be found from [Swagger](https://app.swaggerhub.com/apis-docs/SeCo/nlp.ldf.fi/1.0.0#/name-finder/).

### Publications

* Minna Tamper, Petri Leskinen, Jouni Tuominen and Eero Hyvönen: Modeling and Publishing Finnish Person Names as a Linked Open Data Ontology. 3rd Workshop on Humanities in the Semantic Web (WHiSe 2020), pp. 3-14, CEUR Workshop Proceedings, vol. 2695, June, 2020.


## Dependencies

* Python 3.5.2
* SparqlWrapper
* flask
* flask_cors
* nltk
* validators
* requests

For more information, check [requirements.txt](requirements.txt)

## Configurations

The configurations for the service can be found from the [config/config.ini](config/config.ini) file and configured based on service usage. Notice that all configurations here are not available on the API that contains simpler configurations for testing.

List of configurations available:

* henko_endpoint (default: http://ldf.fi/henko/sparql): sparql endpoint for quering person names
* gender_guess_url (default: http://nlp.ldf.fi/gender-identification): service used to identify gender from a name
* gender_guess_threshold (default: 0.8): gender identification accuracy threshold that is given to the gender guessing service
* regex_url (default: http://nlp.ldf.fi/regex): service used to identify dates from texts
* string_chunking_pattern (default: r'(, |; | \(|\)| ja | tai )'): regular expression pattern to cut sentences into smaller chunks for more accurate name identification
* contextual_chunking_single_separators (default: 'S', 'V'): separators used to identify the role of a person for example in matricles
* context_birth_identifiers (default: 's.', 'syntynyt'): words used in identifying date of birth in text
* context_death_identifiers (default: 'k.', 'kuollut'): words used in identifying date of death in text
* context_lifespan_separators (default: '-', '–'): separators between years

In order to use these configurations, set the environment variable NAME_FINDER_CONFIG_ENV to 'DEFAULT' or to you personal setting. The value is the section name in the config.ini file where the personal settings can be set for the attributes (configurations) defined above.

### Logging configuration

The configurations for logging are in the [conf/logging.ini](conf/logging.ini) file. In production, the configurations should be set to WARNING mode in all log files to limit the amount of logging to only errors. The INFO and DEBUG logging modes serve better the debugging in the development environment.

## Usage

To run use flask as follows:

1. export NAME_FINDER_CONFIG_ENV='DEFAULT'
2. export FLASK_APP=run.py
3. flask run
4. open browser and go to http://localhost:5000/.

#### Parameters

The http interface supports GET and POST methods for the users. Therefore users can give the parameters for GET method in the url:

```
http://nlp.ldf.fi/name-finder?text=Minna Susanna Claire Tamper
```
Post requests support parameters in the url, header, and from a form.

The application supports text mining for following parameters:
* text: the input text from which the entities are extracted
* gender: using gender guessing service to statistically determine gender
* date: extract dates that are related to a name, which are often lifespans or birth dates of a person
* title: extracts possible titles situated in front of the full name, e.g., Presidentti Sauli Niinistö

### Enabling gender guessing

Guess the gender of the name by adding url-parameter ```gender``` with a boolean value (true, 1, false, 0, etc.):

```
http://nlp.ldf.fi/name-finder?text=Minna Susanna Claire Tamper&gender=True
```

By default, the attribute gender is False.

### Enabling related date mining

The dates relating to a name can be extracted using ulr-parameter ```date``` with a boolean value (true, 1, false, 0, etc.):

```
http://nlp.ldf.fi/name-finder?text=Sauli Niinistö (s. 24. elokuuta 1948 Salo)&date=True
```

By default, the attribute date is False.

### Enabling related title mining

The title relating to a name can be extracted using ulr-parameter ```title``` with a boolean value (true, 1, false, 0, etc.):

```
http://nlp.ldf.fi/name-finder?text=Presidentti Sauli Niinistö&title=True
```

By default, the attribute title is False.

#### Results

Results are retuned in json format:

```
{"data":{"0":{"entities":[{"full_name":"Sauli Niinist\u00f6","full_name_lemma":"Sauli Niinist\u00f6","names":[{"end_ind":18,"lemma":"Sauli","location":"1","name":"Sauli","start_ind":13,"type":"Etunimi","uri":"http://ldf.fi/henko/n233"},{"end_ind":28,"lemma":"Niinist\u00f6","location":"2","name":"Niinist\u00f6","start_ind":20,"type":"Sukunimi","uri":"http://ldf.fi/henko/n22872"}],"titles":["presidentti"]}],"sentence":"Presidentti Sauli Niinist\u00f6"}},"date":"2020-05-13","service":"name-finder","status":200}
```

## Running in Docker

`docker-compose up`: builds and runs Name Finder and the needed backend services

The following configuration parameters must be passed as environment variables to the container:

* IP_BACKEND_LAS
* PORT_BACKEND_LAS
* HENKO_ENDPOINT_URL
* IP_BACKEND_GENDER_GUESS
* PORT_BACKEND_GENDER_GUESS
* IP_BACKEND_REGEX
* PORT_BACKEND_REGEX

Other configuration parameters should be set by using a config.ini (see section Configurations above) which can be e.g. bind mounted to container's path `/app/conf/config.ini`.

The log level can be specified by passing the following environment variable to the container:

* LOG_LEVEL
