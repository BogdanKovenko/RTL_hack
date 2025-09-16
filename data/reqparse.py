from flask_restful import reqparse
import werkzeug


parser = reqparse.RequestParser()
parser.add_argument('title', required=True)
parser.add_argument('ssilka', required=True)
parser.add_argument('yroven', required=True)
parser.add_argument('type', required=True)
parser.add_argument('result', required=True)