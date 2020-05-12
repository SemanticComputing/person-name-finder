# name-finder-service

## About

Using [person name ontology, HENKO](http://light.onki.fi/henkilonimisto/en/) and [LAS](http://demo.seco.tkk.fi/las/) the application extractes probable names from given input text.

## Dependencies

* Python 3.5.2
* SparqlWrapper
* flask
* flask_cors
* nltk
* validators
* requests

For more information, check requirements.txt

## Configurations

The configurations for the service can be found from the config/config.ini file and configured based on service usage.

List of configurations available:

* henko_endpoint (default: http://ldf.fi/henko/sparql): sparql endpoint for quering person names
* gender_guess_url (default: http://nlp.ldf.fi/gender-guess): service used to identify gender from a name
* gender_guess_threshold (default: 0.8): gender identification accuracy threshold that is given to the gender guessing service
* regex_url (default: http://nlp.ldf.fi/regex): service used to identify dates from texts
* string_chunking_pattern (default: r'(, |; | \(|\)| ja | tai )'): regular expression pattern to cut sentences into smaller chunks for more accurate name identification
* contextual_chunking_single_separators (default: 'S', 'V'): separators used to identify the role of a person for example in matricles
* context_birth_identifiers (default: 's.', 'syntynyt'): words used in identifying date of birth in text
* context_death_identifiers (default: 'k.', 'kuollut'): words used in identifying date of death in text
* context_lifespan_separators (default: '-', '–'): separators between years

In order to use these configurations, set the environment variable NAME_FINDER_CONFIG_ENV to 'DEFAULT' or to you personal setting. The value is the section name in the config.ini file where the personal settings can be set for the attributes (configurations) defined above.

## Usage

To run use flask as follows:

1. export NAME_FINDER_CONFIG_ENV='DEFAULT'
2. export FLASK_APP=httpInterface.py
3. flask run
4. open browser and go to http://localhost:5000/.

#### Parameters

The http interface supports GET and POST methods for the users. Therefore users can give the parameters for GET method in the url:

```
http://nlp.ldf.fi/name-finder?text=Minna Susanna Claire Tamper
```
Post requests support parameters in the url, header, and from a form.

The application supports text mining for following parameters:
* gender (using gender guessing service to statistically determine gender)
* date (extract dates that are related to a name, which are often lifespans or birth dates of a person)

### Enabling gender guessing

Guess the gender of the name by adding url-parameter gender with a boolean value (true, 1, false, 0, etc.):

```
http://nlp.ldf.fi/name-finder?text=Minna Susanna Claire Tamper&gender=True
```

By default, the attribute gender is False.

### Enabling related date mining

The dates relating to a name can be guessed using ulr-parameter date with a boolean value (true, 1, false, 0, etc.):

```
http://nlp.ldf.fi/name-finder?text=Sauli Niinistö (s. 24. elokuuta 1948 Salo)&date=True
```

By default, the attribute date is False.

#### Results

Results are retuned in json format:

```

```

## Running in Docker

`docker-compose up`: builds and runs Name Finder and the needed backend services

The following configuration parameters must be passed as environment variables to the container:

* HENKO_ENDPOINT_URL
* IP_BACKEND_GENDER_GUESS
* PORT_BACKEND_GENDER_GUESS
* IP_BACKEND_REGEX
* PORT_BACKEND_REGEX

Other configuration parameters should be set by using a config.ini (see section Configurations above) which can be e.g. bind mounted to container's path `/app/conf/config.ini`.
