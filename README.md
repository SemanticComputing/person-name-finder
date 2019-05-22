# name-finder-service

## About

Using person name ontology (http://light.onki.fi/henkilonimisto/en/) and LAS (http://demo.seco.tkk.fi/las/) the application extractes probable names from given input text.

## Dependencies

* Python 3.5.2
* SparqlWrapper
* flask
* flask_cors
* nltk
* requests

For more information, check requirements.txt

## Usage

To run use flask as follows:

1. export FLASK_APP=httpInterface.py
2. flask run
3. open browser and go to http://localhost:5000/.

#### Parameters

The http interface supports GET and POST methods for the users. Therefore users can give the parameters for GET method in the url:

```
http://127.0.0.1:5000/?text=Minna Susanna Claire Tamper
```
Post requests support parameters in the url, header, and from a form.


#### Results

Results are retuned in json format:

```

```

## Running in Docker

`./docker-build.sh`: builds the service

`./docker-run.sh`: runs the service
