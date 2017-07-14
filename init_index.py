import sys
import argparse
from elasticsearch import Elasticsearch
from gdcmodels import get_es_models


parser = argparse.ArgumentParser(
            description='Initialize ES index(es) with settings and mappings.')
parser.add_argument('--index', dest='index', required=True, nargs='+',
                    help='index to be initialized')
parser.add_argument('--prefix', dest='prefix', required=True,
                    help='prefix for the index name')
parser.add_argument('--host', dest='host', required=True,
                    help='Elasticsearch server host name or IP')
parser.add_argument('--port', dest='port', default=9200,
                    help='Elasticsearch server port (default: 9200)')
parser.add_argument('--user', dest='user', default='',
                    help='Elasticsearch client user')
parser.add_argument('--password', dest='password', default='',
                    help='Elasticsearch client password')
parser.add_argument('--delete', dest='delete', action='store_true',
                    help='Delete existing index with the same name')

args = parser.parse_args()
if len(args.prefix) == 0:
    sys.exit('Please specify prefix for the index name, eg, \'gdc_r52\'')


def init_index():
    es_models = get_es_models()

    es = Elasticsearch(hosts="%s:%s" % (args.host, args.port),
                        http_auth=(args.user, args.password))

    for i in args.index:
        if not es_models.get(i):
            print "Specified index name '%s' is not defined in es-models, skipping it!" % i
            continue

        index_name = '_'.join([args.prefix, i])
        if es.indices.exists(index=index_name):
            if not args.delete:
                print "Elasticsearch index '%s' exists, '--delete' not specified, skipping" % index_name
                continue
            else:
                print "Elasticsearch index '%s' exists, '--delete' specified" % index_name
                ans = raw_input("Confirm deleting existing index by typing the index name: ")
                if ans == index_name:
                    print "Deleting existing index '%s'" % index_name
                    es.indices.delete(index=index_name)
                else:
                    print "Index name mismatch, skipping deleting"
                    continue

        print "Creating index '%s'" % index_name
        es.indices.create(index=index_name, body=es_models[i]['_settings'])
        for index_type in es_models[i]:
            if index_type == '_settings': continue  # settings, not index type
            print "Creating index mapping '%s'" % index_name
            es.indices.put_mapping(doc_type=index_type,
                                        index=index_name,
                                        body=es_models[i][index_type]['_mapping']
                                    )


if __name__ == "__main__":
    init_index()
